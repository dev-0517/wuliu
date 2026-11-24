from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event
from config.settings import DATABASE_URL

async_engine = create_async_engine(DATABASE_URL, echo=False)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(async_engine.sync_engine, "connect")
    def configure_sqlite(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")

AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_database_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
