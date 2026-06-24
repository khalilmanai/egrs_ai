import numpy as np
import pandas as pd
import pytest
from analytics.forecast import _apply_seasonal_shape, _get_static_features, forecast_site
from analytics.features import engineer_features, build_query_vector
from analytics.budget import compute_monthly_budget, compute_precomputed_insights


class TestApplySeasonalShape:
    def test_preserves_varied_data(self):
        predictions = [1000, 1200, 1100, 1300, 1400, 1500, 1600, 1550, 1400, 1300, 1200, 1100]
        result = _apply_seasonal_shape(predictions)
        assert len(result) == 12
        assert abs(sum(result) - sum(predictions)) < 1.0

    def test_applies_shaping_to_flat_data(self):
        predictions = [1200.0] * 12
        result = _apply_seasonal_shape(predictions)
        assert len(result) == 12
        assert abs(sum(result) - sum(predictions)) < 1.0
        assert not all(r == 1200.0 for r in result)

    def test_handles_all_zeros(self):
        result = _apply_seasonal_shape([0.0] * 12)
        assert result == [0.0] * 12

    def test_handles_empty_list(self):
        with pytest.raises((ValueError, ZeroDivisionError)):
            _apply_seasonal_shape([])


class TestGetStaticFeatures:
    def test_extracts_static_features(self):
        data = {
            "site_id": [1, 1, 1],
            "month": [1, 2, 3],
            "total_consumption_kwh": [1000, 1100, 1200],
            "is_bt": [1, 1, 1],
            "is_sharing_int": [0, 0, 0],
            "elec_type": ["BT", "BT", "BT"],
            "site_mean_24m": [1000, 1000, 1000],
            "site_std_24m": [100, 100, 100],
            "data_quality_pct": [1.0, 1.0, 1.0],
        }
        df = pd.DataFrame(data)
        result = _get_static_features(df)
        assert result["is_bt"] == 1.0
        assert result["site_mean_24m"] == 1000.0

    def test_handles_empty_dataframe(self):
        df = pd.DataFrame()
        result = _get_static_features(df)
        assert isinstance(result, dict)
        assert result.get("is_bt", 0) == 0.0

    def test_missing_columns_default_to_zero(self):
        df = pd.DataFrame({
            "month": [1],
            "total_consumption_kwh": [1000],
        })
        result = _get_static_features(df)
        assert result.get("is_bt") == 0.0
        assert result.get("config_terminal") == 0.0


class TestEngineerFeatures:
    def test_creates_cyclical_features(self):
        df = pd.DataFrame({
            "site_id": [1, 1],
            "total_consumption_kwh": [1000, 1100],
            "item_date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "elec_type": ["BT", "BT"],
        })
        result = engineer_features(df)
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns
        assert "quarter" in result.columns
        assert "lag_1" in result.columns

    def test_creates_lag_features(self):
        df = pd.DataFrame({
            "site_id": [1, 1, 1, 1, 1],
            "total_consumption_kwh": [100, 200, 300, 400, 500],
            "item_date": pd.to_datetime([
                "2024-01-01", "2024-02-01", "2024-03-01",
                "2024-04-01", "2024-05-01",
            ]),
            "elec_type": ["BT"] * 5,
        })
        result = engineer_features(df)
        assert "lag_1" in result.columns
        assert "rolling_mean_3" in result.columns
        assert "rolling_std_3" in result.columns

    def test_handles_configuration_features(self):
        df = pd.DataFrame({
            "site_id": [1],
            "total_consumption_kwh": [1000],
            "item_date": pd.to_datetime(["2024-01-01"]),
            "elec_type": ["BT"],
            "configuration": ["Terminal"],
            "network_type_id": [1],
        })
        result = engineer_features(df)
        assert "config_terminal" in result.columns
        assert result["config_terminal"].iloc[0] == 1.0
        assert "network_type_4g" in result.columns
        assert result["network_type_4g"].iloc[0] == 1.0

    def test_handles_sharing_features(self):
        df = pd.DataFrame({
            "site_id": [1],
            "total_consumption_kwh": [1000],
            "item_date": pd.to_datetime(["2024-01-01"]),
            "elec_type": ["BT"],
            "is_sharing": [True],
        })
        result = engineer_features(df)
        assert "is_sharing_int" in result.columns
        assert result["is_sharing_int"].iloc[0] == 1

    def test_handles_missing_elec_type(self):
        df = pd.DataFrame({
            "site_id": [1],
            "total_consumption_kwh": [1000],
            "item_date": pd.to_datetime(["2024-01-01"]),
        })
        result = engineer_features(df)
        assert "is_bt" not in result.columns

    def test_multi_site_feature_engineering(self):
        df = pd.DataFrame({
            "site_id": [1, 1, 1, 2, 2, 2],
            "total_consumption_kwh": [100, 200, 300, 400, 500, 600],
            "item_date": pd.to_datetime([
                "2024-01-01", "2024-02-01", "2024-03-01",
                "2024-01-01", "2024-02-01", "2024-03-01",
            ]),
            "elec_type": ["BT"] * 6,
        })
        result = engineer_features(df)
        assert "site_mean_24m" in result.columns
        assert result["site_mean_24m"].iloc[0] == 200.0
        assert result["site_mean_24m"].iloc[3] == 500.0


