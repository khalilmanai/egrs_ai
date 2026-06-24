"""SQL filter constants and query helpers for consistent site filtering.

Centralizes the commonly-used filter pattern `"DirectionId" = 1 AND "StatusId" IN (1,3)`
so changes propagate across all 30+ query locations.
"""

# Default active DRS site filter values
DEFAULT_DIRECTION_ID = 1
ACTIVE_STATUS_IDS = (1, 3)

# Seasonal consumption profile (monthly multipliers relative to mean)
SEASONAL_PROFILE = {
    1: 0.92, 2: 0.93, 3: 0.96, 4: 0.99,
    5: 1.02, 6: 1.05, 7: 1.08, 8: 1.07,
    9: 1.03, 10: 1.00, 11: 0.96, 12: 0.93,
}
SEASONAL_FLATNESS_THRESHOLD = 0.03


def site_filter(table_alias: str = "s") -> str:
    """Return a SQL WHERE clause fragment filtering to active DRS sites.
    
    Args:
        table_alias: The alias used for the 'sites' table in the query (default 's').
    """
    return f'{table_alias}."DirectionId" = {DEFAULT_DIRECTION_ID} AND {table_alias}."StatusId" IN {_format_tuple(ACTIVE_STATUS_IDS)}'


def site_filter_no_alias() -> str:
    """Return a SQL WHERE clause fragment without table alias (for single-table queries)."""
    return f'"DirectionId" = {DEFAULT_DIRECTION_ID} AND "StatusId" IN {_format_tuple(ACTIVE_STATUS_IDS)}'


def _format_tuple(values: tuple) -> str:
    return "(" + ",".join(str(v) for v in values) + ")"
