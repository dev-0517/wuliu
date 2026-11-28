import math
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from db import get_db
from models import Branch, Order, Product, Track, User
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
    {"name": "智能快递柜月卡", "emoji": "🗄️", "desc": "专属格口随时取件", "price": 9.9, "color": "#e0f2fe"},
    {"name": "加厚气泡膜 10m", "emoji": "🧼", "desc": "寄快递防震必备", "price": 12.5, "color": "#fef9c3"},
    {"name": "物流行业模型摆件", "emoji": "🚚", "desc": "经典干线卡车 1:64", "price": 68.0, "color": "#fce7f3"},
    {"name": "保温生鲜箱 25L", "emoji": "🧊", "desc": "生鲜运输锁冷 48h", "price": 39.9, "color": "#dbeafe"},
    {"name": "便携电子秤 50kg", "emoji": "⚖️", "desc": "寄件称重不踩坑", "price": 25.0, "color": "#dcfce7"},
    {"name": "行李寄存袋 加厚", "emoji": "👜", "desc": "搬家寄存两相宜", "price": 15.8, "color": "#fde8e8"},
    {"name": "全局定位追踪器", "emoji": "📍", "desc": "贵重货物实时查", "price": 89.0, "color": "#ede9fe"},
    {"name": "纸箱打包套装 x20", "emoji": "📦", "desc": "五层加厚 各规格", "price": 29.9, "color": "#ffedd5"},
]


def ensure_products(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Product)):
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
             "price": float(p.price), "color": p.color, "stock": p.stock} for p in rows]


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
            "message": "下单成功，可在「快递」页查看物流"}


# ---------- 我的快递 ----------
@router.get("/my-orders")
def my_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Order)
        .where(or_(Order.sender_phone == user.username, Order.receiver_phone == user.username))
        .order_by(Order.created_at.desc()).limit(50)
    ).all()
    out = []
    for o in rows:
        role = "收件" if o.receiver_phone == user.username else "寄件"
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
