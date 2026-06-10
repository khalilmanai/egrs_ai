import sys

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
from core.db import init_db, close_db
from api.routers import health, reports_v2, ingestion_v2, training

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(settings)
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix, tags=["Health"])
    app.include_router(reports_v2.router, prefix=prefix, tags=["Reports PDF"])
    app.include_router(ingestion_v2.router, prefix=prefix, tags=["Ingestion"])
    app.include_router(training.router, prefix=prefix, tags=["Training"])
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("api.main:app", host="0.0.0.0", port=8300, reload=False)
