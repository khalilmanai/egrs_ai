import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from api.job_manager import run_in_background, get_job
from core.db import get_session_sync
from api.auth.dependencies import require_roles
from ml.forecasting.trainer import run_training_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/train", tags=["Training"])


@router.post("", status_code=202)
async def train_model(
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    async def _train():
        session = get_session_sync()
        try:
            return await run_training_pipeline(session)
        finally:
            await session.close()

    job = run_in_background(_train())
    return JSONResponse({"job_id": job.job_id, "status": job.status.value})


@router.get("/status/{job_id}")
async def get_training_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "error": job.error,
    }


@router.get("/result/{job_id}")
async def get_training_result(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == "running" or job.status == "pending":
        raise HTTPException(status_code=425, detail="Job still processing")
    if job.status == "error":
        return JSONResponse(
            {"job_id": job.job_id, "status": "error", "error": job.error},
            status_code=500,
        )
    return JSONResponse({
        "job_id": job.job_id,
        "status": "done",
        "result": job.result,
    })
