import logging
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from core.consumption import get_monthly_consumption_from_invoices, get_alert_aggregates_by_site
from core.sql_filter import SEASONAL_PROFILE, SEASONAL_FLATNESS_THRESHOLD, site_filter, site_filter_no_alias
from analytics.features import engineer_features
from analytics.budget import compute_monthly_budget
from ml.forecasting.xgboost_model import load_model, predict_with_calibration, apply_sanity_bounds
from ml.config import SANITY_BOUNDS
from estimators.tech_consumption import estimate_from_tech_flags

logger = logging.getLogger(__name__)


def _apply_seasonal_shape(predictions: list[float]) -> list[float]:
    arr = np.array(predictions, dtype=float)
    mean_val = arr.mean()
    if mean_val == 0:
        return predictions
    cv = arr.std() / mean_val
    if cv >= SEASONAL_FLATNESS_THRESHOLD:
        return predictions
    profile = np.array([SEASONAL_PROFILE[m] for m in range(1, 13)])
    profile = profile / profile.mean()
    shaped = arr * profile
    shaped = shaped * (arr.sum() / shaped.sum())
    return shaped.tolist()


def _get_static_features(site_hist: pd.DataFrame) -> dict:
    last = site_hist.iloc[-1] if not site_hist.empty else pd.Series()
    static_cols = [
        "is_bt", "is_sharing_int", "config_terminal", "config_nodal", "config_agreg",
        "network_type_4g", "network_type_5g", "estimated_consumption_kwh",
        "has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g",
        "active_alert_count", "has_sfr_alert",
        "site_mean_24m", "site_std_24m", "site_trend_12m",
        "consumption_to_mean_ratio", "data_quality_pct",
    ]
    result = {}
    for col in static_cols:
        if col in last.index:
            val = last[col]
            result[col] = float(val) if not pd.isna(val) else 0.0
        else:
            result[col] = 0.0
    return result


def _get_historical_month_value(site_hist: pd.DataFrame, month: int, col: str = "total_consumption_kwh") -> float:
    if site_hist.empty or col not in site_hist.columns or "month" not in site_hist.columns:
        return 0.0
    sub = site_hist[site_hist["month"] == month]
    if sub.empty:
        return 0.0
    val = sub[col].iloc[-1]
    return float(val) if not pd.isna(val) else 0.0


def _get_last_n_values(site_hist: pd.DataFrame, n: int) -> list[float]:
    if site_hist.empty or "total_consumption_kwh" not in site_hist.columns:
        return []
    vals = site_hist.tail(n)["total_consumption_kwh"].values
    return [float(v) if not pd.isna(v) else 0.0 for v in vals]


