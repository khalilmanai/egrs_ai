from datetime import datetime

BASE_CSS = """
@page {
    size: a4;
    margin: 2cm 1.8cm 2.5cm 1.8cm;
}
body {
    font-family: "Helvetica", "Arial", sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #333;
}
h1 { font-size: 18pt; color: #1a3a5c; margin-top: 0; }
h2 { font-size: 14pt; color: #1a3a5c; border-bottom: 2px solid #2E86AB; padding-bottom: 3px; margin-top: 20px; }
h3 { font-size: 11pt; color: #2E86AB; margin-top: 14px; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 7.5pt; table-layout: fixed; word-break: break-word; }
th { background: #2E86AB; color: white; padding: 4px 4px; text-align: left; font-size: 7.5pt; word-break: break-word; }
td { padding: 3px 4px; border-bottom: 1px solid #ddd; word-break: break-word; }
tr { page-break-inside: avoid; }
tr.alternate td { background: #f5f9fc; }
img.chart { width: 100%; max-width: 550px; margin: 10px 0; }
.cover { text-align: center; padding-top: 180px; }
.cover h1 { font-size: 26pt; color: #1a3a5c; margin-bottom: 8px; }
.cover .subtitle { font-size: 14pt; color: #2E86AB; margin-bottom: 30px; }
.cover .meta { font-size: 10pt; color: #666; }
.cover .logo-line { margin-top: 60px; font-size: 9pt; color: #999; }
.page-break { page-break-before: always; }
.section-desc { color: #555; margin: 4px 0 10px 0; font-style: italic; }
.badge { padding: 2px 6px; font-size: 8pt; font-weight: bold; }
.badge-h { color: #27ae60; }
.badge-l { color: #e74c3c; }
.narrative-box { background: #f8f9fa; padding: 10px; border-left: 4px solid #2E86AB; margin: 10px 0; }
.footer { text-align: center; font-size: 8pt; color: #666; }
.llm-section { margin: 10px 0; }
.llm-subhead { font-size: 10pt; color: #1a3a5c; margin: 6px 0 4px 0; border-bottom: 1px solid #ddd; padding-bottom: 2px; }
.risk-list { margin: 4px 0; padding-left: 18px; }
.risk-item { margin: 2px 0; }
.rec-list { margin: 4px 0; padding-left: 18px; }
.rec-item { margin: 4px 0; }
.prio-badge { display: inline-block; padding: 1px 5px; font-size: 7pt; font-weight: bold; border-radius: 3px; color: #fff; }
.prio-high { background: #e74c3c; }
.prio-medium { background: #f39c12; }
.prio-low { background: #27ae60; }
.llm-error { color: #e74c3c; font-style: italic; }
"""


def _fmt(val: float, decimals: int = 0) -> str:
    return f"{val:,.{decimals}f}"


