"""The report under the held item view: two walks, `held only`, the label lines (spec 0005).

Chains are built by hand over spec 0012 and spec 0013 lines, which no eval chain
touches, so each test controls exactly what each walk visited. The evidence for an item
neither walk reaches is the real rebuilt results of spec 0012, as in `test_report.py`.
"""

from pathlib import Path
from typing import Any

import pytest

from tracepath.pipeline import CorpusResolution, UnitResult, resolve_accepted
from tracepath.rebuild import committed_units, records_for_units
from tracepath.report import (
    HELD_LABEL,
    HELD_MEANING,
    Holding,
    Question,
    Report,
    held_parts,
    holding_units,
    question_from,
    report_lines,
    score,
)
from tracepath.traverse.graph_slice import Link, Node, NodeKind
from tracepath.traverse.walk import Chain, Direction, Step

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SPEC_0012 = "specs/0012-model-client-router/index.md"
SPEC_0013 = "specs/0013-job-search-and-results-list/index.md"
FULL = {("0012", s): 3 for s in ("requirements", "build-plan", "consequences", "follow-up")}

Evidence = tuple[tuple[UnitResult, ...], CorpusResolution]


@pytest.fixture(scope="module")
def evidence() -> Evidence:
    results = tuple(r for r in committed_units(ROOT, SNAPSHOT) if r.unit.record_id == "0012")
    return results, resolve_accepted(results, records_for_units(results, SNAPSHOT, "2e40bcf"))


@pytest.fixture(scope="module")
def split() -> dict[str, tuple[Holding, ...]]:
    return holding_units(SNAPSHOT, [SPEC_0012, SPEC_0013])


def entry(record: str, file: str, line: int) -> dict[str, Any]:
    return {"record": record, "file": f"docs/{file}", "line": line}


#: Start, four items only the held walk reaches, one item at a line the shortcut test
#: reaches both ways, and one item no walk visits (spec 0012 AC-2, line 21).
QUESTION: Question = question_from(
    [
        {
            "question": "Why does the router span open first?",
            "trace": [
                entry("spec 0012 AC-7", SPEC_0012, 26),
                entry("spec 0012 AC-1", SPEC_0012, 20),
                entry("spec 0012 AC-3", SPEC_0012, 22),
                entry("spec 0012 build step registering the span", SPEC_0012, 88),
                entry("spec 0013 AC-1", SPEC_0013, 23),
                entry("spec 0012 AC-2", SPEC_0012, 21),
            ],
        }
    ],
    1,
)


def node(canonical_id: str, line: int, *, held: bool = False, file: str = SPEC_0012) -> Node:
    return Node(
        canonical_id=canonical_id,
        kind=NodeKind.ENTITY,
        file=file,
        file_line=line,
        held=held,
        held_reasons=("known_trap_flag",) if held else (),
    )


def link(source: str, target: str, *, held: bool = False) -> Link:
    return Link(
        type="BLOCKED_BY",
        source=source,
        target=target,
        held=held,
        held_reasons=("runs_disagree",) if held else (),
    )


START = Step(0, node("0012/AC-7", 26), None, None, None, None)
#: Reached by a held link from the start; the node itself accepted.
VIA_HELD_LINK = Step(
    1,
    node("0012/AC-1", 20),
    link("0012/AC-7", "0012/AC-1", held=True),
    Direction.OUTGOING,
    "0012/AC-7",
    None,
)
#: Itself held, reached by an accepted link.
HELD_NODE = Step(
    1,
    node("0012/AC-3", 22, held=True),
    link("0012/AC-7", "0012/AC-3"),
    Direction.OUTGOING,
    "0012/AC-7",
    None,
)
#: Accepted, by an accepted link, from a step a held link reached.
BEHIND_HELD = Step(
    2,
    node("0012#build-plan:7", 88),
    link("0012/AC-1", "0012#build-plan:7"),
    Direction.OUTGOING,
    "0012/AC-1",
    None,
)
#: In another record, by an accepted link from the held node.
ACROSS = Step(
    2,
    node("0013/AC-1", 23, file=SPEC_0013),
    link("0012/AC-3", "0013/AC-1"),
    Direction.OUTGOING,
    "0012/AC-3",
    None,
)