def forecast_site(
    site_hist: pd.DataFrame,
    site_id: int,
    target_year: int,
    model_pkg: dict,
    lag_12_predicted: list[float] | None = None,
) -> list[dict]:
    model = model_pkg["model"]
    features_list = model_pkg["features"]
    calibration = model_pkg.get("calibration", {})

    site_hist = site_hist.sort_values("month")
    site_mean_val = float(site_hist["total_consumption_kwh"].mean())
    static = _get_static_features(site_hist)
    site_mean_24m = static.get("site_mean_24m", site_mean_val)

    hist_12 = _get_last_n_values(site_hist, 12)
    predictions = []
    predicted_map = {}

    for month in range(1, 13):
        row = {}
        row["month"] = month
        row["quarter"] = (month - 1) // 3 + 1
        row["month_sin"] = float(np.sin(2 * np.pi * month / 12))
        row["month_cos"] = float(np.cos(2 * np.pi * month / 12))

        for lag_offset in [1, 2, 3]:
            if month > lag_offset:
                val = predicted_map.get(month - lag_offset, 0.0)
            else:
                hist_idx = 12 - (lag_offset - month)
                if 0 <= hist_idx < len(hist_12):
                    val = hist_12[hist_idx]
                else:
                    val = 0.0
            row[f"lag_{lag_offset}"] = val

        if lag_12_predicted is not None and 0 < month <= len(lag_12_predicted):
            row["lag_12"] = float(lag_12_predicted[month - 1])
        else:
            row["lag_12"] = _get_historical_month_value(site_hist, month)

        recent_3 = []
        for m in range(month - 3, month):
            if m < 1:
                hist_idx = 12 + m
                if 0 <= hist_idx < len(hist_12):
                    recent_3.append(hist_12[hist_idx])
            else:
                recent_3.append(predicted_map.get(m, 0.0))
        row["rolling_mean_3"] = float(np.mean(recent_3)) if recent_3 else 0.0
        row["rolling_std_3"] = float(np.std(recent_3)) if len(recent_3) >= 2 else 0.0

        recent_6 = []
        for m in range(month - 6, month):
            if m < 1:
                hist_idx = 12 + m
                if 0 <= hist_idx < len(hist_12):
                    recent_6.append(hist_12[hist_idx])
            else:
                recent_6.append(predicted_map.get(m, 0.0))
        row["rolling_max_6"] = float(max(recent_6)) if recent_6 else 0.0

        lag_12_val = row["lag_12"]
        row["yoy_change"] = ((row["lag_1"] - lag_12_val) / lag_12_val) if lag_12_val != 0 else 0.0

        row.update(static)

        input_df = pd.DataFrame([row])
        for col in ["year", "site_id", "_tmp_date", "_month_dt"]:
            if col in input_df.columns:
                input_df = input_df.drop(columns=[col])

        missing = [c for c in features_list if c not in input_df.columns]
        for col in missing:
            input_df[col] = 0.0

        pred_kwh, ci_lower, ci_upper = predict_with_calibration(
            model, features_list, input_df, calibration, site_id
        )
        pred_kwh = apply_sanity_bounds(pred_kwh, site_mean_val, site_mean_24m)

        pred_value = max(float(pred_kwh[0]), 0.0)
        lower_val = max(float(ci_lower[0]), 0.0)
        upper_val = max(float(ci_upper[0]), 0.0)

        predicted_map[month] = pred_value
        predictions.append({
            "month": month,
            "predicted_consumption": pred_value,
            "ci_lower": lower_val,
            "ci_upper": upper_val,
        })

    return predictions


async def build_feature_matrix(
    session: AsyncSession,
    target_year: int,
    site_id: int | None = None,
) -> pd.DataFrame:
    historical_data = await get_monthly_consumption_from_invoices(
        session, site_id=site_id, end_year=target_year - 1
    )
    df = pd.DataFrame(historical_data)
    if df.empty:
        return df
    numeric_cols = (
        "total_consumption_kwh", "estimated_consumption", "final_sale",
        "tax_amount", "kwh_price_bt", "kwh_price_mt", "tax_rate"
    )
    for col in df.columns:
        if col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    alert_agg = await get_alert_aggregates_by_site(session, end_year=target_year - 1)
    df["active_alert_count"] = df["site_id"].map(
        lambda sid: alert_agg.get(sid, {}).get("active_alert_count", 0)
    )
    df["has_sfr_alert"] = df["site_id"].map(
        lambda sid: alert_agg.get(sid, {}).get("has_sfr_alert", False)
    ).astype(int)
    df["critical_alert_count"] = df["site_id"].map(
        lambda sid: alert_agg.get(sid, {}).get("critical_alert_count", 0)
    )
    df = engineer_features(df)
    return df


async def _get_sites_data(
    session: AsyncSession,
    target_year: int,
    site_id: int | None = None,
) -> pd.DataFrame:
    df = await build_feature_matrix(session, target_year, site_id=site_id)
    if df.empty:
        return df
    if site_id is not None:
        df = df[df["site_id"] == site_id].copy()
    historic = df[df["year"] < target_year].copy()
    return historic


async def _compute_tech_estimates(session, site_codes: set[str] | None = None) -> dict:
    from sqlalchemy import text
    extra_where = "AND s.\"SiteCode\" = ANY(:codes)" if site_codes else ""
    params = {"codes": list(site_codes)} if site_codes else {}
    r = await session.execute(text(f"""
        SELECT sc.site_code, sc.has_2g, sc.has_3g, sc.has_4g_fdd, sc.has_4g_tdd, sc.has_5g
        FROM site_tech_configs sc
        JOIN sites s ON s."SiteCode" = sc.site_code
        WHERE {site_filter('s')}
        {extra_where}
    """), params)
    total = 0.0
    count = 0
    for row in r:
        total += estimate_from_tech_flags({
            "has_2g": row[1], "has_3g": row[2],
            "has_4g_fdd": row[3], "has_4g_tdd": row[4],
            "has_5g": row[5],
        })
        count += 1
    return {
        "tech_estimated_kwh_month": round(total, 2),
        "tech_estimated_kwh_year": round(total * 12, 2),
        "tech_estimated_sites": count,
    }


