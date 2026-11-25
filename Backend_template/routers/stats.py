from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import Branch, Driver, Order, User, Vehicle
from security import current_user

router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("")
def stats(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = db.execute(select(Order.status, func.count()).group_by(Order.status)).all()
    by_status = {status: count for status, count in rows}

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_new = db.scalar(select(func.count()).select_from(Order).where(Order.created_at >= today_start)) or 0

    return {
        "total_orders": db.scalar(select(func.count()).select_from(Order)) or 0,
        "today_new": today_new,
        "by_status": by_status,
        "branches": db.scalar(select(func.count()).select_from(Branch)) or 0,
        "vehicles": db.scalar(select(func.count()).select_from(Vehicle)) or 0,
        "drivers": db.scalar(select(func.count()).select_from(Driver)) or 0,
    }
