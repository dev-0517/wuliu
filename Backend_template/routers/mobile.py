import math
import random
import re
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from db import get_db
from models import Branch, Order, Payment, Product, Track, User
from routers.orders import next_order_no
from schemas import OrderDetail, TrackOut
from security import current_user

router = APIRouter(prefix="/mobile", tags=["用户端APP"])

CITY_COORDS = {
    "杭州": (120.15, 30.28),
    "上海": (121.47, 31.23),
    "南京": (118.78, 32.06),
}
STATUS_LABEL = {
    "pending": "待揽收",
    "picked": "已揽收",
    "transit": "运输中",
    "delivered": "已签收",
    "exception": "异常",
}

DEMO_PRODUCTS = [
    {"name": "智能快递柜月卡", "emoji": "🗄️", "desc": "专属格口随时取件", "price": 9.9, "color": "#e0f2fe", "image": "/static/products/p1.jpg"},
    {"name": "加厚气泡膜 10m", "emoji": "🧼", "desc": "寄快递防震必备", "price": 12.5, "color": "#fef9c3", "image": "/static/products/p2.jpg"},
    {"name": "物流行业模型摆件", "emoji": "🚚", "desc": "经典干线卡车 1:64", "price": 68.0, "color": "#fce7f3", "image": "/static/products/p3.jpg"},
    {"name": "保温生鲜箱 25L", "emoji": "🧊", "desc": "生鲜运输锁冷 48h", "price": 39.9, "color": "#dbeafe", "image": "/static/products/p4.jpg"},
    {"name": "便携电子秤 50kg", "emoji": "⚖️", "desc": "寄件称重不踩坑", "price": 25.0, "color": "#dcfce7", "image": "/static/products/p5.jpg"},
    {"name": "行李寄存袋 加厚", "emoji": "👜", "desc": "搬家寄存两相宜", "price": 15.8, "color": "#fde8e8", "image": "/static/products/p6.jpg"},
    {"name": "全局定位追踪器", "emoji": "📍", "desc": "贵重货物实时查", "price": 89.0, "color": "#ede9fe", "image": "/static/products/p7.jpg"},
    {"name": "纸箱打包套装 x20", "emoji": "📦", "desc": "五层加厚 各规格", "price": 29.9, "color": "#ffedd5", "image": "/static/products/p8.jpg"},
]


def ensure_products(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Product)):
        # 老数据回填商品图片（按名称匹配）
        by_name = {p["name"]: p["image"] for p in DEMO_PRODUCTS}
        for row in db.scalars(select(Product)).all():
            if not row.image and row.name in by_name:
                row.image = by_name[row.name]
        db.commit()
        return
    for p in DEMO_PRODUCTS:
        db.add(Product(**p))
    db.commit()


def branch_coord(b: Branch) -> tuple[float, float]:
    """网点坐标：按城市基准 + 确定性偏移（演示环境无真实经纬度）"""
    base = CITY_COORDS.get(b.city, (120.15, 30.28))
    rnd = random.Random(b.id * 97 + 13)
    return (round(base[0] + rnd.uniform(-0.08, 0.08), 4),
            round(base[1] + rnd.uniform(-0.06, 0.06), 4))


def haversine(lon1, lat1, lon2, lat2) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def _own_order(db: Session, oid: int, user: User) -> Order:
    order = db.get(Order, oid)
    if not order:
        raise HTTPException(404, "运单不存在")
    if user.username not in (order.sender_phone, order.receiver_phone):
        raise HTTPException(403, "只能查看自己的运单")
    return order


def _create_order(db: Session, **kw) -> Order:
    order = Order(order_no=next_order_no(db), status="pending", **kw)
    db.add(order)
    db.flush()
    db.add(Track(order_id=order.id, status="pending", location=kw.get("sender_address", ""),
                 note="订单已创建，等待揽收"))
    db.commit()
    db.refresh(order)
    return order


# ---------- 商城 ----------
@router.get("/products")
def products(db: Session = Depends(get_db)):
    ensure_products(db)
    rows = db.scalars(select(Product).order_by(Product.id)).all()
    return [{"id": p.id, "name": p.name, "emoji": p.emoji, "desc": p.desc,
             "price": float(p.price), "color": p.color, "stock": p.stock,
             "image": p.image} for p in rows]


