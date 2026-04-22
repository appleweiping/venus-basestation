from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .map_state import MapState


def iter_jsonl_messages(path: str | Path) -> list[str]:
    file_path = Path(path)
    return [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_state_summary(path: str | Path, state: MapState) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return file_path


def write_jsonl(path: str | Path, messages: list[dict[str, Any] | str]) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for message in messages:
        if isinstance(message, str):
            lines.append(message)
        else:
            lines.append(json.dumps(message, ensure_ascii=False))
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path

