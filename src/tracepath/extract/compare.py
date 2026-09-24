"""Comparing the runs of one unit, and routing what is not settled to review.

Agreement is decided on a stated signature and nothing else: an entity's identity
(its verbatim canonical id, else the line its span was located to) and its type. Span
text, rationale spans, citations, provenance and flags are ignored, and so are `struck`
and `followup_status`, which code sets identically for every run. Only accepted items
are written to the graph (AC-11).

Two rules here are easy to "simplify" back into bugs, so both are stated:

* The signature carries no flags. Flags are the least stable thing the model produces,
  and this module already routes any flagged item to review on its own trigger, so
  keeping them in the signature counted them twice and marked *unflagged* neighbours
  as disagreements (AC-11a).
* Runs are compared by **count**, not as sets, and where a count differs every copy of
  that signature is held, not just the surplus. Accepting the first `min(counts)` would
  assert a correspondence the runs never established (AC-11b).
* A derived entity whose span could not be located never accepts on its count. Its
  identity collapses to `COLLAPSED`, so three runs each finding two unlocatable claims
  of one type would otherwise read as agreement while holding six unrelated claims
  (AC-11d). Removing this trades a visible queue row for an invisible wrong node.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from tracepath.extract.ids import IdentifiedEntity, IdentifiedOutput
from tracepath.extract.schema import (
    EntityType,
    ExtractedRelationship,
    LocalEndpoint,
    ReferenceEndpoint,
    normalize_label,
)

#: What a derived id collapses to when its span could not be located. A derived
#: ordinal is not a stability guarantee, because an unlocatable span can take a
#: different `n` per run (AC-3). A located line is stable, so only the unlocatable
#: ones fall back to this.
COLLAPSED = "<derived>"

#: How a located line is written into a signature, so the identity component stays a
#: single string and can never collide with a verbatim id like `0021/AC-2`.
LINE_PREFIX = "line:"

EntitySignature = tuple[str, str]
RelationshipSignature = tuple[str, str, str]


class ComparisonError(Exception):
    """A comparison was asked for that cannot be made."""


class ReviewReasonName(StrEnum):
    """Why an item is held back from the graph until a person rules on it."""

    RUNS_DISAGREE = "runs_disagree"
    KNOWN_TRAP_FLAG = "known_trap_flag"
    UNCLASSIFIED_TYPE = "unclassified_type"
    ENDPOINT_NOT_ACCEPTED = "endpoint_not_accepted"
    SPAN_NOT_LOCATED = "span_not_located"


@dataclass(frozen=True)
class ReviewReason:
    """One reason an item was held, with the detail that reason needs.

    `ENDPOINT_NOT_ACCEPTED` carries the canonical id of the entity the link is waiting
    on, so a reviewer can see what to rule on first. The other four carry nothing.
    """

    name: ReviewReasonName
    detail: str | None = None


@dataclass(frozen=True)
class RunComparison:
    """Whether the runs of one unit agree, and how they differ.

    `entity_counts` and `relationship_counts` map each signature to how many times
    each run produced it, in run order. A set cannot express that, which is why the
    comparison keeps counts (AC-11b).
    """

    agree: bool
    shared_entities: frozenset[EntitySignature]
    differing_entities: frozenset[EntitySignature]
    shared_relationships: frozenset[RelationshipSignature]
    differing_relationships: frozenset[RelationshipSignature]
    entity_counts: tuple[tuple[EntitySignature, tuple[int, ...]], ...]
    relationship_counts: tuple[tuple[RelationshipSignature, tuple[int, ...]], ...]


@dataclass(frozen=True)
class ReviewItem:
    """One item held back, with every reason it was held.

    `canonical_id` is null for a relationship, which has no id of its own; a held link
    is identified by its `signature`, which already carries its type and both
    endpoints. `offset` orders the queue and is not part of the signature.
    """

    signature: EntitySignature | RelationshipSignature
    reasons: tuple[ReviewReason, ...]
    canonical_id: str | None = None
    line: int | None = None
    offset: int | None = None


@dataclass(frozen=True)
class RoutedUnit:
    """What of a unit enters the graph, and what waits for a person."""

    comparison: RunComparison
    accepted_entities: tuple[IdentifiedEntity, ...]
    accepted_relationships: tuple[ExtractedRelationship, ...]
    review: tuple[ReviewItem, ...]


def entity_identity(entity: IdentifiedEntity) -> str:
    """The identity half of an entity's signature (AC-11a).

    A verbatim canonical id stands as it is. Everything else is identified by the line
    its span was located to, which is a property of the source text rather than of the
    run, and so does not shift when two runs find different numbers of spans. The
    canonical id's own shape decides this, not `id_source`: where one verbatim id
    carries both struck and unstruck text, the struck twin keeps `id_source` verbatim
    while taking a derived canonical id (AC-5).
    """
    if "#" not in entity.canonical_id:
        return entity.canonical_id
    if entity.location is not None:
        return f"{LINE_PREFIX}{entity.location.line}"
    return COLLAPSED


def entity_signature(entity: IdentifiedEntity) -> EntitySignature:
    """The tuple agreement is decided on, and nothing else.

    A `label`, normalized, joins the identity half when the entity carries one, so
    three runs disagreeing only on a `label` are caught rather than one being silently
    written (AC-11e). Skipped for a `COLLAPSED` identity: that entity already routes to
    review on `SPAN_NOT_LOCATED` regardless of its label, and appending to `COLLAPSED`
    would stop `is_unlocated_derived()` recognizing it, the exact identity that reason
    exists to catch.
    """
    identity = entity_identity(entity)
    if entity.entity.label is not None and identity != COLLAPSED:
        identity = f"{identity}|label:{normalize_label(entity.entity.label)}"
    return (identity, str(entity.entity.type))


def is_unlocated_derived(signature: EntitySignature | RelationshipSignature) -> bool:
    """Whether a signature is a derived entity whose span could not be located (AC-11d).

    Decided from the signature alone, because the leftover branch of `route_runs()`
    has nothing else: a signature only a later run produced has no first run entity to
    read a location off. A relationship signature is a triple and never qualifies; a
    verbatim entity keeps its own canonical id as its identity whatever its line, so it
    never qualifies either. Only `COLLAPSED` means "a derived entity with no line", and
    that is exactly the case with no identity to compare on.
    """
    return len(signature) == 2 and signature[0] == COLLAPSED


def _endpoint_signature(
    endpoint: LocalEndpoint | ReferenceEndpoint, identities: Mapping[str, str]
) -> str:
    """An endpoint reduced for comparison.

    A local endpoint names an entity in this same output, so it takes that entity's
    identity, the same rule the entity itself is compared by. A reference points
    outside the unit and has no local line to use, so it keeps its record, id and a
    normalized `label` when it carries one (AC-11e); its verbatim mention is text, and
    is ignored the way span text is.
    """
    if isinstance(endpoint, LocalEndpoint):
        return identities.get(endpoint.id, COLLAPSED)
    label = f"|label:{normalize_label(endpoint.label)}" if endpoint.label else ""
    return f"ref:{endpoint.record or ''}/{endpoint.id or ''}{label}"


def relationship_signature(
    relationship: ExtractedRelationship, identities: Mapping[str, str]
) -> RelationshipSignature:
    """The tuple a relationship's agreement is decided on."""
    return (
        str(relationship.type),
        _endpoint_signature(relationship.source, identities),
        _endpoint_signature(relationship.target, identities),
    )


