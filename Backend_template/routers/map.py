from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import AMAP_KEY, AMAP_SECURITY_JSCODE
from db import get_db
from models import Order, User, Vehicle
from security import current_user

router = APIRouter(prefix="/map", tags=["地图"])

# 城市中心点（GCJ-02 高德坐标系）：lng, lat
CITY_COORDS = {
    "杭州": (120.155070, 30.274085),
    "上海": (121.473701, 31.230416),
    "南京": (118.796877, 32.060255),
}

STATUS_PROGRESS = {"pending": 0.0, "picked": 0.12, "exception": 0.65, "delivered": 1.0}

# 城市间公路里程（km，高速常见路径）与货车平均速度
CITY_DISTANCE_KM = {
    ("上海", "杭州"): 175,
    ("上海", "南京"): 300,
    ("杭州", "南京"): 280,
}
AVG_SPEED_KMH = 65


def _eta(city_from: str, city_to: str, progress: float):
    dist = CITY_DISTANCE_KM.get(tuple(sorted((city_from, city_to))), 200)
    remain_km = round(dist * (1 - min(progress, 1.0)), 1)
    minutes = int(remain_km / AVG_SPEED_KMH * 60)
    eta_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")
    return {"distance_km": dist, "remain_km": remain_km, "eta_minutes": minutes, "eta_time": eta_time}


@router.get("/config")
def map_config(_: User = Depends(current_user)):
    """返回前端高德 JS API 凭证（在 .env 中配置 AMAP_KEY / AMAP_SECURITY_JSCODE）。"""
    return {"key": AMAP_KEY, "security_jscode": AMAP_SECURITY_JSCODE}


def _city_of(address: str):
    for city in CITY_COORDS:
        if city in address:
            return city
    return None


def _locate(order: Order) -> dict:
    """按城市坐标 + 运单状态/时间插值出当前位置与轨迹。"""
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
    eta = _eta(city_from, city_to, progress)
    return {
        "supported": True,
        "from_city": city_from,
        "to_city": city_to,
        "origin": {"lng": lng1, "lat": lat1},
        "dest": {"lng": lng2, "lat": lat2},
        "current": {"lng": round(cur_lng, 6), "lat": round(cur_lat, 6)},
        "progress": round(progress, 3),
        "status": order.status,
        "arrived": progress >= 1.0,
        "path": path,
        **eta,
    }


@router.get("/order/{oid}/location")
def order_location(oid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """模拟实时货物定位。"""
    order = db.get(Order, oid)
    if not order:
        raise HTTPException(404, "运单不存在")
    return _locate(order)


@router.get("/vehicle/{vid}/tracking")
def vehicle_tracking(vid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """车辆实时追踪：返回车辆状态与当前承运运单的实时位置。"""
    vehicle = db.get(Vehicle, vid)
    if not vehicle:
        raise HTTPException(404, "车辆不存在")

    order = db.scalar(
        select(Order)
        .where(Order.vehicle_id == vid, Order.status == "transit")
        .order_by(Order.id.desc())
        .limit(1)
    )
    result = {
        "vehicle": {"id": vehicle.id, "plate": vehicle.plate, "model": vehicle.model, "status": vehicle.status},
        "order": None,
        "location": None,
    }
    if order:
        result["order"] = {
            "id": order.id,
            "order_no": order.order_no,
            "goods": order.goods,
            "weight_kg": float(order.weight_kg or 0),
            "sender": order.sender_name,
            "receiver": order.receiver_name,
        }
        result["location"] = _locate(order)
    return result


@router.get("/vehicles/etas")
def vehicles_etas(db: Session = Depends(get_db), _: User = Depends(current_user)):
    """所有运输中车辆的到达预测：车牌、线路、剩余里程、预计到达时间。"""
    out = []
    vehicles = db.scalars(select(Vehicle).where(Vehicle.status == "transit")).all()
    for v in vehicles:
        item = {"vehicle_id": v.id, "plate": v.plate, "model": v.model}
        order = db.scalar(
            select(Order)
            .where(Order.vehicle_id == v.id, Order.status == "transit")
            .order_by(Order.id.desc())
            .limit(1)
        )
        if order:
            loc = _locate(order)
            if loc.get("supported"):
                item.update({
                    "order_no": order.order_no,
                    "from_city": loc["from_city"],
                    "to_city": loc["to_city"],
                    "progress": loc["progress"],
                    "remain_km": loc["remain_km"],
                    "eta_minutes": loc["eta_minutes"],
                    "eta_time": loc["eta_time"],
                })
        out.append(item)
    return out
