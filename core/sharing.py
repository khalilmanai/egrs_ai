from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def compute_sharing_recovery(
    session: AsyncSession,
    site_id: int,
    price_per_kwh: float,
    tax_rate: float,
) -> dict:
    rows = (await session.execute(
        text("""
            SELECT
                so.id AS shared_op_id,
                o.id AS operator_id,
                o.name AS operator_name,
                o.code AS operator_code,
                so."isActive" AS is_active,
                COALESCE(SUM(vm.consumption), 0) AS kwh_attributed,
                COALESCE(SUM(vm.consumption), 0) * :price_per_kwh * (1 + :tax) AS cost_attributed_tnd,
                COUNT(DISTINCT vm."visitId") AS measurement_count
            FROM shared_operators so
            JOIN operators o ON o.id = so."operatorId"
            LEFT JOIN visit_measurements vm ON vm."siteOperatorId" = so.id
                                           AND vm."visitId" IN (
                                               SELECT id FROM visits WHERE "siteId" = :site_id
                                           )
            WHERE so."siteId" = :site_id
            GROUP BY so.id, o.id, o.name, o.code, so."isActive"
            ORDER BY kwh_attributed DESC
        """),
        {"site_id": site_id, "price_per_kwh": price_per_kwh, "tax": tax_rate},
    )).fetchall()

    operators = []
    recovered_cost_tnd = 0.0
    for r in rows:
        op = {
            "shared_operator_id": r[0],
            "operator_id": r[1],
            "name": r[2] or "?",
            "code": r[3] or "?",
            "is_active": bool(r[4]),
            "kwh_attributed": round(float(r[5]) if r[5] else 0, 1),
            "cost_attributed_tnd": round(float(r[6]) if r[6] else 0, 2),
            "measurement_count": int(r[7]) if r[7] else 0,
        }
        operators.append(op)
        if op["is_active"]:
            recovered_cost_tnd += op["cost_attributed_tnd"]

    active_count = len([o for o in operators if o["is_active"]])

    return {
        "sharing_count": active_count,
        "operators": operators,
        "recovered_cost_tnd": round(recovered_cost_tnd, 2),
        "recovered_cost_basis": (
            "Mesure metrique par operateur (visit_measurements.consumption "
            "agregee par siteOperatorId)"
        ),
    }
