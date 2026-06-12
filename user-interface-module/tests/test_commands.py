import json

import pytest

from venus_basestation.__main__ import main
from venus_basestation.mqtt_client import (
    MqttCommandSender,
    MqttSubscriber,
    build_command,
    default_course_command_topic,
    describe_mqtt_config,
    mqtt_config_from_env,
)


def test_build_command_matches_embedded_spec_payloads_byte_exact() -> None:
    # The docs promise the payloads are sent verbatim; pin the wire bytes.
    assert build_command("start") == '{"command":"start","arguments":["--verbose"]}'
    assert build_command("idle") == '{"command":"idle","arguments":[]}'
    assert build_command("stop") == '{"command":"stop","arguments":[]}'


def test_build_command_accepts_custom_arguments() -> None:
    assert json.loads(build_command("start", [])) == {"command": "start", "arguments": []}
    assert json.loads(build_command("idle", ["--fast"])) == {"command": "idle", "arguments": ["--fast"]}


def test_build_command_rejects_unknown_command() -> None:
    with pytest.raises(ValueError):
        build_command("reboot")


def test_default_course_command_topic_derives_recv_topic() -> None:
    assert default_course_command_topic("robot_15_1") == "/pynqbridge/15/recv"
    assert default_course_command_topic("robot_43_1") == "/pynqbridge/43/recv"
    assert default_course_command_topic("unexpected") == "/pynqbridge/43/recv"


def test_mqtt_config_derives_command_topic_from_username(monkeypatch) -> None:
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_COMMAND_TOPIC", raising=False)
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_15_1")

    config = mqtt_config_from_env()

    assert config["command_topic"] == "/pynqbridge/15/recv"


def test_mqtt_config_command_topic_env_override(monkeypatch) -> None:
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_15_1")
    monkeypatch.setenv("VENUS_MQTT_COMMAND_TOPIC", "/custom/recv")

    config = mqtt_config_from_env()

    assert config["command_topic"] == "/custom/recv"


def test_describe_mqtt_config_shows_command_topic_and_hides_password() -> None:
    text = describe_mqtt_config(
        {
            "host": "mqtt.example",
            "port": 1883,
            "username": "robot",
            "password": "secret-password",
            "topics": ["/demo/send"],
            "command_topic": "/demo/recv",
        }
    )

    assert "command_topic=/demo/recv" in text
    assert "secret-password" not in text


class _FakePublishResult:
    def __init__(self, rc: int, acked: bool = True) -> None:
        self.rc = rc
        self._acked = acked

    def wait_for_publish(self, timeout: float | None = None) -> None:
        pass

    def is_published(self) -> bool:
        return self._acked


class _FakeClient:
    def __init__(self, rc: int = 0, acked: bool = True) -> None:
        self.rc = rc
        self.acked = acked
        self.published: list[tuple[str, str, int]] = []

    def publish(self, topic: str, payload: str, qos: int = 0) -> _FakePublishResult:
        self.published.append((topic, payload, qos))
        return _FakePublishResult(self.rc, self.acked)


def _subscriber() -> MqttSubscriber:
    return MqttSubscriber(host="h", port=1883, topics=["/t"], on_observation=lambda obs: None, on_log=lambda msg: None)


def test_publish_command_requires_live_connection() -> None:
    subscriber = _subscriber()

    assert subscriber.publish_command("/demo/recv", build_command("start")) is False


def test_publish_command_publishes_qos1_on_live_client() -> None:
    subscriber = _subscriber()
    fake = _FakeClient()
    subscriber._client = fake
    subscriber.connected = True

    assert subscriber.publish_command("/demo/recv", build_command("stop")) is True
    topic, payload, qos = fake.published[0]
    assert topic == "/demo/recv"
    assert json.loads(payload) == {"command": "stop", "arguments": []}
    assert qos == 1


def test_publish_command_reports_failed_rc() -> None:
    subscriber = _subscriber()
    subscriber._client = _FakeClient(rc=4)
    subscriber.connected = True

    assert subscriber.publish_command("/demo/recv", build_command("idle")) is False
    assert "rc=4" in (subscriber.last_error or "")


def test_publish_command_requires_broker_ack() -> None:
    subscriber = _subscriber()
    subscriber._client = _FakeClient(rc=0, acked=False)
    subscriber.connected = True

    assert subscriber.publish_command("/demo/recv", build_command("stop")) is False
    assert "did not acknowledge" in (subscriber.last_error or "")


class _FakeSenderInfo:
    def __init__(self, published: bool) -> None:
        self._published = published

    def wait_for_publish(self, timeout: float | None = None) -> None:
        pass

    def is_published(self) -> bool:
        return self._published


