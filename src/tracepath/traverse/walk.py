"""The walk: breadth first from one item, along typed links, under fixed rules.

Spec 0004 AC-20 to AC-27. The rules are stated without reference to any eval question:
both directions, the seven typed relationship types, never `PART_OF`, at most three
hops, Record and Unresolved nodes printed and never expanded, each node visited once by
the first path to it, and neighbours taken in one fixed order. The struck flag is
carried as stored and changes nothing about what is followed.
"""

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from tracepath.traverse.graph_slice import TYPED_LINKS, GraphSlice, Link, Node, NodeKind

#: How far from the start the walk goes (AC-23).
MAX_HOPS = 3


class StartNotInGraph(Exception):
    """The start id names nothing the graph holds."""


class Direction(StrEnum):
    """Which way the link that reached a step points, seen from the step it came from."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"


class Stop(StrEnum):
    """Why the walk did not go on from a step."""

    RECORD = "whole document, not expanded"
    UNRESOLVED = "unresolved, not expanded"
    DEPTH_LIMIT = "depth limit"


@dataclass(frozen=True)
class Step:
    """One visited node: how far out, by which link and from which step it was reached.

    `unfollowed` counts the typed links at a depth limit step whose other end was never
    visited, so the output can say what lies past the limit (AC-23).
    """

    hop: int
    node: Node
    via: Link | None
    direction: Direction | None
    parent: str | None
    stop: Stop | None
    unfollowed: int = 0


@dataclass(frozen=True)
class Chain:
    """Every step of one walk, in the order the walk visited them, the start first."""

    start: str
    max_hops: int
    steps: tuple[Step, ...]


#: A neighbour of one node: the link, which way it points, and the node at its far end.
Neighbour = tuple[Link, Direction, str]


def _neighbours(graph: GraphSlice) -> dict[str, tuple[Neighbour, ...]]:
    """Each node's typed links, in the fixed order of AC-26.

    Relationship type name, then outgoing before incoming, then the other node's
    canonical id, all lexical. After AC-16's collapse a type, a direction and the other
    node are unique, so no tie remains to break.
    """
    held = {node.canonical_id for node in graph.nodes}
    found: dict[str, list[Neighbour]] = {}
    for link in graph.links:
        # `PART_OF`, and any other untyped link, is never followed (AC-22).
        if link.type not in TYPED_LINKS:
            continue
        if link.source not in held or link.target not in held:
            continue
        found.setdefault(link.source, []).append((link, Direction.OUTGOING, link.target))
        found.setdefault(link.target, []).append((link, Direction.INCOMING, link.source))
    order = {Direction.OUTGOING: 0, Direction.INCOMING: 1}
    return {
        node: tuple(sorted(links, key=lambda n: (n[0].type, order[n[1]], n[2])))
        for node, links in found.items()
    }


def _terminal(node: Node) -> Stop | None:
    """The stop a node's own kind imposes: a Record or Unresolved node is never expanded."""
    if node.kind is NodeKind.RECORD:
        return Stop.RECORD
    if node.kind is NodeKind.UNRESOLVED:
        return Stop.UNRESOLVED
    return None


def walk(graph: GraphSlice, start: str, max_hops: int = MAX_HOPS) -> Chain:
    """Walk breadth first from `start` and return every step, in the order visited.

    The queue order is the parent order, and a node is visited once, by the first path
    to it, so a cycle ends (AC-25).

    Raises:
        StartNotInGraph: `start` is not a node of the slice (AC-20).
    """
    nodes = {node.canonical_id: node for node in graph.nodes}
    if start not in nodes:
        raise StartNotInGraph(
            f"{start} is not in the graph. An entity held for review is not in the graph."
        )
    neighbours = _neighbours(graph)

    reached: dict[str, tuple[int, Link | None, Direction | None, str | None]] = {
        start: (0, None, None, None)
    }
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        hop = reached[current][0]
        if _terminal(nodes[current]) is not None or hop >= max_hops:
            continue
        for link, direction, other in neighbours.get(current, ()):
            if other in reached:
                continue
            reached[other] = (hop + 1, link, direction, current)
            queue.append(other)

    steps: list[Step] = []
    for canonical_id, (hop, via, way, parent) in reached.items():
        node = nodes[canonical_id]
        stop = _terminal(node)
        unfollowed = 0
        if stop is None and hop >= max_hops:
            unfollowed = sum(
                1 for _, _, other in neighbours.get(canonical_id, ()) if other not in reached
            )
            stop = Stop.DEPTH_LIMIT if unfollowed else None
        steps.append(Step(hop, node, via, way, parent, stop, unfollowed))
    return Chain(start=start, max_hops=max_hops, steps=tuple(steps))
