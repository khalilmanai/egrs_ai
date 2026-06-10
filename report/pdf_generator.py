import asyncio
import logging
from datetime import datetime
from io import BytesIO

from xhtml2pdf import pisa
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from analytics.forecast import compute_global_forecast, compute_site_forecast
from analytics.budget import compute_precomputed_insights
from analytics.trends import compute_yoy_change, compute_monthly_trends
from analytics.summaries import get_yearly_totals, get_site_count, get_yearly_estimated_to_reel_ratio, get_site_estimated_vs_reel_gap
from analytics.anomalies import run_all_detections
from analytics.health import compute_enterprise_health_summary
from core.alerts import get_alert_summary
from llm.client import generate_structured, LLMError
from llm.prompts import (
    SYSTEM_PROMPT,
    build_global_forecast_prompt,
    build_year_analysis_prompt,
    build_site_forecast_prompt,
    GLOBAL_FORECAST_SCHEMA,
    YEAR_ANALYSIS_SCHEMA,
    SITE_FORECAST_SCHEMA,
)
from rag.retriever import get_context_for_report
from report import templates as tpl
from report.charts import (
    yearly_consumption_bars,
    monthly_trend_lines,
    yoy_comparison_bars,
    forecast_overlay,
    mom_change_bars,
)

logger = logging.getLogger(__name__)


async def _call_llm(system: str, prompt: str, schema: dict) -> str:
    try:
        result = await generate_structured(
            system_prompt=system,
            user_prompt=prompt,
            json_schema=schema,
        )
    except LLMError as e:
        logger.warning("LLM error: %s", e)
        return '<div class="llm-section"><p class="llm-error">Analyse narrative non disponible (erreur LLM).</p></div>'
    parts = []
    if result.get("executive_summary"):
        parts.append(
            '<div class="llm-section">'
            '<h3 class="llm-subhead">Synthèse exécutive</h3>'
            f'<p>{result["executive_summary"]}</p>'
            '</div>'
        )
    analysis_key = next(
        (k for k in ("trend_analysis", "performance_analysis", "site_analysis", "anomaly_insights") if result.get(k)),
        None
    )
    if analysis_key:
        label = {
            "trend_analysis": "Analyse des tendances",
            "performance_analysis": "Analyse des performances",
            "site_analysis": "Analyse du site",
            "anomaly_insights": "Analyse des anomalies",
        }.get(analysis_key, "Analyse")
        parts.append(
            '<div class="llm-section">'
            f'<h3 class="llm-subhead">{label}</h3>'
            f'<p>{result[analysis_key]}</p>'
            '</div>'
        )
    if result.get("key_risks"):
        risks = result["key_risks"]
        if isinstance(risks, list):
            seen = set()
            unique = []
            for r in risks:
                if r not in seen:
                    seen.add(r)
                    unique.append(r)
            items = "".join(f'<li class="risk-item">{r}</li>' for r in unique)
            parts.append(
                '<div class="llm-section">'
                '<h3 class="llm-subhead">Risques identifiés</h3>'
                f'<ul class="risk-list">{items}</ul>'
                '</div>'
            )
        elif isinstance(risks, str):
            parts.append(
                '<div class="llm-section">'
                '<h3 class="llm-subhead">Risques identifiés</h3>'
                f'<p>{risks}</p>'
                '</div>'
            )
    if result.get("recommendations"):
        recs = result["recommendations"]
        if isinstance(recs, list):
            items = []
            seen_titles = set()
            for r in recs:
                if isinstance(r, dict):
                    title = r.get('title', '')
                    if title not in seen_titles:
                        seen_titles.add(title)
                        prio = r.get('priority', '').upper()
                        badge = f'<span class="prio-badge prio-{prio.lower()}">{prio}</span>'
                        items.append(f'<li class="rec-item">{badge} <strong>{title}:</strong> {r.get("description", "")}</li>')
                else:
                    items.append(f'<li class="rec-item">{r}</li>')
            parts.append(
                '<div class="llm-section">'
                '<h3 class="llm-subhead">Recommandations</h3>'
                f'<ol class="rec-list">{"".join(items)}</ol>'
                '</div>'
            )
        elif isinstance(recs, str):
            parts.append(
                '<div class="llm-section">'
                '<h3 class="llm-subhead">Recommandations</h3>'
                f'<p>{recs}</p>'
                '</div>'
            )
    return "\n".join(parts) if parts else '<div class="llm-section"><p>Analyse générée.</p></div>'