class _FakeSenderClient:
    """Stands in for paho.mqtt.client.Client in MqttCommandSender tests.

    behavior: 'ok' fires a successful on_connect, 'reject' a refused one,
    'silent' never fires it (drives the connect-timeout branch).
    """

    def __init__(self, *args, behavior: str = "ok", publish_acked: bool = True, **kwargs) -> None:
        self.behavior = behavior
        self.publish_acked = publish_acked
        self.published: list[tuple[str, str, int]] = []
        self.loop_stopped = False
        self.disconnected = False
        self.on_connect = None
        self.connect_timeout = None

    def username_pw_set(self, username: str, password: str) -> None:
        pass

    def connect(self, host: str, port: int) -> None:
        if self.behavior == "reject":
            self.on_connect(self, None, None, "Not authorized", None)
        elif self.behavior == "ok":
            self.on_connect(self, None, None, 0, None)

    def loop_start(self) -> None:
        pass

    def publish(self, topic: str, payload: str, qos: int = 0) -> _FakeSenderInfo:
        self.published.append((topic, payload, qos))
        return _FakeSenderInfo(self.publish_acked)

    def loop_stop(self) -> None:
        self.loop_stopped = True

    def disconnect(self) -> None:
        self.disconnected = True


def _patch_sender_client(monkeypatch, **kwargs) -> dict:
    holder: dict = {}

    def factory(*args, **_ignored):
        holder["client"] = _FakeSenderClient(behavior=kwargs.get("behavior", "ok"), publish_acked=kwargs.get("publish_acked", True))
        return holder["client"]

    monkeypatch.setattr("paho.mqtt.client.Client", factory)
    return holder


def test_command_sender_publishes_qos1_and_cleans_up(monkeypatch) -> None:
    holder = _patch_sender_client(monkeypatch)
    sender = MqttCommandSender("h", 1883, on_log=lambda message: None)

    sender.send("/t/recv", build_command("stop"), timeout=0.5)

    client = holder["client"]
    assert client.published == [("/t/recv", '{"command":"stop","arguments":[]}', 1)]
    assert client.loop_stopped and client.disconnected


def test_command_sender_raises_on_rejected_connection(monkeypatch) -> None:
    holder = _patch_sender_client(monkeypatch, behavior="reject")
    sender = MqttCommandSender("h", 1883, on_log=lambda message: None)

    with pytest.raises(OSError, match="rejected connection"):
        sender.send("/t/recv", build_command("idle"), timeout=0.5)
    assert holder["client"].loop_stopped and holder["client"].disconnected


def test_command_sender_raises_on_connect_timeout(monkeypatch) -> None:
    holder = _patch_sender_client(monkeypatch, behavior="silent")
    sender = MqttCommandSender("h", 1883, on_log=lambda message: None)

    with pytest.raises(OSError, match="timed out connecting"):
        sender.send("/t/recv", build_command("start"), timeout=0.1)
    assert holder["client"].loop_stopped and holder["client"].disconnected


def test_command_sender_raises_on_unacknowledged_publish(monkeypatch) -> None:
    _patch_sender_client(monkeypatch, publish_acked=False)
    sender = MqttCommandSender("h", 1883, on_log=lambda message: None)

    with pytest.raises(OSError, match="did not acknowledge"):
        sender.send("/t/recv", build_command("stop"), timeout=0.5)


def test_cli_send_command_publishes_to_derived_topic(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--source", "mqtt", "--send-command", "start"])
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_15_1")
    monkeypatch.delenv("VENUS_MQTT_COMMAND_TOPIC", raising=False)
    sent: list[tuple[str, str]] = []

    def fake_send(self, topic: str, payload: str, timeout: float = 10.0) -> None:
        sent.append((topic, payload))

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttCommandSender.send", fake_send)

    main()

    topic, payload = sent[0]
    assert topic == "/pynqbridge/15/recv"
    assert json.loads(payload) == {"command": "start", "arguments": ["--verbose"]}
    output = capsys.readouterr().out
    assert "sent command 'start' to /pynqbridge/15/recv" in output
    assert "password=" in output  # sanitized config echo, never the value


def test_cli_send_command_topic_override(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["venus_basestation", "--source", "mqtt", "--send-command", "idle", "--command-topic", "/override/recv"],
    )
    sent: list[tuple[str, str]] = []

    def fake_send(self, topic: str, payload: str, timeout: float = 10.0) -> None:
        sent.append((topic, payload))

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttCommandSender.send", fake_send)

    main()

    assert sent[0][0] == "/override/recv"


def test_cli_send_command_reports_connection_failure(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--source", "mqtt", "--send-command", "stop"])

    def fail_send(self, topic: str, payload: str, timeout: float = 10.0) -> None:
        raise OSError("timed out connecting to broker after 10s")

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttCommandSender.send", fail_send)

    with pytest.raises(SystemExit) as exc:
        main()

    assert "MQTT command could not be sent" in str(exc.value)
    assert "password" in str(exc.value)


def test_cli_send_command_requires_mqtt_source(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--source", "simulated", "--send-command", "start"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert "--send-command requires --source mqtt" in str(exc.value)


def test_cli_send_command_rejects_save_flags(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["venus_basestation", "--source", "mqtt", "--send-command", "stop", "--save-state", "out.json"],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert "--save-state/--save-figure are not supported" in str(exc.value)


def test_cli_send_command_rejects_blank_topic_override(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["venus_basestation", "--source", "mqtt", "--send-command", "start", "--command-topic", "   "],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert "command topic is not configured" in str(exc.value)
