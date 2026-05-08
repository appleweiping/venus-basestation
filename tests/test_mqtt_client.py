from venus_basestation.mqtt_client import describe_mqtt_config
from venus_basestation.mqtt_client import mqtt_config_from_env


def test_mqtt_config_from_env_uses_team28_defaults(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_HOST", raising=False)
    monkeypatch.delenv("VENUS_MQTT_PORT", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)

    config = mqtt_config_from_env()

    assert config["host"] == "mqtt.ics.ele.tue.nl"
    assert config["port"] == 1883
    assert config["topics"] == ["/pynqbridge/robot_43_1/send"]


def test_mqtt_config_from_env_accepts_comma_separated_topics(monkeypatch) -> None:
    monkeypatch.setenv("VENUS_MQTT_TOPICS", "/topic/a, /topic/b")
    monkeypatch.setenv("VENUS_MQTT_PORT", "1884")

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
