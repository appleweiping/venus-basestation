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


def test_deduplicates_static_objects() -> None:
    state = MapState()
    payload = {"robot_id": "robot_1", "event_type": "cliff", "x": 2, "y": 3}
    state.apply(parse_observation(payload))
    state.apply(parse_observation(payload))

    assert len(state.objects) == 1


def test_state_to_dict_contains_expected_sections() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 0}))
    result = state.to_dict()

    assert "robots" in result
    assert "objects" in result
    assert "statuses" in result
    assert result["messages_seen"] == 1


def test_tracks_latest_status_per_robot() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "battery": 78, "mode": "idle"}))

    assert state.statuses["robot_1"]["battery"] == 78
    assert state.to_dict()["statuses"]["robot_1"]["mode"] == "idle"
