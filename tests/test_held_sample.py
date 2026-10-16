"""Experiment 0013's blind sample of held items and its packet, on crafted runs.

No API call, no database. The runs are built by hand: in unit `0099`, `AC-1` agrees
across the three runs, `AC-2` appears in runs 2 and 3 only, worded differently, one
link names `0001/AC-3` in another unit and agrees, and one link names a record the
corpus does not hold and appears in run 1 only.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tracepath.artifacts import build_artifact
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import assign_ids, locate_output
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind
from tracepath.pipeline import UnitResult, review_rows

ROOT = Path(__file__).resolve().parents[1]
STEP = ROOT / "experiments" / "0013-held-item-error-analysis"
SCRIPT = STEP / "prepare_held_sample.py"
MODEL = "claude-sonnet-5"

TEXT = """## Requirements

- **AC-1**: The first claim holds.
- **AC-2**: The second claim holds.
- **AC-3**: The third claim holds.
"""
OTHER = """## Requirements

- **AC-3**: The other claim holds.
"""

UNIT = Unit(
    kind=UnitKind.SECTION,
    record_id="0099",
    section="Requirements",
    text=TEXT,
    path="specs/0099-crafted/index.md",
    start_offset=0,
    start_line=10,
)
OTHER_UNIT = Unit(
    kind=UnitKind.SECTION,
    record_id="0001",
    section="Requirements",
    text=OTHER,
    path="specs/0001-other/index.md",
    start_offset=0,
    start_line=1,
)


def load_script() -> ModuleType:
    name = f"exp0013_{SCRIPT.stem}"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


S = load_script()


def criterion(ac: str, span: str) -> dict[str, Any]:
    return {"id": ac, "id_source": "verbatim", "type": "AcceptanceCriterion", "span": span}


def reference(record: str, ac: str, mention: str) -> dict[str, Any]:
    return {"kind": "reference", "record": record, "id": ac, "mention": mention}


AGREED_LINK = {
    "type": "verifies",
    "source": {"kind": "local", "id": "AC-1"},
    "target": reference("0001", "AC-3", "spec 0001 AC-3"),
}
LONE_LINK = {
    "type": "amended-by",
    "source": {"kind": "local", "id": "AC-1"},
    "target": reference("0050", "AC-9", "0050's AC-9"),
}


def output(entities: list[dict[str, Any]], links: list[dict[str, Any]]) -> ExtractionOutput:
    return ExtractionOutput.model_validate({"entities": entities, "relationships": links})


def result(unit: Unit, slug: str, outputs: list[ExtractionOutput]) -> UnitResult:
    identified = tuple(assign_ids(locate_output(unit, o), unit.record_id, slug) for o in outputs)
    artifacts = tuple(
        build_artifact(
            unit,
            slug,
            n,
            o,
            MODEL,
            "0003.1",
            "2e40bcf",
            "2026-10-15T00:00:00+00:00",
            1,
            "low",
            0,
            0,
        )
        for n, o in enumerate(outputs, start=1)
    )
    return UnitResult(
        unit=unit,
        section_slug=slug,
        artifacts=artifacts,
        identified=identified,
        routed=route_runs(identified),
        input_tokens=0,
        output_tokens=0,
    )


def results() -> tuple[UnitResult, ...]:
    first = criterion("AC-1", "The first claim holds.")
    crafted = result(
        UNIT,
        "requirements",
        [
            output([first], [AGREED_LINK, LONE_LINK]),
            output([first, criterion("AC-2", "The second claim holds.")], [AGREED_LINK]),
            output([first, criterion("AC-2", "The second claim")], [AGREED_LINK]),
        ],
    )
    other = output([criterion("AC-3", "The other claim holds.")], [])
    return crafted, result(OTHER_UNIT, "requirements", [other, other, other])


def items() -> dict[str, Any]:
    """The crafted queue's grouped items, keyed by group."""
    built = results()
    rows = review_rows(built, (), MODEL, "2026-10-15T00:00:00+00:00")
    return {i.group: i for i in S.held_items(rows, built, S.known_entities(built))}


# Groups (one distinct reason name; runs_disagree split by runs present).


def test_one_distinct_reason_name_places_a_row_and_two_names_do_not() -> None:
    assert S.group_of(frozenset({"known_trap_flag"}), (0, 0, 0)) == "d"
    assert S.group_of(frozenset({"endpoint_not_accepted"}), (1, 1, 1)) == "e"
    assert S.group_of(frozenset({"runs_disagree", "known_trap_flag"}), (1, 2, 1)) is None
    assert S.group_of(frozenset({"unclassified_type"}), (1, 1, 1)) is None


