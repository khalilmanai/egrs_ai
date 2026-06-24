import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def compute_visits_summary(session: AsyncSession, site_id: int) -> dict:
    last_row = (await session.execute(
        text("""
            SELECT v.id, v."visitDate", v.comment, v.anomalies, v.status
            FROM visits v
            WHERE v."siteId" = :site_id
            ORDER BY v."visitDate" DESC NULLS LAST
            LIMIT 1
        """),
        {"site_id": site_id},
    )).fetchone()

    if last_row:
        last_visit_date = last_row[1]
        last_visit_status = last_row[4]
        last_comment = (last_row[2] or "").strip()
        last_anomalies = (last_row[3] or "").strip()
        parts = [p for p in (last_comment, last_anomalies) if p]
        last_findings = " | ".join(parts) if parts else "Aucun constat technique enregistre"
        days_since_visit = (datetime.utcnow().date() - last_visit_date.date()).days if last_visit_date else None
    else:
        last_visit_date = None
        last_visit_status = None
        last_findings = "Aucune visite enregistree pour ce site"
        days_since_visit = None

    stats_row = (await session.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE v."visitDate" >= (CURRENT_DATE - INTERVAL '12 months')) AS visits_12m,
                COUNT(*) FILTER (WHERE v."visitDate" >= (CURRENT_DATE - INTERVAL '24 months')) AS visits_24m,
                COUNT(*) FILTER (WHERE v.status = 'REJECTED'
                                  AND v."visitDate" >= (CURRENT_DATE - INTERVAL '24 months')) AS rejected_24m,
                COUNT(DISTINCT v."technicianId") FILTER (
                    WHERE v."visitDate" >= (CURRENT_DATE - INTERVAL '12 months')
                ) AS technicians_12m
            FROM visits v
            WHERE v."siteId" = :site_id
        """),
        {"site_id": site_id},
    )).fetchone()

    visits_12m = int(stats_row[0]) if stats_row and stats_row[0] else 0
    visits_24m = int(stats_row[1]) if stats_row and stats_row[1] else 0
    visits_rejected_24m = int(stats_row[2]) if stats_row and stats_row[2] else 0
    technicians_12m = int(stats_row[3]) if stats_row and stats_row[3] else 0

    vm_rows = (await session.execute(
        text("""
            SELECT vm.id, vm.type, vm.consumption, vm.notes, vm."siteOperatorId",
                   v."visitDate", v.id as visit_id
            FROM visit_measurements vm
            JOIN visits v ON v.id = vm."visitId"
            WHERE v."siteId" = :site_id
              AND vm.consumption IS NOT NULL
            ORDER BY v."visitDate" DESC NULLS LAST, vm.id DESC
            LIMIT 5
        """),
        {"site_id": site_id},
    )).fetchall()

    latest_measurement = None
    if vm_rows:
        r = vm_rows[0]
        latest_measurement = {
            "id": str(r[0]),
            "type": r[1],
            "consumption_kwh": float(r[2]) if r[2] else 0,
            "notes": r[3] or "",
            "site_operator_id": r[4],
            "visit_date": str(r[5])[:19] if r[5] else None,
            "visit_id": r[6],
        }

    result = {
        "days_since_last_visit": days_since_visit,
        "last_visit_date": str(last_visit_date)[:19] if last_visit_date else None,
        "last_visit_status": last_visit_status,
        "last_findings": last_findings,
        "visits_12m_count": visits_12m,
        "visits_24m_count": visits_24m,
        "visits_rejected_24m_count": visits_rejected_24m,
        "technician_count_12m": technicians_12m,
        "latest_measurement": latest_measurement,
    }
    logger.debug("compute_visits_summary for site_id=%d: visits_12m=%d, days_since_visit=%s",
                 site_id, visits_12m, days_since_visit)
    return result
