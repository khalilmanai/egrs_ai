from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from rag.document_rag import query_documents
from data.document_store import get_documents_list, count_chunks

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/rag/query")
async def rag_query(
    question: str = Query(..., description="Natural language question"),
    top_k: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await query_documents(session, question, top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {type(e).__name__}: {e}")


@router.get("/rag/documents")
async def rag_documents(session: AsyncSession = Depends(get_db)):
    docs = await get_documents_list(session)
    total = await count_chunks(session)
    return {"total_chunks": total, "documents": docs}
