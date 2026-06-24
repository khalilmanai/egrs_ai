import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.column_utils import normalize_query_result
from core.sql_filter import site_filter, site_filter_no_alias

logger = logging.getLogger(__name__)


async def get_billing_summary_by_direction(session: AsyncSession, year: int) -> list[dict]:
    r = await session.execute(text(f"""
        SELECT
            s."DirectionId" AS direction_id,
            d."Description" AS direction_name,
            s."ElecType" AS elec_type,
            COUNT(DISTINCT ii.site_id)::int AS site_count,
            SUM(ii.final_sale) / 1000.0 AS total_cost_tnd,
            SUM(ii.tva) / 1000.0 AS total_tax_tnd,
            SUM(((ii.final_sale / 1000.0) / 1.19)) /
            NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0)
            AS total_consumption_kwh
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        LEFT JOIN directions d ON d."DirectionId" = s."DirectionId"
        CROSS JOIN tariff_config tc
        WHERE ii.item_type = 0
          AND EXTRACT(YEAR FROM ii.item_date) = :year
          AND {site_filter('s')}
        GROUP BY s."DirectionId", d."Description", s."ElecType",
                 tc.kwh_price_bt, tc.kwh_price_mt
        ORDER BY s."DirectionId", s."ElecType"
    """), {"year": year})
    rows = [normalize_query_result(dict(row._mapping)) for row in r]
    for row in rows:
        for k in ("total_cost_tnd", "total_tax_tnd", "total_consumption_kwh"):
            if row.get(k) is not None:
                row[k] = float(row[k])
    logger.debug("get_billing_summary_by_direction: %d rows for year=%d", len(rows), year)
    return rows


