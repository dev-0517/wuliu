import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from config.db_config import get_database_session
from config.settings import AGREEMENT_VERSION
from models.data_model import User, LoginSession, AgreementRecord, Case, Conversation, now
from schemas.requests import RegisterRequest, LoginRequest, ProfileRequest
from utils.security import get_current_user, hash_password, verify_password, hash_token, bearer

router = APIRouter(prefix="/api", tags=["账号"])

def user_data(user):
    return {"id": user.id, "username": user.username, "nickname": user.nickname, "created_at": user.created_at}

async def create_login(db, user):
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(user_id=user.id, token_hash=hash_token(token), expires_at=now() + timedelta(days=7)))
    await db.commit()
    return {"token": token, "user": user_data(user)}

@router.post("/auth/register", status_code=201)
async def register(data: RegisterRequest, db=Depends(get_database_session)):
    if not data.agreed:
        raise HTTPException(400, "请阅读并同意服务协议、隐私说明与 AI 使用说明")
    if await db.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(409, "账号已存在")
    user = User(username=data.username, nickname=data.nickname, password_hash=hash_password(data.password))
    db.add(user)
    try:
        await db.flush()
        db.add(AgreementRecord(user_id=user.id, version=AGREEMENT_VERSION))
        return await create_login(db, user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "账号已存在")

@router.post("/auth/login")
async def login(data: LoginRequest, db=Depends(get_database_session)):
    user = await db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "账号或密码不正确")
    return await create_login(db, user)

@router.post("/auth/logout")
async def logout(user=Depends(get_current_user), credentials=Depends(bearer), db=Depends(get_database_session)):
    session = await db.scalar(select(LoginSession).where(LoginSession.token_hash == hash_token(credentials.credentials)))
    if session:
        await db.delete(session)
        await db.commit()
    return {"message": "已退出登录"}

@router.get("/profile")
async def profile(user=Depends(get_current_user), db=Depends(get_database_session)):
    cases = await db.scalar(select(func.count(Case.id)).where(Case.user_id == user.id))
    conversations = await db.scalar(select(func.count(Conversation.id)).where(Conversation.user_id == user.id))
    return {**user_data(user), "case_count": cases, "conversation_count": conversations}

@router.patch("/profile")
async def update_profile(data: ProfileRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    user.nickname = data.nickname
    await db.commit()
    return user_data(user)
