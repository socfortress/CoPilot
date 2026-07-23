"""Server-side chart rendering for the customer PDF report.

Charts are rendered with **matplotlib** (headless ``Agg`` backend) into PNG
bytes, returned as ``data:image/png;base64,...`` URIs. wkhtmltopdf embeds data
URIs directly (they are not "local file access", so this is compatible with the
``disable-local-file-access`` hardening on the renderer). Rendering server-side
— rather than relying on client ECharts — is what lets the PDF carry the same
donut / bar / evolution charts as the reference SOC reports.

All text drawn onto a chart becomes rasterised pixels, so values coming from the
database cannot inject markup into the surrounding HTML.
"""
import base64
import io
import math
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

import matplotlib

matplotlib.use("Agg")  # headless backend; must be set before pyplot import

import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# Brand-neutral categorical palette (distinct hues, echoes the reference reports:
# gold / red / blue / green / violet / black ...).
PALETTE = [
    "#f5c518",  # gold
    "#ee4b3b",  # red
    "#4fa8e0",  # blue
    "#2ecc71",  # green
    "#8c6fe0",  # violet
    "#1a1a1a",  # near-black
    "#f5842b",  # orange
    "#22c1dc",  # cyan
    "#ec4899",  # pink
    "#84cc16",  # lime
]
# Status-aware colours so the "by status" donut reads intuitively.
STATUS_COLORS = {
    "OPEN": "#f5c518",
    "IN_PROGRESS": "#4fa8e0",
    "IN PROGRESS": "#4fa8e0",
    "CLOSED": "#2ecc71",
    "RESOLVED": "#2ecc71",
    "ESCALATED": "#ee4b3b",
    "FALSE_POSITIVE": "#94a3b8",
}
_BAR_FILL = "#8c93e8"  # periwinkle, matches the reference bar charts
_EVO_FILL = "#7c6fd6"  # purple, matches the reference evolution charts
_TEXT = "#1e293b"
_MUTED = "#475569"
_PLOT_BG = "#eaeaf2"  # seaborn-style shaded plot area (evolution charts)

_FONT = fm.FontProperties(family=["DejaVu Sans", "Helvetica", "Arial", "sans-serif"])
_EMPTY_MSG = "No data for this period"


def _fig_to_data_uri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _empty(width_in: float = 5.0, height_in: float = 2.2) -> str:
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    ax.axis("off")
    ax.text(0.5, 0.5, _EMPTY_MSG, ha="center", va="center", color=_MUTED, fontproperties=_FONT, fontsize=12)
    return _fig_to_data_uri(fig)


def _colors_for(labels: Sequence[str], status_aware: bool) -> List[str]:
    if status_aware:
        return [STATUS_COLORS.get(str(label).upper(), PALETTE[i % len(PALETTE)]) for i, label in enumerate(labels)]
    return [PALETTE[i % len(PALETTE)] for i in range(len(labels))]


def donut_png(data: List[Tuple[str, int]], status_aware: bool = False, width_in: float = 5.2, height_in: float = 3.2) -> str:
    """Donut chart with external labels + leader lines: ``Label`` / ``count (pct%)``.

    Mirrors the reference "Distribución de alertas" donuts.
    """
    data = [(str(label), int(value)) for label, value in data if value and value > 0]
    if not data:
        return _empty(width_in, height_in)

    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    total = sum(values)
    colors = _colors_for(labels, status_aware)

    fig, ax = plt.subplots(figsize=(width_in, height_in))
    ax.set_aspect("equal")

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5),
    )

    # External labels with leader lines (matplotlib annotate), like the references.
    # Compute each label's anchor on the wedge and a target text position, then
    # spread same-side labels vertically so small adjacent slices don't collide.
    placements = []
    for wedge, label, value in zip(wedges, labels, values):
        ang = math.radians((wedge.theta2 + wedge.theta1) / 2.0)
        x = math.cos(ang)
        y = math.sin(ang)
        placements.append({"anchor": (x, y), "side": "left" if x >= 0 else "right", "ty": y * 1.32, "label": label, "value": value})

    min_gap = 0.42
    for side in ("left", "right"):
        group = sorted([p for p in placements if p["side"] == side], key=lambda p: p["ty"])
        for i in range(1, len(group)):
            if group[i]["ty"] - group[i - 1]["ty"] < min_gap:
                group[i]["ty"] = group[i - 1]["ty"] + min_gap

    for p in placements:
        x, y = p["anchor"]
        tx = 1.34 if p["side"] == "left" else -1.34
        pct_txt = f"{p['value'] / total * 100:.3g}%"
        ann_text = f"{p['label']}\n{p['value']} ({pct_txt})"
        ax.annotate(
            ann_text,
            xy=(x * 0.98, y * 0.98),
            xytext=(tx, p["ty"]),
            ha="left" if p["side"] == "left" else "right",
            va="center",
            fontproperties=_FONT,
            fontsize=8.5,
            color=_TEXT,
            fontweight="bold",
            arrowprops=dict(arrowstyle="-", color="#94a3b8", lw=0.8, connectionstyle="arc3"),
        )

    # Centre total
    ax.text(0, 0.06, f"{total}", ha="center", va="center", fontproperties=_FONT, fontsize=17, fontweight="bold", color=_TEXT)
    ax.text(0, -0.16, "total", ha="center", va="center", fontproperties=_FONT, fontsize=9, color=_MUTED)
    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.5, 1.5)
    return _fig_to_data_uri(fig)


