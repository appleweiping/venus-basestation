from __future__ import annotations

import argparse

from venus_basestation.fake_messages import simulated_message_dicts
from venus_basestation.io_utils import write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--count", type=int, default=40)
    args = parser.parse_args()

    path = write_jsonl(args.output, simulated_message_dicts(args.count))
    print(f"wrote fake messages to {path}")


if __name__ == "__main__":
    main()

