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


def test_accepts_uart_length_prefixed_bytes_payload() -> None:
    payload = b'{"robot_id":"A","type":"position_update","x":3,"y":5}'
    framed_payload = len(payload).to_bytes(4, "little") + payload

    obs = parse_observation(framed_payload)

    assert obs.robot_id == "A"
    assert obs.event_type == "robot_position"
    assert obs.x == 3.0
    assert obs.y == 5.0


def test_accepts_uart_length_prefixed_text_payload() -> None:
    payload = '{"robot_id":"A","type":"rock_detected","x":3,"y":5,"distance_mm":120}'
    framed_payload = len(payload.encode("utf-8")).to_bytes(4, "little").decode("latin-1") + payload

    obs = parse_observation(framed_payload)

    assert obs.event_type == "rock"
    assert obs.distance_mm == 120.0


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


def test_accepts_likely_real_robot_payload_aliases() -> None:
    obs = parse_observation(
        {
            "robot": "A",
            "message_type": "rock_detection",
            "x": 3,
            "y": 5,
            "object_distance_mm": 240,
            "color": "blue",
        }
    )

    assert obs.robot_id == "A"
    assert obs.event_type == "rock"
    assert obs.distance_mm == 240.0
    assert obs.raw["distance_mm"] == 240


def test_accepts_event_alias_with_native_event_type_name() -> None:
    obs = parse_observation(
        {
            "id": "A",
            "event": "robot_position",
            "x": 1,
            "y": 2,
            "heading_deg": 45,
        }
    )

    assert obs.robot_id == "A"
    assert obs.event_type == "robot_position"
    assert obs.heading == 45.0


def test_accepts_design_report_vocabulary_aliases() -> None:
    border = parse_observation({"robot_id": "A", "type": "border_detected", "x": 1, "y": 2})
    obstacle = parse_observation({"robot_id": "A", "type": "obstacle_detected", "x": 3, "y": 4})
    block = parse_observation({"robot_id": "A", "type": "block_detected", "x": 5, "y": 6})

    assert border.event_type == "boundary"
    assert obstacle.event_type == "obstacle"
    assert block.event_type == "rock"


def test_accepts_current_found_payloads_from_robot_a() -> None:
    payloads = [
        ({"robot_id": "A", "type": "block_found", "x": 2.34, "y": 5.67, "color": "Red", "size": 1}, "rock"),
        ({"robot_id": "A", "type": "border_found", "x": 3.45, "y": 6.78}, "boundary"),
        ({"robot_id": "A", "type": "mountain_found", "x": 0.32, "y": 0.78}, "mountain"),
        ({"robot_id": "A", "type": "cliff_found", "x": 4.56, "y": 7.89}, "cliff"),
    ]

    for payload, event_type in payloads:
        obs = parse_observation(payload)
        assert obs.event_type == event_type
        assert obs.robot_id == "A"


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
