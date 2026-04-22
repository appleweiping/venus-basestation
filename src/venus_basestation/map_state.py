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
    messages_seen: int = 0

    def apply(self, observation: Observation) -> None:
        self.messages_seen += 1
        if observation.event_type == "robot_position":
            self._apply_robot_position(observation)
            return
        if observation.x is None or observation.y is None:
            return
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

