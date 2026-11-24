from fastapi import HTTPException
from sqlalchemy import select
from models.data_model import Case, Material, Conversation, Message

async def get_owned_case(db, user_id, case_id):
    case = await db.scalar(select(Case).where(Case.id == case_id, Case.user_id == user_id))
    if case is None:
        raise HTTPException(404, "案件不存在或无权访问")
    return case

async def get_owned_conversation(db, user_id, conversation_id):
    conversation = await db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
    if conversation is None:
        raise HTTPException(404, "会话不存在或无权访问")
    return conversation

# 所有 AI 工具都经过所有权检查；模型不能传入用户 ID 或任意 SQL。
async def get_case_context(db, user_id, case_id):
    case = await get_owned_case(db, user_id, case_id)
    materials = (await db.scalars(select(Material).where(Material.case_id == case.id).order_by(Material.id))).all()
    return {
        "来源": "当前用户数据库记录；用户陈述未经独立核验",
        "案件ID": case.id, "名称": case.title, "类型": case.category, "来源编号": f"case:{case.id}",
        "案情描述": case.description, "诉求": case.goal, "阶段": case.stage,
        "材料": [{"id": m.id, "来源编号": f"material:{m.id}", "名称": m.name, "说明": m.description, "状态": m.status} for m in materials],
        "提示": "没有记录的事实或材料不得当作已有；未提供经核验的法律知识库。",
    }

async def get_recent_messages(db, conversation_id, limit=12):
    rows = (await db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.desc()).limit(limit))).all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]
