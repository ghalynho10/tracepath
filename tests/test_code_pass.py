"""The code pass of spec 0007, on crafted runs: no API call, no database.

Each test names the criterion it covers. The runs are built by hand so each case the
spec's Critical test scenarios lists is one change away from a plain released bullet.
"""

from typing import Any

from tracepath.extract.codepass import code_decided_ids, parse_bullets
from tracepath.extract.compare import ReviewReason, ReviewReasonName, RoutedUnit, route_runs
from tracepath.extract.ids import IdentifiedOutput, assign_ids, locate_output
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind

TEXT = """## Requirements

- **AC-1**: The first claim holds.
- **AC-2**: The second claim holds under one condition and under another.
- **AC-3**: ~~An old claim that no longer holds.~~
- **AC-4** : A bullet whose colon sits apart from its id.
  - **AC-5**: A nested bullet, not a top level one.
- **AC-6**: One claim under a repeated id.
- **AC-6**: Another claim under the same id.
"""

FLAG = ReviewReason(ReviewReasonName.KNOWN_TRAP_FLAG)
SPLIT = "multi_condition_split"


def unit_of(text: str = TEXT, section: str = "Requirements") -> Unit:
    return Unit(
        kind=UnitKind.SECTION,
        record_id="0099",
        section=section,
        text=text,
        path="specs/0099-crafted/index.md",
        start_offset=0,
        start_line=1,
    )


def criterion(
    ac: str, span: str, flags: tuple[str, ...] = (), kind: str = "AcceptanceCriterion"
) -> dict[str, Any]:
    return {
        "id": ac,
        "id_source": "verbatim",
        "type": kind,
        "span": span,
        "known_trap_flags": list(flags),
    }


AC1 = "The first claim holds."
AC2 = "The second claim holds under one condition and under another."
AC6 = "One claim under a repeated id."


def run(
    *entities: dict[str, Any], links: tuple[dict[str, Any], ...] = (), unit: Unit | None = None
) -> IdentifiedOutput:
    output = ExtractionOutput.model_validate(
        {"entities": list(entities), "relationships": list(links)}
    )
    return assign_ids(locate_output(unit or unit_of(), output), "0099", "requirements")


def plain(flags: tuple[str, ...] = ()) -> IdentifiedOutput:
    """One run with the two parseable criteria, AC-2 flagged as given."""
    return run(criterion("AC-1", AC1), criterion("AC-2", AC2, flags))


def both(outputs: list[IdentifiedOutput]) -> tuple[RoutedUnit, RoutedUnit]:
    """The unit routed without the pass and with it."""
    return route_runs(outputs), route_runs(outputs, code_decided_ids(unit_of(), outputs))


# AC-9, AC-11 and AC-17's counts: what the parse finds.


def test_ac_9_only_top_level_unstruck_bullets_with_the_exact_opening_parse() -> None:
    """covers: AC-9, AC-17 (the struck and unparsed counts)."""
    parse = parse_bullets(unit_of())

    assert parse.parsed == ("AC-1", "AC-2", "AC-6", "AC-6")
    assert parse.struck == 1, "AC-3 opens with ~~ after the colon"
    assert parse.unparsed == 1, "AC-4 has a space before its colon; AC-5 is nested"


def test_ac_9_a_section_other_than_requirements_parses_nothing() -> None:
    """covers: AC-9 (the section clause)."""
    parse = parse_bullets(unit_of(section="Feature design"))

    assert (parse.parsed, parse.struck, parse.unparsed) == ((), 0, 0)
    outputs = [plain(), plain(), plain()]
    assert code_decided_ids(unit_of(section="Feature design"), outputs) == frozenset()


def test_ac_9_an_optional_lower_case_letter_parses() -> None:
    """covers: AC-9 (`AC-N` with a trailing letter)."""
    parse = parse_bullets(unit_of("## Requirements\n\n- **AC-10b**: A claim.\n- **AC-7B**: No.\n"))

    assert parse.parsed == ("AC-10b",)
    assert parse.unparsed == 1


def test_ac_10_a_bullet_every_run_settles_is_code_decided() -> None:
    """covers: AC-10."""
    outputs = [plain(), plain((SPLIT,)), plain()]

    assert code_decided_ids(unit_of(), outputs) == {"0099/AC-1", "0099/AC-2"}


def test_ac_11_an_id_two_bullets_carry_is_not_decided_and_is_named() -> None:
    """covers: AC-11."""
    outputs = [run(criterion("AC-6", AC6)) for _ in range(3)]

    assert code_decided_ids(unit_of(), outputs) == frozenset()
    assert parse_bullets(unit_of()).repeated == ("AC-6",)


def test_ac_9_a_struck_bullet_is_left_to_the_model() -> None:
    """covers: AC-9 (the `~~` clause), even when every run agrees on its id."""
    struck = "~~An old claim that no longer holds.~~"
    outputs = [run(criterion("AC-3", struck)) for _ in range(3)]

    assert code_decided_ids(unit_of(), outputs) == frozenset()


def test_ac_10_a_run_typing_the_id_otherwise_is_not_decided() -> None:
    """covers: AC-10 (the type clause)."""
    other = run(criterion("AC-1", AC1), criterion("AC-2", AC2, kind="Constraint"))

    assert code_decided_ids(unit_of(), [plain(), other, plain()]) == {"0099/AC-1"}