def identities_of(output: IdentifiedOutput) -> Mapping[str, str]:
    """Each entity's canonical id mapped to the identity its signature uses."""
    return {entity.canonical_id: entity_identity(entity) for entity in output.entities}


def _counts(values: Sequence[str]) -> dict[str, int]:
    counted: dict[str, int] = {}
    for value in values:
        counted[value] = counted.get(value, 0) + 1
    return counted


def _tally[S: (EntitySignature, RelationshipSignature)](
    per_run: Sequence[Sequence[S]],
) -> tuple[frozenset[S], frozenset[S], tuple[tuple[S, tuple[int, ...]], ...]]:
    """Split signatures into agreed and differing, by count across the runs.

    A signature is shared only when every run produced it the same number of times.
    Where the count differs at all, the whole signature differs, so every copy of it
    routes to review rather than the surplus alone (AC-11b).
    """
    counted = [_counts([str(s) for s in run]) for run in per_run]
    by_key: dict[str, S] = {str(s): s for run in per_run for s in run}
    shared: set[S] = set()
    differing: set[S] = set()
    tallies: list[tuple[S, tuple[int, ...]]] = []
    for key, signature in by_key.items():
        counts = tuple(run.get(key, 0) for run in counted)
        tallies.append((signature, counts))
        if len(set(counts)) == 1:
            shared.add(signature)
        else:
            differing.add(signature)
    return frozenset(shared), frozenset(differing), tuple(sorted(tallies, key=lambda t: str(t[0])))


