import os
from pathlib import Path
from dotenv import load_dotenv

# 始终读取后端目录的配置，不依赖启动时所在目录。
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'huanuo.db'}")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
AGREEMENT_VERSION = "2026-11-03-v0.2"
