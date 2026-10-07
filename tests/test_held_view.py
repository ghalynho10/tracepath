"""The held item view over the committed artifacts, with no database (spec 0005 build step 3).

`build_held_view()` is pure: the committed run artifacts go in, the held entities, the
held links and the counts come out. The skip cases the corpus does not happen to hold
are made by editing one unit's routing, never by hand writing a graph.
"""

import dataclasses
from collections.abc import Sequence
from pathlib import Path

import pytest

from tracepath.extract.compare import ReviewReason, ReviewReasonName
from tracepath.extract.records import Record
from tracepath.pipeline import (
    CorpusResolution,
    HeldView,
    HeldViewIncomplete,
    UnitResult,
    build_held_view,
    held_reason,
    resolve_accepted,
)
from tracepath.rebuild import committed_units, records_for_units
from tracepath.resolve.endpoints import Target

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"

Corpus = tuple[tuple[UnitResult, ...], CorpusResolution, tuple[Record, ...]]


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    results = committed_units(ROOT, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, COMMIT)
    return results, resolve_accepted(results, records), records


@pytest.fixture(scope="module")
def view(corpus: Corpus) -> HeldView:
    return build_held_view(*corpus)


def view_of(results: Sequence[UnitResult], records: Sequence[Record]) -> HeldView:
    return build_held_view(results, resolve_accepted(results, records), records)


def entity_rows(results: Sequence[UnitResult]) -> int:
    return sum(1 for r in results for i in r.routed.review if len(i.signature) == 2)


def link_rows(results: Sequence[UnitResult], corpus: CorpusResolution) -> int:
    inside = sum(1 for r in results for i in r.routed.review if len(i.signature) == 3)
    return inside + len(corpus.held)


def unit(results: Sequence[UnitResult], record: str, slug: str) -> UnitResult:
    return next(r for r in results if (r.unit.record_id, r.section_slug) == (record, slug))


# How a reason is stored.


def test_a_reason_is_stored_as_its_name_when_it_has_no_detail() -> None:
    assert held_reason(ReviewReason(ReviewReasonName.RUNS_DISAGREE)) == "runs_disagree"


def test_a_reason_with_detail_is_stored_as_name_colon_detail() -> None:
    reason = ReviewReason(ReviewReasonName.ENDPOINT_NOT_ACCEPTED, detail="0002/AC-10")

    assert held_reason(reason) == "endpoint_not_accepted:0002/AC-10"


# AC-17: every held first run entity, with its reasons.


def test_ac_17_a_held_first_run_entity_is_in_the_view_with_its_reasons(view: HeldView) -> None:
    """covers: spec 0005 AC-17."""
    found = {held.entity.canonical_id: held.reasons for held in view.entities}

    assert found["0002/AC-10"] == ("known_trap_flag",)
    assert found["0002#requirements:6"] == ("runs_disagree", "known_trap_flag")


