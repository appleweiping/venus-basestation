from __future__ import annotations

from pathlib import Path

from .map_state import MapState


OBJECT_STYLES = {
    "rock": ("o", "tab:red"),
    "cliff": ("x", "black"),
    "boundary": ("s", "tab:gray"),
    "mountain": ("^", "sienna"),
    "obstacle": ("D", "tab:orange"),
    "color_sensor": ("p", "tab:purple"),
    "distance_sensor": ("h", "tab:cyan"),
}


class MatplotlibDashboard:
    """Matplotlib map view.

    With ``interactive=False`` (headless PNG export) no window is opened: the
    figure is drawn once, when it is saved, instead of after every message.
    """

    def __init__(self, *, interactive: bool = True) -> None:
        try:
            if interactive:
                import matplotlib.pyplot as plt
            else:
                from matplotlib.figure import Figure
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guidance
            raise SystemExit(
                "matplotlib is required for the dashboard. Run `pip install -r requirements-dashboard.txt` first."
            ) from exc

        self.interactive = interactive
        self._state: MapState | None = None
        if interactive:
            self.plt = plt
            self.figure, self.axis = plt.subplots(figsize=(8, 7))
        else:
            self.plt = None
            self.figure = Figure(figsize=(8, 7))
            self.axis = self.figure.subplots()

    def draw(self, state: MapState) -> None:
        self._state = state
        if self.interactive:
            self._paint(state)
            self.plt.pause(0.01)

    def _paint(self, state: MapState) -> None:
        self.axis.clear()
        self.axis.set_title(f"Venus Basestation - {state.messages_seen} messages")
        self.axis.set_xlabel("x")
        self.axis.set_ylabel("y")
        self.axis.grid(True, alpha=0.25)
        self.axis.set_aspect("equal", adjustable="box")
        bounds = state.bounds()
        if bounds:
            min_x, max_x, min_y, max_y = bounds
            pad_x = max((max_x - min_x) * 0.15, 0.4)
            pad_y = max((max_y - min_y) * 0.15, 0.4)
            self.axis.set_xlim(min_x - pad_x, max_x + pad_x)
            self.axis.set_ylim(min_y - pad_y, max_y + pad_y)

        for robot_id, track in state.robots.items():
            if not track.positions:
                continue
            xs, ys = zip(*track.positions)
            self.axis.plot(xs, ys, marker=".", label=robot_id)
            self.axis.scatter(xs[-1], ys[-1], s=80)

        for obj in state.objects:
            marker, color = OBJECT_STYLES.get(obj.event_type, ("*", "tab:blue"))
            self.axis.scatter(obj.x, obj.y, marker=marker, color=color, s=90)
            if obj.label:
                self.axis.annotate(obj.label, (obj.x, obj.y), textcoords="offset points", xytext=(5, 5))

        self.axis.text(
            0.99,
            0.01,
            f"robots={len(state.robots)} objects={len(state.objects)}",
            transform=self.axis.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
        )

        if state.robots:
            self.axis.legend(loc="upper left")

    def show(self) -> None:
        if self.plt is not None:
            self.plt.show()

    def save(self, path: str) -> None:
        if self._state is not None:
            self._paint(self._state)
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.figure.tight_layout()
        self.figure.savefig(output_path, dpi=160)
