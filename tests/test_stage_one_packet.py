"""Stage one's sampler and blind packet (spec 0007 step 7), on crafted runs.

No API call, no database. Each test names the criterion it covers. The runs are built
by hand so one entity is released by the code pass and one is accepted either way.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tracepath.extract.codepass import code_decided_ids
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import IdentifiedOutput, assign_ids, locate_output
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind
from tracepath.measure import (
    CONTROL,
    RELEASED,
    EntityMark,
    arm_key,
    build_packet,
    control_marks,
    draw,
    packet_markdown,
    released_marks,
)
from tracepath.pipeline import UnitResult

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "0012-extraction-accuracy-step-one" / "prepare_stage_one.py"

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


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("exp0012_prepare_stage_one", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["exp0012_prepare_stage_one"] = module
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
