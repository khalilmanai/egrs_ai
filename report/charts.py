import io
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

MONTHS_FR = ["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"]
BRAND_NAVY = "#1A2A4A"
BRAND_ORANGE = "#FF7900"
BRAND_BLUE = "#2E86AB"
BRAND_BERRY = "#A23B72"
BRAND_GREEN = "#27AE60"
BRAND_AMBER = "#F39C12"
BRAND_RED = "#E74C3C"
LIGHT_BG = "#F8FAFC"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "figure.dpi": 150,
})


def _to_img(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    import base64
    return base64.b64encode(buf.read()).decode("utf-8")


def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#ddd")
    ax.spines["bottom"].set_color("#ddd")
    ax.tick_params(colors="#666")


# ── Existing Charts (preserved + restyled) ──────────────────────────

def yearly_consumption_bars(years: list[int], values: list[float],
                            title: str = "Consommation Annuelle (kWh)") -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    colors = [BRAND_BLUE] * len(years)
    bars = ax.bar(years, values, color=colors, width=0.6, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,.0f}", ha="center", va="bottom", fontsize=8, color=BRAND_NAVY)
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold")
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)


def monthly_trend_lines(months: list[int], values: list[float],
                        title: str = "Tendance Mensuelle (kWh)") -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(MONTHS_FR[:len(months)], values, color=BRAND_BLUE, marker="o",
            linewidth=2, markersize=4, markerfacecolor="white", markeredgewidth=1.5)
    ax.fill_between(range(len(months)), values, alpha=0.08, color=BRAND_BLUE)
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold")
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)


def yoy_comparison_bars(years: list[str], bt_values: list[float],
                        mt_values: list[float]) -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    x = np.arange(len(years))
    w = 0.35
    bars1 = ax.bar(x - w / 2, bt_values, w, label="BT", color=BRAND_BLUE, edgecolor="white")
    bars2 = ax.bar(x + w / 2, mt_values, w, label="MT", color=BRAND_BERRY, edgecolor="white")
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{bar.get_height():,.0f}", ha="center", va="bottom", fontsize=7, color=BRAND_NAVY)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{bar.get_height():,.0f}", ha="center", va="bottom", fontsize=7, color=BRAND_NAVY)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_title("Comparaison BT/MT par Année (kWh)", color=BRAND_NAVY, fontweight="bold")
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(frameon=False)
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)


def forecast_overlay(months: list[int], historical: list[float], forecast: list[float],
                     ci_lower: list[float] | None = None, ci_upper: list[float] | None = None) -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    labels = MONTHS_FR
    ax.plot(labels[:len(historical)], historical, color=BRAND_BERRY, marker="s",
            linewidth=2, label="Historique", markerfacecolor="white", markeredgewidth=1.5)
    ax.plot(labels[:len(forecast)], forecast, color=BRAND_BLUE, marker="o",
            linewidth=2, label="Prévision", markerfacecolor="white", markeredgewidth=1.5)
    if ci_lower and ci_upper:
        ax.fill_between(range(len(forecast)), ci_lower, ci_upper,
                        alpha=0.15, color=BRAND_BLUE, label="IC 95%")
    ax.set_title("Prévision vs Historique (kWh)", color=BRAND_NAVY, fontweight="bold")
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(frameon=False)
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)


def mom_change_bars(months: list[int], pct_changes: list[float]) -> str:
    fig, ax = plt.subplots(figsize=(7, 3))
    colors = [BRAND_GREEN if v >= 0 else BRAND_RED for v in pct_changes]
    ax.bar(MONTHS_FR[:len(months)], pct_changes, color=colors, width=0.6, edgecolor="white")
    for i, v in enumerate(pct_changes):
        ax.text(i, v + (0.5 if v >= 0 else -0.5), f"{v:+.1f}%",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=7, fontweight="bold")
    ax.axhline(y=0, color="gray", linewidth=0.8)
    ax.set_title("Variation Mensuelle (%)", color=BRAND_NAVY, fontweight="bold")
    ax.set_ylabel("%")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)


