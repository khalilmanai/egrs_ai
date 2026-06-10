SYSTEM_PROMPT = """
Tu es EGRS-Intelligence, l'analyste energetique expert d'Orange Tunisie.
Tu rediges des analyses strategiques detaillees en francais.

REGLES STRICTES:
- Reponds UNIQUEMENT en francais
- Cite les chiffres cles avec leur valeur et explique LEUR SIGNIFICATION et IMPACT BUSINESS
- Ne te contente pas d'enoncer les chiffres — explique pourquoi ils sont importants
- CONSTAT → CAUSE → IMPACT → RECOMMANDATION pour chaque section
- Chaque section: 8-12 phrases, ton strategique et decisionnel
- Compare les tendances (hausse/baisse, ecarts BT/MT, saisonnalite)
- Si un contexte documentaire est fourni, reference-le dans l'analyse
- Les recommandations doivent etre specifiques, chiffrees et priorisees
"""

GLOBAL_FORECAST_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "trend_analysis": {"type": "string"},
        "key_risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["title", "description", "priority"],
            },
        },
    },
    "required": ["executive_summary", "trend_analysis", "key_risks", "recommendations"],
}

YEAR_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "performance_analysis": {"type": "string"},
        "anomaly_insights": {"type": "string"},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["title", "description", "priority"],
            },
        },
    },
    "required": ["executive_summary", "performance_analysis", "anomaly_insights", "recommendations"],
}

SITE_FORECAST_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "site_analysis": {"type": "string"},
        "key_risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["title", "description", "priority"],
            },
        },
    },
    "required": ["executive_summary", "site_analysis", "key_risks", "recommendations"],
}


def _fmt(val: float, decimals: int = 0) -> str:
    return f"{val:,.{decimals}f}"


