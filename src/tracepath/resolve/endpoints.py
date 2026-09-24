"""Turning relationship endpoints into things the graph can point at (AC-7, AC-10).

A local endpoint already carries a canonical id. A reference is resolved once the whole
corpus is loaded: `record` plus `id` names an entity; `record` plus `label`, with `id`
null, names the entity in that record whose own `label` matches once both are
normalized; `record` alone, with `id` and `label` both null, names a Record; and
anything that names nothing becomes an `:Unresolved` node carrying the verbatim mention
(and the `record`/`label` it named, when it named them). No relationship is dropped for
having an endpoint that cannot be named.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from tracepath.extract.ids import IdentifiedEntity
from tracepath.extract.schema import (
    ExtractedRelationship,
    LocalEndpoint,
    ReferenceEndpoint,
    RelationshipType,
    normalize_label,
)

#: Whitespace and punctuation runs, for the slug an unresolved node is keyed by.
NOT_SLUG = re.compile(r"[^a-z0-9]+")

#: `(record, normalized label)` to the one entity that carries it (AC-7).
LabelIndex = Mapping[tuple[str, str], str]


class Target(StrEnum):
    """What kind of node an endpoint ended up pointing at."""

    ENTITY = "Entity"
    RECORD = "Record"
    UNRESOLVED = "Unresolved"


@dataclass(frozen=True)
class UnresolvedNode:
    """A reference the code could not name, kept as a node so the gap is visible.

    `record` and `label` hold what the reference named, when it named them, distinct
    from `source_record` (the record whose text *made* the reference). A later pass can
    retry the match from these two fields directly, without re-parsing `mention` (AC-10).
    """

    canonical_id: str
    mention: str
    source_record: str
    file: str
    section: str
    line: int | None
    record: str | None = None
    label: str | None = None


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


def build_label_index(entities: Iterable[IdentifiedEntity]) -> LabelIndex:
    """Map `(record, normalized label)` to the one entity that carries it (AC-7).

    A struck entity is excluded: a reference to a label should not land on a version
    AC-5 has already marked superseded, the "current, not history" reading key
    invariant 7 already gives every other lookup. A label more than one unstruck entity
    in a record shares is excluded too, not picked; the caller falls through to
    `:Unresolved` rather than guessing which one, the same standard AC-11b already holds
    a differing count to. The record is read off the entity's own `canonical_id`
    (`<record>/<id>` or `<record>#<slug>:<n>`, AC-3), so the caller need not pair it up.
    """
    candidates: dict[tuple[str, str], set[str]] = {}
    for entity in entities:
        if entity.entity.label is None or entity.struck:
            continue
        record = entity.canonical_id.split("/", 1)[0].split("#", 1)[0]
        key = (record, normalize_label(entity.entity.label))
        candidates.setdefault(key, set()).add(entity.canonical_id)
    return {key: next(iter(ids)) for key, ids in candidates.items() if len(ids) == 1}


def _resolve_one(
    endpoint: LocalEndpoint | ReferenceEndpoint,
    context: LinkContext,
    known_entities: frozenset[str],
    known_records: frozenset[str],
    label_index: LabelIndex,
    gaps: dict[str, UnresolvedNode],
) -> ResolvedEndpoint:
    if isinstance(endpoint, LocalEndpoint):
        return ResolvedEndpoint(canonical_id=endpoint.id, target=Target.ENTITY)

    if endpoint.record is not None and endpoint.id is not None:
        qualified = f"{endpoint.record}/{endpoint.id}"
        if qualified in known_entities:
            return ResolvedEndpoint(canonical_id=qualified, target=Target.ENTITY)
    if endpoint.record is not None and endpoint.id is None and endpoint.label is not None:
        matched = label_index.get((endpoint.record, normalize_label(endpoint.label)))
        if matched is not None and matched in known_entities:
            return ResolvedEndpoint(canonical_id=matched, target=Target.ENTITY)
    if (
        endpoint.record is not None
        and endpoint.id is None
        and endpoint.label is None
        and endpoint.record in known_records
    ):
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
            record=endpoint.record,
            label=endpoint.label,
        ),
    )
    return ResolvedEndpoint(canonical_id=canonical, target=Target.UNRESOLVED)


def resolve_endpoints(
    relationships: Iterable[tuple[ExtractedRelationship, LinkContext]],
    known_entities: frozenset[str],
    known_records: frozenset[str],
    label_index: LabelIndex,
) -> Resolution:
    """Resolve every accepted relationship's endpoints against the whole corpus.

    An endpoint that names nothing becomes an `:Unresolved` node rather than a dropped
    link, so a chain shows the gap instead of breaking quietly or inventing a target.
    `label_index` is built over every **known** entity (identified, not necessarily
    accepted); a match only resolves here when it also lands in `known_entities`, which
    at this point is the accepted set (AC-11c), so a label match to an entity that
    exists but was held never reaches this function at all, it is held before
    resolution the same way a `{record, id}` match already is.
    """
    gaps: dict[str, UnresolvedNode] = {}
    links: list[ResolvedLink] = []
    for relationship, context in relationships:
        links.append(
            ResolvedLink(
                type=relationship.type,
                source=_resolve_one(
                    relationship.source, context, known_entities, known_records, label_index, gaps
                ),
                target=_resolve_one(
                    relationship.target, context, known_entities, known_records, label_index, gaps
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
