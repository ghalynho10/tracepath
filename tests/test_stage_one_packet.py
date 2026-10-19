"""Stage one's sampler and blind packet (spec 0007 step 7), on crafted runs.

No API call, no database. Each test names the criterion it covers. The runs are built
by hand so one entity is released by the code pass and one is accepted either way.
"""

import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.conftest import pre_feature_9_runs
from tracepath.artifacts import RUNS_DIR
from tracepath.extract.codepass import code_decided_ids
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import IdentifiedOutput, assign_ids, locate_output
from tracepath.extract.schema import ExtractionOutput, RelationshipType
from tracepath.extract.units import Unit, UnitKind
from tracepath.measure import (
    CONTROL,
    FAIL,
    INCONCLUSIVE,
    PASS,
    RELEASED,
    RULED_BY,
    EntityMark,
    Ruling,
    RulingsRefused,
    arm_key,
    arm_score,
    build_packet,
    control_marks,
    draw,
    flip_bundled,
    held_items,
    packet_markdown,
    parse_rulings,
    regressions,
    released_marks,
    stage_one_verdict,
    unit_gate,
)
from tracepath.pipeline import CorpusResolution, UnitResult
from tracepath.resolve.endpoints import Resolution, ResolvedEndpoint, ResolvedLink, Target

ROOT = Path(__file__).resolve().parents[1]
STEP = ROOT / "experiments" / "0012-extraction-accuracy-step-one"
SCRIPT = STEP / "prepare_stage_one.py"
SCORE = STEP / "score_stage_one.py"

TEXT = """## Requirements

- **AC-1**: The first claim holds.
- **AC-2**: The second claim holds under one condition and under another.
"""
AC1 = "The first claim holds."
AC2 = "The second claim holds under one condition and under another."
SPLIT = "multi_condition_split"
ADDRESS = "0099:Requirements"

UNIT = Unit(
    kind=UnitKind.SECTION,
    record_id="0099",
    section="Requirements",
    text=TEXT,
    path="specs/0099-crafted/index.md",
    start_offset=0,
    start_line=10,
)


def criterion(ac: str, span: str, flags: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "id": ac,
        "id_source": "verbatim",
        "type": "AcceptanceCriterion",
        "span": span,
        "known_trap_flags": list(flags),
        "rejected_spans": ["a rejected clause"],
    }


def run(flags: tuple[str, ...] = ()) -> IdentifiedOutput:
    output = ExtractionOutput.model_validate(
        {"entities": [criterion("AC-1", AC1), criterion("AC-2", AC2, flags)], "relationships": []}
    )
    return assign_ids(locate_output(UNIT, output), "0099", "requirements")


def results() -> tuple[UnitResult, UnitResult]:
    """The unit routed without the pass and with it: AC-2 is held by its flag alone."""
    outputs = [run((SPLIT,)), run(), run()]

    def result(code_pass: bool) -> UnitResult:
        decided = code_decided_ids(UNIT, outputs) if code_pass else frozenset()
        return UnitResult(
            unit=UNIT,
            section_slug="requirements",
            artifacts=(),
            identified=tuple(outputs),
            routed=route_runs(outputs, decided),
            input_tokens=0,
            output_tokens=0,
        )

    return result(False), result(True)


def mark(n: int, unit: str = ADDRESS, span: str | None = None) -> EntityMark:
    return EntityMark(
        unit=unit,
        canonical_id=f"0099/AC-{n}",
        span=span or f"claim {n}",
        type="AcceptanceCriterion",
        source=f"specs/0099-crafted/index.md:{n}",
    )


def test_ac_25_and_ac_25b_each_arm_draws_from_its_own_pool() -> None:
    """covers: AC-25 (the control's accepted entities), AC-25b (the released ones)."""
    without, with_pass = results()

    assert [m.canonical_id for m in control_marks(without, ADDRESS)] == ["0099/AC-1"]
    assert [m.canonical_id for m in released_marks(with_pass, ADDRESS)] == ["0099/AC-2"]
    assert released_marks(without, ADDRESS) == ()


def test_a_mark_cites_its_line_from_the_top_of_its_file() -> None:
    """covers: AC-26d (the source line), counted as the eval and the graph count it."""
    _, with_pass = results()

    (released,) = released_marks(with_pass, ADDRESS)

    assert released.source == "specs/0099-crafted/index.md:13"
    assert released.span == AC2


