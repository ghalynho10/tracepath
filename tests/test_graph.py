import re

import pytest

from tests.conftest import UNREACHABLE_URI
from tracepath.config import Neo4jSettings
from tracepath.graph import GraphUnavailable, connect, server_version

pytestmark = pytest.mark.integration


def test_connect_returns_a_driver_that_answers_queries(neo4j_settings: Neo4jSettings) -> None:
    with connect(neo4j_settings) as driver:
        version = server_version(driver, neo4j_settings.database)

    assert re.fullmatch(r"5\.\d+\.\d+", version)


def test_unreachable_database_raises_graph_unavailable_naming_the_uri() -> None:
    settings = Neo4jSettings(uri=UNREACHABLE_URI, username="neo4j", password="x", database="neo4j")

    with pytest.raises(GraphUnavailable) as caught:
        connect(settings)

    message = str(caught.value)
    assert UNREACHABLE_URI in message
    assert "docker compose up -d" in message


def test_graph_unavailable_hides_the_driver_error_chain() -> None:
    settings = Neo4jSettings(uri=UNREACHABLE_URI, username="neo4j", password="x", database="neo4j")

    with pytest.raises(GraphUnavailable) as caught:
        connect(settings)

    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
