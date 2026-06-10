import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from api.job_manager import run_in_background, get_job
from api.auth.dependencies import require_roles
from core.db import get_session_sync
from report.pdf_generator import (
    generate_global_forecast_pdf,
    generate_site_forecast_pdf,
    generate_yearly_analysis_pdf,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports PDF"])


class ForecastRequest(BaseModel):
    target_year: int = Field(default=2027, ge=2025, le=2035)


class SiteForecastRequest(BaseModel):
    site_code: str = Field(min_length=1)
    target_year: int = Field(default=2027, ge=2025, le=2035)


class YearAnalysisRequest(BaseModel):
    year: int = Field(default=2026, ge=2020, le=2030)


@router.post("/global-forecast", response_class=Response)
async def create_global_forecast_pdf(
    request: ForecastRequest,
    session: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    try:
        pdf_bytes = await generate_global_forecast_pdf(session, request.target_year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Global forecast PDF failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="prevision_globale_{request.target_year}.pdf"',
        },
    )


@router.post("/site-forecast", response_class=Response)
async def create_site_forecast_pdf(
    request: SiteForecastRequest,
    session: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    try:
        pdf_bytes = await generate_site_forecast_pdf(session, request.site_code, request.target_year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Site forecast PDF failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="prevision_site_{request.site_code}_{request.target_year}.pdf"',
        },
    )


@router.post("/yearly-analysis", response_class=Response)
async def create_yearly_analysis_pdf(
    request: YearAnalysisRequest,
    session: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    try:
        pdf_bytes = await generate_yearly_analysis_pdf(session, request.year)
    except Exception as e:
        logger.exception("Yearly analysis PDF failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="analyse_annuelle_{request.year}.pdf"',
        },
    )


@router.post("/async/global-forecast", status_code=202)
async def create_global_forecast_async(
    request: ForecastRequest,
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    async def _gen():
        session = get_session_sync()
        try:
            return await generate_global_forecast_pdf(session, request.target_year)
        finally:
            await session.close()
    job = run_in_background(_gen())
    return JSONResponse({"job_id": job.job_id, "status": job.status.value})


@router.post("/async/site-forecast", status_code=202)
async def create_site_forecast_async(
    request: SiteForecastRequest,
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    async def _gen():
        session = get_session_sync()
        try:
            return await generate_site_forecast_pdf(session, request.site_code, request.target_year)
        finally:
            await session.close()
    job = run_in_background(_gen())
    return JSONResponse({"job_id": job.job_id, "status": job.status.value})


@router.post("/async/yearly-analysis", status_code=202)
async def create_yearly_analysis_async(
    request: YearAnalysisRequest,
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    async def _gen():
        session = get_session_sync()
        try:
            return await generate_yearly_analysis_pdf(session, request.year)
        finally:
            await session.close()
    job = run_in_background(_gen())
    return JSONResponse({"job_id": job.job_id, "status": job.status.value})


@router.get("/async/status/{job_id}")
async def get_job_status(
    job_id: str,
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.job_id, "status": job.status.value, "error": job.error}


@router.get("/async/result/{job_id}")
async def get_job_result(
    job_id: str,
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == "running" or job.status == "pending":
        raise HTTPException(status_code=425, detail="Job still processing")
    if job.status == "error" or job.error:
        return JSONResponse({"job_id": job.job_id, "status": "error", "error": job.error}, status_code=500)
    return Response(
        content=job.result,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="report_{job.job_id}.pdf"',
        },
    )