def compare_runs(outputs: Sequence[IdentifiedOutput]) -> RunComparison:
    """Compare the runs of one unit on the signature, and nothing else.

    Raises:
        ComparisonError: fewer than two outputs were given, so there is nothing to compare.
    """
    if len(outputs) < 2:
        raise ComparisonError(
            f"comparing runs needs at least two outputs, {len(outputs)} was given"
        )
    per_run_identities = [identities_of(output) for output in outputs]
    entity_runs = [[entity_signature(e) for e in output.entities] for output in outputs]
    link_runs = [
        [relationship_signature(r, identities) for r in output.relationships]
        for output, identities in zip(outputs, per_run_identities, strict=True)
    ]

    shared_entities, differing_entities, entity_counts = _tally(entity_runs)
    shared_links, differing_links, link_counts = _tally(link_runs)

    return RunComparison(
        agree=not differing_entities and not differing_links,
        shared_entities=shared_entities,
        differing_entities=differing_entities,
        shared_relationships=shared_links,
        differing_relationships=differing_links,
        entity_counts=entity_counts,
        relationship_counts=link_counts,
    )


def _entity_reasons(
    entity: IdentifiedEntity, comparison: RunComparison
) -> tuple[ReviewReason, ...]:
    reasons: list[ReviewReason] = []
    if entity_signature(entity) not in comparison.shared_entities:
        reasons.append(ReviewReason(ReviewReasonName.RUNS_DISAGREE))
    if entity.entity.known_trap_flags:
        reasons.append(ReviewReason(ReviewReasonName.KNOWN_TRAP_FLAG))
    if entity.entity.type is EntityType.UNCLASSIFIED:
        reasons.append(ReviewReason(ReviewReasonName.UNCLASSIFIED_TYPE))
    if is_unlocated_derived(entity_signature(entity)):
        reasons.append(ReviewReason(ReviewReasonName.SPAN_NOT_LOCATED))
    return tuple(reasons)


