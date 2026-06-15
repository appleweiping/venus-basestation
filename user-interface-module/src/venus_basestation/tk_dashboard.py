"""Live mission-control desktop dashboard (Tkinter, stdlib only).

Layout:

    +----------------------------------------------------------------+
    | VENUS BASESTATION       conn pill | mission clock | msg rate   |
    +-----------------------------------------+----------------------+
    |                                         | ROBOTS (status cards)|
    |   terrain map: grid, trails, robots,    | DETECTIONS (chips)   |
    |   detected objects, zoom / pan / fit    | MISSION LOG (feed)   |
    |                                         |                      |
    +-----------------------------------------+----------------------+
    | pause | fit | export svg | legend                  status line |
    +----------------------------------------------------------------+

Threading contract: every Tk widget is touched only from the thread that
created the window. Background producers (the MQTT subscriber) must call
``submit()`` which enqueues events; ``start_pump()`` drains the queue from a
``root.after`` loop on the Tk thread.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from queue import Empty, SimpleQueue
import time

from .map_state import MapState
from .theme import DARK, Theme, get_theme


# Backwards-compatible module constants (kept for older imports/tests).
ROBOT_COLORS = list(DARK.robot_palette)
OBJECT_STYLES = dict(DARK.object_styles)

TRAIL_POINTS = 240
RENDER_INTERVAL = 0.033  # ~30 fps ceiling


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


class MessageRateTracker:
    """Sliding-window messages-per-second estimate."""

    def __init__(self, window: float = 5.0) -> None:
        self.window = window
        self._times: deque[float] = deque()

    def record(self, count: int = 1, now: float | None = None) -> None:
        stamp = time.monotonic() if now is None else now
        for _ in range(max(count, 0)):
            self._times.append(stamp)

    def rate(self, now: float | None = None) -> float:
        stamp = time.monotonic() if now is None else now
        cutoff = stamp - self.window
        while self._times and self._times[0] < cutoff:
            self._times.popleft()
        return len(self._times) / self.window


def battery_value(value: object) -> float | None:
    """Parse a battery payload value (``88``, ``"88"``, ``"88%"``) to 0..100."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(min(max(value, 0), 100))
    text = str(value).strip().rstrip("%").strip()
    if not text:
        return None
    try:
        return float(min(max(float(text), 0), 100))
    except ValueError:
        return None


@dataclass
class RobotCard:
    robot_id: str
    mode: str
    battery: float | None
    position: tuple[float, float] | None
    heading: float | None
    color_reading: str | None
    distance_reading: str | None


def robot_cards(state: MapState) -> list[RobotCard]:
    """Assemble per-robot summary data for the sidebar (pure logic, testable)."""
    plain_statuses = {key: value for key, value in state.statuses.items() if "__" not in key}
    robot_ids = sorted(set(state.robots) | set(plain_statuses))
    cards: list[RobotCard] = []
    for robot_id in robot_ids:
        status = plain_statuses.get(robot_id, {})
        track = state.robots.get(robot_id)
        color_status = state.statuses.get(f"{robot_id}__color_sensor", {})
        distance_status = state.statuses.get(f"{robot_id}__distance_sensor", {})
        distance = distance_status.get("distance_mm", distance_status.get("distance"))
        cards.append(
            RobotCard(
                robot_id=robot_id,
                mode=str(status.get("mode", "")) or "—",
                battery=battery_value(status.get("battery")),
                position=track.positions[-1] if track and track.positions else None,
                heading=track.heading if track else None,
                color_reading=str(color_status["color"]) if color_status.get("color") else None,
                distance_reading=f"{distance} mm" if distance is not None else None,
            )
        )
    return cards


