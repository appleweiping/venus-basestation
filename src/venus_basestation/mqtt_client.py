from __future__ import annotations

from collections.abc import Callable
import os
import time

from .message_schema import Observation, parse_observation


ObservationHandler = Callable[[Observation], None]
LogHandler = Callable[[str], None]

DEFAULT_MQTT_HOST = "mqtt.ics.ele.tue.nl"
DEFAULT_MQTT_TOPICS = ["/pynqbridge/robot_43_1/send"]
DEFAULT_MQTT_PORT = 1883


def mqtt_config_from_env() -> dict[str, str | int | list[str]]:
    topics = os.getenv("VENUS_MQTT_TOPICS", "") or os.getenv("VENUS_MQTT_TOPIC", "")
    port = int(os.getenv("VENUS_MQTT_PORT", str(DEFAULT_MQTT_PORT)))
    return {
        "host": os.getenv("VENUS_MQTT_HOST", DEFAULT_MQTT_HOST),
        "port": port,
        "username": os.getenv("VENUS_MQTT_USERNAME", ""),
        "password": os.getenv("VENUS_MQTT_PASSWORD", ""),
        "topics": [topic.strip() for topic in topics.split(",") if topic.strip()] or DEFAULT_MQTT_TOPICS,
    }


def describe_mqtt_config(config: dict[str, str | int | list[str]]) -> str:
    topics = config.get("topics", [])
    topic_text = ", ".join(str(topic) for topic in topics) if isinstance(topics, list) else str(topics)
    username = str(config.get("username", ""))
    password = str(config.get("password", ""))
    return (
        f"MQTT host={config.get('host')} port={config.get('port')} "
        f"topics=[{topic_text}] username={username or '<none>'} "
        f"password={'set' if password else 'missing'}"
    )


class MqttSubscriber:
    def __init__(
        self,
        host: str,
        port: int,
        topics: list[str],
        on_observation: ObservationHandler,
        username: str = "",
        password: str = "",
        on_log: LogHandler | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.topics = topics
        self.on_observation = on_observation
        self.username = username
        self.password = password
        self.on_log = on_log or print
        self.messages_seen = 0
        self.connected = False
        self.last_error: str | None = None

    def run_until(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        client = self._build_client()
        deadline = time.monotonic() + timeout_seconds
        client.connect_timeout = min(max(timeout_seconds, 1.0), 5.0)
        client.connect(self.host, self.port)
        client.loop_start()
        try:
            while time.monotonic() < deadline:
                if self.messages_seen >= min_messages:
                    break
                time.sleep(0.05)
        finally:
            client.loop_stop()
            client.disconnect()
        return self.messages_seen

    def run_forever(self) -> None:
        client = self._build_client()
        client.connect_timeout = 5.0
        client.connect(self.host, self.port)
        client.loop_forever()

    def _build_client(self):
        import paho.mqtt.client as mqtt

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.username:
            client.username_pw_set(self.username, self.password)

        def handle_connect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
            self.connected = True
            self.on_log(f"connected to MQTT broker {self.host}:{self.port} with reason_code={reason_code}")
            for topic in self.topics:
                result, mid = client.subscribe(topic)
                self.on_log(f"subscribing to {topic} result={result} mid={mid}")

        def handle_message(client, userdata, message):  # noqa: ANN001
            try:
                observation = parse_observation(message.payload)
            except Exception as exc:  # pragma: no cover - defensive runtime logging
                self.last_error = f"failed to parse MQTT message on {message.topic}: {exc}"
                self.on_log(self.last_error)
                return
            self.messages_seen += 1
            self.on_observation(observation)

        client.on_connect = handle_connect
        client.on_message = handle_message
        return client
