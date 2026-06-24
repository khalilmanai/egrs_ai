import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.sql_filter import site_filter

logger = logging.getLogger(__name__)


async def get_alert_summary(session: AsyncSession) -> dict:
    r = await session.execute(text(f"""
        SELECT a.type, a.severity, a.status, a.category, COUNT(*) as cnt
        FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE {site_filter('s')}
        GROUP BY a.type, a.severity, a.status, a.category
        ORDER BY cnt DESC
    """))
    breakdown = [dict(row._mapping) for row in r]
    r2 = await session.execute(text(f"""
        SELECT COUNT(*) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE {site_filter('s')}
    """))
    return {"total_alerts": r2.scalar() or 0, "breakdown": breakdown}


async def get_sfr_analysis(session: AsyncSession) -> dict:
    r = await session.execute(text(f"""
        SELECT a.site_id, s."SiteCode", s."SiteName",
               s."DirectionId", a.description, a.created_at
        FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.type = 'SFR'
          AND {site_filter('s')}
        ORDER BY a.created_at DESC
    """))
    alerts = [dict(row._mapping) for row in r]
    r2 = await session.execute(text(f"""
        SELECT COUNT(*) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.type = 'SFR' AND {site_filter('s')}
    """))
    total_sfr = r2.scalar() or 0
    r3 = await session.execute(text(f"""
        SELECT COUNT(DISTINCT a.site_id) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.type = 'SFR' AND {site_filter('s')}
    """))
    sites_affected = r3.scalar() or 0
    return {
        "total_sfr": total_sfr,
        "sites_affected": sites_affected,
        "alerts": alerts,
    }


async def get_alerts_by_site(session: AsyncSession, site_id: int) -> list[dict]:
    r = await session.execute(
        text(f"""
            SELECT a.*, s."SiteCode", s."SiteName"
            FROM alerts a
            JOIN sites s ON s."SiteId" = a.site_id
            WHERE a.site_id = :sid
              AND {site_filter('s')}
            ORDER BY a.created_at DESC
        """),
        {"sid": site_id},
    )
    return [dict(row._mapping) for row in r]
