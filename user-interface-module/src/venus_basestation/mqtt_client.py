from __future__ import annotations

from collections.abc import Callable
import os
import re
import time

from .message_schema import Observation, parse_observation


ObservationHandler = Callable[[Observation], None]
LogHandler = Callable[[str], None]
ConnectionHandler = Callable[[bool, str], None]

DEFAULT_MQTT_HOST = "mqtt.ics.ele.tue.nl"
DEFAULT_MQTT_TOPICS = ["/pynqbridge/43/send"]
DEFAULT_MQTT_PORT = 1883
COURSE_USERNAME_RE = re.compile(r"^robot_(\d+)_\d+$")

# Test broker used by communication-module (hybrid_publisher_test.py)
TEST_MQTT_HOST = "broker.hivemq.com"
TEST_MQTT_TOPICS = ["energy_venus/team28/test"]
TEST_MQTT_PORT = 1883


def default_course_topics(username: str) -> list[str]:
    """Return the course PYNQ bridge topic for a robot credential."""
    match = COURSE_USERNAME_RE.fullmatch(username.strip())
    if match:
        board_number = match.group(1)
        return [f"/pynqbridge/{board_number}/send"]
    return DEFAULT_MQTT_TOPICS


def mqtt_config_from_env() -> dict[str, str | int | list[str]]:
    """Build MQTT config from environment variables.

    Set VENUS_MQTT_PROFILE=test to use the HiveMQ test broker
    (energy_venus/team28/test) used by the communication-module team.
    Default profile uses the course broker (mqtt.ics.ele.tue.nl).
    """
    profile = os.getenv("VENUS_MQTT_PROFILE", "course").lower()
    username = os.getenv("VENUS_MQTT_USERNAME", "")
    if profile == "test":
        default_host = TEST_MQTT_HOST
        default_port = TEST_MQTT_PORT
        default_topics = TEST_MQTT_TOPICS
    else:
        default_host = DEFAULT_MQTT_HOST
        default_port = DEFAULT_MQTT_PORT
        default_topics = default_course_topics(username)

    topics = os.getenv("VENUS_MQTT_TOPICS", "") or os.getenv("VENUS_MQTT_TOPIC", "")
    port = int(os.getenv("VENUS_MQTT_PORT", str(default_port)))
    return {
        "host": os.getenv("VENUS_MQTT_HOST", default_host),
        "port": port,
        "username": username,
        "password": os.getenv("VENUS_MQTT_PASSWORD", ""),
        "topics": [topic.strip() for topic in topics.split(",") if topic.strip()] or default_topics,
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
        on_connect_change: ConnectionHandler | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.topics = topics
        self.on_observation = on_observation
        self.username = username
        self.password = password
        self.on_log = on_log or print
        self.on_connect_change = on_connect_change
        self.messages_seen = 0
        self.connected = False
        self.connection_error: str | None = None
        self.subscriptions_acknowledged = 0
        self.subscription_errors: list[str] = []
        self.last_error: str | None = None

    def run_until(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        self.messages_seen = 0
        self.connected = False
        self.connection_error = None
        self.subscriptions_acknowledged = 0
        self.subscription_errors = []
        self.last_error = None
        client = self._build_client()
        deadline = time.monotonic() + timeout_seconds
        client.connect_timeout = min(max(timeout_seconds, 1.0), 5.0)
        client.connect(self.host, self.port)
        client.loop_start()
        try:
            while time.monotonic() < deadline:
                if self.connection_error or self.subscription_errors:
                    break
                if min_messages <= 0:
                    if self.connected and self.subscriptions_acknowledged >= len(self.topics):
                        break
                elif self.messages_seen >= min_messages:
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
        subscribed_topics: dict[int, str] = {}

        def handle_connect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
            if not _is_success_reason(reason_code):
                self.connection_error = f"MQTT broker rejected connection: {reason_code}"
                self.last_error = self.connection_error
                self.on_log(self.connection_error)
                return
            self.connected = True
            self.on_log(f"connected to MQTT broker {self.host}:{self.port} with reason_code={reason_code}")
            if self.on_connect_change:
                self.on_connect_change(True, self.host)
            for topic in self.topics:
                result, mid = client.subscribe(topic)
                subscribed_topics[mid] = topic
                self.on_log(f"subscribing to {topic} result={result} mid={mid}")

        def handle_subscribe(client, userdata, mid, reason_codes, properties):  # noqa: ANN001
            self.subscriptions_acknowledged += 1
            topic = subscribed_topics.get(mid, f"mid={mid}")
            codes = [str(code) for code in reason_codes]
            failed = any(
                getattr(code, "is_failure", False)
                or "error" in str(code).lower()
                or "not authorized" in str(code).lower()
                for code in reason_codes
            )
            message = f"subscription to {topic} acknowledged: {', '.join(codes)}"
            if failed:
                message = f"subscription to {topic} was not granted by broker: {', '.join(codes)}"
                self.subscription_errors.append(message)
                self.last_error = message
            self.on_log(message)

        def handle_message(client, userdata, message):  # noqa: ANN001
            try:
                observation = parse_observation(message.payload)
            except Exception as exc:  # pragma: no cover - defensive runtime logging
                self.last_error = f"failed to parse MQTT message on {message.topic}: {exc}"
                self.on_log(self.last_error)
                return
            self.messages_seen += 1
            self.on_observation(observation)

        def handle_disconnect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
            self.connected = False
            self.on_log(f"disconnected from MQTT broker {self.host}:{self.port} ({reason_code})")
            if self.on_connect_change:
                self.on_connect_change(False, self.host)

        client.on_connect = handle_connect
        client.on_subscribe = handle_subscribe
        client.on_message = handle_message
        client.on_disconnect = handle_disconnect
        return client


def _is_success_reason(reason_code) -> bool:  # noqa: ANN001
    return reason_code == 0 or str(reason_code).lower() == "success"
