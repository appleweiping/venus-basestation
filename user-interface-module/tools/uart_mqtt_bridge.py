#!/usr/bin/env python3
"""UART -> MQTT bridge for the Venus robot (run ON the PYNQ board).

WHY THIS EXISTS
---------------
Team 28's robot firmware (the `communication` app on the `main` branch) writes
telemetry to **UART0** as `4-byte little-endian length + JSON payload`. Nothing
in the team repo relays that UART stream onto MQTT, so the base-station
dashboard — which subscribes to ``/pynqbridge/<board>/send`` — sees nothing
unless the course's own pynqbridge/ESP32 relay is doing the UART<->MQTT hop.

This script is that missing relay, as a standalone fallback: it reads the
framed JSON from a serial port and republishes each payload to the MQTT topic
the dashboard listens on. Give it to the embedded teammate, or run it on the
PYNQ alongside the firmware.

  ┌─────────────┐  UART0 (4B len + JSON)  ┌────────────────┐  MQTT publish  ┌───────────┐
  │  firmware   │ ───────────────────────▶│ uart_mqtt_bridge│ ─────────────▶ │  broker   │
  │ communication.c                       │ (this script)   │  /pynqbridge/  │           │
  └─────────────┘                         └────────────────┘  <user>/send   └───────────┘

NOT HARDWARE-VERIFIED. The frame parser below is unit-tested offline
(tests/test_uart_bridge.py), but the serial device name, baud rate, and
whether this relay is even needed (vs the course ESP32 bridge) MUST be
confirmed with the embedded teammate / on the actual board before relying on
it for a demo.

USAGE (on the PYNQ, once paho-mqtt + pyserial are installed):
    pip install pyserial paho-mqtt
    VENUS_MQTT_USERNAME=robot_43_1 VENUS_MQTT_PASSWORD=... \
        python uart_mqtt_bridge.py --serial /dev/ttyUSB0 --baud 115200

The topic defaults to /pynqbridge/<board>/send, derived from
VENUS_MQTT_USERNAME (matching the dashboard); override with --topic. CONFIRM
the serial device with the board:
it may be /dev/ttyUSB0, /dev/ttyPS1, /dev/ttyACM0, or COMx on Windows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

# Firmware sends strlen(payload) (< 128 bytes in practice); cap well above that
# so a desynced/garbage length prefix is rejected instead of stalling the read.
MAX_PAYLOAD = 8192
COURSE_USERNAME_RE = re.compile(r"^robot_(?P<board>\d+)_\d+$")


def parse_frames(buffer: bytes, *, max_payload: int = MAX_PAYLOAD) -> tuple[list[bytes], bytes]:
    """Extract complete ``4-byte LE length + JSON`` frames from ``buffer``.

    Returns ``(payloads, remaining)`` where ``payloads`` is the list of
    complete JSON payload byte-strings and ``remaining`` is the leftover bytes
    (an incomplete trailing frame) to prepend to the next read. Pure function —
    no serial or MQTT — so it is fully unit-testable with synthetic bytes.

    Matches Team 28's ``send_message_uart`` exactly: a little-endian uint32
    length followed by that many payload bytes. Resyncs on a garbage prefix by
    skipping one byte, and only accepts a frame whose payload begins with ``{``
    (the firmware always emits a JSON object), so a corrupt/misaligned stream
    recovers instead of locking onto a fake length.
    """
    payloads: list[bytes] = []
    offset = 0
    while len(buffer) - offset >= 4:
        length = int.from_bytes(buffer[offset : offset + 4], "little")
        if length == 0 or length > max_payload:
            offset += 1  # implausible length -> desync, skip a byte and retry
            continue
        end = offset + 4 + length
        if len(buffer) < end:
            break  # frame not fully received yet; keep it for the next read
        payload = buffer[offset + 4 : end]
        if not payload.lstrip().startswith(b"{"):
            offset += 1  # not a JSON object -> desync, skip a byte
            continue
        payloads.append(payload)
        offset = end
    return payloads, buffer[offset:]


def resolve_topic(args_topic: str | None, username: str) -> str:
    if args_topic:
        return args_topic
    username = username.strip()
    match = COURSE_USERNAME_RE.fullmatch(username)
    if not match:
        raise SystemExit(
            "no topic and no valid VENUS_MQTT_USERNAME set; pass --topic /pynqbridge/<board>/send"
        )
    return f"/pynqbridge/{match.group('board')}/send"


def main() -> None:
    parser = argparse.ArgumentParser(description="Relay framed JSON from UART to MQTT.")
    parser.add_argument("--serial", default=os.getenv("VENUS_UART_DEVICE", "/dev/ttyUSB0"),
                        help="Serial device the firmware writes to (CONFIRM with the board).")
    parser.add_argument("--baud", type=int, default=int(os.getenv("VENUS_UART_BAUD", "115200")))
    parser.add_argument("--broker", default=os.getenv("VENUS_MQTT_HOST", "mqtt.ics.ele.tue.nl"))
    parser.add_argument("--port", type=int, default=int(os.getenv("VENUS_MQTT_PORT", "1883")))
    parser.add_argument("--username", default=os.getenv("VENUS_MQTT_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("VENUS_MQTT_PASSWORD", ""))
    parser.add_argument("--topic", default=os.getenv("VENUS_MQTT_TOPICS", "") or None,
                        help="MQTT topic to publish to (default: /pynqbridge/<board>/send).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read and print frames without connecting to MQTT (serial-only check).")
    args = parser.parse_args()

    topic = resolve_topic(args.topic, args.username)

    try:
        import serial  # pyserial
    except ModuleNotFoundError:
        raise SystemExit("pyserial is required: pip install pyserial")

    client = None
    if not args.dry_run:
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError:
            raise SystemExit("paho-mqtt is required: pip install paho-mqtt")
        client = mqtt.Client()
        if args.username:
            client.username_pw_set(args.username, args.password)
        client.connect(args.broker, args.port, keepalive=60)
        client.loop_start()
        print(f"connected to MQTT {args.broker}:{args.port}, publishing UART frames to {topic}")
    else:
        print(f"dry-run: reading {args.serial} @ {args.baud}, NOT publishing")

    try:
        ser = serial.Serial(args.serial, args.baud, timeout=0.5)
    except Exception as exc:  # serial.SerialException and friends
        raise SystemExit(
            f"could not open serial port {args.serial} @ {args.baud}: {exc}. "
            "Confirm the device name with the board / embedded teammate."
        )

    buffer = b""
    forwarded = 0
    try:
        while True:
            chunk = ser.read(256)
            if not chunk:
                continue
            buffer += chunk
            payloads, buffer = parse_frames(buffer)
            for payload in payloads:
                text = payload.decode("utf-8", errors="replace")
                try:
                    json.loads(text)  # skip anything that is not valid JSON
                except json.JSONDecodeError:
                    print(f"skipping non-JSON frame: {text!r}", file=sys.stderr)
                    continue
                if client is not None:
                    client.publish(topic, text, qos=0)
                forwarded += 1
                print(f"[{forwarded}] {text}")
    except KeyboardInterrupt:
        print(f"\nstopping; forwarded {forwarded} frames")
    finally:
        try:
            ser.close()
        except Exception:
            pass
        if client is not None:
            client.loop_stop()
            client.disconnect()


if __name__ == "__main__":
    main()
