import pytest

from venus_basestation.__main__ import main


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
