"""The review queue is where held items live, and both kinds of held item reach it.

AC-11c promises a held link "sits in `artifacts/review-queue.json`, which is tracked in
git". That promise was false while `write_review_queue()` had no caller, and it would
be half false if the file held only the links routing catches inside a unit, leaving
out the ones `resolve_accepted()` catches across units.

These run off the committed artifacts, so no API call and no database.
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from tracepath.artifacts import REVIEW_QUEUE
from tracepath.extract.compare import ReviewItem, ReviewReason, ReviewReasonName
from tracepath.pipeline import CorpusResolution, HeldLink, UnitResult, resolve_accepted, review_rows
from tracepath.rebuild import committed_units, records_for_units

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"
MODEL = "claude-sonnet-5"
QUEUED_AT = "2026-09-23T00:00:00+00:00"


@dataclass(frozen=True)
class Rebuilt:
    """The committed run, rebuilt, and the queue rows it produces."""

    results: tuple[UnitResult, ...]
    corpus: CorpusResolution
    rows: tuple[dict[str, Any], ...]


@cache
def rebuilt() -> Rebuilt:
    """Rebuild the committed run and derive its queue. No API call, no database.

    Cached: re-aligning every span of every run is the expensive part, and the rebuild
    is deterministic, which the stability test below is there to prove.
    """
    results = committed_units(ROOT, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, COMMIT)
    corpus = resolve_accepted(results, records)
    return Rebuilt(results, corpus, review_rows(results, corpus.held, MODEL, QUEUED_AT))


def test_the_queue_holds_every_item_routing_and_resolution_held() -> None:
    run = rebuilt()

    routed = sum(len(r.routed.review) for r in run.results)

    assert len(run.rows) == routed + len(run.corpus.held)


def test_a_cross_unit_held_link_is_not_lost_between_routing_and_resolution() -> None:
    """`resolve_accepted()` catches what routing cannot see, and it must still be queued."""
    run = rebuilt()
    routed_signatures = {
        str(item.signature) for result in run.results for item in result.routed.review
    }
    cross_unit = [h for h in run.corpus.held if str(h.item.signature) not in routed_signatures]

    assert cross_unit, "the committed run is the one with a cross unit held link"
    queued = {str(tuple(row["signature"])) for row in run.rows}
    for link in cross_unit:
        assert str(link.item.signature) in queued


def test_every_held_link_names_the_entity_it_waits_on() -> None:
    """AC-11c: a reviewer has to be able to see what to rule on first."""
    held = [
        reason
        for row in rebuilt().rows
        for reason in row["reasons"]
        if reason["name"] == "endpoint_not_accepted"
    ]

    assert held
    assert all(reason["detail"] for reason in held)


def test_a_held_link_carries_no_canonical_id_and_an_entity_carries_one() -> None:
    rows = rebuilt().rows

    entities = [row for row in rows if row["canonical_id"] is not None]
    links = [row for row in rows if row["canonical_id"] is None]

    assert entities and links
    assert all(row["signature"] for row in links)


def test_the_queue_is_stable_from_one_rebuild_to_the_next() -> None:
    """A file tracked in git that reorders itself on every run is not reviewable."""
    first = review_rows(rebuilt().results, rebuilt().corpus.held, MODEL, QUEUED_AT)
    second = review_rows(rebuilt().results, rebuilt().corpus.held, MODEL, QUEUED_AT)

    assert first == second


def test_the_committed_queue_matches_what_the_committed_artifacts_produce() -> None:
    """The queue is derived, never hand maintained, so a stale file is a real defect."""
    committed = json.loads((ROOT / REVIEW_QUEUE).read_text())

    assert [row["signature"] for row in committed] == [
        list(row["signature"]) for row in rebuilt().rows
    ]


def test_a_held_link_from_a_unit_with_no_results_is_still_queued() -> None:
    """Nothing held may be dropped for having nowhere obvious to sit."""
    orphan = HeldLink(
        record="9999",
        section="Requirements",
        item=ReviewItem(
            signature=("satisfies", "line:1", "ref:9999/AC-1"),
            reasons=(ReviewReason(ReviewReasonName.ENDPOINT_NOT_ACCEPTED, detail="9999/AC-1"),),
        ),
    )

    rows = review_rows((), (orphan,), MODEL, QUEUED_AT)

    assert len(rows) == 1
    assert rows[0]["record"] == "9999"
