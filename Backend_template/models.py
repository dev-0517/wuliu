from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="operator")  # admin / operator
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # —— 用户端 APP 资料与绑定（2026-11 新增，靠 migrate_columns 自动补列）——
    display_name: Mapped[str] = mapped_column(String(50), default="")      # 昵称
    avatar: Mapped[str] = mapped_column(Text, default="")                  # 头像 base64 dataURL
    bound_phone: Mapped[str] = mapped_column(String(20), default="")       # 绑定手机号
    bound_wechat: Mapped[str] = mapped_column(String(80), default="")      # 绑定微信昵称
    bound_qq: Mapped[str] = mapped_column(String(80), default="")          # 绑定 QQ 昵称


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(60), default="")
    capacity_kg: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle/transit/maintenance
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(30), default="")
    license_no: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="available")  # available/driving/rest
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sender_name: Mapped[str] = mapped_column(String(50))
    sender_phone: Mapped[str] = mapped_column(String(30), default="")
    sender_address: Mapped[str] = mapped_column(String(200), default="")
    receiver_name: Mapped[str] = mapped_column(String(50))
    receiver_phone: Mapped[str] = mapped_column(String(30), default="")
    receiver_address: Mapped[str] = mapped_column(String(200), default="")
    origin_branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    dest_branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    goods: Mapped[str] = mapped_column(String(120), default="")
    weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="Track.id"
    )


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    location: Mapped[str] = mapped_column(String(100), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="tracks")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    emoji: Mapped[str] = mapped_column(String(10), default="📦")
    desc: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    color: Mapped[str] = mapped_column(String(20), default="#e0f2fe")  # 卡片底色
    stock: Mapped[int] = mapped_column(Integer, default=999)
    image: Mapped[str] = mapped_column(String(300), default="")        # 商品真实图片 URL


class Payment(Base):
    """商城支付记录：用户扫码付款后生成待审核记录，管理员批准后派发货物。"""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    method: Mapped[str] = mapped_column(String(20))             # wechat / alipay
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="paid")  # paid=已付款待审核 / approved / rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped[Order] = relationship()
    user: Mapped[User] = relationship()
