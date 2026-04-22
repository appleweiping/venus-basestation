from __future__ import annotations

from dataclasses import dataclass, field

from .message_schema import Observation


@dataclass
class MapObject:
    event_type: str
    x: float
    y: float
    robot_id: str
    label: str = ""
    temperature: float | None = None
    confidence: float | None = None


@dataclass
class RobotTrack:
    robot_id: str
    positions: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class MapState:
    robots: dict[str, RobotTrack] = field(default_factory=dict)
    objects: list[MapObject] = field(default_factory=list)
    statuses: dict[str, dict] = field(default_factory=dict)
    messages_seen: int = 0
    _object_keys: set[tuple[str, float, float, str]] = field(default_factory=set)

    def apply(self, observation: Observation) -> None:
        self.messages_seen += 1
        if observation.event_type == "robot_position":
            self._apply_robot_position(observation)
            return
        if observation.event_type == "status":
            self._apply_status(observation)
            return
        if observation.x is None or observation.y is None:
            return
        key = (
            observation.event_type,
            round(observation.x, 3),
            round(observation.y, 3),
            _label_for(observation),
        )
        if key in self._object_keys:
            return
        self._object_keys.add(key)
        self.objects.append(
            MapObject(
                event_type=observation.event_type,
                x=observation.x,
                y=observation.y,
                robot_id=observation.robot_id,
                label=_label_for(observation),
                temperature=observation.temperature,
                confidence=observation.confidence,
            )
        )

    def _apply_robot_position(self, observation: Observation) -> None:
        if observation.x is None or observation.y is None:
            return
        track = self.robots.setdefault(observation.robot_id, RobotTrack(observation.robot_id))
        track.positions.append((observation.x, observation.y))

    def _apply_status(self, observation: Observation) -> None:
        payload = dict(observation.raw or {})
        payload.setdefault("robot_id", observation.robot_id)
        payload.setdefault("event_type", observation.event_type)
        self.statuses[observation.robot_id] = payload

    def bounds(self) -> tuple[float, float, float, float] | None:
        xs: list[float] = []
        ys: list[float] = []
        for track in self.robots.values():
            for x, y in track.positions:
                xs.append(x)
                ys.append(y)
        for obj in self.objects:
            xs.append(obj.x)
            ys.append(obj.y)
        if not xs or not ys:
            return None
        return (min(xs), max(xs), min(ys), max(ys))

    def to_dict(self) -> dict:
        return {
            "messages_seen": self.messages_seen,
            "robots": {
                robot_id: {"positions": positions.positions}
                for robot_id, positions in self.robots.items()
            },
            "statuses": self.statuses,
            "objects": [
                {
                    "event_type": obj.event_type,
                    "x": obj.x,
                    "y": obj.y,
                    "robot_id": obj.robot_id,
                    "label": obj.label,
                    "temperature": obj.temperature,
                    "confidence": obj.confidence,
                }
                for obj in self.objects
            ],
        }


def _label_for(observation: Observation) -> str:
    if observation.event_type == "rock":
        parts = ["rock"]
        if observation.color:
            parts.append(observation.color)
        if observation.size:
            parts.append(observation.size)
        if observation.temperature is not None:
            parts.append(f"{observation.temperature:.1f}C")
        return " ".join(parts)
    return observation.event_type
