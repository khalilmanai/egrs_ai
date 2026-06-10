from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_session
from config.settings import get_settings, Settings


async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session


def get_app_settings() -> Settings:
    return get_settings()
