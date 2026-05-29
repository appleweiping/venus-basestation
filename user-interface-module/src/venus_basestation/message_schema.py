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
    "obstacle",
    "status",
    "color_sensor",
    "distance_sensor",
}

TEAM_MESSAGE_TYPE_ALIASES = {
    "position_update": "robot_position",
    "robot_position_update": "robot_position",
    "position": "robot_position",
    "rock_detected": "rock",
    "rock_detection": "rock",
    "block_detected": "rock",
    "block_detection": "rock",
    "sample_detected": "rock",
    "sample_detection": "rock",
    "cliff_detected": "cliff",
    "cliff_detection": "cliff",
    "boundary_detected": "boundary",
    "boundary_detection": "boundary",
    "border": "boundary",
    "border_detected": "boundary",
    "border_detection": "boundary",
    "edge": "boundary",
    "edge_detected": "boundary",
    "edge_detection": "boundary",
    "mountain_detected": "mountain",
    "mountain_detection": "mountain",
    "obstacle_detected": "obstacle",
    "obstacle_detection": "obstacle",
    "status_update": "status",
    "color_detected": "color_sensor",
    "color_detection": "color_sensor",
    "color_reading": "color_sensor",
    "distance_reading": "distance_sensor",
    "distance_detected": "distance_sensor",
    "distance_detection": "distance_sensor",
}


@dataclass(frozen=True)
class Observation:
    robot_id: str
    event_type: str
    x: float | None = None
    y: float | None = None
    heading: float | None = None
    timestamp: float | None = None
    color: str | None = None
    size: str | None = None
    distance_mm: float | None = None
    temperature: float | None = None
    confidence: float | None = None
    raw: dict[str, Any] | None = None


def parse_observation(payload: str | bytes | dict[str, Any]) -> Observation:
    if isinstance(payload, bytes):
        payload = _strip_uart_length_prefix(payload).decode("utf-8")
    if isinstance(payload, str):
        payload = _strip_text_prefix(payload)
        data = json.loads(payload)
    else:
        data = dict(payload)

    data = normalize_team_payload(data)
    robot_id = str(data.get("robot_id", "")).strip()
    event_type = str(data.get("event_type", "")).strip()

    if not robot_id:
        raise ValueError("robot_id is required")
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type!r}")

    x = _optional_float(data.get("x"))
    y = _optional_float(data.get("y"))
    if event_type in {"robot_position", "rock", "cliff", "boundary", "mountain", "obstacle"} and (
        x is None or y is None
    ):
        raise ValueError(f"x and y are required for event_type {event_type!r}")
    # color_sensor and distance_sensor do NOT require x/y

    return Observation(
        robot_id=robot_id,
        event_type=event_type,
        x=x,
        y=y,
        heading=_optional_float(data.get("heading")),
        timestamp=_optional_float(data.get("timestamp")),
        color=_optional_str(data.get("color")),
        size=_optional_str(data.get("size")),
        distance_mm=_optional_float(data.get("distance_mm")),
        temperature=_optional_float(data.get("temperature")),
        confidence=_optional_float(data.get("confidence")),
        raw=data,
    )


def normalize_team_payload(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if "robot_id" not in normalized and "robot" in normalized:
        normalized["robot_id"] = normalized["robot"]
    if "robot_id" not in normalized and "id" in normalized:
        normalized["robot_id"] = normalized["id"]

    if not str(normalized.get("event_type", "")).strip():
        message_type = str(
            normalized.get("type") or normalized.get("message_type") or normalized.get("event") or ""
        ).strip()
        if message_type in TEAM_MESSAGE_TYPE_ALIASES:
            normalized["event_type"] = TEAM_MESSAGE_TYPE_ALIASES[message_type]
        elif message_type in VALID_EVENT_TYPES:
            normalized["event_type"] = message_type

    if "heading" not in normalized and "heading_deg" in normalized:
        normalized["heading"] = normalized["heading_deg"]
    if "distance_mm" not in normalized:
        if "object_distance_mm" in normalized:
            normalized["distance_mm"] = normalized["object_distance_mm"]
        elif "distance" in normalized:
            normalized["distance_mm"] = normalized["distance"]

    # Normalize color sensor fields from embedded module
    if "color" not in normalized and "detected_color" in normalized:
        normalized["color"] = normalized["detected_color"]
    if "color" not in normalized and "colour" in normalized:
        normalized["color"] = normalized["colour"]

    return normalized


def _strip_uart_length_prefix(payload: bytes) -> bytes:
    if len(payload) < 5 or payload[:1] in {b"{", b"["}:
        return payload

    body = payload[4:]
    for byte_order in ("little", "big"):
        expected_length = int.from_bytes(payload[:4], byte_order)
        if expected_length == len(body):
            return body
    return payload


def _strip_text_prefix(payload: str) -> str:
    stripped = payload.lstrip()
    if stripped.startswith(("{", "[")):
        return stripped

    json_start = min(
        (index for index in (payload.find("{"), payload.find("[")) if index != -1),
        default=-1,
    )
    if json_start == -1:
        return payload

    prefix = payload[:json_start]
    if len(prefix) == 4 and any(ord(char) < 32 for char in prefix):
        return payload[json_start:]
    return payload


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
