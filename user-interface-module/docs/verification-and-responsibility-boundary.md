# Verification And Responsibility Boundary

This document records what the base-station/UI module can currently verify by itself, and what must be confirmed with the rest of Team 28 before the integrated robot demo.

It is meant to prevent unclear ownership: the base-station module should be responsible for parsing supported messages, maintaining the map state, visualizing data, and exporting summaries. It should not be treated as responsible for unconfirmed MQTT topics, robot-side payload changes, sensor accuracy, navigation behavior, or broker availability.

## Topic Mismatch Fix (2026-06-12, v0.3.1)

**Root cause of the teammate's "interface doesn't work" report.** The base
station derived the telemetry topic as `/pynqbridge/<board-number>/send`
(e.g. `/pynqbridge/43/send`), but Team 28's own communication-module code
(`hybrid_publisher_course.py`, `subscriber_course.py`, in both the
communication-module and mapping-new branches) publishes to
`/pynqbridge/robot_43_1/send` — the **full MQTT username**, not the bare
number. MQTT topic matching is exact, so the dashboard subscribed to a topic
the robot never published to, received zero messages, and showed an empty
map.

Fix: telemetry and command topics are now derived from the full username
(`/pynqbridge/<username>/send` and `/pynqbridge/<username>/recv`). The
gitignored `config.local.*.ps1` helpers no longer pin the old numeric topic,
so the corrected derivation applies.

Verified locally on 2026-06-12:

```text
python -m pytest -q                                  -> 79 passed
--source mqtt --headless --mqtt-check (robot_43_1)   -> connected, reason_code=Success,
                                                        /pynqbridge/robot_43_1/send Granted QoS,
                                                        command_topic=/pynqbridge/robot_43_1/recv derived
telemetry roundtrip on the real course broker        -> published Team 28's exact wire format
  (tools/telemetry_roundtrip_check.py)                  ({"robot_id":"A","type":"position_update",...}
                                                        + rock_detected) to /pynqbridge/robot_43_1/send;
                                                        received 2, robot 'A' tracked, rock recorded
tools/tk_live_check.py --inject                      -> dashboard renders Team 28's exact format
                                                        (robot track + heading, 2 rocks, mission log)
```

The recv (command) topic is inferred by symmetry with the send topic; the
2026-06-12 spec text said `/pynqbridge/43/recv`, which conflicts with the
team's full-username send topic. The full-username form is the default and is
overridable via `VENUS_MQTT_COMMAND_TOPIC` / `--command-topic`; confirm the
exact recv topic with the embedded teammate before the first live command.

### Adversarial review hardenings (same pass)

A whole-module multi-agent review after the topic fix surfaced and led to
these additional fixes (all the UI side now survives realistic bad input):

- **NaN/Infinity rejection** — `json.loads` accepts bare `NaN`/`Infinity`; a
  non-finite coordinate is now rejected at parse time so it cannot poison the
  map bounds or crash the grid/SVG render (`math.log10(inf)`).
- **Live stream survives a bad event** — the MQTT message handler wraps the
  observation dispatch, and the Tk pump reschedules in `finally`, so one
  malformed frame or render glitch can no longer kill the subscriber thread
  or freeze the dashboard.
- **Wrong password is visible** — on a broker CONNACK rejection the client now
  turns the connection pill red and disconnects instead of silently retrying
  forever while the UI sits on STANDBY.
- **No misdirected commands** — a missing/typo'd username derives no topic
  (empty) rather than silently falling back to `robot_43_1`, so a command
  (including E-STOP) can never be sent to the wrong board.
- **Honest command feedback** — a QoS-1 PUBACK only proves the broker accepted
  the publish, so the UI/CLI now say "queued at broker; robot receipt
  unconfirmed" rather than "sent".
- **Malformed-input contract** — `parse_observation` raises `ValueError` (not
  `TypeError`) for any non-object JSON or non-numeric coordinate, and names
  the unknown `type` token in the error.
- **`--ui matplotlib --source mqtt` (non-headless)** is rejected with a clear
  message pointing to `--ui tk`; that path never updated the figure from the
  network loop.

### Robot-side caveats to confirm with the embedded teammate

These are NOT base-station defects; they determine whether live telemetry
appears once the topic is correct:

