"""Rebuilding the graph from the committed run artifacts, with no API calls.

This is the regression test for the failure that stopped the first full load:

    GraphWriteFailed: UNCLASSIFIED links: asked to write 7 but the database wrote 2

14 relationship endpoints named entities that had been routed to review and so were
never written. AC-11c holds such a link with its endpoint instead, so the load now
asks for exactly what it can write and every counter matches (AC-7, AC-11, AC-13).

The artifacts under `artifacts/runs/` are the source of truth for a rebuild (spec
0001), so this exercise needs no model call: it re-locates and re-identifies each
committed run against the pinned corpus and drives the real pipeline.
"""

from pathlib import Path

import pytest

from tracepath.config import load_neo4j_settings
from tracepath.extract.records import Record
from tracepath.graph.connection import connect
from tracepath.graph.model import Provenance
from tracepath.graph.schema import clear, create_constraints
from tracepath.pipeline import UnitResult, load, resolve_accepted
from tracepath.rebuild import committed_units as rebuild_units
from tracepath.rebuild import records_for_units

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
RUNS = ROOT / "artifacts" / "runs"
COMMIT = "2e40bcf"

pytestmark = pytest.mark.integration


def committed_units() -> list[UnitResult]:
    """Every committed unit, rebuilt through the real rebuild path. No API calls."""
    return list(rebuild_units(ROOT, SNAPSHOT))


def records_for_all(results: list[UnitResult]) -> list[Record]:
    """Every Record the rebuilt entities hang from."""
    return list(records_for_units(tuple(results), SNAPSHOT, COMMIT))


def test_every_committed_unit_has_all_three_of_its_runs() -> None:
    """A rebuild claims the artifacts are the source of truth, so none may be missing.

    Counted per unit rather than as one total, so adding a unit does not need this
    number changed, while a unit that lost a run still fails.
    """
    per_unit: dict[str, int] = {}
    for path in RUNS.glob("*/*/run-*.json"):
        per_unit[str(path.parent)] = per_unit.get(str(path.parent), 0) + 1

    assert per_unit, "no run artifacts found"
    assert set(per_unit.values()) == {3}, f"a unit is missing runs: {per_unit}"


def test_no_accepted_link_points_at_an_entity_that_was_not_accepted() -> None:
    """AC-11c, without touching the database: holding happens before resolution."""
    results = committed_units()
    records = records_for_all(results)

    corpus = resolve_accepted(results, records)

    accepted = {e.canonical_id for r in results for e in r.routed.accepted_entities}
    record_ids = {r.canonical_id for r in records}
    for link in corpus.resolution.links:
        for endpoint in (link.source, link.target):
            if endpoint.target.value == "Entity":
                assert endpoint.canonical_id in accepted, (
                    f"{endpoint.canonical_id} was resolved but never accepted"
                )
            elif endpoint.target.value == "Record":
                assert endpoint.canonical_id in record_ids

    assert corpus.held, "the committed run is the one that had held links; it should have some"


def test_the_full_load_completes_and_every_counter_matches() -> None:
    """The load that failed at `asked to write 7 but the database wrote 2` now completes."""
    results = committed_units()
    records = records_for_all(results)
    corpus = resolve_accepted(results, records)
    settings = load_neo4j_settings()

    with connect(settings) as driver:
        clear(driver, settings.database)
        create_constraints(driver, settings.database)
        written = load(
            driver,
            settings.database,
            records,
            results,
            corpus.resolution,
            COMMIT,
            Provenance(
                model="claude-sonnet-5",
                prompt_version="0002.2",
                extracted_at="2026-09-23T00:00:00+00:00",
                accepted_by="auto",
            ),
        )
        phantom, _, _ = driver.execute_query(
            "MATCH (n) WHERE n.canonical_id IS NULL RETURN count(n) AS n",
            database_=settings.database,
        )

    assert written["records"] > 0
    assert written["entities"] > 0
    assert phantom[0]["n"] == 0, "AC-13: a phantom node means a write matched nothing"