async def get_yearly_totals(session: AsyncSession, start_year: int, end_year: int) -> list[dict]:
    r = await session.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ii.item_date)::int AS year,
            s."ElecType" AS elec_type,
            COUNT(DISTINCT ii.site_id) AS site_count,
            SUM(ii.final_sale) / 1000.0 AS total_cost_tnd,
            SUM(((ii.final_sale / 1000.0) / 1.19)) /
            NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0)
            AS total_consumption_kwh
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        CROSS JOIN tariff_config tc
        WHERE ii.item_type = 0
          AND EXTRACT(YEAR FROM ii.item_date) BETWEEN :start AND :end
          AND {site_filter('s')}
        GROUP BY EXTRACT(YEAR FROM ii.item_date), s."ElecType",
                 tc.kwh_price_bt, tc.kwh_price_mt
        ORDER BY year, elec_type
    """), {"start": start_year, "end": end_year})
    rows = [dict(row._mapping) for row in r]
    for row in rows:
        for k in ("total_cost_tnd", "total_consumption_kwh"):
            if row.get(k) is not None:
                row[k] = float(row[k])
    return rows


async def get_site_count(session: AsyncSession) -> int:
    r = await session.execute(text(f"""
        SELECT COUNT(*) FROM sites
        WHERE {site_filter_no_alias()}
    """))
    return r.scalar() or 0


async def get_yearly_estimated_to_reel_ratio(session: AsyncSession, year: int) -> dict:
    r = await session.execute(text(f"""
        SELECT
            ii.item_type,
            COUNT(*) AS invoice_count,
            SUM(ii.final_sale) AS total_final_sale,
            SUM(ii.consumption_kwh) AS total_consumption_kwh
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        WHERE EXTRACT(YEAR FROM ii.item_date) = :year
          AND {site_filter('s')}
        GROUP BY ii.item_type
        ORDER BY ii.item_type
    """), {"year": year})
    rows = r.fetchall()
    reel = {"final_sale": 0, "consumption_kwh": 0, "count": 0}
    estimated = {"final_sale": 0, "consumption_kwh": 0, "count": 0}
    for row in rows:
        item_type = row[0]
        d = reel if item_type == 0 else estimated
        d["count"] = int(row[1])
        d["final_sale"] = float(row[2]) if row[2] else 0
        d["consumption_kwh"] = float(row[3]) if row[3] else 0

    ratio_amount = (
        round(estimated["final_sale"] / reel["final_sale"], 4)
        if reel["final_sale"] else 0
    )
    ratio_kwh = (
        round(estimated["consumption_kwh"] / reel["consumption_kwh"], 4)
        if reel["consumption_kwh"] else 0
    )
    gap_amount = estimated["final_sale"] - reel["final_sale"]
    gap_kwh = estimated["consumption_kwh"] - reel["consumption_kwh"]
    pct_gap_amount = (
        round(gap_amount / reel["final_sale"] * 100, 2)
        if reel["final_sale"] else 0
    )
    pct_gap_kwh = (
        round(gap_kwh / reel["consumption_kwh"] * 100, 2)
        if reel["consumption_kwh"] else 0
    )

    return {
        "year": year,
        "reel": {
            "invoice_count": reel["count"],
            "total_final_sale_tnd": round(reel["final_sale"] / 1000, 2),
            "total_consumption_kwh": round(reel["consumption_kwh"], 0),
        },
        "estimated": {
            "invoice_count": estimated["count"],
            "total_final_sale_tnd": round(estimated["final_sale"] / 1000, 2),
            "total_consumption_kwh": round(estimated["consumption_kwh"], 0),
        },
        "ratio_estimated_to_reel": {
            "amount": ratio_amount,
            "consumption_kwh": ratio_kwh,
        },
        "gap_estimated_minus_reel": {
            "amount_tnd": round(gap_amount / 1000, 2),
            "consumption_kwh": round(gap_kwh, 0),
            "amount_pct": pct_gap_amount,
            "consumption_kwh_pct": pct_gap_kwh,
        },
    }


async def get_site_estimated_vs_reel_gap(session: AsyncSession, year: int) -> list[dict]:
    r = await session.execute(text(f"""
        SELECT
            ii.site_id,
            s."SiteCode" AS site_code,
            s."SiteName" AS site_name,
            ii.item_type,
            SUM(ii.final_sale) AS total_final_sale,
            SUM(ii.consumption_kwh) AS total_consumption_kwh,
            COUNT(*) AS invoice_count
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        WHERE EXTRACT(YEAR FROM ii.item_date) = :year
          AND {site_filter('s')}
        GROUP BY ii.site_id, s."SiteCode", s."SiteName", ii.item_type
        ORDER BY s."SiteCode", ii.item_type
    """), {"year": year})
    rows = r.fetchall()
    site_map: dict[int, dict] = {}
    for row in rows:
        sid = row[0]
        if sid not in site_map:
            site_map[sid] = {
                "site_id": sid,
                "site_code": row[1],
                "site_name": row[2],
                "reel_final_sale": 0,
                "reel_consumption_kwh": 0,
                "reel_count": 0,
                "estimated_final_sale": 0,
                "estimated_consumption_kwh": 0,
                "estimated_count": 0,
            }
        d = site_map[sid]
        is_estimated = row[3] == 1
        final_sale = float(row[4]) if row[4] else 0
        kwh = float(row[5]) if row[5] else 0
        count = int(row[6])
        if is_estimated:
            d["estimated_final_sale"] = final_sale
            d["estimated_consumption_kwh"] = kwh
            d["estimated_count"] = count
        else:
            d["reel_final_sale"] = final_sale
            d["reel_consumption_kwh"] = kwh
            d["reel_count"] = count

    results = []
    for d in site_map.values():
        rfs = d["reel_final_sale"]
        rkwh = d["reel_consumption_kwh"]
        efs = d["estimated_final_sale"]
        ekwh = d["estimated_consumption_kwh"]

        gap_amount = efs - rfs
        gap_kwh = ekwh - rkwh

        results.append({
            "site_code": d["site_code"],
            "site_name": d["site_name"],
            "reel": {
                "invoice_count": d["reel_count"],
                "final_sale_tnd": round(rfs / 1000, 2),
                "consumption_kwh": round(rkwh, 0),
            },
            "estimated": {
                "invoice_count": d["estimated_count"],
                "final_sale_tnd": round(efs / 1000, 2),
                "consumption_kwh": round(ekwh, 0),
            },
            "gap": {
                "amount_tnd": round(gap_amount / 1000, 2),
                "consumption_kwh": round(gap_kwh, 0),
                "amount_pct": round(gap_amount / rfs * 100, 2) if rfs else 0,
                "consumption_kwh_pct": round(gap_kwh / rkwh * 100, 2) if rkwh else 0,
            },
        })

    return results
