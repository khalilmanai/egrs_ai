import os
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sqlalchemy.ext.asyncio import AsyncSession
from data.extractors.consumption import get_monthly_consumption_from_invoices
from ml.features import engineer_features
from ml.config import XGBOOST_PARAMS, FEATURE_COLS

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "consumption_xgboost.pkl")


async def train_model(session: AsyncSession):
    os.makedirs(MODEL_DIR, exist_ok=True)
    raw_data = await get_monthly_consumption_from_invoices(session)
    df = pd.DataFrame(raw_data)
    if df.empty:
        raise ValueError("No training data available")

    df = engineer_features(df, target_col="total_consumption_kwh")
    df["target"] = df["total_consumption_kwh"].fillna(0)
    df = df.dropna(subset=["target", "lag_1", "lag_12"])

    available_features = [c for c in FEATURE_COLS if c in df.columns]
    df = df.sort_values("year")

    split_idx = int(len(df) * 0.8)
    X = df[available_features].values
    y = df["target"].values
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    model = xgb.XGBRegressor(**XGBOOST_PARAMS)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    joblib.dump({"model": model, "features": available_features}, MODEL_PATH)
    return model


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run training first."
        )
    data = joblib.load(MODEL_PATH)
    return data["model"], data["features"]


def predict_consumption(
    model: xgb.XGBRegressor,
    features: list[str],
    input_df: pd.DataFrame,
) -> np.ndarray:
    X = input_df[features].values
    return model.predict(X)