def test_ac_17_every_view_entity_is_a_first_run_entity_routing_did_not_accept(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-17 (nothing accepted, nothing from a later run)."""
    results = corpus[0]
    accepted = {e.canonical_id for r in results for e in r.routed.accepted_entities}
    first_run = {e.canonical_id for r in results for e in r.identified[0].entities}

    ids = [held.entity.canonical_id for held in view.entities]
    assert ids and not set(ids) & accepted
    assert set(ids) <= first_run


def test_ac_17_every_held_entity_carries_at_least_one_reason(view: HeldView) -> None:
    assert all(held.reasons for held in view.entities)


# AC-19: held links, in unit and across units, resolved by spec 0002 AC-7.


def test_ac_19_an_in_unit_held_link_is_in_the_view_with_its_reasons(view: HeldView) -> None:
    """covers: spec 0005 AC-19 (a first run relationship routing held)."""
    found = {
        (h.link.type.name, h.link.source.canonical_id, h.link.target.canonical_id): h.reasons
        for h in view.links
    }

    assert found[("UNCLASSIFIED", "0002#requirements:6", "0007/AC-13")] == (
        "runs_disagree",
        "endpoint_not_accepted:0002#requirements:6",
    )


def test_ac_19_a_cross_unit_held_link_is_in_the_view_with_its_reasons(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-19 (a link held for an endpoint in another unit)."""
    cross = corpus[1].held[0]
    assert cross.relationship is not None
    reasons = tuple(held_reason(r) for r in cross.item.reasons)

    assert any(
        h.reasons == reasons
        and h.link.file.startswith(f"specs/{cross.record}")
        and h.link.section == cross.section
        for h in view.links
    )


def test_ac_19_a_record_endpoint_lands_on_its_record(view: HeldView) -> None:
    """covers: spec 0005 AC-19 (a `{record}` endpoint)."""
    [link] = [
        h.link
        for h in view.links
        if h.link.source.canonical_id == "0007/AC-13" and h.link.type.name == "UNCLASSIFIED"
    ]

    assert link.target.canonical_id == "0002"
    assert link.target.target is Target.RECORD


def test_every_cross_unit_held_link_carries_its_relationship(corpus: Corpus) -> None:
    assert corpus[1].held
    assert all(link.relationship is not None for link in corpus[1].held)


# AC-19b: a held link nothing stands behind stops the view.


def test_ac_19b_a_cross_unit_held_link_with_no_relationship_raises(corpus: Corpus) -> None:
    """covers: spec 0005 AC-19b (a cross unit held link with no relationship)."""
    results, resolved, records = corpus
    bare = dataclasses.replace(resolved.held[0], relationship=None)
    broken = dataclasses.replace(resolved, held=(bare, *resolved.held[1:]))

    with pytest.raises(HeldViewIncomplete, match="carries no relationship"):
        build_held_view(results, broken, records)


def test_ac_19b_a_held_in_unit_link_with_no_review_item_raises(corpus: Corpus) -> None:
    """covers: spec 0005 AC-19b (a held in unit link with no review item behind it)."""
    results, resolved, records = corpus
    target = unit(results, "0002", "requirements")
    stripped = dataclasses.replace(
        target,
        routed=dataclasses.replace(
            target.routed,
            review=tuple(i for i in target.routed.review if len(i.signature) == 2),
        ),
    )
    edited = tuple(stripped if r is target else r for r in results)

    with pytest.raises(HeldViewIncomplete, match="no review item stands behind it"):
        build_held_view(edited, resolved, records)


# AC-20, AC-20b: which `:Unresolved` nodes the view makes.


def test_ac_20_every_unresolved_node_of_the_view_is_one_no_accepted_link_made(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-20."""
    accepted = {node.canonical_id for node in corpus[1].resolution.unresolved}
    reached = {e.canonical_id for h in view.links for e in (h.link.source, h.link.target)}

    assert view.unresolved
    assert all(node.canonical_id not in accepted for node in view.unresolved)
    assert all(node.canonical_id in reached for node in view.unresolved)


def test_ac_20b_a_held_link_reaching_an_accepted_unresolved_node_makes_no_node(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-20b (the node stays the accepted one, unmarked)."""
    accepted = {node.canonical_id for node in corpus[1].resolution.unresolved}
    shared = {
        e.canonical_id
        for h in view.links
        for e in (h.link.source, h.link.target)
        if e.canonical_id in accepted
    }

    assert shared
    assert not shared & {node.canonical_id for node in view.unresolved}


# AC-21, AC-22, AC-22c: what is already written is skipped, not merged.


def test_ac_21_a_held_entity_whose_id_an_accepted_entity_holds_is_skipped(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-21 (taken by an accepted entity)."""
    results, _, records = corpus
    target = unit(results, "0002", "requirements")
    held = next(h.entity for h in view.entities if h.unit == target.unit)
    # A second unit that accepted the very entity the first one held.
    twin = dataclasses.replace(
        target,
        section_slug="zz-twin",
        routed=dataclasses.replace(
            target.routed, accepted_entities=(held,), accepted_relationships=(), review=()
        ),
        identified=(dataclasses.replace(target.identified[0], entities=(held,), relationships=()),),
    )

    twinned = view_of((*results, twin), records)

    assert held.canonical_id not in {h.entity.canonical_id for h in twinned.entities}
    assert twinned.skipped_entities == view.skipped_entities + 1


def test_ac_21_a_held_entity_whose_id_an_earlier_held_entity_holds_is_skipped(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-21 (taken by an earlier held entity)."""
    results, _, records = corpus
    target = unit(results, "0002", "requirements")
    held_here = sum(1 for h in view.entities if h.unit == target.unit)
    twin = dataclasses.replace(target, section_slug="zz-twin")

    twinned = view_of((*results, twin), records)

    assert len(twinned.entities) == len(view.entities)
    assert twinned.skipped_entities == view.skipped_entities + held_here


def test_ac_22_no_written_held_link_repeats_an_accepted_link(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-22."""
    accepted = {
        (k.type, k.source.canonical_id, k.target.canonical_id) for k in corpus[1].resolution.links
    }
    written = [
        (h.link.type, h.link.source.canonical_id, h.link.target.canonical_id) for h in view.links
    ]

    assert view.skipped_links > 0
    assert not set(written) & accepted


def test_ac_22c_a_held_link_repeating_an_earlier_held_link_is_skipped(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-22c."""
    results, _, records = corpus
    target = unit(results, "0002", "requirements")
    twin = dataclasses.replace(target, section_slug="zz-twin")

    twinned = view_of((*results, twin), records)
    keys = [
        (h.link.type, h.link.source.canonical_id, h.link.target.canonical_id) for h in twinned.links
    ]

    assert len(keys) == len(set(keys))
    assert twinned.links == view.links
    assert twinned.skipped_links > view.skipped_links


# AC-23, AC-23c: rows nothing stands behind, and the sum that must hold.


def test_ac_23_an_entity_row_only_a_later_run_produced_is_not_written(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-23 (an entity row with no first run entity behind it)."""
    results = corpus[0]
    later_only = sum(
        1
        for r in results
        for i in r.routed.review
        if len(i.signature) == 2 and i.canonical_id is None
    )

    assert later_only > 0
    assert view.not_written_entities == later_only


def test_ac_23_a_link_row_only_a_later_run_produced_is_not_written(view: HeldView) -> None:
    """covers: spec 0005 AC-23 (a link row with no first run relationship behind it)."""
    found = {
        (h.link.type.name, h.link.source.canonical_id, h.link.target.canonical_id)
        for h in view.links
    }

    assert view.not_written_links > 0
    # Spec 0005 names it: only a later run produced this one.
    assert ("SUPERSEDED_BY", "0002/AC-10", "0007/AC-13") not in found


def test_ac_23c_entities_written_skipped_and_not_written_add_up(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-23c (entities)."""
    total = len(view.entities) + view.skipped_entities + view.not_written_entities

    assert total == entity_rows(corpus[0])


def test_ac_23c_links_written_skipped_and_not_written_add_up(
    corpus: Corpus, view: HeldView
) -> None:
    """covers: spec 0005 AC-23c (links)."""
    total = len(view.links) + view.skipped_links + view.not_written_links

    assert total == link_rows(corpus[0], corpus[1])


def test_ac_23c_a_sum_that_does_not_hold_stops_the_view(corpus: Corpus) -> None:
    """covers: spec 0005 AC-23c (the load stops)."""
    results, resolved, records = corpus
    target = unit(results, "0002", "requirements")
    first = target.identified[0]
    accepted = target.routed.accepted_relationships
    held = next(r for r in first.relationships if r not in accepted)
    # The first run names one held link twice, and routing queued it once: one more
    # held link than rows, which no count can explain.
    doubled = dataclasses.replace(
        target,
        identified=(
            dataclasses.replace(first, relationships=(*first.relationships, held)),
            *target.identified[1:],
        ),
    )
    edited = tuple(doubled if r is target else r for r in results)

    with pytest.raises(HeldViewIncomplete, match="do not add up"):
        build_held_view(edited, resolved, records)


# The order is fixed, so two builds are the same.


def test_two_builds_over_the_same_artifacts_are_equal(corpus: Corpus, view: HeldView) -> None:
    assert build_held_view(*corpus) == view


def test_the_view_does_not_depend_on_the_order_units_come_in(
    corpus: Corpus, view: HeldView
) -> None:
    results, _, records = corpus

    assert view_of(tuple(reversed(results)), records) == view


def test_the_counts_are_the_six_the_manifest_carries(view: HeldView) -> None:
    """covers: spec 0005 AC-24 (the six names)."""
    assert list(view.counts()) == [
        "entities",
        "links",
        "unresolved",
        "skipped_entities",
        "skipped_links",
        "not_written",
    ]
    assert view.counts()["not_written"] == view.not_written_entities + view.not_written_links