# ── NEW Charts ──────────────────────────────────────────────────────

def health_donut(healthy: int, warning: int, critical: int,
                 title: str = "Répartition de la Santé des Sites") -> str:
    """Donut chart showing health distribution."""
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    sizes = [healthy, warning, critical]
    colors = [BRAND_GREEN, BRAND_AMBER, BRAND_RED]
    labels = [f"Sains\n({healthy})", f"Alerte\n({warning})", f"Critique\n({critical})"]
    total = sum(sizes) or 1
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
        startangle=90, pctdistance=0.75,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2),
        textprops=dict(fontsize=8, color=BRAND_NAVY),
    )
    centre_text = f"{total}"
    ax.text(0, 0, centre_text, ha="center", va="center", fontsize=14, fontweight="bold", color=BRAND_NAVY)
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold", fontsize=10)
    fig.tight_layout()
    return _to_img(fig)


def monthly_heatmap(monthly_data: list[dict], title: str = "Consommation Mensuelle (kWh)") -> str:
    """Heatmap: months x metric (kWh)."""
    if not monthly_data:
        return ""
    values = np.array([d.get("kwh", 0) for d in monthly_data]).reshape(1, -1)
    fig, ax = plt.subplots(figsize=(7, 1.5))
    im = ax.imshow(values, cmap="YlOrRd", aspect="auto", interpolation="nearest")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v = values[i, j]
            ax.text(j, i, f"{v:,.0f}", ha="center", va="center",
                    fontsize=8, color="white" if v > values.max() * 0.6 else BRAND_NAVY)
    ax.set_xticks(range(len(MONTHS_FR)))
    ax.set_xticklabels(MONTHS_FR, fontsize=7)
    ax.set_yticks([])
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold")
    fig.tight_layout()
    return _to_img(fig)


def cost_trend_line(months: list[int], kwh_values: list[float],
                    cost_values: list[float],
                    title: str = "Évolution Coût et Consommation") -> str:
    """Dual-axis: kWh bars + cost line."""
    fig, ax1 = plt.subplots(figsize=(7, 3.5))
    ax2 = ax1.twinx()

    x = np.arange(len(months))
    bars = ax1.bar(x, kwh_values, color=BRAND_BLUE, alpha=0.25, width=0.6, label="kWh")
    ax1.set_ylabel("kWh", color=BRAND_BLUE)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax1.tick_params(axis="y", colors=BRAND_BLUE)

    line = ax2.plot(MONTHS_FR[:len(months)], cost_values, color=BRAND_ORANGE,
                    marker="o", linewidth=2, markersize=4, label="Coût (TND)")
    ax2.set_ylabel("Coût (TND)", color=BRAND_ORANGE)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.tick_params(axis="y", colors=BRAND_ORANGE)

    for i, (k, c) in enumerate(zip(kwh_values, cost_values)):
        ax1.text(i, k, f"{k:,.0f}", ha="center", va="bottom", fontsize=6.5, color=BRAND_NAVY)

    ax1.set_title(title, color=BRAND_NAVY, fontweight="bold")
    ax1.set_xticks(range(len(months)))
    ax1.set_xticklabels(MONTHS_FR[:len(months)], fontsize=7)
    _style_ax(ax1)
    ax2.spines["top"].set_visible(False)
    fig.tight_layout()
    return _to_img(fig)


