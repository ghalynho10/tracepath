"""The narrow hold rule of spec 0008, on crafted runs and the committed runs: no database.

Each test names the criterion it covers. The crafted runs reuse the code pass tests'
unit and helpers, so each case is one change away from a plain flag only criterion.
"""

from collections import Counter
from typing import Any

import pytest

from tests.test_code_pass import AC1, AC2, SPLIT, criterion, run, unit_of
from tests.test_code_pass_commands import COMMIT, ROOT, SNAPSHOT
from tracepath.extract.codepass import code_decided_ids
from tracepath.extract.compare import (
    NARROW_HOLD,
    ReviewReason,
    ReviewReasonName,
    RoutedUnit,
    route_runs,
)
from tracepath.extract.ids import IdentifiedOutput, assign_ids, locate_output
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind
from tracepath.graph.model import Provenance, link_row
from tracepath.pipeline import (
    CorpusResolution,
    UnitResult,
    graph_build,
    resolve_accepted,
    review_rows,
)
from tracepath.rebuild import (
    apply_code_pass,
    apply_narrow_hold,
    committed_units,
    narrow_hold_tally,
    narrow_link_keys,
    records_for_units,
    released_links,
)
from tracepath.resolve.endpoints import Resolution

FLAG = ReviewReason(ReviewReasonName.KNOWN_TRAP_FLAG)
DISAGREE = ReviewReason(ReviewReasonName.RUNS_DISAGREE)
FAR = "Every seeded listing carries an obviously fake company name."


def waiting(on: str) -> ReviewReason:
    return ReviewReason(ReviewReasonName.ENDPOINT_NOT_ACCEPTED, detail=on)


def satisfies(source: str, target: str, flags: tuple[str, ...] = ()) -> dict[str, Any]:
    """A local link from one criterion to another, flagged as given."""
    return {
        "type": "satisfies",
        "source": {"kind": "local", "id": source},
        "target": {"kind": "local", "id": target},
        "known_trap_flags": list(flags),
    }


def three(
    *entities: dict[str, Any], links: tuple[dict[str, Any], ...] = ()
) -> list[IdentifiedOutput]:
    """Three runs that agree on every signature."""
    return [run(*entities, links=links) for _ in range(3)]


def narrowed(outputs: list[IdentifiedOutput]) -> tuple[RoutedUnit, RoutedUnit]:
    """The unit routed without the rule and with it."""
    return route_runs(outputs), route_runs(outputs, narrow_hold=True)


def accepted(routed: RoutedUnit) -> set[str]:
    return {e.canonical_id for e in routed.accepted_entities}


def link_items(routed: RoutedUnit) -> list[Any]:
    return [i for i in routed.review if len(i.signature) == 3]


# AC-1, AC-1b: the flag is off by default, and what it releases.


def test_ac_1_routing_holds_a_flag_only_entity_unless_the_rule_is_asked_for() -> None:
    """covers: AC-1 (the default routing is unchanged; the rule is opt in)."""
    outputs = three(criterion("AC-1", AC1), criterion("AC-2", AC2, (SPLIT,)))

    default = route_runs(outputs)

    assert [i.canonical_id for i in default.review] == ["0099/AC-2"]
    assert default.narrow_released == ()


def test_ac_1b_a_flag_only_entity_the_runs_agree_on_is_released() -> None:
    """covers: AC-1b (known_trap_flag alone, runs_disagree absent)."""
    off, on = narrowed(three(criterion("AC-1", AC1), criterion("AC-2", AC2, (SPLIT,))))

    assert off.review[0].reasons == (FLAG,)
    assert on.review == ()
    assert accepted(on) == {"0099/AC-1", "0099/AC-2"}
    assert on.narrow_entities == {"0099/AC-2"}
    [release] = on.narrow_released
    assert release.item.reasons == (FLAG,), "released with the reasons that held it"
    assert release.flags == (SPLIT,)


