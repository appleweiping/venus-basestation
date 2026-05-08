from venus_basestation.message_schema import parse_observation


def test_parse_rock_observation() -> None:
    obs = parse_observation(
        {
            "robot_id": "robot_1",
            "event_type": "rock",
            "x": 1.0,
            "y": 2.0,
            "color": "red",
            "size": "small",
            "temperature": 24.5,
        }
    )

    assert obs.robot_id == "robot_1"
    assert obs.event_type == "rock"
    assert obs.x == 1.0
    assert obs.temperature == 24.5


def test_accepts_communication_position_update_payload() -> None:
    obs = parse_observation(
        {
            "robot_id": "A",
            "type": "position_update",
            "x": 3,
            "y": 5,
            "heading": 90,
        }
    )

    assert obs.robot_id == "A"
    assert obs.event_type == "robot_position"
    assert obs.x == 3.0
    assert obs.heading == 90.0
    assert obs.raw["type"] == "position_update"


def test_accepts_communication_rock_detected_payload() -> None:
    obs = parse_observation(
        {
            "robot_id": "A",
            "type": "rock_detected",
            "x": 3,
            "y": 5,
            "distance_mm": 120,
            "color": "red",
            "size": "small",
            "temperature": 28.5,
        }
    )

    assert obs.event_type == "rock"
    assert obs.color == "red"
    assert obs.distance_mm == 120.0
    assert obs.temperature == 28.5
    assert obs.raw["distance_mm"] == 120


def test_accepts_heading_deg_alias() -> None:
    obs = parse_observation(
        {
            "robot_id": "A",
            "event_type": "robot_position",
            "x": 3,
            "y": 5,
            "heading_deg": 180,
        }
    )

    assert obs.heading == 180.0
    assert obs.raw["heading"] == 180


def test_rejects_unknown_event_type() -> None:
    try:
        parse_observation({"robot_id": "robot_1", "event_type": "unknown"})
    except ValueError as exc:
        assert "unsupported event_type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_requires_coordinates_for_rock() -> None:
    try:
        parse_observation({"robot_id": "robot_1", "event_type": "rock"})
    except ValueError as exc:
        assert "x and y are required" in str(exc)
    else:
        raise AssertionError("expected ValueError")
