GLOBAL_FORECAST_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "trend_analysis": {"type": "string"},
        "consumption_forecast": {
            "type": "object",
            "properties": {
                "total_predicted_kwh": {"type": "number"},
                "monthly_breakdown": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "month": {"type": "integer"},
                            "predicted_kwh": {"type": "number"},
                            "predicted_cost_tnd": {"type": "number"},
                        },
                    },
                },
                "yoy_change_percent": {"type": "number"},
                "confidence_level": {"type": "string"},
            },
        },
        "budget_breakdown": {
            "type": "object",
            "properties": {
                "total_budget_tnd": {"type": "number"},
                "by_direction": {"type": "array", "items": {"type": "object"}},
                "by_elec_type": {"type": "object"},
                "monthly_ktnd": {"type": "array", "items": {"type": "number"}},
            },
        },
        "risk_assessment": {
            "type": "object",
            "properties": {
                "anomalies": {"type": "array", "items": {"type": "string"}},
                "confidence_level": {"type": "string"},
                "key_risks": {"type": "array", "items": {"type": "string"}},
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string"},
                    "estimated_impact": {"type": "string"},
                },
                "required": ["title", "description"],
            },
        },
    },
    "required": ["executive_summary", "trend_analysis", "consumption_forecast", "budget_breakdown", "risk_assessment", "recommendations"],
}

YEAR_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "performance_analysis": {"type": "string"},
        "anomaly_insights": {"type": "string"},
        "risk_assessment": {
            "type": "object",
            "properties": {
                "key_risks": {"type": "array", "items": {"type": "string"}},
                "critical_sites_count": {"type": "integer"},
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["title", "description"],
            },
        },
    },
    "required": ["executive_summary", "performance_analysis", "anomaly_insights", "risk_assessment", "recommendations"],
}

SITE_FORECAST_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "site_analysis": {"type": "string"},
        "consumption_forecast": {
            "type": "object",
            "properties": {
                "predicted_kwh": {"type": "number"},
                "monthly_breakdown": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "month": {"type": "integer"},
                            "predicted_kwh": {"type": "number"},
                        },
                    },
                },
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["title", "description"],
            },
        },
    },
    "required": ["executive_summary", "site_analysis", "consumption_forecast", "recommendations"],
}

SYSTEM_PROMPT_BASE = """IMPORTANT : Tu DOIS répondre en français. Toute l'analyse doit être rédigée en français, pas en anglais.

Tu es un analyste énergétique expert pour la plateforme EGRS d'Orange Tunisie. Tu produis des rapports d'intelligence économique détaillés et stratégiques.

RÈGLES CRITIQUES :
- Rédige 6-10 phrases riches par section en français. Sois approfondi, analytique et axé sur les données.
- Cite toujours des chiffres précis : totaux, pourcentages, mois min/max, évolutions N-1 → N+1.
- Compare et contraste : par direction, par type d'électricité (BT vs MT), pics et creux mensuels.
- Nomenclature : N = année en cours, N-1 = année précédente (référence historique), N+1 = année de prévision.
- Toutes les valeurs monétaires en Dinar Tunisien (TND) ou Kilo-TND (KTND = 1000 TND). N'utilise JAMAIS le symbole $.
- Toutes les valeurs énergétiques en kilowatt-heures (kWh).
- Pour les recommandations : chaque recommandation DOIT avoir un **title** (phrase d'action courte en français), une **description** (3-4 phrases en français expliquant le problème, l'action proposée et le résultat attendu), **priority** (high/medium/low), et **estimated_impact** (quantifié si possible, en français).
- Produis UNIQUEMENT du JSON valide correspondant au schéma spécifié.
- N'invente jamais de chiffres — utilise uniquement ceux fournis dans le contexte.
- Adopte un ton de consultant d'entreprise : stratégique, tourné vers l'avenir, conscient des risques.
"""


def _fmt(val: float, decimals: int = 0) -> str:
    return f"{val:,.{decimals}f}"


