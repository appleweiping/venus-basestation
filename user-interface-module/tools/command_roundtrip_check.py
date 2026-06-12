"""End-to-end command uplink check against the public HiveMQ test broker.

Subscribes to a scratch topic, publishes an ``idle`` command through
``MqttCommandSender`` (the same code path as ``--send-command``), and
verifies the payload arrives byte-for-byte. Uses ``idle`` deliberately —
harmless even if a teammate's test device happens to listen on the topic.

Usage:
    PYTHONPATH=src python tools/command_roundtrip_check.py [topic-suffix]
"""

from __future__ import annotations

import sys
import time

from venus_basestation.mqtt_client import MqttCommandSender, build_command


HOST = "broker.hivemq.com"
PORT = 1883


def main() -> int:
    suffix = sys.argv[1] if len(sys.argv) > 1 else "uplink-roundtrip"
    topic = f"energy_venus/team28/{suffix}"

    import paho.mqtt.client as mqtt

    received: list[bytes] = []
    subscribed = False

    def handle_connect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
        client.subscribe(topic, qos=1)

    def handle_subscribe(client, userdata, mid, reason_codes, properties):  # noqa: ANN001
        nonlocal subscribed
        subscribed = True

    def handle_message(client, userdata, message):  # noqa: ANN001
        received.append(message.payload)

    listener = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    listener.on_connect = handle_connect
    listener.on_subscribe = handle_subscribe
    listener.on_message = handle_message
    listener.connect_timeout = 5.0
    listener.connect(HOST, PORT)
    listener.loop_start()
    try:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not subscribed:
            time.sleep(0.05)
        if not subscribed:
            print(f"FAIL: could not subscribe to {topic} on {HOST}")
            return 1

        payload = build_command("idle")
        MqttCommandSender(HOST, PORT).send(topic, payload, timeout=10.0)

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and not received:
            time.sleep(0.05)
    finally:
        listener.loop_stop()
        listener.disconnect()

    if not received:
        print(f"FAIL: command was published but never received on {topic}")
        return 1
    expected = payload.encode("utf-8")
    if received[0] != expected:
        print(f"FAIL: received {received[0]!r}, expected {expected!r}")
        return 1
    print(f"PASS: byte-identical command round-trip on {HOST} topic {topic}: {received[0].decode('utf-8')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