HELD_CHAIN = Chain("0012/AC-7", 3, (START, VIA_HELD_LINK, HELD_NODE, BEHIND_HELD, ACROSS))
CLEAN_CHAIN = Chain("0012/AC-7", 3, (START,))


def held_report(evidence: Evidence, split: Any, clean: Chain | None = CLEAN_CHAIN) -> Report:
    results, corpus = evidence
    return score(QUESTION, clean, results, corpus, FULL, split, with_held=True, held=HELD_CHAIN)


def expected_lines(report: Report) -> list[str]:
    lines = report_lines(report)
    start = lines.index("Expected items:") + 1
    return list(lines[start : start + len(QUESTION.items)])


# AC-12, AC-12b: reached by the clean walk, or held only.


def test_ac_12_an_item_the_clean_walk_reaches_prints_reached(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-12 (reached by the clean walk)."""
    lines = expected_lines(held_report(evidence, split))

    assert lines[0] == (f"  reached      spec 0012 AC-7 · {SPEC_0012}:26 · hop 0 · 0012/AC-7")


def test_ac_12_a_held_shortcut_does_not_relabel_an_item_the_clean_walk_reaches(
    evidence: Any, split: Any
) -> None:
    """covers: spec 0005 AC-12 (whatever path the held walk took to it)."""
    clean_three = Step(
        3,
        node("0012#build-plan:7", 88),
        link("0012/AC-5", "0012#build-plan:7"),
        Direction.OUTGOING,
        "0012/AC-5",
        None,
    )
    clean = Chain("0012/AC-7", 3, (START, clean_three))

    report = held_report(evidence, split, clean)
    finding = report.findings[3]

    assert finding.reached_by == clean_three
    assert finding.held_by is None
    assert expected_lines(report)[3] == (
        f"  reached      spec 0012 build step registering the span · {SPEC_0012}:88 · hop 3 · "
        "0012#build-plan:7"
    )


def test_ac_12b_an_item_only_the_held_walk_reaches_is_held_only_never_reached(
    evidence: Any, split: Any
) -> None:
    """covers: spec 0005 AC-12b."""
    report = held_report(evidence, split)

    for finding in report.findings[1:5]:
        assert finding.reached_by is None
        assert finding.held_by is not None
        assert finding.reason is None
    assert all(line.startswith("  held only    ") for line in expected_lines(report)[1:5])


def test_ac_12b_a_held_entity_is_held_only(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-12b (a held entity always falls here)."""
    finding = held_report(evidence, split).findings[2]

    assert finding.held_by == HELD_NODE


def test_with_no_clean_chain_every_held_walk_item_is_held_only(evidence: Any, split: Any) -> None:
    """The held start: the clean walk has no start and reaches nothing (spec 0005)."""
    report = held_report(evidence, split, clean=None)

    assert [f.reached_by for f in report.findings] == [None] * len(QUESTION.items)
    assert expected_lines(report)[0].startswith("  held only    spec 0012 AC-7 ")


def test_an_item_neither_walk_reaches_keeps_its_spec_0004_reason(evidence: Any, split: Any) -> None:
    """Reasons for items neither walk reaches keep spec 0004's meaning (spec 0005)."""
    results, corpus = evidence
    held = held_report(evidence, split).findings[5]
    default = score(QUESTION, CLEAN_CHAIN, results, corpus, FULL, split).findings[5]

    assert held.reached_by is None and held.held_by is None
    assert held.reason is not None
    assert held.reason == default.reason


# AC-13: a held only line names the held parts of its path.


def test_ac_13_a_held_only_line_names_a_held_link_on_its_path(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-13 (a link as SOURCE -[TYPE]-> TARGET)."""
    assert expected_lines(held_report(evidence, split))[1] == (
        f"  held only    spec 0012 AC-1 · {SPEC_0012}:20 · hop 1 · 0012/AC-1 · "
        "via 0012/AC-7 -[BLOCKED_BY]-> 0012/AC-1"
    )


def test_ac_13_a_held_only_line_names_a_held_node_on_its_path(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-13 (a node as its id)."""
    assert expected_lines(held_report(evidence, split))[2] == (
        f"  held only    spec 0012 AC-3 · {SPEC_0012}:22 · hop 1 · 0012/AC-3 · via 0012/AC-3"
    )


def test_ac_13_the_held_parts_come_from_the_whole_path_back_to_the_start(
    evidence: Any, split: Any
) -> None:
    """covers: spec 0005 AC-13 (from the start, not only the last step)."""
    assert expected_lines(held_report(evidence, split))[3].endswith(
        "· 0012#build-plan:7 · via 0012/AC-7 -[BLOCKED_BY]-> 0012/AC-1"
    )


def test_ac_13_parts_are_in_path_order_link_before_the_node_it_led_to() -> None:
    """covers: spec 0005 AC-13 (joined by `, `, from the start)."""
    held_start = Step(0, node("0012/AC-7", 26, held=True), None, None, None, None)
    to_held = Step(
        1,
        node("0012/AC-3", 22, held=True),
        link("0012/AC-7", "0012/AC-3", held=True),
        Direction.OUTGOING,
        "0012/AC-7",
        None,
    )
    chain = Chain("0012/AC-7", 3, (held_start, to_held))

    assert held_parts(chain, to_held) == (
        "0012/AC-7",
        "0012/AC-7 -[BLOCKED_BY]-> 0012/AC-3",
        "0012/AC-3",
    )


# AC-14, AC-14b: across records, clean and through held items.


def test_ac_14_across_records_counts_only_items_the_clean_walk_reached(
    evidence: Any, split: Any
) -> None:
    """covers: spec 0005 AC-14."""
    lines = report_lines(held_report(evidence, split))

    assert any(line.startswith("Across records: no.") for line in lines)


def test_ac_14b_through_held_items_lists_each_held_only_item_outside_the_start_record(
    evidence: Any, split: Any
) -> None:
    """covers: spec 0005 AC-14b (yes)."""
    lines = report_lines(held_report(evidence, split))

    assert lines[-1] == "Across records through held items: yes (0013/AC-1, hop 2)"


def test_ac_14b_through_held_items_says_no_when_none_is_outside(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-14b (no)."""
    results, corpus = evidence
    inside = Chain("0012/AC-7", 3, HELD_CHAIN.steps[:4])
    report = score(QUESTION, CLEAN_CHAIN, results, corpus, FULL, split, with_held=True, held=inside)

    assert report_lines(report)[-1] == "Across records through held items: no."


# AC-15, AC-16: the label and the meaning line.


def test_ac_15_a_held_report_opens_with_the_second_result_label(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-15."""
    lines = report_lines(held_report(evidence, split))

    assert lines[0] == (
        "Held item view (spec 0005): a second result. Experiment 0009 stays the first."
    )
    assert lines[0] == HELD_LABEL


def test_ac_16_a_held_report_prints_what_held_for_review_still_means(
    evidence: Any, split: Any
) -> None:
    """covers: spec 0005 AC-16."""
    lines = report_lines(held_report(evidence, split))

    assert (
        "held_for_review keeps spec 0004's meaning: the item is held, whether or not this view "
        "wrote it."
    ) in lines
    assert HELD_MEANING in lines


# AC-4: without the flag, no trace of the view.


def test_ac_4_a_default_report_has_no_held_line_outcome_or_label(evidence: Any, split: Any) -> None:
    """covers: spec 0005 AC-4 (the report step)."""
    results, corpus = evidence
    report = score(QUESTION, HELD_CHAIN, results, corpus, FULL, split)
    lines = report_lines(report)

    assert HELD_LABEL not in lines
    assert HELD_MEANING not in lines
    assert not any(line.startswith("  held only") for line in lines)
    assert not any("through held items" in line for line in lines)
    assert all(f.held_by is None for f in report.findings)


def test_visited_steps_are_counted_over_the_held_walk(evidence: Any, split: Any) -> None:
    """The count of visited steps matching no item reads the chain `trace` prints."""
    results, corpus = evidence
    extra = Step(
        1,
        Node(canonical_id="0013", kind=NodeKind.RECORD),
        link("0012/AC-7", "0013", held=True),
        Direction.OUTGOING,
        "0012/AC-7",
        None,
    )
    held = Chain("0012/AC-7", 3, (*HELD_CHAIN.steps, extra))
    report = score(QUESTION, CLEAN_CHAIN, results, corpus, FULL, split, with_held=True, held=held)

    assert report.unmatched_steps == 1
