"""Turning relationship endpoints into things the graph can point at (AC-7, AC-10).

A local endpoint already carries a canonical id. A reference is resolved once the whole
corpus is loaded: `record` plus `id` names an entity, `record` alone names a Record, and
anything that names nothing becomes an `:Unresolved` node carrying the verbatim mention.
No relationship is dropped for having an endpoint that cannot be named.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from tracepath.extract.schema import (
    ExtractedRelationship,
    LocalEndpoint,
    ReferenceEndpoint,
    RelationshipType,
)

#: Whitespace and punctuation runs, for the slug an unresolved node is keyed by.
NOT_SLUG = re.compile(r"[^a-z0-9]+")


class Target(StrEnum):
    """What kind of node an endpoint ended up pointing at."""

    ENTITY = "Entity"
    RECORD = "Record"
    UNRESOLVED = "Unresolved"


@dataclass(frozen=True)
class UnresolvedNode:
    """A reference the code could not name, kept as a node so the gap is visible."""

    canonical_id: str
    mention: str
    source_record: str
    file: str
    section: str
    line: int | None


@dataclass(frozen=True)
class ResolvedEndpoint:
    """One endpoint, resolved to the canonical id of whatever it points at."""

    canonical_id: str
    target: Target


@dataclass(frozen=True)
class ResolvedLink:
    """One relationship with both endpoints resolved, ready for the graph."""

    type: RelationshipType
    source: ResolvedEndpoint
    target: ResolvedEndpoint
    phrase: str | None
    date: str | None
    source_record: str
    file: str
    section: str
    line: int | None


@dataclass(frozen=True)
class LinkContext:
    """Where a relationship was written, which its citation and any gap node carry."""

    source_record: str
    file: str
    section: str
    line: int | None


@dataclass(frozen=True)
class Resolution:
    """Every link resolved, and every gap node the resolution had to create."""

    links: tuple[ResolvedLink, ...]
    unresolved: tuple[UnresolvedNode, ...]


def slugify_mention(mention: str) -> str:
    """The slug an unresolved node is keyed by, from the verbatim mention."""
    return NOT_SLUG.sub("-", mention.lower()).strip("-")


def unresolved_id(source_record: str, mention: str) -> str:
    """The canonical id of an unresolved node.

    Scoped to the source record on purpose: the same words can mean different things
    in different documents.
    """
    return f"unresolved:{source_record}:{slugify_mention(mention)}"


def _resolve_one(
    endpoint: LocalEndpoint | ReferenceEndpoint,
    context: LinkContext,
    known_entities: frozenset[str],
    known_records: frozenset[str],
    gaps: dict[str, UnresolvedNode],
) -> ResolvedEndpoint:
    if isinstance(endpoint, LocalEndpoint):
        return ResolvedEndpoint(canonical_id=endpoint.id, target=Target.ENTITY)

    if endpoint.record is not None and endpoint.id is not None:
        qualified = f"{endpoint.record}/{endpoint.id}"
        if qualified in known_entities:
            return ResolvedEndpoint(canonical_id=qualified, target=Target.ENTITY)
    if endpoint.record is not None and endpoint.id is None and endpoint.record in known_records:
        return ResolvedEndpoint(canonical_id=endpoint.record, target=Target.RECORD)

    canonical = unresolved_id(context.source_record, endpoint.mention)
    gaps.setdefault(
        canonical,
        UnresolvedNode(
            canonical_id=canonical,
            mention=endpoint.mention,
            source_record=context.source_record,
            file=context.file,
            section=context.section,
            line=context.line,
        ),
    )
    return ResolvedEndpoint(canonical_id=canonical, target=Target.UNRESOLVED)


def resolve_endpoints(
    relationships: Iterable[tuple[ExtractedRelationship, LinkContext]],
    known_entities: frozenset[str],
    known_records: frozenset[str],
) -> Resolution:
    """Resolve every accepted relationship's endpoints against the whole corpus.

    An endpoint that names nothing becomes an `:Unresolved` node rather than a dropped
    link, so a chain shows the gap instead of breaking quietly or inventing a target.
    """
    gaps: dict[str, UnresolvedNode] = {}
    links: list[ResolvedLink] = []
    for relationship, context in relationships:
        links.append(
            ResolvedLink(
                type=relationship.type,
                source=_resolve_one(
                    relationship.source, context, known_entities, known_records, gaps
                ),
                target=_resolve_one(
                    relationship.target, context, known_entities, known_records, gaps
                ),
                phrase=relationship.phrase,
                date=relationship.date,
                source_record=context.source_record,
                file=context.file,
                section=context.section,
                line=context.line,
            )
        )
    return Resolution(links=tuple(links), unresolved=tuple(gaps.values()))
