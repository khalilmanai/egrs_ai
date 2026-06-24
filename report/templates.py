from datetime import datetime

# ── Brand Colors ──────────────────────────────────────────────────────────
# Orange Tunisie primary: #FF7900
# Dark navy:     #1A2A4A
# Steel blue:    #2E86AB
# Berry:         #A23B72
# Success green: #27AE60
# Warning amber: #F39C12
# Danger red:    #E74C3C
# Light bg:      #F8FAFC
# Card bg:       #FFFFFF

BASE_CSS = """
@page {
    size: a4;
    margin: 2cm 1.5cm 2.2cm 1.5cm;
    @frame footer {
        -pdf-frame-content: page-footer;
        bottom: 0.5cm;
        height: 1.2cm;
        left: 1.5cm;
        right: 1.5cm;
    }
}
body {
    font-family: "Helvetica", "Arial", sans-serif;
    font-size: 9.5pt;
    line-height: 1.55;
    color: #2c3e50;
}

/* ── Headings ────────────────────────────────────────────────────────── */
h1 { font-size: 18pt; color: #1A2A4A; margin: 0 0 4px 0; }
h2 {
    font-size: 13pt; color: #1A2A4A;
    border-bottom: 3px solid #FF7900;
    padding-bottom: 4px; margin: 22px 0 12px 0;
}
h3 { font-size: 10.5pt; color: #2E86AB; margin: 14px 0 8px 0; }
h4 { font-size: 9.5pt; color: #555; margin: 10px 0 6px 0; }

/* ── Cover Page ──────────────────────────────────────────────────────── */
.cover { text-align: center; padding-top: 160px; }
.cover .brand-bar {
    width: 80px; height: 4px; background: #FF7900;
    margin: 0 auto 30px auto;
}
.cover h1 { font-size: 26pt; color: #1A2A4A; margin-bottom: 6px; letter-spacing: -0.5pt; }
.cover .subtitle { font-size: 14pt; color: #2E86AB; margin-bottom: 8px; }
.cover .classification {
    display: inline-block; padding: 4px 16px;
    background: #1A2A4A; color: #fff;
    font-size: 7pt; letter-spacing: 2pt; text-transform: uppercase;
    margin: 20px 0;
}
.cover .meta-table { margin: 24px auto 0 auto; width: auto; font-size: 9pt; }
.cover .meta-table td { padding: 4px 14px; border: none; color: #555; text-align: left; }
.cover .meta-table td:first-child { font-weight: bold; color: #1A2A4A; text-align: right; }
.cover .footer-line { margin-top: 50px; font-size: 8pt; color: #999; }

/* ── KPI Dashboard ───────────────────────────────────────────────────── */
.kpi-row { width: 100%; }
.kpi-card {
    border: 1px solid #e0e6ed; padding: 10px 8px;
    text-align: center; vertical-align: top;
}
.kpi-value {
    font-size: 16pt; font-weight: bold; color: #1A2A4A;
    font-variant-numeric: tabular-nums;
}
.kpi-label { font-size: 7.5pt; color: #888; text-transform: uppercase; letter-spacing: 0.5pt; margin-top: 2px; }
.kpi-delta { font-size: 7.5pt; margin-top: 1px; }
.kpi-delta.pos { color: #27AE60; }
.kpi-delta.neg { color: #E74C3C; }
.kpi-delta.neutral { color: #888; }
.kpi-icon { font-size: 14pt; display: block; margin-bottom: 2px; }

/* ── Tables ───────────────────────────────────────────────────────────── */
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 7.5pt; }
th {
    background: #1A2A4A; color: white; padding: 5px 7px;
    text-align: left; font-size: 7pt; text-transform: uppercase;
    letter-spacing: 0.3pt;
}
td { padding: 4px 7px; border-bottom: 1px solid #e8ecf0; }
tr { page-break-inside: avoid; }
tr.alternate td { background: #F8FAFC; }
tr:hover td { background: #EEF2F7; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.mois { width: 10%; font-weight: bold; color: #555; }
td.kwh  { width: 27%; }
td.tnd  { width: 27%; }
td.ic   { width: 18%; }

/* ── Compact Tables (high-density data) ──────────────────────────────── */
table.compact { font-size: 6.5pt; margin: 4px 0; }
table.compact th { padding: 3px 5px; font-size: 6pt; }
table.compact td { padding: 2px 5px; }

/* ── Progress Bar ────────────────────────────────────────────────────── */
.progress-bar {
    width: 100%; background: #e8ecf0; margin: 4px 0;
    font-size: 7pt; line-height: 14px; text-align: center; color: #fff;
}
.progress-fill {
    padding: 1px 0; font-weight: bold;
}
.progress-green  .progress-fill { background: #27AE60; }
.progress-amber  .progress-fill { background: #F39C12; }
.progress-red    .progress-fill { background: #E74C3C; }
.progress-blue   .progress-fill { background: #2E86AB; }

/* ── Callout Boxes ────────────────────────────────────────────────────── */
.callout {
    padding: 8px 10px; margin: 10px 0;
    border-left: 4px solid; font-size: 8.5pt;
}
.callout-info    { background: #EBF5FB; border-color: #2E86AB; }
.callout-warning { background: #FEF9E7; border-color: #F39C12; }
.callout-danger  { background: #FDEDEC; border-color: #E74C3C; }
.callout-success { background: #E9F7EF; border-color: #27AE60; }

/* ── Narrative / LLM Sections ────────────────────────────────────────── */
.narrative-box {
    background: #F8FAFC; padding: 12px 14px;
    border-left: 4px solid #FF7900; margin: 10px 0;
    font-size: 9pt; line-height: 1.6;
}
.llm-section { margin: 10px 0; }
.llm-subhead {
    font-size: 10pt; color: #1A2A4A; margin: 8px 0 4px 0;
    border-bottom: 1px solid #ddd; padding-bottom: 2px;
}
.risk-list { margin: 4px 0; padding-left: 18px; }
.risk-item { margin: 3px 0; font-size: 8.5pt; }
.rec-list { margin: 4px 0; padding-left: 18px; }
.rec-item { margin: 5px 0; font-size: 8.5pt; }

/* ── Priority Badges ──────────────────────────────────────────────────── */
.prio-badge {
    display: inline-block; padding: 1px 6px; font-size: 6.5pt;
    font-weight: bold; color: #fff; letter-spacing: 0.3pt;
}
.prio-high   { background: #E74C3C; }
.prio-medium { background: #F39C12; }
.prio-low    { background: #27AE60; }

/* ── Status Badges ───────────────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 1px 7px; font-size: 6.5pt;
    font-weight: bold; color: #fff;
}
.badge-healthy  { background: #27AE60; }
.badge-warning  { background: #F39C12; }
.badge-critical { background: #E74C3C; }
.badge-info     { background: #2E86AB; }

/* ── Charts ───────────────────────────────────────────────────────────── */
img.chart {
    width: 100%; max-width: 520px; margin: 12px auto;
    display: block;
}

/* ── Section Description ─────────────────────────────────────────────── */
.section-desc { color: #777; margin: 2px 0 10px 0; font-style: italic; font-size: 8.5pt; }

/* ── Totals Row ───────────────────────────────────────────────────────── */
tr.total-row td {
    font-weight: bold; background: #1A2A4A; color: #fff;
    border-top: 2px solid #FF7900; padding: 5px 7px;
}

/* ── Highlight Numbers ────────────────────────────────────────────────── */
.highlight-num { font-size: 10pt; font-weight: bold; color: #1A2A4A; }

/* ── Page Footer ──────────────────────────────────────────────────────── */
#page-footer {
    text-align: center; font-size: 7pt; color: #aaa;
    border-top: 1px solid #ddd; padding-top: 4px;
}

/* ── Table of Contents ────────────────────────────────────────────────── */
.toc { margin: 20px 0; }
.toc h2 { border: none; margin-bottom: 14px; }
.toc-entry {
    padding: 4px 0; border-bottom: 1px dotted #ddd;
    font-size: 9pt;
}
.toc-entry .num { color: #FF7900; font-weight: bold; margin-right: 6px; }
.toc-entry .page { float: right; color: #aaa; }
.toc-sub { padding-left: 20px; font-size: 8.5pt; color: #555; }
"""


