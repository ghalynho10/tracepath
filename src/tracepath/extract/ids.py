"""Assigning canonical ids. Code owns identity; the model never writes a final id.

A verbatim `AC-N` token is qualified by its record (`0008/AC-10b`). Everything else
gets a derived id, `<record>#<section-slug>:<n>`, numbered by where the span was
located in the unit so two runs of the same section produce the same ids (AC-3).
"""

import re
from dataclasses import dataclass

from tracepath.extract.locate import Location, locate_line, locate_verbatim
from tracepath.extract.precheck import (
    CheckboxItem,
    StruckRange,
    checkbox_status_at,
    is_struck,
    mark_struck,
    read_checkboxes,
)
from tracepath.extract.schema import (
    EntityType,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionOutput,
    FollowUpStatus,
    IdSource,
    LocalEndpoint,
)
from tracepath.extract.units import Unit


class IdAssignmentError(Exception):
    """An output cannot be given canonical ids as it stands."""


@dataclass(frozen=True)
class LocatedEntity:
    """One extracted entity with everything code, not the model, decided about it."""

    entity: ExtractedEntity
    location: Location | None
    struck: bool
    followup_status: FollowUpStatus | None
    order: int


@dataclass(frozen=True)
class LocatedOutput:
    """One validated output whose spans have been located and marked."""

    entities: tuple[LocatedEntity, ...]
    relationships: tuple[ExtractedRelationship, ...]


@dataclass(frozen=True)
class IdentifiedEntity:
    """One entity with its final canonical id."""

    canonical_id: str
    entity: ExtractedEntity
    location: Location | None
    struck: bool
    followup_status: FollowUpStatus | None


@dataclass(frozen=True)
class IdentifiedOutput:
    """One output with canonical ids on its entities and its local endpoints."""

    entities: tuple[IdentifiedEntity, ...]
    relationships: tuple[ExtractedRelationship, ...]


def slugify(text: str) -> str:
    """A section heading reduced to the slug a derived id carries."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def section_slugs(sections: tuple[str, ...]) -> tuple[str, ...]:
    """The slug of each section of one record, in file order, suffixing any repeat.

    A slug that repeats inside one record gets a numeric suffix, so `<record>#<slug>:<n>`
    still names exactly one section (AC-3). The result is positional rather than keyed
    by heading, because two sections of one record can carry the very same heading.
    """
    slugs: list[str] = []
    used: dict[str, int] = {}
    for section in sections:
        base = slugify(section)
        seen = used.get(base, 0)
        used[base] = seen + 1
        slugs.append(base if seen == 0 else f"{base}-{seen + 1}")
    return tuple(slugs)


def locate_output(unit: Unit, output: ExtractionOutput) -> LocatedOutput:
    """Locate every span and read the markers code owns, before ids are assigned.

    `locate_line()` runs here, so `assign_ids()` can number derived ids by where each
    span really sits in the unit.
    """
    struck_ranges: tuple[StruckRange, ...] = mark_struck(unit.text)
    checkboxes: tuple[CheckboxItem, ...] = read_checkboxes(unit.text)
    located: list[LocatedEntity] = []
    for order, entity in enumerate(output.entities):
        location = (
            locate_verbatim(unit, entity.id)
            if entity.id_source is IdSource.VERBATIM
            else locate_line(unit, entity.span)
        )
        if location is None and entity.id_source is IdSource.VERBATIM:
            location = locate_line(unit, entity.span)
        span_offset = _struck_probe(unit, entity, location)
        located.append(
            LocatedEntity(
                entity=entity,
                location=location,
                struck=is_struck(struck_ranges, span_offset),
                followup_status=(
                    checkbox_status_at(checkboxes, location.offset if location else None)
                    if entity.type is EntityType.FOLLOW_UP
                    else None
                ),
                order=order,
            )
        )
    return LocatedOutput(entities=tuple(located), relationships=output.relationships)


def _struck_probe(unit: Unit, entity: ExtractedEntity, location: Location | None) -> int | None:
    """Where to test for struck text.

    A verbatim entity is located at its definition bullet, which sits outside the
    `~~` markers, so the span itself is what decides whether it is struck.
    """
    span_location = locate_line(unit, entity.span)
    if span_location is not None:
        return span_location.offset
    return location.offset if location else None


def _ordering_key(located: LocatedEntity) -> tuple[int, int, int]:
    """Located spans first, in unit order; unlocatable ones behind, in output order."""
    if located.location is None:
        return (1, 0, located.order)
    return (0, located.location.offset, located.order)


def _verbatim_keepers(entities: tuple[LocatedEntity, ...]) -> dict[int, str]:
    """Pick which entity keeps each verbatim id, by the entity's position.

    Where one verbatim id carries both struck and unstruck text, the unstruck text
    keeps the verbatim id and the struck version falls through to a derived id (AC-5).
    """
    by_id: dict[str, list[LocatedEntity]] = {}
    for located in entities:
        if located.entity.id_source is IdSource.VERBATIM:
            by_id.setdefault(located.entity.id, []).append(located)
    keepers: dict[int, str] = {}
    for entity_id, claimants in by_id.items():
        unstruck = [c for c in claimants if not c.struck]
        winner = min(unstruck or claimants, key=_ordering_key)
        keepers[winner.order] = entity_id
    return keepers


def assign_ids(located: LocatedOutput, record: str, section_slug: str) -> IdentifiedOutput:
    """Give every entity its canonical id, and rewrite local endpoints to match.

    Args:
        located: one validated output whose spans are already located.
        record: the canonical id of the record the unit came from, e.g. `0008`.
        section_slug: the unit's section slug, already made unique within that record.

    Raises:
        IdAssignmentError: a relationship points at a placeholder no entity carries.
    """
    keepers = _verbatim_keepers(located.entities)
    ordered = sorted(located.entities, key=_ordering_key)

    canonical: dict[int, str] = {}
    ordinal = 0
    for item in ordered:
        kept = keepers.get(item.order)
        if kept is not None:
            canonical[item.order] = f"{record}/{kept}"
            continue
        ordinal += 1
        canonical[item.order] = f"{record}#{section_slug}:{ordinal}"

    identified = tuple(
        IdentifiedEntity(
            canonical_id=canonical[item.order],
            entity=item.entity,
            location=item.location,
            struck=item.struck,
            followup_status=item.followup_status,
        )
        for item in sorted(located.entities, key=lambda e: e.order)
    )

    endpoints: dict[str, str] = {}
    for item in ordered:
        endpoints.setdefault(item.entity.id, canonical[item.order])
    for item in located.entities:
        # The keeper of a repeated verbatim id is the one an endpoint means.
        if item.order in keepers:
            endpoints[item.entity.id] = canonical[item.order]

    relationships = tuple(
        _rewrite_endpoints(relationship, endpoints) for relationship in located.relationships
    )
    return IdentifiedOutput(entities=identified, relationships=relationships)


def _rewrite_endpoints(
    relationship: ExtractedRelationship, endpoints: dict[str, str]
) -> ExtractedRelationship:
    """Point a relationship's local endpoints at canonical ids."""
    changes: dict[str, LocalEndpoint] = {}
    for field in ("source", "target"):
        endpoint = getattr(relationship, field)
        if not isinstance(endpoint, LocalEndpoint):
            continue
        canonical = endpoints.get(endpoint.id)
        if canonical is None:
            raise IdAssignmentError(
                f"relationship endpoint {endpoint.id!r} carries no entity to name it"
            )
        changes[field] = LocalEndpoint(id=canonical)
    return relationship.model_copy(update=changes) if changes else relationship
