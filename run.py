import asyncio
import sys
import uvicorn
from config.settings import get_settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    settings = get_settings()
    if settings.debug:
        print("WARNING: debug mode enables uvicorn reloader. PID tracking only tracks the supervisor process, not workers.")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
