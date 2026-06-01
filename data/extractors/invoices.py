from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_invoice_summary(
    session: AsyncSession,
    year: int | None = None,
    site_id: int | None = None,
) -> list[dict]:
    conditions = []
    params = {}
    if year:
        conditions.append("EXTRACT(YEAR FROM ii.item_date) = :year")
        params["year"] = year
    if site_id:
        conditions.append("ii.site_id = :site_id")
        params["site_id"] = site_id
    where = " AND ".join(conditions) if conditions else "TRUE"

    query = text(f"""
        SELECT
            ii.site_id,
            s."SiteCode",
            s."SiteName",
            EXTRACT(YEAR FROM ii.item_date)::int AS year,
            EXTRACT(MONTH FROM ii.item_date)::int AS month,
            COUNT(*) AS invoice_count,
            SUM(ii.final_sale) / 1000.0 AS total_final_sale_tnd,
            SUM(ii.tva) / 1000.0 AS total_tax_tnd,
            SUM(
              (
                (ii.final_sale / 1000.0)
                / (1 + COALESCE(tc.tax_rate, 0))
                - COALESCE(tc.fixed_service_fee, 0)
              ) /
              NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0)
            ) AS total_consumption_kwh,
            s."ElecType" AS elec_type
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        CROSS JOIN tariff_config tc
        WHERE {where}
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        GROUP BY ii.site_id, s."SiteCode", s."SiteName",
                 EXTRACT(YEAR FROM ii.item_date),
                 EXTRACT(MONTH FROM ii.item_date),
                 s."ElecType", tc.tax_rate, tc.fixed_service_fee,
                 tc.kwh_price_bt, tc.kwh_price_mt
        ORDER BY ii.site_id, year, month
    """)
    result = await session.execute(query, params)
    return [dict(row._mapping) for row in result]


async def get_yearly_billing_summary(
    session: AsyncSession,
    year: int,
) -> list[dict]:
    query = text("""
        SELECT
            s."DirectionId" AS direction_id,
            d."Description" AS direction_name,
            s."ElecType" AS elec_type,
            COUNT(DISTINCT ii.site_id) AS site_count,
            SUM(ii.final_sale) / 1000.0 AS total_final_sale_tnd,
            SUM(ii.tva) / 1000.0 AS total_tax_tnd,
            SUM(
              (
                (ii.final_sale / 1000.0)
                / (1 + COALESCE(tc.tax_rate, 0))
                - COALESCE(tc.fixed_service_fee, 0)
              ) /
              NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0)
            ) AS total_consumption_kwh,
            (SUM(ii.final_sale) / 1000.0) / NULLIF(COUNT(DISTINCT ii.site_id), 0) AS avg_cost_per_site
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        LEFT JOIN directions d ON d."DirectionId" = s."DirectionId"
        CROSS JOIN tariff_config tc
        WHERE EXTRACT(YEAR FROM ii.item_date) = :year
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        GROUP BY s."DirectionId", d."Description", s."ElecType",
                 tc.tax_rate, tc.fixed_service_fee,
                 tc.kwh_price_bt, tc.kwh_price_mt
        ORDER BY s."DirectionId", s."ElecType"
    """)
    result = await session.execute(query, {"year": year})
    return [dict(row._mapping) for row in result]


async def get_total_billing_by_period(
    session: AsyncSession,
    start_year: int,
    end_year: int,
) -> list[dict]:
    query = text("""
        SELECT
            EXTRACT(YEAR FROM ii.item_date)::int AS year,
            s."ElecType" AS elec_type,
            COUNT(DISTINCT ii.site_id) AS site_count,
            SUM(ii.final_sale) / 1000.0 AS total_final_sale_tnd,
            SUM(
              (
                (ii.final_sale / 1000.0)
                / (1 + COALESCE(tc.tax_rate, 0))
                - COALESCE(tc.fixed_service_fee, 0)
              ) /
              NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0)
            ) AS total_consumption_kwh
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        CROSS JOIN tariff_config tc
        WHERE EXTRACT(YEAR FROM ii.item_date) BETWEEN :start_yr AND :end_yr
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        GROUP BY EXTRACT(YEAR FROM ii.item_date), s."ElecType",
                 tc.tax_rate, tc.fixed_service_fee,
                 tc.kwh_price_bt, tc.kwh_price_mt
        ORDER BY year, elec_type
    """)
    result = await session.execute(query, {"start_yr": start_year, "end_yr": end_year})
    return [dict(row._mapping) for row in result]