def build_global_forecast_prompt(
    budget: dict,
    billing: list[dict] | None = None,
    insights: dict | None = None,
    health: dict | None = None,
    anomalies: dict | None = None,
    doc_context: str | None = None,
    user_prompt: str | None = None,
) -> str:
    total_kwh = budget.get("total_predicted_kwh", 0)
    total_tnd = budget.get("total_budget_tnd", 0)
    total_sites = budget.get("total_sites", 0)
    hist_kwh = budget.get("total_historical_kwh", 0)
    hist_year = budget.get("historical_year", "N-1")
    tech_kwh = budget.get("tech_estimated_kwh_year", 0)
    bt_count = budget.get("bt_site_count", 0)
    mt_count = budget.get("mt_site_count", 0)
    sfr_affected = budget.get("sfr_affected_sites", 0)
    yoy_pct = insights.get("yoy_growth_pct", 0) if insights else 0
    ci_pct = insights.get("confidence_interval_pct", 0) if insights else 0

    lines = [
        "# PREVISION BUDGETAIRE GLOBALE",
        f"Annee cible: {hist_year + 1 if isinstance(hist_year, int) else 'N'}",
        f"Sites DRS actifs: {total_sites}",
        f"Consommation historique (N-1={hist_year}): {_fmt(hist_kwh)} kWh",
        f"Consommation prevue (N+1): {_fmt(total_kwh)} kWh",
        f"Budget total prevu: {_fmt(total_tnd, 2)} TND",
        f"Sites BT: {bt_count} | Sites MT: {mt_count}",
        f"Estimation technique radio: {_fmt(tech_kwh)} kWh/an",
        f"Sites avec alertes SFR: {sfr_affected}",
        f"Variation N+1/N-1: {yoy_pct}%",
        f"Incertitude (IC 95%): +/-{ci_pct}%",
    ]

    if partial_warn := budget.get("partial_year_warning", False):
        partial_actual = budget.get("partial_year_actual_max")
        lines.append(f"ATTENTION: L'annee {partial_actual} est partielle (<12 mois). La comparaison utilise l'annee {hist_year} (complete).")

    if insights:
        lines.append(f"Ecart XGBoost vs estimation technique: {insights.get('xgb_vs_tech_gap_pct', 0)}%")

    monthly_kwh = budget.get("monthly_kwh", [])
    monthly_cost = budget.get("monthly_budget_tnd", [])
    if any(monthly_kwh):
        lines.extend(["", "# REPARTITION MENSUELLE"])
        months = ["Janvier","Fevrier","Mars","Avril","Mai","Juin",
                   "Juillet","Aout","Septembre","Octobre","Novembre","Decembre"]
        for i, (m, k, c) in enumerate(zip(months, monthly_kwh, monthly_cost)):
            lines.append(f"  {m}: {_fmt(k)} kWh ({_fmt(c,2)} TND)")

    if billing:
        lines.extend(["", "# FACTURATION N-1 PAR DIRECTION"])
        for row in billing:
            name = row.get("direction_name", f"Dir{row.get('direction_id','?')}")
            cost = float(row.get("total_cost_tnd", 0))
            kwh = float(row.get("total_consumption_kwh", 0))
            cnt = row.get("site_count", 0)
            lines.append(f"  {name} ({row.get('elec_type','')}): {_fmt(cost,2)} TND, {_fmt(kwh)} kWh, {cnt} sites")

    if health:
        lines.extend(["", "# SANTE DES SITES"])
        lines.append(f"  Score global: {health.get('overall_health', 'N/A')}/100")
        lines.append(f"  Sains: {health.get('healthy_count',0)} | Alerte: {health.get('warning_count',0)} | Critique: {health.get('critical_count',0)}")
        lines.append(f"  Alertes critiques non resolues: {health.get('unresolved_critical_alerts',0)}")
        bottom = health.get("bottom_10_sites", [])
        if bottom:
            lines.append("  Sites les plus critiques:")
            for s in bottom[:5]:
                lines.append(f"    {s.get('site_code','?')}: score {s.get('health_score',0)}/100 (alerte critique: {s.get('alerts',{}).get('critical',0)})")

    if anomalies and anomalies.get("summary"):
        s = anomalies["summary"]
        lines.extend(["", "# ANOMALIES DETECTEES"])
        lines.append(f"  Total: {s.get('total_anomalies',0)} anomalies ({s.get('zscore_count',0)} Z-score, {s.get('trend_count',0)} tendance, {s.get('iqr_count',0)} IQR)")
        for key in ["zscore", "trend", "iqr"]:
            det = anomalies.get(key, {}).get("anomalies", [])
            for a in det[:2]:
                sid = a.get("site_code") or a.get("site_id", "?")
                if key == "zscore":
                    lines.append(f"  Site {sid}: {a.get('consumption',0)} kWh (z={a.get('z_score','?')}, ecart={a.get('deviation_pct',0):+.1f}%)")
                elif key == "trend":
                    lines.append(f"  Site {sid}: {a.get('previous_kwh',0)} -> {a.get('current_kwh',0)} kWh ({a.get('pct_change',0):+.1f}%)")
                elif key == "iqr":
                    lines.append(f"  Site {sid}: {a.get('consumption',0)} kWh (hors limite IQR)")

    if doc_context:
        lines.extend(["", "# CONTEXTE DOCUMENTAIRE", doc_context[:3000]])

    if user_prompt:
        lines.extend(["", "# DEMANDE UTILISATEUR", user_prompt])

    lines.extend([
        "",
        "Redige l'analyse detaillee suivante en francais (cite les chiffres et explique leur impact):",
        "1. Resume executif: 4-5 phrases — synthese des chiffres cles, tendance principale, risque majeur, enjeu budgetaire",
        "2. Analyse des tendances: evolution N-1 vs N+1, saisonnalite, ecart BT/MT, ecart avec estimation technique",
        "3. Risques identifies: analyses chaque type d'anomalie, impact SFR, sante des sites, facteurs d'incertitude",
        "4. Recommandations: 4 a 6 actions specifiques chiffrees, priorisees (haute/moyenne/basse), avec impact attendu",
    ])

    return "\n".join(lines)


