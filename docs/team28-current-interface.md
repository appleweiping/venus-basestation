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

## Still Needs Team Confirmation

- whether `/pynqbridge/robot_43_1/send` is final for the demo;
- whether `robot_id` will stay as `"A"` or become a real robot/module identifier;
- whether `x` and `y` are centimeters, meters, grid cells, or another unit;
- what `heading = 0` and `heading = 90` mean physically;
- whether detected objects should use robot position, object position, or distance-relative position;
- whether additional object types will be sent before the demo.

## Observed Risks Outside The UI Module

- The mapping/navigation code currently does not provide a complete final coordinate contract.
- The embedded distance-sensor branch contains unresolved merge-conflict markers in one file.
- Broker/network availability still requires a live run close to demo time.
