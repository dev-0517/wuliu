from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.db_config import async_engine
from config.migrations import initialize_database
from config import settings
from models.data_model import Base
from routers import auth, cases, chat

@asynccontextmanager
async def lifespan(app):
    await initialize_database(async_engine, Base.metadata)
    yield
    await async_engine.dispose()

app = FastAPI(title="华诺 AI 助手", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=False,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(chat.router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "ai_configured": bool(settings.DEEPSEEK_API_KEY), "model": settings.DEEPSEEK_MODEL}
