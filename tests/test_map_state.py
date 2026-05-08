from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation


def test_tracks_robot_positions() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 0, "y": 1}))
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "robot_position", "x": 1, "y": 1, "heading": 90}))

    assert state.messages_seen == 2
    assert state.robots["robot_1"].positions == [(0.0, 1.0), (1.0, 1.0)]
    assert state.robots["robot_1"].heading == 90.0


def test_stores_map_objects() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "rock", "x": 2, "y": 3, "distance_mm": 120}))

    assert len(state.objects) == 1
    assert state.objects[0].event_type == "rock"
    assert state.objects[0].distance_mm == 120.0


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
    assert result["robots"]["robot_1"]["heading"] is None


def test_state_to_dict_preserves_team28_coordinate_metadata() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "A", "type": "position_update", "x": 3, "y": 5, "heading": 90}))
    state.apply(
        parse_observation(
            {
                "robot_id": "A",
                "type": "rock_detected",
                "x": 3,
                "y": 5,
                "distance_mm": 120,
                "color": "red",
            }
        )
    )

    result = state.to_dict()

    assert result["robots"]["A"]["positions"] == [(3.0, 5.0)]
    assert result["robots"]["A"]["heading"] == 90.0
    assert result["objects"][0]["distance_mm"] == 120.0


def test_tracks_latest_status_per_robot() -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "battery": 78, "mode": "idle"}))

    assert state.statuses["robot_1"]["battery"] == 78
    assert state.to_dict()["statuses"]["robot_1"]["mode"] == "idle"


def test_recent_events_are_capped() -> None:
    state = MapState()
    for index in range(30):
        state.apply(parse_observation({"robot_id": "robot_1", "event_type": "status", "battery": index}))

    assert len(state.recent_events) == 25
    assert state.recent_events[0]["battery"] == 5
