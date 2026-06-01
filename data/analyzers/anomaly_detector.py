import statistics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def detect_consumption_anomalies(
    session: AsyncSession, year: int, z_threshold: float = 2.0
) -> dict:
    r = await session.execute(
        text("""
            SELECT cv.site_id, cv.year, cv.total_consumption
            FROM consumption_vectors cv
            JOIN sites s ON s."SiteId" = cv.site_id
            WHERE cv.year = :yr
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
            ORDER BY cv.site_id
        """),
        {"yr": year},
    )
    rows = [dict(row._mapping) for row in r]
    if not rows:
        return {"anomalies": [], "stats": {}}

    values = [row["total_consumption"] for row in rows if row["total_consumption"]]
    if len(values) < 3:
        return {"anomalies": [], "stats": {"count": len(values)}}

    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0

    anomalies = []
    for row in rows:
        val = row["total_consumption"]
        if val is None or stdev == 0:
            continue
        z = (val - mean) / stdev
        if abs(z) > z_threshold:
            anomalies.append({
                "site_id": row["site_id"],
                "year": row["year"],
                "consumption": round(val, 2),
                "z_score": round(z, 2),
                "direction": "high" if z > 0 else "low",
                "deviation_percent": round(((val - mean) / mean) * 100, 1),
            })

    anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return {
        "anomalies": anomalies,
        "stats": {
            "total_sites": len(rows),
            "mean": round(mean, 2),
            "stdev": round(stdev, 2) if stdev else 0,
            "anomaly_count": len(anomalies),
            "z_threshold": z_threshold,
        },
    }


async def detect_trend_anomalies(
    session: AsyncSession, year: int, change_threshold: float = 0.5
) -> dict:
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
        return {"anomalies": [], "stats": {}}

    changes = []
    for row in rows:
        prev = row["previous_kwh"]
        curr = row["current_kwh"]
        pct_change = (curr - prev) / prev
        changes.append({
            "site_id": row["site_id"],
            "previous_kwh": round(prev, 2),
            "current_kwh": round(curr, 2),
            "pct_change": round(pct_change * 100, 1),
        })

    changes.sort(key=lambda x: abs(x["pct_change"]), reverse=True)

    anomalies = [
        c for c in changes
        if abs(c["pct_change"]) > change_threshold * 100
    ]

    return {
        "anomalies": anomalies,
        "stats": {
            "total_sites": len(changes),
            "change_threshold_pct": change_threshold * 100,
            "anomaly_count": len(anomalies),
            "avg_change_pct": round(
                statistics.mean([abs(c["pct_change"]) for c in changes]), 1
            ) if changes else 0,
        },
    }


async def get_consumption_stats(
    session: AsyncSession, year: int
) -> dict:
    r = await session.execute(
        text("""
            SELECT
                COUNT(*) as site_count,
                ROUND(AVG(cv.total_consumption)::numeric, 2) as avg_kwh,
                ROUND(MIN(cv.total_consumption)::numeric, 2) as min_kwh,
                ROUND(MAX(cv.total_consumption)::numeric, 2) as max_kwh,
                ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY cv.total_consumption)::numeric, 2) as q1,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY cv.total_consumption)::numeric, 2) as median,
                ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cv.total_consumption)::numeric, 2) as q3
            FROM consumption_vectors cv
            JOIN sites s ON s."SiteId" = cv.site_id
            WHERE cv.year = :yr
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        """),
        {"yr": year},
    )
    row = r.fetchone()._mapping
    stats = dict(row)
    if stats.get("q1") is not None and stats.get("q3") is not None:
        iqr = float(stats["q3"]) - float(stats["q1"])
        stats["iqr"] = round(iqr, 2)
        stats["lower_fence"] = round(float(stats["q1"]) - 1.5 * iqr, 2)
        stats["upper_fence"] = round(float(stats["q3"]) + 1.5 * iqr, 2)
    return stats


async def detect_iqr_anomalies(
    session: AsyncSession, year: int
) -> dict:
    stats = await get_consumption_stats(session, year)
    if stats.get("lower_fence") is None:
        return {"anomalies": [], "stats": stats}

    r = await session.execute(
        text("""
            SELECT cv.site_id, cv.total_consumption,
                   s."SiteCode", s."SiteName"
            FROM consumption_vectors cv
            JOIN sites s ON s."SiteId" = cv.site_id
            WHERE cv.year = :yr
              AND cv.total_consumption IS NOT NULL
              AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
              AND (cv.total_consumption < :lower OR cv.total_consumption > :upper)
            ORDER BY cv.total_consumption DESC
        """),
        {
            "yr": year,
            "lower": stats["lower_fence"],
            "upper": stats["upper_fence"],
        },
    )
    anomalies = []
    for raw in r:
        a = dict(raw._mapping)
        a["consumption"] = round(a["total_consumption"], 2)
        del a["total_consumption"]
        anomalies.append(a)

    return {
        "anomalies": anomalies,
        "stats": stats,
        "anomaly_count": len(anomalies),
    }
