import pytest

from venus_basestation.__main__ import main


@pytest.fixture(autouse=True)
def _course_username(monkeypatch):
    # The course broker always authenticates with a board username; the topic
    # is derived from it. Set a valid one so these checks exercise the broker
    # path rather than the "no derivable topic" guard.
    monkeypatch.delenv("VENUS_MQTT_PROFILE", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPICS", raising=False)
    monkeypatch.delenv("VENUS_MQTT_TOPIC", raising=False)
    monkeypatch.setenv("VENUS_MQTT_USERNAME", "robot_43_1")


def test_mqtt_check_reports_connection_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "venus_basestation",
            "--source",
            "mqtt",
            "--headless",
            "--mqtt-check",
            "--mqtt-timeout",
            "1",
        ],
    )

    def fail_run_until(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        raise TimeoutError("timed out")

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttSubscriber.run_until", fail_run_until)

    with pytest.raises(SystemExit) as exc:
        main()

    assert "MQTT check could not connect" in str(exc.value)
    assert "password" in str(exc.value)


def test_mqtt_check_reports_broker_rejected_connection(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "venus_basestation",
            "--source",
            "mqtt",
            "--headless",
            "--mqtt-check",
            "--mqtt-min-messages",
            "0",
        ],
    )

    def reject_connection(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        self.connection_error = "MQTT broker rejected connection: Bad username or password"
        return 0

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttSubscriber.run_until", reject_connection)

    with pytest.raises(SystemExit) as exc:
        main()

    assert "Bad username or password" in str(exc.value)


def test_mqtt_check_reports_subscription_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "venus_basestation",
            "--source",
            "mqtt",
            "--headless",
            "--mqtt-check",
            "--mqtt-min-messages",
            "0",
        ],
    )

    def reject_subscription(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        self.subscription_errors = ["subscription to /bad/topic was not granted by broker: Unspecified error"]
        return 0

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttSubscriber.run_until", reject_subscription)

    with pytest.raises(SystemExit) as exc:
        main()

    assert "not granted by broker" in str(exc.value)


def test_mqtt_check_allows_connection_only_check(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "venus_basestation",
            "--source",
            "mqtt",
            "--headless",
            "--mqtt-check",
            "--mqtt-min-messages",
            "0",
        ],
    )

    def connect_only(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        assert min_messages == 0
        self.connected = True
        self.subscriptions_acknowledged = len(self.topics)
        return 0

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttSubscriber.run_until", connect_only)

    main()


def test_mqtt_check_without_credentials_exits_instead_of_simulating(monkeypatch) -> None:
    # The README's connection check has no --source; with no credentials it
    # used to fall back to simulated data and open the dashboard.
    monkeypatch.delenv("VENUS_MQTT_USERNAME", raising=False)
    monkeypatch.delenv("VENUS_MQTT_ACCOUNTS", raising=False)
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--mqtt-check", "--mqtt-min-messages", "0"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert "no MQTT credentials" in str(exc.value)


def test_mqtt_check_implies_mqtt_source_and_opens_no_window(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--mqtt-check", "--mqtt-min-messages", "0"])
    checked: list[list[str]] = []

    def connect_only(self, timeout_seconds: float, *, min_messages: int = 1) -> int:
        checked.append(list(self.topics))
        return 0

    def no_window(*args, **kwargs):
        raise AssertionError("--mqtt-check must not open a dashboard window")

    monkeypatch.setattr("venus_basestation.mqtt_client.MqttSubscriber.run_until", connect_only)
    monkeypatch.setattr("venus_basestation.__main__.TkDashboard", no_window)

    main()

    assert checked and "/pynqbridge/43/send" in checked[0]


def test_mqtt_check_rejects_non_mqtt_source(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--source", "simulated", "--mqtt-check"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert "--mqtt-check only works with --source mqtt" in str(exc.value)
