"""
Full rebuild of the consumption_vectors index from historical data.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.vector_store import store_consumption_vector, get_years_with_vectors
from rag.embeddings import build_vectors_for_all_sites


async def rebuild_vector_index(
    session: AsyncSession,
    years: list[int] | None = None,
):
    """Rebuild consumption vectors for given years (or all available years)."""
    if years is None:
        result = await session.execute(
            text("SELECT DISTINCT EXTRACT(YEAR FROM item_date)::int AS year "
                 "FROM invoice_items ORDER BY year")
        )
        years = [row[0] for row in result]

    total = 0
    for year in years:
        vectors = await build_vectors_for_all_sites(session, year)
        for vec in vectors:
            await store_consumption_vector(
                session=session,
                site_id=vec["site_id"],
                year=vec["year"],
                vector=vec["vector"],
                total_consumption=vec["total_consumption"],
                site_configuration=vec["site_configuration"],
                network_type_id=vec["network_type_id"],
                electrical_type=vec["electrical_type"],
                direction_id=vec["direction_id"],
            )
        total += len(vectors)
    return {"years_rebuilt": years, "total_vectors": total}
