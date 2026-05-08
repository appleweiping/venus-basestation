# Message Format

This document defines the first data contract between robot-side software and the base-station software.

The recommended payload format is JSON.

## Event Types

- `robot_position`
- `rock`
- `cliff`
- `boundary`
- `mountain`
- `status`

## Common Fields

```json
{
  "robot_id": "robot_1",
  "event_type": "rock",
  "x": 1.2,
  "y": 0.8,
  "timestamp": 12.3
}
```

## Rock Observation

```json
{
  "robot_id": "robot_1",
  "event_type": "rock",
  "x": 1.2,
  "y": 0.8,
  "color": "red",
  "size": "small",
  "temperature": 24.5,
  "confidence": 0.9,
  "timestamp": 12.3
}
```

## Status Message

```json
{
  "robot_id": "robot_2",
  "event_type": "status",
  "battery": 82,
  "mode": "exploring",
  "timestamp": 15.4
}
```

Status messages are optional but useful for the base station. The current prototype stores the latest status payload per robot in the exported state summary.

## Current Prototype Assumptions

The current base-station prototype already supports:

- `robot_position` messages updating robot tracks
- `rock`, `cliff`, `boundary`, and `mountain` observations updating map objects
- `status` messages updating the latest per-robot status snapshot
- JSONL replay for offline testing
- SVG snapshot export without extra plotting dependencies

## Coordinate System

Current Team 28 assumption after reading the communication and navigation code:

- `x` and `y` are treated as robot-provided map coordinates and displayed without conversion.
- The navigation code uses centimeter-based movement and distance registers, so the best current inference is that `x` and `y` are centimeters from the robot startup origin.
- Positive `x` points right on the dashboard and positive `y` points upward on the dashboard.
- `heading` / `heading_deg` is parsed, stored, exported, and displayed in degrees, but the UI does not rotate or transform coordinates from it because the final physical heading convention is not complete in the navigation code.
- `distance_mm` on object detections is preserved as sensor-relative metadata. Objects are plotted at the payload's provided `x` and `y`.

If the navigation module later changes units or origin, the UI should update the labels/docs rather than silently converting old data.

## MQTT Topics

The course manual describes PYNQ bridge topics in this general form:

```text
/PYNQBRIDGE/{MODULE}/SEND
/PYNQBRIDGE/{MODULE}/RECV
```

The exact module identifiers and credentials should stay out of Git.

The Team 28 communication branch currently uses the TU/e broker and prototype
topic below in its MQTT test scripts:

```text
VENUS_MQTT_HOST=mqtt.ics.ele.tue.nl
VENUS_MQTT_USERNAME=robot_43_1
VENUS_MQTT_TOPICS=/pynqbridge/robot_43_1/send
```

Do not commit the MQTT password. Set `VENUS_MQTT_PASSWORD` locally when running
against the TU/e broker.
For one topic, either `VENUS_MQTT_TOPICS` or the single-topic alias
`VENUS_MQTT_TOPIC` is accepted.

The course manual describes the topic pattern in uppercase, but the current
Team 28 communication prototype uses the lowercase topic above. MQTT topics are
case-sensitive, so use the exact topic from the communication module unless the
team changes it.

## Team 28 Compatibility Payloads

The communication module prototype currently publishes these JSON shapes. The
base-station parser accepts them and normalizes them internally to the event
types above. The parser also preserves Team 28 coordinate metadata:

- `heading` or `heading_deg` for position updates
- `distance_mm` for object detections

Position update:

```json
{
  "robot_id": "A",
  "type": "position_update",
  "x": 3,
  "y": 5,
  "heading": 90
}
```

Rock detection:

```json
{
  "robot_id": "A",
  "type": "rock_detected",
  "x": 3,
  "y": 5,
  "distance_mm": 120,
  "color": "red",
  "size": "small",
  "temperature": 28.5
}
```

Supported compatibility aliases:

- `position_update` -> `robot_position`
- `robot_position_update` -> `robot_position`
- `position` -> `robot_position`
- `rock_detected` -> `rock`
- `rock_detection` -> `rock`
- `cliff_detected` -> `cliff`
- `cliff_detection` -> `cliff`
- `boundary_detected` -> `boundary`
- `boundary_detection` -> `boundary`
- `mountain_detected` -> `mountain`
- `mountain_detection` -> `mountain`
- `status_update` -> `status`

Small field-name aliases are also accepted for demo robustness:

- `message_type` or `event` may be used instead of `type`;
- `robot` or `id` may be used instead of `robot_id`;
- `heading_deg` may be used instead of `heading`;
- `object_distance_mm` or `distance` may be used instead of `distance_mm`.

## Integration Checklist

Before connecting to the real robots, the team should confirm:

- exact publish topic per robot
- exact payload shape
- coordinate origin
- units
- physical meaning of `heading = 0` and rotation direction
- robot identifiers
- duplicate observation behavior
- how uncertainty should be represented
