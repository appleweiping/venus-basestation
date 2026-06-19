from __future__ import annotations

from collections.abc import Callable
import dataclasses
import json
import os
import re
import time

from .message_schema import Observation, parse_observation


ObservationHandler = Callable[[Observation], None]
LogHandler = Callable[[str], None]
ConnectionHandler = Callable[[bool, str], None]

DEFAULT_MQTT_HOST = "mqtt.ics.ele.tue.nl"
DEFAULT_MQTT_PORT = 1883
# The course bridge has appeared in two topic conventions during integration:
# older teammate test scripts used the full MQTT username, while the current
# embedded interface says robots publish/receive on the bare board number
# (robot_43_1 -> /pynqbridge/43/{send,recv}). Subscribe to both telemetry
# forms so stale docs/scripts do not blank the dashboard; use the current bare
# board command topic by default because commands must target one channel.
COURSE_USERNAME_RE = re.compile(r"^robot_(?P<board>\d+)_\d+$")

# Test broker used by communication-module (hybrid_publisher_test.py)
TEST_MQTT_HOST = "broker.hivemq.com"
TEST_MQTT_TOPICS = ["energy_venus/team28/test"]
TEST_MQTT_COMMAND_TOPIC = "energy_venus/team28/test/recv"
TEST_MQTT_PORT = 1883

# Robot command interface (Team 28 embedded spec, updated 2026-06-16).
# The robot subscribes to /pynqbridge/<board>/recv and applies commands at the
# end of its active execution iteration step. The recv topic stays overridable
# (VENUS_MQTT_COMMAND_TOPIC / --command-topic) for last-minute demo changes.
VALID_COMMANDS = ("start", "idle", "stop")
DEFAULT_COMMAND_ARGUMENTS: dict[str, list[str]] = {
    "start": ["--verbose"],
    "idle": [],
    "stop": [],
}


def build_command(command: str, arguments: list[str] | None = None) -> str:
    """Serialize a robot command payload exactly as the embedded spec defines.

    ``start`` exits the IDLE hold / resumes navigation, ``idle`` parks the
    motors and waits, ``stop`` is the emergency kill that terminates the
    embedded application. Default arguments mirror the spec examples.
    """
    if command not in VALID_COMMANDS:
        raise ValueError(f"unsupported command: {command!r} (expected one of {', '.join(VALID_COMMANDS)})")
    payload_arguments = DEFAULT_COMMAND_ARGUMENTS[command] if arguments is None else list(arguments)
    # Compact separators: wire bytes match the spec samples verbatim.
    return json.dumps({"command": command, "arguments": payload_arguments}, separators=(",", ":"))


def _course_board_id(username: str) -> str:
    match = COURSE_USERNAME_RE.fullmatch(username.strip())
    return match.group("board") if match else ""


def course_board_id(username: str) -> str:
    """Public: the bare board number for a course username (``robot_43_1`` ->
    ``43``), or ``""`` if the username is not a course credential. Used to label
    each robot's telemetry when several boards share one dashboard."""
    return _course_board_id(username)


def default_course_topics(username: str) -> list[str]:
    """Telemetry topics to subscribe to for a course robot.

    Current Team 28 robots publish to the bare board topic
    ``/pynqbridge/<board>/send`` (e.g. ``robot_43_1`` -> ``/pynqbridge/43/send``).
    The full-username topic is also subscribed as a compatibility fallback for
    older teammate scripts. Returns an empty list for missing/malformed
    usernames rather than guessing another team's board.
    """
    uname = username.strip()
    board = _course_board_id(uname)
    if board:
        return [f"/pynqbridge/{board}/send", f"/pynqbridge/{uname}/send"]
    return []


def default_course_command_topic(username: str) -> str:
    """Command topic the robot subscribes to: /pynqbridge/<board>/recv.

    Returns an empty string for a missing/malformed username so a typo cannot
    silently misdirect a command (e.g. an E-STOP) to another board's topic.
    """
    uname = username.strip()
    board = _course_board_id(uname)
    if board:
        return f"/pynqbridge/{board}/recv"
    return ""


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
        default_command_topic = TEST_MQTT_COMMAND_TOPIC
    else:
        default_host = DEFAULT_MQTT_HOST
        default_port = DEFAULT_MQTT_PORT
        default_topics = default_course_topics(username)
        default_command_topic = default_course_command_topic(username)

    topics = os.getenv("VENUS_MQTT_TOPICS", "") or os.getenv("VENUS_MQTT_TOPIC", "")
    port = int(os.getenv("VENUS_MQTT_PORT", str(default_port)))
    return {
        "host": os.getenv("VENUS_MQTT_HOST", default_host),
        "port": port,
        "username": username,
        "password": os.getenv("VENUS_MQTT_PASSWORD", ""),
        "topics": [topic.strip() for topic in topics.split(",") if topic.strip()] or default_topics,
        "command_topic": os.getenv("VENUS_MQTT_COMMAND_TOPIC", "").strip() or default_command_topic,
    }