def test_ac_25c_a_draw_records_its_seed_and_repeats_under_it() -> None:
    """covers: AC-25c."""
    pool = [mark(n) for n in range(1, 21)]

    first = draw(ADDRESS, RELEASED, pool, 5, 1234)

    assert first.seed == 1234
    assert first == draw(ADDRESS, RELEASED, pool, 5, 1234)
    assert len(first.marks) == 5 and first.shortfall == 0


def test_ac_25d_a_draw_asking_too_many_takes_all_and_states_the_shortfall() -> None:
    """covers: AC-25d."""
    pool = [mark(1), mark(2), mark(3)]

    short = draw(ADDRESS, RELEASED, pool, 5, 7)

    assert sorted(short.marks, key=lambda m: m.canonical_id) == pool
    assert (short.asked, short.pool, short.shortfall) == (5, 3, 2)


def test_ac_26_items_are_shuffled_under_opaque_ids_grouped_by_unit() -> None:
    """covers: AC-26."""
    draws = [
        draw("A", RELEASED, [mark(n, "A") for n in range(1, 6)], 5, 1),
        draw("A", CONTROL, [mark(n, "A") for n in range(6, 9)], 3, 2),
        draw("B", RELEASED, [mark(n, "B") for n in range(1, 6)], 5, 3),
        draw("B", CONTROL, [mark(n, "B") for n in range(6, 9)], 3, 4),
    ]

    items = build_packet(draws, ["A", "B"], 99)

    assert [i.opaque_id for i in items] == [f"P{n:02d}" for n in range(1, 17)]
    assert [i.mark.unit for i in items] == ["A"] * 8 + ["B"] * 8
    order = [i.mark.canonical_id for i in items[:8]]
    assert order != sorted(order), "the items of a unit are shuffled"
    assert items == build_packet(draws, ["A", "B"], 99)


def test_ac_27_a_mark_both_arms_drew_is_one_item_naming_both() -> None:
    """covers: AC-27 (same canonical id, same span text)."""
    same = mark(1)
    draws = [draw(ADDRESS, RELEASED, [same], 1, 1), draw(ADDRESS, CONTROL, [same, mark(2)], 2, 2)]

    items = build_packet(draws, [ADDRESS], 5)

    assert len(items) == 2
    assert {i.mark.canonical_id: i.arms for i in items}["0099/AC-1"] == (CONTROL, RELEASED)


def test_ac_26d_the_packet_shows_no_flag_reason_canonical_id_or_arm() -> None:
    """covers: AC-26d, on a sample drawn from crafted runs with a released flagged item."""
    without, with_pass = results()
    draws = [
        draw(ADDRESS, RELEASED, released_marks(with_pass, ADDRESS), 5, 1),
        draw(ADDRESS, CONTROL, control_marks(without, ADDRESS), 3, 2),
    ]
    items = build_packet(draws, [ADDRESS], 3)

    text = packet_markdown(items, "Packet", "Rule each item.")

    for forbidden in (
        SPLIT,
        "known_trap_flag",
        "a rejected clause",
        "0099/AC-1",
        "0099/AC-2",
        RELEASED,
        CONTROL,
        "arm",
    ):
        assert forbidden not in text
    for item in items:
        assert f"`{item.opaque_id}` · AcceptanceCriterion" in text
        assert f"  - span: {item.mark.span}" in text
        assert f"  - source: {item.mark.source}" in text


def test_ac_26b_the_arm_key_names_every_item_and_every_seed() -> None:
    """covers: AC-25c (seeds recorded), AC-26b (the file naming each item's arm)."""
    draws = [draw(ADDRESS, RELEASED, [mark(1)], 5, 11), draw(ADDRESS, CONTROL, [mark(2)], 3, 12)]
    items = build_packet(draws, [ADDRESS], 13)

    key = json.loads(json.dumps(arm_key(items, draws, 13)))

    assert key["shuffle_seed"] == 13
    assert [(d["arm"], d["seed"], d["shortfall"]) for d in key["draws"]] == [
        (RELEASED, 11, 4),
        (CONTROL, 12, 2),
    ]
    named = {i["opaque_id"]: i["arms"] for i in key["items"]}
    assert named == {i.opaque_id: list(i.arms) for i in items}


def load_script(path: Path = SCRIPT) -> ModuleType:
    name = f"exp0012_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_script_refuses_to_draw_a_second_sample(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A sample is drawn once: a second draw could replace a sample already seen."""
    script = load_script()
    for name in ("PACKET", "ARMS", "HASH"):
        monkeypatch.setattr(script, name, tmp_path / name.lower())
    (tmp_path / "arms").write_text("{}")

    with pytest.raises(SystemExit, match="already exist"):
        script.build()


