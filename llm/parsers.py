import logging
import re

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {
    "global_forecast": ["executive_summary", "trend_analysis", "consumption_forecast", "budget_breakdown", "risk_assessment", "recommendations"],
    "year_analysis": ["executive_summary", "performance_analysis", "anomaly_insights", "risk_assessment", "recommendations"],
    "site_forecast": ["executive_summary", "site_analysis", "consumption_forecast", "recommendations"],
}


def parse_report_output(llm_output: dict, report_type: str = "global_forecast") -> dict:
    if "error" in llm_output:
        return {
            "status": "error",
            "error": llm_output["error"],
            "raw": llm_output.get("raw", ""),
        }

    critical = validate_report_schema(llm_output, report_type)
    if critical:
        logger.warning("LLM output missing critical fields: %s", critical)
        return {
            "status": "error",
            "error": "; ".join(critical),
            "data": llm_output,
            "partial": True,
        }

    return {
        "status": "success",
        "data": llm_output,
    }


def fixup_llm_data(data: dict, numerical_data: dict | None = None) -> dict:
    data = data or {}

    strip_dollar_from_fields(data)
    deduplicate_recommendations(data)
    backfill_consumption_forecast(data, numerical_data)
    backfill_budget_breakdown(data, numerical_data)

    return data


def strip_dollar_from_fields(data: dict):
    text_fields = ["executive_summary", "trend_analysis", "performance_analysis", "anomaly_insights", "site_analysis"]

    for key in text_fields:
        if isinstance(data.get(key), str):
            data[key] = data[key].replace("$", "")

    if "risk_assessment" in data and isinstance(data["risk_assessment"], dict):
        ra = data["risk_assessment"]
        for field in ["key_risks", "anomalies"]:
            if isinstance(ra.get(field), list):
                ra[field] = [item.replace("$", "") for item in ra[field]]

    if "recommendations" in data and isinstance(data["recommendations"], list):
        for rec in data["recommendations"]:
            for field in ["title", "description", "estimated_impact"]:
                if isinstance(rec.get(field), str):
                    rec[field] = rec[field].replace("$", "")


def deduplicate_recommendations(data: dict):
    recs = data.get("recommendations")
    if not isinstance(recs, list):
        return
    seen = set()
    unique = []
    for rec in recs:
        title = (rec.get("title") or "").strip().lower()
        if title and title not in seen:
            seen.add(title)
            unique.append(rec)
    data["recommendations"] = unique


def backfill_consumption_forecast(data: dict, numerical_data: dict | None):
    cf = data.get("consumption_forecast")
    if not isinstance(cf, dict):
        return

    bb = data.get("budget_breakdown")

    if cf.get("yoy_change_percent") in (0, None, "0", 0.0) and numerical_data:
        gb = numerical_data.get("global", {})
        hist = gb.get("total_historical_kwh", 0)
        pred = gb.get("total_predicted_kwh", 0)
        if hist and pred:
            yoy = round((pred - hist) / hist * 100, 1)
            cf["yoy_change_percent"] = yoy

    mb = cf.get("monthly_breakdown")
    if isinstance(mb, list) and mb:
        monthly_ktnd = []
        if bb and isinstance(bb.get("monthly_ktnd"), list):
            monthly_ktnd = bb["monthly_ktnd"]
        for i, item in enumerate(mb):
            cost = item.get("predicted_cost_tnd", 0)
            if not cost and i < len(monthly_ktnd):
                item["predicted_cost_tnd"] = round(monthly_ktnd[i], 2)


def backfill_budget_breakdown(data: dict, numerical_data: dict | None):
    bb = data.get("budget_breakdown")
    if not isinstance(bb, dict):
        return

    if not bb.get("total_budget_tnd") and numerical_data:
        gb = numerical_data.get("global", {})
        bb["total_budget_tnd"] = gb.get("total_ktnd", 0)


def validate_report_schema(data: dict, report_type: str = "global_forecast") -> list[str]:
    critical = []
    required = REQUIRED_FIELDS.get(report_type, REQUIRED_FIELDS["global_forecast"])

    for key in required:
        if key not in data or not data.get(key):
            critical.append(f"Missing or empty: {key}")

    if "recommendations" in data and isinstance(data["recommendations"], list):
        for i, rec in enumerate(data["recommendations"]):
            if not rec.get("title"):
                rec["title"] = (rec.get("description") or f"Recommandation {i+1}")[:80]
            if not rec.get("description"):
                rec["description"] = rec.get("title", f"Recommandation {i+1}")
            if not rec.get("priority"):
                rec["priority"] = "medium"
            if not rec.get("estimated_impact"):
                rec["estimated_impact"] = "Non quantifié"

    if "risk_assessment" in data and data["risk_assessment"]:
        ra = data["risk_assessment"]
        if not ra.get("key_risks"):
            ra["key_risks"] = ["Risques non spécifiés par l'analyse LLM"]
        if not ra.get("confidence_level"):
            ra["confidence_level"] = "Modéré"
        if not ra.get("anomalies"):
            ra["anomalies"] = ["Aucune anomalie spécifique détectée"]
    elif "risk_assessment" in required and "risk_assessment" not in data:
        data["risk_assessment"] = {
            "key_risks": ["Risques non spécifiés"],
            "confidence_level": "Modéré",
            "anomalies": ["Aucune anomalie spécifique détectée"],
        }

    for fallback_field in ["trend_analysis", "budget_breakdown", "consumption_forecast"]:
        if fallback_field in required and fallback_field not in data:
            if fallback_field == "consumption_forecast":
                data[fallback_field] = {"total_predicted_kwh": 0, "monthly_breakdown": []}
            elif fallback_field == "budget_breakdown":
                data[fallback_field] = {"total_budget_tnd": 0, "by_direction": [], "by_elec_type": {}, "monthly_ktnd": []}
            else:
                data[fallback_field] = data.get("executive_summary", "Analyse non disponible.")

    return critical