def describe_mqtt_config(config: dict[str, str | int | list[str]]) -> str:
    topics = config.get("topics", [])
    topic_text = ", ".join(str(topic) for topic in topics) if isinstance(topics, list) else str(topics)
    username = str(config.get("username", ""))
    password = str(config.get("password", ""))
    command_topic = str(config.get("command_topic", "")) or "<none>"
    return (
        f"MQTT host={config.get('host')} port={config.get('port')} "
        f"topics=[{topic_text}] command_topic={command_topic} username={username or '<none>'} "
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
        label: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.topics = topics
        self.on_observation = on_observation
        self.username = username
        self.password = password
        # When set (multi-robot mode), each received observation's robot_id is
        # prefixed with this label so two boards that both report robot_id "A"
        # render as distinct tracks (e.g. "15:A" and "43:A").
        self.label = label
        self.on_log = on_log or print
        self.on_connect_change = on_connect_change
        self.messages_seen = 0
        self.connected = False
        self.connection_error: str | None = None
        self.subscriptions_acknowledged = 0
        self.subscription_errors: list[str] = []
        self.last_error: str | None = None
        self._client = None

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
            client.disconnect()
            client.loop_stop()
        return self.messages_seen

    def run_forever(self) -> None:
        client = self._build_client()
        client.connect_timeout = 5.0
        client.connect(self.host, self.port)
        client.loop_forever()

    def publish_command(self, topic: str, payload: str, *, ack_timeout: float = 2.0) -> bool:
        """Publish a robot command on the live connection (QoS 1).

        Safe to call from another thread (paho's publish is thread-safe; the
        network thread services the PUBACK while we wait). Success means the
        broker acknowledged the publish — enqueue alone is not enough, because
        on a half-open link paho queues silently for up to the keepalive
        interval while reporting local success. Returns False when the uplink
        is down or the broker does not acknowledge within ``ack_timeout``.
        """
        client = self._client
        if client is None or not self.connected:
            self.last_error = "uplink not connected to broker"
            return False
        result = client.publish(topic, payload, qos=1)
        if result.rc != 0:
            self.last_error = f"command publish to {topic} failed: rc={result.rc}"
            self.on_log(self.last_error)
            return False
        try:
            result.wait_for_publish(timeout=ack_timeout)
            published = result.is_published()
        except (RuntimeError, ValueError) as exc:
            self.last_error = f"command publish to {topic} failed: {exc}"
            self.on_log(self.last_error)
            return False
        if not published:
            self.last_error = (
                f"broker did not acknowledge command publish to {topic} within {ack_timeout:g}s "
                "(it may still be delivered on reconnect)"
            )
            self.on_log(self.last_error)
            return False
        self.on_log(f"published command to {topic}: {payload}")
        return True

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
                # Surface the rejection (turn the UI pill red) and stop paho's
                # silent reconnect_on_failure loop — otherwise a wrong password
                # retries forever while the dashboard just sits on STANDBY and
                # the operator has no idea why nothing is arriving.
                if self.on_connect_change:
                    self.on_connect_change(False, self.host)
                client.disconnect()
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
            if self.label:
                observation = dataclasses.replace(
                    observation, robot_id=f"{self.label}:{observation.robot_id}"
                )
            self.messages_seen += 1
            # The handler runs on paho's network thread; an exception here would
            # propagate out of loop_forever and kill the whole subscriber (paho
            # re-raises on_message errors by default). One bad event must not
            # tear down the live stream.
            try:
                self.on_observation(observation)
            except Exception as exc:  # pragma: no cover - defensive runtime logging
                self.last_error = f"observation handler failed on {message.topic}: {exc}"
                self.on_log(self.last_error)

        def handle_disconnect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
            self.connected = False
            self.on_log(f"disconnected from MQTT broker {self.host}:{self.port} ({reason_code})")
            if self.on_connect_change:
                self.on_connect_change(False, self.host)

        client.on_connect = handle_connect
        client.on_subscribe = handle_subscribe
        client.on_message = handle_message
        client.on_disconnect = handle_disconnect
        self._client = client
        return client


class MqttCommandSender:
    """One-shot command publisher for headless CLI use.

    Connects, publishes a single QoS 1 command, waits for the broker
    acknowledgement, then disconnects. Raises OSError with a concise reason
    on connect/auth/publish failure.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        on_log: LogHandler | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.on_log = on_log or print

    def send(self, topic: str, payload: str, timeout: float = 10.0) -> None:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.username:
            client.username_pw_set(self.username, self.password)

        connected = False
        connection_error: str | None = None

        def handle_connect(client, userdata, flags, reason_code, properties):  # noqa: ANN001
            nonlocal connected, connection_error
            if _is_success_reason(reason_code):
                connected = True
            else:
                connection_error = f"MQTT broker rejected connection: {reason_code}"

        client.on_connect = handle_connect
        client.connect_timeout = min(max(timeout, 1.0), 5.0)
        client.connect(self.host, self.port)
        client.loop_start()
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and not connected and not connection_error:
                time.sleep(0.05)
            if connection_error:
                raise OSError(connection_error)
            if not connected:
                raise OSError(f"timed out connecting to broker after {timeout:g}s")
            info = client.publish(topic, payload, qos=1)
            try:
                info.wait_for_publish(timeout=max(deadline - time.monotonic(), 1.0))
                published = info.is_published()
            except (RuntimeError, ValueError) as exc:
                # paho 2.x raises RuntimeError from wait_for_publish/is_published
                # when the publish rc is non-zero (e.g. connection dropped).
                raise OSError(f"command publish to {topic} failed: {exc}") from exc
            if not published:
                raise OSError(f"broker did not acknowledge command publish to {topic}")
            self.on_log(f"published command to {topic}: {payload}")
        finally:
            client.disconnect()
            client.loop_stop()


def _is_success_reason(reason_code) -> bool:  # noqa: ANN001
    return reason_code == 0 or str(reason_code).lower() == "success"