def build_global_forecast_prompt(
    global_budget: dict,
    billing_summary: list[dict],
    rag_context: str | None = None,
    user_prompt: str | None = None,
) -> str:
    total_kwh = global_budget.get("total_predicted_kwh", 0)
    total_sites = global_budget.get("total_sites", 0)
    total_hist = global_budget.get("total_historical_kwh", 0)
    total_ktnd = global_budget.get("total_ktnd", 0)
    tech_kwh = global_budget.get("tech_estimated_kwh_year", 0)
    hist_year = global_budget.get("historical_year", "N-1")

    lines = [
        f"## Contexte de la Prévision Budgétaire Globale",
        f"- Année cible (N+1) : {_fmt(total_kwh)} kWh prévus sur {total_sites} sites DRS",
        f"- Référence historique (N-1 = {hist_year}) : {_fmt(total_hist)} kWh",
        f"- Budget total prévu : {_fmt(total_ktnd, 2)} KTND",
        f"- Estimation technique radio : {_fmt(tech_kwh)} kWh/an",
    ]

    monthly_kwh = global_budget.get("monthly_kwh", [])
    monthly_ktnd = global_budget.get("monthly_ktnd", [])
    if any(monthly_ktnd):
        lines.append("")
        lines.append("## Répartition Mensuelle")
        months = ["Janvier","Février","Mars","Avril","Mai","Juin",
                   "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
        kwh_min = min(monthly_kwh) if any(monthly_kwh) else 0
        kwh_max = max(monthly_kwh) if any(monthly_kwh) else 0
        kwh_min_idx = monthly_kwh.index(kwh_min) + 1 if monthly_kwh else 0
        kwh_max_idx = monthly_kwh.index(kwh_max) + 1 if monthly_kwh else 0
        lines.append(f"- Mois min : Mois {kwh_min_idx} à {_fmt(kwh_min)} kWh")
        lines.append(f"- Mois max : Mois {kwh_max_idx} à {_fmt(kwh_max)} kWh")
        lines.append(f"- Valeurs mensuelles (KTND) :")
        for m, v in zip(months, monthly_ktnd):
            lines.append(f"  - {m}: {_fmt(v, 2)} KTND ({_fmt(monthly_kwh[months.index(m)], 0)} kWh)")
        total_annual = sum(monthly_kwh)
        avg_monthly = total_annual / 12 if len(monthly_kwh) == 12 else 0
        lines.append(f"- Moyenne mensuelle : {_fmt(avg_monthly)} kWh")
        import statistics
        std_val = statistics.stdev(monthly_kwh) if len(monthly_kwh) > 1 else 0
        lines.append(f"- Écart-type mensuel : {_fmt(std_val)} kWh")

    if billing_summary:
        lines.append("")
        lines.append("## Facturation N par Direction")
        bt_count = mt_count = 0
        bt_kwh = mt_kwh = 0.0
        for row in billing_summary:
            name = row.get("direction_name", row.get("direction_id", "N/A"))
            elec = row.get("elec_type", "")
            cost = float(row.get("total_final_sale_tnd", 0) or 0)
            kwh = float(row.get("total_consumption_kwh", 0) or 0)
            cnt = row.get("site_count", 0)
            lines.append(f"- {name} ({elec}): {_fmt(cost, 2)} TND pour {_fmt(kwh)} kWh ({cnt} sites)")
            if elec == "BT":
                bt_count += cnt
                bt_kwh += kwh
            elif elec == "MT":
                mt_count += cnt
                mt_kwh += kwh
        total_b = bt_kwh + mt_kwh
        if total_b:
            lines.append(f"- Part BT : {_fmt(bt_kwh / total_b * 100, 1)}% ({bt_count} sites)")
            lines.append(f"- Part MT : {_fmt(mt_kwh / total_b * 100, 1)}% ({mt_count} sites)")

    if rag_context:
        lines.append("")
        lines.append("## Contexte RAG")
        lines.append(rag_context)

    if user_prompt:
        lines.append("")
        lines.append("## Demande Supplémentaire de l'Utilisateur")
        lines.append(user_prompt)

    lines.append("")
    lines.append("""
## Instructions Détaillées par Section

Rédige chaque section comme une analyse approfondie de 6 à 10 phrases.

### 1. Résumé Exécutif
Commence par la prévision budgétaire globale : total kWh et KTND, nombre de sites, évolution N-1 → N+1 en pourcentage.
Mets en avant les 2-3 tendances les plus importantes (hausse/baisse de consommation, patterns saisonniers).
Signale le risque ou la préoccupation principale. Termine par les perspectives stratégiques pour N+1.

### 2. Analyse des Tendances
Compare la consommation historique (N-1) vs la prévision (N+1). Calcule le changement exact en %.
Identifie les mois de pic (consommation la plus haute) et de creux (la plus basse), et explique pourquoi.
Compare BT vs MT : quelle direction consomme le plus, de combien (absolu et pourcentage).
Si les données de facturation sont disponibles, détaille par direction.

### 3. Répartition Budgétaire
Budget total prévu en TND et distribution mensuelle. Identifie les facteurs de coût.
Quels mois ont les besoins budgétaires les plus élevés et les plus bas, et quelle est la variance ?
Compare avec l'estimation technique radio : quelle part de la consommation est expliquée par les équipements vs autres facteurs.
Efficacité budgétaire (coût par site par mois).

### 4. Évaluation des Risques
Anomalies détectées dans les données : patterns mensuels inhabituels, sites aberrants, déséquilibres par direction.
Niveau de confiance dans la prévision (élevé/moyen/faible) et justification.
Risques clés : volatilité saisonnière, impact SFR non résolu, dépendance BT/MT, problèmes de qualité des données.
Facteurs pouvant affecter la précision (nouveaux sites, mises à niveau technologiques, changements tarifaires).

### 5. Recommandations
Fournis 3 à 5 recommandations spécifiques et actionnables. Chacune DOIT suivre ce format :
  - **title** : Phrase d'action courte (ex. "Optimiser la consommation BT")
  - **description** : 3-4 phrases expliquant le problème, l'action proposée, le résultat attendu et une quantification si possible
  - **priority** : "high", "medium", ou "low"
  - **estimated_impact** : Estimation chiffrée (ex. "5-8% de réduction BT, ~2M TND/an")

Exemple de recommandation :
  title: "Auditer les 50 sites BT les plus consommateurs"
  description: "Les sites BT représentent 63% de la consommation totale avec 965 sites. Un audit ciblé sur les 50 sites les plus énergivores (consommation > 100 000 kWh/an) permettrait d'identifier les gaspillages et de réduire la facture BT de 3 à 5%. Les actions correctives incluent le remplacement d'équipements obsolètes et l'optimisation de la climatisation."
  priority: "high"
  estimated_impact: "3-5% de réduction, ~250 000 TND/an"

RAPPEL : Toute l'analyse doit être rédigée en français. Pas d'anglais.
""")
    return "\n".join(lines)


def build_year_analysis_prompt(
    health_summary: dict,
    alert_summary: dict,
    sfr_analysis: dict,
    anomaly_analysis: dict,
    billing_summary: list[dict],
    rag_context: str | None = None,
) -> str:
    healthy = health_summary.get("healthy_count", 0)
    warning = health_summary.get("warning_count", 0)
    critical = health_summary.get("critical_count", 0)
    total_scored = health_summary.get("total_sites_scored", 0)
    overall = health_summary.get("overall_health", "N/A")
    unresolved = health_summary.get("unresolved_critical_alerts", 0)
    total_alerts = alert_summary.get("total_alerts", 0)
    total_sfr = sfr_analysis.get("total_sfr", 0)
    sites_sfr = sfr_analysis.get("sites_affected", 0)
    bottom_sites = health_summary.get("bottom_10_sites", [])

    lines = [
        f"## Contexte de l'Analyse de l'Année N",
        f"- Score de santé global : {overall}/100",
        f"- Répartition des sites : {healthy} sains / {warning} avertissements / {critical} critiques (sur {total_scored})",
        f"- Alertes critiques non résolues : {unresolved}",
        f"- Alertes actives totales : {total_alerts}",
        f"- Alertes SFR : {total_sfr} affectant {sites_sfr} sites DRS",
    ]

    if bottom_sites:
        lines.append("- 10 sites en bas de classement (santé la plus faible) :")
        for s in bottom_sites[:5]:
            sc = s.get("health_score", 0)
            nm = s.get("site_code", "")
            lines.append(f"  - {nm}: score {sc}/100 ({s.get('classification', '')})")

    anom = anomaly_analysis or {}
    zscore = anom.get("zscore_anomalies", {})
    trend = anom.get("trend_anomalies", {})
    iqr = anom.get("iqr_anomalies", {})
    z_count = zscore.get("stats", {}).get("anomaly_count", 0)
    z_thresh = zscore.get("stats", {}).get("z_threshold", 2.0)
    t_count = trend.get("stats", {}).get("anomaly_count", 0)
    t_pct = trend.get("stats", {}).get("change_threshold_pct", 50)
    i_count = iqr.get("anomaly_count", 0)

    if z_count:
        lines.append(f"- Anomalies Z-score : {z_count} (seuil {_fmt(z_thresh, 1)} sigma)")
        z_anomalies = zscore.get("anomalies", [])
        if z_anomalies:
            max_z = max(z_anomalies, key=lambda x: x.get("z_score", 0))
            lines.append(f"  - Plus extrême : site {max_z.get('site_id', '')} à z={_fmt(max_z.get('z_score', 0), 1)}, {_fmt(max_z.get('deviation_percent', 0), 1)}% au-dessus de la moyenne")
    if t_count:
        lines.append(f"- Anomalies de tendance (N-1 → N) : {t_count} sites avec >{t_pct}% de changement")
    if i_count:
        lines.append(f"- Anomalies IQR : {i_count}")

    if billing_summary:
        lines.append("")
        lines.append("## Résumé de Facturation par Direction")
        for row in billing_summary:
            name = row.get("direction_name", row.get("direction_id", "N/A"))
            cost = row.get("total_final_sale_tnd", 0)
            kwh = row.get("total_consumption_kwh", 0)
            cnt = row.get("site_count", 0)
            lines.append(f"- {name}: {_fmt(cost, 2)} TND pour {_fmt(kwh)} kWh ({cnt} sites)")

    if rag_context:
        lines.append("")
        lines.append("## Contexte RAG")
        lines.append(rag_context)

    lines.append("""
## Instructions Détaillées par Section

Rédige chaque section comme une analyse approfondie de 6 à 10 phrases.

### 1. Résumé Exécutif
Évaluation globale de la santé du  DRS. Chiffres clés : score de santé, répartition des sites (sains/avertissements/critiques).
Problèmes les plus critiques : alertes non résolues, sites SFR, nombre d'anomalies. Les 2-3 préoccupations majeures pour la direction.
Perspectives stratégiques : ce qui nécessite une action immédiate vs une planification à moyen terme.

### 2. Analyse des Performances
Décompose la répartition de la santé des sites : quel pourcentage est sain vs avertissement vs critique.
Analyse les 10 sites les plus faibles : patterns communs, concentration géographique/par direction.
Impact SFR : combien de sites sont affectés, durée moyenne, impact financier de la consommation non facturée.
Tendances des alertes : quels types d'alertes dominent, quelles catégories sont les plus graves.

### 3. Analyse des Anomalies
Décris les résultats de détection d'anomalies pour les trois méthodes (Z-score, IQR, tendance).
Mets en évidence les valeurs aberrantes les plus extrêmes : quels sites, de combien, et causes potentielles.
Corrélation entre anomalies et statut SFR — les sites avec des lacunes de facturation sont-ils plus susceptibles de présenter des anomalies ?
Changements de tendance N-1 → N : quels sites ont le plus changé et pourquoi.

### 4. Évaluation des Risques
Nombre de sites critiques et leurs caractéristiques. Risques liés aux alertes non résolues.
Risques de lacunes de facturation SFR : exposition financière des périodes non facturées.
Patterns d'anomalies pouvant indiquer des problèmes systémiques (problèmes de comptage, qualité des données).
Niveau de confiance dans l'exhaustivité et l'exactitude des données.

### 5. Recommandations
Fournis 3 à 5 recommandations spécifiques. Chacune DOIT avoir :
  - **title** : Phrase d'action courte
  - **description** : 3-4 phrases avec justification, chiffres précis, résultats attendus
  - **priority** : "high", "medium", ou "low"
  - Exemple : title: "Résorber les alertes SFR des 50 sites les plus critiques"

RAPPEL : Toute l'analyse doit être rédigée en français. Pas d'anglais.
""")
    return "\n".join(lines)


def build_site_forecast_prompt(
    site_info: dict,
    site_budget: dict,
    sfr_alerts: list[dict],
    rag_context: str | None = None,
) -> str:
    hist_kwh = site_info.get("historical_kwh", 0)
    pred_kwh = site_budget.get("total_predicted_kwh", 0)
    pred_ktnd = site_budget.get("total_ktnd", 0)
    hist_year = site_budget.get("historical_year", "N-1")

    lines = [
        f"## Contexte de la Prévision Site",
        f"- Site : {site_info.get('site_code', 'N/A')} — {site_info.get('site_name', 'N/A')}",
        f"- Configuration : {site_info.get('configuration', 'N/A')}",
        f"- Type d'électricité : {site_info.get('elec_type', 'N/A')}",
        f"- Consommation historique (N-1 = {hist_year}) : {_fmt(hist_kwh)} kWh",
        f"- Consommation prévue (N+1) : {_fmt(pred_kwh)} kWh",
        f"- Budget prévu : {_fmt(pred_ktnd, 2)} KTND",
        f"- Évolution N-1 → N+1 : {_fmt(((pred_kwh - hist_kwh) / hist_kwh * 100) if hist_kwh else 0, 1)}%",
    ]

    monthly_kwh = site_budget.get("monthly_kwh", [])
    if any(monthly_kwh):
        lines.append("")
        lines.append("## Consommation Mensuelle (kWh)")
        months = ["J","F","M","A","M","J","J","A","S","O","N","D"]
        for m, v in zip(months, monthly_kwh):
            lines.append(f"- {m}: {_fmt(v)} kWh")
        kwh_min = min(monthly_kwh)
        kwh_max = max(monthly_kwh)
        lines.append(f"- Min : {_fmt(kwh_min)} kWh, Max : {_fmt(kwh_max)} kWh")
        lines.append(f"- Moyenne : {_fmt(sum(monthly_kwh)/12)} kWh")

    if sfr_alerts:
        lines.append("")
        lines.append(f"## Alertes SFR Actives ({len(sfr_alerts)})")
        for a in sfr_alerts[:5]:
            created = str(a.get("created_at", ""))[:10]
            desc = a.get("description", "")[:100]
            lines.append(f"- [{created}] {desc}")

    if rag_context:
        lines.append("")
        lines.append("## Contexte RAG")
        lines.append(rag_context)

    lines.append("""
## Instructions Détaillées par Section

Rédige chaque section comme une analyse approfondie de 5 à 8 phrases.

### 1. Résumé Exécutif
Identification du site, configuration, consommation historique et prévue.
Changement clé : pourcentage d'évolution N-1 → N+1, pourquoi la consommation augmente ou diminue.
Tout problème SFR ou d'alerte affectant la fiabilité des données du site.

### 2. Analyse du Site
Pattern de consommation : quels mois sont les plus élevés/faibles et pourquoi.
Impact de la configuration : comment le setup technique (terminal/nodal/agreg) affecte la consommation.
Si des alertes SFR existent : explique la durée de la lacune de facturation et son impact sur la précision de la prévision.
Comparaison avec des sites similaires si les données de configuration technique sont disponibles.

### 3. Prévision de Consommation
Distribution mensuelle : explique le pattern saisonnier, le min et le max mensuels.
Comparaison N-1 → N+1 : comment la prévision se compare-t-elle à la performance historique.
Détection d'anomalies : toutes valeurs ou patterns mensuels inhabituels nécessitant une investigation.

### 4. Recommandations
Fournis 2 à 3 recommandations spécifiques pour ce site. Chacune DOIT avoir :
  - **title** : Phrase d'action courte
  - **description** : 2-3 phrases avec justification spécifique au site
  - **priority** : "high", "medium", ou "low"

RAPPEL : Toute l'analyse doit être rédigée en français. Pas d'anglais.
""")
    return "\n".join(lines)
