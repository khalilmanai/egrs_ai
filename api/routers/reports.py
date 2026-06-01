import uuid
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.dependencies import get_db
from data.db import get_session_sync
from llm.chain import generate_budget_forecast, compute_budget_fast
from report.forecast import compute_global_budget, compute_site_budget
from report.generator import generate_global_forecast_report, generate_year_analysis_report, generate_site_forecast_report
from llm.prompts import (
    SYSTEM_PROMPT_BASE,
    GLOBAL_FORECAST_SCHEMA,
    YEAR_ANALYSIS_SCHEMA,
    SITE_FORECAST_SCHEMA,
    build_global_forecast_prompt,
    build_year_analysis_prompt,
    build_site_forecast_prompt,
)
from llm.ollama_client import generate_structured_report
from llm.parsers import parse_report_output, fixup_llm_data
from data.analyzers.health_scorer import compute_enterprise_health_summary
from data.extractors.alerts import get_alert_summary, get_sfr_analysis, get_alerts_by_site
from data.extractors.invoices import get_yearly_billing_summary
from data.analyzers.anomaly_detector import (
    detect_consumption_anomalies,
    detect_trend_anomalies,
    detect_iqr_anomalies,
)
from estimators.tech_consumption import estimate_from_tech_flags
from rag.document_rag import query_documents
from api.schemas.reports import (
    ReportRequest,
    ReportResponse,
    JobStatusResponse,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

_jobs: dict[str, dict] = {}
_TTL = timedelta(hours=1)


def _cleanup_stale_jobs():
    now = datetime.now()
    stale = [
        jid for jid, job in _jobs.items()
        if "created_at" in job and now - job["created_at"] > _TTL
    ]
    for jid in stale:
        del _jobs[jid]


@router.post("/budget-forecast", response_model=ReportResponse)
async def create_budget_forecast(
    request: ReportRequest,
    session: AsyncSession = Depends(get_db),
):
    _cleanup_stale_jobs()
    if len(_jobs) > 100:
        raise HTTPException(status_code=503, detail="Too many pending jobs.")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "progress": 0, "created_at": datetime.now()}
    asyncio.create_task(_run_forecast_job(job_id, request))
    return ReportResponse(
        job_id=job_id,
        status="pending",
        message="Report generation started. Poll GET /reports/{job_id} for completion.",
    )


@router.post("/global-forecast", response_model=ReportResponse)
async def create_global_forecast(
    request: ReportRequest,
    session: AsyncSession = Depends(get_db),
):
    _cleanup_stale_jobs()
    if len(_jobs) > 100:
        raise HTTPException(status_code=503, detail="Too many pending jobs.")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "progress": 0, "created_at": datetime.now()}
    asyncio.create_task(_run_global_forecast_job(job_id, request))
    return ReportResponse(
        job_id=job_id,
        status="pending",
        message="Global forecast started. Poll GET /reports/{job_id}.",
    )


@router.get("/year-analysis")
async def get_year_analysis(
    year: int = Query(default=2026, ge=2020),
    session: AsyncSession = Depends(get_db),
):
    health_summary = await compute_enterprise_health_summary(session, year)
    alert_summary_data = await get_alert_summary(session)
    sfr_data = await get_sfr_analysis(session)
    anomaly_zscore = await detect_consumption_anomalies(session, year)
    anomaly_trend = await detect_trend_anomalies(session, year)
    anomaly_iqr = await detect_iqr_anomalies(session, year)
    billing_summary = await get_yearly_billing_summary(session, year)

    anomaly_analysis = {
        "zscore_anomalies": anomaly_zscore,
        "trend_anomalies": anomaly_trend,
        "iqr_anomalies": anomaly_iqr,
    }

    rag_ctx = None
    try:
        rag_result = await query_documents(
            session,
            f"Site health and energy performance for Orange Tunisie year {year}",
            top_k=3,
        )
        if rag_result.get("sources"):
            rag_ctx = rag_result.get("answer", "")
    except Exception:
        pass

    try:
        user_content = build_year_analysis_prompt(
            health_summary=health_summary,
            alert_summary=alert_summary_data,
            sfr_analysis=sfr_data,
            anomaly_analysis=anomaly_analysis,
            billing_summary=billing_summary,
            rag_context=rag_ctx,
        )
        llm_output = await generate_structured_report(
            system_prompt=SYSTEM_PROMPT_BASE,
            user_prompt=user_content,
            json_schema=YEAR_ANALYSIS_SCHEMA,
        )
        parsed = parse_report_output(llm_output, "year_analysis")
        llm_error = parsed.get("status") != "success"
    except Exception:
        parsed = {"status": "error", "error": "LLM analysis failed"}
        llm_error = True

    global_budget = await compute_global_budget(session, year + 1)

    data = {
        "status": parsed.get("status", "error"),
        "data": parsed.get("data"),
        "llm_error": llm_error,
        "target_year": year,
        "enterprise_data": {
            "summary": health_summary,
            "alert_summary": alert_summary_data,
            "sfr_analysis": sfr_data,
            "anomaly_analysis": anomaly_analysis,
            "rag_context": rag_ctx,
        },
        "numerical_data": {
            "global": global_budget or {},
            "billing_summary": billing_summary,
        },
    }

    if data.get("data"):
        data["data"] = fixup_llm_data(data["data"], data.get("numerical_data"))

    report_files = await generate_year_analysis_report(data)
    return {**data, **report_files}


