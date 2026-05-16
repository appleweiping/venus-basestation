# Venus Team 28 Project Archive

This repository now presents the Venus Team 28 project as a complete project archive, not only as Vipin's standalone base-station/UI module.

## What This Repository Contains

- `team-project/` - snapshot of the Team 28 GitLab `main` branch, including the shared PYNQ/libpynq course project and team setup guide.
- `team-project/module-branches/` - source-focused snapshots of the GitLab module branches: communication, algorithm/navigation, embedded software, and mapping.
- `user-interface-module/` - Vipin's computer software and UI module: Python base-station software, MQTT/replay input, map state, Tkinter dashboard, SVG/PNG export, docs, examples, and tests.

The original GitLab project remains the team source of truth for coursework collaboration. This GitHub repository is a public portfolio/archive mirror that makes the full project context visible together with Vipin's own UI contribution.

## Quick Start: User Interface Module

```powershell
cd user-interface-module
python -m venv .venv
if (Test-Path .\.venv\Scripts\Activate.ps1) { .\.venv\Scripts\Activate.ps1 }
pip install -r requirements.txt
$env:PYTHONPATH="src"
python -m venus_basestation --source simulated
```

Headless smoke run:

```powershell
cd user-interface-module
$env:PYTHONPATH="src"
python -m venus_basestation --source simulated --headless --steps 20
```

Run tests:

```powershell
cd user-interface-module
pip install -r requirements-dev.txt
python -m pytest
```

## Team Project Snapshot

See `team-project/README.md` for the original Team 28 software development guide and PYNQ workflow.

See `team-project/PROVENANCE.md` for copy provenance and public-safety rules. See `team-project/module-branches/README.md` for branch snapshot notes.

## Repository Layout

```text
team-project/
  README.md
  .vscode/
  libpynq-5EID0-2023-v0.3.0/
  module-branches/
user-interface-module/
  README.md
  src/venus_basestation/
  docs/
  examples/
  tests/
  tools/
```

## Safety

Do not commit credentials, private keys, real MQTT passwords, personal `sftp.json`, local virtual environments, or generated runtime output.

The UI module uses environment variables for runtime MQTT credentials:

- `VENUS_MQTT_HOST`
- `VENUS_MQTT_USERNAME`
- `VENUS_MQTT_PASSWORD`
- `VENUS_MQTT_TOPICS`

## Provenance

- GitHub archive: `https://github.com/appleweiping/venus-basestation`
- Team GitLab source: `git@gitlab.tue.nl:d.gyftakis/venus-team-28.git`
- Local Team GitLab source at migration: `D:/Undergraduate_project_netherlands/venus-team-28-gitlab`
- Local standalone UI source before migration: `D:/Undergraduate_project_netherlands/Venus basestation`

## Note

This archive intentionally keeps the full team context and the UI module separate. That makes it clear that Vipin owned the computer software/UI role while the public repository still shows how the module fits into the complete Venus project.
