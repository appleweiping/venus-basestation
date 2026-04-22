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

