from venus_basestation.mqtt_client import default_course_topics
from venus_basestation.mqtt_client import describe_mqtt_config
from venus_basestation.mqtt_client import mqtt_config_from_env


def test_mqtt_config_from_env_uses_course_defaults(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_HOST", raising=False)
    monkeypatch.delenv("VENUS_MQTT_PORT", raising=False)
    monkeypatch.delenv("VENUS_MQTT_USERNAME", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPIC", raising=False)

    config = mqtt_config_from_env()

    assert config["host"] == "mqtt.ics.ele.tue.nl"
    assert config["port"] == 1883
    assert config["topics"] == ["/pynqbridge/43/send"]


def test_default_course_topics_derive_numeric_board_topic() -> None:
    assert default_course_topics("robot_15_1") == ["/pynqbridge/15/send"]
    assert default_course_topics("robot_43_1") == ["/pynqbridge/43/send"]
    assert default_course_topics("unexpected") == ["/pynqbridge/43/send"]


def test_mqtt_config_from_env_derives_course_topic_from_username(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPIC", raising=False)
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_15_1")

    config = mqtt_config_from_env()

    assert config["topics"] == ["/pynqbridge/15/send"]


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
