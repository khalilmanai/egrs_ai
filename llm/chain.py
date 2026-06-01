import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from data.extractors.invoices import get_yearly_billing_summary
from data.extractors.consumption import get_monthly_consumption_from_invoices
from report.forecast import compute_global_budget, compute_site_budget, compute_monthly_ktnd, get_forecast_df, run_xgboost
from ml.features import engineer_features, build_query_vector_from_input
from rag.retriever import retrieve_similar_sites
from llm.prompts import SYSTEM_PROMPT_BASE, build_global_forecast_prompt, GLOBAL_FORECAST_SCHEMA
from llm.ollama_client import generate_structured_report
from llm.parsers import parse_report_output, fixup_llm_data
from data.analyzers.health_scorer import compute_enterprise_health_summary
from data.extractors.alerts import get_alert_summary, get_sfr_analysis
from data.analyzers.anomaly_detector import (
    detect_consumption_anomalies, detect_trend_anomalies, detect_iqr_anomalies,
)
from rag.document_rag import query_documents

FRENCH_MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


async def generate_budget_forecast(
    session: AsyncSession,
    new_sites: list[dict],
    target_year: int,
    user_prompt: str | None = None,
    site_name: str | None = None,
    enterprise: bool = False,
) -> dict:
    global_budget = await compute_global_budget(session, target_year)
    if global_budget is None:
        return {"status": "error", "error": "No historical data available"}

    site_info = None
    site_df = None
    site_budget = {"total_predicted_kwh": 0, "total_ktnd": 0, "monthly_kwh": [], "monthly_ktnd": []}
    if site_name:
        result = await session.execute(
            text("""SELECT "SiteId", "SiteName", "SiteCode", "Configuration", "ElecType"
                    FROM sites WHERE ("SiteName" = :name OR "SiteCode" = :name)
                      AND "DirectionId" = 1 AND "StatusId" IN (1,3)"""),
            {"name": site_name},
        )
        row = result.fetchone()
        if row:
            historical_data = await get_monthly_consumption_from_invoices(session, end_year=target_year - 1)
            df = pd.DataFrame(historical_data)
            if not df.empty:
                df = engineer_features(df)
                site_df = df[df["site_id"] == row[0]].copy()
                if not site_df.empty:
                    sf, base_year = get_forecast_df(site_df, target_year)
                    sf = run_xgboost(site_df, sf)
                    site_budget = compute_monthly_ktnd(sf)
                    site_budget["historical_year"] = base_year
                    site_info = {
                        "site_id": row[0], "site_name": row[1], "site_code": row[2],
                        "configuration": row[3], "elec_type": row[4],
                    }

    rag_context = {}
    if new_sites:
        for site_input in new_sites:
            query_vec = build_query_vector_from_input(site_input)
            similar = await retrieve_similar_sites(session, query_vec, limit=10)
            site_input["similar_sites"] = similar
        rag_context["new_site_analysis"] = new_sites

    current_year_billing = await get_yearly_billing_summary(session, target_year - 1)

    user_content = build_global_forecast_prompt(
        global_budget=global_budget,
        billing_summary=current_year_billing,
        rag_context=str(rag_context) if rag_context else None,
        user_prompt=user_prompt,
    )

    try:
        llm_output = await generate_structured_report(
            system_prompt=SYSTEM_PROMPT_BASE,
            user_prompt=user_content,
            json_schema=GLOBAL_FORECAST_SCHEMA,
        )
        parsed = parse_report_output(llm_output, "global_forecast")
    except Exception:
        parsed = {"status": "error", "error": "LLM analysis failed"}

    numerical_data = {
        "global": global_budget,
        "site": None,
        "billing_summary": current_year_billing,
    }
    if site_info is not None:
        numerical_data["site"] = {
            **site_info,
            "historical_kwh": float(site_df["total_consumption_kwh"].sum()) if site_df is not None and not site_df.empty else 0,
            "predicted_kwh": site_budget.get("total_predicted_kwh", 0),
            "total_ktnd": site_budget.get("total_ktnd", 0),
            "monthly_kwh": site_budget.get("monthly_kwh", []),
            "monthly_ktnd": site_budget.get("monthly_ktnd", []),
        }

    llm_data = parsed.get("data")
    if llm_data:
        llm_data = fixup_llm_data(llm_data, numerical_data)

    result = {
        "status": parsed.get("status", "error"),
        "data": llm_data,
        "numerical_data": numerical_data,
        "llm_error": parsed.get("status") != "success",
        "target_year": target_year,
    }

    if enterprise:
        try:
            health_summary = await compute_enterprise_health_summary(session, target_year - 1)
            alert_summary_data = await get_alert_summary(session)
            sfr_data = await get_sfr_analysis(session)
            anomaly_zscore = await detect_consumption_anomalies(session, target_year - 1)
            anomaly_trend = await detect_trend_anomalies(session, target_year - 1)
            anomaly_iqr = await detect_iqr_anomalies(session, target_year - 1)

            rag_ctx = None
            try:
                rag_result = await query_documents(
                    session,
                    f"Energy consumption and budget forecast for Orange Tunisie year {target_year}",
                    top_k=3,
                )
                if rag_result.get("sources"):
                    rag_ctx = rag_result
            except Exception:
                pass

            result["enterprise_data"] = {
                "summary": health_summary,
                "alert_summary": alert_summary_data,
                "sfr_analysis": sfr_data,
                "anomaly_analysis": {
                    "zscore_anomalies": anomaly_zscore,
                    "trend_anomalies": anomaly_trend,
                    "iqr_anomalies": anomaly_iqr,
                },
                "rag_context": rag_ctx,
            }
        except Exception as e:
            result["enterprise_data"] = {"error": f"Enterprise data collection failed: {type(e).__name__}: {e}"}

    return result


async def compute_budget_fast(
    session: AsyncSession,
    target_year: int,
    site_code: str | None = None,
) -> dict:
    if site_code:
        return await compute_site_budget(session, site_code, target_year)
    return await compute_global_budget(session, target_year)
