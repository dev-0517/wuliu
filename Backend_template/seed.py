from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Branch, Driver, Order, Track, User, Vehicle
from security import hash_password


def seed(db: Session) -> None:
    """首次启动写入演示数据，已有数据则跳过。"""
    if db.scalar(select(User).limit(1)) is None:
        db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
        db.add(User(username="operator", password_hash=hash_password("operator123"), role="operator"))

    if db.scalar(select(Branch).limit(1)) is None:
        db.add_all(
            [
                Branch(code="HZ01", name="杭州转运中心", city="杭州", address="浙江省杭州市萧山区物流大道 1 号", phone="0571-88880001"),
                Branch(code="SH01", name="上海分拨中心", city="上海", address="上海市青浦区华新镇物流园 8 号", phone="021-66660002"),
                Branch(code="NJ01", name="南京网点", city="南京", address="江苏省南京市江宁区秣陵街道 66 号", phone="025-55550003"),
            ]
        )

    if db.scalar(select(Vehicle).limit(1)) is None:
        db.add_all(
            [
                Vehicle(plate="浙A·D1234", model="厢式货车 9.6 米", capacity_kg=12000, status="idle", branch_id=1),
                Vehicle(plate="沪B·F5678", model="冷藏车 6.8 米", capacity_kg=6000, status="transit", branch_id=2),
                Vehicle(plate="苏A·G9012", model="依维柯 4.2 米", capacity_kg=2000, status="idle", branch_id=3),
            ]
        )

    if db.scalar(select(Driver).limit(1)) is None:
        db.add_all(
            [
                Driver(name="张伟", phone="13800001111", license_no="A2-330100199001011234", status="available", branch_id=1),
                Driver(name="李强", phone="13800002222", license_no="B2-310100199203054567", status="driving", branch_id=2),
                Driver(name="王芳", phone="13800003333", license_no="A2-320100198807128901", status="available", branch_id=3),
            ]
        )

    if db.scalar(select(Order).limit(1)) is None:
        o1 = Order(
            order_no="WY202611250001",
            sender_name="陈明",
            sender_phone="13900001234",
            sender_address="杭州市西湖区文三路 100 号",
            receiver_name="赵静",
            receiver_phone="13900005678",
            receiver_address="上海市浦东新区世纪大道 200 号",
            origin_branch_id=1,
            dest_branch_id=2,
            driver_id=2,
            vehicle_id=2,
            goods="电子配件 3 箱",
            weight_kg=46.5,
            status="transit",
            remark="易碎品，轻拿轻放",
        )
        o2 = Order(
            order_no="WY202611250002",
            sender_name="刘洋",
            sender_phone="13700001111",
            sender_address="南京市鼓楼区中山路 88 号",
            receiver_name="孙丽",
            receiver_phone="13700002222",
            receiver_address="杭州市余杭区文一西路 969 号",
            origin_branch_id=3,
            dest_branch_id=1,
            goods="服装 8 箱",
            weight_kg=120,
            status="pending",
        )
        o3 = Order(
            order_no="WY202611240003",
            sender_name="周涛",
            sender_phone="13600003333",
            sender_address="上海市静安区南京西路 500 号",
            receiver_name="吴敏",
            receiver_phone="13600004444",
            receiver_address="南京市秦淮区中山南路 300 号",
            origin_branch_id=2,
            dest_branch_id=3,
            goods="文件资料 1 件",
            weight_kg=2.4,
            status="delivered",
        )
        db.add_all([o1, o2, o3])
        db.flush()
        db.add_all(
            [
                Track(order_id=o1.id, status="pending", location="杭州转运中心", note="已下单，等待揽收"),
                Track(order_id=o1.id, status="picked", location="杭州转运中心", note="已揽收，装车发出"),
                Track(order_id=o1.id, status="transit", location="沪杭高速嘉兴段", note="运输中"),
                Track(order_id=o2.id, status="pending", location="南京网点", note="已下单，等待揽收"),
                Track(order_id=o3.id, status="delivered", location="南京网点", note="已签收，签收人：吴敏"),
            ]
        )

    db.commit()
