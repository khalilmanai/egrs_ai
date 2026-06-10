import asyncio

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.dependencies import get_db
from config.settings import get_settings
from llm.client import health_check as ollama_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    ollama_ok = await ollama_health()

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "ollama": "available" if ollama_ok else "unavailable",
    }


@router.post("/shutdown")
async def shutdown(x_api_key: str | None = Header(default=None)):
    """Shut down the server gracefully after the response is sent.
    
    Protected by the internal API key to prevent unauthorized shutdowns.
    """
    settings = get_settings()
    if x_api_key != settings.ai_internal_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    loop = asyncio.get_running_loop()
    loop.call_later(1.0, loop.stop)
    return {"status": "shutting_down"}

