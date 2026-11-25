import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import models  # noqa: F401  确保模型注册到 metadata
from config import CORS_ORIGINS
from db import Base, SessionLocal, engine
from routers import auth, orders, resources, stats
from seed import seed


def init_db(retries: int = 30, delay: int = 2) -> None:
    """容器启动时数据库可能还没就绪，重试建表。"""
    for attempt in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            with SessionLocal() as db:
                seed(db)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            print(f"[init] 数据库未就绪，{delay}s 后重试（{attempt + 1}/{retries}）：{exc}")
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="物流管理系统 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok, "service": "logistics"}
