import os
import json
import asyncio
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from config.settings import get_settings
from report.puppeteer_renderer import render_pdf
from report.chart_generator import generate_all_charts

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


async def generate_global_forecast_report(
    data: dict,
) -> dict:
    settings = get_settings()
    report_id = data.get("report_id", os.urandom(16).hex())
    storage_path = settings.report_storage_path
    os.makedirs(storage_path, exist_ok=True)

    json_path = os.path.join(storage_path, f"{report_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("global_forecast.html")

    html_content = template.render(
        report_id=report_id,
        generated_at=datetime.now().isoformat(),
        data=data,
        report_data=data.get("data") if not data.get("llm_error") else {},
        numerical_data=data.get("numerical_data", {}),
        enterprise_data=data.get("enterprise_data", {}),
        charts=data.get("charts", {}),
        site_name=data.get("site_name", "All Sites"),
        llm_error=data.get("llm_error", False),
        target_year=data.get("target_year", "N/A"),
    )

    pdf_path = os.path.join(storage_path, f"{report_id}.pdf")
    try:
        await render_pdf(html_content, pdf_path)
    except Exception as e:
        pdf_path = None

    return {
        "report_id": report_id,
        "json_url": f"/reports/storage/{report_id}.json",
        "pdf_url": f"/reports/storage/{report_id}.pdf" if pdf_path else None,
    }


async def generate_year_analysis_report(
    data: dict,
) -> dict:
    settings = get_settings()
    report_id = data.get("report_id", os.urandom(16).hex())
    storage_path = settings.report_storage_path
    os.makedirs(storage_path, exist_ok=True)

    json_path = os.path.join(storage_path, f"{report_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    ed = data.get("enterprise_data", {})
    ns = data.get("numerical_data", {})
    charts = {}
    try:
        monthly_kwh = ns.get("global", {}).get("monthly_kwh", [])
        direction_data = ns.get("billing_summary", [])
        top_sites = ed.get("summary", {}).get("bottom_10_sites", [])
        alert_summary = ed.get("alert_summary", {})
        health_score = ed.get("summary", {}).get("overall_health", 0)
        charts = await asyncio.to_thread(
            generate_all_charts,
            monthly_kwh, direction_data,
            top_sites, alert_summary, health_score,
        )
    except Exception:
        charts = {}

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("year_analysis.html")

    html_content = template.render(
        report_id=report_id,
        generated_at=datetime.now().isoformat(),
        data=data,
        report_data=data.get("data") if not data.get("llm_error") else {},
        numerical_data=ns,
        enterprise_data=ed,
        charts=charts,
        llm_error=data.get("llm_error", False),
        target_year=data.get("target_year", "N/A"),
    )

    pdf_path = os.path.join(storage_path, f"{report_id}.pdf")
    try:
        await render_pdf(html_content, pdf_path)
    except Exception as e:
        pdf_path = None

    return {
        "report_id": report_id,
        "json_url": f"/reports/storage/{report_id}.json",
        "pdf_url": f"/reports/storage/{report_id}.pdf" if pdf_path else None,
    }


async def generate_site_forecast_report(
    data: dict,
) -> dict:
    settings = get_settings()
    report_id = data.get("report_id", os.urandom(16).hex())
    storage_path = settings.report_storage_path
    os.makedirs(storage_path, exist_ok=True)

    json_path = os.path.join(storage_path, f"{report_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("site_forecast.html")

    html_content = template.render(
        report_id=report_id,
        generated_at=datetime.now().isoformat(),
        data=data,
        report_data=data.get("data") if not data.get("llm_error") else {},
        numerical_data=data.get("numerical_data", {}),
        llm_error=data.get("llm_error", False),
        target_year=data.get("target_year", "N/A"),
        site_name=data.get("site_name", ""),
        site_code=data.get("site_code", ""),
    )

    pdf_path = os.path.join(storage_path, f"{report_id}.pdf")
    try:
        await render_pdf(html_content, pdf_path)
    except Exception as e:
        pdf_path = None

    return {
        "report_id": report_id,
        "json_url": f"/reports/storage/{report_id}.json",
        "pdf_url": f"/reports/storage/{report_id}.pdf" if pdf_path else None,
    }
