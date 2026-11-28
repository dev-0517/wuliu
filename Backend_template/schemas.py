from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=64)


class UserOut(ORMModel):
    id: int
    username: str
    role: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


class PhoneSendIn(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$", description="11 位手机号")


class PhoneLoginIn(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str = Field(min_length=6, max_length=6)


class QrCreateOut(BaseModel):
    uuid: str
    expire_in: int


class QrPollOut(BaseModel):
    status: str  # waiting / confirmed / expired
    token: str | None = None
    user: dict | None = None


class BranchIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str
    city: str
    address: str = ""
    phone: str = ""


class BranchOut(ORMModel):
    id: int
    code: str
    name: str
    city: str
    address: str
    phone: str


class VehicleIn(BaseModel):
    plate: str
    model: str = ""
    capacity_kg: int = 0
    status: str = "idle"
    branch_id: int | None = None


class VehicleOut(ORMModel):
    id: int
    plate: str
    model: str
    capacity_kg: int
    status: str
    branch_id: int | None


class DriverIn(BaseModel):
    name: str
    phone: str = ""
    license_no: str = ""
    status: str = "available"
    branch_id: int | None = None


class DriverOut(ORMModel):
    id: int
    name: str
    phone: str
    license_no: str
    status: str
    branch_id: int | None


class OrderIn(BaseModel):
    sender_name: str
    sender_phone: str = ""
    sender_address: str = ""
    receiver_name: str
    receiver_phone: str = ""
    receiver_address: str = ""
    origin_branch_id: int | None = None
    dest_branch_id: int | None = None
    driver_id: int | None = None
    vehicle_id: int | None = None
    goods: str = ""
    weight_kg: float = 0
    remark: str = ""


class OrderOut(ORMModel):
    id: int
    order_no: str
    sender_name: str
    sender_phone: str
    sender_address: str
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    origin_branch_id: int | None
    dest_branch_id: int | None
    driver_id: int | None
    vehicle_id: int | None
    goods: str
    weight_kg: float
    status: str
    remark: str
    created_at: datetime
    updated_at: datetime


class TrackOut(ORMModel):
    id: int
    status: str
    location: str
    note: str
    created_at: datetime


class OrderDetail(OrderOut):
    tracks: list[TrackOut] = []


class StatusIn(BaseModel):
    status: str
    location: str = ""
    note: str = ""


class Page(BaseModel):
    total: int
    items: list[OrderOut]