async def compute_global_forecast(
    session: AsyncSession,
    target_year: int,
) -> dict | None:
    try:
        model_pkg = load_model()
    except FileNotFoundError:
        logger.error("Model not found. Train the model first.")
        return None

    historic = await _get_sites_data(session, target_year)
    if historic.empty:
        return None

    # Filter to sites active in the latest complete historical year
    # so forecast and baseline cover the same site set
    max_year = int(historic["year"].max())
    years_with_months = historic.groupby("year")["month"].nunique()
    complete_years = years_with_months[years_with_months == 12]
    if not complete_years.empty:
        ref_year = int(complete_years.index[-1])
    else:
        ref_year = max_year
    sites_in_ref = set(historic[historic["year"] == ref_year]["site_id"].unique())
    site_ids = [sid for sid in historic["site_id"].unique() if sid in sites_in_ref]
    logger.info("Forecasting %d sites (ref year=%d, total unique=%d)",
                len(site_ids), ref_year, len(historic["site_id"].unique()))

    historic = historic[historic["site_id"].isin(site_ids)]

    all_predictions = []

    for sid in site_ids:
        site_hist = historic[historic["site_id"] == sid]
        preds = forecast_site(site_hist, sid, target_year, model_pkg)
        elec_type = str(site_hist["elec_type"].iloc[-1]) if "elec_type" in site_hist.columns else "BT"
        for p in preds:
            p["site_id"] = sid
            p["elec_type"] = elec_type
            all_predictions.append(p)

    if not all_predictions:
        return None

    forecast_df = pd.DataFrame(all_predictions)
    budget = compute_monthly_budget(forecast_df)

    if budget.get("monthly_kwh"):
        budget["monthly_kwh"] = _apply_seasonal_shape(budget["monthly_kwh"])
        budget["monthly_budget_tnd"] = _apply_seasonal_shape(budget["monthly_budget_tnd"])
        budget["total_predicted_kwh"] = sum(budget["monthly_kwh"])
        budget["total_budget_tnd"] = sum(budget["monthly_budget_tnd"])
        budget["monthly_std_kwh"] = round(float(np.array(budget["monthly_kwh"]).std()), 0)

    max_year = int(historic["year"].max())
    last_year_mask = historic["year"] == max_year
    historical_df = historic[last_year_mask]
    hist_months = int(historical_df["month"].nunique()) if "month" in historical_df.columns else 12
    partial_year = hist_months < 12
    if partial_year:
        prev_year_mask = historic["year"] == max_year - 1
        prev_df = historic[prev_year_mask]
        prev_months = int(prev_df["month"].nunique()) if "month" in prev_df.columns else 0
        if prev_months == 12:
            budget["historical_year"] = max_year - 1
            budget["total_historical_kwh"] = float(prev_df["total_consumption_kwh"].sum())
            budget["historical_months"] = prev_months
        else:
            budget["historical_year"] = max_year
            budget["total_historical_kwh"] = float(historical_df["total_consumption_kwh"].sum())
            budget["historical_months"] = hist_months
        budget["partial_year_warning"] = True
        budget["partial_year_actual_max"] = max_year
    else:
        budget["historical_year"] = max_year
        budget["total_historical_kwh"] = float(historical_df["total_consumption_kwh"].sum())
        budget["historical_months"] = hist_months
        budget["partial_year_warning"] = False
    budget["total_sites"] = int(historic["site_id"].nunique())

    bts = historic[historic.get("elec_type") == "BT"]
    mts = historic[historic.get("elec_type") == "MT"]
    budget["bt_site_count"] = int(bts["site_id"].nunique())
    budget["mt_site_count"] = int(mts["site_id"].nunique())

    sfr_sites = historic[historic["has_sfr_alert"] == 1]["site_id"].unique()
    budget["sfr_affected_sites"] = int(len(sfr_sites))

    forecast_site_codes = set(historic["site_code"].unique()) if "site_code" in historic.columns else None
    tech = await _compute_tech_estimates(session, site_codes=forecast_site_codes)
    budget.update(tech)
    budget["features_used"] = model_pkg.get("features", [])

    return budget


