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
from analytics.summaries import (
    get_yearly_totals, get_site_count,
    get_yearly_estimated_to_reel_ratio,
    get_site_estimated_vs_reel_gap,
    get_billing_summary_by_direction,
)
from analytics.anomalies import run_all_detections
from analytics.health import compute_enterprise_health_summary
from core.alerts import get_alert_summary, get_sfr_analysis
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
    health_donut,
    monthly_heatmap,
    cost_trend_line,
    health_gauge,
    ranking_bars,
    estimated_vs_reel_bars,
    monthly_consumption_distribution,
)

logger = logging.getLogger(__name__)


# ── LLM caller (shared) ────────────────────────────────────────────────

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
        (k for k in ("trend_analysis", "performance_analysis", "site_analysis",
                      "anomaly_insights", "cost_analysis", "estimated_vs_reel_analysis",
                      "alert_analysis", "peer_comparison") if result.get(k)),
        None
    )
    if analysis_key:
        label_map = {
            "trend_analysis": "Analyse des tendances",
            "performance_analysis": "Analyse des performances",
            "site_analysis": "Analyse du site",
            "anomaly_insights": "Analyse des anomalies",
            "cost_analysis": "Analyse des coûts",
            "estimated_vs_reel_analysis": "Analyse Estimé vs Réel",
            "alert_analysis": "Analyse des alertes",
            "peer_comparison": "Comparaison entre pairs",
        }
        label = label_map.get(analysis_key, "Analyse")
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
            unique = [r for r in risks if not (r in seen or seen.add(r))]
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
                    title = r.get("title", "")
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        prio = r.get("priority", "").upper()
                        badge = f'<span class="prio-badge prio-{prio.lower()}">{prio}</span>'
                        items.append(f'<li class="rec-item">{badge} <strong>{title}:</strong> {r.get("description", "")}</li>')
                else:
                    items.append(f'<li class="rec-item">{r}</li>')
            if items:
                parts.append(
                    '<div class="llm-section">'
                    '<h3 class="llm-subhead">Recommandations</h3>'
                    f'<ol class="rec-list">{"".join(items)}</ol>'
                    '</div>'
                )
        elif isinstance(recs, str) and recs.strip():
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


def _build_global_kpis(budget: dict, insights: dict, health: dict,
                       anomalies: dict, yoy_data: dict) -> list[dict]:
    total_kwh = budget.get("total_predicted_kwh", 0)
    total_tnd = budget.get("total_budget_tnd", 0)
    total_sites = budget.get("total_sites", 0)
    yoy = insights.get("yoy_growth_pct", 0) if insights else 0
    health_score = health.get("overall_health", 0) if health else 0
    anomaly_count = (anomalies.get("summary", {}).get("total_anomalies", 0)
                     if anomalies and anomalies.get("summary") else 0)
    return [
        {"label": "Prévision kWh", "value": f"{total_kwh:,.0f}",
         "delta_text": f"{yoy:+.1f}% vs N-1", "delta_class": "pos" if yoy >= 0 else "neg",
         "icon": "\u26A1"},
        {"label": "Budget TND", "value": f"{total_tnd:,.0f}",
         "delta_text": "", "delta_class": "", "icon": "\u20AC"},
        {"label": "Sites actifs", "value": f"{total_sites:,}",
         "delta_text": "", "delta_class": "", "icon": "\u2302"},
        {"label": "Santé", "value": f"{health_score:.0f}/100",
         "delta_text": f"{anomaly_count} anomalies", "delta_class": "neg" if anomaly_count > 10 else "neutral",
         "icon": "\u2764"},
    ]


# ── GLOBAL FORECAST PDF ────────────────────────────────────────────────

