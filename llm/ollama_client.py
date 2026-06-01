import json
import httpx
from config.settings import get_settings


async def generate_structured_report(
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
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 4096,
        },
    }
    if json_schema:
        payload["format"] = json_schema

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(
                f"{settings.ollama_host}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Ollama HTTP {e.response.status_code}", "raw": str(e)}
    except httpx.RequestError as e:
        return {"error": f"Ollama connection failed: {type(e).__name__}: {e}", "raw": str(e)}
    except Exception as e:
        import traceback
        return {"error": f"Unexpected Ollama error: {type(e).__name__}: {e}", "raw": traceback.format_exc()[:1000]}

    raw = result.get("response", "{}")
    if json_schema:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "LLM returned invalid JSON", "raw": raw}
    return {"text": raw}


async def check_ollama_health() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return any(settings.ollama_model in m.get("name", "") for m in models)
    except Exception:
        return False
