import json
import asyncio
import logging
import httpx
from config.settings import get_settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = httpx.AsyncClient(
            timeout=settings.ollama_timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


class LLMError(Exception):
    pass


async def generate_structured(
    system_prompt: str,
    user_prompt: str,
    json_schema: dict | None = None,
) -> dict:
    settings = get_settings()
    payload = {
        "model": settings.ollama_model,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 8192,
        },
    }
    if json_schema:
        payload["format"] = json_schema

    client = await get_client()
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            response = await client.post(
                f"{settings.ollama_host}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            raw = result.get("response", "{}")
            if json_schema:
                return json.loads(raw)
            return {"text": raw}
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning("LLM HTTP error (attempt %d/2): %s", attempt + 1, e)
            if attempt == 0:
                await asyncio.sleep(2)
        except (httpx.RequestError, json.JSONDecodeError) as e:
            last_error = e
            logger.warning("LLM request error (attempt %d/2): %s", attempt + 1, e)
            if attempt == 0:
                await asyncio.sleep(2)

    raise LLMError(f"LLM call failed after 2 attempts: {last_error}")


async def health_check() -> bool:
    settings = get_settings()
    try:
        client = await get_client()
        resp = await client.get(f"{settings.ollama_host}/api/tags")
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return any(settings.ollama_model in m.get("name", "") for m in models)
    except Exception:
        return False