def test_ac_1b_a_flagged_link_waiting_on_a_released_entity_is_released() -> None:
    """covers: AC-1b (known_trap_flag and endpoint_not_accepted together)."""
    outputs = three(
        criterion("AC-1", AC1),
        criterion("AC-2", AC2, (SPLIT,)),
        links=(satisfies("AC-2", "AC-1", ("relationship_type_ambiguous",)),),
    )

    off, on = narrowed(outputs)

    [held] = link_items(off)
    assert held.reasons == (FLAG, waiting("0099/AC-2"))
    assert link_items(on) == []
    assert len(on.accepted_relationships) == 1
    [link] = [r for r in on.narrow_released if r.relationship is not None]
    assert link.item.reasons == (FLAG, waiting("0099/AC-2"))
    assert link.flags == ("relationship_type_ambiguous",)


def test_ac_1b_runs_disagree_beside_a_flag_keeps_the_entity_held() -> None:
    """covers: AC-1b (runs_disagree absent is part of the condition)."""
    labelled = criterion("AC-2", AC2, (SPLIT,))
    outputs = [
        run(criterion("AC-1", AC1), {**labelled, "label": "first"}),
        run(criterion("AC-1", AC1), {**labelled, "label": "second"}),
        run(criterion("AC-1", AC1), {**labelled, "label": "first"}),
    ]

    off, on = narrowed(outputs)

    held = [i for i in on.review if i.canonical_id == "0099/AC-2"]
    assert held[0].reasons == (DISAGREE, FLAG)
    assert on.review == off.review
    assert on.narrow_released == ()


# AC-1c: span_not_located and unclassified_type are never released.


def unlocatable(flags: tuple[str, ...] = ()) -> dict[str, Any]:
    """A derived entity whose span belongs to another document, so it cannot be located."""
    return {
        "id": "derived:1",
        "id_source": "derived",
        "type": "Constraint",
        "span": FAR,
        "known_trap_flags": list(flags),
    }


def unclassified(flags: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "id": "AC-1",
        "id_source": "verbatim",
        "type": "unclassified",
        "span": AC1,
        "unclassified_note": "reads as a criterion and a constraint at once",
        "known_trap_flags": list(flags),
    }


@pytest.mark.parametrize(
    ("entity", "kept"),
    [
        (unlocatable(), (ReviewReasonName.SPAN_NOT_LOCATED,)),
        (
            unlocatable((SPLIT,)),
            (ReviewReasonName.KNOWN_TRAP_FLAG, ReviewReasonName.SPAN_NOT_LOCATED),
        ),
        (unclassified(), (ReviewReasonName.UNCLASSIFIED_TYPE,)),
        (
            unclassified((SPLIT,)),
            (ReviewReasonName.KNOWN_TRAP_FLAG, ReviewReasonName.UNCLASSIFIED_TYPE),
        ),
    ],
    ids=["span alone", "span with a flag", "unclassified alone", "unclassified with a flag"],
)
def test_ac_1c_span_not_located_and_unclassified_type_stay_held(
    entity: dict[str, Any], kept: tuple[ReviewReasonName, ...]
) -> None:
    """covers: AC-1c (alone or beside a releasable reason)."""
    off, on = narrowed(three(entity))

    assert [r.name for r in on.review[0].reasons] == list(kept)
    assert on.review == off.review
    assert on.narrow_released == ()
    assert on.accepted_entities == ()


# AC-1d: the written copy is the first settled run's.


def test_ac_1d_a_released_entity_is_written_from_the_first_run() -> None:
    """covers: AC-1d (span text is not in the signature, so the runs agree; run 1's copy wins)."""
    shorter = "The second claim holds under one condition"
    outputs = [
        run(criterion("AC-2", AC2, (SPLIT,))),
        run(criterion("AC-2", shorter, (SPLIT,))),
        run(criterion("AC-2", shorter, (SPLIT,))),
    ]

    _, on = narrowed(outputs)

    [written] = on.accepted_entities
    assert written.entity.span == AC2
    assert written is outputs[0].entities[0]


def test_ac_1d_an_item_two_runs_found_and_a_third_did_not_stays_held() -> None:
    """covers: AC-1d (no other run's copy is taken: runs_disagree keeps it held)."""
    outputs = [run(unlocatable((SPLIT,))), run(unlocatable((SPLIT,))), run()]

    _, on = narrowed(outputs)

    assert on.accepted_entities == ()
    assert ReviewReason(ReviewReasonName.RUNS_DISAGREE) in on.review[0].reasons
    assert on.narrow_released == ()


