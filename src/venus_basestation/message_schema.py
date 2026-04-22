from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


VALID_EVENT_TYPES = {
    "robot_position",
    "rock",
    "cliff",
    "boundary",
    "mountain",
    "status",
}


@dataclass(frozen=True)
class Observation:
    robot_id: str
    event_type: str
    x: float | None = None
    y: float | None = None
    timestamp: float | None = None
    color: str | None = None
    size: str | None = None
    temperature: float | None = None
    confidence: float | None = None
    raw: dict[str, Any] | None = None


def parse_observation(payload: str | bytes | dict[str, Any]) -> Observation:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = dict(payload)

    robot_id = str(data.get("robot_id", "")).strip()
    event_type = str(data.get("event_type", "")).strip()

    if not robot_id:
        raise ValueError("robot_id is required")
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type!r}")

    return Observation(
        robot_id=robot_id,
        event_type=event_type,
        x=_optional_float(data.get("x")),
        y=_optional_float(data.get("y")),
        timestamp=_optional_float(data.get("timestamp")),
        color=_optional_str(data.get("color")),
        size=_optional_str(data.get("size")),
        temperature=_optional_float(data.get("temperature")),
        confidence=_optional_float(data.get("confidence")),
        raw=data,
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