def health_gauge(score: float, title: str = "Score de Santé Global") -> str:
    """Horizontal gauge bar showing health score."""
    fig, ax = plt.subplots(figsize=(5, 1.2))
    score_clamped = max(0, min(100, score))

    thresholds = [(0, 50, BRAND_RED), (50, 80, BRAND_AMBER), (80, 100, BRAND_GREEN)]
    for start, end, color in thresholds:
        ls = max(0, start)
        le = min(100, end)
        if le > ls:
            ax.barh(0, le - ls, left=ls, height=0.5, color=color, alpha=0.3, edgecolor="none")

    # marker
    x_pos = score_clamped / 100.0 * 100
    ax.plot(x_pos, 0, marker="D", color=BRAND_NAVY, markersize=10, zorder=5)

    ax.text(x_pos, -0.6, f"{score_clamped:.0f}/100", ha="center", va="top",
            fontsize=10, fontweight="bold", color=BRAND_NAVY)

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.8, 0.8)
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold", fontsize=9)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100"], fontsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#ddd")
    ax.tick_params(colors="#666")
    fig.tight_layout()
    return _to_img(fig)


def ranking_bars(sites: list[dict], title: str = "Sites les Plus Critiques",
                 max_rows: int = 10) -> str:
    """Horizontal bar chart for bottom N sites by health score."""
    if not sites:
        return ""
    sites_subset = sites[:max_rows]
    names = [s.get("site_code", "?") for s in reversed(sites_subset)]
    scores = [s.get("health_score", 0) for s in reversed(sites_subset)]
    colors = []
    for s in scores:
        if s >= 80:
            colors.append(BRAND_GREEN)
        elif s >= 50:
            colors.append(BRAND_AMBER)
        else:
            colors.append(BRAND_RED)

    fig, ax = plt.subplots(figsize=(6, max(2, len(names) * 0.35)))
    bars = ax.barh(names, scores, color=colors, edgecolor="white", height=0.6)
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{score:.0f}", va="center", fontsize=7.5, fontweight="bold", color=BRAND_NAVY)
    ax.set_xlim(0, 105)
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold")
    ax.set_xlabel("Score de Santé")
    ax.set_xticks([0, 25, 50, 75, 100])
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)


def estimated_vs_reel_bars(reel_kwh: float, estimated_kwh: float,
                           reel_cost: float, estimated_cost: float,
                           title: str = "Estimé vs Réel") -> str:
    """Grouped bars comparing estimated vs real for kWh and cost."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 3))

    # kWh
    categories = ["kWh"]
    x = np.arange(len(categories))
    w = 0.3
    ax1.bar(x - w / 2, [reel_kwh], w, label="Réel", color=BRAND_BLUE, edgecolor="white")
    ax1.bar(x + w / 2, [estimated_kwh], w, label="Estimé", color=BRAND_ORANGE, edgecolor="white")
    ax1.set_ylabel("kWh")
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax1.set_title("Consommation", color=BRAND_NAVY, fontweight="bold")
    ax1.legend(frameon=False, fontsize=7)
    _style_ax(ax1)

    # Cost
    ax2.bar(x - w / 2, [reel_cost], w, label="Réel", color=BRAND_BLUE, edgecolor="white")
    ax2.bar(x + w / 2, [estimated_cost], w, label="Estimé", color=BRAND_ORANGE, edgecolor="white")
    ax2.set_ylabel("TND")
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.set_title("Coût", color=BRAND_NAVY, fontweight="bold")
    ax2.legend(frameon=False, fontsize=7)
    _style_ax(ax2)

    for ax in [ax1, ax2]:
        ax.set_xticks([])

    fig.suptitle(title, color=BRAND_NAVY, fontweight="bold", fontsize=11, y=1.02)
    fig.tight_layout()
    return _to_img(fig)


def monthly_consumption_distribution(monthly_bt: list[float], monthly_mt: list[float],
                                      title: str = "Répartition Mensuelle BT / MT") -> str:
    """Stacked bar chart showing BT and MT split per month."""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    x = np.arange(12)
    w = 0.7
    ax.bar(x, monthly_bt, w, label="BT", color=BRAND_BLUE, edgecolor="white")
    ax.bar(x, monthly_mt, w, bottom=monthly_bt, label="MT", color=BRAND_BERRY, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(MONTHS_FR, fontsize=7)
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_title(title, color=BRAND_NAVY, fontweight="bold")
    ax.legend(frameon=False)
    _style_ax(ax)
    fig.tight_layout()
    return _to_img(fig)
