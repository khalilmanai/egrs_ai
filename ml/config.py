XGBOOST_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "early_stopping_rounds": 20,
}

PROPHET_PARAMS = {
    "yearly_seasonality": True,
    "weekly_seasonality": False,
    "daily_seasonality": False,
    "seasonality_mode": "multiplicative",
    "changepoint_prior_scale": 0.05,
}

FEATURE_COLS = [
    "month", "quarter", "month_sin", "month_cos",
    "lag_1", "lag_2", "lag_3", "lag_12",
    "rolling_mean_3", "rolling_std_3", "rolling_max_6",
    "is_bt", "yoy_change",
]
