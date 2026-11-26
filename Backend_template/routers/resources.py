from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Branch, Driver, Order, User, Vehicle
from schemas import BranchIn, BranchOut, DriverIn, DriverOut, VehicleIn, VehicleOut
from security import current_user, require_admin

router = APIRouter(tags=["基础资料"])


def _order_brief(o: Order) -> dict:
    return {
        "id": o.id,
        "order_no": o.order_no,
        "goods": o.goods,
        "weight_kg": float(o.weight_kg or 0),
        "status": o.status,
        "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "",
    }


# ---------- 网点 ----------
@router.get("/branches/{bid}/detail")
def branch_detail(bid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Branch, bid)
    if not obj:
        raise HTTPException(404, "网点不存在")
    vehicles = db.scalars(select(Vehicle).where(Vehicle.branch_id == bid).order_by(Vehicle.id)).all()
    drivers = db.scalars(select(Driver).where(Driver.branch_id == bid).order_by(Driver.id)).all()
    orders = db.scalars(
        select(Order)
        .where((Order.origin_branch_id == bid) | (Order.dest_branch_id == bid))
        .order_by(Order.id.desc()).limit(8)
    ).all()
    return {
        "branch": obj,
        "vehicles": [{"id": v.id, "plate": v.plate, "model": v.model, "status": v.status} for v in vehicles],
        "drivers": [{"id": d.id, "name": d.name, "phone": d.phone, "status": d.status} for d in drivers],
        "orders": [_order_brief(o) for o in orders],
    }

@router.get("/branches", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Branch).order_by(Branch.id)).all()


@router.post("/branches", response_model=BranchOut)
def create_branch(payload: BranchIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    if db.scalar(select(Branch).where(Branch.code == payload.code)):
        raise HTTPException(400, "网点编码已存在")
    obj = Branch(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/branches/{bid}", response_model=BranchOut)
def update_branch(bid: int, payload: BranchIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Branch, bid)
    if not obj:
        raise HTTPException(404, "网点不存在")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/branches/{bid}")
def delete_branch(bid: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    obj = db.get(Branch, bid)
    if not obj:
        raise HTTPException(404, "网点不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ---------- 车辆 ----------
@router.get("/vehicles/{vid}/detail")
def vehicle_detail(vid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Vehicle, vid)
    if not obj:
        raise HTTPException(404, "车辆不存在")
    branch = db.get(Branch, obj.branch_id) if obj.branch_id else None
    orders = db.scalars(
        select(Order).where(Order.vehicle_id == vid).order_by(Order.id.desc()).limit(8)
    ).all()
    return {
        "vehicle": obj,
        "branch_name": branch.name if branch else "",
        "orders": [_order_brief(o) for o in orders],
    }


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Vehicle).order_by(Vehicle.id)).all()


@router.post("/vehicles", response_model=VehicleOut)
def create_vehicle(payload: VehicleIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    if db.scalar(select(Vehicle).where(Vehicle.plate == payload.plate)):
        raise HTTPException(400, "车牌号已存在")
    obj = Vehicle(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/vehicles/{vid}", response_model=VehicleOut)
def update_vehicle(vid: int, payload: VehicleIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Vehicle, vid)
    if not obj:
        raise HTTPException(404, "车辆不存在")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/vehicles/{vid}")
def delete_vehicle(vid: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    obj = db.get(Vehicle, vid)
    if not obj:
        raise HTTPException(404, "车辆不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ---------- 司机 ----------
@router.get("/drivers/{did}/detail")
def driver_detail(did: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Driver, did)
    if not obj:
        raise HTTPException(404, "司机不存在")
    branch = db.get(Branch, obj.branch_id) if obj.branch_id else None
    orders = db.scalars(
        select(Order).where(Order.driver_id == did).order_by(Order.id.desc()).limit(8)
    ).all()
    return {
        "driver": obj,
        "branch_name": branch.name if branch else "",
        "orders": [_order_brief(o) for o in orders],
    }


@router.get("/drivers", response_model=list[DriverOut])
def list_drivers(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Driver).order_by(Driver.id)).all()


@router.post("/drivers", response_model=DriverOut)
def create_driver(payload: DriverIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = Driver(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/drivers/{did}", response_model=DriverOut)
def update_driver(did: int, payload: DriverIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    obj = db.get(Driver, did)
    if not obj:
        raise HTTPException(404, "司机不存在")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/drivers/{did}")
def delete_driver(did: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    obj = db.get(Driver, did)
    if not obj:
        raise HTTPException(404, "司机不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}