- The compiled firmware (`mapping-new/.../navigation-module`) emits only
  `position_update` over **UART** (4-byte LE length prefix + JSON), never over
  MQTT. Telemetry reaches the broker only if a UART→MQTT bridge process runs
  on the PYNQ and republishes to `/pynqbridge/robot_43_1/send`. **No such
  bridge exists in the team repo.** If the teammate instead runs the Python
  `hybrid_publisher_course.py` on the PYNQ, telemetry (including rocks) flows
  directly and the map populates. Confirm which process actually publishes.
- With the real firmware, only the robot track appears — the rock/cliff/etc.
  panels stay empty by design, because no C code emits those events (they
  exist only in the Python test publisher).
- The firmware's `communication.c` formats `robot_id` (a `char`) with `%s`,
  which is undefined behavior and would emit a malformed/empty `robot_id`.
  Our parser drops a message with an empty `robot_id`; the fix belongs in the
  firmware (`%c`, or `const char *robot_id = "A";`).

Note: the end-to-end roundtrip used the Python publisher's wire format, which
matches the firmware's intended `position_update` JSON, so the base station is
proven correct for documented payloads regardless of the robot-side caveats.

## Robot Command Uplink Verification (2026-06-12, v0.3.0)

Implemented the Team 28 embedded command interface (received 2026-06-12):
the base station now publishes `start` / `idle` / `stop` commands to the
robot's `/pynqbridge/<board>/recv` topic with QoS 1, from the dashboard
COMMAND UPLINK panel (live MQTT mode) or headless via `--send-command`.

Verified locally on 2026-06-12:

```text
python -m pytest -q                                  -> 71 passed
--source mqtt --headless --mqtt-check (robot_43_1)   -> connected, reason_code=Success,
                                                        /pynqbridge/43/send Granted QoS 0,
                                                        command_topic=/pynqbridge/43/recv derived
tools/command_roundtrip_check.py (HiveMQ test broker)
                                                     -> PASS: idle command published via
                                                        MqttCommandSender and received byte-identical
tools/tk_smoke.py                                    -> COMMAND UPLINK panel renders; loopback
                                                        START dispatch confirmed in status line
```

A multi-agent adversarial review of the change confirmed and led to these
hardenings: both publish paths (dashboard and CLI) now gate success on the
broker's QoS 1 PUBACK rather than local enqueue, so "E-STOP sent" is never
shown for a half-open link; command buttons are disabled while the broker
link is down; `build_command` emits the spec sample bytes verbatim (compact
separators); paho's RuntimeError on a dropped connection is translated to a
clean error instead of a traceback; and `.env.example` no longer pins
`VENUS_MQTT_COMMAND_TOPIC`, so the command topic is derived from the
username — preventing a partial credentials edit from sending an emergency
stop to another team's board.

No command was published to the real robot command topic during
verification: a live `stop` would kill a running robot. The end-to-end
publish path was proven on the public test broker instead; the first
command to the real robot should happen with the team present.

## Mission Control Upgrade Verification (2026-06-12, v0.2.0)

The 0.2.0 upgrade replaced the basic Tk window with the mission-control
dashboard (dark/light themes, zoom/pan/fit, robot status cards, detection
chips, color-coded mission log, live KPI header) and moved live MQTT intake
onto a thread-safe queue: the paho network loop now runs on a daemon thread
and only enqueues events, and the Tk thread drains the queue at ~30 fps.
Tkinter widgets are no longer touched from MQTT callback threads.

Verified locally on 2026-06-12 with the project virtual environment:

```text
python -m pytest -q                                  -> 50 passed
--source simulated --headless --steps 40             -> processed 56 messages, state + SVG written
--source jsonl examples/team28_communication_messages.jsonl
                                                     -> processed 4 messages (Team 28 payloads still parse)
--source jsonl examples/demo_mission.jsonl --headless
                                                     -> processed 108 messages, docs/assets/mission-dashboard.svg
PYTHONPATH=src python tools/tk_smoke.py              -> windowed run, both update paths
                                                        (synchronous draw + threaded submit/start_pump),
                                                        screenshot captured, window auto-closed cleanly
```