async def generate_global_forecast_pdf(
    session: AsyncSession,
    target_year: int,
) -> bytes:
    budget = await compute_global_forecast(session, target_year)
    if budget is None:
        raise ValueError("No forecast data available")

    insights = compute_precomputed_insights(budget)

    yearly_totals, monthly_trends, yoy_data, anomalies, health, alert_summary, site_count, billing, sfr = await asyncio.gather(
        get_yearly_totals(session, target_year - 4, target_year - 1),
        compute_monthly_trends(session, target_year - 1),
        compute_yoy_change(session, target_year - 1),
        run_all_detections(session, target_year - 1),
        compute_enterprise_health_summary(session, target_year - 1),
        get_alert_summary(session),
        get_site_count(session),
        get_billing_summary_by_direction(session, target_year - 1),
        get_sfr_analysis(session),
    )

    mom_changes = await _compute_mom_changes(session, target_year - 1)

    budget["total_sites"] = site_count
    monthly_kwh = budget.get("monthly_kwh", [])
    monthly_cost = budget.get("monthly_budget_tnd", [])
    monthly_ci_lower = budget.get("monthly_ci_lower", [])
    monthly_ci_upper = budget.get("monthly_ci_upper", [])

    # ── Charts ──────────────────────────────────────────────────────
    chart_yearly, chart_monthly_trend, chart_forecast, chart_mom, chart_health_donut, chart_health_gauge, chart_cost = await asyncio.gather(
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
        asyncio.to_thread(health_donut,
            health.get("healthy_count", 0) if health else 0,
            health.get("warning_count", 0) if health else 0,
            health.get("critical_count", 0) if health else 0),
        asyncio.to_thread(health_gauge,
            health.get("overall_health", 0) if health else 0),
        asyncio.to_thread(cost_trend_line,
            [d["month"] for d in monthly_trends],
            [d["kwh"] for d in monthly_trends],
            [d["cost_tnd"] for d in monthly_trends]),
    )

    yoy_bt = []
    yoy_mt = []
    for d in yearly_totals:
        if d["elec_type"] == "BT":
            yoy_bt.append(d["total_consumption_kwh"])
        elif d["elec_type"] == "MT":
            yoy_mt.append(d["total_consumption_kwh"])
    years_labels = sorted(set(str(d["year"]) for d in yearly_totals))
    chart_yoy = ""
    if yoy_bt and yoy_mt:
        chart_yoy = await asyncio.to_thread(yoy_comparison_bars, years_labels, yoy_bt, yoy_mt)

    # ── Charts for sections after LLM delay ─────────────────────────
    chart_bottom = await asyncio.to_thread(ranking_bars,
        health.get("bottom_10_sites", []) if health else [],
        title="Sites les Plus Critiques")

    # ── LLM ─────────────────────────────────────────────────────────
    prompt = build_global_forecast_prompt(
        budget=budget,
        billing=billing,
        insights=insights,
        health=health,
        anomalies=anomalies,
        alert_summary=alert_summary,
        sfr_analysis=sfr,
        mom_changes=mom_changes,
        estimated_to_reel=None,
        yearly_totals=yearly_totals,
        ci_lower=monthly_ci_lower,
        ci_upper=monthly_ci_upper,
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

    # ── Build sections ──────────────────────────────────────────────
    gen_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    cover = tpl.cover_page(
        "Rapport de Prévision Budgétaire Globale",
        f"Orange Tunisie — Budget N+1 ({target_year})",
        target_year, gen_time,
    )

    kpis = _build_global_kpis(budget, insights, health, anomalies, yoy_data)
    kpi_dashboard = tpl.kpi_dashboard(kpis)

    toc_sections = [
        ("Résumé Exécutif", "exec-summary"),
        ("Indicateurs Clés", "kpi"),
        ("Population des Sites", "population"),
        ("Performances Historiques", "historical"),
        ("Tendances Mensuelles", "monthly-trends"),
        ("Santé des Sites", "health"),
        ("Détection d'Anomalies", "anomalies"),
        ("Alertes", "alerts"),
        ("Analyse des Coûts", "cost"),
        ("Variation Annuelle (YoY)", "yoy"),
        ("Prévisions N+1", "forecast"),
        ("Recommandations", "recommendations"),
        ("Annexes", "appendix"),
    ]
    toc = tpl.table_of_contents(toc_sections)

    sections = [
        # 1. Executive summary
        tpl.exec_summary_section(narrative_html),

        # 2. KPI Dashboard
        '<h2>Indicateurs Clés</h2>',
        kpi_dashboard,

        # 3. Methodology
        tpl.methodology_section(),

        # 4. Site Population
        tpl.site_population_table(
            {k: budget.get(k) for k in ["total_sites", "bt_site_count", "mt_site_count",
                                          "tech_estimated_kwh_year", "sfr_affected_sites"]}
        ),

        # 5. Historical Performance
        tpl.historical_performance_table(yearly_totals),
        f'<img class="chart" src="data:image/png;base64,{chart_yearly}" alt="Consommation annuelle"/>',
    ]
    if chart_yoy:
        sections.append(f'<img class="chart" src="data:image/png;base64,{chart_yoy}" alt="Comparaison BT/MT"/>')

    sections += [
        # 6. Monthly Trends
        '<div class="page-break"></div>',
        tpl.monthly_trends_table(monthly_trends),
        f'<img class="chart" src="data:image/png;base64,{chart_monthly_trend}" alt="Tendance mensuelle"/>',
        tpl.mom_table(mom_changes),
        f'<img class="chart" src="data:image/png;base64,{chart_mom}" alt="Variation MoM"/>',

        # 7. Health
        '<div class="page-break"></div>',
        tpl.health_score_section(health, chart_health_donut) if health else "",
        f'<img class="chart" src="data:image/png;base64,{chart_health_gauge}" alt="Jauge de santé"/>',
    ]
    if chart_bottom:
        sections.append(f'<img class="chart" src="data:image/png;base64,{chart_bottom}" alt="Sites critiques"/>')

    sections += [
        # Top 10 healthiest
        tpl.site_ranking_table(
            health.get("top_10_healthiest", []) if health else [],
            title="Sites les Plus Sains", max_rows=10
        ),
    ]

    if anomalies and anomalies.get("summary"):
        sections += [
            # 8. Anomalies
            '<div class="page-break"></div>',
            tpl.anomaly_summary_table(anomalies["summary"]),
        ]

    if alert_summary and alert_summary.get("breakdown"):
        sections += [
            # 9. Alerts
            tpl.alert_breakdown_table(alert_summary.get("breakdown", []), alert_summary.get("total_alerts", 0)),
        ]

    sections += [
        # 10. Cost Analysis
        '<div class="page-break"></div>',
        tpl.cost_analysis_table(monthly_trends,
                                sum(d.get("kwh", 0) for d in monthly_trends),
                                sum(d.get("cost_tnd", 0) for d in monthly_trends)),
        f'<img class="chart" src="data:image/png;base64,{chart_cost}" alt="Coût vs consommation"/>',

        # 11. YoY
        tpl.yoy_table(yoy_data),

        # 12. Forecast
        '<div class="page-break"></div>',
        tpl.forecast_table(monthly_kwh, monthly_cost, monthly_ci_lower, monthly_ci_upper),
        f'<img class="chart" src="data:image/png;base64,{chart_forecast}" alt="Prévision vs historique"/>',

        # 13. Appendix
        tpl.appendix_section(doc_context),
    ]

    html_str = tpl.full_report(tpl.BASE_CSS, cover, toc, *sections)
    buf = BytesIO()
    pisa_status = await asyncio.to_thread(pisa.CreatePDF, src=html_str, dest=buf, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf error: {pisa_status.err}")
    return buf.getvalue()


# ── SITE FORECAST PDF ──────────────────────────────────────────────────

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
        target_year, gen_time,
    )

    # Charts
    chart_forecast, chart_est_vs_reel, chart_health_g = await asyncio.gather(
        asyncio.to_thread(forecast_overlay,
            list(range(1, 13)),
            [hist_kwh / 12] * 12, monthly_kwh,
            monthly_ci_lower, monthly_ci_upper),
        asyncio.to_thread(estimated_vs_reel_bars,
            site_gap["reel"]["consumption_kwh"] if site_gap else 0,
            site_gap["estimated"]["consumption_kwh"] if site_gap else 0,
            site_gap["reel"]["final_sale_tnd"] if site_gap else 0,
            site_gap["estimated"]["final_sale_tnd"] if site_gap else 0,
            title="Estimé vs Réel (N-1)") if site_gap else asyncio.to_thread(lambda: ""),
        asyncio.to_thread(health_gauge, 50),  # placeholder; site-level health not available
    )

    # LLM
    prompt = build_site_forecast_prompt(
        site_budget=site_budget,
        alerts=None,
        estimated_vs_reel_gap=site_gap,
    )
    narrative_html = await _call_llm(SYSTEM_PROMPT, prompt, SITE_FORECAST_SCHEMA)

    doc_context = await get_context_for_report(
        session,
        f"Site {site_code} {site_budget.get('site_name', '')} consommation Orange Tunisie",
    )
    if not doc_context:
        doc_context = ""

    # Gap table
    gap_html = ""
    if site_gap:
        g = site_gap.get("gap", {})
        gap_html = f"""
        <h2>Écart Estimé vs Réel (N-1)</h2>
        <p class="section-desc">Comparaison entre factures estimées et réelles pour l'année {target_year - 1}.</p>
        <table>
            <tr><th>Indicateur</th><th>Réel</th><th>Estimé</th><th>Écart</th><th>%</th></tr>
            <tr><td>Montant facturé (TND)</td>
                <td class="num">{site_gap['reel']['final_sale_tnd']:,.2f}</td>
                <td class="num">{site_gap['estimated']['final_sale_tnd']:,.2f}</td>
                <td class="num">{g['amount_tnd']:,.2f}</td>
                <td class="num" style="color:{'#27AE60' if g['amount_pct']>=0 else '#E74C3C'};font-weight:bold;">{g['amount_pct']:+.2f}%</td></tr>
            <tr class="alternate"><td>Consommation (kWh)</td>
                <td class="num">{site_gap['reel']['consumption_kwh']:,.0f}</td>
                <td class="num">{site_gap['estimated']['consumption_kwh']:,.0f}</td>
                <td class="num">{g['consumption_kwh']:,.0f}</td>
                <td class="num" style="color:{'#27AE60' if g['consumption_kwh_pct']>=0 else '#E74C3C'};font-weight:bold;">{g['consumption_kwh_pct']:+.2f}%</td></tr>
            <tr><td>Nombre de factures</td>
                <td class="num">{site_gap['reel']['invoice_count']}</td>
                <td class="num">{site_gap['estimated']['invoice_count']}</td>
                <td class="num">-</td>
                <td class="num">-</td></tr>
        </table>
        """
    chart_est = f'<img class="chart" src="data:image/png;base64,{chart_est_vs_reel}" alt="Estimé vs Réel"/>' if chart_est_vs_reel else ""

    # Tech equipment indicators
    tech_flags = []
    for flag in ["has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g"]:
        if site_budget.get(flag):
            tech_flags.append(flag.replace("has_", "").replace("_", " ").upper())
    tech_html = f"<p>{' | '.join(tech_flags)}</p>" if tech_flags else "<p>Aucun équipement radio documenté</p>"

    sections = [
        tpl.exec_summary_section(narrative_html),

        # KPI Dashboard
        '<h2>Indicateurs Clés</h2>',
        tpl.kpi_dashboard([
            {"label": "Code site", "value": site_code, "delta_text": "", "delta_class": "", "icon": ""},
            {"label": "kWh historique", "value": f"{hist_kwh:,.0f}", "delta_text": "", "delta_class": "", "icon": "\u26A1"},
            {"label": "kWh prévu", "value": f"{pred_kwh:,.0f}", "delta_text": f"{yoy_pct:+.1f}%", "delta_class": "pos" if yoy_pct >= 0 else "neg", "icon": ""},
            {"label": "Budget TND", "value": f"{site_budget.get('total_budget_tnd', 0):,.0f}", "delta_text": "", "delta_class": "", "icon": "\u20AC"},
        ]),

        # Site Details
        '<h2>Données du Site</h2>',
        f"""
        <table>
            <tr><th style="width:40%;">Propriété</th><th style="width:60%;">Valeur</th></tr>
            <tr><td>Code site</td><td><strong>{site_code}</strong></td></tr>
            <tr class="alternate"><td>Nom</td><td>{site_budget.get('site_name', '')}</td></tr>
            <tr><td>Configuration</td><td>{site_budget.get('configuration', '')}</td></tr>
            <tr class="alternate"><td>Type électrique</td><td>{site_budget.get('elec_type', '')}</td></tr>
            <tr><td>Consommation historique (N-1)</td><td class="num">{hist_kwh:,.0f} kWh</td></tr>
            <tr class="alternate"><td>Prévision (N+1)</td><td class="num">{pred_kwh:,.0f} kWh</td></tr>
            <tr><td>Budget prévu</td><td class="num">{site_budget.get('total_budget_tnd', 0):,.2f} TND</td></tr>
            <tr class="alternate"><td>Variation YoY</td><td class="num" style="color:{'#27AE60' if yoy_pct>=0 else '#E74C3C'};font-weight:bold;">{yoy_pct:+.1f}%</td></tr>
            <tr><td>Estimation technique radio</td><td class="num">{site_budget.get('tech_estimated_kwh_month', 0):,.0f} kWh/mois ({site_budget.get('tech_estimated_kwh_year', 0):,.0f} kWh/an)</td></tr>
            <tr class="alternate"><td>Alertes SFR actives</td><td>{'<span class="badge badge-critical">Oui</span>' if site_budget.get('has_sfr_alert') else '<span class="badge badge-healthy">Non</span>'}</td></tr>
            <tr><td>Équipements radio</td><td>{tech_html}</td></tr>
        </table>
        """,

        # Forecast
        '<div class="page-break"></div>',
        '<h2>Prévision Mensuelle</h2>',
        tpl.forecast_table(monthly_kwh, monthly_cost, monthly_ci_lower, monthly_ci_upper),
        f'<img class="chart" src="data:image/png;base64,{chart_forecast}" alt="Prévision site"/>',

        # Estimated vs Real
        gap_html,
        chart_est,

        tpl.appendix_section(doc_context),
    ]

    html_str = tpl.full_report(tpl.BASE_CSS, cover, *sections)
    buf = BytesIO()
    pisa_status = await asyncio.to_thread(pisa.CreatePDF, src=html_str, dest=buf, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf error: {pisa_status.err}")
    return buf.getvalue()


# ── YEARLY ANALYSIS PDF ────────────────────────────────────────────────

async def generate_yearly_analysis_pdf(
    session: AsyncSession,
    year: int,
) -> bytes:
    yearly_totals, monthly_trends, yoy_data, anomalies, health, alert_summary, site_count, estimated_to_reel, billing, sfr = await asyncio.gather(
        get_yearly_totals(session, year - 3, year),
        compute_monthly_trends(session, year),
        compute_yoy_change(session, year),
        run_all_detections(session, year),
        compute_enterprise_health_summary(session, year),
        get_alert_summary(session),
        get_site_count(session),
        get_yearly_estimated_to_reel_ratio(session, year),
        get_billing_summary_by_direction(session, year),
        get_sfr_analysis(session),
    )

    mom_changes = await _compute_mom_changes(session, year)

    # Charts
    chart_yearly, chart_monthly, chart_mom, chart_health_donut, chart_health_gauge, chart_cost, chart_est_vs_reel = await asyncio.gather(
        asyncio.to_thread(yearly_consumption_bars,
            [d["year"] for d in yearly_totals],
            [d["total_consumption_kwh"] for d in yearly_totals]),
        asyncio.to_thread(monthly_trend_lines,
            [d["month"] for d in monthly_trends],
            [d["kwh"] for d in monthly_trends]),
        asyncio.to_thread(mom_change_bars,
            [c["month"] for c in mom_changes],
            [c["pct_change"] for c in mom_changes]),
        asyncio.to_thread(health_donut,
            health.get("healthy_count", 0) if health else 0,
            health.get("warning_count", 0) if health else 0,
            health.get("critical_count", 0) if health else 0),
        asyncio.to_thread(health_gauge,
            health.get("overall_health", 0) if health else 0),
        asyncio.to_thread(cost_trend_line,
            [d["month"] for d in monthly_trends],
            [d["kwh"] for d in monthly_trends],
            [d["cost_tnd"] for d in monthly_trends]),
        asyncio.to_thread(estimated_vs_reel_bars,
            estimated_to_reel.get("reel", {}).get("total_consumption_kwh", 0),
            estimated_to_reel.get("estimated", {}).get("total_consumption_kwh", 0),
            estimated_to_reel.get("reel", {}).get("total_final_sale_tnd", 0),
            estimated_to_reel.get("estimated", {}).get("total_final_sale_tnd", 0),
            title="Estimé vs Réel"),
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

    chart_bottom = await asyncio.to_thread(ranking_bars,
        health.get("bottom_10_sites", []) if health else [],
        title="Sites les Plus Critiques")

    # LLM
    prompt = build_year_analysis_prompt(
        health=health,
        billing=billing,
        anomalies=anomalies,
        sfr_analysis=sfr,
        alert_summary=alert_summary,
        estimated_to_reel=estimated_to_reel,
        mom_changes=mom_changes,
        yearly_totals=yearly_totals,
        yoy_data=yoy_data,
    )
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
        year, gen_time,
    )

    toc_sections = [
        ("Résumé Exécutif", "exec-summary"),
        ("Indicateurs Clés", "kpi"),
        ("Population", "population"),
        ("Estimé vs Réel", "est-vs-reel"),
        ("Performances Historiques", "historical"),
        ("Tendances Mensuelles", "monthly-trends"),
        ("Santé des Sites", "health"),
        ("Détection d'Anomalies", "anomalies"),
        ("Alertes", "alerts"),
        ("Analyse des Coûts", "cost"),
        ("Variation Annuelle (YoY)", "yoy"),
        ("Recommandations", "recommendations"),
        ("Annexes", "appendix"),
    ]
    toc = tpl.table_of_contents(toc_sections)

    sections = [
        tpl.exec_summary_section(narrative_html),

        '<h2>Indicateurs Clés</h2>',
        tpl.kpi_dashboard([
            {"label": "Consommation N", "value": f"{yoy_data.get('total_current_kwh', 0):,.0f}",
             "delta_text": f"{yoy_data.get('overall_yoy_pct', 0):+.1f}% vs N-1",
             "delta_class": "pos" if yoy_data.get('overall_yoy_pct', 0) >= 0 else "neg", "icon": "\u26A1"},
            {"label": "Sites actifs", "value": f"{site_count:,}",
             "delta_text": "", "delta_class": "", "icon": "\u2302"},
            {"label": "Santé", "value": f"{health.get('overall_health', 0):.0f}/100" if health else "N/A",
             "delta_text": f"{health.get('critical_count', 0)} sites critiques" if health else "",
             "delta_class": "neg" if health and health.get('critical_count', 0) > 5 else "neutral", "icon": "\u2764"},
            {"label": "Alertes SFR", "value": f"{sfr.get('total_sfr', 0)}",
             "delta_text": f"{sfr.get('sites_affected', 0)} sites" if sfr else "",
             "delta_class": "neg" if sfr and sfr.get('total_sfr', 0) > 10 else "neutral", "icon": "\u26A0"},
        ]),

        tpl.methodology_section(),

        '<h2>Population</h2>',
        f'<p>Sites DRS actifs: <strong>{site_count:,}</strong></p>',

        # Estimated vs Real
        '<div class="page-break"></div>',
        tpl.estimated_to_reel_table(estimated_to_reel),
        f'<img class="chart" src="data:image/png;base64,{chart_est_vs_reel}" alt="Estimé vs Réel"/>',

        # Historical
        tpl.historical_performance_table(yearly_totals),
        f'<img class="chart" src="data:image/png;base64,{chart_yearly}" alt="Consommation annuelle"/>',
    ]
    if chart_yoy:
        sections.append(f'<img class="chart" src="data:image/png;base64,{chart_yoy}" alt="Comparaison BT/MT"/>')

    sections += [
        # Monthly Trends
        '<div class="page-break"></div>',
        tpl.monthly_trends_table(monthly_trends),
        f'<img class="chart" src="data:image/png;base64,{chart_monthly}" alt="Tendance mensuelle"/>',
        tpl.mom_table(mom_changes),
        f'<img class="chart" src="data:image/png;base64,{chart_mom}" alt="Variation MoM"/>',

        # Health
        '<div class="page-break"></div>',
        tpl.health_score_section(health, chart_health_donut) if health else "",
        f'<img class="chart" src="data:image/png;base64,{chart_health_gauge}" alt="Jauge de santé"/>',
    ]
    if chart_bottom:
        sections.append(f'<img class="chart" src="data:image/png;base64,{chart_bottom}" alt="Sites critiques"/>')
    sections += [
        tpl.site_ranking_table(
            health.get("top_10_healthiest", []) if health else [],
            title="Sites les Plus Sains", max_rows=10
        ),
    ]

    if anomalies and anomalies.get("summary"):
        sections += [
            '<div class="page-break"></div>',
            tpl.anomaly_summary_table(anomalies["summary"]),
        ]

    if alert_summary and alert_summary.get("breakdown"):
        sections += [
            tpl.alert_breakdown_table(alert_summary.get("breakdown", []), alert_summary.get("total_alerts", 0)),
        ]

    sections += [
        # Cost
        '<div class="page-break"></div>',
        tpl.cost_analysis_table(monthly_trends,
                                sum(d.get("kwh", 0) for d in monthly_trends),
                                sum(d.get("cost_tnd", 0) for d in monthly_trends)),
        f'<img class="chart" src="data:image/png;base64,{chart_cost}" alt="Coût vs consommation"/>',

        # YoY
        tpl.yoy_table(yoy_data),

        tpl.appendix_section(doc_context),
    ]

    html_str = tpl.full_report(tpl.BASE_CSS, cover, toc, *sections)
    buf = BytesIO()
    pisa_status = await asyncio.to_thread(pisa.CreatePDF, src=html_str, dest=buf, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf error: {pisa_status.err}")
    return buf.getvalue()
