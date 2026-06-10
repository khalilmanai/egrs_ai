import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from analytics.forecast import compute_global_forecast, compute_site_forecast
from analytics.budget import compute_precomputed_insights
from analytics.trends import compute_yoy_change, compute_monthly_trends
from analytics.anomalies import run_all_detections
from analytics.health import compute_enterprise_health_summary
from analytics.summaries import get_billing_summary_by_direction
from analytics.similarity import retrieve_context_for_new_sites
from analytics.features import build_query_vector
from core.alerts import get_alert_summary, get_sfr_analysis, get_alerts_by_site
from core.vector_store import search_similar_vectors
from llm.client import generate_structured, LLMError
from rag.retriever import get_context_for_report
from llm.prompts import (
    build_global_forecast_prompt, GLOBAL_FORECAST_SCHEMA,
    build_year_analysis_prompt, YEAR_ANALYSIS_SCHEMA,
    build_site_forecast_prompt, SITE_FORECAST_SCHEMA,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


async def generate_global_forecast_report(
    session: AsyncSession,
    target_year: int,
    new_sites: list[dict] | None = None,
    user_prompt: str | None = None,
    include_enterprise: bool = False,
) -> dict:
    budget = await compute_global_forecast(session, target_year)
    if budget is None:
        return {"status": "error", "error": "No historical data available. Ensure model is trained."}

    insights = compute_precomputed_insights(budget)

    billing_task = get_billing_summary_by_direction(session, target_year - 1)
    rag_task = retrieve_context_for_new_sites(session, new_sites) if new_sites else None
    health_task = compute_enterprise_health_summary(session, target_year - 1) if include_enterprise else None
    anomalies_task = run_all_detections(session, target_year - 1) if include_enterprise else None

    tasks = [billing_task]
    if rag_task:
        tasks.append(rag_task)
    if health_task:
        tasks.append(health_task)
    if anomalies_task:
        tasks.append(anomalies_task)

    results = await asyncio.gather(*tasks)
    billing = results[0]
    rag_context = None
    health = None
    anomalies = None
    idx = 1
    if rag_task:
        rag_context = results[idx]
        idx += 1
    if health_task:
        health = results[idx]
        idx += 1
    if anomalies_task:
        anomalies = results[idx]

    doc_context = await get_context_for_report(
        session,
        f"Budget prévisionnel Orange Tunisie {target_year} consommation électrique sites DRS",
    )

    prompt = build_global_forecast_prompt(
        budget=budget,
        billing=billing,
        insights=insights,
        health=health,
        anomalies=anomalies,
        doc_context=doc_context,
        user_prompt=user_prompt,
    )

    try:
        llm_output = await generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            json_schema=GLOBAL_FORECAST_SCHEMA,
        )
        narrative = llm_output
        llm_error = False
    except LLMError as e:
        logger.warning("LLM error in global forecast: %s", e)
        narrative = None
        llm_error = True

    return {
        "status": "success" if not llm_error else "error",
        "target_year": target_year,
        "numerical_data": {
            "global": budget,
            "billing": billing,
            "insights": insights,
            "rag_context": rag_context,
        },
        "narrative": narrative,
        "llm_error": llm_error,
        "new_sites_analyzed": bool(new_sites),
    }


async def generate_year_analysis(
    session: AsyncSession,
    year: int,
    user_prompt: str | None = None,
) -> dict:
    health, billing, anomalies, sfr = await asyncio.gather(
        compute_enterprise_health_summary(session, year),
        get_billing_summary_by_direction(session, year),
        run_all_detections(session, year),
        get_sfr_analysis(session),
    )

    doc_context = await get_context_for_report(
        session,
        f"Analyse annuelle consommation énergie Orange Tunisie {year}",
    )

    prompt = build_year_analysis_prompt(
        health=health,
        billing=billing,
        anomalies=anomalies,
        sfr_analysis=sfr,
        doc_context=doc_context,
        user_prompt=user_prompt,
    )

    try:
        llm_output = await generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            json_schema=YEAR_ANALYSIS_SCHEMA,
        )
        narrative = llm_output
        llm_error = False
    except LLMError as e:
        logger.warning("LLM error in year analysis: %s", e)
        narrative = None
        llm_error = True

    return {
        "status": "success" if not llm_error else "error",
        "target_year": year,
        "numerical_data": {
            "health": health,
            "billing": billing,
            "anomalies": anomalies,
            "sfr": sfr,
        },
        "narrative": narrative,
        "llm_error": llm_error,
    }


async def generate_site_forecast_report(
    session: AsyncSession,
    site_code: str,
    target_year: int,
    user_prompt: str | None = None,
) -> dict:
    site_budget = await compute_site_forecast(session, site_code, target_year)
    if site_budget is None:
        return {"status": "error", "error": f"Site '{site_code}' not found or no data available"}

    alerts = []
    try:
        alerts = await get_alerts_by_site(session, site_budget.get("site_id"))
        sfr_alerts = [a for a in (alerts or []) if "SFR" in str(a.get("type", "")).upper()]
    except Exception:
        sfr_alerts = []

    doc_context = await get_context_for_report(
        session,
        f"Site {site_code} {site_budget.get('site_name', '')} consommation Orange Tunisie",
    )

    prompt = build_site_forecast_prompt(
        site_budget=site_budget,
        alerts=sfr_alerts,
        doc_context=doc_context,
        user_prompt=user_prompt,
    )

    try:
        llm_output = await generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            json_schema=SITE_FORECAST_SCHEMA,
        )
        narrative = llm_output
        llm_error = False
    except LLMError as e:
        logger.warning("LLM error in site forecast: %s", e)
        narrative = None
        llm_error = True

    return {
        "status": "success" if not llm_error else "error",
        "target_year": target_year,
        "site_code": site_code,
        "site_name": site_budget.get("site_name", ""),
        "numerical_data": {
            "site": site_budget,
            "alerts": sfr_alerts,
        },
        "narrative": narrative,
        "llm_error": llm_error,
    }
