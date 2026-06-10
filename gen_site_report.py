import asyncio
from core.db import init_db, close_db, get_session_sync
from config.settings import get_settings
from report.pdf_generator import generate_site_forecast_pdf


async def main():
    settings = get_settings()
    await init_db(settings)

    session = get_session_sync()
    try:
        pdf = await generate_site_forecast_pdf(session, "TUN_0125", 2027)
        with open("site_forecast_TUN_0125.pdf", "wb") as f:
            f.write(pdf)
        print(f"Site forecast: {len(pdf)} bytes -> site_forecast_TUN_0125.pdf")
    finally:
        await session.close()
    await close_db()


asyncio.run(main())
