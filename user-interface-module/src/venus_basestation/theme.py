"""Shared design tokens for the Tk dashboard and SVG snapshot renderers.

Tk canvases have no alpha channel, so "glow" and "trail fade" effects are
produced by blending marker colors toward the canvas background. Keeping the
palette and the blend math here lets both renderers (and the tests) agree on
the exact colors.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def blend(color_a: str, color_b: str, t: float) -> str:
    """Linear blend between two ``#rrggbb`` colors. ``t=0`` is A, ``t=1`` is B."""
    t = min(max(t, 0.0), 1.0)
    a = color_a.lstrip("#")
    b = color_b.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        va = int(a[i : i + 2], 16)
        vb = int(b[i : i + 2], 16)
        channels.append(round(va + (vb - va) * t))
    return "#" + "".join(f"{value:02x}" for value in channels)


@dataclass(frozen=True)
class Theme:
    name: str
    # Window chrome
    bg: str
    panel: str
    panel_alt: str
    border: str
    # Map canvas
    canvas_bg: str
    grid: str
    grid_strong: str
    star: str
    # Typography
    text: str
    text_muted: str
    text_faint: str
    # Semantic
    accent: str
    ok: str
    warn: str
    danger: str
    # Series
    robot_palette: tuple[str, ...] = (
        "#38bdf8",
        "#a78bfa",
        "#34d399",
        "#fb923c",
        "#f472b6",
        "#facc15",
    )
    object_styles: dict[str, tuple[str, str]] = field(
        default_factory=lambda: {
            "rock": ("#f87171", "oval"),
            "cliff": ("#e2e8f0", "cross"),
            "boundary": ("#94a3b8", "square"),
            "mountain": ("#d6a35c", "triangle"),
            "obstacle": ("#fb923c", "diamond"),
            "color_sensor": ("#c084fc", "oval"),
            "distance_sensor": ("#22d3ee", "square"),
        }
    )

    def robot_color(self, index: int) -> str:
        return self.robot_palette[index % len(self.robot_palette)]

    def trail_shades(self, color: str, steps: int = 3) -> list[str]:
        """Oldest-to-newest trail colors, fading the series color into the canvas."""
        if steps <= 1:
            return [color]
        shades = []
        for i in range(steps):
            # Oldest segment sits 75% of the way to the background; newest is pure.
            t = 0.75 * (1 - i / (steps - 1))
            shades.append(blend(color, self.canvas_bg, t))
        return shades

    def glow_shades(self, color: str, layers: int = 3) -> list[str]:
        """Outer-to-inner halo colors for a marker glow."""
        return [blend(color, self.canvas_bg, 0.55 + 0.15 * (layers - 1 - i)) for i in range(layers)]

    def object_style(self, event_type: str) -> tuple[str, str]:
        return self.object_styles.get(event_type, (self.text_muted, "oval"))

    def battery_color(self, level: float | None) -> str:
        if level is None:
            return self.text_faint
        if level >= 60:
            return self.ok
        if level >= 30:
            return self.warn
        return self.danger

    def event_color(self, event_type: str) -> str:
        if event_type == "robot_position":
            return self.accent
        if event_type == "status":
            return self.ok
        return self.object_styles.get(event_type, (self.text_muted, "oval"))[0]


DARK = Theme(
    name="dark",
    bg="#0b1020",
    panel="#10172e",
    panel_alt="#16203d",
    border="#1f2c4f",
    canvas_bg="#0a0e1c",
    grid="#152038",
    grid_strong="#1e2c4d",
    star="#243454",
    text="#e6edf7",
    text_muted="#8ea0c0",
    text_faint="#56678a",
    accent="#38bdf8",
    ok="#34d399",
    warn="#fbbf24",
    danger="#f87171",
)

LIGHT = Theme(
    name="light",
    bg="#eef2f7",
    panel="#ffffff",
    panel_alt="#f1f5fb",
    border="#d4deeb",
    canvas_bg="#fbfdff",
    grid="#e7edf5",
    grid_strong="#d8e1ee",
    star="#eef2f8",
    text="#16233c",
    text_muted="#5a6b88",
    text_faint="#94a3b8",
    accent="#0284c7",
    ok="#059669",
    warn="#d97706",
    danger="#dc2626",
    robot_palette=(
        "#2563eb",
        "#7c3aed",
        "#0f766e",
        "#ea580c",
        "#db2777",
        "#ca8a04",
    ),
    object_styles={
        "rock": ("#d1495b", "oval"),
        "cliff": ("#111827", "cross"),
        "boundary": ("#6b7280", "square"),
        "mountain": ("#8b5e34", "triangle"),
        "obstacle": ("#c2410c", "diamond"),
        "color_sensor": ("#7c3aed", "oval"),
        "distance_sensor": ("#0891b2", "square"),
    },
)

THEMES = {DARK.name: DARK, LIGHT.name: LIGHT}


def get_theme(name: str | None) -> Theme:
    return THEMES.get((name or "dark").lower(), DARK)
