import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Branch, Driver, Order, Track, User, Vehicle
from security import hash_password

SENDERS = ["陈明", "刘洋", "周涛", "郑凯", "冯雪", "许亮", "何静", "吕强", "施雨", "张帆"]
RECEIVERS = ["赵静", "孙丽", "吴敏", "林杰", "徐娜", "高翔", "罗丹", "梁波", "宋佳", "唐磊"]
GOODS = [
    ("电子配件", 8, 60), ("服装", 50, 200), ("食品生鲜", 20, 150),
    ("家具建材", 200, 900), ("图书", 15, 80), ("日用百货", 30, 260),
]
STATIONS = ["杭州转运中心", "上海分拨中心", "南京网点", "沪杭高速嘉兴段", "G60 江浙界", "宁杭高速溧阳段"]
CITIES = [("杭州市西湖区文三路", "上海市浦东新区世纪大道"), ("南京市鼓楼区中山路", "杭州市余杭区文一西路"),
          ("上海市静安区南京西路", "南京市秦淮区中山南路"), ("杭州市滨江区江南大道", "上海市闵行区莘庄镇")]


def generate_orders(db: Session, branches, vehicles, drivers, count: int = 72) -> None:
    """生成近 30 天的演示运单，回填 created_at 让大屏趋势/日历有数据。"""
    from sqlalchemy import func

    rng = random.Random(2026)
    now = datetime.now()
    seq = db.scalar(select(func.count()).select_from(Order)) or 0
    status_pool = (
        ["delivered"] * 34 + ["transit"] * 12 + ["picked"] * 8 + ["pending"] * 10 + ["exception"] * 4
    )
    for i in range(count):
        days_ago = rng.randint(0, 29)
        created = now - timedelta(
            days=days_ago,
            hours=rng.randint(0, 11),
            minutes=rng.randint(0, 59),
        )
        if days_ago == 0 and created > now:
            created = now
        b_org, b_dst = rng.sample(branches, 2)
        goods, w_min, w_max = rng.choice(GOODS)
        drv = rng.choice(drivers) if rng.random() < 0.8 else None
        veh = rng.choice(vehicles) if drv and rng.random() < 0.85 else None
        status = status_pool[i % len(status_pool)]
        if days_ago > 3 and status in ("pending",):
            status = "delivered"
        city_pair = rng.choice(CITIES)
        seq += 1
        order = Order(
            order_no=f"WY{created.strftime('%Y%m%d')}{seq:04d}",
            sender_name=rng.choice(SENDERS),
            sender_phone=f"139{rng.randint(10000000, 99999999)}",
            sender_address=f"{city_pair[0]}{rng.randint(1, 299)} 号",
            receiver_name=rng.choice(RECEIVERS),
            receiver_phone=f"137{rng.randint(10000000, 99999999)}",
            receiver_address=f"{city_pair[1]}{rng.randint(1, 299)} 号",
            origin_branch_id=b_org.id,
            dest_branch_id=b_dst.id,
            driver_id=drv.id if drv else None,
            vehicle_id=veh.id if veh else None,
            goods=f"{goods} {rng.randint(1, 12)} 箱",
            weight_kg=round(rng.uniform(w_min, w_max), 1),
            status=status,
            created_at=created,
            updated_at=created,
        )
        db.add(order)
        db.flush()
        flow = ["pending", "picked", "transit", "delivered"]
        steps = flow[: flow.index(status) + 1] if status in flow else ["pending", "exception"]
        for j, st in enumerate(steps):
            db.add(
                Track(
                    order_id=order.id,
                    status=st,
                    location=rng.choice(STATIONS),
                    note={"pending": "已下单，等待揽收", "picked": "已揽收，装车发出",
                          "transit": "干线运输中", "delivered": "已签收", "exception": "异常：地址待确认"}[st],
                    created_at=created + timedelta(hours=j * rng.randint(2, 8)),
                )
            )


