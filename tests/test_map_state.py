from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation


def test_tracks_robot_positions() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 1}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 1, "y": 1}))

    assert state.messages_seen == 2
    assert state.robots["robot_1"].positions == [(0.0, 1.0), (1.0, 1.0)]


def test_stores_map_objects() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "cliff", "x": 2, "y": 3}))

    assert len(state.objects) == 1
    assert state.objects[0].event_type == "cliff"

