from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Branch, Driver, User, Vehicle
from schemas import BranchIn, BranchOut, DriverIn, DriverOut, VehicleIn, VehicleOut
from security import current_user, require_admin

router = APIRouter(tags=["基础资料"])


# ---------- 网点 ----------
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
