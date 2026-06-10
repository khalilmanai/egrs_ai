import statistics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def compute_yoy_change(session: AsyncSession, year: int) -> dict:
    r = await session.execute(
        text("""
            SELECT curr.site_id,
                   curr.total_consumption as current_kwh,
                   prev.total_consumption as previous_kwh
            FROM consumption_vectors curr
            JOIN consumption_vectors prev
                ON prev.site_id = curr.site_id AND prev.year = curr.year - 1
            JOIN sites s ON s."SiteId" = curr.site_id
            WHERE curr.year = :yr
              AND curr.total_consumption IS NOT NULL
              AND prev.total_consumption IS NOT NULL
              AND prev.total_consumption > 0
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        """),
        {"yr": year},
    )
    rows = [dict(row._mapping) for row in r]
    if not rows:
        return {"changes": [], "stats": {}}

    total_current = sum(r["current_kwh"] for r in rows)
    total_previous = sum(r["previous_kwh"] for r in rows)
    overall_pct = round((total_current - total_previous) / total_previous * 100, 1) if total_previous else 0

    changes = []
    for row in rows:
        prev = row["previous_kwh"]
        curr = row["current_kwh"]
        pct_change = (curr - prev) / prev * 100
        changes.append({
            "site_id": row["site_id"],
            "previous_kwh": round(prev, 2),
            "current_kwh": round(curr, 2),
            "pct_change": round(pct_change, 1),
        })

    changes.sort(key=lambda x: abs(x["pct_change"]), reverse=True)

    return {
        "overall_yoy_pct": overall_pct,
        "total_current_kwh": round(total_current, 0),
        "total_previous_kwh": round(total_previous, 0),
        "total_sites": len(changes),
        "avg_abs_change_pct": round(
            statistics.mean([abs(c["pct_change"]) for c in changes]), 1
        ) if changes else 0,
        "site_changes": changes,
    }


async def compute_monthly_trends(session: AsyncSession, year: int) -> list[dict]:
    r = await session.execute(
        text("""
            SELECT
                EXTRACT(MONTH FROM ii.item_date)::int AS month,
                s."ElecType" AS elec_type,
                SUM(((ii.final_sale / 1000.0) / 1.19)) /
                NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt
                       ELSE tc.kwh_price_mt END, 0) AS total_kwh,
                SUM(ii.final_sale) / 1000.0 AS total_cost_tnd
            FROM invoice_items ii
            JOIN sites s ON s."SiteId" = ii.site_id
            CROSS JOIN tariff_config tc
            WHERE ii.item_type = 0
              AND EXTRACT(YEAR FROM ii.item_date) = :yr
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
            GROUP BY EXTRACT(MONTH FROM ii.item_date), s."ElecType",
                     tc.kwh_price_bt, tc.kwh_price_mt
            ORDER BY month
        """),
        {"yr": year},
    )
    rows = [dict(row._mapping) for row in r]
    for row in rows:
        for k in ("total_kwh", "total_cost_tnd"):
            if row.get(k) is not None:
                row[k] = float(row[k])

    months_data = {m: {"kwh": 0, "cost_tnd": 0} for m in range(1, 13)}
    for row in rows:
        m = row["month"]
        months_data[m]["kwh"] += row.get("total_kwh", 0)
        months_data[m]["cost_tnd"] += row.get("total_cost_tnd", 0)

    result = []
    for m in range(1, 13):
        d = months_data[m]
        result.append({
            "month": m,
            "kwh": round(d["kwh"], 0),
            "cost_tnd": round(d["cost_tnd"], 2),
        })

    return result
