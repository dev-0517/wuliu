import hashlib
import hmac
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_database_session
from models.data_model import User, LoginSession, now

bearer = HTTPBearer(auto_error=False)

def hash_password(password: str):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}${digest}"

def verify_password(password: str, stored: str):
    salt, expected = stored.split("$")
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)

def hash_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_database_session)):
    if credentials is None:
        raise HTTPException(401, "请先登录")
    result = await db.execute(select(User).join(LoginSession, LoginSession.user_id == User.id).where(
        LoginSession.token_hash == hash_token(credentials.credentials), LoginSession.expires_at > now()))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    return user
