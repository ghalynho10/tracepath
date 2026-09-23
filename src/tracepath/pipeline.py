"""Composing the stages into one thread: unit, runs, ids, comparison, routing, load.

The order is the one spec 0002 fixes: `unit -> pre-check -> three model runs ->
validate -> compare -> assign ids -> accepted or review -> load`. Only accepted items
reach the graph.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import anthropic
from neo4j import Driver

from tracepath.artifacts import RunArtifact, build_artifact
from tracepath.config import AnthropicSettings
from tracepath.extract.client import MAX_TOKENS, PROMPT_VERSION, run_with_retry
from tracepath.extract.compare import RoutedUnit, route_runs
from tracepath.extract.ids import IdentifiedOutput, assign_ids, locate_output
from tracepath.extract.records import Record
from tracepath.extract.schema import EntityType
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
from tracepath.resolve.endpoints import LinkContext, Resolution, resolve_endpoints

log = logging.getLogger(__name__)


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


def run_unit(
    client: anthropic.Anthropic,
    settings: AnthropicSettings,
    unit: Unit,
    section_slug: str,
    commit: str,
    extracted_at: str,
) -> UnitResult:
    """Run one unit the run policy's number of times and settle what it produced."""
    artifacts: list[RunArtifact] = []
    identified: list[IdentifiedOutput] = []
    input_tokens = 0
    output_tokens = 0
    for run in range(1, settings.runs_per_unit + 1):
        call = run_with_retry(client, settings, unit, run)
        output = call.output
        input_tokens += call.input_tokens
        output_tokens += call.output_tokens
        artifacts.append(
            build_artifact(
                unit=unit,
                section_slug=section_slug,
                run=run,
                output=output,
                model=settings.model,
                prompt_version=PROMPT_VERSION,
                commit=commit,
                extracted_at=extracted_at,
                max_output_tokens=MAX_TOKENS,
                effort=settings.effort or "default",
            )
        )
        identified.append(assign_ids(locate_output(unit, output), unit.record_id, section_slug))
    return UnitResult(
        unit=unit,
        section_slug=section_slug,
        artifacts=tuple(artifacts),
        identified=tuple(identified),
        routed=route_runs(identified),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def resolve_accepted(results: Sequence[UnitResult], records: Sequence[Record]) -> Resolution:
    """Resolve every accepted relationship against everything the corpus loaded."""
    known_entities = frozenset(
        entity.canonical_id for result in results for entity in result.routed.accepted_entities
    )
    known_records = frozenset(record.canonical_id for record in records)
    pairs = [
        (
            relationship,
            LinkContext(
                source_record=result.unit.record_id,
                file=result.unit.path,
                section=result.unit.section,
                line=result.unit.start_line,
            ),
        )
        for result in results
        for relationship in result.routed.accepted_relationships
    ]
    return resolve_endpoints(pairs, known_entities, known_records)


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
