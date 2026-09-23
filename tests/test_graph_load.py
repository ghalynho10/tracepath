from collections.abc import Iterator

import pytest
from neo4j import Driver

from tracepath.config import Neo4jSettings
from tracepath.extract.schema import EntityType, RelationshipType
from tracepath.graph import connect
from tracepath.graph.load import (
    GraphWriteFailed,
    write_entities,
    write_links,
    write_part_of,
    write_records,
    write_specified_by,
    write_unresolved,
)
from tracepath.graph.schema import CONSTRAINTS, clear, constraint_names, create_constraints

pytestmark = pytest.mark.integration


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        clear(opened, neo4j_settings.database)
        create_constraints(opened, neo4j_settings.database)
        yield opened
        clear(opened, neo4j_settings.database)


def record_row(canonical_id: str, kind: str = "spec") -> dict[str, object]:
    return {
        "canonical_id": canonical_id,
        "kind": kind,
        "title": f"Record {canonical_id}",
        "path": f"specs/{canonical_id}/index.md",
        "commit": "2e40bcf",
        "aliases": [canonical_id],
    }


def entity_row(canonical_id: str, entity_type: str = "AcceptanceCriterion") -> dict[str, object]:
    return {
        "canonical_id": canonical_id,
        "type": entity_type,
        "text": "the criterion text",
        "rationale": [],
        "flags": [],
        "id_source": "verbatim",
        "struck": False,
        "file": "specs/0012/index.md",
        "section": "Requirements",
        "line": 12,
        "commit": "2e40bcf",
        "model": "claude-sonnet-5",
        "prompt_version": "1",
        "extracted_at": "2026-09-22T00:00:00Z",
        "accepted_by": "auto",
    }


# AC-9: one uniqueness constraint per node kind, and a rebuild is idempotent.