# After the rulings: parse, flip, score and gate (AC-18c, AC-19 to AC-19c, AC-26e).

RULED = """# Packet

## 0099:Requirements

- [x] agree · `P01` · AcceptanceCriterion

  - source: specs/0099-crafted/index.md:12
  - span: claim 1
  - reason: gap:bundled-ac (two conditions)

- [x] disagree · `P02` · Feature
  - source: specs/0099-crafted/index.md:13
  - span: claim 2
  - reason: needs knowledge not in the text

- [ ] agree / disagree / unsure · `P03` · AcceptanceCriterion
  - span: claim 3
  - reason:

- [x] unsure · `P04` · AcceptanceCriterion
  - span: claim 4
  - reason:
"""


def test_rulings_are_read_from_the_ticked_lines_with_their_reasons() -> None:
    """covers: AC-18e (an unruled item is absent, so it is reported apart)."""
    rulings = parse_rulings(RULED)

    assert {i: r.mark for i, r in rulings.items()} == {
        "P01": "agree",
        "P02": "disagree",
        "P04": "unsure",
    }
    assert rulings["P01"].reason == "gap:bundled-ac (two conditions)"


def test_a_ticked_line_whose_mark_cannot_be_read_is_refused() -> None:
    """A misread mark would score silently, so it stops the scoring."""
    with pytest.raises(RulingsRefused, match="P01"):
        parse_rulings(RULED.replace("- [x] agree · `P01`", "- [x] agre · `P01`"))


def test_an_item_ruled_twice_is_refused() -> None:
    """Two rulings of one item would leave the score to whichever was read last."""
    twice = RULED + "\n- [x] agree · `P02` · Feature\n  - reason:\n"

    with pytest.raises(RulingsRefused, match="P02 is ruled twice"):
        parse_rulings(twice)


def test_ac_26e_a_bundled_agree_on_an_unflagged_entity_counts_disagree() -> None:
    """covers: AC-26e (flipped only when tagged, ruled agree and unflagged; counted)."""
    rulings = parse_rulings(RULED)

    after, flipped = flip_bundled(rulings, frozenset())
    kept, none = flip_bundled(rulings, frozenset({"P01"}))

    assert flipped == ("P01",) and after["P01"].mark == "disagree"
    assert none == () and kept["P01"].mark == "agree"
    assert after["P02"] == rulings["P02"]


def test_ac_19_and_ac_18c_every_mark_not_ruled_agree_counts_against() -> None:
    """covers: AC-19 (4 of 5), AC-18c (unsure counts against in the gate), AC-18d."""
    rulings = {f"P{n}": Ruling(f"P{n}", "agree", "") for n in range(1, 4)}
    rulings["P4"] = Ruling("P4", "unsure", "")
    ids = ["P1", "P2", "P3", "P4", "P5"]

    three = arm_score(ids, rulings)
    four = arm_score(ids, {**rulings, "P5": Ruling("P5", "agree", "")})

    assert (three.agree, three.unsure, three.unruled) == (3, 1, 1)
    assert unit_gate(three) == FAIL
    assert unit_gate(four) == PASS
    knowledge = arm_score(["P02"], parse_rulings(RULED))
    assert (knowledge.disagree, knowledge.knowledge) == (1, 1)


def test_ac_19c_fewer_than_5_released_is_inconclusive_and_holds_stage_one() -> None:
    """covers: AC-19c, and AC-19b's place in the verdict."""
    all_agree = {f"P{n}": Ruling(f"P{n}", "agree", "") for n in range(1, 4)}

    short = unit_gate(arm_score(["P1", "P2", "P3"], all_agree))

    assert short == INCONCLUSIVE
    assert stage_one_verdict([PASS, INCONCLUSIVE, PASS], ()) == INCONCLUSIVE
    assert stage_one_verdict([PASS, PASS], ()) == PASS
    assert stage_one_verdict([PASS, INCONCLUSIVE], ()) == INCONCLUSIVE
    assert stage_one_verdict([PASS, PASS], ("entity lost",)) == FAIL
    assert stage_one_verdict([FAIL, INCONCLUSIVE], ()) == FAIL


def test_ac_19b_an_entity_accepted_only_without_the_pass_is_named_lost() -> None:
    """covers: AC-19b (checked by code over the chosen units)."""
    without, with_pass = results()
    empty = CorpusResolution(Resolution((), ()), ())
    chosen = [("0099", "Requirements")]

    assert regressions([without], [with_pass], empty, empty, chosen) == ()
    # Read the arms the other way round, the released entity is what a pass would lose.
    assert regressions([with_pass], [without], empty, empty, chosen) == ("entity 0099/AC-2 lost",)
    assert regressions([with_pass], [without], empty, empty, []) == ()


