import asyncio
from sqlalchemy import text
from data.db import init_db, close_db, get_session_sync
from data.vector_store import store_consumption_vector, get_vectors_count
from rag.embeddings import build_vectors_for_all_sites
from config.settings import get_settings


async def main():
    settings = get_settings()
    await init_db(settings)

    session = get_session_sync()

    before = await get_vectors_count(session)
    print(f"Vectors before: {before}")

    result = await session.execute(
        text("SELECT DISTINCT EXTRACT(YEAR FROM item_date)::int AS year FROM invoice_items ORDER BY year")
    )
    years = [row[0] for row in result]
    print(f"Years to process: {years}")

    for year in years:
        print(f"Building vectors for {year}...")
        vectors = await build_vectors_for_all_sites(session, year)
        for i, vec in enumerate(vectors):
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
            if (i + 1) % 100 == 0:
                await session.commit()
        await session.commit()
        print(f"  -> {len(vectors)} vectors stored")

    after = await get_vectors_count(session)
    print(f"Vectors after: {after}")
    print("Done!")
    await session.close()
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
