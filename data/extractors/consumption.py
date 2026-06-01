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
            EXTRACT(YEAR FROM ii.item_date)::int AS year,
            EXTRACT(MONTH FROM ii.item_date)::int AS month,
            ii.item_date,
            (
              (ii.final_sale / 1000.0)
              / (1 + COALESCE(tc.tax_rate, 0))
              - COALESCE(tc.fixed_service_fee, 0)
            ) /
              NULLIF(CASE WHEN s."ElecType" = 'BT' THEN tc.kwh_price_bt ELSE tc.kwh_price_mt END, 0) AS total_consumption_kwh,
            ii.final_sale,
            ii.tva as tax_amount,
            tc.kwh_price_bt,
            tc.kwh_price_mt,
            tc.tax_rate
        FROM invoice_items ii
        JOIN sites s ON s."SiteId" = ii.site_id
        LEFT JOIN tariff_config tc ON tc.id = 1
        WHERE {where_clause}
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        ORDER BY ii.site_id, ii.item_date
    """)
    result = await session.execute(query, params)
    return [dict(row._mapping) for row in result]


async def get_monthly_consumption_from_visits(
    session: AsyncSession,
    site_id: int | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict]:
    conditions = ["vm.consumption IS NOT NULL"]
    params = {}
    if site_id:
        conditions.append("v.\"siteId\" = :site_id")
        params["site_id"] = site_id
    if start_year:
        conditions.append("EXTRACT(YEAR FROM v.\"visitDate\") >= :start_year")
        params["start_year"] = start_year
    if end_year:
        conditions.append("EXTRACT(YEAR FROM v.\"visitDate\") <= :end_year")
        params["end_year"] = end_year

    where_clause = " AND ".join(conditions)

    query = text(f"""
        SELECT
            v."siteId" as site_id,
            s."SiteCode" as site_code,
            s."SiteName" as site_name,
            s."Configuration" as configuration,
            s."ElecType" as elec_type,
            EXTRACT(YEAR FROM v.\"visitDate\")::int AS year,
            EXTRACT(MONTH FROM v.\"visitDate\")::int AS month,
            v."visitDate" as visit_date,
            vm.type as measurement_type,
            vm."meterIndex" as meter_index,
            vm."previousIndex" as previous_index,
            vm.consumption as consumption_kwh,
            vm."siteOperatorId" as site_operator_id,
            o.name as operator_name
        FROM visit_measurements vm
        JOIN visits v ON v.id = vm."visitId"
        JOIN sites s ON s."SiteId" = v."siteId"
        LEFT JOIN shared_operators so ON so.id = vm."siteOperatorId"
        LEFT JOIN operators o ON o.id = so."operatorId"
        WHERE {where_clause}
          AND s."DirectionId" = 1 AND s."StatusId" IN (1,3)
        ORDER BY v."siteId", v."visitDate"
    """)
    result = await session.execute(query, params)
    return [dict(row._mapping) for row in result]


async def get_all_sites_with_metadata(session: AsyncSession) -> list[dict]:
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
