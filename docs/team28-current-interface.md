# Team 28 Current Interface

This note captures the current interface found in the Team 28 GitLab branches on 2026-05-08.

It is not a final contract. It is the best current bridge between the communication module and the user-interface/base-station module.

## Current MQTT Settings

The communication-module branch currently uses:

```text
host: mqtt.ics.ele.tue.nl
topic: /pynqbridge/robot_43_1/send
username: robot_43_1
```

The password exists in the communication test script, but should not be copied into this repository or committed again. Set it locally with:

```powershell
$env:VENUS_MQTT_PASSWORD="<password from the communication-module owner>"
```

The base-station defaults now match the current host and topic. For explicit local setup:

```powershell
$env:PYTHONPATH="src"
$env:VENUS_MQTT_HOST="mqtt.ics.ele.tue.nl"
$env:VENUS_MQTT_USERNAME="robot_43_1"
$env:VENUS_MQTT_PASSWORD="<password from the communication-module owner>"
$env:VENUS_MQTT_TOPICS="/pynqbridge/robot_43_1/send"
python -m venus_basestation --source mqtt --headless --save-state outputs\live_mqtt_state.json
```

For the Tkinter UI:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source mqtt --ui tk
```

For a demo-prep smoke check without opening the UI:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source mqtt --headless --mqtt-check --mqtt-timeout 15 --save-state outputs\mqtt_check_state.json
```

This prints sanitized MQTT settings and waits for at least one parseable message.
If it connects but receives zero messages, the likely causes are: no robot currently
publishing, wrong topic, broker/network issue, or a payload shape outside the
documented compatibility aliases.

## Current Payloads

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

The user-interface module already accepts these shapes.

The user-interface module now preserves the Team 28 coordinate metadata in structured state:

- `heading` is stored on the latest robot track and shown/exported as degrees.
- `distance_mm` is stored on detected objects and shown/exported as sensor-relative metadata.
- Object markers are still plotted at the provided `x` and `y`, because the payload already includes object coordinates.

## Coordinate Interpretation From Current Code

Reading the Team 28 communication, mapping, and navigation branches gives this current best interpretation:

- `x` and `y` are map coordinates supplied by the robot-side modules.
- The navigation code moves and records distance in centimeters, so `x` and `y` are most likely centimeters from the startup origin.
- The mapping/navigation code does not currently define a complete final heading convention, so the UI records `heading` as raw degrees and does not transform it.
- `distance_mm` is a sensor/object-distance field, not a map-coordinate unit for `x` and `y`.

This means the UI can proceed without another teammate answer for basic compatibility: it receives their values, stores them, displays them, and avoids making unsupported coordinate transformations.

## Extra Runtime Tolerance

The parser also accepts these likely small field-name variations so the demo is less brittle:

- `message_type` or `event` instead of `type`;
- `robot` or `id` instead of `robot_id`;
- `rock_detection`, `cliff_detection`, `boundary_detection`, and `mountain_detection` aliases;
- `heading_deg` instead of `heading`;
- `object_distance_mm` or `distance` instead of `distance_mm`.

Unsupported or malformed MQTT messages are logged and skipped instead of stopping the UI.

## Still Needs Team Confirmation

- whether `/pynqbridge/robot_43_1/send` is final for the demo;
- whether `robot_id` will stay as `"A"` or become a real robot/module identifier;
- whether the current centimeter/startup-origin interpretation of `x` and `y` is the final demo contract;
- what `heading = 0` and `heading = 90` mean physically if the UI later needs an arrow or rotation;
- whether detected objects will always include object `x` and `y`;
- whether additional object types will be sent before the demo.

## Observed Risks Outside The UI Module

- The mapping/navigation code currently does not provide a complete final coordinate contract.
- The embedded distance-sensor branch contains unresolved merge-conflict markers in one file.
- Broker/network availability still requires a live run close to demo time.