def _fmt(val: float, decimals: int = 0) -> str:
    return f"{val:,.{decimals}f}"


# ── Cover Page ─────────────────────────────────────────────────────────

def cover_page(title: str, subtitle: str, year: int,
               generated_at: str | None = None,
               classification: str = "CONFIDENTIEL",
               author: str = "EGRS Intelligence") -> str:
    gen = generated_at or datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""
    <div class="cover">
        <div class="brand-bar"></div>
        <h1>{title}</h1>
        <div class="subtitle">{subtitle}</div>
        <div class="classification">{classification}</div>
        <table class="meta-table">
            <tr><td>Année de référence</td><td>{year}</td></tr>
            <tr><td>Généré le</td><td>{gen}</td></tr>
            <tr><td>Auteur</td><td>{author}</td></tr>
            <tr><td>Source</td><td>EGRS — Orange Tunisie</td></tr>
        </table>
        <div class="footer-line">Orange Tunisie — EGRS Intelligence<br>Système de Management de l'Énergie</div>
    </div>
    """


# ── Table of Contents ──────────────────────────────────────────────────

def table_of_contents(sections: list[tuple[str, str]]) -> str:
    """sections: list of (label, anchor_id) tuples. Auto-numbers 1.1, 1.2, etc."""
    entries = []
    for i, (label, _) in enumerate(sections, 1):
        entries.append(f'<div class="toc-entry"><span class="num">{i:02d}</span>{label}</div>')
    return f"""
    <div class="page-break"></div>
    <div class="toc">
        <h2>Table des Matières</h2>
        {"".join(entries)}
    </div>
    <div class="page-break"></div>
    """


# ── KPI Dashboard ──────────────────────────────────────────────────────

def kpi_dashboard(kpis: list[dict]) -> str:
    """kpis: [{label, value, delta_text, delta_class ('pos'|'neg'|'neutral'), icon}]
       Renders a 3 or 4 column card grid using an HTML table (xhtml2pdf compatible).
    """
    cols = min(len(kpis), 4)
    rows_html = ""
    for i, kpi in enumerate(kpis):
        if i % cols == 0:
            if i > 0:
                rows_html += "</tr>"
            rows_html += "<tr>"
        val = kpi.get("value", "")
        lbl = kpi.get("label", "")
        delta = kpi.get("delta_text", "")
        dcls = kpi.get("delta_class", "")
        icon = kpi.get("icon", "")
        delta_html = f'<div class="kpi-delta {dcls}">{delta}</div>' if delta else ""
        icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""
        rows_html += f'<td class="kpi-card">{icon_html}<div class="kpi-value">{val}</div><div class="kpi-label">{lbl}</div>{delta_html}</td>'
    if rows_html:
        rows_html += "</tr>"
    return f'<table class="kpi-row"><tr>{rows_html}</tr></table>' if rows_html else ""


# ── Progress Bar ───────────────────────────────────────────────────────

def progress_bar(pct: float, color_class: str = "progress-blue",
                 show_label: bool = True, label: str = "") -> str:
    pct_clamped = max(0, min(100, pct))
    pct_label = label or f"{pct_clamped:.0f}%"
    return f"""
    <div class="progress-bar {color_class}">
        <div class="progress-fill" style="width:{pct_clamped:.1f}%;">{pct_label if show_label else ""}</div>
    </div>
    """


# ── Callout Boxes ──────────────────────────────────────────────────────

def callout_box(text: str, style: str = "info") -> str:
    return f'<div class="callout callout-{style}">{text}</div>'


# ── Executive Summary ──────────────────────────────────────────────────

def exec_summary_section(narrative_html: str) -> str:
    return f"""
    <h2>Résumé Exécutif</h2>
    <div class="narrative-box">{narrative_html}</div>
    """


# ── Methodology ────────────────────────────────────────────────────────

def methodology_section() -> str:
    return """
    <h2>Méthodologie des Données</h2>
    <p>Les données de consommation sont dérivées des factures (<em>invoice_items</em>) en appliquant la formule standard:</p>
    <p><strong>kWh = ((final_sale / 1000) / 1.19) / prix_kWh</strong></p>
    <p>Le prix unitaire du kWh dépend du type électrique du site (BT: 0,396 TND, MT: 0,414 TND). Le taux de TVA est fixé à 19%. Seuls les sites DRS actifs (DirectionId=1, StatusId IN (1,3)) sont inclus.</p>
    <p>Les prévisions sont générées par un modèle XGBoost entraîné sur l'historique de consommation. Les intervalles de confiance à 95% sont calculés à partir de l'écart-type des prédictions.</p>
    """


# ── Site Population ────────────────────────────────────────────────────

def site_population_table(sites_data: dict) -> str:
    total = sites_data.get("total_sites", 0)
    bt = sites_data.get("bt_site_count", 0)
    mt = sites_data.get("mt_site_count", 0)
    tech_kwh = sites_data.get("tech_estimated_kwh_year", 0)
    sfr = sites_data.get("sfr_affected_sites", 0)
    return f"""
    <h2>Population des Sites</h2>
    <table>
        <tr><th style="width:60%;">Indicateur</th><th style="width:40%;">Valeur</th></tr>
        <tr><td>Total sites DRS actifs</td><td class="num highlight-num">{total:,}</td></tr>
        <tr class="alternate"><td>Sites BT</td><td class="num">{bt:,}</td></tr>
        <tr><td>Sites MT</td><td class="num">{mt:,}</td></tr>
        <tr class="alternate"><td>Estimation technique radio (kWh/an)</td><td class="num">{tech_kwh:,.0f}</td></tr>
        <tr><td>Sites avec alertes SFR</td><td class="num">{sfr:,}</td></tr>
    </table>
    """


# ── Historical Performance ────────────────────────────────────────────

def historical_performance_table(yearly_data: list[dict]) -> str:
    rows_html = ""
    for i, d in enumerate(yearly_data):
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += (
            f"<tr{cls}>"
            f"<td>{d.get('year', '')}</td>"
            f"<td>{d.get('elec_type', '')}</td>"
            f"<td class='num'>{_fmt(d.get('total_consumption_kwh', 0))}</td>"
            f"<td class='num'>{_fmt(d.get('total_cost_tnd', 0), 2)}</td>"
            f"<td class='num'>{d.get('site_count', 0)}</td>"
            f"</tr>\n"
        )
    return f"""
    <h2>Performances Historiques</h2>
    <table>
        <tr><th>Année</th><th>Type</th><th>kWh</th><th>Coût (TND)</th><th>Sites</th></tr>
        {rows_html}
    </table>
    """


# ── Monthly Trends ─────────────────────────────────────────────────────

def monthly_trends_table(monthly_data: list[dict]) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i, d in enumerate(monthly_data):
        m = d.get("month", 1) - 1
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += (
            f"<tr{cls}>"
            f"<td class='mois'>{months_abbr[m] if 0 <= m < 12 else m+1}</td>"
            f"<td class='num kwh'>{_fmt(d.get('kwh', 0))}</td>"
            f"<td class='num tnd'>{_fmt(d.get('cost_tnd', 0), 2)}</td>"
            f"</tr>\n"
        )
    return f"""
    <h2>Répartition Mensuelle</h2>
    <table>
        <colgroup><col><col><col></colgroup>
        <tr><th style='width:10%'>Mois</th><th style='width:45%'>kWh</th><th style='width:45%'>TND</th></tr>
        {rows_html}
    </table>
    """


# ── Forecast Table ─────────────────────────────────────────────────────

def forecast_table(kwh_values: list[float], cost_values: list[float],
                   ci_lower: list[float] | None = None,
                   ci_upper: list[float] | None = None) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i in range(min(len(kwh_values), 12)):
        lo = ci_lower[i] if ci_lower and i < len(ci_lower) else 0
        hi = ci_upper[i] if ci_upper and i < len(ci_upper) else 0
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += (
            f"<tr{cls}>"
            f"<td class='mois'>{months_abbr[i]}</td>"
            f"<td class='num kwh'>{_fmt(kwh_values[i])}</td>"
            f"<td class='num tnd'>{_fmt(cost_values[i], 2)}</td>"
            f"<td class='num ic'>{_fmt(lo)}</td>"
            f"<td class='num ic'>{_fmt(hi)}</td>"
            f"</tr>\n"
        )
    total_kwh = sum(kwh_values)
    total_cost = sum(cost_values)
    return f"""
    <h2>Prévisions N+1</h2>
    <table>
        <colgroup><col><col><col><col><col></colgroup>
        <tr><th style='width:10%'>Mois</th><th style='width:27%'>kWh</th><th style='width:27%'>TND</th><th style='width:18%'>IC-</th><th style='width:18%'>IC+</th></tr>
        {rows_html}
        <tr class="total-row"><td>Total</td><td class="num">{_fmt(total_kwh)}</td><td class="num">{_fmt(total_cost, 2)}</td><td></td><td></td></tr>
    </table>
    <div class="callout callout-info">L'intervalle de confiance à 95% reflète l'incertitude du modèle XGBoost. Plus l'écart est large, plus la prévision est incertaine.</div>
    """


# ── MoM Table ──────────────────────────────────────────────────────────

def mom_table(changes: list[dict]) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i, c in enumerate(changes):
        m = c.get("month", 1) - 1
        pct = c.get("pct_change", 0)
        cls = ' class="alternate"' if i % 2 else ""
        color = "#27AE60" if pct >= 0 else "#E74C3C"
        rows_html += (
            f"<tr{cls}>"
            f"<td class='mois'>{months_abbr[m] if 0 <= m < 12 else m+1}</td>"
            f"<td class='num'>{_fmt(c.get('kwh', 0))}</td>"
            f"<td class='num'>{_fmt(c.get('prev_kwh', 0))}</td>"
            f"<td class='num'><span style='color:{color};font-weight:bold;'>{pct:+.1f}%</span></td>"
            f"</tr>\n"
        )
    return f"""
    <h2>Variation Mensuelle (MoM)</h2>
    <table>
        <colgroup><col><col><col><col></colgroup>
        <tr><th style='width:10%'>Mois</th><th style='width:30%'>kWh (N)</th><th style='width:30%'>kWh (N-1)</th><th style='width:30%'>Variation</th></tr>
        {rows_html}
    </table>
    """


# ── YoY Table ──────────────────────────────────────────────────────────

def yoy_table(yoy_data: dict) -> str:
    overall = yoy_data.get("overall_yoy_pct", 0)
    color = "#27AE60" if overall >= 0 else "#E74C3C"
    arrow = "\u25B2" if overall >= 0 else "\u25BC"
    return f"""
    <h2>Variation Annuelle (YoY)</h2>
    <div class="callout callout-info" style="text-align:center;font-size:11pt;">
        Variation globale: <span style="color:{color};font-weight:bold;">{overall:+.1f}%</span> {arrow}
    </div>
    <table>
        <tr><th style="width:60%;">Indicateur</th><th style="width:40%;">Valeur</th></tr>
        <tr><td>Consommation N (kWh)</td><td class="num">{_fmt(yoy_data.get('total_current_kwh', 0))}</td></tr>
        <tr class="alternate"><td>Consommation N-1 (kWh)</td><td class="num">{_fmt(yoy_data.get('total_previous_kwh', 0))}</td></tr>
        <tr><td>Sites comparés</td><td class="num">{yoy_data.get('total_sites', 0)}</td></tr>
        <tr class="alternate"><td>Variation absolue moyenne</td><td class="num">{yoy_data.get('avg_abs_change_pct', 0):.1f}%</td></tr>
    </table>
    """


# ── Estimated vs Real ──────────────────────────────────────────────────

def estimated_to_reel_table(data: dict) -> str:
    reel = data.get("reel", {})
    estimated = data.get("estimated", {})
    ratio = data.get("ratio_estimated_to_reel", {})
    gap = data.get("gap_estimated_minus_reel", {})
    amount_gap = gap.get("amount_pct", 0)
    kwh_gap = gap.get("consumption_kwh_pct", 0)
    amount_color = "#27AE60" if amount_gap >= 0 else "#E74C3C"
    kwh_color = "#27AE60" if kwh_gap >= 0 else "#E74C3C"
    return f"""
    <h2>Rapport Estimé vs Réel</h2>
    <p class="section-desc">Comparaison des factures estimées (item_type=1) et réelles (item_type=0) pour l'année {data.get('year', '')}.</p>
    <table>
        <tr><th>Indicateur</th><th>Réel</th><th>Estimé</th><th>Ratio Est./Réel</th><th>Écart</th></tr>
        <tr><td>Montant facturé (TND)</td>
            <td class="num">{_fmt(reel.get('total_final_sale_tnd', 0), 2)}</td>
            <td class="num">{_fmt(estimated.get('total_final_sale_tnd', 0), 2)}</td>
            <td class="num">{ratio.get('amount', 0):.4f}</td>
            <td class="num"><span style="color:{amount_color};font-weight:bold;">{amount_gap:+.2f}%</span></td></tr>
        <tr class="alternate"><td>Consommation (kWh)</td>
            <td class="num">{_fmt(reel.get('total_consumption_kwh', 0))}</td>
            <td class="num">{_fmt(estimated.get('total_consumption_kwh', 0))}</td>
            <td class="num">{ratio.get('consumption_kwh', 0):.4f}</td>
            <td class="num"><span style="color:{kwh_color};font-weight:bold;">{kwh_gap:+.2f}%</span></td></tr>
        <tr><td>Nombre de factures</td>
            <td class="num">{reel.get('invoice_count', 0)}</td>
            <td class="num">{estimated.get('invoice_count', 0)}</td>
            <td class="num">-</td>
            <td class="num">-</td></tr>
    </table>
    """


# ── Cost Analysis ──────────────────────────────────────────────────────

def cost_analysis_table(monthly_data: list[dict], total_kwh: float, total_cost: float) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i, d in enumerate(monthly_data):
        m = d.get("month", 1) - 1
        kwh = d.get("kwh", 0)
        cost = d.get("cost_tnd", 0)
        avg_cost_per_kwh = cost / kwh if kwh else 0
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += (
            f"<tr{cls}>"
            f"<td class='mois'>{months_abbr[m] if 0 <= m < 12 else m+1}</td>"
            f"<td class='num'>{_fmt(kwh)}</td>"
            f"<td class='num'>{_fmt(cost, 2)}</td>"
            f"<td class='num'>{_fmt(avg_cost_per_kwh, 3)}</td>"
            f"</tr>\n"
        )
    avg_overall = total_cost / total_kwh if total_kwh else 0
    return f"""
    <h2>Analyse des Coûts</h2>
    <p class="section-desc">Répartition des coûts par mois et coût unitaire moyen du kWh.</p>
    <table>
        <tr><th style='width:10%'>Mois</th><th style='width:30%'>kWh</th><th style='width:30%'>Coût (TND)</th><th style='width:30%'>TND/kWh</th></tr>
        {rows_html}
        <tr class="total-row"><td>Total</td><td class="num">{_fmt(total_kwh)}</td><td class="num">{_fmt(total_cost, 2)}</td><td class="num">{_fmt(avg_overall, 3)}</td></tr>
    </table>
    <div class="callout callout-info">Coût unitaire moyen pondéré: <strong>{avg_overall:.3f} TND/kWh</strong></div>
    """


# ── Site Ranking Table ─────────────────────────────────────────────────

def site_ranking_table(sites: list[dict], title: str = "Classement des Sites",
                       max_rows: int = 10) -> str:
    if not sites:
        return ""
    rows_html = ""
    for i, s in enumerate(sites[:max_rows]):
        cls = ' class="alternate"' if i % 2 else ""
        score = s.get("health_score", 0)
        badge_cls = "badge-healthy" if score >= 80 else ("badge-warning" if score >= 50 else "badge-critical")
        rows_html += (
            f"<tr{cls}>"
            f"<td class='num'>{i + 1}</td>"
            f"<td>{s.get('site_code', '')}</td>"
            f"<td>{s.get('site_name', '')}</td>"
            f"<td class='num'>{_fmt(s.get('consumption_kwh', 0))}</td>"
            f"<td class='num'><span class='badge {badge_cls}'>{score:.0f}</span></td>"
            f"<td>{s.get('classification', '')}</td>"
            f"</tr>\n"
        )
    return f"""
    <h2>{title}</h2>
    <table class="compact">
        <tr><th>#</th><th>Code</th><th>Nom</th><th>kWh</th><th>Score</th><th>État</th></tr>
        {rows_html}
    </table>
    """


# ── Alert Breakdown Table ──────────────────────────────────────────────

def alert_breakdown_table(breakdown: list[dict], total: int) -> str:
    if not breakdown:
        return ""
    rows_html = ""
    for i, a in enumerate(breakdown):
        cls = ' class="alternate"' if i % 2 else ""
        severity = str(a.get("severity", "")).lower()
        badge_cls = {"critical": "badge-critical", "high": "badge-warning",
                      "medium": "badge-info", "low": "badge-healthy"}.get(severity, "badge-info")
        rows_html += (
            f"<tr{cls}>"
            f"<td>{a.get('type', '')}</td>"
            f"<td><span class='badge {badge_cls}'>{a.get('severity', '')}</span></td>"
            f"<td>{a.get('status', '')}</td>"
            f"<td>{a.get('category', '')}</td>"
            f"<td class='num'>{a.get('cnt', 0)}</td>"
            f"</tr>\n"
        )
    return f"""
    <h2>Répartition des Alertes</h2>
    <p class="section-desc">Total: <strong>{total}</strong> alertes actives.</p>
    <table class="compact">
        <tr><th>Type</th><th>Sévérité</th><th>Statut</th><th>Catégorie</th><th>Nombre</th></tr>
        {rows_html}
    </table>
    """


# ── Anomaly Summary Table ──────────────────────────────────────────────

def anomaly_summary_table(summary: dict) -> str:
    return f"""
    <h2>Détection d'Anomalies</h2>
    <table>
        <tr><th>Type d'anomalie</th><th>Nombre de sites</th><th>Seuil</th></tr>
        <tr>
            <td>Z-score (consommation anormale)</td>
            <td class="num">{summary.get('zscore_count', 0)}</td>
            <td>|z| > 2</td>
        </tr>
        <tr class="alternate">
            <td>Tendance (changement brutal)</td>
            <td class="num">{summary.get('trend_count', 0)}</td>
            <td>Variation > 50%</td>
        </tr>
        <tr>
            <td>IQR (hors interquartile)</td>
            <td class="num">{summary.get('iqr_count', 0)}</td>
            <td>Hors [Q1-1.5*IQR, Q3+1.5*IQR]</td>
        </tr>
        <tr class="total-row">
            <td>Total</td>
            <td class="num">{summary.get('total_anomalies', 0)}</td>
            <td></td>
        </tr>
    </table>
    """


# ── Health Score Section ───────────────────────────────────────────────

def health_score_section(health: dict, health_chart_b64: str = "") -> str:
    overall = health.get("overall_health", 0)
    healthy = health.get("healthy_count", 0)
    warning = health.get("warning_count", 0)
    critical = health.get("critical_count", 0)
    total = health.get("total_sites_scored", 0) or 1

    bar_color = "progress-green" if overall >= 80 else ("progress-amber" if overall >= 50 else "progress-red")
    chart_html = f'<img class="chart" src="data:image/png;base64,{health_chart_b64}" alt="Santé des sites"/>' if health_chart_b64 else ""

    return f"""
    <h2>Santé des Sites</h2>
    <table>
        <tr><th style="width:50%;">Indicateur</th><th style="width:50%;">Valeur</th></tr>
        <tr><td>Score global de santé</td>
            <td class="num"><span class="highlight-num">{overall:.1f}</span> / 100</td></tr>
        <tr class="alternate"><td>Sites sains (≥80)</td>
            <td class="num"><span class="badge badge-healthy">{healthy}</span> ({healthy/total*100:.0f}%)</td></tr>
        <tr><td>Sites en alerte (50-79)</td>
            <td class="num"><span class="badge badge-warning">{warning}</span> ({warning/total*100:.0f}%)</td></tr>
        <tr class="alternate"><td>Sites critiques (&lt;50)</td>
            <td class="num"><span class="badge badge-critical">{critical}</span> ({critical/total*100:.0f}%)</td></tr>
        <tr><td>Alertes critiques non résolues</td>
            <td class="num">{health.get('unresolved_critical_alerts', 0)}</td></tr>
    </table>
    {progress_bar(overall, bar_color, label=f"Score global: {overall:.0f} / 100")}
    {chart_html}
    """


# ── Peer Comparison Table (for site reports) ───────────────────────────

def peer_comparison_table(site_kwh: float, site_type: str,
                          peers: dict) -> str:
    """peers: {avg_kwh, site_count, min_kwh, max_kwh}"""
    pct_of_avg = (site_kwh / peers.get("avg_kwh", 1) * 100) if peers.get("avg_kwh") else 0
    color = "#27AE60" if abs(pct_of_avg - 100) < 15 else ("#F39C12" if abs(pct_of_avg - 100) < 30 else "#E74C3C")
    return f"""
    <h2>Comparaison entre Pairs</h2>
    <p class="section-desc">Consommation du site vs la moyenne des sites {site_type}.</p>
    <table>
        <tr><th style="width:60%;">Indicateur</th><th style="width:40%;">Valeur</th></tr>
        <tr><td>Type électrique</td><td>{site_type}</td></tr>
        <tr class="alternate"><td>Consommation du site (kWh)</td><td class="num highlight-num">{_fmt(site_kwh)}</td></tr>
        <tr><td>Moyenne des pairs (kWh)</td><td class="num">{_fmt(peers.get('avg_kwh', 0))}</td></tr>
        <tr class="alternate"><td>Minimum des pairs (kWh)</td><td class="num">{_fmt(peers.get('min_kwh', 0))}</td></tr>
        <tr><td>Maximum des pairs (kWh)</td><td class="num">{_fmt(peers.get('max_kwh', 0))}</td></tr>
        <tr class="alternate"><td>Nombre de pairs</td><td class="num">{peers.get('site_count', 0)}</td></tr>
        <tr><td>Ratio site / moyenne</td><td class="num"><span style="color:{color};font-weight:bold;">{pct_of_avg:.1f}%</span></td></tr>
    </table>
    """


# ── LLM Narrative Section ─────────────────────────────────────────────

def llm_section(title: str, content: str) -> str:
    return f"""
    <h2>{title}</h2>
    <div class="narrative-box">{content}</div>
    """


# ── Appendix ───────────────────────────────────────────────────────────

def appendix_section(rag_context: str | None = None) -> str:
    parts = ["""
    <div class="page-break"></div>
    <h2>Annexes</h2>
    <h3>Méthode de calcul</h3>
    <p>La consommation en kWh est calculée à partir du montant final de facturation (final_sale) en appliquant la formule: ((final_sale / 1000) / 1.19) / prix_kWh. Le prix du kWh est déterminé par le type électrique du site.</p>
    <h3>Modèle de prévision</h3>
    <p>XGBoost avec 300 arbres (max_depth=6), features de saisonnalité (month_sin, month_cos), valeurs décalées (lag_1, lag_2, lag_3, lag_12), moyennes mobiles (rolling_mean_3, rolling_std_3), et caractéristiques statiques du site.</p>
    <h3>Moteur RAG</h3>
    <p>Les documents de référence (budgets, rapports) sont vectorisés via nomic-embed-text (768d) et recherchés par similarité cosinus dans PostgreSQL pgvector.</p>
    <h3>Score de santé</h3>
    <p>Le score de santé (0-100) combine: consommation anormale (z-score), nombre et sévérité des alertes, ancienneté des alertes SFR, et stabilité de la consommation.</p>
    """]
    if rag_context:
        parts.append(f"<h3>Documents de Référence</h3><pre style='font-size:7pt; white-space:pre-wrap;'>{rag_context[:5000]}</pre>")
    return "\n".join(parts)


# ── Full Report Wrapper ────────────────────────────────────────────────

def full_report(css: str, cover: str, *sections: str) -> str:
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>{css or BASE_CSS}</style>
</head>
<body>
{cover}
{body}
<div id="page-footer">
    <pdf:pagenumber> / <pdf:pagecount> &mdash; Orange Tunisie — EGRS Intelligence
</div>
</body>
</html>"""