@router.get("/site-forecast/{site_code}")
async def get_site_forecast(
    site_code: str,
    target_year: int = Query(default=2027, ge=2025),
    session: AsyncSession = Depends(get_db),
):
    site_budget = await compute_site_budget(session, site_code, target_year)
    if site_budget is None:
        raise HTTPException(status_code=404, detail=f"Site '{site_code}' not found or no data")

    r = await session.execute(
        text("""
            SELECT st.*, s."SiteName", s."Configuration"
            FROM site_tech_configs st
            JOIN sites s ON s."SiteCode" = st.site_code
            WHERE st.site_code = :code
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        """),
        {"code": site_code},
    )
    tech_row = r.fetchone()
    tech_config = None
    if tech_row:
        flags = {
            "has_2g": tech_row[1], "has_3g": tech_row[2],
            "has_4g_fdd": tech_row[3], "has_4g_tdd": tech_row[4],
            "has_5g": tech_row[5],
        }
        tech_config = {
            "site_code": tech_row[0],
            "site_name": tech_row[9],
            **flags,
            "radio_config": tech_row[6],
            "estimated_kwh_per_month": estimate_from_tech_flags(flags),
        }

    sfr_alerts = []
    try:
        alerts = await get_alerts_by_site(session, site_budget["site_id"])
        sfr_alerts = [a for a in (alerts or []) if "SFR" in str(a.get("type", "")).upper()]
    except Exception:
        pass

    site_info = {
        "site_id": site_budget["site_id"],
        "site_name": site_budget["site_name"],
        "site_code": site_budget["site_code"],
        "configuration": site_budget.get("configuration", ""),
        "elec_type": site_budget.get("elec_type", ""),
        "historical_kwh": site_budget.get("historical_kwh", 0),
    }

    try:
        user_content = build_site_forecast_prompt(
            site_info=site_info,
            site_budget=site_budget,
            sfr_alerts=sfr_alerts,
        )
        llm_output = await generate_structured_report(
            system_prompt=SYSTEM_PROMPT_BASE,
            user_prompt=user_content,
            json_schema=SITE_FORECAST_SCHEMA,
        )
        parsed = parse_report_output(llm_output, "site_forecast")
        llm_error = parsed.get("status") != "success"
    except Exception:
        parsed = {"status": "error", "error": "LLM analysis failed"}
        llm_error = True

    data = {
        "status": parsed.get("status", "error"),
        "data": parsed.get("data"),
        "llm_error": llm_error,
        "target_year": target_year,
        "site_name": site_budget.get("site_name", ""),
        "site_code": site_code,
        "numerical_data": {
            "site": site_budget,
            "tech_config": tech_config,
            "sfr_alerts": sfr_alerts,
        },
    }

    if data.get("data"):
        data["data"] = fixup_llm_data(data["data"], data.get("numerical_data"))

    report_files = await generate_site_forecast_report(data)
    return {**data, **report_files}


@router.get("/global-budget")
async def get_global_budget(
    target_year: int = Query(default=2027, ge=2025),
    session: AsyncSession = Depends(get_db),
):
    result = await compute_budget_fast(session, target_year=target_year, site_code=None)
    if result is None:
        raise HTTPException(status_code=404, detail="No data available")
    return result


@router.get("/site-budget/{site_code}")
async def get_site_budget(
    site_code: str,
    target_year: int = Query(default=2027, ge=2025),
    session: AsyncSession = Depends(get_db),
):
    result = await compute_budget_fast(session, target_year=target_year, site_code=site_code)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Site '{site_code}' not found")
    return result


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0),
        result=job.get("result"),
        error=job.get("error"),
    )


async def _run_forecast_job(job_id: str, request: ReportRequest):
    session = get_session_sync()
    try:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["progress"] = 10
        chain_result = await generate_budget_forecast(
            session=session,
            new_sites=request.new_sites or [],
            target_year=request.target_year,
            user_prompt=request.user_prompt,
            site_name=request.site_name,
            enterprise=request.enterprise,
        )
        _jobs[job_id]["progress"] = 60
        report_files = await generate_global_forecast_report(chain_result)
        _jobs[job_id]["progress"] = 90
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 100
        _jobs[job_id]["result"] = {
            "data": chain_result,
            **report_files,
        }
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
    finally:
        await session.close()


async def _run_global_forecast_job(job_id: str, request: ReportRequest):
    session = get_session_sync()
    try:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["progress"] = 10

        global_budget = await compute_global_budget(session, request.target_year)
        if global_budget is None:
            raise ValueError("No historical data available")
        _jobs[job_id]["progress"] = 30

        billing_summary = await get_yearly_billing_summary(session, request.target_year - 1)
        _jobs[job_id]["progress"] = 40

        user_content = build_global_forecast_prompt(
            global_budget=global_budget,
            billing_summary=billing_summary,
            rag_context=None,
            user_prompt=request.user_prompt,
        )

        try:
            llm_output = await generate_structured_report(
                system_prompt=SYSTEM_PROMPT_BASE,
                user_prompt=user_content,
                json_schema=GLOBAL_FORECAST_SCHEMA,
            )
            parsed = parse_report_output(llm_output)
        except Exception:
            parsed = {"status": "error", "error": "LLM analysis failed"}

        _jobs[job_id]["progress"] = 60

        llm_data = parsed.get("data")
        numerical_data = {"global": global_budget, "billing_summary": billing_summary}
        if llm_data:
            llm_data = fixup_llm_data(llm_data, numerical_data)

        chain_result = {
            "status": parsed.get("status", "error"),
            "data": llm_data,
            "numerical_data": numerical_data,
            "llm_error": parsed.get("status") != "success",
            "target_year": request.target_year,
        }

        report_files = await generate_global_forecast_report(chain_result)
        _jobs[job_id]["progress"] = 90
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 100
        _jobs[job_id]["result"] = {
            "data": chain_result,
            **report_files,
        }
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
    finally:
        await session.close()
