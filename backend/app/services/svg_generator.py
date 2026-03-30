"""SVG chart generator — pure Python, no external dependencies.

Produces analytics SVG charts for the BridgeAI dashboard:
- pipeline_funnel: Lead pipeline funnel with stage counts
- revenue_bar: Monthly revenue bar chart
- lead_score_histogram: Lead score distribution
- agent_activity: Agent task completion timeline (sparkline)
"""
from __future__ import annotations

import html
from typing import Any


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0f172a",
    "surface": "#1e293b",
    "border": "#334155",
    "accent": "#3b82f6",
    "green": "#22c55e",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "text_primary": "#f1f5f9",
    "text_muted": "#64748b",
    "stage_colors": ["#3b82f6", "#8b5cf6", "#f59e0b", "#22c55e", "#10b981", "#ef4444"],
}

STAGE_LABELS = ["new", "qualified", "proposal", "negotiation", "won", "lost"]


def _esc(v: Any) -> str:
    return html.escape(str(v))


# ---------------------------------------------------------------------------
# Pipeline funnel
# ---------------------------------------------------------------------------

def pipeline_funnel(pipeline_data: dict[str, int], width: int = 480, height: int = 320) -> str:
    """Horizontal funnel chart showing lead counts per stage.

    Args:
        pipeline_data: dict mapping stage name → lead count.
        width/height: SVG viewport dimensions in pixels.
    """
    stages = STAGE_LABELS
    counts = [pipeline_data.get(s, 0) for s in stages]
    max_count = max(counts) if any(counts) else 1

    bar_area_w = width - 160
    bar_h = 36
    gap = 12
    total_h = len(stages) * (bar_h + gap) + gap
    chart_y_start = (height - total_h) // 2 + 24

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="font-family:Inter,system-ui,sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="{COLORS["bg"]}" rx="12"/>',
        f'<text x="20" y="22" fill="{COLORS["text_primary"]}" font-size="13" font-weight="600">Pipeline Funnel</text>',
    ]

    for i, (stage, count) in enumerate(zip(stages, counts)):
        y = chart_y_start + i * (bar_h + gap)
        bar_w = int((count / max_count) * bar_area_w) if max_count else 0
        color = COLORS["stage_colors"][i % len(COLORS["stage_colors"])]
        label_x = 20
        bar_x = 120

        # Stage label
        lines.append(
            f'<text x="{label_x}" y="{y + bar_h // 2 + 5}" fill="{COLORS["text_muted"]}" '
            f'font-size="11" text-anchor="start">{_esc(stage.title())}</text>'
        )
        # Background track
        lines.append(
            f'<rect x="{bar_x}" y="{y}" width="{bar_area_w}" height="{bar_h}" '
            f'fill="{COLORS["surface"]}" rx="4"/>'
        )
        # Value bar
        if bar_w > 0:
            lines.append(
                f'<rect x="{bar_x}" y="{y}" width="{bar_w}" height="{bar_h}" '
                f'fill="{color}" rx="4" opacity="0.85"/>'
            )
        # Count label
        label_val_x = bar_x + max(bar_w, 0) + 8
        lines.append(
            f'<text x="{label_val_x}" y="{y + bar_h // 2 + 5}" fill="{COLORS["text_primary"]}" '
            f'font-size="12" font-weight="600">{count}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Revenue bar chart
# ---------------------------------------------------------------------------

def revenue_bar(monthly_data: list[dict[str, Any]], width: int = 560, height: int = 280) -> str:
    """Monthly revenue bar chart.

    Args:
        monthly_data: list of {"month": "Jan", "revenue": 12500.0} dicts, up to 12 entries.
        width/height: SVG viewport dimensions.
    """
    if not monthly_data:
        monthly_data = []

    data = monthly_data[-12:]  # max 12 bars
    n = len(data)
    if n == 0:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" style="font-family:Inter,system-ui,sans-serif;">'
            f'<rect width="{width}" height="{height}" fill="{COLORS["bg"]}" rx="12"/>'
            f'<text x="{width//2}" y="{height//2}" fill="{COLORS["text_muted"]}" font-size="12" text-anchor="middle">No revenue data</text>'
            f'</svg>'
        )

    max_rev = max(float(d.get("revenue", 0)) for d in data) or 1
    pad_l, pad_r, pad_t, pad_b = 48, 20, 40, 36
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    bar_w = int(chart_w / n * 0.6)
    bar_gap = int(chart_w / n)

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="font-family:Inter,system-ui,sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="{COLORS["bg"]}" rx="12"/>',
        f'<text x="20" y="24" fill="{COLORS["text_primary"]}" font-size="13" font-weight="600">Monthly Revenue</text>',
    ]

    # Y gridlines (4 lines)
    for tick in range(1, 5):
        y = pad_t + chart_h - int(tick / 4 * chart_h)
        val = int(max_rev * tick / 4)
        lines.append(
            f'<line x1="{pad_l}" y1="{y}" x2="{width - pad_r}" y2="{y}" '
            f'stroke="{COLORS["border"]}" stroke-width="0.5" stroke-dasharray="3,3"/>'
        )
        lines.append(
            f'<text x="{pad_l - 6}" y="{y + 4}" fill="{COLORS["text_muted"]}" '
            f'font-size="9" text-anchor="end">R{val:,}</text>'
        )

    for i, d in enumerate(data):
        rev = float(d.get("revenue", 0))
        bh = int(rev / max_rev * chart_h) if max_rev else 0
        bx = pad_l + i * bar_gap + (bar_gap - bar_w) // 2
        by = pad_t + chart_h - bh

        # Bar
        lines.append(
            f'<rect x="{bx}" y="{by}" width="{bar_w}" height="{bh}" '
            f'fill="{COLORS["accent"]}" rx="3" opacity="0.85"/>'
        )
        # Month label
        month_label = _esc(str(d.get("month", "")))
        lines.append(
            f'<text x="{bx + bar_w // 2}" y="{height - 6}" fill="{COLORS["text_muted"]}" '
            f'font-size="9" text-anchor="middle">{month_label}</text>'
        )
        # Value label on bar top
        if bh > 16:
            lines.append(
                f'<text x="{bx + bar_w // 2}" y="{by - 4}" fill="{COLORS["text_primary"]}" '
                f'font-size="8" text-anchor="middle">R{int(rev):,}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lead score histogram
# ---------------------------------------------------------------------------

def lead_score_histogram(scores: list[float], width: int = 400, height: int = 220) -> str:
    """Lead score distribution histogram (10 buckets, 0–1 range).

    Args:
        scores: list of float scores between 0.0 and 1.0.
        width/height: SVG viewport dimensions.
    """
    buckets = [0] * 10
    for s in scores:
        idx = min(int(float(s) * 10), 9)
        buckets[idx] += 1

    max_count = max(buckets) or 1
    n = 10
    pad_l, pad_r, pad_t, pad_b = 36, 16, 36, 28
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    bar_w = int(chart_w / n * 0.75)
    bar_gap = int(chart_w / n)

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="font-family:Inter,system-ui,sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="{COLORS["bg"]}" rx="12"/>',
        f'<text x="16" y="24" fill="{COLORS["text_primary"]}" font-size="12" font-weight="600">Lead Score Distribution</text>',
    ]

    for i, count in enumerate(buckets):
        bh = int(count / max_count * chart_h) if max_count else 0
        bx = pad_l + i * bar_gap + (bar_gap - bar_w) // 2
        by = pad_t + chart_h - bh

        # Colour by score bucket: low=red, mid=amber, high=green
        if i < 4:
            color = COLORS["red"]
        elif i < 7:
            color = COLORS["amber"]
        else:
            color = COLORS["green"]

        lines.append(
            f'<rect x="{bx}" y="{by}" width="{bar_w}" height="{bh}" '
            f'fill="{color}" rx="2" opacity="0.8"/>'
        )
        label = f"{i * 10}–{(i + 1) * 10}"
        lines.append(
            f'<text x="{bx + bar_w // 2}" y="{height - 6}" fill="{COLORS["text_muted"]}" '
            f'font-size="7" text-anchor="middle">{label}</text>'
        )
        if count > 0:
            lines.append(
                f'<text x="{bx + bar_w // 2}" y="{by - 3}" fill="{COLORS["text_primary"]}" '
                f'font-size="8" text-anchor="middle">{count}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent activity sparkline
# ---------------------------------------------------------------------------

def agent_activity_sparkline(
    task_counts: list[int],
    labels: list[str] | None = None,
    width: int = 480,
    height: int = 120,
) -> str:
    """Sparkline of agent task completions over time.

    Args:
        task_counts: list of int counts per time bucket (e.g., hourly/daily).
        labels: optional x-axis labels. If omitted, indices are used.
        width/height: SVG viewport dimensions.
    """
    n = len(task_counts)
    if n < 2:
        task_counts = task_counts + [0] * (2 - n)
        n = 2

    labels = labels or [str(i) for i in range(n)]
    max_val = max(task_counts) or 1
    pad_l, pad_r, pad_t, pad_b = 36, 16, 30, 24
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    def px(i: int) -> int:
        return pad_l + int(i / (n - 1) * chart_w)

    def py(v: int) -> int:
        return pad_t + chart_h - int(v / max_val * chart_h)

    points = [(px(i), py(v)) for i, v in enumerate(task_counts)]
    polyline = " ".join(f"{x},{y}" for x, y in points)
    # Fill area below the line
    fill_pts = (
        f"{pad_l},{pad_t + chart_h} "
        + polyline
        + f" {pad_l + chart_w},{pad_t + chart_h}"
    )

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="font-family:Inter,system-ui,sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="{COLORS["bg"]}" rx="12"/>',
        f'<text x="16" y="20" fill="{COLORS["text_primary"]}" font-size="11" font-weight="600">Agent Activity</text>',
        # Fill
        f'<polygon points="{fill_pts}" fill="{COLORS["accent"]}" opacity="0.12"/>',
        # Line
        f'<polyline points="{polyline}" fill="none" stroke="{COLORS["accent"]}" '
        f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
    ]

    # Dots + labels
    step = max(1, n // 8)
    for i, (x, y) in enumerate(points):
        lines.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{COLORS["accent"]}"/>')
        if i % step == 0:
            label = _esc(labels[i]) if i < len(labels) else str(i)
            lines.append(
                f'<text x="{x}" y="{height - 4}" fill="{COLORS["text_muted"]}" '
                f'font-size="8" text-anchor="middle">{label}</text>'
            )

    lines.append("</svg>")
    return "\n".join(lines)