# AC-2: a waiting link releases only when every entity it waits on is accepted.


def test_ac_2_a_link_waiting_on_an_entity_still_held_stays_held() -> None:
    """covers: AC-2 (the entity it waits on is held for runs_disagree)."""
    labelled = criterion("AC-2", AC2, (SPLIT,))
    link = (satisfies("AC-2", "AC-1"),)
    outputs = [
        run(criterion("AC-1", AC1), {**labelled, "label": "first"}, links=link),
        run(criterion("AC-1", AC1), {**labelled, "label": "second"}, links=link),
        run(criterion("AC-1", AC1), {**labelled, "label": "first"}, links=link),
    ]

    _, on = narrowed(outputs)

    [held] = link_items(on)
    assert held.reasons == (waiting("0099/AC-2"),)
    assert on.accepted_relationships == ()


def test_ac_2_the_same_link_releases_once_its_entity_releases() -> None:
    """covers: AC-2, AC-3b (released, and listed as the rule's own link release)."""
    outputs = three(
        criterion("AC-1", AC1),
        criterion("AC-2", AC2, (SPLIT,)),
        links=(satisfies("AC-2", "AC-1"),),
    )

    off, on = narrowed(outputs)

    assert [i.reasons for i in link_items(off)] == [(waiting("0099/AC-2"),)]
    assert link_items(on) == []
    assert [r.item.reasons for r in on.narrow_released if r.relationship] == [
        (waiting("0099/AC-2"),)
    ]


def test_ac_2_a_link_waiting_on_two_entities_stays_held_while_one_waits() -> None:
    """covers: AC-2 (every entity it waits on; its queue row names only the one still waiting)."""
    link = (satisfies("AC-2", "AC-1"),)
    outputs = [
        run(
            {**criterion("AC-1", AC1), "label": label}, criterion("AC-2", AC2, (SPLIT,)), links=link
        )
        for label in ("x", "y", "x")
    ]

    off, on = narrowed(outputs)

    assert [i.reasons for i in link_items(off)] == [(waiting("0099/AC-2"), waiting("0099/AC-1"))]
    assert on.narrow_entities == {"0099/AC-2"}
    assert [i.reasons for i in link_items(on)] == [(waiting("0099/AC-1"),)]


def test_ac_2_a_code_pass_release_counts_as_accepted() -> None:
    """covers: AC-2 (an entity the code pass released frees the link the rule then releases)."""
    outputs = three(
        criterion("AC-1", AC1),
        criterion("AC-2", AC2, (SPLIT,)),
        links=(satisfies("AC-2", "AC-1", ("relationship_type_ambiguous",)),),
    )
    decided = code_decided_ids(unit_of(), outputs)

    on = route_runs(outputs, decided, narrow_hold=True)

    assert on.released == {"0099/AC-2"}
    assert link_items(on) == []
    [link] = on.narrow_released
    assert link.item.reasons == (FLAG,), "the code pass accepted its end, so only its flag held it"


# AC-2 across units: a link held for an entity in another unit.


ELSEWHERE = "## Requirements\n\n- **AC-1**: A claim elsewhere.\n"


def a_unit(record: str, text: str) -> Unit:
    return Unit(
        kind=UnitKind.SECTION,
        record_id=record,
        section="Requirements",
        text=text,
        path=f"specs/{record}-crafted/index.md",
        start_offset=0,
        start_line=1,
    )


def elsewhere() -> list[IdentifiedOutput]:
    """Three runs of 0098, whose AC-1 satisfies 0099's AC-2 by reference."""
    link = {
        "type": "satisfies",
        "source": {"kind": "local", "id": "AC-1"},
        "target": {"kind": "reference", "record": "0099", "id": "AC-2", "mention": "0099 AC-2"},
    }
    output = ExtractionOutput.model_validate(
        {"entities": [criterion("AC-1", "A claim elsewhere.")], "relationships": [link]}
    )
    unit = a_unit("0098", ELSEWHERE)
    return [assign_ids(locate_output(unit, output), "0098", "requirements") for _ in range(3)]


