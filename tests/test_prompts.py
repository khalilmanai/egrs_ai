from llm.prompts import (
    build_global_forecast_prompt,
    build_year_analysis_prompt,
    build_site_forecast_prompt,
)


def test_build_global_forecast_prompt_minimal():
    budget = {
        "total_predicted_kwh": 1000000,
        "total_budget_tnd": 500000.0,
        "total_sites": 500,
        "total_historical_kwh": 950000,
        "historical_year": 2025,
        "tech_estimated_kwh_year": 900000,
        "bt_site_count": 300,
        "mt_site_count": 200,
        "sfr_affected_sites": 10,
        "monthly_kwh": [],
        "monthly_budget_tnd": [],
    }
    prompt = build_global_forecast_prompt(budget)
    assert "PREVISION BUDGETAIRE GLOBALE" in prompt
    assert "1,000,000" in prompt
    assert "500,000" in prompt
    assert "500" in prompt


def test_build_global_forecast_prompt_with_insights():
    budget = {
        "total_predicted_kwh": 1000000,
        "total_budget_tnd": 500000.0,
        "total_sites": 500,
        "total_historical_kwh": 950000,
        "historical_year": 2025,
        "tech_estimated_kwh_year": 900000,
        "bt_site_count": 300,
        "mt_site_count": 200,
        "sfr_affected_sites": 10,
        "monthly_kwh": [80000] * 12 + [90000],
        "monthly_budget_tnd": [40000] * 12 + [45000],
    }
    insights = {
        "yoy_growth_pct": 5.3,
        "confidence_interval_pct": 3.2,
        "xgb_vs_tech_gap_pct": 11.1,
    }
    prompt = build_global_forecast_prompt(budget, insights=insights)
    assert "PREVISION BUDGETAIRE GLOBALE" in prompt
    assert "5.3%" in prompt
    assert "3.2%" in prompt
    assert "11.1%" in prompt


def test_build_year_analysis_prompt():
    health = {
        "overall_health": 78,
        "healthy_count": 300,
        "warning_count": 150,
        "critical_count": 50,
        "total_sites_scored": 500,
        "unresolved_critical_alerts": 12,
        "bottom_10_sites": [
            {"site_code": "SITE001", "health_score": 25, "classification": "critique"}
        ],
    }
    prompt = build_year_analysis_prompt(health)
    assert "ANALYSE DE L'ANNEE N" in prompt
    assert "78/100" in prompt
    assert "SITE001" in prompt


def test_build_site_forecast_prompt():
    site_budget = {
        "site_code": "SITE001",
        "site_name": "Site Test",
        "configuration": "NODAL",
        "elec_type": "BT",
        "historical_kwh": 12000,
        "total_predicted_kwh": 13000,
        "total_budget_tnd": 6500.0,
        "historical_year": 2025,
        "tech_estimated_kwh_month": 1000,
        "tech_estimated_kwh_year": 12000,
        "has_sfr_alert": False,
        "active_alert_count": 0,
        "monthly_kwh": [1000] * 12,
        "monthly_budget_tnd": [500] * 12,
        "has_2g": True,
        "has_4g_fdd": True,
        "has_5g": False,
    }
    prompt = build_site_forecast_prompt(site_budget)
    assert "PREVISION SITE" in prompt
    assert "SITE001" in prompt
    assert "13,000" in prompt
    assert "8.3%" in prompt
