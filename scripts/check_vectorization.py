import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import init_db, close_db, get_session_sync
from config.settings import get_settings


async def check_vectorization_status():
    """Check the current status of vectorization and identify missing vectors."""
    settings = get_settings()
    await init_db(settings)
    
    session = get_session_sync()
    
    try:
        # Get total sites
        result = await session.execute(text('SELECT COUNT(*) FROM "sites"'))
        total_sites = result.scalar()
        print(f"Total sites in database: {total_sites}")
        
        # Get sites with invoice data
        result = await session.execute(text('SELECT COUNT(DISTINCT site_id) FROM invoice_items WHERE item_type = 0'))
        sites_with_data = result.scalar()
        print(f"Sites with invoice data: {sites_with_data}")
        
        # Get sites with vectors
        result = await session.execute(text('SELECT COUNT(DISTINCT site_id) FROM consumption_vectors'))
        sites_with_vectors = result.scalar()
        print(f"Sites with vectors: {sites_with_vectors}")
        
        # Get total vectors
        result = await session.execute(text('SELECT COUNT(*) FROM consumption_vectors'))
        total_vectors = result.scalar()
        print(f"Total vectors: {total_vectors}")
        
        # Get years covered
        result = await session.execute(text('SELECT COUNT(DISTINCT year) FROM consumption_vectors'))
        years_covered = result.scalar()
        print(f"Years covered: {years_covered}")
        
        # Check for sites with data but no vectors
        result = await session.execute(text('''
            SELECT COUNT(DISTINCT s."SiteId") 
            FROM "sites" s
            JOIN invoice_items ii ON ii.site_id = s."SiteId"
            WHERE ii.item_type = 0
            AND s."SiteId" NOT IN (SELECT site_id FROM consumption_vectors)
        '''))
        sites_missing_vectors = result.scalar()
        print(f"Sites with data but missing vectors: {sites_missing_vectors}")
        
        # Check for sites without data but with vectors
        result = await session.execute(text('''
            SELECT COUNT(DISTINCT s."SiteId") 
            FROM "sites" s
            LEFT JOIN invoice_items ii ON ii.site_id = s."SiteId" AND ii.item_type = 0
            WHERE ii.site_id IS NULL
            AND s."SiteId" IN (SELECT site_id FROM consumption_vectors)
        '''))
        sites_without_data_but_with_vectors = result.scalar()
        print(f"Sites without data but with vectors: {sites_without_data_but_with_vectors}")
        
        # Check for empty vectors
        result = await session.execute(text('SELECT COUNT(*) FROM consumption_vectors WHERE vector IS NULL'))
        null_vectors = result.scalar()
        print(f"Null vectors: {null_vectors}")
        
        # Check for years without vectors
        result = await session.execute(text('''
            SELECT COUNT(DISTINCT EXTRACT(YEAR FROM item_date)::int) 
            FROM invoice_items 
            WHERE item_type = 0
            AND EXTRACT(YEAR FROM item_date)::int NOT IN (SELECT year FROM consumption_vectors)
        '''))
        years_without_vectors = result.scalar()
        print(f"Years without vectors: {years_without_vectors}")
        
    finally:
        await session.close()
        await close_db()


if __name__ == "__main__":
    asyncio.run(check_vectorization_status())
