from venus_basestation.mqtt_client import MqttSubscriber
from venus_basestation.mqtt_client import default_course_topics
from venus_basestation.mqtt_client import describe_mqtt_config
from venus_basestation.mqtt_client import mqtt_config_from_env


class _FakeMessage:
    def __init__(self, payload: bytes, topic: str = "/pynqbridge/robot_43_1/send") -> None:
        self.payload = payload
        self.topic = topic


class _RecordingClient:
    """Minimal stand-in for the paho client passed to the connect callback."""

    def __init__(self) -> None:
        self.disconnected = False

    def disconnect(self) -> None:
        self.disconnected = True

    def subscribe(self, topic):  # pragma: no cover - success path not exercised here
        return (0, 1)


def test_mqtt_config_from_env_uses_course_defaults(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_HOST", raising=False)
    monkeypatch.delenv("VENUS_MQTT_PORT", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPIC", raising=False)
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_43_1")

    config = mqtt_config_from_env()

    assert config["host"] == "mqtt.ics.ele.tue.nl"
    assert config["port"] == 1883
    assert config["topics"] == ["/pynqbridge/robot_43_1/send"]


def test_mqtt_config_requires_username_to_derive_course_topic(monkeypatch) -> None:
    # Safety: with no/invalid username the course topic is NOT guessed — it
    # is left empty so a typo'd credential can't silently target another board.
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_USERNAME", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPIC", raising=False)

    config = mqtt_config_from_env()

    assert config["topics"] == []


def test_default_course_topics_use_full_username() -> None:
    # The pynqbridge id is the full MQTT username, matching Team 28's own
    # publisher (/pynqbridge/robot_43_1/send) — not the bare board number.
    assert default_course_topics("robot_15_1") == ["/pynqbridge/robot_15_1/send"]
    assert default_course_topics("robot_43_1") == ["/pynqbridge/robot_43_1/send"]
    # A malformed/typo username refuses to derive a topic instead of guessing.
    assert default_course_topics("unexpected") == []
    assert default_course_topics("robot15") == []


def test_subscribed_topic_matches_team_publisher_exactly() -> None:
    # Regression guard for the "interface doesn't work" bug: Team 28's
    # communication-module publishes telemetry to this exact string. MQTT
    # matching is exact, so the subscribed topic must match byte-for-byte.
    team_publisher_topic = "/pynqbridge/robot_43_1/send"
    assert default_course_topics("robot_43_1") == [team_publisher_topic]


def test_mqtt_config_from_env_derives_course_topic_from_username(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPIC", raising=False)
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_15_1")

    config = mqtt_config_from_env()

    assert config["topics"] == ["/pynqbridge/robot_15_1/send"]


def test_mqtt_config_from_env_accepts_comma_separated_topics(monkeypatch) -> None:
    monkeypatch.setenv("VENUS_MQTT_TOPICS", "/topic/a, /topic/b")
    monkeypatch.setenv("VENUS_MQTT_PORT", "1884")
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_15_1")

    config = mqtt_config_from_env()

    assert config["port"] == 1884
    assert config["topics"] == ["/topic/a", "/topic/b"]


def test_mqtt_config_from_env_accepts_singular_topic_alias(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.setenv("VENUS_MQTT_TOPIC", "/single/topic")

    config = mqtt_config_from_env()

    assert config["topics"] == ["/single/topic"]


def test_describe_mqtt_config_does_not_expose_password() -> None:
    text = describe_mqtt_config(
        {
            "host": "mqtt.example",
            "port": 1883,
            "username": "robot",
            "password": "secret-password",
            "topics": ["/demo/topic"],
        }
    )

    assert "secret-password" not in text
    assert "password=set" in text
    assert "/demo/topic" in text


def test_handle_message_survives_handler_exception() -> None:
    # An exception in on_observation must not propagate out of paho's loop and
    # kill the live subscriber — one bad event should be logged and skipped.
    logs: list[str] = []
    sub = MqttSubscriber(
        host="h",
        port=1883,
        topics=["/t"],
        on_observation=lambda obs: (_ for _ in ()).throw(RuntimeError("boom")),
        on_log=logs.append,
    )
    client = sub._build_client()
    payload = b'{"robot_id":"A","type":"position_update","x":1,"y":2}'

    client.on_message(client, None, _FakeMessage(payload))  # must not raise

    assert sub.messages_seen == 1
    assert any("observation handler failed" in line for line in logs)


def test_handle_connect_rejection_surfaces_and_stops_retry() -> None:
    # A broker rejection (e.g. wrong password) must turn the UI pill red and
    # disconnect, not silently retry forever while the dashboard sits idle.
    conn_events: list[tuple[bool, str]] = []
    sub = MqttSubscriber(
        host="mqtt.example",
        port=1883,
        topics=["/t"],
        on_observation=lambda obs: None,
        on_log=lambda msg: None,
        on_connect_change=lambda ok, broker: conn_events.append((ok, broker)),
    )
    sub._build_client()  # wires the closures and captures self
    fake = _RecordingClient()

    sub._client.on_connect(fake, None, None, "Not authorized", None)

    assert conn_events == [(False, "mqtt.example")]
    assert fake.disconnected is True
    assert sub.connection_error and "rejected connection" in sub.connection_error
