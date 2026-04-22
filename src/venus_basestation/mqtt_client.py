from __future__ import annotations

from collections.abc import Callable
import os

from .message_schema import Observation, parse_observation


ObservationHandler = Callable[[Observation], None]


def mqtt_config_from_env() -> dict[str, str | list[str]]:
    topics = os.getenv("VENUS_MQTT_TOPICS", "")
    return {
        "host": os.getenv("VENUS_MQTT_HOST", "mqtt.ics.ele.tue.nl"),
        "username": os.getenv("VENUS_MQTT_USERNAME", ""),
        "password": os.getenv("VENUS_MQTT_PASSWORD", ""),
        "topics": [topic.strip() for topic in topics.split(",") if topic.strip()],
    }


class MqttSubscriber:
    def __init__(
        self,
        host: str,
        topics: list[str],
        on_observation: ObservationHandler,
        username: str = "",
        password: str = "",
    ) -> None:
        self.host = host
        self.topics = topics
        self.on_observation = on_observation
        self.username = username
        self.password = password

    def run_forever(self) -> None:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.username:
            client.username_pw_set(self.username, self.password)

        def handle_connect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
            for topic in self.topics:
                client.subscribe(topic)

        def handle_message(client, userdata, message):  # noqa: ANN001
            try:
                self.on_observation(parse_observation(message.payload))
            except Exception as exc:  # pragma: no cover - defensive runtime logging
                print(f"failed to parse MQTT message on {message.topic}: {exc}")

        client.on_connect = handle_connect
        client.on_message = handle_message
        client.connect(self.host)
        client.loop_forever()

