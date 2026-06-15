"""Live-broker Tk dashboard check: the teammate's exact scenario.

Wires a real MqttSubscriber into the mission-control dashboard (the same way
`python -m venus_basestation --source mqtt --ui tk` does), publishes Team 28's
exact telemetry format to the live topic from a background client, captures a
screenshot of the rendered map, then closes. Proves the full live path:
real broker -> derived topic -> parse -> queue -> dashboard render.

Run on a Python with tkinter + Pillow (system Python), reading VENUS_MQTT_*
from the environment:

    . .\\config.local.robot43.ps1
    PYTHONPATH=src <python-with-tk-and-pillow> tools/tk_live_check.py --screenshot outputs/tk_live.png
"""

from __future__ import annotations

import argparse
import json
import threading
import time

from venus_basestation.map_state import MapState
from venus_basestation.mqtt_client import MqttSubscriber, mqtt_config_from_env
from venus_basestation.tk_dashboard import TkDashboard


TEAM_MESSAGES = [
    {"robot_id": "A", "type": "position_update", "x": 0, "y": 0, "heading": 90},
    {"robot_id": "A", "type": "position_update", "x": 4, "y": 2, "heading": 80},
    {"robot_id": "A", "type": "rock_detected", "x": 5, "y": 3, "distance_mm": 120, "color": "red", "size": "small", "temperature": 28.5},
    {"robot_id": "A", "type": "position_update", "x": 9, "y": 5, "heading": 70},
    {"robot_id": "A", "type": "position_update", "x": 14, "y": 6, "heading": 60},
    {"robot_id": "A", "type": "rock_detected", "x": 15, "y": 7, "distance_mm": 210, "color": "green", "size": "large", "temperature": 31.0},
    {"robot_id": "A", "type": "position_update", "x": 20, "y": 6, "heading": 45},
]


def _run_inject(args) -> None:
    """Render Team 28's exact wire format through the dashboard queue, no broker."""
    from venus_basestation.message_schema import parse_observation

    state = MapState()
    dashboard = TkDashboard(theme="dark")
    dashboard.root.geometry(args.geometry)
    dashboard.set_connection_status(True, "inject-loopback")
    dashboard.start_pump(state)

    def feed() -> None:
        time.sleep(0.4)
        for message in TEAM_MESSAGES:
            dashboard.submit("obs", parse_observation(json.dumps(message)))
            time.sleep(0.2)
        dashboard.submit("log", "team-format telemetry rendered")

    threading.Thread(target=feed, name="inject-feed", daemon=True).start()

    def capture_and_close() -> None:
        _capture(dashboard, args.screenshot)
        print(f"messages_seen={state.messages_seen} robots={list(state.robots)} objects={state.object_counts()}")
        dashboard.root.destroy()

    dashboard.root.after(int(args.seconds * 1000), capture_and_close)
    dashboard.show()


def _capture(dashboard, path: str | None) -> None:
    if not path:
        return
    try:
        from PIL import ImageGrab

        dashboard.root.attributes("-topmost", True)
        dashboard.root.lift()
        dashboard.root.update_idletasks()
        dashboard.root.update()
        image = ImageGrab.grab()
        scale = image.width / max(dashboard.root.winfo_screenwidth(), 1)
        x = dashboard.root.winfo_rootx() * scale
        y = dashboard.root.winfo_rooty() * scale
        w = dashboard.root.winfo_width() * scale
        h = dashboard.root.winfo_height() * scale
        image.crop((int(x), int(y), int(min(x + w, image.width)), int(min(y + h, image.height)))).save(path)
        print(f"screenshot saved to {path}")
    except Exception as exc:  # pragma: no cover
        print(f"screenshot failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot")
    parser.add_argument("--geometry", default="1000x640+2+2")
    parser.add_argument("--seconds", type=float, default=4.0)
    parser.add_argument(
        "--inject",
        action="store_true",
        help="Feed Team 28's exact message format straight into the dashboard "
        "queue (no broker) — deterministic render proof.",
    )
    args = parser.parse_args()

    if args.inject:
        _run_inject(args)
        return

    config = mqtt_config_from_env()
    host, port = str(config["host"]), int(config["port"])
    topic = list(config["topics"])[0]
    username, password = str(config["username"]), str(config["password"])
    print(f"live check: host={host} topic={topic} username={username or '<none>'}")

    state = MapState()
    dashboard = TkDashboard(theme="dark")
    dashboard.root.geometry(args.geometry)

    subscriber = MqttSubscriber(
        host=host,
        port=port,
        topics=[topic],
        username=username,
        password=password,
        on_observation=lambda obs: dashboard.submit("obs", obs),
        on_log=lambda message: print(f"  [sub] {message}"),
        on_connect_change=lambda ok, broker: dashboard.submit("conn", (ok, broker)),
    )
    threading.Thread(target=subscriber.run_forever, name="live-sub", daemon=True).start()
    dashboard.start_pump(state)

    def publish_team_messages() -> None:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if username:
            client.username_pw_set(username, password)
        client.connect(host, port)
        client.loop_start()
        time.sleep(1.0)  # let our subscriber's SUBACK land first
        x = 0
        for _ in range(8):
            client.publish(topic, json.dumps({"robot_id": "A", "type": "position_update", "x": x, "y": x // 2, "heading": 90}), qos=1)
            if x % 3 == 0:
                client.publish(topic, json.dumps({
                    "robot_id": "A", "type": "rock_detected", "x": x, "y": x // 2,
                    "distance_mm": 120 + x * 10, "color": "red", "size": "small", "temperature": 28.5,
                }), qos=1)
            x += 2
            time.sleep(0.25)
        client.loop_stop()
        client.disconnect()

    threading.Thread(target=publish_team_messages, name="live-pub", daemon=True).start()

    def capture_and_close() -> None:
        if args.screenshot:
            try:
                from PIL import ImageGrab

                dashboard.root.attributes("-topmost", True)
                dashboard.root.lift()
                dashboard.root.update_idletasks()
                dashboard.root.update()
                image = ImageGrab.grab()
                scale = image.width / max(dashboard.root.winfo_screenwidth(), 1)
                x = dashboard.root.winfo_rootx() * scale
                y = dashboard.root.winfo_rooty() * scale
                w = dashboard.root.winfo_width() * scale
                h = dashboard.root.winfo_height() * scale
                image.crop((int(x), int(y), int(min(x + w, image.width)), int(min(y + h, image.height)))).save(args.screenshot)
                print(f"screenshot saved to {args.screenshot}")
            except Exception as exc:  # pragma: no cover
                print(f"screenshot failed: {exc}")
        print(f"messages_seen={state.messages_seen} robots={list(state.robots)} objects={state.object_counts()}")
        dashboard.root.destroy()

    dashboard.root.after(int(args.seconds * 1000), capture_and_close)
    dashboard.show()


if __name__ == "__main__":
    main()
