import json
import re
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from data.document_store import store_chunk, search_similar_chunks, ensure_document_tables

OLLAMA_URL = "http://localhost:11434/api/embed"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
EMBED_MODEL = "qwen2.5:3b"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


async def embed_text(text: str) -> list[float]:
    r = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": text}, timeout=30)
    r.raise_for_status()
    data = r.json()
    embeddings = data.get("embeddings", [])
    if not embeddings:
        raise ValueError("No embedding returned")
    return embeddings[0]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    buffer = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(buffer) + len(para) < chunk_size:
            buffer += "\n\n" + para if buffer else para
        else:
            if buffer:
                chunks.append(buffer)
            buffer = para
    if buffer:
        chunks.append(buffer)

    if len(chunks) <= 1:
        return chunks if chunks else []

    merged = []
    for i, chunk in enumerate(chunks):
        if i > 0 and len(chunk) < chunk_size // 2 and merged:
            merged[-1] += "\n\n" + chunk
        else:
            merged.append(chunk)

    result = []
    for chunk in merged:
        if len(chunk) > chunk_size * 1.5:
            words = chunk.split()
            for i in range(0, len(words), chunk_size // 2):
                sub = " ".join(words[i:i + chunk_size])
                if sub:
                    result.append(sub)
        else:
            result.append(chunk)
    return result


def extract_text_from_excel(filepath: str) -> str:
    import pandas as pd
    xls = pd.ExcelFile(filepath)
    parts = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        parts.append(f"=== Sheet: {sheet_name} ===")
        parts.append(df.to_string(index=False))
    return "\n\n".join(parts)


def extract_text_from_file(filepath: str) -> str:
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    if ext == "txt":
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    elif ext in ("xlsx", "xls"):
        return extract_text_from_excel(filepath)
    elif ext == "csv":
        import pandas as pd
        df = pd.read_csv(filepath)
        return df.to_string(index=False)
    elif ext == "pdf":
        try:
            import pymupdf
            doc = pymupdf.open(filepath)
            return "\n\n".join(page.get_text() for page in doc)
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(filepath) as pdf:
                    return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
            except ImportError:
                raise ValueError("No PDF library available. Install pymupdf or pdfplumber.")
    else:
        raise ValueError(f"Unsupported file type: .{ext}")


async def ingest_document(
    session: AsyncSession,
    filepath: str,
    document_name: str | None = None,
) -> dict:
    await ensure_document_tables(session)

    if document_name is None:
        document_name = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

    text_content = extract_text_from_file(filepath)
    chunks = chunk_text(text_content)

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        embedding = await embed_text(chunk)
        await store_chunk(session, document_name, i, chunk, embedding)

    return {
        "document_name": document_name,
        "chunks_indexed": total,
        "characters": len(text_content),
    }


async def query_documents(
    session: AsyncSession,
    question: str,
    top_k: int = 5,
) -> dict:
    await ensure_document_tables(session)

    question_embedding = await embed_text(question)
    similar = await search_similar_chunks(session, question_embedding, limit=top_k)

    if not similar:
        return {
            "answer": "No relevant documents found to answer this question.",
            "sources": [],
        }

    context = "\n\n".join(
        f"[Document: {s['document_name']}, Section {s['chunk_index']}]\n{s['content']}"
        for s in similar
    )

    system_prompt = """You are an AI assistant for Orange Tunisie's EGRS platform.
Answer questions based ONLY on the provided context. If the context doesn't contain enough information, say so.
Cite the source document name in your answer. Be concise and factual."""

    user_prompt = f"""## Context from internal documents:
{context}

## Question:
{question}

Answer the question using only the context above. Include specific numbers, dates, and document references where applicable."""

    r = requests.post(OLLAMA_CHAT_URL, json={
        "model": EMBED_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }, timeout=60)
    r.raise_for_status()
    data = r.json()
    answer = data.get("message", {}).get("content", "")

    return {
        "answer": answer,
        "sources": [
            {
                "document_name": s["document_name"],
                "chunk_index": s["chunk_index"],
                "similarity": s["similarity"],
                "content_preview": s["content"][:200],
            }
            for s in similar
        ],
    }
