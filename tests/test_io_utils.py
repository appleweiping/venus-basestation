from pathlib import Path

from venus_basestation.io_utils import iter_jsonl_messages
from venus_basestation.io_utils import write_jsonl
from venus_basestation.io_utils import write_state_summary
from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation


def test_write_jsonl_and_read_back(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path / "messages.jsonl",
        [
            {"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 0},
            {"robot_id": "robot_1", "event_type": "status", "battery": 95},
        ],
    )

    messages = iter_jsonl_messages(path)

    assert len(messages) == 2
    assert "\"event_type\": \"robot_position\"" in messages[0]


def test_write_state_summary_includes_statuses(tmp_path: Path) -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "battery": 95}))

    path = write_state_summary(tmp_path / "state.json", state)
    text = path.read_text(encoding="utf-8")

    assert "\"statuses\"" in text
    assert "\"battery\": 95" in text


def test_iter_jsonl_messages_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "messages.jsonl"
    path.write_text("{\"robot_id\":\"robot_1\",\"event_type\":\"status\"}\n\n", encoding="utf-8")

    messages = iter_jsonl_messages(path)

    assert messages == ['{"robot_id":"robot_1","event_type":"status"}']
