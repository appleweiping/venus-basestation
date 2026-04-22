from __future__ import annotations

from .map_state import MapState


OBJECT_STYLES = {
    "rock": ("o", "tab:red"),
    "cliff": ("x", "black"),
    "boundary": ("s", "tab:gray"),
    "mountain": ("^", "sienna"),
}


class MatplotlibDashboard:
    def __init__(self) -> None:
        import matplotlib.pyplot as plt

        self.plt = plt
        self.figure, self.axis = plt.subplots(figsize=(8, 7))

    def draw(self, state: MapState) -> None:
        self.axis.clear()
        self.axis.set_title(f"Venus Basestation - {state.messages_seen} messages")
        self.axis.set_xlabel("x")
        self.axis.set_ylabel("y")
        self.axis.grid(True, alpha=0.25)
        self.axis.set_aspect("equal", adjustable="datalim")

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

        if state.robots:
            self.axis.legend(loc="upper left")
        self.plt.pause(0.01)

    def show(self) -> None:
        self.plt.show()

