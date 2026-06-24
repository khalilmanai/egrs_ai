import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import init_db, close_db, get_session_sync
from config.settings import get_settings


async def check_sites_with_vectors_no_data():
    """Check sites that have vectors but no invoice data."""
    settings = get_settings()
    await init_db(settings)
    
    session = get_session_sync()
    
    try:
        # Get sites with vectors but no invoice data
        result = await session.execute(text('''
            SELECT s."SiteId", s."SiteCode", s."SiteName", s."DirectionId", s."StatusId"
            FROM "sites" s
            WHERE s."SiteId" IN (SELECT site_id FROM consumption_vectors)
            AND s."SiteId" NOT IN (SELECT site_id FROM invoice_items WHERE item_type = 0)
            ORDER BY s."SiteId"
        '''))
        
        sites = result.fetchall()
        print(f"\nSites with vectors but no invoice data: {len(sites)}")
        print("\nSite Details:")
        print("-" * 80)
        for site in sites:
            print(f"Site ID: {site[0]:5d} | Code: {site[1]:10s} | Name: {site[2]:30s} | Direction: {site[3]:2d} | Status: {site[4]:2d}")
        
    finally:
        await session.close()
        await close_db()


if __name__ == "__main__":
    asyncio.run(check_sites_with_vectors_no_data())
