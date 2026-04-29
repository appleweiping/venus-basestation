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
if (Test-Path .\.venv\Scripts\Activate.ps1) { .\.venv\Scripts\Activate.ps1 } else { .\.venv\bin\Activate.ps1 }
pip install -r requirements.txt
$env:PYTHONPATH="src"
python -m venus_basestation --source simulated
```

This launches the built-in Tkinter desktop UI, which does not require extra GUI dependencies.

For the optional matplotlib dashboard and PNG export:

```powershell
pip install -r requirements-dashboard.txt
```

For a headless smoke run:

```powershell
python -m venus_basestation --source simulated --headless --steps 20
```

Explicitly use the Tkinter UI:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source simulated --ui tk --steps 30
```

Use the matplotlib dashboard if you installed the dashboard extras:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source simulated --ui matplotlib --steps 30
```

Replay the example JSONL file and export a state summary:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source jsonl --jsonl-path examples\sample_messages.jsonl --headless --save-state outputs\sample_state.json
```

Export a PNG dashboard snapshot without opening an interactive window:

```powershell
$env:PYTHONPATH="src"
$env:MPLBACKEND="Agg"
python -m venus_basestation --source jsonl --jsonl-path examples\sample_messages.jsonl --headless --save-figure outputs\sample_dashboard.png
```

If `matplotlib` is not available, you can still export a clean SVG snapshot using only the standard library:

```powershell
$env:PYTHONPATH="src"
python -m venus_basestation --source jsonl --jsonl-path examples\sample_messages.jsonl --headless --save-figure outputs\sample_dashboard.svg
```

Generate a fake JSONL stream for testing:

```powershell
$env:PYTHONPATH="src"
python tools\generate_fake_jsonl.py outputs\fake_messages.jsonl --count 60
```

Run the automated tests:

```powershell
pip install -r requirements-dev.txt
python -m pytest
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
  tk_dashboard.py      Desktop UI built with Tkinter
docs/
  message-format.md    Shared data contract for robot-side integration
examples/
  sample_messages.jsonl
tests/
```

## What Already Works

This repository already supports:

- simulated robot messages
- JSON/JSONL replay
- message validation
- in-memory map state
- robot path tracking
- object plotting
- live desktop UI with map, robot status, and recent event feed
- state export to JSON
- dashboard figure export
- SVG snapshot export without extra plotting dependencies
- basic automated tests
- latest per-robot status snapshot export

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

## Next Team-Dependent Steps

The main things still needed from teammates are:

- exact MQTT topics
- final payload format
- coordinate system agreement
- a few sample real messages

## Current Integration Boundary

You can already build and test everything up to this boundary without teammates:

- parser and validation
- fake message generation
- JSONL replay
- map state updates
- Tkinter UI
- state export
- dashboard rendering

When teammate input arrives, the main work left should only be:

- replacing fake/replay input with real MQTT topics
- aligning the final payload fields
- aligning the agreed coordinate system
