import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import get_settings
from rag.document_rag import OLLAMA_EMBED_MODEL


async def _embed_query(query: str) -> list[float]:
    settings = get_settings()
    payload = {
        "model": OLLAMA_EMBED_MODEL,
        "input": [query],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.ollama_host}/api/embed",
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()
        embs = result.get("embeddings", [])
        return embs[0] if embs else []
    except Exception:
        return []


async def search_documents(
    session: AsyncSession,
    query: str,
    limit: int = 10,
    metric: str = "cosine",
) -> list[dict]:
    query_vec = await _embed_query(query)
    if not query_vec:
        return []

    operator = {"cosine": "<=>", "l2": "<->", "inner": "<#>"}.get(metric, "<=>")
    vector_str = "[" + ",".join(str(v) for v in query_vec) + "]"

    try:
        r = await session.execute(
            text(f"""
                SELECT doc_id, filename, chunk_index, content,
                       (embedding {operator} CAST(:query_vec AS vector(768))) AS distance
                FROM document_chunks
                ORDER BY distance
                LIMIT :limit
            """),
            {"query_vec": vector_str, "limit": limit},
        )
        return [dict(row._mapping) for row in r]
    except Exception:
        return []


async def get_context_for_report(
    session: AsyncSession,
    query: str,
    max_chunks: int = 8,
) -> str:
    try:
        results = await search_documents(session, query, limit=max_chunks)
        if not results:
            return ""
        parts = []
        for r in results:
            parts.append(f"[{r['filename']} - chunk {r['chunk_index']}] (dist: {r['distance']:.4f})\n{r['content']}")
        return "\n\n".join(parts)
    except Exception:
        return ""
