"""The fixture graph written into real Neo4j and read back gives the same chain (AC-33).

Written through the same write functions `load()` uses, and read through the one
Cypher read `trace` uses, so the round trip covers every property the walk prints.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver

from tests import trace_fixture as fx
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

EXPECTED = Path(__file__).parent / "fixtures" / "trace-fixture-expected.txt"


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


def test_the_fixture_read_back_from_neo4j_walks_to_the_same_output(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    write_fixture(driver, neo4j_settings.database)

    lines = render_chain(walk(read_graph(driver, neo4j_settings.database), fx.START))

    assert "\n".join(lines) + "\n" == EXPECTED.read_text()


def test_the_read_leaves_part_of_out_of_the_slice(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    write_fixture(driver, neo4j_settings.database)

    graph = read_graph(driver, neo4j_settings.database)

    assert {link.type for link in graph.links} <= {t.name for t in RelationshipType}
    assert len(graph.links) == len(fx.LINKS)
    assert len(graph.nodes) == len(fx.RECORDS) + len(fx.ENTITIES) + len(fx.UNRESOLVED)


def test_two_reads_of_one_graph_give_the_same_slice(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    write_fixture(driver, neo4j_settings.database)

    assert read_graph(driver, neo4j_settings.database) == read_graph(
        driver, neo4j_settings.database
    )


def test_an_empty_graph_reads_as_an_empty_slice(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    graph = read_graph(driver, neo4j_settings.database)

    assert graph.nodes == ()
    assert graph.links == ()
