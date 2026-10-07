"""The held fixture written into real Neo4j and read back walks to the same output (spec 0005).

Written through the same write functions `load()` uses, and read through the one Cypher
read `trace` uses, so the round trip covers `held` and `held_reasons` as stored.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver

from tests import held_fixture as fx
from tests.test_held_walk import clean_slice
from tracepath.config import Neo4jSettings
from tracepath.extract.schema import EntityType, RelationshipType
from tracepath.graph import connect
from tracepath.graph.load import (
    write_entities,
    write_links,
    write_part_of,
    write_records,
    write_unresolved,
)
from tracepath.graph.read import read_graph
from tracepath.graph.schema import clear, create_constraints
from tracepath.traverse.render import render_chain
from tracepath.traverse.walk import walk

pytestmark = pytest.mark.integration

EXPECTED = Path(__file__).parent / "fixtures" / "held-fixture-expected.txt"


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        clear(opened, neo4j_settings.database)
        create_constraints(opened, neo4j_settings.database)
        yield opened
        clear(opened, neo4j_settings.database)


def write_fixture(driver: Driver, database: str) -> None:
    write_records(driver, database, fx.RECORDS)
    by_type: dict[EntityType, list[dict[str, object]]] = {}
    for row in fx.ENTITIES:
        by_type.setdefault(EntityType(row["type"]), []).append(row)
    write_entities(driver, database, dict(by_type))
    write_unresolved(driver, database, fx.UNRESOLVED)
    write_part_of(driver, database, fx.PART_OF)
    by_link: dict[RelationshipType, list[dict[str, object]]] = {}
    for link_type, row in fx.LINKS:
        by_link.setdefault(RelationshipType[link_type], []).append(row)
    write_links(driver, database, dict(by_link))


def test_the_held_fixture_read_back_with_held_walks_to_the_hand_written_output(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    write_fixture(driver, neo4j_settings.database)

    graph = read_graph(driver, neo4j_settings.database, with_held=True)

    assert "\n".join(render_chain(walk(graph, fx.START))) + "\n" == EXPECTED.read_text()


def test_the_held_fixture_read_back_without_held_is_the_clean_slice(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: spec 0005 AC-2, AC-3 (through the real read)."""
    write_fixture(driver, neo4j_settings.database)

    assert read_graph(driver, neo4j_settings.database) == clean_slice()