def corpus_of(
    here: list[IdentifiedOutput], *, narrow: bool
) -> tuple[list[UnitResult], CorpusResolution]:
    """0099 from `here` and 0098 from `elsewhere()`, routed and resolved together."""
    results = [
        UnitResult(
            unit=unit,
            section_slug="requirements",
            artifacts=(),
            identified=tuple(outputs),
            routed=route_runs(outputs, narrow_hold=narrow),
            input_tokens=0,
            output_tokens=0,
        )
        for unit, outputs in ((unit_of(), here), (a_unit("0098", ELSEWHERE), elsewhere()))
    ]
    return results, resolve_accepted(results, ())


FLAG_ONLY = [run(criterion("AC-2", AC2, (SPLIT,))) for _ in range(3)]
DISAGREEING = [run({**criterion("AC-2", AC2), "label": label}) for label in ("a", "b", "a")]


def test_ac_2_a_link_held_across_units_releases_with_the_entity_it_waits_on() -> None:
    """covers: AC-2, AC-5 (an endpoint_not_accepted release counted across units)."""
    _, before = corpus_of(FLAG_ONLY, narrow=False)
    results, after = corpus_of(FLAG_ONLY, narrow=True)

    assert [h.item.reasons for h in before.held] == [(waiting("0099/AC-2"),)]
    assert after.held == ()
    assert len(released_links(before, after)) == 1
    tally = narrow_hold_tally(before, results, after)
    assert (tally.entities, tally.links) == (1, 1)
    assert dict(tally.by_reason) == {"known_trap_flag": 1, "endpoint_not_accepted": 1}
    assert dict(tally.by_flag) == {SPLIT: 1}


def test_ac_2_a_link_held_across_units_stays_held_when_its_entity_does() -> None:
    """covers: AC-2 (the entity in the other unit is held for runs_disagree)."""
    results, after = corpus_of(DISAGREEING, narrow=True)

    assert [h.item.reasons for h in after.held] == [(waiting("0099/AC-2"),)]
    assert after.resolution.links == ()
    _, before = corpus_of(DISAGREEING, narrow=False)
    assert narrow_hold_tally(before, results, after).links == 0


# AC-3b, AC-4: the stamps.


def test_ac_4_with_both_rules_the_code_pass_stamp_wins() -> None:
    """covers: AC-4 (both given: the code pass released it, not the rule)."""
    outputs = three(criterion("AC-1", AC1), criterion("AC-2", AC2, (SPLIT,)))
    decided = code_decided_ids(unit_of(), outputs)

    both_on = route_runs(outputs, decided, narrow_hold=True)
    narrow_alone = route_runs(outputs, narrow_hold=True)

    assert both_on.released == {"0099/AC-2"}
    assert both_on.narrow_entities == frozenset()
    assert narrow_alone.released == frozenset()
    assert narrow_alone.narrow_entities == {"0099/AC-2"}, "the code pass did not run"


PROVENANCE = Provenance("m", "0003.1", "2026-10-01T00:00:00+00:00", "auto", COMMIT)


def test_ac_3b_a_link_row_carries_accepted_by_only_when_the_rule_released_it() -> None:
    """covers: AC-3b (no link carried a value before; a released link carries narrow_hold)."""
    results, after = corpus_of(FLAG_ONLY, narrow=True)
    [link] = after.resolution.links

    assert "accepted_by" not in link_row(link, PROVENANCE)["properties"]
    assert link_row(link, PROVENANCE, NARROW_HOLD)["properties"]["accepted_by"] == "narrow_hold"
    _, before = corpus_of(FLAG_ONLY, narrow=False)
    assert narrow_link_keys(before, after) == {
        (link.type, link.source.canonical_id, link.target.canonical_id)
    }
    assert results[0].routed.narrow_entities == {"0099/AC-2"}


# AC-5c: the manifest key.


def test_ac_5c_the_manifest_has_a_narrow_hold_key_only_when_the_rule_ran() -> None:
    """covers: AC-5c, AC-5 (the key, and the counts beside it)."""
    empty = CorpusResolution(Resolution((), ()), ())
    counts = {"entities": 1, "links": 0}

    plain = graph_build((), empty, (), COMMIT, 0, {})
    narrow = graph_build((), empty, (), COMMIT, 0, {}, narrow_hold=counts)

    assert "narrow_hold" not in plain
    assert "narrow_hold_released" not in plain
    assert narrow["narrow_hold"] is True
    assert narrow["narrow_hold_released"] == counts


