import numpy as np
import pandas as pd


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

    _engineer_static_features(df)
    _engineer_long_term_features(df)

    return df


def _engineer_static_features(df: pd.DataFrame):
    numeric_cols = [
        "estimated_consumption", "final_sale", "tax_amount",
        "kwh_price_bt", "kwh_price_mt", "tax_rate",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    if "configuration" in df.columns:
        df["config_terminal"] = (df["configuration"].str.lower() == "terminal").astype(float)
        df["config_nodal"] = (df["configuration"].str.lower() == "nodal").astype(float)
        df["config_agreg"] = (df["configuration"].str.lower() == "agreg").astype(float)

    if "network_type_id" in df.columns:
        df["network_type_4g"] = (df["network_type_id"] == 1).astype(float)
        df["network_type_5g"] = (df["network_type_id"] == 2).astype(float)

    if "estimated_consumption" in df.columns:
        df["estimated_consumption_kwh"] = pd.to_numeric(
            df["estimated_consumption"], errors="coerce"
        ).fillna(0).astype(float)

    for col in ["has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)

    for col in ["active_alert_count", "has_sfr_alert"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)


def _engineer_long_term_features(df: pd.DataFrame, target_col: str = "total_consumption_kwh", site_id_col: str = "site_id"):
    if target_col not in df.columns or site_id_col not in df.columns:
        return

    site_mean = df.groupby(site_id_col)[target_col].mean()
    site_std = df.groupby(site_id_col)[target_col].std().fillna(0)

    df["site_mean_24m"] = df[site_id_col].map(site_mean).fillna(1)
    df["site_std_24m"] = df[site_id_col].map(site_std).fillna(0)
    df["consumption_to_mean_ratio"] = df[target_col] / df["site_mean_24m"].replace(0, 1)

    if "item_date" in df.columns:
        date_col = "item_date"
    elif "year" in df.columns and "month" in df.columns:
        df["_tmp_date"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str) + "-01")
        date_col = "_tmp_date"
    else:
        df["site_trend_12m"] = 0.0
        df["data_quality_pct"] = 1.0
        return

    df = df.sort_values([site_id_col, date_col])

    def _compute_trend(grp):
        vals = grp.tail(12)[target_col].values
        if len(vals) < 3:
            return 0.0
        x = np.arange(len(vals))
        slope = np.polyfit(x, vals, 1)[0]
        mean_val = float(np.mean(vals)) or 1.0
        return slope / mean_val

    trend_map = df.groupby(site_id_col).apply(_compute_trend).to_dict()
    df["site_trend_12m"] = df[site_id_col].map(trend_map).fillna(0.0)

    def _compute_data_quality(grp):
        total = len(grp)
        non_null = grp[target_col].notna().sum()
        return non_null / total if total > 0 else 0.0

    dq_map = df.groupby(site_id_col).apply(_compute_data_quality).to_dict()
    df["data_quality_pct"] = df[site_id_col].map(dq_map).fillna(1.0)


def build_query_vector(site_input: dict) -> list[float]:
    estimated = site_input.get("estimated_consumption", 5000)
    seasonal_pattern = site_input.get("seasonal_pattern", None)
    if seasonal_pattern and len(seasonal_pattern) == 12:
        total = sum(seasonal_pattern)
        if total > 0:
            return [estimated * (v / total) for v in seasonal_pattern]
    monthly = estimated / 12
    return [monthly] * 12
