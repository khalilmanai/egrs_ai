import statistics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def detect_zscore_anomalies(
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
                "deviation_pct": round(((val - mean) / mean) * 100, 1),
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
    session: AsyncSession, year: int, change_threshold_pct: float = 50.0
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
        pct_change = (curr - prev) / prev * 100
        changes.append({
            "site_id": row["site_id"],
            "previous_kwh": round(prev, 2),
            "current_kwh": round(curr, 2),
            "pct_change": round(pct_change, 1),
        })

    changes.sort(key=lambda x: abs(x["pct_change"]), reverse=True)

    anomalies = [c for c in changes if abs(c["pct_change"]) > change_threshold_pct]

    return {
        "anomalies": anomalies[:20],
        "stats": {
            "total_sites": len(changes),
            "change_threshold_pct": change_threshold_pct,
            "anomaly_count": len(anomalies),
            "avg_abs_change_pct": round(
                statistics.mean([abs(c["pct_change"]) for c in changes]), 1
            ) if changes else 0,
        },
    }


async def detect_iqr_anomalies(session: AsyncSession, year: int) -> dict:
    stats_r = await session.execute(
        text("""
            SELECT
                COUNT(*) as site_count,
                ROUND(AVG(cv.total_consumption)::numeric, 2) as avg_kwh,
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
    stats = dict(stats_r.fetchone()._mapping)

    if stats.get("q1") is None or stats.get("q3") is None:
        return {"anomalies": [], "stats": stats, "anomaly_count": 0}

    iqr = float(stats["q3"]) - float(stats["q1"])
    lower_fence = float(stats["q1"]) - 1.5 * iqr
    upper_fence = float(stats["q3"]) + 1.5 * iqr

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
        {"yr": year, "lower": lower_fence, "upper": upper_fence},
    )
    anomalies = []
    for raw in r:
        a = dict(raw._mapping)
        a["consumption"] = round(a["total_consumption"], 2)
        del a["total_consumption"]
        anomalies.append(a)

    return {
        "anomalies": anomalies,
        "stats": {
            "q1": float(stats["q1"]),
            "q3": float(stats["q3"]),
            "iqr": round(iqr, 2),
            "lower_fence": round(lower_fence, 2),
            "upper_fence": round(upper_fence, 2),
            "median": float(stats["median"]),
        },
        "anomaly_count": len(anomalies),
    }


async def run_all_detections(session: AsyncSession, year: int) -> dict:
    zscore = await detect_zscore_anomalies(session, year)
    trend = await detect_trend_anomalies(session, year)
    iqr = await detect_iqr_anomalies(session, year)

    return {
        "zscore": zscore,
        "trend": trend,
        "iqr": iqr,
        "summary": {
            "zscore_count": zscore["stats"].get("anomaly_count", 0),
            "trend_count": trend["stats"].get("anomaly_count", 0),
            "iqr_count": iqr.get("anomaly_count", 0),
            "total_anomalies": (
                zscore["stats"].get("anomaly_count", 0)
                + trend["stats"].get("anomaly_count", 0)
                + iqr.get("anomaly_count", 0)
            ),
        },
    }
