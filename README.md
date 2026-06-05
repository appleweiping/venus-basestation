<p align="center">
  <strong>Venus Basestation</strong>
</p>

<p align="center">
  Base-station software and visualization dashboard for a multi-robot planetary exploration system.
  Receives robot telemetry over MQTT, maintains a live world model, and renders explored terrain in real time.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/platform-PYNQ%20%7C%20desktop-lightgrey?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
</p>

---

## Overview

This repository contains two things:

- **`user-interface-module/`** — the computer software and UI module: Python base-station, MQTT subscriber, JSONL replay, map state engine, Tkinter desktop dashboard, SVG/PNG export, and automated tests.
- **`team-project/`** — a snapshot of the shared team codebase (PYNQ embedded software, communication module, algorithm/navigation module, mapping module) mirrored from the team GitLab for portfolio context.

The team GitLab remains the authoritative source for coursework collaboration. This repository is a public portfolio mirror.

---

## Architecture

```
robot hardware (PYNQ)
  └─ embedded software module
       └─ communication module  ──MQTT──▶  venus_basestation
                                              ├─ message_schema   (parse + validate)
                                              ├─ map_state        (world model)
                                              ├─ tk_dashboard     (live Tkinter UI)
                                              ├─ dashboard        (matplotlib export)
                                              └─ svg_snapshot     (stdlib SVG export)
```

**Input sources** (selectable at runtime):

| Source | Flag | Description |
|--------|------|-------------|
| Simulated | `--source simulated` | Built-in fake message generator |
| JSONL replay | `--source jsonl` | Replay a recorded `.jsonl` file |
| Live MQTT | `--source mqtt` | Subscribe to broker topics |

---

## Quick Start

```bash
cd user-interface-module
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
PYTHONPATH=src python -m venus_basestation --source simulated
```

Headless smoke run (no window):

```bash
PYTHONPATH=src python -m venus_basestation --source simulated --headless --steps 20
```

Replay a recorded session:

```bash
PYTHONPATH=src python -m venus_basestation \
  --source jsonl \
  --jsonl-path examples/sample_messages.jsonl \
  --headless \
  --save-state outputs/state.json
```

Connect to a live MQTT broker:

```bash
export VENUS_MQTT_HOST=mqtt.ics.ele.tue.nl
export VENUS_MQTT_USERNAME=robot_15_1
export VENUS_MQTT_PASSWORD=<password>
export VENUS_MQTT_TOPICS=/pynqbridge/15/send
PYTHONPATH=src python -m venus_basestation --source mqtt --ui tk
```

The course broker uses the numeric communication-board topic, e.g.
`/pynqbridge/15/send` for `robot_15_1` and `/pynqbridge/43/send` for
`robot_43_1`. If `VENUS_MQTT_TOPICS` is not set, the base station derives this
topic from `VENUS_MQTT_USERNAME`.

Verify broker connectivity without opening the UI:

```bash
PYTHONPATH=src python -m venus_basestation \
  --source mqtt --headless --mqtt-check --mqtt-timeout 15 --mqtt-min-messages 0 \
  --save-state outputs/mqtt_check.json
```

Use `--mqtt-min-messages 0` to verify broker login and topic subscription even
when the robot is not publishing. Use the default minimum of `1` when you want
to verify live robot payloads too.

Export a PNG dashboard snapshot:

```bash
pip install -r requirements-dashboard.txt
MPLBACKEND=Agg PYTHONPATH=src python -m venus_basestation \
  --source jsonl \
  --jsonl-path examples/sample_messages.jsonl \
  --headless \
  --save-figure outputs/dashboard.png
```

Export an SVG snapshot (no extra dependencies):

```bash
PYTHONPATH=src python -m venus_basestation \
  --source jsonl \
  --jsonl-path examples/sample_messages.jsonl \
  --headless \
  --save-figure outputs/dashboard.svg
```

---

## CLI Reference

```
python -m venus_basestation [options]

--source {simulated,mqtt,jsonl}   Input source (default: simulated)
--headless                        Run without opening a window
--ui {tk,matplotlib}              Dashboard backend (default: tk)
--steps N                         Simulated steps to run (default: 40)
--delay SECS                      Delay between simulated steps (default: 0.05)
--jsonl-path PATH                 JSONL file for --source jsonl
--save-figure PATH                Write final figure to PNG or SVG
--save-state PATH                 Write final map state to JSON
--mqtt-check                      Verify broker config and exit
--mqtt-timeout SECS               Timeout for --mqtt-check (default: 10)
--mqtt-min-messages N             Minimum messages for --mqtt-check (default: 1)
```

---

## Message Format

The base-station accepts JSON messages with the following canonical fields:

```json
{
  "robot_id": "robot_43_1",
  "event_type": "rock",
  "x": 1.23,
  "y": 4.56,
  "color": "red",
  "size": "large",
  "distance_mm": 320.0,
  "confidence": 0.91
}
```

**Supported event types:** `robot_position`, `rock`, `cliff`, `boundary`, `mountain`, `obstacle`, `status`, `color_sensor`, `distance_sensor`

The parser normalizes common field name variants from the communication module (e.g. `type=position_update` → `event_type=robot_position`, `object_distance_mm` → `distance_mm`). See [`docs/message-format.md`](user-interface-module/docs/message-format.md) for the full contract.

The current Team 28 UART test sends robot-to-ESP32 messages as `4-byte payload length + JSON payload bytes`. MQTT normally forwards only the JSON body, but the parser also accepts MQTT payloads where that 4-byte UART length prefix is still present.

---

## MQTT Environment Variables

| Variable | Description |
|----------|-------------|
| `VENUS_MQTT_HOST` | Broker hostname |
| `VENUS_MQTT_PORT` | Broker port (default: 1883) |
| `VENUS_MQTT_USERNAME` | Username |
| `VENUS_MQTT_PASSWORD` | Password — never commit this |
| `VENUS_MQTT_TOPICS` | Comma-separated topic list |

---

## Project Layout

```
user-interface-module/
  src/venus_basestation/
    __main__.py          CLI entry point and run loop
    message_schema.py    Message parsing, validation, field normalization
    map_state.py         In-memory world model (robots, objects, events)
    tk_dashboard.py      Live Tkinter desktop UI
    dashboard.py         Matplotlib visualization and PNG export
    svg_snapshot.py      SVG export (stdlib only, no matplotlib)
    mqtt_client.py       MQTT subscriber wrapper
    fake_messages.py     Simulated robot observations
    io_utils.py          JSONL reader and state writer
  docs/
    message-format.md
    team28-current-interface.md
    verification-and-responsibility-boundary.md
  examples/
  tests/
  tools/

team-project/
  libpynq-5EID0-2023-v0.3.0/    Shared PYNQ course library
  module-branches/               Snapshots of all team modules
  README.md                      Original team development guide
  PROVENANCE.md
```

---

## Running Tests

```bash
cd user-interface-module
pip install -r requirements-dev.txt
python -m pytest -v
```

---

## Development

Generate a fake JSONL stream for offline testing:

```bash
PYTHONPATH=src python tools/generate_fake_jsonl.py outputs/fake.jsonl --count 60
```

---

## Safety

- Do not commit MQTT credentials, `sftp.json`, `.venv/`, or generated output files.
- Use environment variables for all runtime secrets.
- The `--mqtt-check` flag prints sanitized config and never prints the password value.

---

## License

Original code in `user-interface-module/` is MIT licensed. The `team-project/` snapshot retains the original team licensing. See [`LICENSE`](LICENSE) and [`team-project/PROVENANCE.md`](team-project/PROVENANCE.md).
