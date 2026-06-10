from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_site_by_code(session: AsyncSession, site_code: str) -> dict | None:
    r = await session.execute(
        text("""
            SELECT "SiteId", "SiteCode", "SiteName", "Configuration",
                   "ElecType", "DirectionId", "NetworkTypeId",
                   "SharingType", "SharingMode", "IsSharing",
                   "IsSolar", "EstimatedConsumption", "MaxConsumption",
                   "StatusId"
            FROM sites
            WHERE "SiteCode" = :code
              AND "DirectionId" = 1 AND "StatusId" IN (1,3)
            LIMIT 1
        """),
        {"code": site_code},
    )
    row = r.fetchone()
    if not row:
        return None
    return {
        "site_id": row[0],
        "site_code": row[1],
        "site_name": row[2],
        "configuration": row[3],
        "elec_type": row[4],
        "direction_id": row[5],
        "network_type_id": row[6],
        "sharing_type": row[7],
        "sharing_mode": row[8],
        "is_sharing": bool(row[9]),
        "is_solar": bool(row[10]),
        "estimated_consumption": float(row[11]) if row[11] else 0,
        "max_consumption": float(row[12]) if row[12] else 0,
        "status_id": row[13],
    }


async def get_site_id_by_code(session: AsyncSession, site_code: str) -> int | None:
    r = await session.execute(
        text("""SELECT "SiteId" FROM sites WHERE "SiteCode" = :code
                  AND "DirectionId" = 1 AND "StatusId" IN (1,3)"""),
        {"code": site_code},
    )
    row = r.fetchone()
    return row[0] if row else None


async def get_site_count(session: AsyncSession) -> int:
    r = await session.execute(text("""
        SELECT COUNT(*) FROM sites
        WHERE "DirectionId" = 1 AND "StatusId" IN (1,3)
    """))
    return r.scalar() or 0
