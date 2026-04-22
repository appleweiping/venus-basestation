# Venus Basestation

Base-station software and visualization dashboard for a Venus-style robotics exploration project.

The project receives robot observations, maintains a simple world model, and visualizes the explored terrain. It is designed to start with simulated messages and later connect to real MQTT topics.

## Goals

- Receive robot telemetry and object observations.
- Track robot paths and discovered terrain features.
- Visualize rocks, cliffs, mountains, boundaries, and robot positions.
- Keep the message format explicit so robot-side software and UI software can integrate cleanly.
- Support simulation and replay before the physical robots are ready.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m venus_basestation --source simulated
```

For a headless smoke run:

```powershell
python -m venus_basestation --source simulated --headless --steps 20
```

## Project Layout

```text
src/venus_basestation/
  __main__.py          CLI entry point
  dashboard.py         Matplotlib visualization
  fake_messages.py     Simulated robot observations
  map_state.py         In-memory world model
  message_schema.py    Message parsing and validation
  mqtt_client.py       MQTT subscriber wrapper
docs/
  message-format.md    Shared data contract for robot-side integration
examples/
  sample_messages.jsonl
tests/
```

## Message Flow

```text
robot / simulator
  -> MQTT or local generator
  -> message parser
  -> map state
  -> dashboard
```

## Safety

Do not commit credentials.

Use environment variables or a local ignored file for real MQTT credentials:

- `VENUS_MQTT_HOST`
- `VENUS_MQTT_USERNAME`
- `VENUS_MQTT_PASSWORD`
- `VENUS_MQTT_TOPICS`

