import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

MONTHS_FR = ["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"]

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


def yearly_consumption_bars(years: list[int], values: list[float], title: str = "Consommation Annuelle (kWh)") -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    colors = ["#2E86AB"] * len(years)
    bars = ax.bar(years, values, color=colors, width=0.6, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_title(title)
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _to_img(fig)


def monthly_trend_lines(months: list[int], values: list[float], title: str = "Tendance Mensuelle (kWh)") -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(MONTHS_FR[:len(months)], values, color="#2E86AB", marker="o", linewidth=2, markersize=4)
    ax.fill_between(range(len(months)), values, alpha=0.1, color="#2E86AB")
    ax.set_title(title)
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _to_img(fig)


def yoy_comparison_bars(years: list[str], bt_values: list[float], mt_values: list[float]) -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    x = np.arange(len(years))
    w = 0.35
    ax.bar(x - w / 2, bt_values, w, label="BT", color="#2E86AB", edgecolor="white")
    ax.bar(x + w / 2, mt_values, w, label="MT", color="#A23B72", edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_title("Comparaison BT/MT par Année (kWh)")
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _to_img(fig)


def forecast_overlay(months: list[int], historical: list[float], forecast: list[float],
                     ci_lower: list[float] | None = None, ci_upper: list[float] | None = None) -> str:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    labels = MONTHS_FR
    ax.plot(labels[:len(historical)], historical, color="#A23B72", marker="s", linewidth=2, label="Historique")
    ax.plot(labels[:len(forecast)], forecast, color="#2E86AB", marker="o", linewidth=2, label="Prévision")
    if ci_lower and ci_upper:
        ax.fill_between(range(len(forecast)), ci_lower, ci_upper, alpha=0.2, color="#2E86AB", label="IC 95%")
    ax.set_title("Prévision vs Historique (kWh)")
    ax.set_ylabel("kWh")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _to_img(fig)


def mom_change_bars(months: list[int], pct_changes: list[float]) -> str:
    fig, ax = plt.subplots(figsize=(7, 3))
    colors = ["#2E86AB" if v >= 0 else "#A23B72" for v in pct_changes]
    ax.bar(MONTHS_FR[:len(months)], pct_changes, color=colors, width=0.6, edgecolor="white")
    ax.axhline(y=0, color="gray", linewidth=0.8)
    ax.set_title("Variation Mensuelle (%)")
    ax.set_ylabel("%")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _to_img(fig)