def cover_page(title: str, subtitle: str, year: int, generated_at: str | None = None) -> str:
    gen = generated_at or datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""
    <div class="cover">
        <h1>{title}</h1>
        <div class="subtitle">{subtitle}</div>
        <div class="meta">Année de référence: {year}</div>
        <div class="meta">Généré le: {gen}</div>
        <div class="logo-line">Orange Tunisie — EGRS Intelligence</div>
    </div>
    """


def exec_summary_section(narrative_html: str) -> str:
    return f"""
    <h2>Résumé Exécutif</h2>
    <div class="narrative-box">{narrative_html}</div>
    """


def methodology_section() -> str:
    return """
    <h2>Méthodologie des Données</h2>
    <p>Les données de consommation sont dérivées des factures (<em>invoice_items</em>) en appliquant la formule standard:</p>
    <p><strong>kWh = ((final_sale / 1000) / 1.19) / prix_kWh</strong></p>
    <p>Le prix unitaire du kWh dépend du type électrique du site (BT: 0,396 TND, MT: 0,414 TND). Le taux de TVA est fixé à 19%. Seuls les sites DRS actifs (DirectionId=1, StatusId IN (1,3)) sont inclus.</p>
    <p>Les prévisions sont générées par un modèle XGBoost entraîné sur l'historique de consommation. Les intervalles de confiance à 95% sont calculés à partir de l'écart-type des prédictions.</p>
    """


def site_population_table(sites_data: dict) -> str:
    total = sites_data.get("total_sites", 0)
    bt = sites_data.get("bt_site_count", 0)
    mt = sites_data.get("mt_site_count", 0)
    tech_kwh = sites_data.get("tech_estimated_kwh_year", 0)
    sfr = sites_data.get("sfr_affected_sites", 0)
    return f"""
    <h2>Population des Sites</h2>
    <table>
        <tr><th>Indicateur</th><th>Valeur</th></tr>
        <tr><td>Total sites DRS actifs</td><td>{total:,}</td></tr>
        <tr class="alternate"><td>Sites BT</td><td>{bt:,}</td></tr>
        <tr><td>Sites MT</td><td>{mt:,}</td></tr>
        <tr class="alternate"><td>Estimation technique radio (kWh/an)</td><td>{tech_kwh:,.0f}</td></tr>
        <tr><td>Sites avec alertes SFR</td><td>{sfr:,}</td></tr>
    </table>
    """


def historical_performance_table(yearly_data: list[dict]) -> str:
    rows_html = ""
    for i, d in enumerate(yearly_data):
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += f"<tr{cls}><td>{d.get('year', '')}</td><td>{d.get('elec_type', '')}</td><td>{_fmt(d.get('total_consumption_kwh', 0))}</td><td>{_fmt(d.get('total_cost_tnd', 0), 2)}</td><td>{d.get('site_count', 0)}</td></tr>\n"
    return f"""
    <h2>Performances Historiques</h2>
    <table>
        <tr><th>Année</th><th>Type</th><th>kWh</th><th>Coût (TND)</th><th>Sites</th></tr>
        {rows_html}
    </table>
    """


def monthly_trends_table(monthly_data: list[dict]) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i, d in enumerate(monthly_data):
        m = d.get("month", 1) - 1
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += f"<tr{cls}><td>{months_abbr[m] if 0 <= m < 12 else m+1}</td><td>{_fmt(d.get('kwh', 0))}</td><td>{_fmt(d.get('cost_tnd', 0), 2)}</td></tr>\n"
    return f"""
    <h2>Répartition Mensuelle</h2>
    <table>
        <tr><th>Mois</th><th>kWh</th><th>TND</th></tr>
        {rows_html}
    </table>
    """


def forecast_table(kwh_values: list[float], cost_values: list[float],
                   ci_lower: list[float] | None = None, ci_upper: list[float] | None = None) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i in range(min(len(kwh_values), 12)):
        lo = ci_lower[i] if ci_lower and i < len(ci_lower) else 0
        hi = ci_upper[i] if ci_upper and i < len(ci_upper) else 0
        cls = ' class="alternate"' if i % 2 else ""
        rows_html += f"<tr{cls}><td>{months_abbr[i]}</td><td>{_fmt(kwh_values[i])}</td><td>{_fmt(cost_values[i], 2)}</td><td>{_fmt(lo)}</td><td>{_fmt(hi)}</td></tr>\n"
    total_kwh = sum(kwh_values)
    total_cost = sum(cost_values)
    return f"""
    <h2>Prévisions N+1</h2>
    <table>
        <tr><th>Mois</th><th>kWh</th><th>TND</th><th>IC-</th><th>IC+</th></tr>
        {rows_html}
        <tr style="font-weight:bold; background:#e8f0fe;"><td>Total</td><td>{_fmt(total_kwh)}</td><td>{_fmt(total_cost, 2)}</td><td></td><td></td></tr>
    </table>
    """


def mom_table(changes: list[dict]) -> str:
    months_abbr = ["Jan","Fév","Mar","Avr","Mai","Jui","Juil","Aoû","Sep","Oct","Nov","Déc"]
    rows_html = ""
    for i, c in enumerate(changes):
        m = c.get("month", 1) - 1
        pct = c.get("pct_change", 0)
        cls = ' class="alternate"' if i % 2 else ""
        color = "#27ae60" if pct >= 0 else "#e74c3c"
        rows_html += f"<tr{cls}><td>{months_abbr[m] if 0 <= m < 12 else m+1}</td><td>{_fmt(c.get('kwh', 0))}</td><td>{_fmt(c.get('prev_kwh', 0))}</td><td><span class='badge' style='color:{color};'>{pct:+.1f}%</span></td></tr>\n"
    return f"""
    <h2>Variation Mensuelle</h2>
    <table>
        <tr><th>Mois</th><th>kWh (N)</th><th>kWh (N-1)</th><th>Var</th></tr>
        {rows_html}
    </table>
    """


def yoy_table(yoy_data: dict) -> str:
    return f"""
    <h2>Variation Annuelle (YoY)</h2>
    <table>
        <tr><th>Indicateur</th><th>Valeur</th></tr>
        <tr><td>Variation globale</td><td>{yoy_data.get('overall_yoy_pct', 0):+.1f}%</td></tr>
        <tr class="alternate"><td>Consommation N (kWh)</td><td>{_fmt(yoy_data.get('total_current_kwh', 0))}</td></tr>
        <tr><td>Consommation N-1 (kWh)</td><td>{_fmt(yoy_data.get('total_previous_kwh', 0))}</td></tr>
        <tr class="alternate"><td>Sites comparés</td><td>{yoy_data.get('total_sites', 0)}</td></tr>
        <tr><td>Variation absolue moyenne</td><td>{yoy_data.get('avg_abs_change_pct', 0):.1f}%</td></tr>
    </table>
    """


def llm_section(title: str, content: str) -> str:
    return f"""
    <h2>{title}</h2>
    <div class="narrative-box">{content}</div>
    """


def appendix_section(rag_context: str | None = None) -> str:
    parts = ["""
    <div class="page-break"></div>
    <h2>Annexes</h2>
    <p>Méthode de calcul: La consommation en kWh est calculée à partir du montant final de facturation (final_sale) en appliquant la formule: ((final_sale / 1000) / 1.19) / prix_kWh. Le prix du kWh est déterminé par le type électrique du site.</p>
    <p>Modèle de prévision: XGBoost avec features de saisonnalité (month_sin, month_cos), valeurs décalées (lag_1, lag_2, lag_3, lag_12), moyennes mobiles (rolling_mean_3, rolling_std_3), et caractéristiques statiques du site.</p>
    <p>Moteur RAG: Les documents de référence (budgets, rapports) sont vectorisés via nomic-embed-text (768d) et recherchés par similarité cosinus dans PostgreSQL pgvector.</p>
    """]
    if rag_context:
        parts.append(f"<h3>Documents de Référence</h3><pre style='font-size:7pt; white-space:pre-wrap;'>{rag_context[:5000]}</pre>")
    return "\n".join(parts)


def estimated_to_reel_table(data: dict) -> str:
    reel = data.get("reel", {})
    estimated = data.get("estimated", {})
    ratio = data.get("ratio_estimated_to_reel", {})
    gap = data.get("gap_estimated_minus_reel", {})
    return f"""
    <h2>Rapport Estimé vs Réel</h2>
    <p class="section-desc">Comparaison des factures estimées (item_type=1) et réelles (item_type=0) pour l'année {data.get('year', '')}.</p>
    <table>
        <tr><th>Indicateur</th><th>Réel</th><th>Estimé</th><th>Ratio Est./Réel</th><th>Écart</th></tr>
        <tr><td>Montant facturé (TND)</td>
            <td>{_fmt(reel.get('total_final_sale_tnd', 0), 2)}</td>
            <td>{_fmt(estimated.get('total_final_sale_tnd', 0), 2)}</td>
            <td>{ratio.get('amount', 0):.4f}</td>
            <td>{gap.get('amount_pct', 0):+.2f}%</td></tr>
        <tr class="alternate"><td>Consommation (kWh)</td>
            <td>{_fmt(reel.get('total_consumption_kwh', 0))}</td>
            <td>{_fmt(estimated.get('total_consumption_kwh', 0))}</td>
            <td>{ratio.get('consumption_kwh', 0):.4f}</td>
            <td>{gap.get('consumption_kwh_pct', 0):+.2f}%</td></tr>
        <tr><td>Nombre de factures</td>
            <td>{reel.get('invoice_count', 0)}</td>
            <td>{estimated.get('invoice_count', 0)}</td>
            <td>-</td>
            <td>-</td></tr>
    </table>
    """


def full_report(css: str, cover: str, *sections: str) -> str:
    body = "\n".join(sections)
    footer = '<div class="footer"><pdf:pagenumber> / <pdf:pagecount></div>'
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>{css or BASE_CSS}</style>
</head>
<body>
{cover}
{body}
{footer}
</body>
</html>"""