def hbar_png(data: List[Tuple[str, int]], width_in: float = 8.4, max_label: int = 60, color: Optional[str] = None) -> str:
    """Horizontal bar chart with a top axis, gridlines and value labels.

    Mirrors the reference "Top títulos de alertas" / "Top taxonomías" charts.
    ``color`` overrides the bar fill (used to theme the report with a customer
    brand color); it defaults to the neutral periwinkle reference fill.
    """
    data = [(str(label), int(value)) for label, value in data if value is not None]
    if not data:
        return _empty(width_in, 1.6)

    # Highest value at the top (reverse for matplotlib's bottom-up y axis).
    data = list(data)[::-1]
    labels = [d[0] if len(d[0]) <= max_label else d[0][: max_label - 1] + "…" for d in data]
    values = [d[1] for d in data]

    height_in = max(1.4, 0.34 * len(data) + 0.6)
    fig, ax = plt.subplots(figsize=(width_in, height_in))

    fill = color or _BAR_FILL
    edge = color or "#6f77d6"
    y = range(len(values))
    ax.barh(list(y), values, color=fill, edgecolor=edge, linewidth=0.4, height=0.68)

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontproperties=_FONT, fontsize=8, color=_TEXT)
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.tick_params(axis="x", labelsize=8, colors=_MUTED, length=0)
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)

    max_v = max(values) if values else 1
    for yi, v in zip(y, values):
        ax.text(v + max_v * 0.01, yi, f"{v}", va="center", ha="left", fontproperties=_FONT, fontsize=8, fontweight="bold", color=_TEXT)
    ax.set_xlim(0, max_v * 1.12)
    return _fig_to_data_uri(fig)


def evolution_png(
    months: List[str],
    values: List[int],
    color: Optional[str] = None,
    width_in: float = 6.4,
    height_in: float = 3.0,
) -> str:
    """Monthly evolution bar chart with a shaded plot area and value labels.

    Mirrors the reference "Evolución de alertas / casos" charts.
    """
    if not months or not values:
        return _empty(width_in, height_in)

    color = color or _EVO_FILL
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    ax.set_facecolor(_PLOT_BG)

    x = range(len(values))
    bars = ax.bar(list(x), values, color=color, width=0.62, zorder=3)

    ax.set_xticks(list(x))
    ax.set_xticklabels(months, fontproperties=_FONT, fontsize=8, color=_MUTED)
    ax.tick_params(axis="y", labelsize=8, colors=_MUTED, length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color="white", linewidth=1.1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)

    max_v = max(values) if values else 1
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_v * 0.02,
            f"{v}",
            ha="center",
            va="bottom",
            fontproperties=_FONT,
            fontsize=8,
            fontweight="bold",
            color=_TEXT,
        )
    ax.set_ylim(0, max_v * 1.16 if max_v else 1)
    return _fig_to_data_uri(fig)


__all__ = ["donut_png", "hbar_png", "evolution_png", "PALETTE"]
