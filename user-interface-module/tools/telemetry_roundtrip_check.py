"""End-to-end telemetry check: publish Team 28's exact wire format, receive it.

This proves the topic fix on the real course broker. It runs our
``MqttSubscriber`` on the username-derived topic and, from a separate client,
publishes the same messages Team 28's ``hybrid_publisher_course.py`` sends
(``{"robot_id":"A","type":"position_update",...}`` and ``rock_detected``).
It then asserts the messages arrived, parsed, and updated the map state —
the chain that "interface doesn't work" was breaking.

Publishing to the ``/send`` (telemetry) topic mimics the team's own test
publisher and never commands the robot (that is the ``/recv`` topic).

Usage:
    # course broker (reads VENUS_MQTT_* from the environment / config.local.*):
    PYTHONPATH=src python tools/telemetry_roundtrip_check.py
    # public test broker (no credentials needed):
    PYTHONPATH=src python tools/telemetry_roundtrip_check.py --profile test
"""

from __future__ import annotations

import argparse
import json
import threading
import time

from venus_basestation.map_state import MapState
from venus_basestation.mqtt_client import MqttSubscriber, mqtt_config_from_env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    config = mqtt_config_from_env()
    host = str(config["host"])
    port = int(config["port"])
    topic = list(config["topics"])[0]
    username = str(config["username"])
    password = str(config["password"])

    print(f"roundtrip: host={host} port={port} topic={topic} username={username or '<none>'}")

    state = MapState()
    subscriber = MqttSubscriber(
        host=host,
        port=port,
        topics=[topic],
        username=username,
        password=password,
        on_observation=state.apply,
        on_log=lambda message: print(f"  [sub] {message}"),
    )

    # Run our subscriber on a background thread, exactly like the live UI does.
    received = threading.Event()
    original_apply = state.apply

    def tracking_apply(observation) -> None:
        original_apply(observation)
        received.set()

    state.apply = tracking_apply  # type: ignore[method-assign]

    sub_thread = threading.Thread(
        target=lambda: subscriber.run_until(args.timeout, min_messages=2),
        name="roundtrip-subscriber",
        daemon=True,
    )
    sub_thread.start()

    # Give the subscriber time to connect and have its subscription acked.
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline and not subscriber.connected:
        time.sleep(0.05)
    if not subscriber.connected:
        print("FAIL: subscriber could not connect to the broker")
        return 1
    time.sleep(0.5)  # let SUBACK land

    import paho.mqtt.client as mqtt

    publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if username:
        publisher.username_pw_set(username, password)
    publisher.connect(host, port)
    publisher.loop_start()
    try:
        # Byte-for-byte the messages Team 28's hybrid_publisher_course.py sends.
        messages = [
            {"robot_id": "A", "type": "position_update", "x": 0, "y": 0, "heading": 90},
            {
                "robot_id": "A",
                "type": "rock_detected",
                "x": 0,
                "y": 0,
                "distance_mm": 120,
                "color": "red",
                "size": "small",
                "temperature": 28.5,
            },
        ]
        for message in messages:
            info = publisher.publish(topic, json.dumps(message), qos=1)
            info.wait_for_publish(timeout=5.0)
            print(f"  [pub] {message['type']}")
            time.sleep(0.3)
    finally:
        publisher.loop_stop()
        publisher.disconnect()

    sub_thread.join(timeout=args.timeout)

    if state.messages_seen < 2:
        print(f"FAIL: received {state.messages_seen} messages (expected >= 2)")
        return 1
    if "A" not in state.robots:
        print(f"FAIL: robot 'A' not tracked; robots={list(state.robots)}")
        return 1
    rock_count = state.object_counts().get("rock", 0)
    if rock_count < 1:
        print(f"FAIL: rock detection not recorded; objects={state.object_counts()}")
        return 1

    print(
        f"PASS: received {state.messages_seen} messages on {topic}; "
        f"robot 'A' tracked at {state.robots['A'].positions[-1]}, "
        f"rock detections={rock_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
