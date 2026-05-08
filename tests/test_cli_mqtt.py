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