def seed(db: Session) -> None:
    """首次启动写入演示数据：先 flush 拿到真实主键，再建立外键关联。"""
    if db.scalar(select(User).limit(1)) is None:
        db.add_all(
            [
                User(username="admin", password_hash=hash_password("admin123"), role="admin"),
                User(username="operator", password_hash=hash_password("operator123"), role="operator"),
            ]
        )
        db.flush()

    # 已有网点说明演示数据已初始化过，直接结束
    if db.scalar(select(Branch).limit(1)) is not None:
        db.commit()
        return

    b1 = Branch(code="HZ01", name="杭州转运中心", city="杭州", address="浙江省杭州市萧山区物流大道 1 号", phone="0571-88880001")
    b2 = Branch(code="SH01", name="上海分拨中心", city="上海", address="上海市青浦区华新镇物流园 8 号", phone="021-66660002")
    b3 = Branch(code="NJ01", name="南京网点", city="南京", address="江苏省南京市江宁区秣陵街道 66 号", phone="025-55550003")
    db.add_all([b1, b2, b3])
    db.flush()

    v1 = Vehicle(plate="浙A·D1234", model="厢式货车 9.6 米", capacity_kg=12000, status="transit", branch_id=b1.id)
    v2 = Vehicle(plate="沪B·F5678", model="冷藏车 6.8 米", capacity_kg=6000, status="transit", branch_id=b2.id)
    v3 = Vehicle(plate="苏A·G9012", model="依维柯 4.2 米", capacity_kg=2000, status="idle", branch_id=b3.id)
    v4 = Vehicle(plate="浙A·H2468", model="厢式货车 7.7 米", capacity_kg=8000, status="maintenance", branch_id=b1.id)
    db.add_all([v1, v2, v3, v4])
    db.flush()

    d1 = Driver(name="张伟", phone="13800001111", license_no="A2-330100199001011234", status="driving", branch_id=b1.id)
    d2 = Driver(name="李强", phone="13800002222", license_no="B2-310100199203054567", status="driving", branch_id=b2.id)
    d3 = Driver(name="王芳", phone="13800003333", license_no="A2-320100198807128901", status="available", branch_id=b3.id)
    d4 = Driver(name="赵磊", phone="13800004444", license_no="B2-330100199505056789", status="rest", branch_id=b1.id)
    db.add_all([d1, d2, d3, d4])
    db.flush()

    generate_orders(db, [b1, b2, b3], [v1, v2, v3, v4], [d1, d2, d3, d4])
    db.commit()


EXTRA_VEHICLES = [
    ("苏B·K3344", "冷藏车 9.6 米", 15000, "idle", "SH01"),
    ("浙A·J7788", "厢式货车 12.5 米", 25000, "transit", "HZ01"),
    ("沪C·M9900", "厢式货车 4.2 米", 1500, "idle", "SH01"),
    ("浙A·L5566", "依维柯 4.2 米", 2000, "idle", "HZ01"),
]
EXTRA_DRIVERS = [
    ("陈刚", "13800005555", "B2-320100199202022222", "available", "SH01"),
    ("刘军", "13800006666", "A2-330100199303033333", "driving", "NJ01"),
]


def ensure_extra_fleet(db: Session) -> None:
    """补足演示车队与司机（幂等：按车牌/姓名去重，老库重启也能自动补上）。"""
    codes = db.execute(select(Branch.code, Branch.id)).all()
    by_code = {code: bid for code, bid in codes}

    plates = {plate for (plate,) in db.execute(select(Vehicle.plate)).all()}
    for plate, model, cap, status, code in EXTRA_VEHICLES:
        if plate not in plates:
            db.add(Vehicle(plate=plate, model=model, capacity_kg=cap, status=status, branch_id=by_code.get(code)))

    names = {name for (name,) in db.execute(select(Driver.name)).all()}
    for name, phone, lic, status, code in EXTRA_DRIVERS:
        if name not in names:
            db.add(Driver(name=name, phone=phone, license_no=lic, status=status, branch_id=by_code.get(code)))

    db.commit()
