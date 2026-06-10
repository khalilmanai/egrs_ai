import os
import json
import logging
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sqlalchemy.ext.asyncio import AsyncSession
from core.consumption import (
    get_monthly_consumption_from_invoices,
    get_alert_aggregates_by_site,
)
from ml.features import engineer_features
from ml.config import (
    XGBOOST_PARAMS, FEATURE_COLS,
    LOG_TRANSFORM_TARGET, VALIDATION_YEARS,
    TRAINING_UP_TO_YEAR, SANITY_BOUNDS,
    CONFIDENCE_STD_MULTIPLIER,
)

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "consumption_xgboost.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "training_metrics.json")


async def _prepare_training_data(session: AsyncSession) -> pd.DataFrame:
    raw_data = await get_monthly_consumption_from_invoices(session)
    df = pd.DataFrame(raw_data)
    if df.empty:
        raise ValueError("No training data available")

    numeric_cols = (
        "total_consumption_kwh", "estimated_consumption", "final_sale",
        "tax_amount", "kwh_price_bt", "kwh_price_mt", "tax_rate"
    )
    for col in df.columns:
        if col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    alert_agg = await get_alert_aggregates_by_site(session)
    df["active_alert_count"] = df["site_id"].map(
        lambda sid: alert_agg.get(sid, {}).get("active_alert_count", 0)
    )
    df["has_sfr_alert"] = df["site_id"].map(
        lambda sid: alert_agg.get(sid, {}).get("has_sfr_alert", False)
    ).astype(int)
    df["critical_alert_count"] = df["site_id"].map(
        lambda sid: alert_agg.get(sid, {}).get("critical_alert_count", 0)
    )

    df = engineer_features(df, target_col="total_consumption_kwh")

    target = df["total_consumption_kwh"].fillna(0)
    if LOG_TRANSFORM_TARGET:
        target = np.log1p(target.clip(lower=0))

    df["target"] = target
    df = df.dropna(subset=["target", "lag_1", "lag_12"]).copy()

    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    return df


async def train_model(session: AsyncSession):
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = await _prepare_training_data(session)

    available_features = [c for c in FEATURE_COLS if c in df.columns]
    logger.info("Training with %d features: %s", len(available_features), available_features)

    train_mask = df["year"] <= TRAINING_UP_TO_YEAR
    val_mask = df["year"].isin(VALIDATION_YEARS)

    X_train = df.loc[train_mask, available_features].values
    y_train = df.loc[train_mask, "target"].values
    X_val = df.loc[val_mask, available_features].values
    y_val = df.loc[val_mask, "target"].values

    logger.info("Train rows: %d (years <= %d), Val rows: %d (years %s)",
                len(X_train), TRAINING_UP_TO_YEAR, len(X_val), VALIDATION_YEARS)

    model = xgb.XGBRegressor(**XGBOOST_PARAMS)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    y_pred_log = model.predict(X_val)
    y_val_orig = np.expm1(y_val)
    y_pred_orig = np.expm1(y_pred_log)

    rmse = float(np.sqrt(np.mean((y_val_orig - y_pred_orig) ** 2)))
    mae = float(np.mean(np.abs(y_val_orig - y_pred_orig)))
    r2 = float(1 - np.sum((y_val_orig - y_pred_orig) ** 2) / np.sum((y_val_orig - np.mean(y_val_orig)) ** 2))
    logger.info("Validation — RMSE: %.2f, MAE: %.2f, R²: %.4f", rmse, mae, r2)

    importance = model.feature_importances_
    feat_imp = sorted(
        zip(available_features, importance),
        key=lambda x: x[1], reverse=True,
    )
    logger.info("Top-5 features: %s", feat_imp[:5])

    val_df = df.loc[val_mask].copy()
    val_df["pred_log"] = y_pred_log
    val_df["pred_kwh"] = y_pred_orig
    val_df["residual"] = val_df["target"] - val_df["pred_log"]
    val_df["residual_kwh"] = val_df["total_consumption_kwh"] - val_df["pred_kwh"]

    site_calibration = (
        val_df.groupby("site_id")["residual"]
        .agg(["mean", "std"])
        .rename(columns={"mean": "bias", "std": "std"})
        .fillna(0)
    )
    global_std = float(val_df["residual"].std())
    global_bias = float(val_df["residual"].mean())
    median_std = float(val_df.groupby("site_id")["residual"].std().median())

    calibration = {
        "site_bias": site_calibration["bias"].to_dict(),
        "site_std": site_calibration["std"].to_dict(),
        "global_std": global_std,
        "global_bias": global_bias,
        "median_site_std": median_std,
        "log_transform": LOG_TRANSFORM_TARGET,
    }

    metrics = {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "feature_importance": {
            name: round(float(imp), 4) for name, imp in feat_imp
        },
        "features_used": available_features,
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "validation_years": VALIDATION_YEARS,
        "training_up_to_year": TRAINING_UP_TO_YEAR,
        "log_transform": LOG_TRANSFORM_TARGET,
        "calibration_global_std": round(global_std, 4),
        "calibration_global_bias": round(global_bias, 4),
        "calibration_median_site_std": round(median_std, 4),
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    joblib.dump({
        "model": model,
        "features": available_features,
        "calibration": calibration,
        "log_transform": LOG_TRANSFORM_TARGET,
    }, MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)
    return model, metrics


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run training first."
        )
    data = joblib.load(MODEL_PATH)
    return data


def predict_consumption(
    model: xgb.XGBRegressor,
    features: list[str],
    input_df: pd.DataFrame,
) -> np.ndarray:
    missing = [c for c in features if c not in input_df.columns]
    if missing:
        for col in missing:
            input_df[col] = 0.0
        logger.warning("Missing features set to 0: %s", missing)
    X = input_df[features].values
    return model.predict(X)


def predict_with_calibration(
    model: xgb.XGBRegressor,
    features: list[str],
    input_df: pd.DataFrame,
    calibration: dict,
    site_id: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pred_log = predict_consumption(model, features, input_df)
    pred_log = pred_log.clip(min=0, max=20)  # cap at ~485M kWh to prevent inf in expm1
    pred_kwh = np.expm1(pred_log)

    if site_id is not None:
        site_bias = calibration.get("site_bias", {}).get(site_id, calibration.get("global_bias", 0))
        site_std = calibration.get("site_std", {}).get(site_id, calibration.get("median_site_std", calibration.get("global_std", 0)))
    else:
        site_bias = calibration.get("global_bias", 0)
        site_std = calibration.get("median_site_std", calibration.get("global_std", 0))

    site_std = max(site_std, 0.01)
    multiplier = CONFIDENCE_STD_MULTIPLIER

    pred_log_corrected = pred_log - site_bias
    pred_kwh = np.expm1(np.clip(pred_log_corrected, 0, 20))

    ci_lower = np.expm1(np.clip(pred_log_corrected - multiplier * site_std, 0, 20))
    ci_upper = np.expm1(np.clip(pred_log_corrected + multiplier * site_std, 0, 20))

    return pred_kwh, ci_lower, ci_upper


def apply_sanity_bounds(
    predictions: np.ndarray,
    site_mean: float | None = None,
    site_mean_24m: float | None = None,
) -> np.ndarray:
    reference = site_mean_24m or site_mean
    if reference is None or reference <= 0:
        return predictions
    max_val = reference * SANITY_BOUNDS["max_multiplier_vs_mean"]
    min_val = reference * SANITY_BOUNDS["min_multiplier_vs_mean"]
    return np.clip(predictions, min_val, max_val)
