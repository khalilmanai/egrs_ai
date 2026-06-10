import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from ml.forecasting.xgboost_model import train_model as train_xgb, METRICS_PATH

logger = logging.getLogger(__name__)


async def run_training_pipeline(session: AsyncSession):
    results = {}
    try:
        model, metrics = await train_xgb(session)
        results["xgboost"] = "trained"
        results["metrics"] = metrics
        logger.info("XGBoost trained — RMSE: %.2f, MAE: %.2f, R²: %.4f",
                     metrics["rmse"], metrics["mae"], metrics["r2"])
    except Exception as e:
        results["xgboost"] = f"failed: {e}"
        logger.error("XGBoost training failed: %s", e)
    return results
