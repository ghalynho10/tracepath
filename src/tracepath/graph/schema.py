"""The graph's own shape: one uniqueness constraint per node kind (AC-9, AC-13).

Neo4j Community enforces uniqueness and nothing else. Existence, property type and key
constraints are Enterprise features, so every other guarantee rests on the loader's own
assertions. Every statement here uses `IF NOT EXISTS`, so a rebuild is idempotent.
"""

from neo4j import Driver

#: One uniqueness constraint per node kind. The entity constraint is on the shared
#: `:Entity` label rather than per type label, so one canonical id cannot exist twice
#: under two different types (spec 0001, as amended by spec 0002).
CONSTRAINTS = (
    "CREATE CONSTRAINT entity_canonical_id_unique IF NOT EXISTS "
    "FOR (n:Entity) REQUIRE n.canonical_id IS UNIQUE",
    "CREATE CONSTRAINT record_canonical_id_unique IF NOT EXISTS "
    "FOR (n:Record) REQUIRE n.canonical_id IS UNIQUE",
    "CREATE CONSTRAINT unresolved_canonical_id_unique IF NOT EXISTS "
    "FOR (n:Unresolved) REQUIRE n.canonical_id IS UNIQUE",
)

#: The label every entity carries besides its own type label.
ENTITY_LABEL = "Entity"


def create_constraints(driver: Driver, database: str) -> tuple[str, ...]:
    """Create every constraint, and return the names of the ones this call added."""
    added: list[str] = []
    for statement in CONSTRAINTS:
        summary = driver.execute_query(statement, database_=database).summary
        if summary.counters.constraints_added:
            added.append(statement.split()[2])
    return tuple(added)


def constraint_names(driver: Driver, database: str) -> frozenset[str]:
    """The names of the constraints the database currently holds."""
    records, _, _ = driver.execute_query(
        "SHOW CONSTRAINTS YIELD name RETURN name", database_=database
    )
    return frozenset(str(record["name"]) for record in records)


def clear(driver: Driver, database: str) -> int:
    """Delete every node and relationship, and return how many nodes went.

    The graph is derived and rebuildable from the run artifacts, so a rebuild starts
    from empty rather than trying to reconcile.
    """
    summary = driver.execute_query("MATCH (n) DETACH DELETE n", database_=database).summary
    return int(summary.counters.nodes_deleted)
