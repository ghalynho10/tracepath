"""Writing the resolved graph, with every write asserting its own result (AC-13).

Neo4j has no foreign keys. A relationship write whose pattern does not match both
endpoints writes nothing at all, and says so only in its counters, so every statement
here checks what it actually did and raises rather than returning quietly.

Cypher 5 has no dynamic labels or relationship types, so each entity type and each
relationship type is written by its own statement, built from the closed enums. Nothing
from the corpus is ever interpolated into a query; every value travels as a parameter.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from neo4j import Driver

from tracepath.extract.schema import EntityType, RelationshipType
from tracepath.resolve.endpoints import ResolvedLink

#: The label each entity carries besides `:Entity`, one per type in the closed set.
TYPE_LABELS = {
    EntityType.FEATURE: "Feature",
    EntityType.CONSTRAINT: "Constraint",
    EntityType.ACCEPTANCE_CRITERION: "AcceptanceCriterion",
    EntityType.CONSEQUENCE: "Consequence",
    EntityType.FOLLOW_UP: "FollowUp",
    EntityType.BUILD_STEP: "BuildStep",
    EntityType.TEST_SCENARIO: "TestScenario",
    EntityType.UNCLASSIFIED: "Unclassified",
}

#: The relationship type each link type is written as, one per type in the closed set.
LINK_TYPES = {
    RelationshipType.SUPERSEDED_BY: "SUPERSEDED_BY",
    RelationshipType.CORRECTED_BY: "CORRECTED_BY",
    RelationshipType.AMENDED_BY: "AMENDED_BY",
    RelationshipType.BLOCKED_BY: "BLOCKED_BY",
    RelationshipType.VERIFIES: "VERIFIES",
    RelationshipType.SATISFIES: "SATISFIES",
    RelationshipType.UNCLASSIFIED: "UNCLASSIFIED",
}


class GraphWriteFailed(Exception):
    """A write did not do what it was asked to do."""


@dataclass(frozen=True)
class WriteCounts:
    """What one load actually wrote."""

    records: int
    entities: int
    unresolved: int
    part_of: int
    specified_by: int
    links: int


def _write(
    driver: Driver, database: str, statement: str, rows: Sequence[dict[str, Any]], what: str
) -> int:
    """Run one batched write and assert it touched every row it was given.

    Raises:
        GraphWriteFailed: the statement reported fewer written rows than it was given.
    """
    if not rows:
        return 0
    records, _, _ = driver.execute_query(statement, rows=list(rows), database_=database)
    written = int(records[0]["written"]) if records else 0
    if written != len(rows):
        raise GraphWriteFailed(
            f"{what}: asked to write {len(rows)} but the database wrote {written}. "
            "An endpoint the pattern needs is missing, so nothing was written for it."
        )
    return written


def write_records(driver: Driver, database: str, rows: Sequence[dict[str, Any]]) -> int:
    """Upsert every `:Record` node."""
    return _write(
        driver,
        database,
        "UNWIND $rows AS row "
        "MERGE (r:Record {canonical_id: row.canonical_id}) "
        "SET r += row "
        "RETURN count(r) AS written",
        rows,
        "records",
    )


def write_unresolved(driver: Driver, database: str, rows: Sequence[dict[str, Any]]) -> int:
    """Upsert every `:Unresolved` node."""
    return _write(
        driver,
        database,
        "UNWIND $rows AS row "
        "MERGE (u:Unresolved {canonical_id: row.canonical_id}) "
        "SET u += row "
        "RETURN count(u) AS written",
        rows,
        "unresolved nodes",
    )


def write_entities(
    driver: Driver, database: str, rows_by_type: dict[EntityType, Sequence[dict[str, Any]]]
) -> int:
    """Upsert entities, one statement per type, since Cypher 5 has no dynamic labels."""
    written = 0
    for entity_type, rows in rows_by_type.items():
        label = TYPE_LABELS[entity_type]
        written += _write(
            driver,
            database,
            "UNWIND $rows AS row "
            "MERGE (e:Entity {canonical_id: row.canonical_id}) "
            "SET e += row "
            f"SET e:{label} "
            "RETURN count(e) AS written",
            rows,
            f"{label} entities",
        )
    return written


def write_part_of(driver: Driver, database: str, rows: Sequence[dict[str, Any]]) -> int:
    """Link every entity to the one record it belongs to.

    Both endpoints are matched, never merged, so a missing record fails the write
    instead of quietly creating a phantom node to hang the entity from.
    """
    return _write(
        driver,
        database,
        "UNWIND $rows AS row "
        "MATCH (e:Entity {canonical_id: row.from_id}) "
        "MATCH (r:Record {canonical_id: row.to_id}) "
        "MERGE (e)-[:PART_OF]->(r) "
        "RETURN count(*) AS written",
        rows,
        "PART_OF links",
    )


def write_feature_part_of(driver: Driver, database: str, rows: Sequence[dict[str, Any]]) -> int:
    """Link every feature row record to the scope document it sits in."""
    return _write(
        driver,
        database,
        "UNWIND $rows AS row "
        "MATCH (f:Record {canonical_id: row.from_id}) "
        "MATCH (d:Record {canonical_id: row.to_id}) "
        "MERGE (f)-[:PART_OF]->(d) "
        "RETURN count(*) AS written",
        rows,
        "feature PART_OF links",
    )


def write_specified_by(driver: Driver, database: str, rows: Sequence[dict[str, Any]]) -> int:
    """Link every feature row to the spec its own pointer line cites."""
    return _write(
        driver,
        database,
        "UNWIND $rows AS row "
        "MATCH (f:Record {canonical_id: row.from_id}) "
        "MATCH (s:Record {canonical_id: row.to_id}) "
        "MERGE (f)-[rel:SPECIFIED_BY]->(s) "
        "SET rel.source_line = row.source_line "
        "RETURN count(rel) AS written",
        rows,
        "SPECIFIED_BY links",
    )


def write_links(
    driver: Driver, database: str, rows_by_type: dict[RelationshipType, Sequence[dict[str, Any]]]
) -> int:
    """Write the typed relationships, one statement per type.

    An endpoint may be an Entity, a Record or an Unresolved node, so the pattern
    matches on the shared `canonical_id` without demanding a label.
    """
    written = 0
    for link_type, rows in rows_by_type.items():
        name = LINK_TYPES[link_type]
        written += _write(
            driver,
            database,
            "UNWIND $rows AS row "
            "MATCH (a) WHERE a.canonical_id = row.from_id "
            "MATCH (b) WHERE b.canonical_id = row.to_id "
            f"MERGE (a)-[rel:{name}]->(b) "
            "SET rel += row.properties "
            "RETURN count(rel) AS written",
            rows,
            f"{name} links",
        )
    return written


def by_link_type(links: Sequence[ResolvedLink]) -> dict[RelationshipType, list[ResolvedLink]]:
    """Group resolved links by type, so each type gets its own statement."""
    grouped: dict[RelationshipType, list[ResolvedLink]] = {}
    for link in links:
        grouped.setdefault(link.type, []).append(link)
    return grouped
