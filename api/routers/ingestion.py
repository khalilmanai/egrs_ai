import os
import tempfile
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from rag.document_rag import ingest_document
from data.document_store import get_documents_list, delete_document, count_chunks

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".txt", ".pdf"}


@router.post("/new-sites")
async def ingest_new_sites(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Use .xlsx, .xls, or .csv",
        )

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        if ext == ".csv":
            df = pd.read_csv(tmp_path)
        else:
            df = pd.read_excel(tmp_path)

        required = {"configuration", "network_type", "electrical_type",
                     "direction_id", "estimated_consumption"}
        df.columns = df.columns.str.lower().str.strip()
        missing = required - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {', '.join(missing)}",
            )

        records = df.to_dict(orient="records")
        total_sites = sum(r.get("site_count", 1) for r in records)

        return {
            "status": "parsed",
            "total_rows": len(records),
            "total_sites": total_sites,
            "sites": records,
            "message": f"Parsed {len(records)} configurations ({total_sites} total sites). "
                       f"Use POST /reports/budget-forecast with this data.",
        }
    finally:
        os.unlink(tmp_path)


@router.post("/document")
async def ingest_document_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".txt", ".pdf", ".xlsx", ".xls", ".csv"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file: {ext}")

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = await ingest_document(session, tmp_path, file.filename)
        return {"status": "indexed", **result}
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    finally:
        os.unlink(tmp_path)


@router.get("/documents")
async def list_documents(session: AsyncSession = Depends(get_db)):
    docs = await get_documents_list(session)
    total = await count_chunks(session)
    return {"total_chunks": total, "documents": docs}


@router.delete("/documents/{document_name:path}")
async def remove_document(document_name: str, session: AsyncSession = Depends(get_db)):
    await delete_document(session, document_name)
    return {"status": "deleted", "document_name": document_name}
