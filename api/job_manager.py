import uuid
import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)


_jobs: dict[str, Job] = {}


def create_job() -> Job:
    job_id = uuid.uuid4().hex[:12]
    job = Job(job_id=job_id)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def run_in_background(coro):
    job = create_job()
    task = asyncio.create_task(_run_job(job, coro))
    job._task = task
    return job


async def _run_job(job: Job, coro):
    job.status = JobStatus.RUNNING
    try:
        result = await coro
        job.result = result
        job.status = JobStatus.DONE
    except Exception as e:
        logger.exception("Job %s failed", job.job_id)
        job.error = str(e)
        job.status = JobStatus.ERROR


def cleanup_old_jobs(max_age_seconds: int = 3600):
    _jobs.clear()
