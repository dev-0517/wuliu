from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from config.db_config import get_database_session
from config.settings import DEEPSEEK_MODEL
from models.data_model import Conversation, Message, MessageSource, now
from schemas.requests import ConversationRequest, ConversationUpdate, ChatRequest
from utils.security import get_current_user
from crud.cases import get_owned_case, get_owned_conversation, get_recent_messages, get_case_context
from services.ai_service import generate_answer, DISCLAIMER
from services.grounding import source_catalog, validate_answer_sources

router = APIRouter(prefix="/api/conversations", tags=["AI 对话与历史"])
# MVP 单进程保护：同一个会话生成期间拒绝重复发送，finally 确保释放。
busy_conversations = set()

@router.get("")
async def history(period: str = Query("all", pattern="^(all|week|month|halfyear)$"), page: int = Query(1, ge=1), q: str = Query("", max_length=100), mode: str = Query("all", pattern="^(all|general|case)$"), user=Depends(get_current_user), db=Depends(get_database_session)):
    statement = select(Conversation).where(Conversation.user_id == user.id)
    if q.strip():
        matched_messages = select(Message.conversation_id).where(Message.content.contains(q.strip(), autoescape=True))
        statement = statement.where(or_(Conversation.title.contains(q.strip(), autoescape=True), Conversation.id.in_(matched_messages)))
    if mode == "general":
        statement = statement.where(Conversation.case_id.is_(None))
    elif mode == "case":
        statement = statement.where(Conversation.case_id.is_not(None))
    days = {"week": 7, "month": 30, "halfyear": 180}.get(period)
    if days:
        statement = statement.where(Conversation.updated_at >= now()-timedelta(days=days))
    return (await db.scalars(statement.order_by(Conversation.updated_at.desc(), Conversation.id.desc()).offset((page-1)*20).limit(20))).all()

@router.post("", status_code=201)
async def create(data: ConversationRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, data.case_id) if data.case_id is not None else None
    conversation = Conversation(user_id=user.id, case_id=case.id if case else None, title=f"{case.title} · 咨询"[:100] if case else "与小诺的新对话")
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

@router.get("/{conversation_id}")
async def detail(conversation_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    conversation = await get_owned_conversation(db, user.id, conversation_id)
    messages = (await db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id))).all()
    sources = (await db.scalars(select(MessageSource).join(Message, Message.id == MessageSource.message_id).where(Message.conversation_id == conversation_id))).all()
    lookup = {s.message_id: s.sources for s in sources}
    return {"conversation": conversation, "messages": [{**jsonable_encoder(m), "sources": lookup.get(m.id, [])} for m in messages]}

@router.patch("/{conversation_id}")
async def rename(conversation_id: int, data: ConversationUpdate, user=Depends(get_current_user), db=Depends(get_database_session)):
    conversation = await get_owned_conversation(db, user.id, conversation_id)
    if conversation_id in busy_conversations:
        raise HTTPException(409, "正在生成回答，请稍后修改标题")
    conversation.title = data.title
    await db.commit()
    return conversation

@router.delete("/{conversation_id}")
async def remove(conversation_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    conversation = await get_owned_conversation(db, user.id, conversation_id)
    if conversation_id in busy_conversations:
        raise HTTPException(409, "正在生成回答，请稍后删除")
    await db.delete(conversation)
    await db.commit()
    return {"message": "已删除会话"}

@router.post("/{conversation_id}/messages")
async def send(conversation_id: int, data: ChatRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    conversation = await get_owned_conversation(db, user.id, conversation_id)
    if conversation_id in busy_conversations:
        raise HTTPException(409, "当前会话正在生成回答，请勿重复发送")
    busy_conversations.add(conversation_id)
    try:
        recent_count = await db.scalar(select(func.count(Message.id)).join(Conversation).where(Conversation.user_id == user.id, Message.role == "user", Message.created_at >= now()-timedelta(minutes=1)))
        if recent_count >= 6:
            raise HTTPException(429, "每分钟最多发送 6 条问题，请稍后再试")
        history = await get_recent_messages(db, conversation_id)
        context = await get_case_context(db, user.id, conversation.case_id) if conversation.case_id is not None else None
        sources = source_catalog(context) if context is not None else []
        # 释放读取事务，避免在模型等待期间占用数据库事务。
        await db.commit()
        answer, tokens = await generate_answer(db, user.id, conversation.case_id, history, data.content, context=context)
        if context is not None:
            validate_answer_sources(answer, sources)
        question = Message(conversation_id=conversation_id, role="user", content=data.content)
        reply = Message(conversation_id=conversation_id, role="assistant", content=answer + ("\n\n" + DISCLAIMER if context is not None else ""), model=DEEPSEEK_MODEL, token_usage=tokens)
        db.add_all([question, reply])
        await db.flush()
        if sources:
            db.add(MessageSource(message_id=reply.id, sources=sources))
        if conversation.case_id is None and not history:
            conversation.title = data.content[:40]
        conversation.updated_at = now()
        # 成功后成对保存，失败时不留下重复提问和虚假的成功回答。
        await db.commit()
        await db.refresh(question)
        await db.refresh(reply)
        return {"question": question, "reply": {**jsonable_encoder(reply), "sources": sources}, "title": conversation.title}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "会话或关联案件已变化，本轮未保存，请刷新后重试")
    finally:
        busy_conversations.discard(conversation_id)
