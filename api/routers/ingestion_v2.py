import os
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from rag.document_rag import ingest_upload, get_total_chunks
from api.auth.dependencies import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".pdf", ".txt"}


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_roles("ADMINISTRATEUR", "MANAGER")),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    result = await ingest_upload(session, contents, file.filename)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("detail", "Ingestion failed"))

    total = await get_total_chunks(session)
    result["total_chunks_in_db"] = total
    return result


@router.get("/status")
async def ingestion_status(session: AsyncSession = Depends(get_db)):
    total = await get_total_chunks(session)
    return {"total_chunks": total, "embedding_model": "nomic-embed-text", "vector_dimension": 768}