def _relationship_reasons(
    relationship: ExtractedRelationship,
    comparison: RunComparison,
    identities: Mapping[str, str],
    accepted_ids: frozenset[str],
    known_ids: frozenset[str],
) -> tuple[ReviewReason, ...]:
    """Why a relationship is held.

    An unclassified relationship alone never routes to review: it enters the graph
    carrying its phrase, so the uncertainty is visible in the chain rather than hidden
    in a queue. A local endpoint naming an entity that exists in this unit but was not
    accepted does hold the link, under `ENDPOINT_NOT_ACCEPTED`, naming that entity
    (AC-11c). An endpoint naming nothing the unit holds is not this case: it is a
    reference, and AC-7's `:Unresolved` fallback covers it at resolution time.
    """
    reasons: list[ReviewReason] = []
    if relationship_signature(relationship, identities) not in comparison.shared_relationships:
        reasons.append(ReviewReason(ReviewReasonName.RUNS_DISAGREE))
    if relationship.known_trap_flags:
        reasons.append(ReviewReason(ReviewReasonName.KNOWN_TRAP_FLAG))
    for endpoint in (relationship.source, relationship.target):
        if not isinstance(endpoint, LocalEndpoint):
            continue
        if endpoint.id in known_ids and endpoint.id not in accepted_ids:
            reasons.append(ReviewReason(ReviewReasonName.ENDPOINT_NOT_ACCEPTED, detail=endpoint.id))
    return tuple(reasons)


def _item_for(entity: IdentifiedEntity, reasons: tuple[ReviewReason, ...]) -> ReviewItem:
    return ReviewItem(
        signature=entity_signature(entity),
        reasons=reasons,
        canonical_id=entity.canonical_id,
        line=entity.location.line if entity.location else None,
        offset=entity.location.offset if entity.location else None,
    )


def _queue_key(item: ReviewItem) -> tuple[int, int, str]:
    """Lowest located offset first, unlocatable items behind, then by signature."""
    if item.offset is None:
        return (1, 0, str(item.signature))
    return (0, item.offset, str(item.signature))


def route_runs(outputs: Sequence[IdentifiedOutput]) -> RoutedUnit:
    """Compare the runs of one unit and split it into what is accepted and what waits.

    The first run supplies the accepted items, since every accepted signature is one
    all the runs produced the same number of times. Entities are settled before
    relationships, because whether a link is held depends on whether its endpoint was
    accepted (AC-11c).

    Raises:
        ComparisonError: fewer than two outputs were given.
    """
    comparison = compare_runs(outputs)
    first = outputs[0]
    identities = identities_of(first)

    accepted_entities: list[IdentifiedEntity] = []
    review: list[ReviewItem] = []
    seen: set[str] = set()

    for entity in first.entities:
        reasons = _entity_reasons(entity, comparison)
        if reasons:
            review.append(_item_for(entity, reasons))
            seen.add(str(entity_signature(entity)))
        else:
            accepted_entities.append(entity)

    accepted_ids = frozenset(entity.canonical_id for entity in accepted_entities)
    known_ids = frozenset(entity.canonical_id for entity in first.entities)

    accepted_links: list[ExtractedRelationship] = []
    for relationship in first.relationships:
        reasons = _relationship_reasons(
            relationship, comparison, identities, accepted_ids, known_ids
        )
        if reasons:
            signature = relationship_signature(relationship, identities)
            review.append(ReviewItem(signature=signature, reasons=reasons))
            seen.add(str(signature))
        else:
            accepted_links.append(relationship)

    # A signature only some runs produced never reaches the first run's lists.
    leftovers: frozenset[EntitySignature | RelationshipSignature] = (
        comparison.differing_entities | comparison.differing_relationships
    )
    for leftover in leftovers:
        if str(leftover) not in seen:
            # A leftover carries `SPAN_NOT_LOCATED` on the same rule as a first run
            # entity. Without this, two structurally identical unlocatable items would
            # get different reasons depending only on which run happened to find one
            # first, and the committed queue already holds such rows (AC-11d).
            reasons = (ReviewReason(ReviewReasonName.RUNS_DISAGREE),)
            if is_unlocated_derived(leftover):
                reasons += (ReviewReason(ReviewReasonName.SPAN_NOT_LOCATED),)
            review.append(ReviewItem(signature=leftover, reasons=reasons))
            seen.add(str(leftover))

    return RoutedUnit(
        comparison=comparison,
        accepted_entities=tuple(accepted_entities),
        accepted_relationships=tuple(accepted_links),
        review=tuple(sorted(review, key=_queue_key)),
    )
