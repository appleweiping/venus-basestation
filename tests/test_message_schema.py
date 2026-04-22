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


def test_rejects_unknown_event_type() -> None:
    try:
        parse_observation({"robot_id": "robot_1", "event_type": "unknown"})
    except ValueError as exc:
        assert "unsupported event_type" in str(exc)
    else:
        raise AssertionError("expected ValueError")

