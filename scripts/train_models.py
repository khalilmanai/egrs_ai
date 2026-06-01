"""
Train XGBoost model from historical consumption data.
Run: python -m scripts.train_models
"""
import asyncio
from data.db import init_db, close_db, get_session_sync
from ml.forecasting.trainer import run_training_pipeline
from config.settings import get_settings


async def main():
    settings = get_settings()
    await init_db(settings)
    session = get_session_sync()
    try:
        results = await run_training_pipeline(session)
        print("Training results:", results)
    finally:
        await session.close()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