def build_year_analysis_prompt(
    health: dict,
    billing: list[dict] | None = None,
    anomalies: dict | None = None,
    sfr_analysis: dict | None = None,
    doc_context: str | None = None,
    user_prompt: str | None = None,
) -> str:
    lines = [
        "# ANALYSE DE L'ANNEE N",
        f"Score de sante global: {health.get('overall_health', 'N/A')}/100",
        f"Repartition: {health.get('healthy_count',0)} sains / {health.get('warning_count',0)} avertissements / {health.get('critical_count',0)} critiques",
        f"Total sites notes: {health.get('total_sites_scored',0)}",
        f"Alertes critiques non resolues: {health.get('unresolved_critical_alerts',0)}",
    ]

    bottom = health.get("bottom_10_sites", [])
    if bottom:
        lines.append("Sites les plus critiques:")
        for s in bottom[:5]:
            lines.append(f"  {s.get('site_code','?')}: score {s.get('health_score',0)}/100 ({s.get('classification','')})")

    if anomalies and anomalies.get("summary"):
        s = anomalies["summary"]
        lines.extend(["", "# ANOMALIES"])
        if s.get("zscore_count"):
            lines.append(f"  Z-score: {s['zscore_count']} sites")
            for a in anomalies.get("zscore", {}).get("anomalies", [])[:3]:
                lines.append(f"    Site {a.get('site_id','?')}: {a.get('consumption',0)} kWh (z={a.get('z_score','?')}, ecart={a.get('deviation_pct',0):+.1f}%)")
        if s.get("trend_count"):
            lines.append(f"  Tendance: {s['trend_count']} sites")
            for a in anomalies.get("trend", {}).get("anomalies", [])[:3]:
                lines.append(f"    Site {a.get('site_id','?')}: {a.get('previous_kwh',0)} -> {a.get('current_kwh',0)} kWh ({a.get('pct_change',0):+.1f}%)")
        if s.get("iqr_count"):
            lines.append(f"  IQR: {s['iqr_count']} sites")
            for a in anomalies.get("iqr", {}).get("anomalies", [])[:3]:
                lines.append(f"    Site {a.get('site_code',a.get('site_id','?'))}: {a.get('consumption',0)} kWh (hors limite IQR)")

    if billing:
        lines.extend(["", "# FACTURATION PAR DIRECTION"])
        for row in billing:
            name = row.get("direction_name", f"Dir{row.get('direction_id','?')}")
            cost = float(row.get("total_cost_tnd", 0))
            kwh = float(row.get("total_consumption_kwh", 0))
            lines.append(f"  {name}: {_fmt(kwh)} kWh, {_fmt(cost,2)} TND")

    if sfr_analysis:
        lines.extend(["", "# ALERTES SFR"])
        lines.append(f"  Total alertes: {sfr_analysis.get('total_sfr',0)}")
        lines.append(f"  Sites affectes: {sfr_analysis.get('sites_affected',0)}")

    if doc_context:
        lines.extend(["", "# CONTEXTE DOCUMENTAIRE", doc_context[:3000]])

    if user_prompt:
        lines.extend(["", "# DEMANDE UTILISATEUR", user_prompt])

    lines.extend([
        "",
        "Redige l'analyse detaillee suivante en francais (cite les chiffres et explique leur impact):",
        "1. Resume executif: 4-5 phrases — score sante global, problemes critiques, tendance generale, points d'attention",
        "2. Analyse des performances: repartition sains/alerte/critique, analyse des 5 plus faibles (score, consommation, alertes), impact SFR, ecarts de consommation",
        "3. Analyse des anomalies: decris chaque type (Z-score, tendance, IQR) avec sites, valeurs et directions, explique pourquoi c'est significatif",
        "4. Recommandations: 4 a 6 actions specifiques chiffrees, priorisees (haute/moyenne/basse), avec impact attendu",
    ])

    return "\n".join(lines)