def nice_grid_step(span: float, target_lines: int = 6) -> float:
    """Pick a 1/2/5 x 10^k grid step that yields roughly ``target_lines`` lines."""
    if span <= 0:
        return 1.0
    raw = span / max(target_lines, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiple in (1, 2, 5, 10):
        if raw <= multiple * magnitude:
            return multiple * magnitude
    return 10 * magnitude


def split_trail(points: list[tuple[float, float]], parts: int) -> list[list[tuple[float, float]]]:
    """Split a polyline into ``parts`` consecutive chunks that share joints."""
    if len(points) < 2 or parts <= 1:
        return [points] if len(points) >= 2 else []
    chunk = max(2, math.ceil(len(points) / parts))
    chunks: list[list[tuple[float, float]]] = []
    start = 0
    while start < len(points) - 1:
        end = min(start + chunk, len(points) - 1)
        chunks.append(points[start : end + 1])
        start = end
    return chunks


def _starfield(width: int, height: int, count: int = 110) -> list[tuple[float, float, float]]:
    """Deterministic pseudo-random star positions: (x, y, radius)."""
    stars = []
    seed = 0x2545F491
    for i in range(count):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        x = (seed % 10_000) / 10_000 * width
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        y = (seed % 10_000) / 10_000 * height
        radius = 0.6 + (i % 3) * 0.4
        stars.append((x, y, radius))
    return stars


class TkDashboard:
    def __init__(self, theme: str | Theme = "dark") -> None:
        import tkinter as tk
        from tkinter import font as tkfont

        self.tk = tk
        self.theme = theme if isinstance(theme, Theme) else get_theme(theme)
        t = self.theme

        self.root = tk.Tk()
        self.root.title("Venus Basestation — Mission Control")
        width = min(1280, self.root.winfo_screenwidth() - 40)
        height = min(800, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"{width}x{height}+10+10")
        self.root.minsize(900, 580)
        self.root.configure(bg=t.bg)

        self._state: MapState | None = None
        self._queue: SimpleQueue = SimpleQueue()
        self._pump_scheduled = False
        self._dirty = True
        self._paused = False
        self._last_render = 0.0
        self._messages_counted = 0
        self._rate = MessageRateTracker()
        self._started = time.monotonic()
        self._zoom = 1.0
        self._pan = [0.0, 0.0]
        self._view_locked = False
        self._drag_anchor: tuple[float, float] | None = None
        self._proj: Projection | None = None
        self._connected = False
        self._command_handler = None

        base_family = "Bahnschrift" if "Bahnschrift" in tkfont.families() else "Segoe UI"
        self._font_title = (base_family, 17, "bold")
        self._font_h2 = (base_family, 10, "bold")
        self._font_body = ("Segoe UI", 10)
        self._font_small = ("Segoe UI", 8)
        self._font_mono = ("Consolas", 9)

        self._build_header()
        self._build_body()
        self._build_footer()
        self._bind_events()
        self._tick_clock()

    # ------------------------------------------------------------------ UI build
    def _build_header(self) -> None:
        tk = self.tk
        t = self.theme
        header = tk.Frame(self.root, bg=t.bg)
        header.pack(fill="x", padx=14, pady=(12, 6))

        title_box = tk.Frame(header, bg=t.bg)
        title_box.pack(side="left")
        tk.Label(
            title_box, text="VENUS BASESTATION", font=self._font_title, bg=t.bg, fg=t.text
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="MISSION CONTROL · multi-robot telemetry",
            font=self._font_small,
            bg=t.bg,
            fg=t.text_muted,
        ).pack(anchor="w")

        metrics = tk.Frame(header, bg=t.bg)
        metrics.pack(side="right")

        self._rate_label = self._metric(metrics, "LINK RATE", "0.0 msg/s")
        self._count_label = self._metric(metrics, "MESSAGES", "0")
        self._clock_label = self._metric(metrics, "MISSION CLOCK", "00:00")

        pill = tk.Frame(metrics, bg=t.panel, highlightbackground=t.border, highlightthickness=1)
        pill.pack(side="right", padx=(0, 10), ipadx=10, ipady=5)
        self._conn_dot = tk.Canvas(pill, width=10, height=10, bg=t.panel, highlightthickness=0)
        self._conn_dot.pack(side="left", padx=(8, 6), pady=4)
        self._conn_dot.create_oval(1, 1, 9, 9, fill=t.text_faint, outline="", tags="dot")
        self._conn_label = tk.Label(pill, text="STANDBY", font=self._font_h2, bg=t.panel, fg=t.text_muted)
        self._conn_label.pack(side="left", padx=(0, 8))

    def _metric(self, parent, caption: str, value: str):
        tk = self.tk
        t = self.theme
        box = tk.Frame(parent, bg=t.bg)
        box.pack(side="right", padx=10)
        label = tk.Label(box, text=value, font=(self._font_mono[0], 13, "bold"), bg=t.bg, fg=t.text)
        label.pack(anchor="e")
        tk.Label(box, text=caption, font=self._font_small, bg=t.bg, fg=t.text_faint).pack(anchor="e")
        return label

    def _build_body(self) -> None:
        tk = self.tk
        t = self.theme
        body = tk.Frame(self.root, bg=t.bg)
        body.pack(fill="both", expand=True, padx=14)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg=t.canvas_bg, highlightthickness=1, highlightbackground=t.border)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        sidebar = tk.Frame(body, bg=t.bg, width=360)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(6, weight=1)

        tk.Label(sidebar, text="COMMAND UPLINK", font=self._font_h2, bg=t.bg, fg=t.text_faint).grid(
            row=0, column=0, sticky="w", pady=(2, 4)
        )
        self._build_command_panel(sidebar, row=1)

        tk.Label(sidebar, text="ROBOTS", font=self._font_h2, bg=t.bg, fg=t.text_faint).grid(
            row=2, column=0, sticky="w", pady=(10, 4)
        )
        self.cards_canvas = tk.Canvas(sidebar, bg=t.bg, highlightthickness=0, height=200)
        self.cards_canvas.grid(row=3, column=0, sticky="ew")

        tk.Label(sidebar, text="DETECTIONS", font=self._font_h2, bg=t.bg, fg=t.text_faint).grid(
            row=4, column=0, sticky="w", pady=(10, 4)
        )
        self.chips_canvas = tk.Canvas(sidebar, bg=t.bg, highlightthickness=0, height=60)
        self.chips_canvas.grid(row=5, column=0, sticky="ew")

        log_box = tk.Frame(sidebar, bg=t.bg)
        log_box.grid(row=6, column=0, sticky="nsew", pady=(10, 0))
        tk.Label(log_box, text="MISSION LOG", font=self._font_h2, bg=t.bg, fg=t.text_faint).pack(anchor="w", pady=(0, 4))
        self.feed = tk.Text(
            log_box,
            bg=t.panel,
            fg=t.text_muted,
            insertbackground=t.text,
            relief="flat",
            font=self._font_mono,
            wrap="word",
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=t.border,
            state="disabled",
            cursor="arrow",
        )
        self.feed.pack(fill="both", expand=True)
        for event_type in (
            "robot_position",
            "status",
            "rock",
            "cliff",
            "boundary",
            "mountain",
            "obstacle",
            "color_sensor",
            "distance_sensor",
        ):
            self.feed.tag_configure(event_type, foreground=t.event_color(event_type))
        self.feed.tag_configure("plain", foreground=t.text_muted)

    def _build_command_panel(self, sidebar, *, row: int) -> None:
        """Robot command uplink: start / idle / emergency stop.

        Buttons stay disabled until a command handler is attached (live MQTT
        mode); replay/simulated sources have no uplink. The robot applies
        commands at the end of its active iteration step, so feedback here
        only confirms the *send* — actual robot state arrives via telemetry.
        """
        tk = self.tk
        t = self.theme
        panel = tk.Frame(sidebar, bg=t.panel, highlightthickness=1, highlightbackground=t.border)
        panel.grid(row=row, column=0, sticky="ew")
        buttons = tk.Frame(panel, bg=t.panel)
        buttons.pack(fill="x", padx=8, pady=(8, 4))

        self._command_buttons: list = []

        def command_button(text: str, command_name: str, fg: str, bg: str) -> None:
            button = tk.Button(
                buttons,
                text=text,
                command=lambda: self._dispatch_command(command_name),
                font=self._font_h2,
                bg=bg,
                fg=fg,
                activebackground=t.border,
                activeforeground=fg,
                disabledforeground=t.text_faint,
                relief="flat",
                padx=10,
                pady=4,
                cursor="hand2",
                borderwidth=0,
                highlightthickness=1,
                highlightbackground=t.border,
                state="disabled",
            )
            button.pack(side="left", expand=True, fill="x", padx=(0, 6))
            self._command_buttons.append(button)

        command_button("▶ START", "start", t.ok, t.panel_alt)
        command_button("⏸ IDLE", "idle", t.warn, t.panel_alt)
        command_button("⛔ E-STOP", "stop", t.bg, t.danger)

        self._command_status = tk.Label(
            panel,
            text="uplink available in live MQTT mode only",
            font=self._font_small,
            bg=t.panel,
            fg=t.text_faint,
            anchor="w",
        )
        self._command_status.pack(fill="x", padx=10, pady=(0, 6))

    def set_command_handler(self, handler) -> None:
        """Attach the command uplink. ``handler(command)`` returns the topic
        the command was published to, or raises on failure.

        Buttons only become clickable once the broker link is up (see
        ``set_connection_status``); attaching the handler before the
        connection exists keeps them disabled until the conn event arrives.
        """
        self._command_handler = handler
        state = "normal" if self._connected else "disabled"
        for button in self._command_buttons:
            button.config(state=state)
        if self._connected:
            self._command_status.config(text="uplink ready — commands apply at the robot's next iteration step")
        else:
            self._command_status.config(text="uplink attached — waiting for broker link")

    def _dispatch_command(self, command: str) -> None:
        handler = getattr(self, "_command_handler", None)
        if handler is None:
            return
        t = self.theme
        try:
            topic = handler(command)
        except Exception as exc:
            self._command_status.config(text=f"'{command}' failed: {exc}", fg=t.danger)
            self._set_status(f"command '{command}' failed: {exc}")
            return
        # A QoS-1 PUBACK only proves the broker accepted the publish; MQTT
        # never reports whether any client is subscribed. Say "queued", not
        # "sent", so an operator never trusts an undelivered command (e.g. an
        # E-STOP to a topic no robot is listening on). Robot receipt is
        # confirmed only by returning telemetry.
        label = {"start": "START queued", "idle": "IDLE queued", "stop": "E-STOP QUEUED"}[command]
        color = t.danger if command == "stop" else t.ok
        self._command_status.config(text=f"{label} → {topic} · broker accepted, robot receipt unconfirmed", fg=color)
        self._set_status(f"command '{command}' queued at broker for {topic} (confirm via telemetry)")

    def _build_footer(self) -> None:
        tk = self.tk
        t = self.theme
        footer = tk.Frame(self.root, bg=t.bg)
        footer.pack(fill="x", padx=14, pady=(8, 12))

        self._pause_button = self._button(footer, "⏸  PAUSE", self.toggle_pause)
        self._button(footer, "⤢  FIT VIEW", self.fit_view)
        self._button(footer, "⬇  EXPORT SVG", self.export_svg)

        self.legend_canvas = tk.Canvas(footer, bg=t.bg, highlightthickness=0, height=22, width=470)
        self.legend_canvas.pack(side="left", padx=(14, 0))
        self._draw_legend()

        self._status_line = tk.Label(
            footer,
            text="space pause · F fit · S export · wheel zoom · drag pan",
            font=self._font_small,
            bg=t.bg,
            fg=t.text_faint,
            anchor="e",
        )
        self._status_line.pack(side="right", fill="x", expand=True)

    def _button(self, parent, text: str, command):
        tk = self.tk
        t = self.theme
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=self._font_h2,
            bg=t.panel_alt,
            fg=t.text,
            activebackground=t.border,
            activeforeground=t.text,
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=t.border,
        )
        button.pack(side="left", padx=(0, 8))
        return button

    def _draw_legend(self) -> None:
        t = self.theme
        canvas = self.legend_canvas
        canvas.delete("all")
        x = 4
        for event_type in ("rock", "cliff", "boundary", "mountain", "obstacle", "color_sensor", "distance_sensor"):
            color, shape = t.object_style(event_type)
            cy = 11
            self._draw_marker(canvas, x + 5, cy, color, shape, size=4)
            label = event_type.replace("_sensor", " sensor").replace("_", " ")
            text_id = canvas.create_text(x + 14, cy, text=label, anchor="w", fill=t.text_faint, font=self._font_small)
            bbox = canvas.bbox(text_id)
            x = (bbox[2] if bbox else x + 40) + 12

    def _bind_events(self) -> None:
        self.canvas.bind("<Configure>", lambda event: self._mark_dirty())
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda event: self._apply_zoom(1.1, event.x, event.y))
        self.canvas.bind("<Button-5>", lambda event: self._apply_zoom(1 / 1.1, event.x, event.y))
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", lambda event: setattr(self, "_drag_anchor", None))
        self.canvas.bind("<Double-Button-1>", lambda event: self.fit_view())
        self.root.bind("<space>", lambda event: self.toggle_pause())
        self.root.bind("<f>", lambda event: self.fit_view())
        self.root.bind("<F>", lambda event: self.fit_view())
        self.root.bind("<s>", lambda event: self.export_svg())
        self.root.bind("<S>", lambda event: self.export_svg())

    # --------------------------------------------------------------- public API
    def draw(self, state: MapState) -> None:
        """Synchronous update (simulated/JSONL replay paths, Tk thread only)."""
        self._state = state
        self._account_messages(state)
        self._mark_dirty()
        now = time.monotonic()
        if now - self._last_render >= RENDER_INTERVAL:
            self._render()
            self.root.update_idletasks()
            self.root.update()

    def show(self) -> None:
        self._render()
        self.root.mainloop()

    def submit(self, kind: str, payload: object = None) -> None:
        """Thread-safe event intake: ('obs', Observation) / ('conn', (ok, broker)) / ('log', str)."""
        self._queue.put((kind, payload))

    def start_pump(self, state: MapState, interval_ms: int = 33) -> None:
        """Drain submitted events from the Tk thread on a fixed cadence."""
        self._state = state
        if self._pump_scheduled:
            return
        self._pump_scheduled = True
        self._pump(interval_ms)

    def set_connection_status(self, connected: bool, broker: str = "") -> None:
        t = self.theme
        self._connected = connected
        if connected:
            self._conn_dot.itemconfig("dot", fill=t.ok)
            self._conn_label.config(text=f"LINK · {broker}" if broker else "LINK UP", fg=t.ok)
        else:
            self._conn_dot.itemconfig("dot", fill=t.text_faint)
            self._conn_label.config(text="STANDBY", fg=t.text_muted)
        # Commands are only meaningful on a live link: block clicks during
        # known outages instead of letting them fail (or queue) misleadingly.
        if self._command_handler is not None:
            state = "normal" if connected else "disabled"
            for button in self._command_buttons:
                button.config(state=state)
            if not connected:
                self._command_status.config(text="uplink down — commands blocked until reconnect", fg=t.warn)

    # ------------------------------------------------------------------ actions
    def toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_button.config(text="▶  RESUME" if self._paused else "⏸  PAUSE")
        self._set_status("display paused — data still recording" if self._paused else "display resumed")
        if not self._paused:
            self._mark_dirty()
            self._render()

    def fit_view(self) -> None:
        self._zoom = 1.0
        self._pan = [0.0, 0.0]
        self._view_locked = False
        self._mark_dirty()
        self._render()

    def export_svg(self) -> None:
        if not self._state:
            self._set_status("nothing to export yet")
            return
        from .svg_snapshot import write_svg_snapshot

        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = write_svg_snapshot(f"outputs/snapshot-{stamp}.svg", self._state, theme=self.theme)
        self._set_status(f"snapshot saved → {path}")

    # ----------------------------------------------------------------- internals
    def _set_status(self, text: str) -> None:
        # The footer shares space with the legend; keep the line short.
        self._status_line.config(text=text if len(text) <= 64 else text[:61] + "…")

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _account_messages(self, state: MapState) -> None:
        delta = state.messages_seen - self._messages_counted
        if delta > 0:
            self._rate.record(delta)
            self._messages_counted = state.messages_seen

    def _pump(self, interval_ms: int) -> None:
        # The whole live UI rides on this self-rescheduling after-chain. If any
        # apply()/render() ever raised, the reschedule would be skipped and the
        # dashboard would freeze permanently (only a stderr traceback). Isolate
        # per-event failures and guarantee the reschedule in finally.
        try:
            drained = 0
            while drained < 500:
                try:
                    kind, payload = self._queue.get_nowait()
                except Empty:
                    break
                drained += 1
                try:
                    if kind == "obs" and self._state is not None:
                        self._state.apply(payload)
                    elif kind == "conn":
                        ok, broker = payload
                        self.set_connection_status(ok, broker)
                    elif kind == "log":
                        self._set_status(str(payload))
                except Exception:  # one bad event must not stall the pump
                    pass
            if drained and self._state is not None:
                self._account_messages(self._state)
                self._mark_dirty()
            if self._dirty and not self._paused:
                self._render()
        except Exception:  # never let a render glitch kill the live loop
            pass
        finally:
            self.root.after(interval_ms, lambda: self._pump(interval_ms))

    def _tick_clock(self) -> None:
        elapsed = int(time.monotonic() - self._started)
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(minutes, 60)
        text = f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
        self._clock_label.config(text=text)
        self._rate_label.config(text=f"{self._rate.rate():.1f} msg/s")
        self.root.after(500, self._tick_clock)

    # ------------------------------------------------------------ view transform
    def _world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        assert self._proj is not None
        px, py = self._proj.point(x, y)
        cx = self._proj.width / 2
        cy = self._proj.height / 2
        return (px - cx) * self._zoom + cx + self._pan[0], (py - cy) * self._zoom + cy + self._pan[1]

    def _screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        assert self._proj is not None
        proj = self._proj
        cx = proj.width / 2
        cy = proj.height / 2
        px = (sx - cx - self._pan[0]) / self._zoom + cx
        py = (sy - cy - self._pan[1]) / self._zoom + cy
        usable_width = proj.width - proj.margin * 2
        usable_height = proj.height - proj.margin * 2
        x = proj.min_x + (px - proj.margin) / max(usable_width, 1e-9) * (proj.max_x - proj.min_x)
        y = proj.min_y + (proj.height - proj.margin - py) / max(usable_height, 1e-9) * (proj.max_y - proj.min_y)
        return x, y

    def _on_wheel(self, event) -> None:
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self._apply_zoom(factor, event.x, event.y)

    def _apply_zoom(self, factor: float, sx: float, sy: float) -> None:
        new_zoom = min(max(self._zoom * factor, 0.2), 40.0)
        if self._proj is None or new_zoom == self._zoom:
            return
        cx = self._proj.width / 2
        cy = self._proj.height / 2
        ratio = new_zoom / self._zoom
        self._pan[0] = sx - cx - (sx - cx - self._pan[0]) * ratio
        self._pan[1] = sy - cy - (sy - cy - self._pan[1]) * ratio
        self._zoom = new_zoom
        self._view_locked = True
        self._mark_dirty()
        self._render()

    def _on_drag_start(self, event) -> None:
        self._drag_anchor = (event.x, event.y)

    def _on_drag_move(self, event) -> None:
        if self._drag_anchor is None:
            return
        dx = event.x - self._drag_anchor[0]
        dy = event.y - self._drag_anchor[1]
        self._drag_anchor = (event.x, event.y)
        self._pan[0] += dx
        self._pan[1] += dy
        self._view_locked = True
        self._mark_dirty()
        self._render()

    # ----------------------------------------------------------------- rendering
    def _render(self) -> None:
        if self._state is None or self._paused:
            return
        self._last_render = time.monotonic()
        self._dirty = False
        state = self._state

        self._count_label.config(text=str(state.messages_seen))
        self._render_map(state)
        self._render_cards(state)
        self._render_chips(state)
        self._render_feed(state)

    def _canvas_size(self) -> tuple[int, int]:
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            width = int(self.canvas["width"] or 860)
            height = int(self.canvas["height"] or 640)
        return width, height

    def _render_map(self, state: MapState) -> None:
        t = self.theme
        canvas = self.canvas
        canvas.delete("all")
        width, height = self._canvas_size()
        self._proj = projection_for_state(state, width=width, height=height, margin=44)

        for x, y, radius in _starfield(width, height):
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=t.star, outline="")

        self._draw_grid(width, height)
        self._draw_tracks(state)
        self._draw_objects(state)

        if self._view_locked:
            canvas.create_text(
                width - 10,
                12,
                text=f"zoom ×{self._zoom:.1f} — double-click to fit",
                anchor="e",
                fill=t.text_faint,
                font=self._font_small,
            )
        if not state.robots and not state.objects:
            canvas.create_text(
                width / 2,
                height / 2,
                text="AWAITING TELEMETRY",
                fill=t.text_faint,
                font=(self._font_title[0], 14, "bold"),
            )

    def _draw_grid(self, width: int, height: int) -> None:
        t = self.theme
        canvas = self.canvas
        x0, y0 = self._screen_to_world(0, height)
        x1, y1 = self._screen_to_world(width, 0)
        step = nice_grid_step(max(x1 - x0, y1 - y0, 1e-9))

        gx = math.floor(x0 / step) * step
        while gx <= x1:
            sx, _ = self._world_to_screen(gx, 0)
            major = abs(gx % (step * 2)) < step / 2 or abs(gx) < step / 2
            canvas.create_line(sx, 0, sx, height, fill=t.grid_strong if abs(gx) < step / 2 else t.grid)
            if major:
                canvas.create_text(sx + 3, height - 8, text=f"{gx:g}", anchor="w", fill=t.text_faint, font=self._font_small)
            gx += step
        gy = math.floor(y0 / step) * step
        while gy <= y1:
            _, sy = self._world_to_screen(0, gy)
            major = abs(gy % (step * 2)) < step / 2 or abs(gy) < step / 2
            canvas.create_line(0, sy, width, sy, fill=t.grid_strong if abs(gy) < step / 2 else t.grid)
            if major:
                canvas.create_text(6, sy - 8, text=f"{gy:g}", anchor="w", fill=t.text_faint, font=self._font_small)
            gy += step

    def _draw_tracks(self, state: MapState) -> None:
        t = self.theme
        canvas = self.canvas
        for index, (robot_id, track) in enumerate(sorted(state.robots.items())):
            if not track.positions:
                continue
            color = t.robot_color(index)
            points = [self._world_to_screen(x, y) for x, y in track.positions[-TRAIL_POINTS:]]
            shades = t.trail_shades(color)
            for shade, chunk in zip(shades, split_trail(points, len(shades))):
                flattened = [coord for point in chunk for coord in point]
                if len(flattened) >= 4:
                    canvas.create_line(*flattened, fill=shade, width=2, smooth=True, capstyle="round")

            px, py = points[-1]
            for layer, glow in enumerate(t.glow_shades(color)):
                radius = 15 - layer * 4
                canvas.create_oval(px - radius, py - radius, px + radius, py + radius, fill=glow, outline="")
            canvas.create_oval(px - 5, py - 5, px + 5, py + 5, fill=color, outline=t.canvas_bg, width=1)

            if track.heading is not None:
                angle = math.radians(track.heading)
                hx = px + math.cos(angle) * 24
                hy = py - math.sin(angle) * 24
                canvas.create_line(px, py, hx, hy, fill=color, width=2, arrow=self.tk.LAST)

            label = robot_id if track.heading is None else f"{robot_id} · {track.heading:.0f}°"
            text_id = canvas.create_text(px + 12, py - 16, text=label, anchor="w", fill=t.text, font=self._font_h2)
            bbox = canvas.bbox(text_id)
            if bbox:
                pad = 3
                chip = canvas.create_rectangle(
                    bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad, fill=t.panel, outline=t.border
                )
                canvas.tag_lower(chip, text_id)

    def _draw_objects(self, state: MapState) -> None:
        t = self.theme
        canvas = self.canvas
        for obj in state.objects:
            px, py = self._world_to_screen(obj.x, obj.y)
            color, shape = t.object_style(obj.event_type)
            halo = t.glow_shades(color, layers=1)[0]
            canvas.create_oval(px - 11, py - 11, px + 11, py + 11, fill=halo, outline="")
            self._draw_marker(canvas, px, py, color, shape, size=7)
            # Only informative labels (e.g. rock details); bare type names are
            # already explained by the legend and would clutter dense maps.
            if obj.label and obj.label != obj.event_type:
                canvas.create_text(px + 13, py - 11, text=obj.label, anchor="w", fill=t.text_muted, font=self._font_small)

    @staticmethod
    def _draw_marker(canvas, px: float, py: float, color: str, shape: str, *, size: int) -> None:
        s = size
        if shape == "square":
            canvas.create_rectangle(px - s, py - s, px + s, py + s, fill=color, outline="")
        elif shape == "triangle":
            canvas.create_polygon(px, py - s - 1, px - s - 1, py + s, px + s + 1, py + s, fill=color, outline="")
        elif shape == "diamond":
            canvas.create_polygon(px, py - s - 1, px - s - 1, py, px, py + s + 1, px + s + 1, py, fill=color, outline="")
        elif shape == "cross":
            canvas.create_line(px - s, py - s, px + s, py + s, fill=color, width=2)
            canvas.create_line(px - s, py + s, px + s, py - s, fill=color, width=2)
        else:
            canvas.create_oval(px - s, py - s, px + s, py + s, fill=color, outline="")

    def _render_cards(self, state: MapState) -> None:
        t = self.theme
        canvas = self.cards_canvas
        canvas.delete("all")
        cards = robot_cards(state)
        card_height = 92
        spacing = 8
        width = max(canvas.winfo_width(), 200)
        canvas.config(height=max(len(cards) * (card_height + spacing), 40))
        if not cards:
            canvas.create_text(4, 18, text="no robots reporting yet", anchor="w", fill=t.text_faint, font=self._font_body)
            return

        for index, card in enumerate(cards):
            top = index * (card_height + spacing)
            color = t.robot_color(index)
            self._round_rect(canvas, 0, top, width - 2, top + card_height, radius=12, fill=t.panel, outline=t.border)
            canvas.create_oval(14, top + 14, 24, top + 24, fill=color, outline="")
            canvas.create_text(32, top + 19, text=card.robot_id, anchor="w", fill=t.text, font=(self._font_body[0], 11, "bold"))
            canvas.create_text(width - 14, top + 19, text=card.mode.upper(), anchor="e", fill=t.accent, font=self._font_small)

            bar_x, bar_y, bar_w = 14, top + 38, width - 96
            self._round_rect(canvas, bar_x, bar_y, bar_x + bar_w, bar_y + 8, radius=4, fill=t.panel_alt, outline=t.border)
            if card.battery is not None:
                fill_w = bar_w * card.battery / 100
                self._round_rect(
                    canvas, bar_x, bar_y, bar_x + max(fill_w, 6), bar_y + 8, radius=4, fill=t.battery_color(card.battery), outline=""
                )
                canvas.create_text(bar_x + bar_w + 10, bar_y + 4, text=f"{card.battery:.0f}%", anchor="w", fill=t.text_muted, font=self._font_small)
            else:
                canvas.create_text(bar_x + bar_w + 10, bar_y + 4, text="batt —", anchor="w", fill=t.text_faint, font=self._font_small)

            detail_parts = []
            if card.position:
                detail_parts.append(f"({card.position[0]:g}, {card.position[1]:g})")
            if card.heading is not None:
                detail_parts.append(f"{card.heading:g}°")
            canvas.create_text(14, top + 60, text="POS  " + (" · ".join(detail_parts) or "—"), anchor="w", fill=t.text_muted, font=self._font_mono)

            sensor_parts = []
            if card.color_reading:
                sensor_parts.append(f"color {card.color_reading}")
            if card.distance_reading:
                sensor_parts.append(f"dist {card.distance_reading}")
            canvas.create_text(14, top + 76, text="SNS  " + (" · ".join(sensor_parts) or "—"), anchor="w", fill=t.text_faint, font=self._font_mono)

    def _render_chips(self, state: MapState) -> None:
        t = self.theme
        canvas = self.chips_canvas
        canvas.delete("all")
        counts = state.object_counts()
        if not counts:
            canvas.create_text(4, 14, text="no detections yet", anchor="w", fill=t.text_faint, font=self._font_body)
            return
        x, y = 0, 4
        width = max(canvas.winfo_width(), 200)
        for event_type, count in sorted(counts.items()):
            color, _ = t.object_style(event_type)
            label = f"{event_type.replace('_', ' ')} × {count}"
            text_width = 8 * len(label) + 26
            if x + text_width > width and x > 0:
                x = 0
                y += 28
            self._round_rect(canvas, x, y, x + text_width, y + 22, radius=11, fill=t.panel, outline=t.border)
            canvas.create_oval(x + 8, y + 7, x + 16, y + 15, fill=color, outline="")
            canvas.create_text(x + 22, y + 11, text=label, anchor="w", fill=t.text_muted, font=self._font_small)
            x += text_width + 8
        canvas.config(height=y + 28)

    def _render_feed(self, state: MapState) -> None:
        feed = self.feed
        feed.config(state="normal")
        feed.delete("1.0", self.tk.END)
        entries = state.recent_event_entries(limit=14)
        if not entries:
            feed.insert(self.tk.END, "listening…", "plain")
        else:
            for event_type, line in reversed(entries):
                feed.insert(self.tk.END, "▌ ", event_type)
                feed.insert(self.tk.END, line + "\n", "plain")
        feed.config(state="disabled")

    def _round_rect(self, canvas, x0: float, y0: float, x1: float, y1: float, *, radius: float, fill: str, outline: str) -> int:
        radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
        points = [
            x0 + radius, y0, x1 - radius, y0, x1, y0, x1, y0 + radius,
            x1, y1 - radius, x1, y1, x1 - radius, y1, x0 + radius, y1,
            x0, y1, x0, y1 - radius, x0, y0 + radius, x0, y0,
        ]
        return canvas.create_polygon(points, smooth=True, fill=fill, outline=outline)
