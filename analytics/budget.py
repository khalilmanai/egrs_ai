import numpy as np
import pandas as pd
from config.settings import get_settings

_settings = get_settings()
PRICE_BT = _settings.kwh_price_bt
PRICE_MT = _settings.kwh_price_mt
TAX_RATE = _settings.tax_rate


def compute_monthly_budget(forecast_df: pd.DataFrame) -> dict:
    if forecast_df.empty or "predicted_consumption" not in forecast_df.columns:
        return {
            "total_predicted_kwh": 0,
            "total_budget_tnd": 0,
            "monthly_kwh": [0] * 12,
            "monthly_budget_tnd": [0] * 12,
            "monthly_ci_lower": [0] * 12,
            "monthly_ci_upper": [0] * 12,
        }

    forecast_df = forecast_df.copy()
    forecast_df["_price"] = forecast_df.get("elec_type", pd.Series(["BT"])).map(
        lambda x: PRICE_MT if x == "MT" else PRICE_BT
    )
    forecast_df["_cost_tnd"] = (
        forecast_df["predicted_consumption"]
        * forecast_df["_price"]
        * (1 + TAX_RATE)
    )

    monthly_kwh = forecast_df.groupby("month")["predicted_consumption"].sum()
    monthly_cost = forecast_df.groupby("month")["_cost_tnd"].sum()

    monthly_kwh_arr = [float(monthly_kwh.get(m, 0)) for m in range(1, 13)]
    monthly_cost_arr = [float(monthly_cost.get(m, 0)) for m in range(1, 13)]

    monthly_ci_lower = []
    monthly_ci_upper = []
    for m in range(1, 13):
        mdata = forecast_df[forecast_df["month"] == m]
        if mdata.empty:
            monthly_ci_lower.append(0)
            monthly_ci_upper.append(0)
            continue
        total_pred = mdata["predicted_consumption"].sum()
        site_stds = (mdata["ci_upper"] - mdata["ci_lower"]) / (2.0 * 1.96)
        total_std = np.sqrt((site_stds ** 2).sum())
        monthly_ci_lower.append(float(max(total_pred - 1.96 * total_std, 0)))
        monthly_ci_upper.append(float(total_pred + 1.96 * total_std))

    predicted_kwh = forecast_df["predicted_consumption"].values
    std_err = float(predicted_kwh.std()) / max(float(np.sqrt(len(predicted_kwh))), 1)

    return {
        "total_predicted_kwh": float(forecast_df["predicted_consumption"].sum()),
        "total_budget_tnd": float(forecast_df["_cost_tnd"].sum()),
        "monthly_kwh": [round(v, 0) for v in monthly_kwh_arr],
        "monthly_budget_tnd": [round(v, 2) for v in monthly_cost_arr],
        "monthly_ci_lower": [round(v, 0) for v in monthly_ci_lower],
        "monthly_ci_upper": [round(v, 0) for v in monthly_ci_upper],
        "std_error": round(std_err, 2),
    }


def compute_precomputed_insights(budget: dict) -> dict:
    total_kwh = budget.get("total_predicted_kwh", 0)
    total_tnd = budget.get("total_budget_tnd", 0)
    hist_kwh = budget.get("total_historical_kwh", 0)
    hist_months = budget.get("historical_months", 0)
    total_sites = budget.get("total_sites", 0)

    if hist_kwh and hist_months and hist_months >= 1:
        hist_annualized = hist_kwh * 12 / hist_months
    else:
        hist_annualized = hist_kwh
    yoy = round(((total_kwh - hist_annualized) / hist_annualized * 100), 1) if hist_annualized else 0

    monthly_kwh = budget.get("monthly_kwh", [])
    if any(monthly_kwh):
        max_kwh = max(monthly_kwh)
        min_kwh = min(monthly_kwh)
        max_idx = monthly_kwh.index(max_kwh) + 1
        min_idx = monthly_kwh.index(min_kwh) + 1
    else:
        max_kwh = min_kwh = max_idx = min_idx = 0

    tech_kwh = budget.get("tech_estimated_kwh_year", 0)
    tech_gap = round(((total_kwh - tech_kwh) / tech_kwh * 100), 1) if tech_kwh else 0

    monthly_ci_lower = budget.get("monthly_ci_lower", [])
    monthly_ci_upper = budget.get("monthly_ci_upper", [])
    total_lower = sum(monthly_ci_lower) if monthly_ci_lower else 0
    total_upper = sum(monthly_ci_upper) if monthly_ci_upper else 0
    ci_pct = round(((total_upper - total_lower) / 2 / total_kwh * 100), 1) if total_kwh else 0
    ci_pct = min(ci_pct, 50.0)

    return {
        "yoy_growth_pct": yoy,
        "total_sites": total_sites,
        "total_kwh": round(total_kwh, 0),
        "total_tnd": round(total_tnd, 2),
        "hist_kwh": round(hist_kwh, 0),
        "xgb_vs_tech_gap_pct": tech_gap,
        "tech_kwh": round(tech_kwh, 0),
        "confidence_interval_pct": ci_pct,
        "max_month_kwh": round(max_kwh, 0),
        "min_month_kwh": round(min_kwh, 0),
        "max_month": max_idx,
        "min_month": min_idx,
        "monthly_kwh": [round(v, 0) for v in monthly_kwh],
        "monthly_budget_tnd": [round(v, 2) for v in budget.get("monthly_budget_tnd", [])],
        "partial_year_warning": budget.get("partial_year_warning", False),
        "historical_year": budget.get("historical_year", 0),
    }
