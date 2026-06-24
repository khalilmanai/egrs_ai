from core.column_utils import normalize_column_name, normalize_query_result, get_column_mapping
from analytics.forecast import _get_historical_month_value, _get_last_n_values, _get_static_features


class TestNormalizeColumnName:
    def test_camel_case_to_snake(self):
        assert normalize_column_name("DirectionId") == "direction_id"
        assert normalize_column_name("SiteCode") == "site_code"
        assert normalize_column_name("ElecType") == "elec_type"

    def test_already_snake_case(self):
        assert normalize_column_name("site_id") == "site_id"
        assert normalize_column_name("total_consumption") == "total_consumption"

    def test_single_word(self):
        assert normalize_column_name("Vector") == "vector"
        assert normalize_column_name("Year") == "year"

    def test_acronym_handling(self):
        assert normalize_column_name("SFRAlert") == "sfr_alert"
        assert normalize_column_name("HTTPSConfig") == "https_config"

    def test_mixed_case(self):
        assert normalize_column_name("SiteId") == "site_id"
        assert normalize_column_name("NetworkTypeId") == "network_type_id"


class TestNormalizeQueryResult:
    def test_normalizes_keys(self):
        result = {
            "SiteId": 1,
            "SiteCode": "SITE-001",
            "ElecType": "BT",
            "DirectionId": 1,
        }
        normalized = normalize_query_result(result)
        assert "site_id" in normalized
        assert "site_code" in normalized
        assert "elec_type" in normalized
        assert "direction_id" in normalized
        assert normalized["site_id"] == 1

    def test_preserves_snake_case_keys(self):
        result = {"site_id": 1, "total_consumption": 1000.0}
        normalized = normalize_query_result(result)
        assert normalized["site_id"] == 1
        assert normalized["total_consumption"] == 1000.0

    def test_handles_empty_dict(self):
        assert normalize_query_result({}) == {}

    def test_preserves_values(self):
        result = {"SiteName": "Test Site", "IsSharing": True, "SiteId": 42}
        normalized = normalize_query_result(result)
        assert normalized["site_name"] == "Test Site"
        assert normalized["is_sharing"] is True
        assert normalized["site_id"] == 42


class TestGetColumnMapping:
    def test_contains_essential_mappings(self):
        mapping = get_column_mapping()
        assert mapping["SiteId"] == "site_id"
        assert mapping["DirectionId"] == "direction_id"
        assert mapping["ElecType"] == "elec_type"

    def test_includes_invoice_columns(self):
        mapping = get_column_mapping()
        assert mapping["site_id"] == "site_id"
        assert mapping["item_type"] == "item_type"

    def test_includes_tariff_columns(self):
        mapping = get_column_mapping()
        assert mapping["kwh_price_bt"] == "kwh_price_bt"
        assert mapping["kwh_price_mt"] == "kwh_price_mt"


class TestGetHistoricalMonthValue:
    def setup_method(self):
        import pandas as pd
        self.hist = pd.DataFrame({
            "site_id": [1, 1, 1, 1],
            "month": [1, 2, 3, 4],
            "total_consumption_kwh": [1000, 1100, 1200, 1300],
            "year": [2025] * 4,
        })

    def test_returns_correct_month(self):
        import pandas as pd
        hist = pd.DataFrame({
            "month": [1, 2, 3, 4],
            "total_consumption_kwh": [1000, 1100, 1200, 1300],
        })
        val = _get_historical_month_value(hist, 3)
        assert val == 1200.0

    def test_returns_last_for_duplicate_months(self):
        import pandas as pd
        hist = pd.DataFrame({
            "month": [3, 3],
            "total_consumption_kwh": [1200, 1250],
        })
        val = _get_historical_month_value(hist, 3)
        assert val == 1250.0

    def test_returns_zero_for_missing_month(self):
        import pandas as pd
        hist = pd.DataFrame({
            "month": [1, 2, 4],
            "total_consumption_kwh": [1000, 1100, 1300],
        })
        val = _get_historical_month_value(hist, 3)
        assert val == 0.0

    def test_handles_empty_dataframe(self):
        import pandas as pd
        hist = pd.DataFrame()
        val = _get_historical_month_value(hist, 1)
        assert val == 0.0


class TestGetLastNValues:
    def test_returns_last_n_values(self):
        import pandas as pd
        hist = pd.DataFrame({
            "total_consumption_kwh": [100, 200, 300, 400, 500],
        })
        vals = _get_last_n_values(hist, 3)
        assert vals == [300.0, 400.0, 500.0]

    def test_returns_all_when_less_than_n(self):
        import pandas as pd
        hist = pd.DataFrame({
            "total_consumption_kwh": [100, 200],
        })
        vals = _get_last_n_values(hist, 5)
        assert vals == [100.0, 200.0]

    def test_handles_empty(self):
        import pandas as pd
        hist = pd.DataFrame()
        vals = _get_last_n_values(hist, 3)
        assert vals == []

    def test_converts_nan_to_zero(self):
        import pandas as pd
        import numpy as np
        hist = pd.DataFrame({
            "total_consumption_kwh": [100, np.nan, 300],
        })
        vals = _get_last_n_values(hist, 3)
        assert vals[0] == 100.0
        assert vals[1] == 0.0
        assert vals[2] == 300.0


class TestGetStaticFeatures:
    def test_extracts_all_specified_columns(self):
        import pandas as pd
        data = {
            "month": [3],
            "total_consumption_kwh": [1200],
            "is_bt": [1],
            "is_sharing_int": [0],
            "config_terminal": [1],
            "config_nodal": [0],
            "config_agreg": [0],
            "network_type_4g": [1],
            "network_type_5g": [0],
            "estimated_consumption_kwh": [10000],
            "has_2g": [1],
            "has_3g": [0],
            "has_4g_fdd": [1],
            "has_4g_tdd": [0],
            "has_5g": [0],
            "active_alert_count": [2],
            "has_sfr_alert": [0],
            "site_mean_24m": [1100],
            "site_std_24m": [150],
            "site_trend_12m": [0.02],
            "consumption_to_mean_ratio": [1.09],
            "data_quality_pct": [0.95],
        }
        df = pd.DataFrame(data)
        result = _get_static_features(df)
        assert result["is_bt"] == 1.0
        assert result["config_terminal"] == 1.0
        assert result["network_type_4g"] == 1.0
        assert result["estimated_consumption_kwh"] == 10000.0
        assert result["site_mean_24m"] == 1100.0
        assert result["data_quality_pct"] == 0.95

    def test_handles_missing_tech_flags(self):
        import pandas as pd
        df = pd.DataFrame({
            "month": [1],
            "total_consumption_kwh": [1000],
            "is_bt": [1],
            "is_sharing_int": [0],
            "site_mean_24m": [1100],
            "site_std_24m": [100],
            "data_quality_pct": [1.0],
        })
        result = _get_static_features(df)
        assert result["has_2g"] == 0.0
        assert result["has_4g_fdd"] == 0.0

    def test_handles_nan_values_in_static_features(self):
        import pandas as pd
        import numpy as np
        df = pd.DataFrame({
            "month": [1],
            "total_consumption_kwh": [1000],
            "is_bt": [1],
            "is_sharing_int": [0],
            "site_mean_24m": [np.nan],
            "site_std_24m": [np.nan],
            "data_quality_pct": [np.nan],
        })
        result = _get_static_features(df)
        assert result["site_mean_24m"] == 0.0
        assert result["site_std_24m"] == 0.0
        assert result["data_quality_pct"] == 0.0
