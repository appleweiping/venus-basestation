"""Mission-style SVG snapshot export (stdlib only, deterministic output).

The snapshot mirrors the Tk dashboard's theme: dark terrain panel, fading
robot trails with glow, object markers with halos, a legend with detection
counts, and a status footer. No wall-clock data is embedded, so re-exporting
the same state produces byte-identical files.
"""

from __future__ import annotations

from html import escape
import math
from pathlib import Path

from .map_state import MapState
from .theme import DARK, Theme, get_theme
from .tk_dashboard import nice_grid_step, split_trail


# Backwards-compatible constant (older imports/tests).
OBJECT_STYLES = dict(DARK.object_styles)

HEADER_HEIGHT = 86
FOOTER_HEIGHT = 46
PANEL_MARGIN = 24
PLOT_MARGIN = 52


def write_svg_snapshot(
    path: str | Path,
    state: MapState,
    *,
    width: int = 960,
    height: int = 760,
    theme: str | Theme = "dark",
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    t = theme if isinstance(theme, Theme) else get_theme(theme)

    panel_x = PANEL_MARGIN
    panel_y = HEADER_HEIGHT
    panel_w = width - PANEL_MARGIN * 2
    panel_h = height - HEADER_HEIGHT - FOOTER_HEIGHT

    bounds = state.bounds()
    if bounds:
        min_x, max_x, min_y, max_y = bounds
    else:
        min_x = min_y = -1.0
        max_x = max_y = 1.0
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    min_x -= span_x * 0.15
    max_x += span_x * 0.15
    min_y -= span_y * 0.15
    max_y += span_y * 0.15

    inner_x = panel_x + PLOT_MARGIN
    inner_y = panel_y + PLOT_MARGIN
    inner_w = panel_w - PLOT_MARGIN * 2
    inner_h = panel_h - PLOT_MARGIN * 2

    def project(x: float, y: float) -> tuple[float, float]:
        px = inner_x + (x - min_x) / max(max_x - min_x, 1e-9) * inner_w
        py = inner_y + inner_h - (y - min_y) / max(max_y - min_y, 1e-9) * inner_h
        return (round(px, 2), round(py, 2))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        f"text {{ font-family: 'Segoe UI', Arial, sans-serif; fill: {t.text}; }}",
        ".title { font-size: 22px; font-weight: 700; letter-spacing: 1px; }",
        f".subtitle {{ font-size: 12px; fill: {t.text_muted}; }}",
        f".label {{ font-size: 11px; fill: {t.text_muted}; }}",
        f".axis {{ font-size: 10px; fill: {t.text_faint}; }}",
        ".robot-label { font-size: 12px; font-weight: 600; }",
        f".legend {{ font-size: 11px; fill: {t.text_muted}; }}",
        "</style>",
        f'<rect x="0" y="0" width="100%" height="100%" fill="{t.bg}" />',
        # Header
        f'<rect x="{panel_x}" y="26" width="4" height="36" rx="2" fill="{t.accent}" />',
        f'<text class="title" x="{panel_x + 14}" y="44">Venus Basestation Snapshot</text>',
        f'<text class="subtitle" x="{panel_x + 14}" y="64">MISSION CONTROL · '
        f"messages={state.messages_seen} · robots={len(state.robots)} · objects={len(state.objects)}</text>",
        # Terrain panel
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="16" '
        f'fill="{t.canvas_bg}" stroke="{t.border}" />',
    ]

    parts.extend(_grid(t, project, min_x, max_x, min_y, max_y, inner_x, inner_y, inner_w, inner_h))
    parts.extend(_trails(t, state, project))
    parts.extend(_objects(t, state, project))
    parts.extend(_legend(t, state, panel_x + panel_w, panel_y))

    # Footer
    status_y = height - FOOTER_HEIGHT + 24
    if state.statuses:
        latest_status = ", ".join(
            f"{escape(robot_id)}: {escape(str(payload.get('mode', 'status')))}"
            for robot_id, payload in sorted(state.statuses.items())
            if "__" not in robot_id
        )
        parts.append(f'<text class="subtitle" x="{panel_x}" y="{status_y}">latest status — {latest_status}</text>')
    else:
        parts.append(f'<text class="subtitle" x="{panel_x}" y="{status_y}">latest status — none received</text>')

    parts.append("</svg>")
    output_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return output_path


def _grid(t: Theme, project, min_x, max_x, min_y, max_y, inner_x, inner_y, inner_w, inner_h) -> list[str]:
    parts: list[str] = []
    step = nice_grid_step(max(max_x - min_x, max_y - min_y))
    bottom = inner_y + inner_h

    gx = math.floor(min_x / step) * step
    while gx <= max_x:
        sx, _ = project(gx, min_y)
        stroke = t.grid_strong if abs(gx) < step / 2 else t.grid
        parts.append(f'<line x1="{sx}" y1="{inner_y}" x2="{sx}" y2="{bottom}" stroke="{stroke}" />')
        parts.append(f'<text class="axis" x="{sx + 3}" y="{bottom + 16}">{gx:g}</text>')
        gx += step
    gy = math.floor(min_y / step) * step
    while gy <= max_y:
        _, sy = project(min_x, gy)
        stroke = t.grid_strong if abs(gy) < step / 2 else t.grid
        parts.append(f'<line x1="{inner_x}" y1="{sy}" x2="{inner_x + inner_w}" y2="{sy}" stroke="{stroke}" />')
        parts.append(f'<text class="axis" x="{inner_x - 34}" y="{sy + 3}">{gy:g}</text>')
        gy += step
    return parts


