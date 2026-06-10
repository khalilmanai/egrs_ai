import os
import tempfile
import httpx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import get_settings

_settings = get_settings()
OLLAMA_EMBED_MODEL = _settings.embed_model
CHUNK_SIZE = _settings.embed_chunk_size
CHUNK_OVERLAP = _settings.embed_chunk_overlap


def _extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=None)
        parts = []
        for sheet_name, sheet_df in df.items():
            parts.append(f"--- Feuille: {sheet_name} ---")
            parts.append(sheet_df.to_string(index=False))
        return "\n".join(parts)
    elif ext == ".csv":
        df = pd.read_csv(file_path)
        return df.to_string(index=False)
    elif ext == ".pdf":
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            return "\n".join(text_parts)
        except ImportError:
            try:
                import PyPDF2
                text_parts = []
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
                return "\n".join(text_parts)
            except ImportError:
                raise RuntimeError("No PDF parser available. Install pdfplumber or PyPDF2.")
    raise ValueError(f"Unsupported file type: {ext}")


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks if chunks else [text[:chunk_size]]


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    payload = {
        "model": OLLAMA_EMBED_MODEL,
        "input": texts,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.ollama_host}/api/embed",
            json=payload,
        )
        resp.raise_for_status()
        result = resp.json()
    return result.get("embeddings", [])


async def ingest_file(
    session: AsyncSession,
    file_path: str,
    filename: str | None = None,
) -> dict:
    file_text = _extract_text(file_path)
    if not file_text.strip():
        return {"status": "error", "detail": "No text could be extracted from the file"}

    chunks = _chunk_text(file_text)
    safe_name = filename or os.path.basename(file_path)

    embeddings = await _embed_texts(chunks)
    if not embeddings or len(embeddings) != len(chunks):
        return {"status": "error", "detail": f"Embedding failed: got {len(embeddings)} embeddings for {len(chunks)} chunks"}

    for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
        vector_str = "[" + ",".join(str(v) for v in emb) + "]"
        await session.execute(
            text("""
                INSERT INTO document_chunks (document_name, chunk_index, content, embedding, metadata)
                VALUES (:document_name, :chunk_index, :content, CAST(:embedding AS vector(768)), :metadata)
            """),
            {
                "document_name": safe_name,
                "chunk_index": i,
                "content": chunk_text,
                "embedding": vector_str,
                "metadata": '{}',
            },
        )

    await session.commit()
    return {
        "status": "success",
        "filename": safe_name,
        "chunks_created": len(chunks),
        "embedding_model": OLLAMA_EMBED_MODEL,
    }


async def ingest_upload(
    session: AsyncSession,
    file_bytes: bytes,
    filename: str,
) -> dict:
    ext = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return await ingest_file(session, tmp_path, filename=filename)
    finally:
        os.unlink(tmp_path)


async def get_total_chunks(session: AsyncSession) -> int:
    r = await session.execute(text("SELECT COUNT(*) FROM document_chunks"))
    return r.scalar() or 0
