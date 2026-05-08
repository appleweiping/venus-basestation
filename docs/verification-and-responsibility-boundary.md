# Verification And Responsibility Boundary

This document records what the base-station/UI module can currently verify by itself, and what must be confirmed with the rest of Team 28 before the integrated robot demo.

It is meant to prevent unclear ownership: the base-station module should be responsible for parsing supported messages, maintaining the map state, visualizing data, and exporting summaries. It should not be treated as responsible for unconfirmed MQTT topics, robot-side payload changes, sensor accuracy, navigation behavior, or broker availability.

## Last Local Verification

Checked locally on 2026-05-08 from the GitHub repository:

```text
D:/Undergraduate_project_netherlands/Venus basestation
```

Repository state at the start of verification:

```text
branch: main
remote: https://github.com/appleweiping/venus-basestation.git
head: 1cd4cd6 Support Team 28 communication payloads
```

## Commands That Passed

Run these from the repository root with the project virtual environment.

```powershell
$env:PYTHONPATH="src"
.\.venv\bin\python.exe -m pytest -q
```

Observed result:

```text
17 passed
```

```powershell
$env:PYTHONPATH="src"
.\.venv\bin\python.exe -m venus_basestation --source simulated --headless --steps 20 --save-state outputs\codex_verify_simulated_state.json
```

Observed result:

```text
processed 31 messages
wrote state summary to outputs\codex_verify_simulated_state.json
```

```powershell
$env:PYTHONPATH="src"
.\.venv\bin\python.exe -m venus_basestation --source jsonl --jsonl-path examples\sample_messages.jsonl --headless --save-state outputs\codex_verify_sample_state.json
```

Observed result:

```text
processed 5 messages
wrote state summary to outputs\codex_verify_sample_state.json
```

```powershell
$env:PYTHONPATH="src"
.\.venv\bin\python.exe -m venus_basestation --source jsonl --jsonl-path examples\team28_communication_messages.jsonl --headless --save-state outputs\codex_verify_team28_state.json
```

Observed result:

```text
processed 4 messages
wrote state summary to outputs\codex_verify_team28_state.json
```

```powershell
$env:PYTHONPATH="src"
.\.venv\bin\python.exe -m venus_basestation --source jsonl --jsonl-path examples\sample_messages.jsonl --headless --save-figure outputs\codex_verify_sample_dashboard.svg
```

Observed result:

```text
processed 5 messages
wrote svg snapshot to outputs\codex_verify_sample_dashboard.svg
```

## What Is Verified

- The automated unit test suite passes locally.
- Simulated message processing works in headless mode.
- JSONL replay works with the internal message format.
- JSONL replay works with the current Team 28 communication-module sample payloads:
  - `position_update`
  - `rock_detected`
- Compatibility aliases normalize Team 28-style payloads into the internal event types.
- Map state export to JSON works.
- SVG dashboard snapshot export works without installing `matplotlib`.
- The repository does not require committing local credentials; MQTT settings are read from environment variables.

## What Is Not Verified Yet

These items depend on other modules or deployment conditions and must be confirmed before claiming full team integration:

- Exact final MQTT topic names.
- Exact final robot-side JSON payload fields.
- Robot IDs used by the team.
- Coordinate origin, units, and orientation.
- Whether the robot publishes duplicate or repeated observations.
- Broker credentials and broker availability during demo time.
- Live MQTT end-to-end flow with real robot messages.
- The current communication-module topic and payload have been read from GitLab, but a live broker run with a real robot is still required.
- Sensor correctness, navigation correctness, or embedded-control behavior.
- PNG export, unless `matplotlib` is installed with `requirements-dashboard.txt`.

## Responsibility Boundary

The base-station/UI module is responsible for:

- accepting documented payloads;
- rejecting invalid payloads with parser errors;
- updating the in-memory map state from supported event types;
- showing robot paths and detected map objects;
- exporting state summaries and snapshots;
- documenting required external inputs.

The base-station/UI module is not responsible for:

- a teammate changing the payload format without updating the shared contract;
- missing or wrong MQTT topics;
- unavailable broker/network;
- wrong robot coordinates or units supplied by another module;
- physical robot behavior, navigation, or sensor quality;
- secrets or credentials not provided through environment variables.

## Before Pushing Or Merging To GitLab

Use this checklist before sending the module to the team GitLab repository:

- Re-run `python -m pytest -q`.
- Re-run the Team 28 JSONL replay command.
- Confirm the GitLab branch contains this module in its own scoped folder or branch.
- Ask the communication-module owner to provide one fresh real or near-real sample message.
- Compare the fresh sample message against `docs/message-format.md`.
- Update `examples/team28_communication_messages.jsonl` if the team changes the payload.
- Do not commit `.env`, broker passwords, screenshots with credentials, or local output files.

## GitHub And GitLab Notes

- GitHub is currently the verified standalone source for this module.
- GitLab should be treated as verified only after the same commands pass from the GitLab branch or clone.
- If GitLab has a different folder layout, run tests from the module folder and keep the base-station files separated from other team modules.
