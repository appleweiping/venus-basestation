"""Local smoke test for the Tk mission-control dashboard.

Feeds simulated telemetry through both update paths (synchronous ``draw`` and
the thread-safe ``submit``/``start_pump`` queue), optionally captures a PNG of
the live window (requires Pillow), then closes itself.

Usage:
    PYTHONPATH=src python tools/tk_smoke.py [--screenshot outputs/tk_smoke.png] [--theme dark]
"""

from __future__ import annotations

import argparse
import threading
import time

from venus_basestation.fake_messages import simulated_messages
from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation
from venus_basestation.tk_dashboard import TkDashboard


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", help="Save a PNG of the live window to this path.")
    parser.add_argument("--theme", default="dark", choices=["dark", "light"])
    parser.add_argument("--steps", type=int, default=46)
    parser.add_argument("--geometry", help="Override window geometry, e.g. 980x600+0+0.")
    parser.add_argument("--jsonl", help="Replay this JSONL file instead of the simulated stream.")
    args = parser.parse_args()

    state = MapState()
    dashboard = TkDashboard(theme=args.theme)
    if args.geometry:
        dashboard.root.geometry(args.geometry)
    dashboard.set_connection_status(True, "smoke-test")

    # Path 1: synchronous draw() calls, as used by simulated/JSONL replay.
    if args.jsonl:
        from venus_basestation.io_utils import iter_jsonl_messages

        for payload in iter_jsonl_messages(args.jsonl):
            state.apply(parse_observation(payload))
            dashboard.draw(state)
    else:
        for payload in simulated_messages(args.steps, delay=0.0):
            state.apply(parse_observation(payload))
            dashboard.draw(state)

    # Path 2: thread-safe queue intake, as used by live MQTT.
    def feed_from_thread() -> None:
        for payload in simulated_messages(8, delay=0.02):
            observation = parse_observation(payload)
            dashboard.submit("obs", observation)
        dashboard.submit("log", "smoke feed complete")

    threading.Thread(target=feed_from_thread, daemon=True).start()
    dashboard.start_pump(state)

    def capture_and_close() -> None:
        if args.screenshot:
            try:
                from PIL import ImageGrab

                dashboard.root.update_idletasks()
                # Window coordinates are logical pixels; the grab is physical.
                # Rescale the bbox by the actual DPI ratio before cropping.
                image = ImageGrab.grab()
                scale = image.width / max(dashboard.root.winfo_screenwidth(), 1)
                x = dashboard.root.winfo_rootx() * scale
                y = dashboard.root.winfo_rooty() * scale
                w = dashboard.root.winfo_width() * scale
                h = dashboard.root.winfo_height() * scale
                image.crop((int(x), int(y), int(min(x + w, image.width)), int(min(y + h, image.height)))).save(args.screenshot)
                print(f"screenshot saved to {args.screenshot}")
            except Exception as exc:  # pragma: no cover - best-effort capture
                print(f"screenshot failed: {exc}")
        dashboard.root.destroy()

    dashboard.root.after(2500, capture_and_close)
    started = time.monotonic()
    dashboard.show()
    print(f"smoke run OK: {state.messages_seen} messages, {time.monotonic() - started:.1f}s window time")


if __name__ == "__main__":
    main()