@router.post("/buy/{pid}")
def buy(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_products(db)
    p = db.get(Product, pid)
    if not p:
        raise HTTPException(404, "商品不存在")
    first = db.scalar(select(Branch).order_by(Branch.id))
    order = _create_order(
        db,
        sender_name="智慧商城仓库",
        sender_phone="10086",
        sender_address=first.city + "·商城前置仓" if first else "杭州·商城前置仓",
        receiver_name=user.username,
        receiver_phone=user.username,
        receiver_address="收货地址：下单时填写（演示默认网点自提）",
        origin_branch_id=first.id if first else None,
        goods=f"{p.name} ×1",
        weight_kg=round(random.uniform(0.5, 3.0), 2),
        remark=f"商城下单 #{p.id}",
    )
    return {"ok": True, "order_id": order.id, "order_no": order.order_no,
            "amount": float(p.price),
            "message": "下单成功，请完成支付，审核通过后即派发货物"}


# ---------- 我的快递 ----------
@router.get("/my-orders")
def my_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    phones = {user.username, user.bound_phone} - {""}
    rows = db.scalars(
        select(Order)
        .where(or_(*[or_(Order.sender_phone == p, Order.receiver_phone == p) for p in phones]))
        .order_by(Order.created_at.desc()).limit(50)
    ).all()
    out = []
    for o in rows:
        role = "收件" if o.receiver_phone in phones else "寄件"
        out.append({
            "id": o.id, "order_no": o.order_no, "goods": o.goods,
            "status": o.status, "status_label": STATUS_LABEL.get(o.status, o.status),
            "sender_address": o.sender_address, "receiver_address": o.receiver_address,
            "weight_kg": float(o.weight_kg), "role": role,
            "created_at": o.created_at.strftime("%m-%d %H:%M"),
        })
    return out


@router.get("/my-orders/{oid}", response_model=OrderDetail)
def my_order_detail(oid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _own_order(db, oid, user)


@router.get("/my-orders/{oid}/tracks", response_model=list[TrackOut])
def my_order_tracks(oid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = _own_order(db, oid, user)
    return order.tracks


# ---------- 寄快递 ----------
@router.post("/send")
def send_parcel(payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = str(payload.get("receiver_name", "")).strip()
    phone = str(payload.get("receiver_phone", "")).strip()
    addr = str(payload.get("receiver_address", "")).strip()
    goods = str(payload.get("goods", "个人寄件")).strip() or "个人寄件"
    weight = float(payload.get("weight_kg") or 1.0)
    if not name or not phone:
        raise HTTPException(400, "请填写收件人姓名和电话")
    first = db.scalar(select(Branch).order_by(Branch.id))
    order = _create_order(
        db,
        sender_name=user.username,
        sender_phone=user.username,
        sender_address="本人寄件（网点自送）",
        receiver_name=name,
        receiver_phone=phone,
        receiver_address=addr,
        origin_branch_id=first.id if first else None,
        goods=goods,
        weight_kg=weight,
        remark="用户端寄件",
    )
    return {"ok": True, "order_id": order.id, "order_no": order.order_no,
            "message": "寄件下单成功，等待网点揽收"}


# ---------- 附近网点 ----------
@router.get("/nearby")
def nearby(lat: float = 30.28, lon: float = 120.15, db: Session = Depends(get_db)):
    rows = db.scalars(select(Branch).order_by(Branch.id)).all()
    items = []
    for b in rows:
        blo, bla = branch_coord(b)
        items.append({
            "id": b.id, "code": b.code, "name": b.name, "city": b.city,
            "address": b.address, "phone": b.phone,
            "lon": blo, "lat": bla,
            "distance_km": haversine(lon, lat, blo, bla),
        })
    items.sort(key=lambda x: x["distance_km"])
    return items[:10]


# ---------- 支付（扫码收款 + 后台审核） ----------
@router.post("/pay/{oid}")
def pay(oid: int, payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """选择微信/支付宝支付：返回对应收款码，生成支付记录，等待管理员审核。"""
    order = _own_order(db, oid, user)
    method = payload.get("method", "wechat")
    if method not in ("wechat", "alipay"):
        raise HTTPException(400, "支付方式仅支持 wechat / alipay")
    # 金额取商品价格（商城单 remark 带 #pid）；寄件单不在线支付
    m = re.search(r"#(\d+)", order.remark or "")
    amount = 0.0
    if m:
        p = db.get(Product, int(m.group(1)))
        if p:
            amount = float(p.price)
    if amount <= 0:
        raise HTTPException(400, "该运单无需在线支付")
    dup = db.scalar(select(Payment).where(
        Payment.order_id == oid, Payment.status.in_(["paid", "approved"])))
    if dup:
        raise HTTPException(409, "该订单已有支付记录，请等待审核")
    pay_rec = Payment(order_id=oid, user_id=user.id, method=method, amount=amount)
    db.add(pay_rec)
    db.commit()
    db.refresh(pay_rec)
    return {"ok": True, "payment_id": pay_rec.id, "amount": amount,
            "qr": "/static/pay/wechat_qr.jpg" if method == "wechat" else "/static/pay/alipay_qr.jpg",
            "message": "请扫码支付后点击「我已完成支付」"}


@router.post("/pay-confirm/{payment_id}")
def pay_confirm(payment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """用户扫码付款后确认：记录进入「已付款待审核」状态。"""
    rec = db.get(Payment, payment_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "支付记录不存在")
    if rec.status != "paid":
        raise HTTPException(409, "该记录状态不允许重复确认")
    return {"ok": True, "message": "支付记录已提交，管理员审核通过后将派发货物"}


@router.get("/my-payments")
def my_payments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Payment).where(Payment.user_id == user.id)
                      .order_by(Payment.created_at.desc()).limit(30)).all()
    out = []
    for r in rows:
        o = db.get(Order, r.order_id)
        out.append({
            "id": r.id, "order_no": o.order_no if o else "", "goods": o.goods if o else "",
            "method": r.method, "amount": float(r.amount), "status": r.status,
            "created_at": r.created_at.strftime("%m-%d %H:%M"),
        })
    return out


# ---------- 个人资料：头像 / 昵称 / 绑定 ----------
def _mask_phone(p: str) -> str:
    return f"{p[:3]}****{p[7:]}" if len(p) == 11 else p


@router.get("/profile")
def profile(user: User = Depends(current_user)):
    return {
        "username": user.username, "role": user.role,
        "display_name": user.display_name or user.username,
        "avatar": user.avatar or "",
        "bound_phone": _mask_phone(user.bound_phone) if user.bound_phone else "",
        "bound_wechat": user.bound_wechat or "",
        "bound_qq": user.bound_qq or "",
        "created_at": user.created_at.strftime("%Y-%m-%d"),
    }


@router.post("/profile")
def update_profile(payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = str(payload.get("display_name", "")).strip()
    avatar = str(payload.get("avatar", "")).strip()
    if name:
        user.display_name = name[:20]
    if avatar:
        if len(avatar) > 400_000:
            raise HTTPException(413, "头像图片过大，请换小图")
        if not avatar.startswith("data:image/"):
            raise HTTPException(400, "头像格式不正确")
        user.avatar = avatar
    db.commit()
    return {"ok": True, "message": "资料已更新"}


@router.post("/bind/phone")
def bind_phone(payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """绑定手机号：需先获取短信验证码（真实短信/演示回显由系统配置决定）。"""
    from routers.auth import _sms_codes
    phone = str(payload.get("phone", "")).strip()
    code = str(payload.get("code", "")).strip()
    if not re.fullmatch(r"1\d{10}", phone):
        raise HTTPException(400, "请输入正确的 11 位手机号")
    item = _sms_codes.get(phone)
    if not item or item[0] != code or item[1] < time.time():
        raise HTTPException(401, "验证码错误或已过期")
    _sms_codes.pop(phone, None)
    clash = db.scalar(select(User).where(User.username == phone))
    if clash and clash.id != user.id:
        raise HTTPException(409, "该手机号已被其他账号绑定")
    user.bound_phone = phone
    db.commit()
    return {"ok": True, "message": f"手机号 {_mask_phone(phone)} 绑定成功"}


@router.post("/bind/social")
def bind_social(payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """绑定微信/QQ。演示模式由前端确认；接开放平台后此处换成 OAuth 回调落库。"""
    kind = payload.get("kind", "")
    nick = str(payload.get("nickname", "")).strip()[:30]
    if kind not in ("wechat", "qq") or not nick:
        raise HTTPException(400, "参数不完整")
    if kind == "wechat":
        user.bound_wechat = nick
    else:
        user.bound_qq = nick
    db.commit()
    return {"ok": True, "message": f"{'微信' if kind == 'wechat' else 'QQ'}「{nick}」绑定成功"}
