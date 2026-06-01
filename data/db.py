import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from config.settings import Settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_engine = None
_session_factory = None


async def init_db(settings: Settings):
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_min_size,
        max_overflow=settings.db_max_size - settings.db_min_size,
        echo=settings.debug,
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db():
    global _engine
    if _engine:
        await _engine.dispose()


async def get_session():
    async with _session_factory() as session:
        yield session


def get_session_sync() -> AsyncSession:
    return _session_factory()


create_session = get_session_sync  # alias for clarity
