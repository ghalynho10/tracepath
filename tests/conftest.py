"""Shared fixtures. Integration tests use the real Neo4j from `docker compose up -d`."""

import logging
from collections.abc import Iterator

import pytest

from tracepath.config import Neo4jSettings, load_neo4j_settings
from tracepath.graph import GraphUnavailable, connect

# Nothing listens on port 1, so connecting there fails for real, with no mock.
UNREACHABLE_URI = "bolt://localhost:1"


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