def test_an_endpoint_waiting_on_both_ends_is_one_distinct_reason() -> None:
    row = {"reasons": [{"name": "endpoint_not_accepted"}, {"name": "endpoint_not_accepted"}]}
    assert S.group_of(S.reason_names(row), (1, 1, 1)) == "e"


@pytest.mark.parametrize(
    ("counts", "group"), [((1, 2, 1), "a"), ((0, 1, 1), "b"), ((1, 0, 0), "c")]
)
def test_runs_disagree_is_split_by_how_many_runs_hold_the_signature(
    counts: tuple[int, ...], group: str
) -> None:
    assert S.group_of(frozenset({"runs_disagree"}), counts) == group


def test_each_held_row_takes_its_per_run_counts_and_its_model() -> None:
    found = items()

    # Only later runs hold it, so its row is a leftover and names no canonical id.
    assert (found["b"].signature, found["b"].canonical_id) == (
        ("0099/AC-2", "AcceptanceCriterion"),
        None,
    )
    assert found["b"].counts == (0, 1, 1)
    assert found["c"].signature == ("amended-by", "0099/AC-1", "ref:0050/AC-9")
    assert found["c"].counts == (1, 0, 0)
    assert {i.model for i in found.values()} == {MODEL}


# Wording and ends.


def test_the_wording_is_the_earliest_run_that_holds_the_signature() -> None:
    b = items()["b"]

    assert b.run == 2
    assert b.mark.kind == S.ENTITY
    assert b.mark.parts[0].span == "The second claim holds."


def test_an_entity_cites_its_line_from_the_top_of_its_file() -> None:
    b = items()["b"]

    assert b.mark.parts[0].source == "specs/0099-crafted/index.md:13"
    assert b.mark.lines == (("specs/0099-crafted/index.md", 13),)


def test_a_link_shows_both_ends_and_only_its_local_end_has_a_line() -> None:
    c = items()["c"]

    local, far = c.mark.parts
    assert (c.mark.kind, c.mark.type) == (S.LINK, "amended-by")
    assert (local.span, local.source, local.words) == (
        "The first claim holds.",
        "specs/0099-crafted/index.md:12",
        None,
    )
    assert (far.words, far.span, far.source) == ("0050's AC-9", None, None)
    assert c.mark.lines == (("specs/0099-crafted/index.md", 12),)


def test_a_cross_unit_end_shows_the_known_entity_its_words_match() -> None:
    built = results()
    known = S.known_entities(built)
    run, mark = S.held_mark(("verifies", "0099/AC-1", "ref:0001/AC-3"), built[0], known)

    assert run == 1
    assert mark.parts[1] == S.Shown(
        span="The other claim holds.", source="specs/0001-other/index.md:3", words="spec 0001 AC-3"
    )


# Eval passages and exclusions.

LINES = [
    "# Title",
    "",
    "The first sentence of a wrapped",
    "paragraph ends [here](../x.md).",
    "",
    "A later line, skipped to.",
]


def test_a_passage_runs_from_its_cited_line_through_the_lines_its_quote_covers() -> None:
    quote = "The first sentence of a wrapped paragraph ends [here]."
    assert S.passage("docs/a.md", 3, quote, LINES) == S.Passage("a.md", 3, 4)


def test_a_passage_cited_on_the_blank_line_above_still_covers_its_quote() -> None:
    quote = "The first sentence [...] A later line, skipped to."
    assert S.passage("docs/a.md", 2, quote, LINES) == S.Passage("a.md", 2, 6)


def test_a_quote_not_found_from_its_cited_line_is_refused() -> None:
    with pytest.raises(ValueError, match="not found"):
        S.passage("docs/a.md", 5, "The first sentence", LINES)


