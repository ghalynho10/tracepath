"""Composing the stages into one thread: unit, runs, ids, comparison, routing, load.

The order is the one spec 0002 fixes: `unit -> pre-check -> three model runs ->
validate -> compare -> assign ids -> accepted or review -> load`. Only accepted items
reach the graph.
"""

import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic
from neo4j import Driver

from tracepath.artifacts import RunArtifact, build_artifact, review_entry, run_path
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
from tracepath.extract.ids import (
    IdentifiedOutput,
    assign_ids,
    label_binding_rules,
    locate_output,
)
from tracepath.extract.records import Record
from tracepath.extract.schema import (
    EntityType,
    ExtractedRelationship,
    LocalEndpoint,
    RelationshipType,
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
from tracepath.graph.schema import clear, create_constraints
from tracepath.resolve.endpoints import (
    LabelIndex,
    LinkContext,
    Resolution,
    ResolvedLink,
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
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


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
    cache_written = 0
    cache_read = 0

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
                run_id=attempt.run_id,
                raw_response=attempt.raw_response,
                stop_reason=attempt.stop_reason,
                error=attempt.error,
                cache_creation_input_tokens=attempt.cache_creation_input_tokens,
                cache_read_input_tokens=attempt.cache_read_input_tokens,
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
            # A dropped attempt's unmeasured (null) count adds nothing here; its own
            # artifact keeps the null.
            input_tokens += attempt.input_tokens or 0
            output_tokens += attempt.output_tokens or 0
            cache_written += attempt.cache_creation_input_tokens
            cache_read += attempt.cache_read_input_tokens
        located = label_binding_rules(unit, locate_output(unit, outcome.output))
        identified.append(assign_ids(located, unit.record_id, section_slug))
    return UnitResult(
        unit=unit,
        section_slug=section_slug,
        artifacts=tuple(artifacts),
        identified=tuple(identified),
        routed=route_runs(identified),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_written,
        cache_read_input_tokens=cache_read,
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


class ProvenanceMismatch(Exception):
    """A unit's runs do not agree on where they came from, so no one provenance fits."""


def unit_provenance(result: UnitResult, accepted_by: str) -> Provenance:
    """Where one unit's accepted items came from, read off that unit's own run artifacts.

    Per unit, not per load: a graph rebuilt from units extracted under different prompt
    versions must say which version each node came from, or a prompt change cannot be
    told apart from a stable one. The timestamp is the first settled run's, since
    `route_runs()` takes the accepted items from that run.

    Raises:
        ProvenanceMismatch: the unit has no settled run, or its settled runs name more
            than one model, prompt version or corpus commit. Runs compared across a
            prompt change say nothing about stability, so stamping the unit with either
            would be a guess.
    """
    settled = sorted((a for a in result.artifacts if a.output is not None), key=lambda a: a.run)
    where = f"{result.unit.record_id} {result.unit.section}"
    if not settled:
        raise ProvenanceMismatch(f"{where}: no settled run to read provenance from")
    models = sorted({a.model for a in settled})
    versions = sorted({a.prompt_version for a in settled})
    commits = sorted({a.commit for a in settled})
    if len(models) > 1 or len(versions) > 1:
        raise ProvenanceMismatch(f"{where}: runs mix models {models} or prompt versions {versions}")
    if len(commits) > 1:
        raise ProvenanceMismatch(f"{where}: runs mix corpus commits {commits}")
    first = settled[0]
    return Provenance(
        model=first.model,
        prompt_version=first.prompt_version,
        extracted_at=first.extracted_at,
        accepted_by=accepted_by,
        commit=first.commit,
    )


def link_provenances(
    results: Sequence[UnitResult], provenances: Sequence[Provenance]
) -> dict[tuple[str, str], Provenance]:
    """Each unit's provenance keyed by `(file, section)`, the place a link was written.

    A resolved link carries its `file` and `section` and nothing else about its unit,
    so that pair is the key (spec 0004, Value sourcing). Two units of one file can share
    a section name (spec 0007 has two `Build plan` units); when they also share a
    provenance the key is still exact, and when they do not, either stamp would be a
    guess.

    Raises:
        ProvenanceMismatch: two units with the same `(file, section)` differ in
            provenance.
    """
    by_place: dict[tuple[str, str], Provenance] = {}
    for result, provenance in zip(results, provenances, strict=True):
        place = (result.unit.path, result.unit.section)
        held = by_place.setdefault(place, provenance)
        stamp = (provenance.model, provenance.prompt_version, provenance.commit)
        if (held.model, held.prompt_version, held.commit) != stamp:
            raise ProvenanceMismatch(
                f"{place[0]} {place[1]}: two units share this section and differ in "
                "provenance, so a link written there cannot be stamped"
            )
    return by_place


def collapsed_links(links: Sequence[ResolvedLink]) -> int:
    """How many resolved links collapse into a relationship another link already makes.

    The write is a `MERGE` on type and both endpoints, so two same type links between
    one pair become one relationship (spec 0004 AC-16, AC-51).
    """
    return len(links) - len(
        {(link.type, link.source.canonical_id, link.target.canonical_id) for link in links}
    )


def load(
    driver: Driver,
    database: str,
    records: Sequence[Record],
    results: Sequence[UnitResult],
    resolution: Resolution,
    commit: str,
    accepted_by: str,
    *,
    clear_first: bool = False,
) -> dict[str, int]:
    """Write records, entities, unresolved nodes and links, asserting every write.

    Each entity and each link carries its own unit's provenance (`unit_provenance()`).
    Every row, provenance included, is settled before the first write, so a unit or a
    link that cannot be stamped stops the load before anything reaches the graph.
    `clear_first` empties the graph and creates the constraints only after that, so a
    refused load leaves the previous graph standing (spec 0004 AC-15).

    Raises:
        ProvenanceMismatch: a unit's runs disagree on model, prompt version or commit,
            or a link was written in a section no loaded unit holds.
    """
    provenances = [unit_provenance(result, accepted_by) for result in results]
    by_place = link_provenances(results, provenances)
    link_rows: dict[RelationshipType, list[dict[str, Any]]] = {}
    for link_type, links in by_link_type(resolution.links).items():
        rows: list[dict[str, Any]] = []
        for link in links:
            provenance = by_place.get((link.file, link.section))
            if provenance is None:
                raise ProvenanceMismatch(
                    f"a {link.type} link was written in {link.file} {link.section}, "
                    "which no loaded unit holds, so it has no provenance to carry"
                )
            rows.append(link_row(link, provenance))
        link_rows[link_type] = rows

    if clear_first:
        clear(driver, database)
        create_constraints(driver, database)

    written: dict[str, int] = {}
    written["records"] = write_records(driver, database, [record_row(r) for r in records])

    by_type: dict[EntityType, list[dict[str, object]]] = {}
    part_of: list[dict[str, str]] = []
    for result, provenance in zip(results, provenances, strict=True):
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
    written["links"] = write_links(driver, database, dict(link_rows))
    return written


def graph_build(
    results: Sequence[UnitResult],
    corpus: CorpusResolution,
    provenances: Sequence[Provenance],
    corpus_commit: str,
    review_log_entries: int,
    passes: Mapping[tuple[str, str], tuple[str, ...]],
) -> dict[str, Any]:
    """The build manifest `load` writes to `artifacts/graph-build.json` (spec 0004 AC-17).

    `passes` holds each unit's distinct `extracted_at` values, keyed by `(record,
    section_slug)`, read from all its artifacts (AC-65); more than one marks a resume.

    It holds no timestamp, so two loads over unchanged artifacts write the same bytes
    (AC-18). A unit's accepted links are the ones the load writes from its section; its
    held links are the ones routing held inside it plus the ones `resolve_accepted()`
    held for an endpoint in another unit, so the two together account for every link
    its first run produced.
    """
    units: list[dict[str, Any]] = []
    for result, provenance in zip(results, provenances, strict=True):
        place = (result.unit.path, result.unit.section)
        # A link's signature is (type, source, target); a held entity's is a pair, and
        # one with no located line has no id either, so the id alone cannot tell them apart.
        held_inside = sum(1 for item in result.routed.review if len(item.signature) == 3)
        held_across = sum(
            1
            for link in corpus.held
            if (link.record, link.section) == (result.unit.record_id, result.unit.section)
        )
        units.append(
            {
                "record": result.unit.record_id,
                "section": result.unit.section,
                "section_slug": result.section_slug,
                "run_files": [run_path(Path(), a).as_posix() for a in result.artifacts],
                "model": provenance.model,
                "prompt_version": provenance.prompt_version,
                "accepted_entities": len(result.routed.accepted_entities),
                "accepted_links": sum(
                    1 for link in corpus.resolution.links if (link.file, link.section) == place
                ),
                "held_links": held_inside + held_across,
                "extracted_at": list(passes.get((result.unit.record_id, result.section_slug), ())),
            }
        )
    versions = Counter(provenance.prompt_version for provenance in provenances)
    return {
        "corpus_commit": corpus_commit,
        "units": units,
        "prompt_versions": dict(sorted(versions.items())),
        "review_log_entries": review_log_entries,
    }
