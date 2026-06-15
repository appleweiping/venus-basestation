from pathlib import Path

from venus_basestation.env_config import has_mqtt_credentials, load_dotenv, resolve_source


def test_load_dotenv_populates_unset_keys(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "# Venus settings",
                "VENUS_MQTT_USERNAME=robot_43_1",
                'VENUS_MQTT_PASSWORD="secret"',
                "VENUS_MQTT_HOST = mqtt.ics.ele.tue.nl ",
                "",
                "BARE_LINE_WITHOUT_EQUALS",
            ]
        ),
        encoding="utf-8",
    )
    env: dict[str, str] = {}

    loaded = load_dotenv([tmp_path], environ=env)

    assert loaded == [str(tmp_path / ".env")]
    assert env["VENUS_MQTT_USERNAME"] == "robot_43_1"
    assert env["VENUS_MQTT_PASSWORD"] == "secret"  # quotes stripped
    assert env["VENUS_MQTT_HOST"] == "mqtt.ics.ele.tue.nl"  # whitespace trimmed
    assert "BARE_LINE_WITHOUT_EQUALS" not in env


def test_load_dotenv_does_not_override_existing(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("VENUS_MQTT_PASSWORD=from_file", encoding="utf-8")
    env = {"VENUS_MQTT_PASSWORD": "from_shell"}

    load_dotenv([tmp_path], environ=env)

    assert env["VENUS_MQTT_PASSWORD"] == "from_shell"


def test_load_dotenv_missing_file_is_noop(tmp_path: Path) -> None:
    env: dict[str, str] = {}

    assert load_dotenv([tmp_path], environ=env) == []
    assert env == {}


def test_resolve_source_explicit_wins() -> None:
    assert resolve_source("simulated", has_credentials=True) == ("simulated", None)
    assert resolve_source("jsonl", has_credentials=False) == ("jsonl", None)


def test_resolve_source_auto_selects_mqtt_with_credentials() -> None:
    source, hint = resolve_source(None, has_credentials=True)
    assert source == "mqtt"
    assert hint and "--source mqtt" in hint


def test_resolve_source_falls_back_to_simulated_without_credentials() -> None:
    source, hint = resolve_source(None, has_credentials=False)
    assert source == "simulated"
    assert hint and ".env" in hint


def test_has_mqtt_credentials() -> None:
    assert has_mqtt_credentials({"VENUS_MQTT_USERNAME": "robot_43_1"}) is True
    assert has_mqtt_credentials({"VENUS_MQTT_USERNAME": "   "}) is False
    assert has_mqtt_credentials({}) is False
