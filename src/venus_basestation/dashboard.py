from __future__ import annotations

from pathlib import Path

from .map_state import MapState


OBJECT_STYLES = {
    "rock": ("o", "tab:red"),
    "cliff": ("x", "black"),
    "boundary": ("s", "tab:gray"),
    "mountain": ("^", "sienna"),
}


class MatplotlibDashboard:
    def __init__(self) -> None:
        try:
            import matplotlib.pyplot as plt
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guidance
            raise SystemExit(
                "matplotlib is required for the dashboard. Run `pip install -r requirements.txt` first."
            ) from exc

        self.plt = plt
        self.figure, self.axis = plt.subplots(figsize=(8, 7))

    def draw(self, state: MapState) -> None:
        self.axis.clear()
        self.axis.set_title(f"Venus Basestation - {state.messages_seen} messages")
        self.axis.set_xlabel("x")
        self.axis.set_ylabel("y")
        self.axis.grid(True, alpha=0.25)
        self.axis.set_aspect("equal", adjustable="datalim")
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
        self.plt.pause(0.01)

    def show(self) -> None:
        self.plt.show()

    def save(self, path: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.figure.tight_layout()
        self.figure.savefig(output_path, dpi=160)