def _trails(t: Theme, state: MapState, project) -> list[str]:
    parts: list[str] = []
    for index, (robot_id, track) in enumerate(sorted(state.robots.items())):
        if not track.positions:
            continue
        color = t.robot_color(index)
        points = [project(x, y) for x, y in track.positions]
        polyline_all = " ".join(f"{x},{y}" for x, y in points)
        if len(points) >= 2:
            parts.append(
                f'<polyline fill="none" stroke="{color}" stroke-opacity="0.22" stroke-width="7" '
                f'stroke-linecap="round" stroke-linejoin="round" points="{polyline_all}" />'
            )
            shades = t.trail_shades(color)
            for shade, chunk in zip(shades, split_trail(points, len(shades))):
                polyline = " ".join(f"{x},{y}" for x, y in chunk)
                parts.append(
                    f'<polyline fill="none" stroke="{shade}" stroke-width="2.5" '
                    f'stroke-linecap="round" stroke-linejoin="round" points="{polyline}" />'
                )

        last_x, last_y = points[-1]
        parts.append(f'<circle cx="{last_x}" cy="{last_y}" r="12" fill="{color}" fill-opacity="0.25" />')
        parts.append(f'<circle cx="{last_x}" cy="{last_y}" r="5.5" fill="{color}" stroke="{t.canvas_bg}" stroke-width="1" />')
        if track.heading is not None:
            angle = math.radians(track.heading)
            hx = round(last_x + math.cos(angle) * 22, 2)
            hy = round(last_y - math.sin(angle) * 22, 2)
            parts.append(f'<line x1="{last_x}" y1="{last_y}" x2="{hx}" y2="{hy}" stroke="{color}" stroke-width="2" />')

        robot_label = robot_id if track.heading is None else f"{robot_id} · {track.heading:.0f}°"
        label_x = last_x + 14
        label_y = last_y - 12
        label_w = 7.2 * len(robot_label) + 12
        parts.append(
            f'<rect x="{label_x - 6}" y="{label_y - 13}" width="{label_w:.0f}" height="19" rx="5" '
            f'fill="{t.panel}" stroke="{t.border}" />'
        )
        parts.append(f'<text class="robot-label" x="{label_x}" y="{label_y + 1}" fill="{color}">{escape(robot_label)}</text>')
    return parts


def _objects(t: Theme, state: MapState, project) -> list[str]:
    parts: list[str] = []
    for obj in state.objects:
        x, y = project(obj.x, obj.y)
        color, shape = t.object_style(obj.event_type)
        parts.append(f'<circle cx="{x}" cy="{y}" r="10" fill="{color}" fill-opacity="0.16" />')
        parts.append(_marker(x, y, color, shape))
        # Bare type names are covered by the legend; only annotate rich labels.
        if obj.label and obj.label != obj.event_type:
            parts.append(f'<text class="label" x="{x + 12}" y="{y - 9}">{escape(obj.label)}</text>')
    return parts


def _marker(x: float, y: float, color: str, shape: str, size: float = 6.5) -> str:
    s = size
    if shape == "square":
        return f'<rect x="{x - s}" y="{y - s}" width="{2 * s}" height="{2 * s}" rx="2" fill="{color}" />'
    if shape == "triangle":
        return f'<polygon points="{x},{y - s - 1} {x - s},{y + s - 1} {x + s},{y + s - 1}" fill="{color}" />'
    if shape == "diamond":
        return f'<polygon points="{x},{y - s - 1} {x - s - 1},{y} {x},{y + s + 1} {x + s + 1},{y}" fill="{color}" />'
    if shape == "cross":
        return (
            f'<g stroke="{color}" stroke-width="2.4" stroke-linecap="round">'
            f'<line x1="{x - s}" y1="{y - s}" x2="{x + s}" y2="{y + s}" />'
            f'<line x1="{x - s}" y1="{y + s}" x2="{x + s}" y2="{y - s}" /></g>'
        )
    return f'<circle cx="{x}" cy="{y}" r="{s}" fill="{color}" />'


def _legend(t: Theme, state: MapState, panel_right: int, panel_top: int) -> list[str]:
    counts = state.object_counts()
    if not counts:
        return []
    entries = sorted(counts.items())
    row_height = 20
    box_w = 190
    box_h = 16 + row_height * len(entries)
    box_x = panel_right - box_w - 16
    box_y = panel_top + 16
    parts = [
        f'<rect x="{box_x}" y="{box_y}" width="{box_w}" height="{box_h}" rx="10" '
        f'fill="{t.panel}" fill-opacity="0.92" stroke="{t.border}" />'
    ]
    for row, (event_type, count) in enumerate(entries):
        color, shape = t.object_style(event_type)
        cy = box_y + 18 + row * row_height
        parts.append(_marker(box_x + 18, cy, color, shape, size=5))
        label = event_type.replace("_", " ")
        parts.append(f'<text class="legend" x="{box_x + 34}" y="{cy + 4}">{escape(label)} × {count}</text>')
    return parts
