"""Shared fixtures. Integration tests use the real Neo4j from `docker compose up -d`."""

import logging
from collections.abc import Iterator

import pytest

from tracepath.config import Neo4jSettings, load_neo4j_settings
from tracepath.graph import GraphUnavailable, connect

# Nothing listens on port 1, so connecting there fails for real, with no mock.
UNREACHABLE_URI = "bolt://localhost:1"

#: The key and API address every test runs with (spec 0004 AC-74). Nothing listens on
#: port 1, so a test that forgot to point at the fake API fails instead of spending.
FAKE_API_KEY = "sk-ant-test"
UNREACHABLE_API = "http://localhost:1"


@pytest.fixture(autouse=True)
def no_real_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test runs with a fake key and an unreachable API (spec 0004 AC-74).

    The developer's `.env` holds a real key and `config.py` loads `.env` on every
    settings read. `load_dotenv()` never replaces a variable already set, so setting
    these first means the real key cannot load in a test, while `.env` still supplies
    the Neo4j settings the integration tests need. A test that uses the fake API sets
    its own base URL.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_API_KEY)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", UNREACHABLE_API)


@pytest.fixture(scope="session")
def neo4j_settings() -> Neo4jSettings:
    """Settings for the running Neo4j; fails loudly if it is not up."""
    settings = load_neo4j_settings()
    try:
        connect(settings).close()
    except GraphUnavailable as exc:
        pytest.fail(f"Integration tests need Neo4j: {exc}")
    return settings


@pytest.fixture(autouse=True)
def reset_tracepath_log_level() -> Iterator[None]:
    """`--debug` raises the tracepath logger level; undo it so tests stay independent."""
    logger = logging.getLogger("tracepath")
    level = logger.level
    yield
    logger.setLevel(level)
