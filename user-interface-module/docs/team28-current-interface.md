# Team 28 Current Interface

This note captures the current base-station integration contract after the
2026-06-16 teammate update. Do not commit real MQTT passwords; keep them in a
local `.env` file or shell environment only.

## MQTT Settings

The TU/e MQTT broker is:

```text
host: mqtt.ics.ele.tue.nl
port: 1883
```

Authentication still uses the full robot username, but the current live topics
use the bare board number:

```text
robot A username: robot_15_1
robot A telemetry topic: /pynqbridge/15/send

robot B username: robot_43_1
robot B telemetry topic: /pynqbridge/43/send
robot B command topic: /pynqbridge/43/recv
```

When `VENUS_MQTT_TOPICS` is unset, the base station derives the bare-board
telemetry topic from `VENUS_MQTT_USERNAME` and also subscribes to the older
full-username topic as a fallback. This means `robot_43_1` subscribes to both
`/pynqbridge/43/send` and `/pynqbridge/robot_43_1/send`.

## Local Setup

Create `user-interface-module/.env` from `.env.example` and set the matching
username/password locally:

```powershell
cd user-interface-module
Copy-Item .env.example .env
# Edit .env; do not commit it.
```

For robot B, the key fields should be:

```text
VENUS_MQTT_HOST=mqtt.ics.ele.tue.nl
VENUS_MQTT_USERNAME=robot_43_1
VENUS_MQTT_PASSWORD=<robot B password>
```

Leave `VENUS_MQTT_TOPICS` and `VENUS_MQTT_COMMAND_TOPIC` unset unless the team
changes the bridge topics again.

Run a broker/subscription check without requiring live robot traffic:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source mqtt --headless --mqtt-check --mqtt-min-messages 0
```

Run the Tk dashboard:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source mqtt --ui tk
```

If the program shows simulated example data, it did not see
`VENUS_MQTT_USERNAME`; check that `.env` exists in `user-interface-module/` or
that the variables are exported in the shell that launches the program.

## Robot Commands

The robot processes structural commands at the end of its active execution
iteration. The base station publishes compact JSON payloads with QoS 1:

```json
{"command":"start","arguments":["--verbose"]}
```

```json
{"command":"idle","arguments":[]}
```

```json
{"command":"stop","arguments":[]}
```

By default, `robot_43_1` commands go to `/pynqbridge/43/recv`. A broker PUBACK
only means the broker accepted the publish; actual robot state must be confirmed
from returning telemetry.

## Payload Compatibility

The UI accepts the current Team 28 payload aliases, including:

- `position_update` -> `robot_position`
- `block_found`, `rock_detected`, `rock_found` -> `rock`
- `border_found`, `border_detected` -> `boundary`
- `mountain_found` -> `mountain`
- `cliff_found` -> `cliff`

Plain JSON MQTT payloads are accepted. UART-framed payloads with a 4-byte
length prefix are also accepted if the prefix length matches the JSON bytes.

## Still Needs Team Confirmation

- whether robot A also accepts commands at `/pynqbridge/15/recv`;
- whether `robot_id` stays as `"A"`/`"B"` or becomes the MQTT username;
- final coordinate units, origin, and heading convention;
- whether detected objects always include map `x` and `y`.
