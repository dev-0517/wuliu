from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import AMAP_KEY, AMAP_SECURITY_JSCODE
from db import get_db
from models import Order, User
from security import current_user

router = APIRouter(prefix="/map", tags=["地图"])

# 城市中心点（GCJ-02 高德坐标系）：lng, lat
CITY_COORDS = {
    "杭州": (120.155070, 30.274085),
    "上海": (121.473701, 31.230416),
    "南京": (118.796877, 32.060255),
}

STATUS_PROGRESS = {"pending": 0.0, "picked": 0.12, "exception": 0.65, "delivered": 1.0}


@router.get("/config")
def map_config(_: User = Depends(current_user)):
    """返回前端高德 JS API 凭证（在 .env 中配置 AMAP_KEY / AMAP_SECURITY_JSCODE）。"""
    return {"key": AMAP_KEY, "security_jscode": AMAP_SECURITY_JSCODE}


def _city_of(address: str):
    for city in CITY_COORDS:
        if city in address:
            return city
    return None


@router.get("/order/{oid}/location")
def order_location(oid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """模拟实时货物定位：按城市坐标 + 运单状态/时间插值出当前位置与轨迹。"""
    order = db.get(Order, oid)
    if not order:
        raise HTTPException(404, "运单不存在")

    city_from = _city_of(order.sender_address or "")
    city_to = _city_of(order.receiver_address or "")
    if not city_from or not city_to or city_from == city_to:
        return {"supported": False, "message": "该运单地址暂不支持地图定位"}

    lng1, lat1 = CITY_COORDS[city_from]
    lng2, lat2 = CITY_COORDS[city_to]

    # 进度：固定状态映射 + 运输中按创建时间推进
    progress = STATUS_PROGRESS.get(order.status)
    if progress is None:  # transit
        hours = max(0.0, (datetime.now() - order.created_at).total_seconds() / 3600)
        progress = min(0.85, 0.25 + hours * 0.02)

    cur_lng = lng1 + (lng2 - lng1) * progress
    cur_lat = lat1 + (lat2 - lat1) * progress

    # 已走过路径的插值点
    n = 16
    path = [
        {"lng": round(lng1 + (cur_lng - lng1) * i / n, 6), "lat": round(lat1 + (cur_lat - lat1) * i / n, 6)}
        for i in range(n + 1)
    ]
    return {
        "supported": True,
        "from_city": city_from,
        "to_city": city_to,
        "origin": {"lng": lng1, "lat": lat1},
        "dest": {"lng": lng2, "lat": lat2},
        "current": {"lng": round(cur_lng, 6), "lat": round(cur_lat, 6)},
        "progress": round(progress, 3),
        "status": order.status,
        "path": path,
    }
