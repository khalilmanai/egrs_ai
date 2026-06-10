from sqlalchemy.ext.asyncio import AsyncSession
from core.vector_store import search_similar_vectors
from analytics.features import build_query_vector


async def find_similar_sites(
    session: AsyncSession,
    consumption_pattern: list[float],
    limit: int = 20,
) -> list[dict]:
    return await search_similar_vectors(session, consumption_pattern, limit=limit)


async def retrieve_context_for_new_sites(
    session: AsyncSession,
    new_sites: list[dict],
) -> dict:
    all_similar = []
    for site_input in new_sites:
        query_vec = build_query_vector(site_input)
        similar = await find_similar_sites(session, query_vec, limit=10)
        avg_cons = (
            sum(s["total_consumption"] or 0 for s in similar) / len(similar)
            if similar else 0
        )
        all_similar.append({
            "input_site": site_input,
            "similar_sites": similar,
            "avg_consumption": avg_cons,
        })
    return {
        "total_new_sites": len(new_sites),
        "avg_predicted_consumption": sum(
            s["avg_consumption"] for s in all_similar
        ),
        "site_analyses": all_similar,
    }
