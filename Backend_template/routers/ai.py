import json
import os
import urllib.request

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import BASE_DIR
from db import get_db
from models import Branch, Driver, Order, User, Vehicle
from security import current_user

router = APIRouter(prefix="/ai", tags=["AI 助手"])

BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
API_KEY = os.getenv("DASHSCOPE_API_KEY", "")


class AskIn(BaseModel):
    question: str
    history: list[dict] = []  # [{role, content}] 最多带最近几轮


def _overview(db: Session) -> str:
    """把当前运营数据摘要塞给 AI，让它能回答与系统数据相关的问题。"""
    by_status = dict(db.execute(select(Order.status, func.count()).group_by(Order.status)).all())
    total = sum(by_status.values())
    weight = db.scalar(select(func.coalesce(func.sum(Order.weight_kg), 0.0))) or 0
    vehicles = dict(db.execute(select(Vehicle.status, func.count()).group_by(Vehicle.status)).all())
    drivers = dict(db.execute(select(Driver.status, func.count()).group_by(Driver.status)).all())
    branches = [name for (name,) in db.execute(select(Branch.name)).all()]
    return json.dumps({
        "总运单": total, "各状态运单": by_status, "运输总量kg": round(float(weight), 1),
        "网点": branches,
        "车辆状态分布": vehicles,
        "司机状态分布": drivers,
    }, ensure_ascii=False)


@router.post("/ask")
def ask(body: AskIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    if not API_KEY:
        return {"answer": "未配置 AI 服务（缺少 DASHSCOPE_API_KEY），请在 Backend_template/.env 中填写。"}

    system = (
        "你是物流管理系统「智慧物流全球通」的 AI 运营助手。"
        "用简体中文回答，语气专业友好，回答简洁。"
        "涉及数据时优先使用下面提供的系统实时数据；数据里没有的就基于物流行业常识回答。"
        "排版要求：用 Markdown，可用 ### 小标题、**加粗**、- 列表和 | 表格 | 让回答清晰易读，"
        "不要输出代码块。\n\n系统实时数据：" + _overview(db)
    )
    messages = [{"role": "system", "content": system}]
    for m in body.history[-6:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": str(m["content"])[:2000]})
    messages.append({"role": "user", "content": body.question[:2000]})

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1200,
    }).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=payload, method="POST",
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        answer = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        answer = f"AI 服务暂时不可用，请稍后再试。（{exc}）"
    return {"answer": answer}
