LOG_TRANSFORM_TARGET = True
FORECAST_HORIZON = 12
VALIDATION_YEARS = [2025]
TRAINING_UP_TO_YEAR = 2024
MAX_YOY_GROWTH_PCT = 30
MIN_YOY_GROWTH_PCT = -30
CONFIDENCE_STD_MULTIPLIER = 1.0

XGBOOST_PARAMS = {
    "n_estimators": 500,
    "max_depth": 5,
    "learning_rate": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "early_stopping_rounds": 30,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
}

FEATURE_COLS = [
    # Temporal
    "month", "quarter", "month_sin", "month_cos",
    # Lags
    "lag_1", "lag_2", "lag_3", "lag_12",
    # Rolling windows
    "rolling_mean_3", "rolling_std_3", "rolling_max_6",
    # Electrical
    "is_bt", "yoy_change",
    # Site metadata
    "is_sharing_int",
    "config_terminal", "config_nodal", "config_agreg",
    "network_type_4g", "network_type_5g",
    "estimated_consumption_kwh",
    # Radio technology flags
    "has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g",
    # Alert-derived
    "active_alert_count", "has_sfr_alert",
    # Long-term site features
    "site_mean_24m", "site_std_24m", "site_trend_12m",
    "consumption_to_mean_ratio", "data_quality_pct",
]

SANITY_BOUNDS = {
    "max_multiplier_vs_mean": 2.0,
    "min_multiplier_vs_mean": 0.3,
}