def build_site_forecast_prompt(
    site_budget: dict,
    alerts: list[dict] | None = None,
    doc_context: str | None = None,
    user_prompt: str | None = None,
) -> str:
    hist_kwh = site_budget.get("historical_kwh", 0)
    pred_kwh = site_budget.get("total_predicted_kwh", 0)
    pred_tnd = site_budget.get("total_budget_tnd", 0)
    hist_year = site_budget.get("historical_year", "N-1")
    tech_kwh_m = site_budget.get("tech_estimated_kwh_month", 0)
    tech_kwh_y = site_budget.get("tech_estimated_kwh_year", 0)
    has_sfr = site_budget.get("has_sfr_alert", False)
    alert_count = site_budget.get("active_alert_count", 0)
    yoy = round(((pred_kwh - hist_kwh) / hist_kwh * 100), 1) if hist_kwh else 0

    partial_warn = site_budget.get("partial_year_warning", False)

    lines = [
        "# PREVISION SITE",
        f"Site: {site_budget.get('site_code','?')} — {site_budget.get('site_name','?')}",
        f"Configuration: {site_budget.get('configuration','?')} | Electrique: {site_budget.get('elec_type','?')}",
        f"Consommation historique (N-1={hist_year}): {_fmt(hist_kwh)} kWh",
        f"Consommation prevue (N+1): {_fmt(pred_kwh)} kWh",
        f"Budget prevu: {_fmt(pred_tnd,2)} TND",
    ]

    if partial_warn:
        lines.append("ATTENTION: Annee partielle detectee — la comparaison utilise l'annee complete precedente.")

    lines.append(f"Evolution N-1 -> N+1: {yoy}%")
    lines.append(f"Estimation technique: {_fmt(tech_kwh_y)} kWh/an ({_fmt(tech_kwh_m)} kWh/mois)")

    tech_flags = []
    for flag in ["has_2g", "has_3g", "has_4g_fdd", "has_4g_tdd", "has_5g"]:
        if site_budget.get(flag):
            tech_flags.append(flag.replace("has_", "").replace("_", " ").upper())
    if tech_flags:
        lines.append(f"Equipements radio: {', '.join(tech_flags)}")
    if has_sfr:
        lines.append("ATTENTION: Site avec alertes SFR actives — donnees historiques potentiellement incompletes")
    if alert_count:
        lines.append(f"Alertes actives: {alert_count}")

    monthly = site_budget.get("monthly_kwh", [])
    if any(monthly):
        lines.extend(["", "# CONSOMMATION MENSUELLE PREVUE (kWh)"])
        months_short = ["J","F","M","A","M","J","J","A","S","O","N","D"]
        for m_short, v in zip(months_short, monthly):
            lines.append(f"  {m_short}: {_fmt(v)}")
        lines.append(f"  Min: {_fmt(min(monthly))} | Max: {_fmt(max(monthly))} | Moy: {_fmt(sum(monthly)/12)}")

    if alerts:
        lines.extend(["", f"Alertes SFR actives ({len(alerts)})"])
        for a in alerts[:5]:
            created = str(a.get("created_at", ""))[:10]
            desc = str(a.get("description", ""))[:100]
            lines.append(f"  [{created}] {desc}")

    if doc_context:
        lines.extend(["", "# CONTEXTE DOCUMENTAIRE", doc_context[:3000]])

    if user_prompt:
        lines.extend(["", "# DEMANDE UTILISATEUR", user_prompt])

    lines.extend([
        "",
        "Redige l'analyse detaillee suivante en francais (cite les chiffres et explique leur impact):",
        "1. Resume executif: 3-4 phrases — identification, tendance de consommation, comparaison technique radio, budget, alertes eventuelles",
        "2. Analyse du site: pattern saisonnier mensuel (min/max/moyenne), impact des equipements radio, consequences des alertes SFR si presentes",
        "3. Risques: facteurs pouvant invalider la prevision (SFR, annee partielle, equipements changes), quantifie l'impact potentiel",
        "4. Recommandations: 2 a 4 actions specifiques au site, chiffrees et priorisees",
    ])

    return "\n".join(lines)
