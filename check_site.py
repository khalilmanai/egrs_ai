import asyncio
from core.db import init_db, close_db, get_session_sync
from config.settings import get_settings
from core.sql_filter import site_filter
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
                WHERE {site_filter('s')}
                  AND ii.item_type = 0
                  AND s."SiteCode" = 'TUN_0091'
                GROUP BY s."SiteCode"
            """)
        )
        row = r.fetchone()
        if row:
            print(f"TUN_0091: {row[1]} invoices")
        else:
            print("TUN_0091 not found or no invoice data")

        r2 = await session.execute(
            text("""
                SELECT MIN(EXTRACT(YEAR FROM item_date)), MAX(EXTRACT(YEAR FROM item_date))
                FROM invoice_items ii
                JOIN sites s ON s."SiteId" = ii.site_id
                WHERE s."SiteCode" = 'TUN_0091'
            """)
        )
        row2 = r2.fetchone()
        if row2:
            print(f"Year range: {row2[0]} - {row2[1]}")
    finally:
        await session.close()
    await close_db()


asyncio.run(main())
