import numpy as np
import pandas as pd


def build_query_vector_from_input(site_input: dict) -> list[float]:
    estimated = site_input.get("estimated_consumption", 5000)
    seasonal_pattern = site_input.get("seasonal_pattern", None)
    if seasonal_pattern and len(seasonal_pattern) == 12:
        total = sum(seasonal_pattern)
        if total > 0:
            return [estimated * (v / total) for v in seasonal_pattern]
    monthly = estimated / 12
    return [monthly] * 12


def engineer_features(
    df: pd.DataFrame,
    site_id_col: str = "site_id",
    target_col: str = "total_consumption_kwh",
    date_col: str = "item_date",
) -> pd.DataFrame:
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values([site_id_col, date_col])

    df["year"] = df[date_col].dt.year
    df["month"] = df[date_col].dt.month
    df["quarter"] = df[date_col].dt.quarter
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    df = df.sort_values([site_id_col, date_col])
    df["lag_1"] = df.groupby(site_id_col)[target_col].shift(1)
    df["lag_2"] = df.groupby(site_id_col)[target_col].shift(2)
    df["lag_3"] = df.groupby(site_id_col)[target_col].shift(3)
    df["lag_12"] = df.groupby(site_id_col)[target_col].shift(12)

    df["rolling_mean_3"] = (
        df.groupby(site_id_col)[target_col]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    df["rolling_std_3"] = (
        df.groupby(site_id_col)[target_col]
        .transform(lambda x: x.rolling(3, min_periods=1).std())
    )
    df["rolling_max_6"] = (
        df.groupby(site_id_col)[target_col]
        .transform(lambda x: x.rolling(6, min_periods=1).max())
    )

    if "elec_type" in df.columns:
        df["is_bt"] = (df["elec_type"] == "BT").astype(int)
    if "is_sharing" in df.columns:
        df["is_sharing_int"] = df["is_sharing"].astype(int)
    if "lag_12" in df.columns:
        df["yoy_change"] = (
            (df[target_col] - df["lag_12"]) / df["lag_12"].replace(0, np.nan)
        )

    return df
