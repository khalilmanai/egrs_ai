import statistics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def compute_site_health_scores(session: AsyncSession, year: int) -> list[dict]:
    r = await session.execute(text("""
        WITH drs_sites AS (
            SELECT "SiteId" FROM sites
            WHERE "DirectionId" = 1 AND "StatusId" IN (1,3)
        ),
        consumption_stats AS (
            SELECT
                cv.site_id,
                cv.total_consumption,
                ROUND(AVG(cv.total_consumption) OVER ()::numeric, 2) AS global_mean,
                ROUND(STDDEV(cv.total_consumption) OVER ()::numeric, 2) AS global_std
            FROM consumption_vectors cv
            JOIN drs_sites d ON d."SiteId" = cv.site_id
            WHERE cv.year = :yr AND cv.total_consumption IS NOT NULL
        ),
        alert_counts AS (
            SELECT
                a.site_id,
                COUNT(*) AS alert_total,
                COUNT(*) FILTER (WHERE a.severity = 'CRITICAL') AS critical_count,
                COUNT(*) FILTER (WHERE a.severity = 'HIGH') AS high_count,
                COUNT(*) FILTER (WHERE a.status = 'NEW') AS unresolved_count
            FROM alerts a
            JOIN drs_sites d ON d."SiteId" = a.site_id
            GROUP BY a.site_id
        ),
        sfr_months AS (
            SELECT
                a.site_id,
                MIN(a.created_at) AS first_sfr_date,
                MAX(a.created_at) AS last_sfr_date
            FROM alerts a
            JOIN drs_sites d ON d."SiteId" = a.site_id
            WHERE a.type = 'SFR'
            GROUP BY a.site_id
        )
        SELECT
            c.site_id,
            s."SiteCode",
            s."SiteName",
            s."DirectionId",
            c.total_consumption,
            c.global_mean,
            c.global_std,
            COALESCE(a.alert_total, 0) AS alert_total,
            COALESCE(a.critical_count, 0) AS critical_count,
            COALESCE(a.high_count, 0) AS high_count,
            COALESCE(a.unresolved_count, 0) AS unresolved_count,
            CASE WHEN sm.first_sfr_date IS NOT NULL
                THEN (CURRENT_DATE - sm.first_sfr_date::date)
                ELSE 0
            END AS sfr_days_since_first
        FROM consumption_stats c
        JOIN sites s ON s."SiteId" = c.site_id
        LEFT JOIN alert_counts a ON a.site_id = c.site_id
        LEFT JOIN sfr_months sm ON sm.site_id = c.site_id
        ORDER BY c.total_consumption DESC
    """), {"yr": year})

    rows = [dict(row._mapping) for row in r]

    if not rows:
        return []

    consumption_max = max(r["total_consumption"] for r in rows)
    consumption_min = min(r["total_consumption"] for r in rows)
    consumption_range = consumption_max - consumption_min if consumption_max != consumption_min else 1

    max_sfr_days = max(float(r["sfr_days_since_first"]) for r in rows) if rows else 0

    results = []
    for row in rows:
        score = 100.0

        consumption = float(row["total_consumption"])
        global_mean = float(row["global_mean"]) if row["global_mean"] else 0
        global_std = float(row["global_std"]) if row["global_std"] else 0

        z_score = 0
        if global_std > 0:
            z_score = (consumption - global_mean) / global_std

        cons_norm = (consumption - consumption_min) / consumption_range
        cons_score = 100 - (abs(cons_norm - 0.5) * 100)
        score -= (100 - cons_score) * 0.15

        if abs(z_score) > 3:
            score -= 15
        elif abs(z_score) > 2:
            score -= 8

        critical = float(row["critical_count"])
        high = float(row["high_count"])
        unresolved = float(row["unresolved_count"])
        score -= min(critical * 5, 30)
        score -= min(high * 3, 15)
        score -= min(unresolved * 2, 10)

        sfr_days = float(row["sfr_days_since_first"])
        sfr_penalty = min((sfr_days / 30) * 2, 20) if max_sfr_days > 0 else 0
        score -= sfr_penalty

        score = max(0, min(100, round(score, 1)))

        classification = "healthy" if score >= 80 else "warning" if score >= 50 else "critical"

        results.append({
            "site_id": row["site_id"],
            "site_code": row["SiteCode"],
            "site_name": row["SiteName"],
            "direction_id": row["DirectionId"],
            "consumption_kwh": round(consumption, 2),
            "z_score": round(z_score, 2),
            "alerts": {
                "total": int(row["alert_total"]),
                "critical": int(critical),
                "high": int(high),
                "unresolved": int(unresolved),
            },
            "sfr_days_since_first": int(sfr_days),
            "health_score": score,
            "classification": classification,
        })

    return results


async def compute_enterprise_health_summary(
    session: AsyncSession, year: int
) -> dict:
    scores = await compute_site_health_scores(session, year)
    if not scores:
        return {"overall_health": 0, "sites": [], "summary": {}}

    all_scores = [s["health_score"] for s in scores]
    overall = round(statistics.mean(all_scores), 1)
    healthy = [s for s in scores if s["classification"] == "healthy"]
    warning = [s for s in scores if s["classification"] == "warning"]
    critical = [s for s in scores if s["classification"] == "critical"]

    scores_sorted = sorted(scores, key=lambda x: x["health_score"])
    bottom_10 = scores_sorted[:10]
    top_10 = scores_sorted[-10:]
    top_10.reverse()

    r = await session.execute(text("""
        SELECT COUNT(*) FROM alerts a
        JOIN sites s ON s."SiteId" = a.site_id
        WHERE a.severity = 'CRITICAL' AND a.status = 'NEW'
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
    """))
    unresolved_critical = r.scalar() or 0

    return {
        "overall_health": overall,
        "total_sites_scored": len(scores),
        "healthy_count": len(healthy),
        "warning_count": len(warning),
        "critical_count": len(critical),
        "unresolved_critical_alerts": unresolved_critical,
        "top_10_healthiest": top_10,
        "bottom_10_sites": bottom_10,
        "sites": scores,
    }
