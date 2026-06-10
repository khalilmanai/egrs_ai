import asyncio
from core.db import init_db, close_db, get_session_sync
from config.settings import get_settings
from sqlalchemy import text


async def main():
    settings = get_settings()
    await init_db(settings)
    session = get_session_sync()
    try:
        r = await session.execute(
            text("""
                SELECT s."SiteCode", COUNT(*) as cnt
                FROM invoice_items ii
                JOIN sites s ON s."SiteId" = ii.site_id
                WHERE s."DirectionId" = 1 AND s."StatusId" IN (1,3)
                  AND ii.item_type = 0
                GROUP BY s."SiteCode"
                HAVING COUNT(*) >= 24
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)
        )
        print("Sites with most invoice data:")
        for row in r:
            print(f"  {row[0]} ({row[1]} invoices)")
    finally:
        await session.close()
    await close_db()


asyncio.run(main())
