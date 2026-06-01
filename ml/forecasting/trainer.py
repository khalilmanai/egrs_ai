from sqlalchemy.ext.asyncio import AsyncSession
from ml.forecasting.xgboost_model import train_model as train_xgb


async def run_training_pipeline(session: AsyncSession):
    """Run full training pipeline. Returns training results."""
    results = {}
    try:
        model = await train_xgb(session)
        results["xgboost"] = "trained"
    except Exception as e:
        results["xgboost"] = f"failed: {e}"
    return results
