from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_OPERATORS = {
    "cosine": "<=>",
    "l2": "<->",
    "inner": "<#>",
}


async def store_consumption_vector(
    session: AsyncSession,
    site_id: int,
    year: int,
    vector: list[float],
    total_consumption: float,
    site_configuration: str | None = None,
    network_type_id: int | None = None,
    electrical_type: str | None = None,
    direction_id: int | None = None,
):
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"
    query = text("""
        INSERT INTO consumption_vectors
            (site_id, year, vector, total_consumption, site_configuration,
             network_type_id, electrical_type, direction_id)
        VALUES (:site_id, :year, CAST(:vector AS vector), :total, :config,
                :network_type, :elec_type, :direction)
        ON CONFLICT (site_id, year)
        DO UPDATE SET
            vector = CAST(:vector AS vector),
            total_consumption = :total,
            updated_at = NOW()
    """)
    await session.execute(query, {
        "site_id": site_id,
        "year": year,
        "vector": vector_str,
        "total": total_consumption,
        "config": site_configuration,
        "network_type": network_type_id,
        "elec_type": electrical_type,
        "direction": direction_id,
    })
    await session.commit()


async def search_similar_vectors(
    session: AsyncSession,
    query_vector: list[float],
    limit: int = 20,
    metric: str = "cosine",
) -> list[dict]:
    operator = _OPERATORS.get(metric, "<=>")
    query = text(f"""
        SELECT
            cv.site_id,
            cv.year,
            cv.total_consumption,
            cv.site_configuration,
            cv.network_type_id,
            cv.electrical_type,
            cv.direction_id,
            s."SiteName" as site_name,
            s."SiteCode" as site_code,
            s."Configuration" as configuration,
            s."ElecType" as elec_type,
            (cv.vector {operator} CAST(:query_vec AS vector)) AS distance
        FROM consumption_vectors cv
        JOIN sites s ON s."SiteId" = cv.site_id
        WHERE cv.vector IS NOT NULL
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        ORDER BY distance
        LIMIT :limit
    """)
    result = await session.execute(query, {
        "query_vec": str(query_vector),
        "limit": limit,
    })
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


async def delete_vectors_for_site(session: AsyncSession, site_id: int):
    await session.execute(
        text("DELETE FROM consumption_vectors WHERE site_id = :sid"),
        {"sid": site_id},
    )
    await session.commit()


async def get_vectors_count(session: AsyncSession) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM consumption_vectors")
    )
    return result.scalar()


async def get_years_with_vectors(session: AsyncSession) -> list[int]:
    result = await session.execute(
        text("SELECT DISTINCT year FROM consumption_vectors ORDER BY year")
    )
    return [row[0] for row in result]
