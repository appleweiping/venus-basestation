# Message Format

This document defines the first data contract between robot-side software and the base-station software.

The recommended payload format is JSON.

The current UART test from the mapping/embedded side sends messages as:

```text
4-byte payload length + JSON payload bytes
```

The base station normally receives the JSON after the ESP32 forwards it over
MQTT. For robustness, the parser also accepts MQTT payloads where this 4-byte
UART length prefix is still present.

## Event Types

- `robot_position`
- `rock`
- `cliff`
- `boundary`
- `mountain`
- `obstacle`
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
- `rock`, `cliff`, `boundary`, `mountain`, and `obstacle` observations updating map objects
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

The current Team 28 bridge addresses each board by the bare board number inside
the MQTT username, so the publish topic uses `15` for `robot_15_1` and `43` for
`robot_43_1`:

```text
VENUS_MQTT_HOST=mqtt.ics.ele.tue.nl
VENUS_MQTT_USERNAME=robot_15_1
# topic derived automatically -> /pynqbridge/15/send
```

Robot B follows the same rule: `robot_43_1` publishes on
`/pynqbridge/43/send`. If `VENUS_MQTT_TOPICS` is not set, the base station
derives the bare-board topic from `VENUS_MQTT_USERNAME` and also subscribes to
the older full-username form as a compatibility fallback, so the simplest
correct setup is to leave the topic unset.

Do not commit the MQTT password. Set `VENUS_MQTT_PASSWORD` locally when running
against the TU/e broker.
For one topic, either `VENUS_MQTT_TOPICS` or the single-topic alias
`VENUS_MQTT_TOPIC` is accepted.
Use `--mqtt-check --mqtt-min-messages 0` to verify broker login and topic
subscription without requiring a live robot payload.

The course manual describes the topic pattern in uppercase, but the current
Team 28 communication setup uses lowercase topics. MQTT topics are
case-sensitive, so use the exact numeric board topic from the communication
module unless the team changes it.

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
- `rock_found` -> `rock`
- `block_detected` -> `rock`
- `block_detection` -> `rock`
- `block_found` -> `rock`
- `sample_detected` -> `rock`
- `sample_detection` -> `rock`
- `sample_found` -> `rock`
- `cliff_detected` -> `cliff`
- `cliff_detection` -> `cliff`
- `cliff_found` -> `cliff`
- `boundary_detected` -> `boundary`
- `boundary_detection` -> `boundary`
- `boundary_found` -> `boundary`
- `border`, `border_detected`, `border_detection`, `border_found` -> `boundary`
- `edge`, `edge_detected`, `edge_detection`, `edge_found` -> `boundary`
- `mountain_detected` -> `mountain`
- `mountain_detection` -> `mountain`
- `mountain_found` -> `mountain`
- `obstacle_detected` -> `obstacle`
- `obstacle_detection` -> `obstacle`
- `obstacle_found` -> `obstacle`
- `status_update` -> `status`

Small field-name aliases are also accepted for demo robustness:

- `message_type` or `event` may be used instead of `type`;
- `robot` or `id` may be used instead of `robot_id`;
- `heading_deg` may be used instead of `heading`;
- `object_distance_mm` or `distance` may be used instead of `distance_mm`.

Transport-level tolerance:

- plain UTF-8 JSON MQTT payloads are accepted;
- UART-framed payloads with a 4-byte length prefix followed by UTF-8 JSON are
  accepted if the prefix length matches the remaining payload bytes.

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