def test_every_constraint_is_created_and_creating_them_again_adds_nothing(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    names = constraint_names(driver, neo4j_settings.database)
    assert {"entity_canonical_id_unique", "record_canonical_id_unique"} <= names

    added_again = create_constraints(driver, neo4j_settings.database)

    assert added_again == ()
    assert len(CONSTRAINTS) == 3


def test_the_database_itself_refuses_a_second_entity_with_the_same_id(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    write_entities(
        driver,
        neo4j_settings.database,
        {EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1")]},
    )

    # A second node with the same id under a different type label must not exist.
    records, _, _ = driver.execute_query(
        "MATCH (e:Entity {canonical_id: $id}) RETURN count(e) AS n",
        id="0012/AC-1",
        database_=neo4j_settings.database,
    )
    assert records[0]["n"] == 1

    with pytest.raises(Exception, match=r"already exists|ConstraintValidationFailed"):
        driver.execute_query(
            "CREATE (e:Entity {canonical_id: $id})",
            id="0012/AC-1",
            database_=neo4j_settings.database,
        )


def test_an_entity_carries_the_shared_label_plus_exactly_one_type_label(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    write_entities(
        driver,
        neo4j_settings.database,
        {
            EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1")],
            EntityType.BUILD_STEP: [entity_row("0012#build-plan:1", "BuildStep")],
        },
    )

    records, _, _ = driver.execute_query(
        "MATCH (e:Entity) RETURN e.canonical_id AS id, labels(e) AS labels ORDER BY id",
        database_=neo4j_settings.database,
    )

    by_id = {r["id"]: sorted(r["labels"]) for r in records}
    assert by_id["0012/AC-1"] == ["AcceptanceCriterion", "Entity"]
    assert by_id["0012#build-plan:1"] == ["BuildStep", "Entity"]


def test_every_entity_is_part_of_exactly_one_record(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    write_records(driver, database, [record_row("0012")])
    write_entities(driver, database, {EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1")]})

    written = write_part_of(driver, database, [{"from_id": "0012/AC-1", "to_id": "0012"}])

    assert written == 1
    records, _, _ = driver.execute_query(
        "MATCH (e:Entity)-[:PART_OF]->(r:Record) RETURN count(r) AS n", database_=database
    )
    assert records[0]["n"] == 1


def test_a_feature_row_links_to_the_spec_its_pointer_line_cites(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    write_records(driver, database, [record_row("feature-21", "scope_feature"), record_row("0009")])

    written = write_specified_by(
        driver, database, [{"from_id": "feature-21", "to_id": "0009", "source_line": 182}]
    )

    assert written == 1
    records, _, _ = driver.execute_query(
        "MATCH (:Record {canonical_id: 'feature-21'})-[rel:SPECIFIED_BY]->(s:Record) "
        "RETURN s.canonical_id AS spec, rel.source_line AS line",
        database_=database,
    )
    assert records[0]["spec"] == "0009"
    assert records[0]["line"] == 182


# AC-13: every write asserts its own result and raises on a mismatch.


def test_a_link_whose_endpoint_is_missing_raises_instead_of_writing_nothing(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    write_entities(driver, database, {EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1")]})

    with pytest.raises(GraphWriteFailed, match="PART_OF"):
        write_part_of(driver, database, [{"from_id": "0012/AC-1", "to_id": "0099"}])


def test_a_missing_endpoint_creates_no_phantom_node(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    write_entities(driver, database, {EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1")]})

    with pytest.raises(GraphWriteFailed):
        write_part_of(driver, database, [{"from_id": "0012/AC-1", "to_id": "0099"}])

    records, _, _ = driver.execute_query(
        "MATCH (n {canonical_id: '0099'}) RETURN count(n) AS n", database_=database
    )
    assert records[0]["n"] == 0


def test_a_partly_satisfiable_batch_raises_rather_than_writing_the_half_that_matched(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    write_records(driver, database, [record_row("0012")])
    write_entities(
        driver,
        database,
        {
            EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1"), entity_row("0012/AC-2")],
        },
    )

    with pytest.raises(GraphWriteFailed, match="asked to write 2"):
        write_part_of(
            driver,
            database,
            [{"from_id": "0012/AC-1", "to_id": "0012"}, {"from_id": "0012/AC-2", "to_id": "0099"}],
        )


def test_writing_the_same_rows_twice_leaves_one_node_and_one_link(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    for _ in range(2):
        write_records(driver, database, [record_row("0012")])
        write_entities(
            driver, database, {EntityType.ACCEPTANCE_CRITERION: [entity_row("0012/AC-1")]}
        )
        write_part_of(driver, database, [{"from_id": "0012/AC-1", "to_id": "0012"}])

    records, _, _ = driver.execute_query("MATCH (n) RETURN count(n) AS nodes", database_=database)
    links, _, _ = driver.execute_query(
        "MATCH ()-[r:PART_OF]->() RETURN count(r) AS links", database_=database
    )
    assert records[0]["nodes"] == 2
    assert links[0]["links"] == 1


# AC-8 and AC-10: history points old to new, and an unresolved endpoint is a real node.


def test_a_history_link_is_stored_old_to_new(driver: Driver, neo4j_settings: Neo4jSettings) -> None:
    database = neo4j_settings.database
    write_entities(
        driver,
        database,
        {
            EntityType.ACCEPTANCE_CRITERION: [
                entity_row("0021#requirements:1"),
                entity_row("0021/AC-2"),
            ]
        },
    )

    write_links(
        driver,
        database,
        {
            RelationshipType.SUPERSEDED_BY: [
                {
                    "from_id": "0021#requirements:1",
                    "to_id": "0021/AC-2",
                    "properties": {"phrase": "SUPERSEDED 2026-09-14"},
                }
            ]
        },
    )

    records, _, _ = driver.execute_query(
        "MATCH (old)-[:SUPERSEDED_BY]->(new) "
        "WHERE NOT (new)-[:SUPERSEDED_BY]->() "
        "RETURN old.canonical_id AS old, new.canonical_id AS new",
        database_=database,
    )
    assert records[0]["old"] == "0021#requirements:1"
    assert records[0]["new"] == "0021/AC-2"


def test_a_link_may_end_on_an_unresolved_node_carrying_its_verbatim_mention(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    write_entities(driver, database, {EntityType.ACCEPTANCE_CRITERION: [entity_row("0008/AC-1")]})
    write_unresolved(
        driver,
        database,
        [
            {
                "canonical_id": "unresolved:0008:binding-rule-6",
                "mention": "spec 0001's binding rule 6",
                "source_record": "0008",
                "file": "specs/0008/index.md",
                "section": "Preamble",
            }
        ],
    )

    written = write_links(
        driver,
        database,
        {
            RelationshipType.UNCLASSIFIED: [
                {
                    "from_id": "0008/AC-1",
                    "to_id": "unresolved:0008:binding-rule-6",
                    "properties": {"phrase": "gains a third item"},
                }
            ]
        },
    )

    assert written == 1
    records, _, _ = driver.execute_query(
        "MATCH (:Entity)-[rel:UNCLASSIFIED]->(u:Unresolved) "
        "RETURN u.mention AS mention, rel.phrase AS phrase",
        database_=database,
    )
    assert records[0]["mention"] == "spec 0001's binding rule 6"
    assert records[0]["phrase"] == "gains a third item"


def test_an_unlocated_line_is_absent_rather_than_stored_as_a_guess(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    row = entity_row("0012/AC-1")
    del row["line"]

    write_entities(driver, database, {EntityType.ACCEPTANCE_CRITERION: [row]})

    records, _, _ = driver.execute_query(
        "MATCH (e:Entity {canonical_id: '0012/AC-1'}) RETURN e.line AS line", database_=database
    )
    assert records[0]["line"] is None
