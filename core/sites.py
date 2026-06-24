import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.column_utils import normalize_query_result
from core.sql_filter import site_filter, site_filter_no_alias

logger = logging.getLogger(__name__)


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
              AND {site_filter_no_alias()}
            LIMIT 1
        """),
        {"code": site_code},
    )
    row = r.fetchone()
    if not row:
        return None
    result = {
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
    return normalize_query_result(result)


async def get_site_id_by_code(session: AsyncSession, site_code: str) -> int | None:
    r = await session.execute(
        text(f"""SELECT "SiteId" FROM sites WHERE "SiteCode" = :code
                  AND {site_filter_no_alias()}"""),
        {"code": site_code},
    )
    row = r.fetchone()
    return row[0] if row else None


async def get_site_count(session: AsyncSession) -> int:
    r = await session.execute(text(f"""
        SELECT COUNT(*) FROM sites
        WHERE {site_filter_no_alias()}
    """))
    return r.scalar() or 0
