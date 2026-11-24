import os
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# 测试使用独立数据库，不读取开发账号和案件。
test_directory = tempfile.TemporaryDirectory(prefix="huanuo-tests-")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (Path(test_directory.name)/"test.db").as_posix()
from fastapi.testclient import TestClient
from main import app
from config.db_config import async_engine
from models.data_model import Base

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        async def reset():
            async with async_engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
                await connection.run_sync(Base.metadata.create_all)
        test_client.portal.call(reset)
        yield test_client
