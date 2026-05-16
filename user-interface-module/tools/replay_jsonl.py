from __future__ import annotations

import argparse
from pathlib import Path

from venus_basestation.io_utils import iter_jsonl_messages
from venus_basestation.io_utils import write_state_summary
from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--save-state")
    args = parser.parse_args()

    state = MapState()
    for line in iter_jsonl_messages(args.path):
        state.apply(parse_observation(line))

    print(f"messages: {state.messages_seen}")
    print(f"robots: {len(state.robots)}")
    print(f"objects: {len(state.objects)}")
    if args.save_state:
        path = write_state_summary(args.save_state, state)
        print(f"state written to: {path}")


if __name__ == "__main__":
    main()
