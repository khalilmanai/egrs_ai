import pandas as pd
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from data.extractors.consumption import get_monthly_consumption_from_invoices
from ml.features import engineer_features
from ml.forecasting.xgboost_model import load_model, predict_consumption
from estimators.tech_consumption import estimate_from_tech_flags

PRICE_BT = 0.396
PRICE_MT = 0.414
TAX_RATE = 0.19


def compute_monthly_ktnd(forecast_df: pd.DataFrame) -> dict:
    if forecast_df.empty or "predicted_consumption" not in forecast_df.columns:
        return {"monthly_kwh": [0]*12, "monthly_ktnd": [0]*12, "total_ktnd": 0, "total_predicted_kwh": 0}

    forecast_df = forecast_df.copy()
    forecast_df["_price"] = forecast_df.get("elec_type", pd.Series(["BT"])).map(
        lambda x: PRICE_MT if x == "MT" else PRICE_BT
    )
    forecast_df["_ktnd"] = (
        forecast_df["predicted_consumption"]
        * forecast_df["_price"]
        * (1 + TAX_RATE)
        / 1000
    )

    monthly_kwh = forecast_df.groupby("month")["predicted_consumption"].sum()
    monthly_ktnd = forecast_df.groupby("month")["_ktnd"].sum()

    monthly_kwh_arr = [float(monthly_kwh.get(m, 0)) for m in range(1, 13)]
    monthly_ktnd_arr = [float(monthly_ktnd.get(m, 0)) for m in range(1, 13)]

    return {
        "total_predicted_kwh": float(forecast_df["predicted_consumption"].sum()),
        "total_ktnd": float(forecast_df["_ktnd"].sum()),
        "monthly_kwh": monthly_kwh_arr,
        "monthly_ktnd": monthly_ktnd_arr,
    }


def get_forecast_df(df: pd.DataFrame, target_year: int) -> tuple[pd.DataFrame, int]:
    years = df.groupby("year")["month"].nunique()
    complete = years[years >= 11].index
    if len(complete) > 0:
        base_year = int(complete.max())
    else:
        base_year = int(df["year"].max())
    forecast_df = df[df["year"] == base_year].copy()
    if forecast_df.empty:
        return pd.DataFrame(), base_year
    forecast_df["year"] = target_year
    return forecast_df, base_year


def run_xgboost(df: pd.DataFrame, forecast_df: pd.DataFrame) -> pd.DataFrame:
    try:
        model, features = load_model()
        predictions = predict_consumption(model, features, forecast_df)
        forecast_df["predicted_consumption"] = predictions
        return forecast_df
    except FileNotFoundError:
        return pd.DataFrame()


async def compute_global_budget(
    session: AsyncSession,
    target_year: int,
) -> dict:
    historical_data = await get_monthly_consumption_from_invoices(
        session, end_year=target_year - 1
    )
    df = pd.DataFrame(historical_data)
    if df.empty:
        return None
    df = engineer_features(df)

    forecast_df, base_year = get_forecast_df(df, target_year)
    forecast_df = run_xgboost(df, forecast_df)
    budget = compute_monthly_ktnd(forecast_df)
    historical_df = df[df["year"] == base_year]
    budget["total_sites"] = int(historical_df["site_id"].nunique()) if not historical_df.empty else 0
    budget["historical_year"] = base_year
    budget["total_historical_kwh"] = float(historical_df["total_consumption_kwh"].sum()) if not historical_df.empty else 0

    r = await session.execute(text("""
        SELECT st.has_2g, st.has_3g, st.has_4g_fdd, st.has_4g_tdd, st.has_5g
        FROM site_tech_configs st
        JOIN sites s ON s."SiteCode" = st.site_code
        WHERE s."DirectionId" = 1 AND s."StatusId" IN (1,3)
    """))
    tech_total = 0.0
    tech_count = 0
    for row in r:
        tech_total += estimate_from_tech_flags({
            "has_2g": row[0], "has_3g": row[1],
            "has_4g_fdd": row[2], "has_4g_tdd": row[3],
            "has_5g": row[4],
        })
        tech_count += 1
    budget["tech_estimated_kwh_month"] = round(tech_total, 2)
    budget["tech_estimated_kwh_year"] = round(tech_total * 12, 2)
    budget["tech_estimated_sites"] = tech_count

    return budget


async def compute_site_budget(
    session: AsyncSession,
    site_code: str,
    target_year: int,
) -> dict | None:
    result = await session.execute(
        text("""SELECT "SiteId", "SiteName", "SiteCode", "Configuration", "ElecType"
                FROM sites WHERE "SiteCode" = :code
                  AND "DirectionId" = 1 AND "StatusId" IN (1,3)"""),
        {"code": site_code},
    )
    row = result.fetchone()
    if not row:
        return None
    site_info = {
        "site_id": row[0], "site_name": row[1], "site_code": row[2],
        "configuration": row[3], "elec_type": row[4],
    }
    historical_data = await get_monthly_consumption_from_invoices(
        session, site_id=site_info["site_id"], end_year=target_year - 1
    )

    df = pd.DataFrame(historical_data)
    if df.empty:
        return None
    df = engineer_features(df)

    site_forecast_df, base_year = get_forecast_df(df, target_year)
    site_forecast_df = run_xgboost(df, site_forecast_df)
    site_budget = compute_monthly_ktnd(site_forecast_df)

    historical_kwh = float(df[df["year"] == base_year]["total_consumption_kwh"].sum()) if not df.empty else 0
    site_budget["historical_year"] = base_year

    return {
        **site_info,
        **site_budget,
        "historical_kwh": historical_kwh,
    }
