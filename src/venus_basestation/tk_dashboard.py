from __future__ import annotations

from dataclasses import dataclass

from .map_state import MapState


ROBOT_COLORS = ["#2563eb", "#0f766e", "#7c3aed", "#ea580c"]
OBJECT_STYLES = {
    "rock": ("#d1495b", "oval"),
    "cliff": ("#111827", "cross"),
    "boundary": ("#6b7280", "square"),
    "mountain": ("#8b5e34", "triangle"),
}


@dataclass
class Projection:
    width: int
    height: int
    margin: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def point(self, x: float, y: float) -> tuple[float, float]:
        usable_width = self.width - self.margin * 2
        usable_height = self.height - self.margin * 2
        px = self.margin + (x - self.min_x) / max(self.max_x - self.min_x, 1e-9) * usable_width
        py = self.height - self.margin - (y - self.min_y) / max(self.max_y - self.min_y, 1e-9) * usable_height
        return px, py


def projection_for_state(state: MapState, *, width: int, height: int, margin: int = 30) -> Projection:
    bounds = state.bounds()
    if bounds:
        min_x, max_x, min_y, max_y = bounds
    else:
        min_x = min_y = -1.0
        max_x = max_y = 1.0
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    pad_x = span_x * 0.2
    pad_y = span_y * 0.2
    return Projection(
        width=width,
        height=height,
        margin=margin,
        min_x=min_x - pad_x,
        max_x=max_x + pad_x,
        min_y=min_y - pad_y,
        max_y=max_y + pad_y,
    )


class TkDashboard:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Venus Basestation")
        self.root.geometry("1180x760")

        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 10))
        self.title_var = tk.StringVar(value="Venus Basestation")
        self.summary_var = tk.StringVar(value="Waiting for data")
        ttk.Label(header, textvariable=self.title_var, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(header, textvariable=self.summary_var, font=("Segoe UI", 10)).pack(anchor="w")

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, width=720, height=620, background="#f8fafc", highlightthickness=1, highlightbackground="#d9e2ec")
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        sidebar = ttk.Frame(body)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.rowconfigure(1, weight=1)
        sidebar.rowconfigure(3, weight=1)

        ttk.Label(sidebar, text="Robot Status", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.status_box = tk.Text(sidebar, height=10, width=42, wrap="word")
        self.status_box.grid(row=1, column=0, sticky="nsew", pady=(6, 12))

        ttk.Label(sidebar, text="Recent Events", font=("Segoe UI", 11, "bold")).grid(row=2, column=0, sticky="w")
        self.events_box = tk.Text(sidebar, height=16, width=42, wrap="word")
        self.events_box.grid(row=3, column=0, sticky="nsew", pady=(6, 12))

        self.legend_var = tk.StringVar(value="Legend: robot path / rocks / cliffs / boundaries / mountains")
        ttk.Label(sidebar, textvariable=self.legend_var, wraplength=320).grid(row=4, column=0, sticky="w")

    def draw(self, state: MapState) -> None:
        self.title_var.set(f"Venus Basestation - {state.messages_seen} messages")
        counts = state.object_counts()
        summary = ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "no static objects yet"
        self.summary_var.set(f"robots={len(state.robots)} | objects={len(state.objects)} | {summary}")

        self.canvas.delete("all")
        width = int(self.canvas["width"])
        height = int(self.canvas["height"])
        projection = projection_for_state(state, width=width, height=height)
        self._draw_grid(width, height, projection.margin)
        self._draw_tracks(state, projection)
        self._draw_objects(state, projection)
        self._update_status_box(state)
        self._update_events_box(state)
        self.root.update_idletasks()
        self.root.update()

    def show(self) -> None:
        self.root.mainloop()

    def _draw_grid(self, width: int, height: int, margin: int) -> None:
        for i in range(5):
            x = margin + (width - 2 * margin) * i / 4
            y = margin + (height - 2 * margin) * i / 4
            self.canvas.create_line(x, margin, x, height - margin, fill="#e5e7eb")
            self.canvas.create_line(margin, y, width - margin, y, fill="#e5e7eb")
        self.canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#cbd5e1")

    def _draw_tracks(self, state: MapState, projection: Projection) -> None:
        for index, (robot_id, track) in enumerate(sorted(state.robots.items())):
            if not track.positions:
                continue
            color = ROBOT_COLORS[index % len(ROBOT_COLORS)]
            points = [projection.point(x, y) for x, y in track.positions]
            flattened = [coord for point in points for coord in point]
            if len(flattened) >= 4:
                self.canvas.create_line(*flattened, fill=color, width=3, smooth=True)
            px, py = points[-1]
            self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill=color, outline=color)
            self.canvas.create_text(px + 32, py - 12, text=robot_id, fill=color, font=("Segoe UI", 10, "bold"))

    def _draw_objects(self, state: MapState, projection: Projection) -> None:
        for obj in state.objects:
            px, py = projection.point(obj.x, obj.y)
            color, shape = OBJECT_STYLES.get(obj.event_type, ("#334155", "oval"))
            if shape == "oval":
                self.canvas.create_oval(px - 7, py - 7, px + 7, py + 7, fill=color, outline=color)
            elif shape == "square":
                self.canvas.create_rectangle(px - 7, py - 7, px + 7, py + 7, fill=color, outline=color)
            elif shape == "triangle":
                self.canvas.create_polygon(px, py - 8, px - 8, py + 7, px + 8, py + 7, fill=color, outline=color)
            else:
                self.canvas.create_line(px - 7, py - 7, px + 7, py + 7, fill=color, width=2)
                self.canvas.create_line(px - 7, py + 7, px + 7, py - 7, fill=color, width=2)
            if obj.label:
                self.canvas.create_text(px + 44, py - 10, text=obj.label, fill="#0f172a", font=("Segoe UI", 9))

    def _update_status_box(self, state: MapState) -> None:
        self.status_box.delete("1.0", self.tk.END)
        if not state.statuses:
            self.status_box.insert(self.tk.END, "No status messages yet.")
            return
        for robot_id, payload in sorted(state.statuses.items()):
            mode = payload.get("mode", "status")
            battery = payload.get("battery", "n/a")
            lines = [
                f"{robot_id}",
                f"  mode: {mode}",
                f"  battery: {battery}",
            ]
            if payload.get("timestamp") is not None:
                lines.append(f"  timestamp: {payload['timestamp']}")
            self.status_box.insert(self.tk.END, "\n".join(lines) + "\n\n")

    def _update_events_box(self, state: MapState) -> None:
        self.events_box.delete("1.0", self.tk.END)
        lines = state.recent_event_lines(limit=12)
        if not lines:
            self.events_box.insert(self.tk.END, "No events yet.")
            return
        self.events_box.insert(self.tk.END, "\n".join(reversed(lines)))
