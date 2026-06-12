# Team 28 Current Interface

This note captures the current interface found in the Team 28 GitLab branches on 2026-05-08, the teammate-provided MQTT board credentials received on 2026-06-05, and the robot command interface received on 2026-06-12.

It is not a final contract. It is the best current bridge between the communication module and the user-interface/base-station module.

## Current MQTT Settings

The teammate-provided course broker settings currently use numeric communication-board topics:

```text
host: mqtt.ics.ele.tue.nl
robot A topic: /pynqbridge/15/send
robot A username: robot_15_1
robot B topic: /pynqbridge/43/send
robot B username: robot_43_1
```

Passwords should not be copied into this repository or committed. Set the matching password locally with:

```powershell
$env:VENUS_MQTT_PASSWORD="<password from the communication-module owner>"
```

The base station derives the numeric topic from `VENUS_MQTT_USERNAME` when
`VENUS_MQTT_TOPICS` is not set. For explicit local setup with robot A:

```powershell
$env:PYTHONPATH="src"
$env:VENUS_MQTT_HOST="mqtt.ics.ele.tue.nl"
$env:VENUS_MQTT_USERNAME="robot_15_1"
$env:VENUS_MQTT_PASSWORD="<password from the communication-module owner>"
$env:VENUS_MQTT_TOPICS="/pynqbridge/15/send"
python -m venus_basestation --source mqtt --headless --save-state outputs\live_mqtt_state.json
```

For robot B, use `VENUS_MQTT_USERNAME="robot_43_1"` and
`VENUS_MQTT_TOPICS="/pynqbridge/43/send"` with robot B's matching password.

For the Tkinter UI:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source mqtt --ui tk
```

For a demo-prep smoke check without opening the UI:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source mqtt --headless --mqtt-check --mqtt-timeout 15 --mqtt-min-messages 0 --save-state outputs\mqtt_check_state.json
```

This prints sanitized MQTT settings and verifies the broker login plus
subscription acknowledgement. Keep `--mqtt-min-messages 0` when the robot is not
publishing yet. Remove it or set it to `1` when you want to require one
parseable live robot message too.

If broker login or subscription fails, the check reports that setup error. If
live-message mode receives zero messages, the likely causes are: no robot
currently publishing, a payload shape outside the documented compatibility
aliases, or a robot-side publishing issue.

The mapping/embedded UART test documents the robot-to-ESP32 frame as
`4 bytes payload length + JSON payload bytes`. The base station still expects
MQTT messages to be JSON, but it now also tolerates messages where that 4-byte
UART length prefix is forwarded together with the JSON payload.

## Robot Command Interface (received 2026-06-12)

The embedded module confirmed the broker constraints (host
`mqtt.ics.ele.tue.nl`, port `1883`, standard unencrypted TCP, board
credentials as above) and defined the inbound control channel:

- The robot **subscribes** to `/pynqbridge/43/recv` (board 43; the base
  station derives `/pynqbridge/<board>/recv` from the username).
- The robot processes structural state changes cleanly **upon completing its
  active execution iteration step** — commands are not applied mid-iteration,
  so the UI reports "sent", and the actual state change is confirmed by
  returning telemetry.

Supported command payloads (sent verbatim by the base station, compact JSON):

```json
{"command":"start","arguments":["--verbose"]}
```

Start Navigation: exit the initial IDLE hold or resume from a paused state to
execute spatial tracking.

```json
{"command":"idle","arguments":[]}
```

Pause Navigation: break execution safely, park motors, and enter a
non-blocking IDLE loop waiting for a subsequent resume signal.

```json
{"command":"stop","arguments":[]}
```

Emergency Stop (Kill): immediately halt program loops, destroy peripheral
configurations safely, and completely terminate the application framework on
the embedded architecture.

The base station publishes commands with QoS 1 (at-least-once): an emergency
stop must not be lost, and the iteration-boundary processing makes duplicate
delivery harmless. Commands are available from the dashboard COMMAND UPLINK
panel in live MQTT mode, or headless via
`python -m venus_basestation --source mqtt --send-command {start,idle,stop}`.

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

The supplied design-report and brainstorming ZIP files do not define a different JSON payload or MQTT topic. They describe the same hybrid approach: periodic position updates plus immediate event messages for rocks, cliffs/borders, mountains, obstacles, and robot positions.

The parser also accepts these likely small field-name variations so the demo is less brittle:

- `message_type` or `event` instead of `type`;
- `robot` or `id` instead of `robot_id`;
- `rock_detection`, `cliff_detection`, `boundary_detection`, `mountain_detection`, and `obstacle_detection` aliases;
- current live `*_found` aliases such as `block_found`, `border_found`,
  `mountain_found`, and `cliff_found`;
- design-report vocabulary such as `border_detected`, `edge_detected`, and `block_detected`;
- `heading_deg` instead of `heading`;
- `object_distance_mm` or `distance` instead of `distance_mm`.
- an optional 4-byte UART length prefix before the JSON payload, when the
  prefix length matches the JSON byte length.

Unsupported or malformed MQTT messages are logged and skipped instead of stopping the UI.

## Still Needs Team Confirmation

- whether the teammate-provided numeric board topics remain final for the demo;
- whether `robot_id` will stay as `"A"` or become a real robot/module identifier;
- whether the current centimeter/startup-origin interpretation of `x` and `y` is the final demo contract;
- what `heading = 0` and `heading = 90` mean physically if the UI later needs an arrow or rotation;
- whether detected objects will always include object `x` and `y`;
- whether additional object types will be sent before the demo.

## Observed Risks Outside The UI Module

- The mapping/navigation code currently does not provide a complete final coordinate contract.
- The embedded distance-sensor branch contains unresolved merge-conflict markers in one file.
- Broker/network availability still requires a live run close to demo time.