The CLI surface is backward compatible; `--theme {dark,light}` is the only
new flag. The message contract, MQTT defaults, and mqtt-check behavior are
unchanged.

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
36 passed
```

Additional MQTT board-topic checks on 2026-06-05:

```powershell
$env:PYTHONPATH="src"
$env:VENUS_MQTT_HOST="mqtt.ics.ele.tue.nl"
$env:VENUS_MQTT_USERNAME="robot_15_1"
$env:VENUS_MQTT_PASSWORD="<matching password>"
Remove-Item Env:VENUS_MQTT_TOPICS -ErrorAction SilentlyContinue
Remove-Item Env:VENUS_MQTT_TOPIC -ErrorAction SilentlyContinue
.\.venv\bin\python.exe -m venus_basestation --source mqtt --headless --mqtt-check --mqtt-timeout 3 --mqtt-min-messages 0
```

Observed result:

```text
MQTT host=mqtt.ics.ele.tue.nl port=1883 topics=[/pynqbridge/15/send] username=robot_15_1 password=set
connected to MQTT broker mqtt.ics.ele.tue.nl:1883 with reason_code=Success
subscribing to /pynqbridge/15/send result=0 mid=1
subscription to /pynqbridge/15/send acknowledged: Granted QoS 0
processed 0 messages
```

The same check with `VENUS_MQTT_USERNAME="robot_43_1"` derived
`/pynqbridge/43/send` and received `Granted QoS 0`.

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
- Team 28 coordinate metadata is preserved:
  - position `heading` is parsed, stored, displayed, and exported;
  - object `distance_mm` is parsed, stored, displayed, and exported.
- MQTT runtime diagnostics print sanitized broker/topic settings and never print the password value.
- A short `--mqtt-check` mode can connect, subscribe, wait for live traffic, and save any received state for demo-prep checks.
- MQTT course topics are derived from the full username, such as `robot_15_1` -> `/pynqbridge/robot_15_1/send` (matching Team 28's communication-module publisher).
- MQTT subscription acknowledgements are logged, so broker ACL rejection is visible separately from zero live messages.
- MQTT broker/network connection failures are reported as concise setup errors instead of Python tracebacks.
- Likely small field-name variations are tolerated, including `message_type`, `event`, `robot`, `id`, `heading_deg`, and `object_distance_mm`.
- Design-report terminology is tolerated where practical: `border`/`edge` normalize to `boundary`, `block`/`sample` normalize to `rock`, and `obstacle` is accepted as a displayed map object.
- Current live `*_found` event names are tolerated, including `block_found`, `border_found`, `mountain_found`, and `cliff_found`.
- Map state export to JSON works.
- SVG dashboard snapshot export works without installing `matplotlib`.
- The repository does not require committing local credentials; MQTT settings are read from environment variables.

## What Is Not Verified Yet

These items depend on other modules or deployment conditions and must be confirmed before claiming full team integration:

- Whether the teammate-provided numeric MQTT topic names remain final through the demo.
- Exact final robot-side JSON payload fields.
- Robot IDs used by the team.
- Final coordinate origin, units, and orientation. Current code reading suggests centimeter coordinates from robot startup origin, but this remains a team contract issue.
- Final physical heading convention. The UI preserves raw heading degrees but does not infer rotation direction from incomplete navigation code.
- Whether the robot publishes duplicate or repeated observations.
- Broker credentials and broker availability during demo time.
- Live MQTT end-to-end flow with real robot messages.
- The current communication-module payload has been read from GitLab, and teammate-provided MQTT topics have been checked against broker subscription ACKs, but a live broker run with real robot messages is still required.
- Sensor correctness, navigation correctness, or embedded-control behavior.
- PNG export, unless `matplotlib` is installed with `requirements-dashboard.txt`.

## Responsibility Boundary

The base-station/UI module is responsible for:

- accepting documented payloads;
- preserving documented Team 28 fields such as `heading` and `distance_mm`;
- rejecting invalid payloads with parser errors;
- updating the in-memory map state from supported event types;
- showing robot paths and detected map objects;
- exporting state summaries and snapshots;
- documenting required external inputs.

The base-station/UI module is not responsible for:

- a teammate changing the payload format without updating the shared contract;
- missing or wrong MQTT topics after the UI has printed the subscribed topic and zero-message check result;
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