async def _compute_mom_changes(session: AsyncSession, year: int) -> list[dict]:
    current = {d["month"]: d for d in await compute_monthly_trends(session, year)}
    previous = {d["month"]: d for d in await compute_monthly_trends(session, year - 1)}
    changes = []
    for m in range(1, 13):
        cur = current.get(m, {}).get("kwh", 0)
        prev = previous.get(m, {}).get("kwh", 0)
        pct = ((cur - prev) / prev * 100) if prev else 0
        changes.append({"month": m, "kwh": cur, "prev_kwh": prev, "pct_change": pct})
    return changes


async def generate_global_forecast_pdf(
    session: AsyncSession,
    target_year: int,
) -> bytes:
    budget = await compute_global_forecast(session, target_year)
    if budget is None:
        raise ValueError("No forecast data available")

    insights = compute_precomputed_insights(budget)

    yearly_totals, monthly_trends, yoy_data, anomalies, health, alert_summary, site_count = await asyncio.gather(
        get_yearly_totals(session, target_year - 4, target_year - 1),
        compute_monthly_trends(session, target_year - 1),
        compute_yoy_change(session, target_year - 1),
        run_all_detections(session, target_year - 1),
        compute_enterprise_health_summary(session, target_year - 1),
        get_alert_summary(session),
        get_site_count(session),
    )

    mom_changes = await _compute_mom_changes(session, target_year - 1)

    budget["total_sites"] = site_count

    monthly_kwh = budget.get("monthly_kwh", [])
    monthly_cost = budget.get("monthly_budget_tnd", [])
    monthly_ci_lower = budget.get("monthly_ci_lower", [])
    monthly_ci_upper = budget.get("monthly_ci_upper", [])

    chart_yearly, chart_monthly_trend, chart_forecast, chart_mom = await asyncio.gather(
        asyncio.to_thread(yearly_consumption_bars,
            [d["year"] for d in yearly_totals],
            [d["total_consumption_kwh"] for d in yearly_totals]),
        asyncio.to_thread(monthly_trend_lines,
            [d["month"] for d in monthly_trends],
            [d["kwh"] for d in monthly_trends]),
        asyncio.to_thread(forecast_overlay,
            list(range(1, 13)),
            [d["kwh"] for d in monthly_trends],
            monthly_kwh, monthly_ci_lower, monthly_ci_upper),
        asyncio.to_thread(mom_change_bars,
            [c["month"] for c in mom_changes],
            [c["pct_change"] for c in mom_changes]),
    )

    yoy_bt = []
    yoy_mt = []
    for d in yearly_totals:
        if d["elec_type"] == "BT":
            yoy_bt.append(d["total_consumption_kwh"])
        elif d["elec_type"] == "MT":
            yoy_mt.append(d["total_consumption_kwh"])
    years_labels = sorted(set(str(d["year"]) for d in yearly_totals))
    if yoy_bt and yoy_mt:
        chart_yoy = await asyncio.to_thread(yoy_comparison_bars, years_labels, yoy_bt, yoy_mt)
    else:
        chart_yoy = ""

    prompt = build_global_forecast_prompt(
        budget=budget,
        billing=None,
        insights=insights,
        health=health,
        anomalies=anomalies,
    )

    narrative_task = _call_llm(SYSTEM_PROMPT, prompt, GLOBAL_FORECAST_SCHEMA)

    doc_context_task = get_context_for_report(
        session,
        f"Budget prévisionnel Orange Tunisie {target_year} consommation électrique sites DRS",
    )

    try:
        narrative_html, doc_context = await asyncio.wait_for(
            asyncio.gather(narrative_task, doc_context_task), timeout=180
        )
    except asyncio.TimeoutError:
        narrative_html = "<p>Analyse narrative non disponible (timeout LLM).</p>"
        doc_context = ""

    gen_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    cover = tpl.cover_page(
        "Rapport de Prévision Budgétaire Globale",
        f"Orange Tunisie — Budget N+1 ({target_year})",
        target_year,
        gen_time,
    )

    sections = [
        tpl.exec_summary_section(narrative_html),
        tpl.methodology_section(),
    ]

    site_data = {k: budget.get(k) for k in ["total_sites", "bt_site_count", "mt_site_count", "tech_estimated_kwh_year", "sfr_affected_sites"]}
    sections.append(tpl.site_population_table(site_data))

    sections.append(tpl.historical_performance_table(yearly_totals))

    sections.append(f'<img class="chart" src="data:image/png;base64,{chart_yearly}" alt="Consommation annuelle"/>')
    if chart_yoy:
        sections.append(f'<img class="chart" src="data:image/png;base64,{chart_yoy}" alt="Comparaison BT/MT"/>')

    sections.append(tpl.monthly_trends_table(monthly_trends))
    sections.append(f'<img class="chart" src="data:image/png;base64,{chart_monthly_trend}" alt="Tendance mensuelle"/>')

    sections.append(tpl.mom_table(mom_changes))
    sections.append(f'<img class="chart" src="data:image/png;base64,{chart_mom}" alt="Variation MoM"/>')

    sections.append(tpl.yoy_table(yoy_data))

    sections.append(tpl.forecast_table(monthly_kwh, monthly_cost, monthly_ci_lower, monthly_ci_upper))
    sections.append(f'<img class="chart" src="data:image/png;base64,{chart_forecast}" alt="Prévision vs historique"/>')

    if anomalies and anomalies.get("summary"):
        s = anomalies["summary"]
        sections.append(tpl.llm_section("Analyse des Anomalies",
            f"<p>{s.get('zscore_count', 0)} anomalies Z-score, {s.get('trend_count', 0)} anomalies de tendance, {s.get('iqr_count', 0)} anomalies IQR détectées.</p>"))

    if health:
        sections.append(tpl.llm_section("Santé des Sites",
            f"<p>Score global: {health.get('overall_health', 'N/A')}/100. Sain: {health.get('healthy_count', 0)}, Alerte: {health.get('warning_count', 0)}, Critique: {health.get('critical_count', 0)}.</p>"))

    sections.append(tpl.appendix_section(doc_context))

    html_str = tpl.full_report(tpl.BASE_CSS, cover, *sections)
    buf = BytesIO()
    pisa_status = await asyncio.to_thread(pisa.CreatePDF, src=html_str, dest=buf, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf error: {pisa_status.err}")
    return buf.getvalue()


async def generate_site_forecast_pdf(
    session: AsyncSession,
    site_code: str,
    target_year: int,
) -> bytes:
    site_budget = await compute_site_forecast(session, site_code, target_year)
    if site_budget is None:
        raise ValueError(f"Site '{site_code}' not found")

    site_gaps_all = await get_site_estimated_vs_reel_gap(session, target_year - 1)
    site_gap = next((g for g in site_gaps_all if g["site_code"] == site_code), None)

    monthly_kwh = site_budget.get("monthly_kwh", [])
    monthly_cost = site_budget.get("monthly_budget_tnd", [])
    monthly_ci_lower = site_budget.get("monthly_ci_lower", [])
    monthly_ci_upper = site_budget.get("monthly_ci_upper", [])

    hist_kwh = site_budget.get("historical_kwh", 0)
    pred_kwh = site_budget.get("total_predicted_kwh", 0)
    yoy_pct = ((pred_kwh - hist_kwh) / hist_kwh * 100) if hist_kwh else 0

    gen_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    cover = tpl.cover_page(
        f"Prévision Site — {site_code}",
        f"{site_budget.get('site_name', '')} | {site_budget.get('configuration', '')} | {site_budget.get('elec_type', '')}",
        target_year,
        gen_time,
    )

    chart_forecast = await asyncio.to_thread(forecast_overlay,
        list(range(1, 13)),
        [hist_kwh / 12] * 12,
        monthly_kwh,
        monthly_ci_lower,
        monthly_ci_upper,
    )

    prompt = build_site_forecast_prompt(site_budget=site_budget)
    narrative_html = await _call_llm(SYSTEM_PROMPT, prompt, SITE_FORECAST_SCHEMA)

    doc_context = await get_context_for_report(
        session,
        f"Site {site_code} {site_budget.get('site_name', '')} consommation Orange Tunisie",
    )
    if not doc_context:
        doc_context = ""

    gap_html = ""
    if site_gap:
        g = site_gap.get("gap", {})
        gap_html = f"""
        <h2>Écart Estimé vs Réel (N-1)</h2>
        <p class="section-desc">Comparaison entre factures estimées et réelles pour l'année {target_year - 1}.</p>
        <table>
            <tr><th>Indicateur</th><th>Réel</th><th>Estimé</th><th>Écart</th><th>%</th></tr>
            <tr><td>Montant facturé (TND)</td><td>{site_gap['reel']['final_sale_tnd']:,.2f}</td><td>{site_gap['estimated']['final_sale_tnd']:,.2f}</td><td>{g['amount_tnd']:,.2f}</td><td>{g['amount_pct']:+.2f}%</td></tr>
            <tr class="alternate"><td>Consommation (kWh)</td><td>{site_gap['reel']['consumption_kwh']:,.0f}</td><td>{site_gap['estimated']['consumption_kwh']:,.0f}</td><td>{g['consumption_kwh']:,.0f}</td><td>{g['consumption_kwh_pct']:+.2f}%</td></tr>
            <tr><td>Nombre de factures</td><td>{site_gap['reel']['invoice_count']}</td><td>{site_gap['estimated']['invoice_count']}</td><td>-</td><td>-</td></tr>
        </table>
        """

    sections = [
        tpl.exec_summary_section(narrative_html),
        tpl.methodology_section(),
        f"""
        <h2>Données du Site</h2>
        <table>
            <tr><th>Propriété</th><th>Valeur</th></tr>
            <tr><td>Code site</td><td>{site_code}</td></tr>
            <tr><td>Nom</td><td>{site_budget.get('site_name', '')}</td></tr>
            <tr><td>Configuration</td><td>{site_budget.get('configuration', '')}</td></tr>
            <tr><td>Type électrique</td><td>{site_budget.get('elec_type', '')}</td></tr>
            <tr><td>Consommation historique (N-1)</td><td>{hist_kwh:,.0f} kWh</td></tr>
            <tr><td>Prévision (N+1)</td><td>{pred_kwh:,.0f} kWh</td></tr>
            <tr><td>Budget prévu</td><td>{site_budget.get('total_budget_tnd', 0):,.2f} TND</td></tr>
            <tr><td>Variation YoY</td><td>{yoy_pct:+.1f}%</td></tr>
            <tr><td>Estimation technique (kWh/mois)</td><td>{site_budget.get('tech_estimated_kwh_month', 0):,.0f}</td></tr>
            <tr><td>Estimation technique (kWh/an)</td><td>{site_budget.get('tech_estimated_kwh_year', 0):,.0f}</td></tr>
        </table>
        """,
        tpl.forecast_table(monthly_kwh, monthly_cost, monthly_ci_lower, monthly_ci_upper),
        f'<img class="chart" src="data:image/png;base64,{chart_forecast}" alt="Prévision site"/>',
        gap_html,
        tpl.appendix_section(doc_context),
    ]

    html_str = tpl.full_report(tpl.BASE_CSS, cover, *sections)
    buf = BytesIO()
    pisa_status = await asyncio.to_thread(pisa.CreatePDF, src=html_str, dest=buf, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf error: {pisa_status.err}")
    return buf.getvalue()


async def generate_yearly_analysis_pdf(
    session: AsyncSession,
    year: int,
) -> bytes:
    yearly_totals, monthly_trends, yoy_data, anomalies, health, alert_summary, site_count, estimated_to_reel = await asyncio.gather(
        get_yearly_totals(session, year - 3, year),
        compute_monthly_trends(session, year),
        compute_yoy_change(session, year),
        run_all_detections(session, year),
        compute_enterprise_health_summary(session, year),
        get_alert_summary(session),
        get_site_count(session),
        get_yearly_estimated_to_reel_ratio(session, year),
    )

    mom_changes = await _compute_mom_changes(session, year)

    chart_yearly, chart_monthly, chart_mom = await asyncio.gather(
        asyncio.to_thread(yearly_consumption_bars,
            [d["year"] for d in yearly_totals],
            [d["total_consumption_kwh"] for d in yearly_totals]),
        asyncio.to_thread(monthly_trend_lines,
            [d["month"] for d in monthly_trends],
            [d["kwh"] for d in monthly_trends]),
        asyncio.to_thread(mom_change_bars,
            [c["month"] for c in mom_changes],
            [c["pct_change"] for c in mom_changes]),
    )

    yoy_bt = []
    yoy_mt = []
    for d in yearly_totals:
        if d["elec_type"] == "BT":
            yoy_bt.append(d["total_consumption_kwh"])
        elif d["elec_type"] == "MT":
            yoy_mt.append(d["total_consumption_kwh"])
    years_labels = sorted(set(str(d["year"]) for d in yearly_totals))
    chart_yoy = await asyncio.to_thread(yoy_comparison_bars, years_labels, yoy_bt, yoy_mt) if yoy_bt and yoy_mt else ""

    prompt = build_year_analysis_prompt(health=health, billing=None, anomalies=anomalies)
    narrative_html = await _call_llm(SYSTEM_PROMPT, prompt, YEAR_ANALYSIS_SCHEMA)

    doc_context = await get_context_for_report(
        session,
        f"Analyse annuelle consommation énergie Orange Tunisie {year}",
    )
    if not doc_context:
        doc_context = ""

    gen_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    cover = tpl.cover_page(
        "Rapport d'Analyse Annuelle",
        f"Orange Tunisie — Bilan {year}",
        year,
        gen_time,
    )

    sections = [
        tpl.exec_summary_section(narrative_html),
        tpl.methodology_section(),
        f"<h2>Population</h2><p>Sites DRS actifs: {site_count:,}</p>",
        tpl.estimated_to_reel_table(estimated_to_reel),
        tpl.historical_performance_table(yearly_totals),
        f'<img class="chart" src="data:image/png;base64,{chart_yearly}" alt="Consommation annuelle"/>',
        f'<img class="chart" src="data:image/png;base64,{chart_yoy}" alt="Comparaison BT/MT"/>',
        tpl.monthly_trends_table(monthly_trends),
        f'<img class="chart" src="data:image/png;base64,{chart_monthly}" alt="Tendance mensuelle"/>',
        tpl.mom_table(mom_changes),
        f'<img class="chart" src="data:image/png;base64,{chart_mom}" alt="Variation MoM"/>',
        tpl.yoy_table(yoy_data),
    ]

    if anomalies and anomalies.get("summary"):
        s = anomalies["summary"]
        sections.append(tpl.llm_section("Anomalies Détectées",
            f"<p>{s.get('zscore_count', 0)} Z-score, {s.get('trend_count', 0) or 0} tendances, {s.get('iqr_count', 0) or 0} IQR.</p>"))

    if health:
        sections.append(tpl.llm_section("Santé des Sites",
            f"<p>Score: {health.get('overall_health', 'N/A')}/100. Sain: {health.get('healthy_count', 0)}, Alerte: {health.get('warning_count', 0)}, Critique: {health.get('critical_count', 0)}.</p>"))

    sections.append(tpl.appendix_section(doc_context))

    html_str = tpl.full_report(tpl.BASE_CSS, cover, *sections)
    buf = BytesIO()
    pisa_status = await asyncio.to_thread(pisa.CreatePDF, src=html_str, dest=buf, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf error: {pisa_status.err}")
    return buf.getvalue()
