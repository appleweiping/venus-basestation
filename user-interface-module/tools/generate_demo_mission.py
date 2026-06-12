"""Generate a deterministic demo mission JSONL (three robots exploring an arena).

The scene mimics the course setup: centimeter coordinates from a corner
origin, a rectangular boundary, a mountain ridge, a cliff edge, scattered
rock samples, and periodic status / sensor telemetry.

Usage:
    PYTHONPATH=src python tools/generate_demo_mission.py [examples/demo_mission.jsonl]
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys


def build_messages() -> list[dict]:
    messages: list[dict] = []
    clock = 0.0

    def emit(payload: dict) -> None:
        nonlocal clock
        clock = round(clock + 0.4, 1)
        messages.append({"timestamp": clock, **payload})

    # Arena boundary posts (240 x 160 cm), sparse so the map stays readable.
    for x in range(0, 241, 60):
        emit({"robot_id": "robot_15_1", "event_type": "boundary", "x": x, "y": 0})
        emit({"robot_id": "robot_15_1", "event_type": "boundary", "x": x, "y": 160})
    for y in range(40, 160, 40):
        emit({"robot_id": "robot_43_1", "event_type": "boundary", "x": 0, "y": y})
        emit({"robot_id": "robot_43_1", "event_type": "boundary", "x": 240, "y": y})

    # robot_15_1: spiral sweep from the arena center.
    for step in range(26):
        angle = step * 0.42
        radius = 8 + step * 2.6
        x = round(120 + math.cos(angle) * radius, 1)
        y = round(80 + math.sin(angle) * radius * 0.66, 1)
        heading = round((math.degrees(angle) + 90) % 360, 1)
        emit({"robot_id": "robot_15_1", "event_type": "robot_position", "x": x, "y": y, "heading": heading})
        if step % 8 == 4:
            emit({"robot_id": "robot_15_1", "event_type": "status", "mode": "exploring", "battery": 96 - step * 2})
        if step in {7, 15, 23}:
            emit(
                {
                    "robot_id": "robot_15_1",
                    "event_type": "rock",
                    "x": round(x + 6, 1),
                    "y": round(y + 4, 1),
                    "color": ["red", "green", "blue"][step % 3],
                    "size": "large" if step % 2 else "small",
                    "distance_mm": 240 + step * 10,
                    "confidence": 0.9,
                }
            )
        if step == 11:
            emit({"robot_id": "robot_15_1", "event_type": "color_sensor", "color": "green"})

    # robot_43_1: lawnmower sweep across the west half.
    for step in range(24):
        row = step // 6
        forward = step % 6
        x = round(20 + (forward * 18 if row % 2 == 0 else (5 - forward) * 18), 1)
        y = round(24 + row * 34, 1)
        heading = 0.0 if row % 2 == 0 else 180.0
        emit({"robot_id": "robot_43_1", "event_type": "robot_position", "x": x, "y": y, "heading": heading})
        if step % 9 == 5:
            emit({"robot_id": "robot_43_1", "event_type": "status", "mode": "sweeping", "battery": 88 - step * 2})
        if step in {4, 16}:
            emit(
                {
                    "robot_id": "robot_43_1",
                    "event_type": "obstacle",
                    "x": round(x + 8, 1),
                    "y": round(y + 6, 1),
                    "distance_mm": 180,
                }
            )
        if step == 10:
            emit({"robot_id": "robot_43_1", "event_type": "distance_sensor", "distance_mm": 264})

    # robot_28_1: arc patrol along the mountain ridge in the north-east,
    # kept inside the 240 x 160 arena.
    for step in range(18):
        angle = math.pi * (0.15 + 0.04 * step)
        x = round(186 + math.cos(angle) * 42, 1)
        y = round(30 + math.sin(angle) * 92, 1)
        heading = round((math.degrees(angle) + 90) % 360, 1)
        emit({"robot_id": "robot_28_1", "event_type": "robot_position", "x": x, "y": y, "heading": heading})
        if step % 7 == 3:
            emit({"robot_id": "robot_28_1", "event_type": "status", "mode": "surveying", "battery": 74 - step})
        if step in {5, 9, 13}:
            emit(
                {
                    "robot_id": "robot_28_1",
                    "event_type": "mountain",
                    "x": round(x + 8, 1),
                    "y": round(y + 6, 1),
                }
            )
        if step in {8, 14}:
            emit(
                {
                    "robot_id": "robot_28_1",
                    "event_type": "cliff",
                    "x": round(x - 10, 1),
                    "y": round(y + 12, 1),
                }
            )

    # Final status round so every robot card shows fresh data.
    emit({"robot_id": "robot_15_1", "event_type": "status", "mode": "returning", "battery": 46})
    emit({"robot_id": "robot_43_1", "event_type": "status", "mode": "charging", "battery": 28})
    emit({"robot_id": "robot_28_1", "event_type": "status", "mode": "surveying", "battery": 58})
    return messages


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/demo_mission.jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    messages = build_messages()
    target.write_text("\n".join(json.dumps(message) for message in messages) + "\n", encoding="utf-8")
    print(f"wrote {len(messages)} messages to {target}")


if __name__ == "__main__":
    main()
