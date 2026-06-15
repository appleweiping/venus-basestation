"""Zero-dependency .env loading and data-source resolution.

The teammate's pain point: running the program with no arguments shows
simulated example data, and connecting to the robot means knowing to pass
``--source mqtt`` *and* exporting credentials. To remove that friction:

- ``load_dotenv()`` reads a local ``.env`` (copied from ``.env.example``) so
  credentials live in one file instead of shell exports.
- ``resolve_source()`` picks MQTT automatically when credentials are present,
  and otherwise falls back to simulated data with a clear hint about how to
  connect.

Both are pure stdlib and fully testable.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(search_dirs: list[Path] | None = None, *, environ: dict | None = None) -> list[str]:
    """Load ``KEY=VALUE`` lines from a local ``.env`` into the environment.

    Existing environment values are never overridden (an explicit shell export
    or CI variable wins). Lines that are blank, comments (``#``), or lack ``=``
    are skipped; surrounding quotes on the value are stripped. Returns the list
    of ``.env`` paths actually read.
    """
    env = os.environ if environ is None else environ
    if search_dirs is None:
        module_root = Path(__file__).resolve().parent.parent.parent
        search_dirs = [Path.cwd(), module_root]

    loaded: list[str] = []
    seen: set[Path] = set()
    for directory in search_dirs:
        path = Path(directory) / ".env"
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in env:
                env[key] = value
        loaded.append(str(path))
    return loaded


def resolve_source(explicit_source: str | None, *, has_credentials: bool) -> tuple[str, str | None]:
    """Resolve the data source and an optional one-line hint for the user.

    An explicit ``--source`` always wins. Otherwise, MQTT is chosen when a
    board username is configured (the user clearly wants the robot), and
    simulated data is the safe fallback for a quick look.
    """
    if explicit_source is not None:
        return explicit_source, None
    if has_credentials:
        return "mqtt", (
            "No --source given; MQTT credentials detected -> connecting to the robot "
            "(--source mqtt). Pass --source simulated for demo data instead."
        )
    return "simulated", (
        "No --source given; showing simulated demo data. To connect to the robot, set "
        "VENUS_MQTT_USERNAME and VENUS_MQTT_PASSWORD (copy .env.example to .env) and re-run."
    )


def has_mqtt_credentials(environ: dict | None = None) -> bool:
    env = os.environ if environ is None else environ
    return bool(env.get("VENUS_MQTT_USERNAME", "").strip())
