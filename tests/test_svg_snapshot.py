from pathlib import Path

from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation
from venus_basestation.svg_snapshot import write_svg_snapshot


def test_write_svg_snapshot_creates_svg_file(tmp_path: Path) -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 0}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "rock", "x": 1, "y": 1, "color": "red"}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "mode": "exploring"}))

    path = write_svg_snapshot(tmp_path / "snapshot.svg", state)
    text = path.read_text(encoding="utf-8")

    assert "<svg" in text
    assert "Venus Basestation Snapshot" in text
    assert "latest status" in text
