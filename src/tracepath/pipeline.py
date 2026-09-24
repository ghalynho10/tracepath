"""Composing the stages into one thread: unit, runs, ids, comparison, routing, load.

The order is the one spec 0002 fixes: `unit -> pre-check -> three model runs ->
validate -> compare -> assign ids -> accepted or review -> load`. Only accepted items
reach the graph.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import anthropic
from neo4j import Driver

from tracepath.artifacts import RunArtifact, build_artifact, review_entry
from tracepath.config import AnthropicSettings
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    Attempt,
    ExtractionFailed,
    run_with_retry,
)
from tracepath.extract.compare import (
    ReviewItem,
    ReviewReason,
    ReviewReasonName,
    RoutedUnit,
    identities_of,
    relationship_signature,
    route_runs,
)
from tracepath.extract.ids import IdentifiedOutput, assign_ids, locate_output
from tracepath.extract.records import Record
from tracepath.extract.schema import (
    EntityType,
    ExtractedRelationship,
    LocalEndpoint,
    normalize_label,
)
from tracepath.extract.units import Unit
from tracepath.graph.load import (
    by_link_type,
    write_entities,
    write_links,
    write_part_of,
    write_records,
    write_unresolved,
)
from tracepath.graph.model import Provenance, entity_row, link_row, record_row, unresolved_row
from tracepath.resolve.endpoints import (
    LabelIndex,
    LinkContext,
    Resolution,
    build_label_index,
    resolve_endpoints,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeldLink:
    """One relationship held because an endpoint entity was not accepted (AC-11c).

    It is not dropped: it goes to the review queue beside the entity it waits on, and
    the review step releases it when that entity is accepted.
    """

    record: str
    section: str
    item: ReviewItem


@dataclass(frozen=True)
class CorpusResolution:
    """Every accepted link resolved, and every link held for an unaccepted endpoint."""

    resolution: Resolution
    held: tuple[HeldLink, ...]


@dataclass(frozen=True)
class UnitResult:
    """Everything one unit produced: its runs, its comparison, and what was accepted."""

    unit: Unit
    section_slug: str
    artifacts: tuple[RunArtifact, ...]
    identified: tuple[IdentifiedOutput, ...]
    routed: RoutedUnit
    input_tokens: int
    output_tokens: int


class UnitFailed(Exception):
    """A unit could not be extracted, and here is everything it spent trying.

    The artifacts are carried out of the failure rather than lost with it, so the shell
    can still write them. A unit that dies without writing what its calls cost is the
    defect spec 0001's artifact storage amendment exists to close.
    """

    def __init__(self, message: str, artifacts: tuple[RunArtifact, ...]) -> None:
        """Record the failure and every artifact built before it."""
        super().__init__(message)
        self.artifacts = artifacts


def run_unit(
    client: anthropic.Anthropic,
    settings: AnthropicSettings,
    unit: Unit,
    section_slug: str,
    commit: str,
    extracted_at: str,
) -> UnitResult:
    """Run one unit the run policy's number of times and settle what it produced.

    One artifact per **attempt**, not per run: a failed attempt gets its own, carrying
    its usage and no output, so the cost of a retry is written down beside the call
    that replaced it (spec 0001).

    Raises:
        UnitFailed: a run failed again after its retry. The exception carries every
            artifact built so far, the failed attempts included.
    """
    artifacts: list[RunArtifact] = []
    identified: list[IdentifiedOutput] = []
    input_tokens = 0
    output_tokens = 0

    def record(run: int, attempt: Attempt) -> None:
        artifacts.append(
            build_artifact(
                unit=unit,
                section_slug=section_slug,
                run=run,
                attempt=attempt.number,
                output=attempt.output,
                model=settings.model,
                prompt_version=PROMPT_VERSION,
                commit=commit,
                extracted_at=extracted_at,
                max_output_tokens=MAX_TOKENS,
                effort=settings.effort or "default",
                input_tokens=attempt.input_tokens,
                output_tokens=attempt.output_tokens,
                error=attempt.error,
            )
        )

    for run in range(1, settings.runs_per_unit + 1):
        try:
            outcome = run_with_retry(client, settings, unit, run)
        except ExtractionFailed as exc:
            for attempt in exc.attempts:
                record(run, attempt)
            raise UnitFailed(str(exc), tuple(artifacts)) from exc
        for attempt in outcome.attempts:
            record(run, attempt)
            input_tokens += attempt.input_tokens
            output_tokens += attempt.output_tokens
        identified.append(
            assign_ids(locate_output(unit, outcome.output), unit.record_id, section_slug)
        )
    return UnitResult(
        unit=unit,
        section_slug=section_slug,
        artifacts=tuple(artifacts),
        identified=tuple(identified),
        routed=route_runs(identified),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _waiting_on(
    relationship: ExtractedRelationship,
    accepted_ids: frozenset[str],
    known_ids: frozenset[str],
    known_label_index: LabelIndex,
) -> str | None:
    """The entity a relationship is waiting on, if either endpoint was not accepted.

    An endpoint naming an entity the corpus holds but review has not released is a
    held link, never an `:Unresolved` node: the target is named, so drawing a gap
    there would break AC-10 and key invariant 8. An endpoint naming nothing the
    corpus holds is a different case entirely, and AC-7's fallback covers it. A
    `{record, label}` endpoint takes the same rule as a `{record, id}` one, checked
    against `known_label_index`, built over every known entity so a match to one
    still waiting on review is not missed (AC-7).
    """
    for endpoint in (relationship.source, relationship.target):
        if isinstance(endpoint, LocalEndpoint):
            qualified = endpoint.id
        elif endpoint.record is not None and endpoint.id is not None:
            qualified = f"{endpoint.record}/{endpoint.id}"
        elif endpoint.record is not None and endpoint.id is None and endpoint.label is not None:
            matched = known_label_index.get((endpoint.record, normalize_label(endpoint.label)))
            if matched is None:
                continue
            qualified = matched
        else:
            continue
        if qualified in known_ids and qualified not in accepted_ids:
            return qualified
    return None


def resolve_accepted(results: Sequence[UnitResult], records: Sequence[Record]) -> CorpusResolution:
    """Resolve every accepted relationship against everything the corpus loaded.

    Holding is decided here, before resolution, so `resolve_endpoints()` never sees a
    link whose endpoint was held and its `:Unresolved` fallback keeps meaning exactly
    what AC-7 says it means. This is the contract the first full load lacked, which is
    why it failed with `asked to write 7 but the database wrote 2` (AC-11c).
    """
    accepted_ids = frozenset(
        entity.canonical_id for result in results for entity in result.routed.accepted_entities
    )
    # The `if` sits before the clause that indexes, not after it. A comprehension
    # evaluates its clauses left to right, so a trailing guard runs only once
    # `result.identified[0]` has already been read and has already raised.
    known_entities = tuple(
        entity
        for result in results
        if result.identified
        for entity in result.identified[0].entities
    )
    known_ids = frozenset(entity.canonical_id for entity in known_entities)
    known_records = frozenset(record.canonical_id for record in records)
    # Built once over every known entity, not only the accepted ones, so a label match
    # to an entity still waiting on review is caught at `_waiting_on()` below, not
    # missed the way an `:Unresolved` fallback would miss it (AC-7). `resolve_endpoints`
    # reuses the very same index and checks its own, narrower `known_entities` (the
    # accepted set) before trusting a match, the same two site shape a `{record, id}`
    # reference already has between here and there.
    known_label_index = build_label_index(known_entities)

    pairs: list[tuple[ExtractedRelationship, LinkContext]] = []
    held: list[HeldLink] = []
    for result in results:
        # A unit that identified nothing has no entities to name and no links to
        # resolve, so it contributes nothing here. Skipping it is what the guard on
        # `known_ids` above means, applied to the same unit.
        if not result.identified:
            continue
        identities = identities_of(result.identified[0])
        context = LinkContext(
            source_record=result.unit.record_id,
            file=result.unit.path,
            section=result.unit.section,
            line=result.unit.start_line,
        )
        for relationship in result.routed.accepted_relationships:
            waiting = _waiting_on(relationship, accepted_ids, known_ids, known_label_index)
            if waiting is not None:
                held.append(
                    HeldLink(
                        record=result.unit.record_id,
                        section=result.unit.section,
                        item=ReviewItem(
                            signature=relationship_signature(relationship, identities),
                            reasons=(
                                ReviewReason(
                                    ReviewReasonName.ENDPOINT_NOT_ACCEPTED, detail=waiting
                                ),
                            ),
                        ),
                    )
                )
                continue
            pairs.append((relationship, context))

    return CorpusResolution(
        resolution=resolve_endpoints(pairs, accepted_ids, known_records, known_label_index),
        held=tuple(held),
    )


def review_rows(
    results: Sequence[UnitResult],
    held: Sequence[HeldLink],
    model: str,
    queued_at: str,
) -> tuple[dict[str, Any], ...]:
    """Every item a corpus run held back, as the rows of `artifacts/review-queue.json`.

    Two kinds of held item meet here, and both belong in the one file AC-11c names.
    Routing holds an item within its unit, which covers the three within unit reasons
    and a link whose endpoint its own unit did not accept. `resolve_accepted()` holds a
    link whose endpoint sits in another unit, which routing cannot see. Leaving either
    out would make AC-11c's promise, that a held link sits in a file tracked in git,
    false for half the held links.

    Rows keep each unit's own order, which `route_runs()` already sorted by lowest
    located offset (AC-11b), and a unit's cross unit held links follow its routed rows,
    ordered by signature so the file is stable from one run to the next.
    """
    by_unit: dict[tuple[str, str], list[HeldLink]] = {}
    for link in held:
        by_unit.setdefault((link.record, link.section), []).append(link)

    rows: list[dict[str, Any]] = []
    for result in results:
        key = (result.unit.record_id, result.unit.section)
        for item in result.routed.review:
            rows.append(review_entry(key[0], key[1], item, model, queued_at))
        for link in sorted(by_unit.pop(key, []), key=lambda h: str(h.item.signature)):
            rows.append(review_entry(link.record, link.section, link.item, model, queued_at))

    # A held link whose unit is not among the results would otherwise vanish silently.
    for (record, section), links in sorted(by_unit.items()):
        for link in sorted(links, key=lambda h: str(h.item.signature)):
            rows.append(review_entry(record, section, link.item, model, queued_at))
    return tuple(rows)


def load(
    driver: Driver,
    database: str,
    records: Sequence[Record],
    results: Sequence[UnitResult],
    resolution: Resolution,
    commit: str,
    provenance: Provenance,
) -> dict[str, int]:
    """Write records, entities, unresolved nodes and links, asserting every write."""
    written: dict[str, int] = {}
    written["records"] = write_records(driver, database, [record_row(r) for r in records])

    by_type: dict[EntityType, list[dict[str, object]]] = {}
    part_of: list[dict[str, str]] = []
    for result in results:
        for entity in result.routed.accepted_entities:
            by_type.setdefault(entity.entity.type, []).append(
                entity_row(entity, result.unit, commit, provenance)
            )
            part_of.append({"from_id": entity.canonical_id, "to_id": result.unit.record_id})
    written["entities"] = write_entities(driver, database, dict(by_type))
    written["unresolved"] = write_unresolved(
        driver, database, [unresolved_row(node) for node in resolution.unresolved]
    )
    written["part_of"] = write_part_of(driver, database, part_of)
    written["links"] = write_links(
        driver,
        database,
        {
            link_type: [link_row(link) for link in links]
            for link_type, links in by_link_type(resolution.links).items()
        },
    )
    return written
