import pytest


@pytest.fixture(autouse=True)
def _no_local_dotenv(monkeypatch):
    """Keep tests hermetic: never load a developer's local .env into main().

    main() calls load_dotenv() to ease live setup; in tests that would leak a
    real .env's VENUS_* values into cases that delete/set those vars.
    """
    monkeypatch.setattr("venus_basestation.__main__.load_dotenv", lambda *args, **kwargs: [])