# AC-5, AC-6: over the committed runs.


Routed = tuple[tuple[UnitResult, ...], CorpusResolution]


@pytest.fixture(scope="module")
def routings() -> dict[str, Routed]:
    """The committed corpus routed four ways: neither, code pass, narrow hold, both."""
    plain = committed_units(ROOT, SNAPSHOT)
    records = records_for_units(plain, SNAPSHOT, COMMIT)
    found = {
        "plain": plain,
        "code": apply_code_pass(plain),
        "narrow": apply_narrow_hold(plain),
        "both": apply_narrow_hold(plain, code_pass=True),
    }
    return {name: (results, resolve_accepted(results, records)) for name, results in found.items()}


def accepted_ids(routed: Routed) -> set[str]:
    return {e.canonical_id for r in routed[0] for e in r.routed.accepted_entities}


def link_multiset(routed: Routed) -> Counter[Any]:
    return Counter(routed[1].resolution.links)


@pytest.mark.slow
def test_ac_6_every_release_of_either_rule_alone_survives_both(routings: dict[str, Routed]) -> None:
    """covers: AC-6 (the union is monotone, entities and links alike)."""
    both = routings["both"]
    for alone in ("plain", "code", "narrow"):
        assert accepted_ids(routings[alone]) <= accepted_ids(both), alone
        assert not link_multiset(routings[alone]) - link_multiset(both), alone
    assert accepted_ids(routings["narrow"]) | accepted_ids(routings["code"]) == accepted_ids(both)


@pytest.mark.slow
def test_ac_6_no_entity_is_released_twice(routings: dict[str, Routed]) -> None:
    """covers: AC-6, AC-4 (with both, an entity is the code pass's or the rule's, never both)."""
    both = routings["both"][0]
    code = {i for r in routings["code"][0] for i in r.released}
    assert code, "the committed runs hold code pass releases"
    assert {i for r in both for i in r.released} == code
    for result in both:
        assert not result.released & result.routed.narrow_entities


@pytest.mark.slow
def test_ac_5_the_tally_matches_a_count_off_the_two_queues(routings: dict[str, Routed]) -> None:
    """covers: AC-5 (released items, by reason and flag, counted from the queues' row keys)."""
    plain_results, before = routings["plain"]
    narrow_results, after = routings["narrow"]
    tally = narrow_hold_tally(before, narrow_results, after)

    def keyed(results: tuple[UnitResult, ...], corpus: CorpusResolution) -> Counter[Any]:
        rows = review_rows(results, corpus.held, "m", "t")
        return Counter((r["record"], r["section"], str(r["signature"])) for r in rows)

    gone = keyed(plain_results, before) - keyed(narrow_results, after)
    plain_rows = review_rows(plain_results, before.held, "m", "t")
    reasons: Counter[str] = Counter()
    both = 0
    remaining = Counter(gone)
    for row in plain_rows:
        key = (row["record"], row["section"], str(row["signature"]))
        if remaining[key] == 0:
            continue
        remaining[key] -= 1
        names = {r["name"] for r in row["reasons"]}
        reasons.update(names)
        both += {"known_trap_flag", "endpoint_not_accepted"} <= names

    assert tally.entities + tally.links == sum(gone.values())
    assert tally.links == len(released_links(before, after))
    assert dict(tally.by_reason) == {
        "known_trap_flag": reasons["known_trap_flag"],
        "endpoint_not_accepted": reasons["endpoint_not_accepted"],
    }
    assert tally.held_for_both == both
    assert tally.entities == sum(len(r.routed.narrow_entities) for r in narrow_results)


@pytest.mark.slow
def test_ac_2_every_released_link_has_every_end_accepted(routings: dict[str, Routed]) -> None:
    """covers: AC-2, key invariant 3 (no written link ends on a held entity)."""
    results, after = routings["narrow"]
    known = {e.canonical_id for r in results for e in r.identified[0].entities}
    held = known - accepted_ids(routings["narrow"])
    for link in after.resolution.links:
        assert link.source.canonical_id not in held
        assert link.target.canonical_id not in held
