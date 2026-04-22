from __future__ import annotations

from html import escape
from pathlib import Path

from .map_state import MapState


OBJECT_STYLES = {
    "rock": ("#d1495b", "circle"),
    "cliff": ("#1f1f1f", "cross"),
    "boundary": ("#6c757d", "square"),
    "mountain": ("#8d5a2b", "triangle"),
}


def write_svg_snapshot(path: str | Path, state: MapState, *, width: int = 900, height: int = 720) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    margin = 60
    bounds = state.bounds()
    if bounds:
        min_x, max_x, min_y, max_y = bounds
    else:
        min_x = min_y = -1.0
        max_x = max_y = 1.0

    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    pad_x = span_x * 0.15
    pad_y = span_y * 0.15
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y

    inner_width = width - margin * 2
    inner_height = height - margin * 2

    def project(x: float, y: float) -> tuple[float, float]:
        px = margin + (x - min_x) / max(max_x - min_x, 1e-9) * inner_width
        py = height - margin - (y - min_y) / max(max_y - min_y, 1e-9) * inner_height
        return (round(px, 2), round(py, 2))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: 'Segoe UI', Arial, sans-serif; fill: #1f2933; }",
        ".title { font-size: 24px; font-weight: 700; }",
        ".subtitle { font-size: 13px; fill: #52606d; }",
        ".label { font-size: 12px; }",
        ".robot-label { font-size: 12px; font-weight: 600; }",
        "</style>",
        '<rect x="0" y="0" width="100%" height="100%" fill="#f8fafc" />',
        f'<rect x="{margin}" y="{margin}" width="{inner_width}" height="{inner_height}" rx="18" fill="#ffffff" stroke="#d9e2ec" />',
        f'<text class="title" x="{margin}" y="34">Venus Basestation Snapshot</text>',
        f'<text class="subtitle" x="{margin}" y="54">messages={state.messages_seen} robots={len(state.robots)} objects={len(state.objects)}</text>',
    ]

    for i in range(5):
        x = margin + inner_width * i / 4
        y = margin + inner_height * i / 4
        parts.append(f'<line x1="{x:.2f}" y1="{margin}" x2="{x:.2f}" y2="{height - margin}" stroke="#eef2f6" />')
        parts.append(f'<line x1="{margin}" y1="{y:.2f}" x2="{width - margin}" y2="{y:.2f}" stroke="#eef2f6" />')

    robot_palette = ["#2563eb", "#0f766e", "#7c3aed", "#ea580c"]
    for index, (robot_id, track) in enumerate(sorted(state.robots.items())):
        if not track.positions:
            continue
        color = robot_palette[index % len(robot_palette)]
        points = [project(x, y) for x, y in track.positions]
        polyline = " ".join(f"{x},{y}" for x, y in points)
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline}" />')
        last_x, last_y = points[-1]
        parts.append(f'<circle cx="{last_x}" cy="{last_y}" r="7" fill="{color}" />')
        parts.append(f'<text class="robot-label" x="{last_x + 10}" y="{last_y - 10}">{escape(robot_id)}</text>')

    for obj in state.objects:
        x, y = project(obj.x, obj.y)
        color, shape = OBJECT_STYLES.get(obj.event_type, ("#334e68", "circle"))
        if shape == "circle":
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" />')
        elif shape == "square":
            parts.append(f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" fill="{color}" rx="2" />')
        elif shape == "triangle":
            parts.append(f'<polygon points="{x},{y - 8} {x - 7},{y + 6} {x + 7},{y + 6}" fill="{color}" />')
        else:
            parts.append(f'<line x1="{x - 6}" y1="{y - 6}" x2="{x + 6}" y2="{y + 6}" stroke="{color}" stroke-width="2" />')
            parts.append(f'<line x1="{x - 6}" y1="{y + 6}" x2="{x + 6}" y2="{y - 6}" stroke="{color}" stroke-width="2" />')
        if obj.label:
            parts.append(f'<text class="label" x="{x + 8}" y="{y - 8}">{escape(obj.label)}</text>')

    status_y = height - margin + 22
    if state.statuses:
        latest_status = ", ".join(
            f"{robot_id}: {escape(str(payload.get('mode', 'status')))}"
            for robot_id, payload in sorted(state.statuses.items())
        )
        parts.append(f'<text class="subtitle" x="{margin}" y="{status_y}">latest status: {latest_status}</text>')

    parts.append("</svg>")
    output_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return output_path
