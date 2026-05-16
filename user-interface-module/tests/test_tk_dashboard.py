from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation
from venus_basestation.tk_dashboard import projection_for_state


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
