from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_monthly_consumption_from_invoices(
    session: AsyncSession,
    site_id: int | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict]:
    conditions = []
    params = {}
    if site_id:
        conditions.append("ii.site_id = :site_id")
        params["site_id"] = site_id
    if start_year:
        conditions.append("EXTRACT(YEAR FROM ii.item_date) >= :start_year")
        params["start_year"] = start_year
    if end_year:
        conditions.append("EXTRACT(YEAR FROM ii.item_date) <= :end_year")
        params["end_year"] = end_year

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = text(f"""
        SELECT
            ii.site_id,
            s."SiteCode" as site_code,
            s."SiteName" as site_name,
            s."Configuration" as configuration,
            s."ElecType" as elec_type,
            s."NetworkTypeId" as network_type_id,
            s."DirectionId" as direction_id,
            s."IsSharing" as is_sharing,
            s."EstimatedConsumption" as estimated_consumption,
            COALESCE(st.has_2g, FALSE) as has_2g,
            COALESCE(st.has_3g, FALSE) as has_3g,
            COALESCE(st.has_4g_fdd, FALSE) as has_4g_fdd,
            COALESCE(st.has_4g_tdd, FALSE) as has_4g_tdd,
            COALESCE(st.has_5g, FALSE) as has_5g,
            EXTRACT(YEAR FROM ii.item_date)::int AS year,
            EXTRACT(MONTH FROM ii.item_date)::int AS month,
            ii.item_date,
            ((ii.final_sale / 1000.0) / 1.19) /
              NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0) AS total_consumption_kwh,
            ii.final_sale,
            ii.tva as tax_amount,
            tc.kwh_price_bt,
            tc.kwh_price_mt
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        LEFT JOIN tariff_config tc ON tc.id = 1
        LEFT JOIN site_tech_configs st ON st.site_code = s."SiteCode"
        WHERE {where_clause}
          AND ii.item_type = 0
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        ORDER BY ii.site_id, ii.item_date
    """)
    result = await session.execute(query, params)
    return [dict(row._mapping) for row in result]


async def get_alert_aggregates_by_site(
    session: AsyncSession,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[int, dict]:
    alert_conditions = ["a.site_id IS NOT NULL"]
    alert_params = {}
    if start_year:
        alert_conditions.append("EXTRACT(YEAR FROM a.created_at) >= :alert_start_year")
        alert_params["alert_start_year"] = start_year
    if end_year:
        alert_conditions.append("EXTRACT(YEAR FROM a.created_at) <= :alert_end_year")
        alert_params["alert_end_year"] = end_year

    alert_where = " AND ".join(alert_conditions)

    query = text(f"""
        SELECT
            a.site_id,
            COUNT(*) AS active_alert_count,
            BOOL_OR(CASE WHEN a.type = 'SFR' THEN TRUE ELSE FALSE END) AS has_sfr_alert,
            COUNT(CASE WHEN a.severity = 'critical' THEN 1 END) AS critical_alert_count
        FROM alerts a
        WHERE {alert_where}
        GROUP BY a.site_id
    """)
    result = await session.execute(query, alert_params)
    rows = result.fetchall()
    return {
        row.site_id: {
            "active_alert_count": row.active_alert_count,
            "has_sfr_alert": row.has_sfr_alert,
            "critical_alert_count": row.critical_alert_count,
        }
        for row in rows
    }


async def get_all_sites(session: AsyncSession) -> list[dict]:
    query = text("""
        SELECT
            "SiteId" as site_id,
            "SiteCode" as site_code,
            "SiteName" as site_name,
            "Configuration" as configuration,
            "ElecType" as elec_type,
            "NetworkTypeId" as network_type_id,
            "DirectionId" as direction_id,
            "IsSharing" as is_sharing,
            "EstimatedConsumption" as estimated_consumption,
            "MaxConsumption" as max_consumption,
            "StatusId" as status_id
        FROM sites
        WHERE "DirectionId" = 1 AND "StatusId" IN (1,3)
        ORDER BY "SiteId"
    """)
    result = await session.execute(query)
    return [dict(row._mapping) for row in result]
