def normalize_column_name(column_name: str) -> str:
    """
    Convert database column name to normalized Python attribute name.
    
    Examples:
        "DirectionId" -> "direction_id"
        "SiteCode" -> "site_code"
        "ElecType" -> "elec_type"
        "NetworkTypeId" -> "network_type_id"
    """
    import re
    
    # Handle camelCase to snake_case conversion
    # Insert underscore before capital letters (except at start)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', column_name)
    # Handle consecutive capital letters
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    
    # Convert to lowercase
    return s2.lower()


def get_column_mapping() -> dict[str, str]:
    """
    Get mapping from database column names to Python attribute names.
    
    This provides a centralized way to handle column name conversions
    throughout the application.
    """
    return {
        # Sites table
        "SiteId": "site_id",
        "SiteCode": "site_code",
        "SiteName": "site_name",
        "Configuration": "configuration",
        "ElecType": "elec_type",
        "NetworkTypeId": "network_type_id",
        "DirectionId": "direction_id",
        "IsSharing": "is_sharing",
        "EstimatedConsumption": "estimated_consumption",
        "MaxConsumption": "max_consumption",
        "RealConsumption": "real_consumption",
        "StatusId": "status_id",
        
        # Invoice items table
        "item_id": "item_id",
        "invoice_id": "invoice_id",
        "site_id": "site_id",
        "item_no": "item_no",
        "description": "description",
        "item_type": "item_type",
        "item_date": "item_date",
        "consumption_kwh": "consumption_kwh",
        "consumption_amount": "consumption_amount",
        "credit": "credit",
        "tva": "tva",
        "final_sale": "final_sale",
        "district_code": "district_code",
        
        # Tariff config
        "id": "id",
        "tax_rate": "tax_rate",
        "kwh_price_bt": "kwh_price_bt",
        "kwh_price_mt": "kwh_price_mt",
        "fixed_service_fee": "fixed_service_fee",
        
        # Consumption vectors
        "id": "id",
        "site_id": "site_id",
        "year": "year",
        "vector": "vector",
        "total_consumption": "total_consumption",
        "site_configuration": "site_configuration",
        "network_type_id": "network_type_id",
        "electrical_type": "electrical_type",
        "direction_id": "direction_id",
        
        # Alerts
        "site_id": "site_id",
        "type": "type",
        "severity": "severity",
        "created_at": "created_at",
        
        # Directions
        "DirectionId": "direction_id",
        "Code": "code",
        "Description": "description",
    }


def normalize_query_result(result: dict) -> dict:
    """
    Normalize a database query result dictionary to use consistent keys.
    
    This function takes a dictionary from a database query and ensures
    that all keys are normalized to snake_case for consistency.
    """
    mapping = get_column_mapping()
    normalized = {}
    
    for key, value in result.items():
        # Try to find the normalized key
        normalized_key = mapping.get(key, normalize_column_name(key))
        normalized[normalized_key] = value
    
    return normalized


def get_quoted_column(column_name: str) -> str:
    """
    Get the quoted version of a column name for SQL queries.
    
    This ensures that column names are properly quoted in SQL queries
    to handle special characters and case sensitivity.
    """
    return f'"{column_name}"'