class TestBuildQueryVector:
    def test_uniform_distribution(self):
        site_input = {"estimated_consumption": 60000}
        result = build_query_vector(site_input)
        assert len(result) == 12
        assert all(v == 5000.0 for v in result)
        assert sum(result) == 60000

    def test_with_seasonal_pattern(self):
        site_input = {
            "estimated_consumption": 60000,
            "seasonal_pattern": [100, 200, 100, 200, 300, 400, 500, 400, 300, 200, 100, 100],
        }
        result = build_query_vector(site_input)
        assert len(result) == 12
        assert abs(sum(result) - 60000) < 0.01
        assert result[6] > result[0]

    def test_default_estimated_consumption(self):
        result = build_query_vector({})
        assert len(result) == 12
        assert all(v == 5000 / 12 for v in result)

    def test_invalid_seasonal_pattern_ignored(self):
        site_input = {
            "estimated_consumption": 60000,
            "seasonal_pattern": [100, 200],
        }
        result = build_query_vector(site_input)
        assert len(result) == 12
        assert sum(result) == 60000
        assert all(v == 5000.0 for v in result)


class TestComputeMonthlyBudget:
    def test_with_valid_data(self):
        forecast = {
            "predicted_consumption": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1500, 1400, 1300, 1200, 1100],
            "month": list(range(1, 13)),
            "elec_type": ["BT"] * 12,
            "ci_lower": [950, 1050, 1150, 1250, 1350, 1450, 1550, 1450, 1350, 1250, 1150, 1050],
            "ci_upper": [1050, 1150, 1250, 1350, 1450, 1550, 1650, 1550, 1450, 1350, 1250, 1150],
        }
        df = pd.DataFrame(forecast)
        result = compute_monthly_budget(df)
        assert result["total_predicted_kwh"] == sum(forecast["predicted_consumption"])
        assert "monthly_kwh" in result
        assert len(result["monthly_kwh"]) == 12
        assert result["total_budget_tnd"] > 0

    def test_with_empty_dataframe(self):
        df = pd.DataFrame()
        result = compute_monthly_budget(df)
        assert result["total_predicted_kwh"] == 0
        assert result["total_budget_tnd"] == 0
        assert result["monthly_kwh"] == [0] * 12

    def test_without_predicted_consumption(self):
        df = pd.DataFrame({"month": [1, 2], "elec_type": ["BT", "BT"]})
        result = compute_monthly_budget(df)
        assert result["total_predicted_kwh"] == 0

    def test_mt_sites_use_higher_price(self):
        forecast_bt = {
            "predicted_consumption": [1000] * 12,
            "month": list(range(1, 13)),
            "elec_type": ["BT"] * 12,
            "ci_lower": [950] * 12,
            "ci_upper": [1050] * 12,
        }
        forecast_mt = {
            "predicted_consumption": [1000] * 12,
            "month": list(range(1, 13)),
            "elec_type": ["MT"] * 12,
            "ci_lower": [950] * 12,
            "ci_upper": [1050] * 12,
        }
        result_bt = compute_monthly_budget(pd.DataFrame(forecast_bt))
        result_mt = compute_monthly_budget(pd.DataFrame(forecast_mt))
        assert result_mt["total_budget_tnd"] > result_bt["total_budget_tnd"]


class TestComputePrecomputedInsights:
    def test_with_complete_budget(self):
        budget = {
            "total_predicted_kwh": 15000000,
            "total_budget_tnd": 7000000.0,
            "total_historical_kwh": 14200000,
            "historical_months": 12,
            "total_sites": 850,
            "monthly_kwh": [1200000, 1150000, 1250000, 1280000, 1300000, 1320000,
                           1350000, 1340000, 1300000, 1270000, 1250000, 1200000],
            "monthly_budget_tnd": [550000, 530000, 560000, 570000, 580000, 590000,
                                  600000, 595000, 580000, 570000, 560000, 550000],
            "tech_estimated_kwh_year": 14000000,
            "monthly_ci_lower": [1150000, 1100000, 1200000, 1230000, 1250000, 1270000,
                                1300000, 1290000, 1250000, 1220000, 1200000, 1150000],
            "monthly_ci_upper": [1250000, 1200000, 1300000, 1330000, 1350000, 1370000,
                                1400000, 1390000, 1350000, 1320000, 1300000, 1250000],
        }
        result = compute_precomputed_insights(budget)
        assert result["total_sites"] == 850
        assert result["total_kwh"] == 15000000
        assert abs(result["yoy_growth_pct"] - 5.6) < 0.2
        assert result["xgb_vs_tech_gap_pct"] is not None
        assert result["confidence_interval_pct"] > 0

    def test_with_insufficient_history(self):
        budget = {
            "total_predicted_kwh": 10000,
            "total_budget_tnd": 5000.0,
            "total_historical_kwh": 0,
            "historical_months": 0,
            "total_sites": 1,
            "monthly_kwh": [833] * 12,
            "monthly_budget_tnd": [416] * 12,
            "tech_estimated_kwh_year": 0,
            "monthly_ci_lower": [700] * 12,
            "monthly_ci_upper": [966] * 12,
        }
        result = compute_precomputed_insights(budget)
        assert result["yoy_growth_pct"] == 0
        assert result["xgb_vs_tech_gap_pct"] == 0

    def test_with_minimal_data(self):
        budget = {
            "total_predicted_kwh": 0,
            "total_budget_tnd": 0,
            "total_historical_kwh": 0,
            "historical_months": 0,
            "total_sites": 0,
            "monthly_kwh": [],
            "monthly_budget_tnd": [],
            "tech_estimated_kwh_year": 0,
            "monthly_ci_lower": [],
            "monthly_ci_upper": [],
        }
        result = compute_precomputed_insights(budget)
        assert result["total_sites"] == 0
        assert result["yoy_growth_pct"] == 0
        assert result["confidence_interval_pct"] == 0