def test_only_trace_steps_and_their_also_passages_are_read(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("\n".join(LINES))
    step = {"file": "docs/a.md", "line": 6, "quote": "A later line"}
    payload = {
        "entries": [
            {
                "trace": [{**step, "also": {"line": 1, "quote": "# Title"}}],
                "corroboration": {**step, "line": 3, "quote": "The first sentence"},
            },
            {"checked": [{"where": "docs/a.md", "found": "nothing"}]},
        ]
    }
    found = S.eval_passages(payload, tmp_path)

    assert found == (S.Passage("a.md", 6, 6), S.Passage("a.md", 1, 1))


def test_every_committed_eval_chain_passage_is_found_in_the_snapshot() -> None:
    payload = json.loads((ROOT / "eval" / "linked-records-research.json").read_text())
    found = S.eval_passages(payload, ROOT / "corpus" / "jobhunt")

    assert len(found) == 20
    assert all(p.start <= p.end for p in found)


def test_an_entity_inside_a_passage_and_a_link_with_one_local_end_inside_are_left_out() -> None:
    found = items()
    inside = (S.Passage("specs/0099-crafted/index.md", 12, 12),)

    assert S.exclusion(found["c"], inside, frozenset()) == S.IN_PASSAGE
    assert S.exclusion(found["b"], inside, frozenset()) is None
    assert S.exclusion(found["b"], (S.Passage("specs/other.md", 13, 13),), frozenset()) is None


def test_only_the_trap_flag_group_leaves_out_what_0012_drew() -> None:
    b = S.HeldItem(**{**vars(items()["b"]), "canonical_id": "0099/AC-2"})
    drawn = frozenset({"0099/AC-2"})

    assert S.exclusion(b, (), drawn) is None
    flagged = S.HeldItem(**{**vars(b), "group": "d"})
    assert S.exclusion(flagged, (), drawn) == S.DRAWN_BY_0012


# Draw, packet and arm file.


def test_a_draw_asking_too_many_takes_all_and_states_the_shortfall() -> None:
    pool = list(items().values())
    d = S.draw("b", pool, 4, 7)

    assert (d.pool, len(d.items), d.shortfall) == (2, 2, 2)


def test_a_draw_repeats_under_its_seed_whatever_the_pool_order() -> None:
    pool = list(items().values()) * 3
    assert S.draw("c", pool, 2, 5) == S.draw("c", list(reversed(pool)), 2, 5)


def test_items_are_shuffled_together_under_opaque_ids_numbered_after_the_shuffle() -> None:
    found = items()
    draws = [S.draw("b", [found["b"]], 4, 1), S.draw("c", [found["c"]], 4, 2)]
    packet = S.build_packet(draws, 3)

    assert [i for i, _ in packet] == ["H01", "H02"]
    assert {item.group for _, item in packet} == {"b", "c"}


def test_the_packet_shows_no_group_reason_count_model_id_or_acceptance_state() -> None:
    found = items()
    draws = [S.draw("b", [found["b"]], 4, 1), S.draw("c", [found["c"]], 4, 2)]
    text = S.packet_markdown(S.build_packet(draws, 3), "Packet", S.INTRO)

    for forbidden in (
        "runs_disagree",
        "known_trap_flag",
        "endpoint_not_accepted",
        MODEL,
        "0099/AC-",
        "ref:",
        "group",
        "accepted",
        "held",
        "waiting",
        "(0, 1, 1)",
        "[0, 1, 1]",
    ):
        assert forbidden not in text
    assert "  - span: The second claim holds." in text
    assert "  - to words: 0050's AC-9" in text
    assert "  - to target: not resolved" in text


def test_every_item_has_a_ruling_slot_a_note_and_a_should_have_been() -> None:
    found = items()
    text = S.packet_markdown(S.build_packet([S.draw("b", [found["b"]], 4, 1)], 3), "P", "")

    assert "- [ ] agree / disagree / unsure · `H01` · entity · AcceptanceCriterion" in text
    assert "  - note: " in text
    assert "  - should have been: " in text


def test_the_arm_file_names_every_seed_and_each_items_group_counts_model_and_run() -> None:
    found = items()
    draws = [S.draw("b", [found["b"]], 4, 11), S.draw("c", [found["c"]], 4, 12)]
    packet = S.build_packet(draws, 13)

    key = json.loads(json.dumps(S.arm_key(packet, draws, 13, {"d": {S.DRAWN_BY_0012: 2}})))

    assert key["shuffle_seed"] == 13
    assert [(d["group"], d["seed"], d["shortfall"]) for d in key["draws"]] == [
        ("b", 11, 3),
        ("c", 12, 3),
    ]
    assert key["excluded"]["d"] == {S.DRAWN_BY_0012: 2}
    named = {
        i["opaque_id"]: (i["group"], i["counts"], i["model"], i["wording_run"])
        for i in key["items"]
    }
    assert named == {
        opaque_id: (item.group, list(item.counts), MODEL, item.run) for opaque_id, item in packet
    }


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


def test_the_committed_packet_holds_twenty_items_each_with_its_slots() -> None:
    packet = STEP / "data" / "held-packet.md"
    if not packet.exists():
        pytest.skip("the sample has not been drawn yet")
    text = packet.read_text()

    ids = re.findall(r"^- \[[ x]\] .*`(H\d\d)` · ", text, re.MULTILINE)
    assert ids == [f"H{n:02d}" for n in range(1, 21)]
    assert text.count("\n  - note:") == 20
    assert text.count("\n  - should have been:") == 20