def test_ac_28b_held_items_are_the_units_queue_rows() -> None:
    """covers: AC-28b."""
    without, with_pass = results()
    empty = CorpusResolution(Resolution((), ()), ())

    assert (held_items(without, empty), held_items(with_pass, empty)) == (1, 0)


def link(file: str = "specs/0099-crafted/index.md", line: int = 12) -> ResolvedLink:
    return ResolvedLink(
        type=RelationshipType.SATISFIES,
        source=ResolvedEndpoint("0099/AC-2", Target.ENTITY),
        target=ResolvedEndpoint("0099/AC-1", Target.ENTITY),
        phrase=None,
        date=None,
        source_record="0099",
        file=file,
        section="Requirements",
        line=line,
    )


def test_ac_19b_a_link_accepted_only_without_the_pass_is_named_lost() -> None:
    """covers: AC-19b (the links: in the chosen units only, counted as a multiset)."""
    without, with_pass = results()
    chosen = [("0099", "Requirements")]
    ours, other = link(), link("specs/0098-other/index.md", 4)

    def lost(before: tuple[ResolvedLink, ...], after: tuple[ResolvedLink, ...]) -> tuple[str, ...]:
        return regressions(
            [without],
            [with_pass],
            CorpusResolution(Resolution(before, ()), ()),
            CorpusResolution(Resolution(after, ()), ()),
            chosen,
        )

    assert lost((ours, other), ()) == (
        "link 0099 satisfies at specs/0099-crafted/index.md:12 lost",
    ), "the link in a unit not chosen is not checked"
    assert lost((ours,), (ours,)) == ()
    assert len(lost((ours, ours), (ours,))) == 1, "one of two equal links lost is a loss"


# The scoring script itself (experiment 0012's `score_stage_one.py`), on committed files.


def test_ac_29b_scoring_refuses_runs_on_another_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """covers: AC-29b (a `units.json` expecting another model than the runs name)."""
    script = load_script(SCORE)
    # A root holding only the one unit's runs and the READMEs AC-24 reads, so the
    # script rebuilds one unit, not the whole corpus.
    root = tmp_path / "root"
    shutil.copytree(ROOT / RUNS_DIR / "0009", root / RUNS_DIR / "0009")
    for readme in RULED_BY:
        (root / readme).parent.mkdir(parents=True)
        shutil.copy(ROOT / readme, root / readme)
    monkeypatch.setattr(script, "ROOT", root)
    arms = b'{"items": []}\n'
    files = {
        "UNITS": json.dumps(
            {
                "expected_model": "claude-sonnet-5",
                "units": [{"record": "0009", "section": "Requirements"}],
            }
        ),
        "PACKET": "# Packet\n",
        "HASH": f"{hashlib.sha256(arms).hexdigest()}  arms\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text)
        monkeypatch.setattr(script, name, tmp_path / name)
    (tmp_path / "ARMS").write_bytes(arms)
    monkeypatch.setattr(script, "ARMS", tmp_path / "ARMS")
    monkeypatch.setattr(script, "RESULT", tmp_path / "result.json")
    # The commit date is read from git for the committed list only; this list has none.
    monkeypatch.setattr(script, "units_committed_at", lambda: datetime(2026, 10, 1, tzinfo=UTC))

    with pytest.raises(SystemExit, match=r"0009:Requirements runs name \['claude-sonnet-5-5'\]"):
        script.score()

    assert not (tmp_path / "result.json").exists(), "nothing is scored from refused runs"


def test_ac_27b_the_committed_result_is_scored_again_from_the_committed_rulings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """covers: AC-27b, AC-19b, AC-28b (the recorded stage one result, byte for byte).

    Scored over the 29 units before feature 9, the corpus the result was recorded on.
    """
    script = load_script(SCORE)
    monkeypatch.setattr(script, "RESULT", tmp_path / "result.json")
    frozen = pre_feature_9_runs(tmp_path / "frozen")
    rebuild = script.committed_units

    def frozen_units(_root: Path, snapshot: Path, **flags: bool) -> tuple[UnitResult, ...]:
        return tuple(rebuild(frozen, snapshot, **flags))

    monkeypatch.setattr(script, "committed_units", frozen_units)

    script.score()

    assert (tmp_path / "result.json").read_bytes() == (
        STEP / "data" / "stage-one-result.json"
    ).read_bytes()
