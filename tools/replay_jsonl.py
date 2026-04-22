from __future__ import annotations

import argparse
from pathlib import Path

from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    state = MapState()
    for line in args.path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        state.apply(parse_observation(line))

    print(f"messages: {state.messages_seen}")
    print(f"robots: {len(state.robots)}")
    print(f"objects: {len(state.objects)}")


if __name__ == "__main__":
    main()

