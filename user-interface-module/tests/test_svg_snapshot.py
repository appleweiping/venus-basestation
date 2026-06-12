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


def test_svg_snapshot_includes_legend_counts(tmp_path: Path) -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 0}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "rock", "x": 1, "y": 1, "color": "red"}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "cliff", "x": 2, "y": 2}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "rock", "x": 3, "y": 3, "color": "blue"}))

    text = write_svg_snapshot(tmp_path / "legend.svg", state).read_text(encoding="utf-8")

    assert "rock × 2" in text
    assert "cliff × 1" in text


def test_svg_snapshot_is_deterministic_and_supports_light_theme(tmp_path: Path) -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 0, "heading": 45}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "mountain", "x": 4, "y": 2}))

    first = write_svg_snapshot(tmp_path / "a.svg", state).read_text(encoding="utf-8")
    second = write_svg_snapshot(tmp_path / "b.svg", state).read_text(encoding="utf-8")
    light = write_svg_snapshot(tmp_path / "light.svg", state, theme="light").read_text(encoding="utf-8")

    assert first == second
    assert light != first
    assert "Venus Basestation Snapshot" in light
