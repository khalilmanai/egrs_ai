from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_alert_summary(session: AsyncSession) -> dict:
    r = await session.execute(text("""
        SELECT a.type, a.severity, a.status, a.category, COUNT(*) as cnt
        FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        GROUP BY a.type, a.severity, a.status, a.category
        ORDER BY cnt DESC
    """))
    breakdown = [dict(row._mapping) for row in r]
    r2 = await session.execute(text("""
        SELECT COUNT(*) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE s."DirectionId" = 1 AND s."StatusId" IN (1,3)
    """))
    total = r2.scalar()
    return {"total_alerts": total, "breakdown": breakdown}


async def get_sfr_analysis(session: AsyncSession) -> dict:
    r = await session.execute(text("""
        SELECT a.site_id, s."SiteCode", s."SiteName",
               s."DirectionId", a.description, a.created_at
        FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.type = 'SFR'
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        ORDER BY a.created_at DESC
    """))
    alerts = [dict(row._mapping) for row in r]
    r2 = await session.execute(text("""
        SELECT COUNT(*) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.type = 'SFR' AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
    """))
    total_sfr = r2.scalar()
    r3 = await session.execute(text("""
        SELECT COUNT(DISTINCT a.site_id) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.type = 'SFR' AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
    """))
    sites_affected = r3.scalar()
    return {
        "alert_type": "SFR (Sans Facturation Réelle)",
        "total_sfr": total_sfr,
        "sites_affected": sites_affected,
        "alerts": alerts,
    }


async def get_alerts_by_site(session: AsyncSession, site_id: int) -> list[dict]:
    r = await session.execute(
        text("""
            SELECT a.*, s."SiteCode", s."SiteName"
            FROM alerts a
            JOIN sites s ON s."SiteId" = a.site_id
            WHERE a.site_id = :sid
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
            ORDER BY a.created_at DESC
        """),
        {"sid": site_id},
    )
    return [dict(row._mapping) for row in r]


async def get_alert_trend(session: AsyncSession) -> dict:
    r = await session.execute(text("""
        SELECT DATE_TRUNC('month', a.created_at)::date AS month,
               a.type, COUNT(*) AS cnt
        FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        GROUP BY month, a.type
        ORDER BY month DESC, a.type
    """))
    rows = [dict(row._mapping) for row in r]
    return {"monthly_trend": rows}


async def get_recent_alerts(session: AsyncSession, limit: int = 20) -> list[dict]:
    r = await session.execute(
        text("""
            SELECT a.id, a.type, a.severity, a.status, a.category,
                   a.site_id, s."SiteCode", s."SiteName",
                   a.description, a.created_at, a.savings
            FROM alerts a
            JOIN sites s ON s."SiteId" = a.site_id
            WHERE s."DirectionId" = 1 AND s."StatusId" IN (1,3)
            ORDER BY a.created_at DESC
            LIMIT :lim
        """),
        {"lim": limit},
    )
    return [dict(row._mapping) for row in r]
