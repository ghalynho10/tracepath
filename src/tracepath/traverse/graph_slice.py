"""The immutable slice of the graph a walk runs over: nodes and typed links, as read.

Built from plain property maps, so the Cypher read and a hand built test fixture make
it the same way. Nothing here knows about Neo4j, the eval set, or any one question.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from tracepath.extract.schema import RelationshipType

#: The seven typed relationship types a walk may follow (spec 0004 AC-21), by the name
#: the graph stores them under. `PART_OF` and `SPECIFIED_BY` are not among them.
TYPED_LINKS = frozenset(link_type.name for link_type in RelationshipType)


class NodeKind(StrEnum):
    """The three kinds of node a chain can pass through."""

    ENTITY = "Entity"
    RECORD = "Record"
    UNRESOLVED = "Unresolved"


class SliceError(Exception):
    """A node or link read back from the graph lacks what a chain step must print."""


@dataclass(frozen=True)
class Node:
    """One node and the properties a chain step prints. Absent properties are `None`."""

    canonical_id: str
    kind: NodeKind
    type: str | None = None
    text: str | None = None
    struck: bool | None = None
    file: str | None = None
    section: str | None = None
    line: int | None = None
    file_line: int | None = None
    commit: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    title: str | None = None
    path: str | None = None
    mention: str | None = None
    record: str | None = None


@dataclass(frozen=True)
class Link:
    """One typed relationship, `source` to `target` as stored, with its own citation."""

    type: str
    source: str
    target: str
    phrase: str | None = None
    file: str | None = None
    section: str | None = None
    line: int | None = None
    commit: str | None = None
    prompt_version: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class GraphSlice:
    """Every node and every typed link the walk may use, in a fixed order."""

    nodes: tuple[Node, ...]
    links: tuple[Link, ...]


def _text(properties: Mapping[str, object], key: str) -> str | None:
    value = properties.get(key)
    return value if isinstance(value, str) else None


def _number(properties: Mapping[str, object], key: str) -> int | None:
    value = properties.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _flag(properties: Mapping[str, object], key: str) -> bool | None:
    value = properties.get(key)
    return value if isinstance(value, bool) else None


def node_from_properties(labels: Iterable[str], properties: Mapping[str, object]) -> Node:
    """One node from its labels and stored properties.

    Raises:
        SliceError: the node has no canonical id, or none of the three node labels.
    """
    canonical_id = _text(properties, "canonical_id")
    if canonical_id is None:
        raise SliceError(f"a node with labels {sorted(labels)} has no canonical_id")
    held = set(labels)
    kind = next((k for k in NodeKind if k.value in held), None)
    if kind is None:
        raise SliceError(f"{canonical_id} is not an Entity, a Record or an Unresolved node")
    return Node(
        canonical_id=canonical_id,
        kind=kind,
        type=_text(properties, "type"),
        text=_text(properties, "text"),
        struck=_flag(properties, "struck"),
        file=_text(properties, "file"),
        section=_text(properties, "section"),
        line=_number(properties, "line"),
        file_line=_number(properties, "file_line"),
        commit=_text(properties, "commit"),
        prompt_version=_text(properties, "prompt_version"),
        model=_text(properties, "model"),
        title=_text(properties, "title"),
        path=_text(properties, "path"),
        mention=_text(properties, "mention"),
        record=_text(properties, "record"),
    )


def link_from_properties(
    link_type: str, source: str, target: str, properties: Mapping[str, object]
) -> Link:
    """One typed link from its type, its two endpoint ids and its stored properties."""
    return Link(
        type=link_type,
        source=source,
        target=target,
        phrase=_text(properties, "phrase"),
        file=_text(properties, "file"),
        section=_text(properties, "section"),
        line=_number(properties, "line"),
        commit=_text(properties, "commit"),
        prompt_version=_text(properties, "prompt_version"),
        model=_text(properties, "model"),
    )


def graph_slice(nodes: Iterable[Node], links: Iterable[Link]) -> GraphSlice:
    """A slice in one fixed order: nodes by id, links by type, source and target.

    Only typed links are kept, so a `PART_OF` link handed in is dropped here and never
    reaches the walk (spec 0004 AC-22). The order does not depend on how the rows came
    back, so the same graph always makes the same slice.
    """
    return GraphSlice(
        nodes=tuple(sorted(nodes, key=lambda n: n.canonical_id)),
        links=tuple(
            sorted(
                (link for link in links if link.type in TYPED_LINKS),
                key=lambda k: (k.type, k.source, k.target),
            )
        ),
    )