def test_ac_10_a_run_with_two_claimants_of_the_id_is_not_decided() -> None:
    """covers: AC-10 (exactly one entity carries the id)."""
    twice = run(
        criterion("AC-1", AC1),
        criterion("AC-2", AC2),
        criterion("AC-2", "under one condition"),
    )

    assert code_decided_ids(unit_of(), [plain(), plain(), twice]) == {"0099/AC-1"}


def test_ac_10_a_run_missing_the_id_is_not_decided() -> None:
    """covers: AC-10 (in each of the runs)."""
    missing = run(criterion("AC-1", AC1))

    assert code_decided_ids(unit_of(), [plain(), missing, plain()]) == {"0099/AC-1"}


# AC-12 to AC-14: what routing does with the set.


def test_ac_12_a_split_flag_in_one_run_alone_no_longer_holds_it() -> None:
    """covers: AC-12 (a run with no flag qualifies), AC-12b (the flag is kept)."""
    outputs = [plain((SPLIT,)), plain(), plain()]

    off, on = both(outputs)

    assert [i.canonical_id for i in off.review] == ["0099/AC-2"]
    assert off.review[0].reasons == (FLAG,)
    assert off.released == frozenset()
    assert on.review == ()
    assert on.released == {"0099/AC-2"}
    released = next(e for e in on.accepted_entities if e.canonical_id == "0099/AC-2")
    assert [str(f) for f in released.entity.known_trap_flags] == [SPLIT]


def test_ac_12_another_flag_in_a_later_run_still_holds_it() -> None:
    """covers: AC-12 (every run's flags are read, not only the first's)."""
    outputs = [plain((SPLIT,)), plain(), plain(("rationale_boundary_call",))]

    _, on = both(outputs)

    assert [i.canonical_id for i in on.review] == ["0099/AC-2"]
    assert on.released == frozenset()


def test_ac_12_another_flag_beside_the_split_flag_still_holds_it() -> None:
    """covers: AC-12 (a subset of `multi_condition_split`, nothing more)."""
    outputs = [plain((SPLIT, "embedded_second_claim")), plain(), plain()]

    _, on = both(outputs)

    assert [i.canonical_id for i in on.review] == ["0099/AC-2"]


def test_ac_12c_and_ac_14_a_signature_that_differs_keeps_every_reason() -> None:
    """covers: AC-12c, AC-14 (runs_disagree still holds it, with its full reason list)."""
    labelled = criterion("AC-2", AC2, (SPLIT,))
    outputs = [
        run(criterion("AC-1", AC1), {**labelled, "label": "first"}),
        run(criterion("AC-1", AC1), {**labelled, "label": "second"}),
        run(criterion("AC-1", AC1), {**labelled, "label": "first"}),
    ]

    off, on = both(outputs)

    assert "0099/AC-2" in code_decided_ids(unit_of(), outputs)
    held = [i for i in on.review if i.canonical_id == "0099/AC-2"]
    assert held[0].reasons == (ReviewReason(ReviewReasonName.RUNS_DISAGREE), FLAG)
    assert on.review == off.review
    assert on.released == frozenset()


def test_ac_13_an_entity_accepted_without_the_pass_is_accepted_with_it() -> None:
    """covers: AC-13 (no flag in run 1, another flag in run 2)."""
    outputs = [plain(), plain(("rationale_boundary_call",)), plain()]

    off, on = both(outputs)

    assert off.accepted_entities == on.accepted_entities
    assert {e.canonical_id for e in on.accepted_entities} == {"0099/AC-1", "0099/AC-2"}
    assert on.released == frozenset(), "accepted without the pass, so not released by it"


# AC-15 to AC-15c: only acceptance can differ.


def test_ac_15_the_pass_changes_acceptance_and_nothing_the_runs_wrote() -> None:
    """covers: AC-15, AC-15b (a held entity's row), AC-15c (a held link names only what waits)."""
    link = {
        "type": "satisfies",
        "source": {"kind": "local", "id": "AC-2"},
        "target": {"kind": "local", "id": "AC-1"},
    }
    outputs = [
        run(
            criterion("AC-1", AC1, ("rationale_boundary_call",)),
            criterion("AC-2", AC2, (SPLIT,)),
            links=(link,),
        )
        for _ in range(3)
    ]
    snapshot = [(o.entities, o.relationships) for o in outputs]

    off, on = both(outputs)

    assert [(o.entities, o.relationships) for o in outputs] == snapshot
    assert off.comparison == on.comparison
    held_off = [i for i in off.review if i.canonical_id == "0099/AC-1"]
    held_on = [i for i in on.review if i.canonical_id == "0099/AC-1"]
    assert held_on == held_off
    [link_off] = [i for i in off.review if len(i.signature) == 3]
    [link_on] = [i for i in on.review if len(i.signature) == 3]
    assert link_off.signature == link_on.signature
    assert [r.detail for r in link_off.reasons] == ["0099/AC-2", "0099/AC-1"]
    assert [r.detail for r in link_on.reasons] == ["0099/AC-1"]
    assert {e.canonical_id for e in on.accepted_entities} == {"0099/AC-2"}
    assert off.accepted_entities == ()