async def compute_site_forecast(
    session: AsyncSession,
    site_code: str,
    target_year: int,
) -> dict | None:
    from sqlalchemy import text
    result = await session.execute(
        text("""SELECT "SiteId", "SiteName", "SiteCode", "Configuration", "ElecType"
                FROM sites WHERE "SiteCode" = :code
                  AND {site_filter_no_alias()}"""),
        {"code": site_code},
    )
    row = result.fetchone()
    if not row:
        return None

    site_id, site_name, scode, config, elec_type = row[0], row[1], row[2], row[3], row[4]
    try:
        model_pkg = load_model()
    except FileNotFoundError:
        logger.error("Model not found.")
        return None

    historic = await _get_sites_data(session, target_year, site_id=site_id)
    if historic.empty:
        return None

    site_hist = historic[historic["site_id"] == site_id].copy()
    if site_hist.empty:
        return None

    preds = forecast_site(site_hist, site_id, target_year, model_pkg)
    for p in preds:
        p["site_id"] = site_id
        p["elec_type"] = elec_type

    forecast_df = pd.DataFrame(preds)
    site_budget = compute_monthly_budget(forecast_df)
    if site_budget.get("monthly_kwh"):
        site_budget["monthly_kwh"] = _apply_seasonal_shape(site_budget["monthly_kwh"])
        site_budget["monthly_budget_tnd"] = _apply_seasonal_shape(site_budget["monthly_budget_tnd"])
        site_budget["total_predicted_kwh"] = sum(site_budget["monthly_kwh"])
        site_budget["total_budget_tnd"] = sum(site_budget["monthly_budget_tnd"])

    last_year_max = int(site_hist["year"].max())
    last_site_df = site_hist[site_hist["year"] == last_year_max]
    site_hist_months = int(last_site_df["month"].nunique()) if "month" in last_site_df.columns else 12
    if site_hist_months < 12:
        prev_site_df = site_hist[site_hist["year"] == last_year_max - 1]
        prev_site_months = int(prev_site_df["month"].nunique()) if "month" in prev_site_df.columns else 0
        if prev_site_months == 12:
            site_budget["historical_year"] = last_year_max - 1
            site_budget["historical_kwh"] = float(prev_site_df["total_consumption_kwh"].sum())
        else:
            site_budget["historical_year"] = last_year_max
            site_budget["historical_kwh"] = float(last_site_df["total_consumption_kwh"].sum())
        site_budget["partial_year_warning"] = True
    else:
        site_budget["historical_year"] = last_year_max
        site_budget["historical_kwh"] = float(last_site_df["total_consumption_kwh"].sum())
        site_budget["partial_year_warning"] = False

    has_radio = any(col in site_hist.columns for col in
                    ["has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g"])
    if has_radio:
        last_row = site_hist.iloc[-1]
        tech_est = estimate_from_tech_flags({
            "has_2g": bool(last_row.get("has_2g", False)),
            "has_3g": bool(last_row.get("has_3g", False)),
            "has_4g_fdd": bool(last_row.get("has_4g_fdd", False)),
            "has_4g_tdd": bool(last_row.get("has_4g_tdd", False)),
            "has_5g": bool(last_row.get("has_5g", False)),
        })
    else:
        tech_est = estimate_from_tech_flags({})

    has_sfr = bool(site_hist["has_sfr_alert"].iloc[-1]) if "has_sfr_alert" in site_hist.columns else False
    alert_count = int(site_hist["active_alert_count"].iloc[-1]) if "active_alert_count" in site_hist.columns else 0

    tech_flags = {}
    for col in ["has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g"]:
        if col in site_hist.columns:
            tech_flags[col] = bool(site_hist[col].iloc[-1])

    site_budget.update({
        "site_id": site_id,
        "site_name": site_name,
        "site_code": scode,
        "configuration": config,
        "elec_type": elec_type,
        "tech_estimated_kwh_month": round(tech_est, 2),
        "tech_estimated_kwh_year": round(tech_est * 12, 2),
        "has_sfr_alert": has_sfr,
        "active_alert_count": alert_count,
        **tech_flags,
    })

    return site_budget
