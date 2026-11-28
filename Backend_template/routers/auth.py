import random
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import User
from schemas import LoginIn, PhoneLoginIn, PhoneSendIn, QrCreateOut, QrPollOut, RegisterIn, TokenOut, UserOut
from security import create_token, current_user, hash_password, verify_password
from sms import send_sms, sms_configured

router = APIRouter(prefix="/auth", tags=["认证"])

# 演示环境：短信验证码与扫码登录状态存内存（真实环境应接短信服务商/微信开放平台回调）
_sms_codes: dict[str, tuple[str, float]] = {}   # phone -> (code, expire_ts)
_qr_logins: dict[str, dict] = {}                # uuid -> {"status": waiting|confirmed, "token": ..., "user": ...}

SMS_TTL = 300          # 验证码 5 分钟有效
QR_TTL = 300           # 扫码二维码 5 分钟有效


def _cleanup():
    now = time.time()
    for k in [k for k, (_, exp) in _sms_codes.items() if exp < now]:
        _sms_codes.pop(k, None)
    for k, v in list(_qr_logins.items()):
        if v.get("expire", now + QR_TTL) < now:
            _qr_logins.pop(k, None)


def _token_out(user: User) -> TokenOut:
    return TokenOut(token=create_token(user), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return _token_out(user)


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(409, "该用户名已被注册")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role="operator")
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_out(user)


@router.post("/sms/send")
def sms_send(payload: PhoneSendIn, db: Session = Depends(get_db)):
    """发送短信验证码。已配置短信服务则真实下发，否则演示模式回显。"""
    _cleanup()
    code = f"{random.randint(0, 999999):06d}"
    _sms_codes[payload.phone] = (code, time.time() + SMS_TTL)
    if sms_configured():
        try:
            send_sms(payload.phone, code)
            return {"ok": True, "expire_in": SMS_TTL,
                    "message": "验证码已发送到你的手机，请查收短信"}
        except Exception as exc:
            # 发送失败则作废该验证码，避免演示回显泄露
            _sms_codes.pop(payload.phone, None)
            raise HTTPException(502, f"短信发送失败：{exc}")
    return {"ok": True, "expire_in": SMS_TTL, "demo_code": code,
            "message": "演示环境未配置短信服务，验证码已直接回显"}


@router.post("/phone-login", response_model=TokenOut)
def phone_login(payload: PhoneLoginIn, db: Session = Depends(get_db)):
    """手机号 + 验证码登录，首次登录自动注册。"""
    _cleanup()
    item = _sms_codes.get(payload.phone)
    if not item or item[0] != payload.code or item[1] < time.time():
        raise HTTPException(401, "验证码错误或已过期")
    _sms_codes.pop(payload.phone, None)
    user = db.scalar(select(User).where(User.username == payload.phone))
    if not user:
        user = User(username=payload.phone, password_hash=hash_password(secrets.token_hex(16)), role="operator")
        db.add(user)
        db.commit()
        db.refresh(user)
    return _token_out(user)


@router.post("/qr/create", response_model=QrCreateOut)
def qr_create(db: Session = Depends(get_db)):
    """生成扫码登录二维码。演示模式：二维码由前端绘制，需点击「模拟扫码」确认。"""
    _cleanup()
    qid = uuid.uuid4().hex
    _qr_logins[qid] = {"status": "waiting", "expire": time.time() + QR_TTL}
    return QrCreateOut(uuid=qid, expire_in=QR_TTL)


@router.get("/qr/poll", response_model=QrPollOut)
def qr_poll(uuid: str, db: Session = Depends(get_db)):
    """前端轮询扫码状态；confirmed 时返回 token 并使二维码失效（一次性）。"""
    _cleanup()
    item = _qr_logins.get(uuid)
    if not item:
        return QrPollOut(status="expired")
    if item["status"] == "confirmed":
        _qr_logins.pop(uuid, None)
        return QrPollOut(status="confirmed", token=item["token"], user=item["user"])
    return QrPollOut(status="waiting")


@router.post("/qr/confirm", response_model=TokenOut)
def qr_confirm(uuid: str, db: Session = Depends(get_db)):
    """确认扫码（演示模式由前端按钮触发；真实环境由微信/QQ 开放平台回调）。"""
    _cleanup()
    item = _qr_logins.get(uuid)
    if not item:
        raise HTTPException(404, "二维码已过期，请刷新")
    # 为本次扫码创建一个临时访客账号
    user = User(username=f"guest_{uuid[:8]}", password_hash=hash_password(secrets.token_hex(16)), role="operator")
    db.add(user)
    db.commit()
    db.refresh(user)
    out = _token_out(user)
    item["status"] = "confirmed"
    item["token"] = out.token
    item["user"] = out.user.model_dump()
    return out


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut.model_validate(user)
