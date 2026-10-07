"""Reading the graph back as the slice a walk runs over (spec 0004 build plan step 4).

One deterministic read: every Entity, Record and Unresolved node, and every link of the
seven typed relationship types, each in a fixed order. `PART_OF` is never read, so the
walk cannot follow it. Nothing here names the eval set or any one question (AC-31).
"""

from typing import Any

from neo4j import Driver, RoutingControl

from tracepath.graph.load import LINK_TYPES
from tracepath.traverse.graph_slice import (
    GraphSlice,
    graph_slice,
    link_from_properties,
    node_from_properties,
)

#: The whole read, in one statement. The first part collects the nodes in id order; the
#: `OPTIONAL MATCH` keeps the one row alive when the graph holds no typed link, and
#: `collect` drops its null.
READ_SLICE = (
    "MATCH (n) WHERE n:Entity OR n:Record OR n:Unresolved "
    "WITH n ORDER BY n.canonical_id "
    "WITH collect({labels: labels(n), properties: properties(n)}) AS nodes "
    "OPTIONAL MATCH (a)-[r]->(b) WHERE type(r) IN $types "
    "WITH nodes, a, r, b ORDER BY type(r), a.canonical_id, b.canonical_id "
    "RETURN nodes, collect(CASE WHEN r IS NULL THEN null ELSE "
    "{type: type(r), source: a.canonical_id, target: b.canonical_id, "
    "properties: properties(r)} END) AS links"
)


def read_graph(driver: Driver, database: str, *, with_held: bool = False) -> GraphSlice:
    """Every node and typed link the graph holds, as an immutable slice.

    Held items are dropped unless `with_held` is set; the Cypher read is the same
    either way, and `graph_slice()` decides (spec 0005).

    Raises:
        SliceError: a node read back has no canonical id or no known label.
    """
    records, _, _ = driver.execute_query(
        READ_SLICE,
        types=sorted(LINK_TYPES.values()),
        database_=database,
        routing_=RoutingControl.READ,
    )
    if not records:
        return graph_slice((), (), with_held=with_held)
    row: dict[str, Any] = records[0].data()
    nodes = (node_from_properties(n["labels"], n["properties"]) for n in row["nodes"])
    links = (
        link_from_properties(k["type"], k["source"], k["target"], k["properties"])
        for k in row["links"]
    )
    return graph_slice(nodes, links, with_held=with_held)
