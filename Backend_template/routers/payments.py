# -*- coding: utf-8 -*-
"""管理端支付审核：用户扫码付款后生成记录，管理员批准后派发货物。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Order, Payment, Track, User
from security import current_user

router = APIRouter(prefix="/payments", tags=["支付审核"])


def _admin(user: User) -> User:
    if user.role != "admin":
        raise HTTPException(403, "仅管理员可审核支付")
    return user


@router.get("")
def payments_list(user: User = Depends(current_user), db: Session = Depends(get_db)):
    _admin(user)
    rows = db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(100)).all()
    out = []
    for r in rows:
        o = db.get(Order, r.order_id)
        u = db.get(User, r.user_id)
        out.append({
            "id": r.id, "order_no": o.order_no if o else "", "goods": o.goods if o else "",
            "username": u.username if u else "",
            "method": r.method, "amount": float(r.amount), "status": r.status,
            "created_at": r.created_at.strftime("%m-%d %H:%M"),
            "reviewed_at": r.reviewed_at.strftime("%m-%d %H:%M") if r.reviewed_at else "",
        })
    return out


@router.post("/{pid}/approve")
def approve(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _admin(user)
    rec = db.get(Payment, pid)
    if not rec:
        raise HTTPException(404, "支付记录不存在")
    if rec.status != "paid":
        raise HTTPException(409, "该记录已处理过")
    rec.status = "approved"
    rec.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    order = db.get(Order, rec.order_id)
    if order:
        order.status = "picked"     # 审核通过 → 派发货物
        db.add(Track(order_id=order.id, status="picked",
                     location="智慧商城前置仓", note="支付审核通过，货物已打包发出"))
    db.commit()
    return {"ok": True, "message": "已批准，货物派发中"}


@router.post("/{pid}/reject")
def reject(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _admin(user)
    rec = db.get(Payment, pid)
    if not rec:
        raise HTTPException(404, "支付记录不存在")
    if rec.status != "paid":
        raise HTTPException(409, "该记录已处理过")
    rec.status = "rejected"
    rec.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"ok": True, "message": "已驳回"}
