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

Initial assumption:

- coordinates are relative to the team's chosen map origin
- unit is meters unless the team decides otherwise
- positive `x` points right on the dashboard
- positive `y` points upward on the dashboard

This should be confirmed with the robot-side team early.

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
VENUS_MQTT_TOPICS=/PYNQBRIDGE/YOUR_MODULE/SEND
```

Replace `YOUR_MODULE` with the final bridge module identifier once the team
confirms it.

## Team 28 Compatibility Payloads

The communication module prototype currently publishes these JSON shapes. The
base-station parser accepts them and normalizes them internally to the event
types above.

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
- `rock_detected` -> `rock`
- `cliff_detected` -> `cliff`
- `boundary_detected` -> `boundary`
- `mountain_detected` -> `mountain`
- `status_update` -> `status`

## Integration Checklist

Before connecting to the real robots, the team should confirm:

- exact publish topic per robot
- exact payload shape
- coordinate origin
- units
- robot identifiers
- duplicate observation behavior
- how uncertainty should be represented
