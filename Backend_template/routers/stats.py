from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import Branch, Driver, Order, User, Vehicle
from security import current_user

router = APIRouter(prefix="/stats", tags=["统计"])

TREND_DAYS = 14


def _daily_counts(db: Session, start: datetime, end: datetime):
    rows = db.execute(
        select(func.date(Order.created_at), func.count())
        .where(Order.created_at >= start, Order.created_at < end)
        .group_by(func.date(Order.created_at))
    ).all()
    return {str(d): n for d, n in rows}


@router.get("")
def stats(db: Session = Depends(get_db), _: User = Depends(current_user)):
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time())

    by_status_rows = db.execute(select(Order.status, func.count()).group_by(Order.status)).all()
    by_status = {status: count for status, count in by_status_rows}
    total = sum(by_status.values())

    today_rows = db.execute(
        select(Order.status, func.count()).where(Order.created_at >= today_start).group_by(Order.status)
    ).all()
    today_by_status = {status: count for status, count in today_rows}
    today_total = sum(today_by_status.values())

    delivered = by_status.get("delivered", 0)
    exception = by_status.get("exception", 0)
    completion = round(delivered / total * 100, 1) if total else 0
    normal_rate = round((total - exception) / total * 100, 1) if total else 100
    exception_rate = round(100 - normal_rate, 1)

    # 网点运单量排行（含重量）
    branch_rows = db.execute(
        select(
            Branch.id,
            Branch.name,
            func.count(Order.id),
            func.coalesce(func.sum(Order.weight_kg), 0.0),
        )
        .outerjoin(Order, Order.origin_branch_id == Branch.id)
        .group_by(Branch.id, Branch.name)
        .order_by(func.count(Order.id).desc())
        .limit(5)
    ).all()
    branch_count = db.scalar(select(func.count()).select_from(Branch)) or 0

    # 司机接单排行
    driver_rows = db.execute(
        select(Driver.name, func.count(Order.id))
        .outerjoin(Order, Order.driver_id == Driver.id)
        .group_by(Driver.id, Driver.name)
        .order_by(func.count(Order.id).desc())
        .limit(5)
    ).all()

    # 车辆承运排行与状态分布
    vehicle_rows = db.execute(
        select(Vehicle.plate, Vehicle.status, func.count(Order.id))
        .outerjoin(Order, Order.vehicle_id == Vehicle.id)
        .group_by(Vehicle.id, Vehicle.plate, Vehicle.status)
        .order_by(func.count(Order.id).desc())
        .limit(5)
    ).all()
    vehicle_status_rows = db.execute(select(Vehicle.status, func.count()).group_by(Vehicle.status)).all()
    vehicle_by_status = {status: count for status, count in vehicle_status_rows}
    vehicle_total = sum(vehicle_by_status.values())
    vehicle_used = vehicle_total - vehicle_by_status.get("idle", 0)
    vehicle_usage = round(vehicle_used / vehicle_total * 100, 1) if vehicle_total else 0

    # 近 14 天趋势 + 本月日历
    trend_start = today_start - timedelta(days=TREND_DAYS - 1)
    trend_map = _daily_counts(db, trend_start, now)
    trend = [
        {"date": (trend_start + timedelta(days=i)).strftime("%m-%d"),
         "count": trend_map.get((trend_start + timedelta(days=i)).date().isoformat(), 0)}
        for i in range(TREND_DAYS)
    ]
    month_start = datetime.combine(now.date().replace(day=1), datetime.min.time())
    month_map = _daily_counts(db, month_start, now)

    return {
        "total_orders": total,
        "today_new": today_total,
        "by_status": by_status,
        "today_by_status": today_by_status,
        "completion_rate": completion,
        "normal_rate": normal_rate,
        "exception_rate": exception_rate,
        "branches": branch_count,
        "branch_weight": round(db.scalar(select(func.coalesce(func.sum(Order.weight_kg), 0.0))) or 0, 1),
        "branch_rank": [
            {"name": name, "orders": n, "weight": round(float(w or 0), 1)} for _, name, n, w in branch_rows
        ],
        "vehicles": db.scalar(select(func.count()).select_from(Vehicle)) or 0,
        "drivers": db.scalar(select(func.count()).select_from(Driver)) or 0,
        "vehicle_by_status": vehicle_by_status,
        "vehicle_usage": vehicle_usage,
        "vehicle_rank": [{"plate": plate, "status": status, "orders": n} for plate, status, n in vehicle_rows],
        "driver_rank": [{"name": name, "orders": n} for name, n in driver_rows],
        "trend": trend,
        "calendar": month_map,
    }
