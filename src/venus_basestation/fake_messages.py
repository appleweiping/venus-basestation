from __future__ import annotations

from collections.abc import Iterator
import json
import math
import time


def simulated_messages(count: int | None = None, delay: float = 0.0) -> Iterator[str]:
    step = 0
    while count is None or step < count:
        robot_id = "robot_1" if step % 2 == 0 else "robot_2"
        x = round(math.cos(step / 5) + step * 0.04, 3)
        y = round(math.sin(step / 5) + (0.3 if robot_id == "robot_2" else 0.0), 3)
        yield json.dumps(
            {
                "robot_id": robot_id,
                "event_type": "robot_position",
                "x": x,
                "y": y,
                "timestamp": step,
            }
        )

        if step in {5, 12, 18}:
            yield json.dumps(
                {
                    "robot_id": robot_id,
                    "event_type": "rock",
                    "x": round(x + 0.1, 3),
                    "y": round(y + 0.15, 3),
                    "color": ["red", "green", "blue"][step % 3],
                    "size": "small" if step % 2 else "large",
                    "temperature": 24.0 + step / 10,
                    "confidence": 0.85,
                    "timestamp": step + 0.1,
                }
            )

        if step in {8, 16}:
            yield json.dumps(
                {
                    "robot_id": robot_id,
                    "event_type": "cliff",
                    "x": round(x - 0.2, 3),
                    "y": round(y + 0.2, 3),
                    "timestamp": step + 0.2,
                }
            )

        step += 1
        if delay:
            time.sleep(delay)

