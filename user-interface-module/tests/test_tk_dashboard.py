from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation
from venus_basestation.tk_dashboard import (
    MessageRateTracker,
    battery_value,
    nice_grid_step,
    projection_for_state,
    robot_cards,
    split_trail,
)


def test_recent_event_lines_include_status_and_rock() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "mode": "exploring", "battery": 88}))
    state.apply(
        parse_observation(
            {
                "robot_id": "robot_1",
                "event_type": "rock",
                "x": 1,
                "y": 2,
                "color": "red",
                "size": "small",
                "temperature": 24.5,
            }
        )
    )

    lines = state.recent_event_lines(limit=5)

    assert any("battery=88" in line for line in lines)
    assert any("rock red small 24.5C" in line for line in lines)


def test_projection_for_state_expands_bounds() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 0}))
    state.apply(parse_observation({"robot_id": "robot_2", "event_type": "robot_position", "x": 10, "y": 5}))

    projection = projection_for_state(state, width=700, height=500)

    assert projection.min_x < 0
    assert projection.max_x > 10
    assert projection.min_y < 0
    assert projection.max_y > 5


def test_message_rate_tracker_uses_sliding_window() -> None:
    tracker = MessageRateTracker(window=5.0)
    tracker.record(10, now=100.0)

    assert tracker.rate(now=100.0) == 2.0
    assert tracker.rate(now=106.0) == 0.0


def test_battery_value_parses_common_payloads() -> None:
    assert battery_value(88) == 88.0
    assert battery_value("88") == 88.0
    assert battery_value("88%") == 88.0
    assert battery_value(150) == 100.0
    assert battery_value(-5) == 0.0
    assert battery_value("n/a") is None
    assert battery_value(None) is None
    assert battery_value(True) is None


def test_nice_grid_step_picks_125_series() -> None:
    assert nice_grid_step(10) == 2
    assert nice_grid_step(100) == 20
    assert nice_grid_step(0.5) == 0.1
    assert nice_grid_step(0) == 1.0


def test_split_trail_chunks_share_joints() -> None:
    points = [(float(i), float(i)) for i in range(10)]

    chunks = split_trail(points, 3)

    assert len(chunks) >= 2
    for first, second in zip(chunks, chunks[1:]):
        assert first[-1] == second[0]
    covered = [chunks[0][0]]
    for chunk in chunks:
        covered.extend(chunk[1:])
    assert covered == points


def test_split_trail_handles_short_input() -> None:
    assert split_trail([], 3) == []
    assert split_trail([(0.0, 0.0)], 3) == []


def test_robot_cards_collects_status_track_and_sensors() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 2, "y": 3, "heading": 90}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "mode": "exploring", "battery": 72}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "color_sensor", "color": "red"}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "distance_sensor", "distance_mm": 320}))

    cards = robot_cards(state)

    assert len(cards) == 1
    card = cards[0]
    assert card.robot_id == "robot_1"
    assert card.mode == "exploring"
    assert card.battery == 72.0
    assert card.position == (2.0, 3.0)
    assert card.heading == 90.0
    assert card.color_reading == "red"
    assert card.distance_reading == "320 mm"
