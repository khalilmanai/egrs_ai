import base64
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

FRENCH_MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

COLORS = {
    "primary": "#FF7A01",
    "secondary": "#333333",
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#17a2b8",
}


def _to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close(fig)
    return img_b64


def generate_monthly_trend_chart(monthly_kwh: list[float], title: str = "Monthly Consumption Forecast (kWh)") -> str:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    months = FRENCH_MONTHS[:len(monthly_kwh)]
    x = range(len(months))
    ax.bar(x, monthly_kwh, color=COLORS["primary"], width=0.6, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("kWh", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold", color=COLORS["secondary"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout()
    return _to_base64(fig)


def generate_direction_pie_chart(direction_data: list[dict], value_key: str = "total_consumption_kwh") -> str:
    fig, ax = plt.subplots(figsize=(5, 4))
    labels = [d.get("direction_name", f"Dir {i}") for i, d in enumerate(direction_data)]
    values = [d.get(value_key, 0) for d in direction_data]
    if not values or sum(values) == 0:
        values = [1]
        labels = ["No data"]
    colors_pie = [COLORS["primary"], COLORS["info"], COLORS["success"], COLORS["warning"], COLORS["danger"]]
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%", startangle=90,
        colors=colors_pie[:len(values)],
        textprops={"fontsize": 9},
    )
    ax.legend(wedges, labels, loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.1))
    ax.set_title("Consommation par Direction", fontsize=11, fontweight="bold", color=COLORS["secondary"])
    fig.tight_layout()
    return _to_base64(fig)


def generate_top_sites_chart(sites: list[dict], value_key: str = "consumption_kwh") -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    sites = sites[:10]
    names = [s.get("site_code", s.get("site_name", f"Site {i}"))[:20] for i, s in enumerate(sites)]
    values = [s.get(value_key, 0) for s in sites]
    y_pos = range(len(names))
    ax.barh(y_pos, values, color=COLORS["primary"], height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("kWh", fontsize=10)
    ax.set_title("Top 10 Sites - Consommation", fontsize=11, fontweight="bold", color=COLORS["secondary"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout()
    return _to_base64(fig)


def generate_alert_severity_chart(alert_summary: dict) -> str:
    fig, ax = plt.subplots(figsize=(5, 4))
    breakdown = alert_summary.get("breakdown", [])
    severity_counts = {}
    for b in breakdown:
        sev = b.get("severity", "UNKNOWN")
        severity_counts[sev] = severity_counts.get(sev, 0) + b.get("cnt", 0)
    if not severity_counts:
        severity_counts = {"No alerts": 1}
    labels = list(severity_counts.keys())
    values = list(severity_counts.values())
    colors_map = {"CRITICAL": COLORS["danger"], "HIGH": COLORS["warning"],
                  "MEDIUM": COLORS["info"], "LOW": COLORS["success"]}
    colors_chart = [colors_map.get(l, COLORS["secondary"]) for l in labels]
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%", startangle=90,
        colors=colors_chart, textprops={"fontsize": 9},
    )
    ax.legend(wedges, labels, loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.1))
    ax.set_title("Alertes par Sévérité", fontsize=11, fontweight="bold", color=COLORS["secondary"])
    fig.tight_layout()
    return _to_base64(fig)


def generate_health_gauge(overall_score: float) -> str:
    fig, ax = plt.subplots(figsize=(4, 3), subplot_kw={"projection": "polar"})
    ax.set_theta_offset(1.5 * np.pi)
    ax.set_theta_direction(-1)
    ax.set_xticks(np.linspace(0, 2 * np.pi, 5))
    ax.set_xticklabels(["0", "25", "50", "75", "100"], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([])

    theta = np.linspace(0, 2 * np.pi, 100)
    r = [0.8] * 100
    colors_gradient = [
        (1, 0.3, 0.3), (1, 0.6, 0.2), (1, 0.8, 0.2),
        (0.6, 0.8, 0.2), (0.2, 0.7, 0.3),
    ]
    for i in range(5):
        start = int(i * 20)
        end = int((i + 1) * 20)
        ax.fill_between(theta[start:end], 0, r[start:end], color=colors_gradient[i], alpha=0.7)

    score_theta = (overall_score / 100) * 2 * np.pi
    ax.plot([score_theta, score_theta], [0, 0.95], color="black", linewidth=2)
    ax.plot(score_theta, 0.95, marker="v", color="black", markersize=8)

    ax.set_title(f"État de Santé Global\n{overall_score}/100", fontsize=11,
                 fontweight="bold", color=COLORS["secondary"], pad=20)
    fig.tight_layout()
    return _to_base64(fig)


def generate_all_charts(
    monthly_kwh: list[float],
    direction_data: list[dict],
    top_sites: list[dict],
    alert_summary: dict,
    health_score: float,
) -> dict:
    charts = {}
    try:
        charts["monthly_trend"] = generate_monthly_trend_chart(monthly_kwh)
    except Exception as e:
        charts["monthly_trend"] = None
    try:
        charts["direction_pie"] = generate_direction_pie_chart(direction_data)
    except Exception as e:
        charts["direction_pie"] = None
    try:
        charts["top_sites"] = generate_top_sites_chart(top_sites)
    except Exception as e:
        charts["top_sites"] = None
    try:
        charts["alert_severity"] = generate_alert_severity_chart(alert_summary)
    except Exception as e:
        charts["alert_severity"] = None
    try:
        charts["health_gauge"] = generate_health_gauge(health_score)
    except Exception as e:
        charts["health_gauge"] = None
    return charts
