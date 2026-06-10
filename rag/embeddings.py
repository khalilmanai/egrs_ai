from sqlalchemy.ext.asyncio import AsyncSession
from core.consumption import get_monthly_consumption_from_invoices, get_all_sites


async def build_consumption_vector(
    monthly_data: list[dict],
    site_id: int,
    year: int,
) -> tuple[list[float], float] | None:
    month_map = {
        row["month"]: row["total_consumption_kwh"] or 0
        for row in monthly_data
        if row["site_id"] == site_id and row["year"] == year
    }
    if not month_map:
        return None
    vector = [float(month_map.get(m, 0)) for m in range(1, 13)]
    total = sum(vector)
    if total == 0:
        return None
    return (vector, total)


async def build_vectors_for_all_sites(
    session: AsyncSession,
    year: int,
) -> list[dict]:
    monthly_data = await get_monthly_consumption_from_invoices(
        session, start_year=year, end_year=year
    )
    sites_data = await get_all_sites(session)
    site_meta = {s["site_id"]: s for s in sites_data}

    vectors = []
    seen_sites = {row["site_id"] for row in monthly_data}

    for sid in seen_sites:
        result = await build_consumption_vector(monthly_data, sid, year)
        if result is None:
            continue
        vector, total = result
        meta = site_meta.get(sid, {})
        vectors.append({
            "site_id": sid,
            "year": year,
            "vector": vector,
            "total_consumption": total,
            "site_configuration": meta.get("configuration"),
            "network_type_id": meta.get("network_type_id"),
            "electrical_type": meta.get("elec_type"),
            "direction_id": meta.get("direction_id"),
        })
    return vectors
