from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from db import get_db
from models import Order, Track, User
from schemas import OrderDetail, OrderIn, OrderOut, Page, StatusIn, TrackOut
from security import current_user, require_admin

router = APIRouter(prefix="/orders", tags=["运单"])

VALID_STATUS = ["pending", "picked", "transit", "delivered", "exception"]


def next_order_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"WY{today}"
    count = db.scalar(select(func.count()).select_from(Order).where(Order.order_no.like(f"{prefix}%"))) or 0
    for _ in range(50):
        count += 1
        candidate = f"{prefix}{count:04d}"
        if not db.scalar(select(Order.id).where(Order.order_no == candidate)):
            return candidate
    return f"{prefix}{datetime.now().strftime('%H%M%S')}"


@router.get("", response_model=Page)
def list_orders(
    status: str = "",
    keyword: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Order.order_no.like(like),
                Order.sender_name.like(like),
                Order.receiver_name.like(like),
                Order.sender_phone.like(like),
                Order.receiver_phone.like(like),
                Order.goods.like(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Order.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return Page(total=total, items=[OrderOut.model_validate(x) for x in items])


@router.post("", response_model=OrderOut)
def create_order(payload: OrderIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = Order(**payload.model_dump(), order_no=next_order_no(db))
    db.add(obj)
    db.flush()
    db.add(Track(order_id=obj.id, status="pending", location="下单网点", note="已创建运单，等待揽收"))
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{oid}", response_model=OrderDetail)
def get_order(oid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.scalar(select(Order).where(Order.id == oid).options(selectinload(Order.tracks)))
    if not obj:
        raise HTTPException(404, "运单不存在")
    return OrderDetail.model_validate(obj)


@router.put("/{oid}", response_model=OrderOut)
def update_order(oid: int, payload: OrderIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Order, oid)
    if not obj:
        raise HTTPException(404, "运单不存在")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{oid}/status", response_model=OrderDetail)
def change_status(oid: int, payload: StatusIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    if payload.status not in VALID_STATUS:
        raise HTTPException(400, f"状态非法，可选：{'/'.join(VALID_STATUS)}")
    obj = db.scalar(select(Order).where(Order.id == oid).options(selectinload(Order.tracks)))
    if not obj:
        raise HTTPException(404, "运单不存在")
    obj.status = payload.status
    db.add(Track(order_id=obj.id, status=payload.status, location=payload.location, note=payload.note))
    db.commit()
    db.refresh(obj)
    return OrderDetail.model_validate(obj)


@router.get("/{oid}/tracks", response_model=list[TrackOut])
def list_tracks(oid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    if not db.get(Order, oid):
        raise HTTPException(404, "运单不存在")
    return db.scalars(select(Track).where(Track.order_id == oid).order_by(Track.id)).all()


@router.delete("/{oid}")
def delete_order(oid: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    obj = db.get(Order, oid)
    if not obj:
        raise HTTPException(404, "运单不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}
