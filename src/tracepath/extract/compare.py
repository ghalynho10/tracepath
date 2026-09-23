"""Comparing the runs of one unit, and routing what is not settled to review.

Agreement is decided on a stated signature and nothing else: an entity's collapsed
canonical id, its type and its sorted flags. Span text, rationale spans, citations and
provenance are ignored, and so are `struck` and `followup_status`, which code sets
identically for every run. Only accepted items are written to the graph (AC-11).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from tracepath.extract.ids import IdentifiedEntity, IdentifiedOutput
from tracepath.extract.schema import (
    EntityType,
    ExtractedRelationship,
    IdSource,
    LocalEndpoint,
    ReferenceEndpoint,
)

#: What every derived id collapses to before comparison, because a derived ordinal is
#: not a stability guarantee: an unlocatable span can take a different `n` per run.
COLLAPSED = "<derived>"

EntitySignature = tuple[str, str, tuple[str, ...]]
RelationshipSignature = tuple[str, str, str, tuple[str, ...]]


class ComparisonError(Exception):
    """A comparison was asked for that cannot be made."""


class ReviewReason(StrEnum):
    """Why an item is held back from the graph until a person rules on it."""

    RUNS_DISAGREE = "runs_disagree"
    KNOWN_TRAP_FLAG = "known_trap_flag"
    UNCLASSIFIED_TYPE = "unclassified_type"


@dataclass(frozen=True)
class RunComparison:
    """Whether the runs of one unit agree, and which signatures they differ on."""

    agree: bool
    shared_entities: frozenset[EntitySignature]
    differing_entities: frozenset[EntitySignature]
    shared_relationships: frozenset[RelationshipSignature]
    differing_relationships: frozenset[RelationshipSignature]


@dataclass(frozen=True)
class ReviewItem:
    """One item held back, with every reason it was held."""

    signature: EntitySignature | RelationshipSignature
    reasons: tuple[ReviewReason, ...]


@dataclass(frozen=True)
class RoutedUnit:
    """What of a unit enters the graph, and what waits for a person."""

    comparison: RunComparison
    accepted_entities: tuple[IdentifiedEntity, ...]
    accepted_relationships: tuple[ExtractedRelationship, ...]
    review: tuple[ReviewItem, ...]


def collapse(canonical_id: str) -> str:
    """Collapse a derived canonical id, leaving a verbatim one as it is."""
    return COLLAPSED if "#" in canonical_id else canonical_id


def entity_signature(entity: IdentifiedEntity) -> EntitySignature:
    """The tuple agreement is decided on, and nothing else."""
    collapsed = (
        COLLAPSED if entity.entity.id_source is IdSource.DERIVED else collapse(entity.canonical_id)
    )
    return (
        collapsed,
        str(entity.entity.type),
        tuple(sorted(str(f) for f in entity.entity.known_trap_flags)),
    )


def _endpoint_signature(endpoint: LocalEndpoint | ReferenceEndpoint) -> str:
    """An endpoint reduced for comparison.

    A reference's verbatim mention is text, so it is ignored the same way span text is.
    """
    if isinstance(endpoint, LocalEndpoint):
        return collapse(endpoint.id)
    return f"ref:{endpoint.record or ''}/{endpoint.id or ''}"


def relationship_signature(relationship: ExtractedRelationship) -> RelationshipSignature:
    """The tuple a relationship's agreement is decided on."""
    return (
        str(relationship.type),
        _endpoint_signature(relationship.source),
        _endpoint_signature(relationship.target),
        tuple(sorted(str(f) for f in relationship.known_trap_flags)),
    )


def compare_runs(outputs: Sequence[IdentifiedOutput]) -> RunComparison:
    """Compare the runs of one unit on the signature, and nothing else.

    Raises:
        ComparisonError: fewer than two outputs were given, so there is nothing to compare.
    """
    if len(outputs) < 2:
        raise ComparisonError(
            f"comparing runs needs at least two outputs, {len(outputs)} was given"
        )
    entity_sets = [{entity_signature(e) for e in output.entities} for output in outputs]
    link_sets = [{relationship_signature(r) for r in output.relationships} for output in outputs]

    shared_entities = frozenset.intersection(*(frozenset(s) for s in entity_sets))
    all_entities = frozenset.union(*(frozenset(s) for s in entity_sets))
    shared_links = frozenset.intersection(*(frozenset(s) for s in link_sets))
    all_links = frozenset.union(*(frozenset(s) for s in link_sets))

    return RunComparison(
        agree=all_entities == shared_entities and all_links == shared_links,
        shared_entities=shared_entities,
        differing_entities=all_entities - shared_entities,
        shared_relationships=shared_links,
        differing_relationships=all_links - shared_links,
    )


def _entity_reasons(
    entity: IdentifiedEntity, comparison: RunComparison
) -> tuple[ReviewReason, ...]:
    reasons: list[ReviewReason] = []
    if entity_signature(entity) not in comparison.shared_entities:
        reasons.append(ReviewReason.RUNS_DISAGREE)
    if entity.entity.known_trap_flags:
        reasons.append(ReviewReason.KNOWN_TRAP_FLAG)
    if entity.entity.type is EntityType.UNCLASSIFIED:
        reasons.append(ReviewReason.UNCLASSIFIED_TYPE)
    return tuple(reasons)


def _relationship_reasons(
    relationship: ExtractedRelationship, comparison: RunComparison
) -> tuple[ReviewReason, ...]:
    """An unclassified relationship alone never routes to review.

    It enters the graph carrying its phrase, so the uncertainty is visible in the
    chain rather than hidden in a queue.
    """
    reasons: list[ReviewReason] = []
    if relationship_signature(relationship) not in comparison.shared_relationships:
        reasons.append(ReviewReason.RUNS_DISAGREE)
    if relationship.known_trap_flags:
        reasons.append(ReviewReason.KNOWN_TRAP_FLAG)
    return tuple(reasons)


def route_runs(outputs: Sequence[IdentifiedOutput]) -> RoutedUnit:
    """Compare the runs of one unit and split it into what is accepted and what waits.

    The first run supplies the accepted items, since every accepted signature is one
    all the runs agreed on.

    Raises:
        ComparisonError: fewer than two outputs were given.
    """
    comparison = compare_runs(outputs)
    first = outputs[0]

    accepted_entities: list[IdentifiedEntity] = []
    accepted_links: list[ExtractedRelationship] = []
    review: dict[EntitySignature | RelationshipSignature, tuple[ReviewReason, ...]] = {}

    for entity in first.entities:
        reasons = _entity_reasons(entity, comparison)
        if reasons:
            review[entity_signature(entity)] = reasons
        else:
            accepted_entities.append(entity)

    for relationship in first.relationships:
        reasons = _relationship_reasons(relationship, comparison)
        if reasons:
            review[relationship_signature(relationship)] = reasons
        else:
            accepted_links.append(relationship)

    # A signature only some runs produced never reaches the first run's lists.
    for signature in comparison.differing_entities | comparison.differing_relationships:
        review.setdefault(signature, (ReviewReason.RUNS_DISAGREE,))

    return RoutedUnit(
        comparison=comparison,
        accepted_entities=tuple(accepted_entities),
        accepted_relationships=tuple(accepted_links),
        review=tuple(
            ReviewItem(signature=signature, reasons=reasons)
            for signature, reasons in sorted(review.items(), key=lambda item: str(item[0]))
        ),
    )
