import asyncio
from core.db import init_db, close_db, get_session_sync
from config.settings import get_settings
from report.pdf_generator import (
    generate_global_forecast_pdf,
    generate_site_forecast_pdf,
    generate_yearly_analysis_pdf,
)


async def main():
    settings = get_settings()
    await init_db(settings)

    # 1. Global forecast 2026
    print("=== Generating global forecast 2026 ===")
    s1 = get_session_sync()
    try:
        pdf = await generate_global_forecast_pdf(s1, 2026)
        with open("global_forecast_2026.pdf", "wb") as f:
            f.write(pdf)
        print(f"  OK: {len(pdf)} bytes")
    except Exception as e:
        print(f"  FAIL: {e}")
    finally:
        await s1.close()

    # 2. Yearly analysis 2025
    print("=== Generating yearly analysis 2025 ===")
    s2 = get_session_sync()
    try:
        pdf = await generate_yearly_analysis_pdf(s2, 2025)
        with open("yearly_analysis_2025.pdf", "wb") as f:
            f.write(pdf)
        print(f"  OK: {len(pdf)} bytes")
    except Exception as e:
        print(f"  FAIL: {e}")
    finally:
        await s2.close()

    # 3. Site forecast TUN_0091 for 2026
    print("=== Generating site forecast TUN_0091 2026 ===")
    s3 = get_session_sync()
    try:
        pdf = await generate_site_forecast_pdf(s3, "TUN_0091", 2026)
        with open("site_forecast_TUN_0091.pdf", "wb") as f:
            f.write(pdf)
        print(f"  OK: {len(pdf)} bytes")
    except Exception as e:
        print(f"  FAIL: {e}")
    finally:
        await s3.close()

    await close_db()
    print("\n=== All done ===")


asyncio.run(main())
