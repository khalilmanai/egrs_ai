import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_document_tables(session: AsyncSession):
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id SERIAL PRIMARY KEY,
            document_name VARCHAR(500) NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding vector(2048),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc_name
        ON document_chunks (document_name)
    """))
    await session.commit()


async def store_chunk(
    session: AsyncSession,
    document_name: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    metadata: dict | None = None,
):
    vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
    await session.execute(text("""
        INSERT INTO document_chunks
            (document_name, chunk_index, content, embedding, metadata)
        VALUES (:name, :idx, :content, CAST(:vec AS vector), :meta)
    """), {
        "name": document_name,
        "idx": chunk_index,
        "content": content,
        "vec": vector_str,
        "meta": json.dumps(metadata or {}),
    })
    await session.commit()


async def search_similar_chunks(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int = 5,
    similarity_threshold: float = 0.5,
) -> list[dict]:
    result = await session.execute(text("""
        SELECT
            id, document_name, chunk_index, content, metadata,
            (embedding <=> CAST(:query AS vector)) AS distance
        FROM document_chunks
        WHERE embedding IS NOT NULL
          AND (embedding <=> CAST(:query AS vector)) < :threshold
        ORDER BY distance
        LIMIT :lim
    """), {
        "query": str(query_embedding),
        "threshold": 1.0 - similarity_threshold,
        "lim": limit,
    })
    rows = []
    for row in result:
        d = dict(row._mapping)
        d["similarity"] = round(1.0 - d["distance"], 4)
        del d["distance"]
        rows.append(d)
    return rows


async def get_documents_list(session: AsyncSession) -> list[dict]:
    result = await session.execute(text("""
        SELECT document_name, COUNT(*) as chunk_count,
               MIN(created_at) as first_indexed,
               MAX(created_at) as last_indexed
        FROM document_chunks
        GROUP BY document_name
        ORDER BY last_indexed DESC
    """))
    return [dict(row._mapping) for row in result]


async def delete_document(session: AsyncSession, document_name: str):
    await session.execute(
        text("DELETE FROM document_chunks WHERE document_name = :name"),
        {"name": document_name},
    )
    await session.commit()


async def count_chunks(session: AsyncSession) -> int:
    result = await session.execute(text("SELECT COUNT(*) FROM document_chunks"))
    return result.scalar()
