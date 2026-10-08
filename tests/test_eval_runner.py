"""The eval runner's scoring over the hand built fixture graphs, no Neo4j (spec 0006).

The fixtures (`tests/trace_fixture.py`, `tests/held_fixture.py`) are not eval chains.
Their files are written into a temporary snapshot here, with each section heading on
the line the fixture cites, so the report step can find the unit each item sits in.
No run files back them, so an item not reached reads `section_not_extracted`.

Absence questions need real accepted entities, so those tests use spec 0012's rebuilt
results, as `tests/test_report.py` does, with chains built by hand.
"""

import dataclasses
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests import held_fixture as hx
from tests import trace_fixture as fx
from tracepath.cli import _Committed, _score_question
from tracepath.extract.compare import ReviewItem, ReviewReason, ReviewReasonName
from tracepath.pipeline import CorpusResolution, HeldLink, UnitResult, resolve_accepted
from tracepath.rebuild import committed_units, records_for_units, settled_run_counts
from tracepath.report import (
    EVAL_FILE,
    SPEC_AC,
    EvalEntryUnusable,
    ExpectedItem,
    Holding,
    Question,
    Reason,
    Report,
    Start,
    Verdict,
    holding_units,
    question_from,
    read_eval_set,
    read_sidecar,
    report_lines,
    resolve_start,
    result_lines,
    score,
    verdict,
)
from tracepath.resolve.endpoints import Resolution
from tracepath.traverse.graph_slice import (
    GraphSlice,
    Node,
    NodeKind,
    graph_slice,
    link_from_properties,
    node_from_properties,
)
from tracepath.traverse.walk import Chain, Step

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SPEC_0012 = "specs/0012-model-client-router/index.md"
FULL = {("0012", s): 3 for s in ("requirements", "build-plan", "consequences", "follow-up")}
EMPTY = CorpusResolution(resolution=Resolution(links=(), unresolved=()), held=())
NOTHING = _Committed(results=(), corpus=EMPTY, settled={})

#: The fixture items, at the file lines the fixture's rows give them.
START_LINE, AC2_LINE, AC5_LINE, BUILD_LINE = 12, 13, 16, 60


def _fixture_text(title: str, sections: dict[str, int], length: int) -> str:
    lines = [f"filler line {n}" for n in range(1, length + 1)]
    lines[0] = f"# {title}"
    for heading, line in sections.items():
        lines[line - 1] = f"## {heading}"
    return "\n".join(lines) + "\n"


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A snapshot holding only the fixture files, each heading on its cited line."""
    root = tmp_path_factory.mktemp("snapshot")
    for file, title, sections in (
        (fx.FILE, "9001. Fixture walk", fx.SECTION_STARTS),
        (hx.FILE, "9003. Fixture held", hx.SECTION_STARTS),
        (hx.NEIGHBOUR_FILE, "9004. Fixture held neighbour", hx.SECTION_STARTS),
    ):
        path = root / file
        path.parent.mkdir(parents=True)
        path.write_text(_fixture_text(title, sections, 70))
    return root


def walk_slice() -> GraphSlice:
    nodes = [node_from_properties(["Record"], row) for row in fx.RECORDS]
    nodes += [node_from_properties(["Entity", row["type"]], row) for row in fx.ENTITIES]
    nodes += [node_from_properties(["Unresolved"], row) for row in fx.UNRESOLVED]
    links = [
        link_from_properties(t, r["from_id"], r["to_id"], r["properties"]) for t, r in fx.LINKS
    ]
    return graph_slice(nodes, links)


def held_slice(*, with_held: bool) -> GraphSlice:
    nodes = [node_from_properties(["Record"], row) for row in hx.RECORDS]
    nodes += [node_from_properties(["Entity", row["type"]], row) for row in hx.ENTITIES]
    nodes += [node_from_properties(["Unresolved"], row) for row in hx.UNRESOLVED]
    links = [
        link_from_properties(t, r["from_id"], r["to_id"], r["properties"]) for t, r in hx.LINKS
    ]
    return graph_slice(nodes, links, with_held=with_held)


def entry(record: str, file: str, line: int, also: Any = None) -> dict[str, Any]:
    step: dict[str, Any] = {"record": record, "file": f"docs/{file}", "line": line}
    if also is not None:
        step["also"] = also
    return step


def fixture_question(*trace: dict[str, Any], number: int = 1) -> Question:
    entries = [{"question": f"Fixture question {n}?", "trace": list(trace)} for n in range(number)]
    return question_from(entries, number)


def scored(
    question: Question, graph: GraphSlice, snapshot: Path, *, with_held: bool = False
) -> Report:
    return _score_question(question, graph, NOTHING, snapshot, with_held=with_held).report


# AC-5, AC-6, AC-6c: pass and fail for a question with a trace list.


def test_ac_6_a_question_whose_every_item_is_reached_passes(snapshot: Path) -> None:
    """covers: AC-6, AC-5."""
    question = fixture_question(
        entry("spec 9001 AC-1", fx.FILE, START_LINE),
        entry("spec 9001 AC-2", fx.FILE, AC2_LINE),
        entry("spec 9001 build step", fx.FILE, BUILD_LINE),
    )
    report = scored(question, walk_slice(), snapshot)
    outcome = verdict(report)

    assert outcome.verdict is Verdict.PASS
    assert outcome.reached == outcome.expected == 2
    assert result_lines(report, outcome, None)[0] == (
        "Question 1: PASS · 2 of 2 expected items reached besides the start."
    )


def test_ac_6c_a_question_with_an_item_not_reached_fails_with_its_reason(snapshot: Path) -> None:
    """covers: AC-6c, AC-5 (the item past the depth limit)."""
    question = fixture_question(
        entry("spec 9001 AC-1", fx.FILE, START_LINE),
        entry("spec 9001 AC-2", fx.FILE, AC2_LINE),
        entry("spec 9001 AC-5", fx.FILE, AC5_LINE),
    )
    report = scored(question, walk_slice(), snapshot)
    outcome = verdict(report)

    assert outcome.verdict is Verdict.FAIL
    assert result_lines(report, outcome, None)[0] == (
        "Question 1: FAIL · 1 of 2 expected items reached besides the start."
    )
    assert f"  not reached  spec 9001 AC-5 · {fx.FILE}:{AC5_LINE} · section_not_extracted" in (
        report_lines(report)
    )


def test_ac_6_a_start_not_in_the_graph_fails_even_with_no_other_item(snapshot: Path) -> None:
    """covers: AC-6 (its start in the clean slice), spec 0004 AC-52."""
    question = fixture_question(entry("spec 9001 AC-9", fx.FILE, 20))

    report = scored(question, walk_slice(), snapshot)

    assert not report.start_in_clean_slice
    assert verdict(report).verdict is Verdict.FAIL


def test_ac_6b_an_item_only_a_held_link_reaches_is_held_only_and_fails(snapshot: Path) -> None:
    """covers: AC-6b (9003/AC-4's only path runs through a held link)."""
    question = fixture_question(
        entry("spec 9003 AC-1", hx.FILE, 12),
        entry("spec 9003 AC-5", hx.FILE, 16),
        entry("spec 9003 AC-4", hx.FILE, 15),
    )
    report = scored(question, held_slice(with_held=True), snapshot, with_held=True)
    outcome = verdict(report)

    assert report.findings[2].held_by is not None
    assert report.findings[2].reached_by is None
    assert any(line.startswith("  held only    spec 9003 AC-4 ") for line in report_lines(report))
    assert outcome.verdict is Verdict.FAIL
    assert (outcome.reached, outcome.expected) == (1, 2)


def test_ac_6_the_same_question_without_the_held_item_passes(snapshot: Path) -> None:
    """The control for AC-6b: only the held item turned the result."""
    question = fixture_question(
        entry("spec 9003 AC-1", hx.FILE, 12), entry("spec 9003 AC-5", hx.FILE, 16)
    )

    report = scored(question, held_slice(with_held=True), snapshot, with_held=True)

    assert verdict(report).verdict is Verdict.PASS


# AC-10, AC-10b: the start marker, and K and M besides the start.


def test_ac_10_a_reached_step_at_hop_0_is_marked_the_start(snapshot: Path) -> None:
    """covers: AC-10 (reached)."""
    question = fixture_question(entry("spec 9001 AC-1", fx.FILE, START_LINE))

    lines = report_lines(scored(question, walk_slice(), snapshot))

    assert (
        f"  reached      spec 9001 AC-1 · {fx.FILE}:{START_LINE} · hop 0 · the start · 9001/AC-1"
    ) in lines


def test_ac_10_a_held_only_step_at_hop_0_is_marked_the_start(snapshot: Path) -> None:
    """covers: AC-10 (held only): a held start is reached by the held walk alone."""
    question = fixture_question(entry("spec 9003 AC-2", hx.FILE, 13))

    lines = report_lines(scored(question, held_slice(with_held=True), snapshot, with_held=True))

    assert (
        f"  held only    spec 9003 AC-2 · {hx.FILE}:13 · hop 0 · the start · 9003/AC-2 · "
        "via 9003/AC-2"
    ) in lines


def test_ac_10_a_step_past_hop_0_carries_no_marker(snapshot: Path) -> None:
    """covers: AC-10 (only hop 0)."""
    question = fixture_question(
        entry("spec 9001 AC-1", fx.FILE, START_LINE), entry("spec 9001 AC-2", fx.FILE, AC2_LINE)
    )

    lines = report_lines(scored(question, walk_slice(), snapshot))

    assert f"  reached      spec 9001 AC-2 · {fx.FILE}:{AC2_LINE} · hop 1 · 9001/AC-2" in lines


def test_ac_10b_k_and_m_leave_out_every_item_on_the_start_line(snapshot: Path) -> None:
    """covers: AC-10b (an `also` line at the start's own line is left out too)."""
    question = fixture_question(
        entry("spec 9001 AC-1", fx.FILE, START_LINE),
        entry("spec 9001 AC-1 again", fx.FILE, START_LINE),
        entry("spec 9001 AC-5", fx.FILE, AC5_LINE),
    )

    outcome = verdict(scored(question, walk_slice(), snapshot))

    assert (outcome.reached, outcome.expected) == (0, 1)


def test_ac_10b_with_no_start_node_nothing_is_left_out(snapshot: Path) -> None:
    """covers: AC-10b (the resolved start node's file and line: none, so none left out)."""
    question = fixture_question(
        entry("spec 9001 AC-9", fx.FILE, 20), entry("spec 9001 AC-2", fx.FILE, AC2_LINE)
    )

    outcome = verdict(scored(question, walk_slice(), snapshot))

    assert (outcome.reached, outcome.expected) == (0, 2)


# AC-11 to AC-15b: how a question starts.


def test_ac_11_a_first_entry_in_ac_form_keeps_the_spec_0004_start() -> None:
    """covers: AC-11."""
    question = fixture_question(entry("spec 9001 AC-1 (struck)", fx.FILE, START_LINE))

    assert (question.start, question.start_at) == ("9001/AC-1", None)


def test_ac_12_a_first_entry_not_in_ac_form_starts_at_the_entity_on_its_line(
    snapshot: Path,
) -> None:
    """covers: AC-12, AC-10c (the entity at FILE:LINE)."""
    question = fixture_question(entry("spec 9001 build step one", fx.FILE, BUILD_LINE))
    report = scored(question, walk_slice(), snapshot)

    assert report.start.id == "9001#build-plan:1"
    assert report.start_in_clean_slice
    assert report_lines(report)[1] == (
        'Start item: 9001#build-plan:1, from the first trace entry "spec 9001 build step one", '
        f"the entity at {fx.FILE}:{BUILD_LINE}."
    )


def _with_entities(graph: GraphSlice, *ids: str, line: int, held: bool = False) -> GraphSlice:
    extra = tuple(
        Node(canonical_id=i, kind=NodeKind.ENTITY, file=fx.FILE, file_line=line, held=held)
        for i in ids
    )
    return GraphSlice(nodes=(*graph.nodes, *extra), links=graph.links)


def test_ac_12b_the_lowest_id_wins_comparing_numbers_as_numbers() -> None:
    """covers: AC-12b (`:9` before `:10`, which a lexical order would reverse)."""
    graph = _with_entities(walk_slice(), "9001#consequences:10", "9001#consequences:9", line=70)
    question = fixture_question(entry("spec 9001 a consequence", fx.FILE, 70))

    start = resolve_start(question, graph)

    assert (start.id, start.candidates) == ("9001#consequences:9", 2)


def test_ac_12b_the_start_line_says_how_many_candidates_sat_on_the_line(snapshot: Path) -> None:
    """covers: AC-12b (the count), AC-10c."""
    graph = _with_entities(walk_slice(), "9001#build-plan:10", line=BUILD_LINE)
    question = fixture_question(entry("spec 9001 build step one", fx.FILE, BUILD_LINE))

    lines = report_lines(scored(question, graph, snapshot))

    assert lines[1] == (
        'Start item: 9001#build-plan:1, from the first trace entry "spec 9001 build step one", '
        f"the entity at {fx.FILE}:{BUILD_LINE}, the lowest id of the 2 entities on that line."
    )


def test_ac_12c_no_entity_on_the_line_means_no_start_and_a_fail(snapshot: Path) -> None:
    """covers: AC-12c, AC-10c (`Start item: none`)."""
    question = fixture_question(
        entry("spec 9001 a paragraph", fx.FILE, 20), entry("spec 9001 AC-2", fx.FILE, AC2_LINE)
    )
    report = scored(question, walk_slice(), snapshot)

    assert report.start == Start(None, candidates=0)
    assert report_lines(report)[1] == f"Start item: none, no entity at {fx.FILE}:20."
    assert [f.reason for f in report.findings] == [Reason.SECTION_NOT_EXTRACTED] * 2
    assert verdict(report).verdict is Verdict.FAIL


def test_ac_12d_a_held_entity_is_a_candidate_when_no_accepted_one_holds_the_line() -> None:
    """covers: AC-12d (9003/AC-2 is held and alone on its line)."""
    question = fixture_question(entry("spec 9003 a held criterion", hx.FILE, 13))

    assert resolve_start(question, held_slice(with_held=True)).id == "9003/AC-2"
    assert resolve_start(question, held_slice(with_held=False)).id is None


def test_ac_12d_an_accepted_entity_on_the_line_beats_a_lower_held_one() -> None:
    """covers: AC-12d (the default and held runs start at the same node)."""
    held = _with_entities(held_slice(with_held=True), "9003#a:1", line=70, held=True)
    both = _with_entities(held, "9003#b:2", line=70)
    question = fixture_question(entry("spec 9003 a line", fx.FILE, 70))

    assert resolve_start(question, both).id == "9003#b:2"
    assert resolve_start(question, held).id == "9003#a:1"


def test_ac_13_the_clean_walk_starts_at_the_id_the_held_read_resolved(snapshot: Path) -> None:
    """covers: AC-13 (a held start is absent from the clean slice, so no clean walk)."""
    question = fixture_question(
        entry("spec 9003 a held criterion", hx.FILE, 13), entry("spec 9003 AC-3", hx.FILE, 14)
    )

    result = _score_question(
        question, held_slice(with_held=True), NOTHING, snapshot, with_held=True
    )

    assert result.chain is not None and result.chain.start == "9003/AC-2"
    assert result.report.start.id == "9003/AC-2"
    assert not result.report.start_in_clean_slice
    assert result.report.findings[1].held_by is not None


def checked_entry(*wheres: str) -> dict[str, Any]:
    return {"question": "Why?", "checked": [{"where": w, "found": "x"} for w in wheres]}


ABSENT = (ExpectedItem("spec 9001 AC-5", fx.FILE, AC5_LINE, "AC-5"),)


def test_ac_14_no_trace_list_starts_from_the_first_checked_entry_in_ac_form() -> None:
    """covers: AC-14 (an earlier entry not in that form is passed over)."""
    entries = [
        checked_entry(
            "docs/specs/0008-app-shell/rationale.md",
            "docs/specs/0008-app-shell/index.md line 67 (AC-14)",
            "docs/specs/0007-auth/index.md line 25 (AC-4)",
        )
    ]

    question = question_from(entries, 1, absence=ABSENT)

    assert question.start == "0008/AC-14"
    assert question.start_label == "docs/specs/0008-app-shell/index.md line 67 (AC-14)"
    assert question.absence


def test_ac_14_the_checked_start_line_names_its_source(snapshot: Path) -> None:
    """covers: AC-10c (`from the first checked entry`)."""
    where = "docs/specs/9001-fixture-walk/index.md line 12 (AC-1)"
    question = question_from([checked_entry(where)], 1, absence=ABSENT)

    lines = report_lines(scored(question, walk_slice(), snapshot))

    assert lines[1] == f'Start item: 9001/AC-1, from the first checked entry "{where}".'
    assert lines[3] == "Items that should not be reached:"


@pytest.mark.parametrize(
    "where",
    [
        "docs/specs/0008-app-shell/index.md line 67",
        "docs/specs/0008-app-shell/index.md AC-4 (lines 25-27)",
        "docs/specs/0008-app-shell/rationale.md line 3 (AC-1)",
    ],
)
def test_ac_15_no_checked_entry_in_ac_form_means_unusable(where: str) -> None:
    """covers: AC-15 (no start is guessed)."""
    with pytest.raises(EvalEntryUnusable, match=r"question 1.*no start item is guessed"):
        question_from([checked_entry(where)], 1, absence=ABSENT)


def test_ac_15b_no_trace_list_and_no_absence_entry_is_unusable() -> None:
    """covers: AC-15b (first case)."""
    with pytest.raises(EvalEntryUnusable, match="no trace list and no absence entry"):
        question_from([checked_entry("docs/specs/0008-x/index.md line 67 (AC-14)")], 1)


def test_ac_15b_a_trace_list_with_an_absence_entry_is_unusable() -> None:
    """covers: AC-15b (second case)."""
    entries = [{"trace": [entry("spec 9001 AC-1", fx.FILE, START_LINE)]}]

    with pytest.raises(EvalEntryUnusable, match="neither kind"):
        question_from(entries, 1, absence=ABSENT)


def test_ac_15b_an_absence_entry_in_a_held_out_file_is_unusable() -> None:
    """covers: AC-15b (third case)."""
    entries = [checked_entry("docs/specs/0008-x/index.md line 67 (AC-14)")]

    with pytest.raises(EvalEntryUnusable, match="held out"):
        question_from(entries, 1, absence=ABSENT, held_out=True)


def test_ac_15b_an_empty_absence_list_is_unusable() -> None:
    """covers: AC-15b (no question can pass with no items)."""
    entries = [checked_entry("docs/specs/0008-x/index.md line 67 (AC-14)")]

    with pytest.raises(EvalEntryUnusable, match="no absence items"):
        question_from(entries, 1, absence=())


# AC-16 to AC-17e: absence questions, over spec 0012's real rebuilt results.

Evidence = tuple[tuple[UnitResult, ...], CorpusResolution]


@pytest.fixture(scope="module")
def evidence() -> Evidence:
    results = tuple(r for r in committed_units(ROOT, SNAPSHOT) if r.unit.record_id == "0012")
    return results, resolve_accepted(results, records_for_units(results, SNAPSHOT, "2e40bcf"))


@pytest.fixture(scope="module")
def no_held(evidence: Evidence) -> Evidence:
    """Spec 0012's results with every held link taken out."""
    results, corpus = evidence
    return (
        tuple(
            dataclasses.replace(r, routed=dataclasses.replace(r.routed, review=())) for r in results
        ),
        dataclasses.replace(corpus, held=()),
    )


@pytest.fixture(scope="module")
def split() -> dict[str, tuple[Holding, ...]]:
    return holding_units(SNAPSHOT, [SPEC_0012])


def absence_question(*items: tuple[str, int]) -> Question:
    rows = tuple(
        ExpectedItem(label, SPEC_0012, line, m.group(2) if (m := SPEC_AC.match(label)) else None)
        for label, line in items
    )
    where = "docs/specs/0012-model-client-router/index.md line 26 (AC-7)"
    return question_from([checked_entry(where)], 1, absence=rows)


def step_at(canonical_id: str, line: int, hop: int) -> Step:
    node = Node(canonical_id=canonical_id, kind=NodeKind.ENTITY, file=SPEC_0012, file_line=line)
    return Step(hop, node, None, None, None if hop == 0 else "0012/AC-7", None)


START_STEP = step_at("0012/AC-7", 26, 0)


def absence_report(
    question: Question,
    chain: Chain | None,
    evidence: Evidence,
    split: dict[str, tuple[Holding, ...]],
    **held: Any,
) -> Report:
    results, corpus = evidence
    return score(question, chain, results, corpus, FULL, split, start=Start("0012/AC-7"), **held)


def test_ac_16_an_absence_items_token_comes_from_its_sidecar_label() -> None:
    """covers: AC-16 (the AC-34 regex over the label)."""
    sidecar = read_sidecar(ROOT, ROOT / EVAL_FILE)

    assert sidecar is not None
    absence = sidecar.questions[4].absence
    assert absence is not None
    assert [(i.label, i.file, i.line, i.token) for i in absence] == [
        ("spec 0007 AC-4", "specs/0007-auth-and-per-user-isolation/index.md", 25, "AC-4"),
        ("spec 0007 AC-19", "specs/0007-auth-and-per-user-isolation/index.md", 42, "AC-19"),
    ]


def test_ac_17_an_absence_whose_items_are_accepted_and_unlinked_passes(
    no_held: Evidence, split: Any
) -> None:
    """covers: AC-17, AC-5 (an absence pass counts no item)."""
    question = absence_question(("spec 0012 AC-1", 20), ("spec 0012 AC-2", 21))
    report = absence_report(question, Chain("0012/AC-7", 3, (START_STEP,)), no_held, split)
    outcome = verdict(report)

    assert [(f.accepted_here, f.reason) for f in report.findings] == [(True, Reason.NO_LINK)] * 2
    assert outcome.verdict is Verdict.PASS
    assert result_lines(report, outcome, None)[0] == (
        "Question 1: PASS · 0 of 2 expected items reached besides the start."
    )


def test_ac_17b_an_absence_item_reached_fails_naming_it_and_its_hop(
    no_held: Evidence, split: Any
) -> None:
    """covers: AC-17b."""
    question = absence_question(("spec 0012 AC-1", 20), ("spec 0012 AC-2", 21))
    chain = Chain("0012/AC-7", 3, (START_STEP, step_at("0012/AC-2", 21, 2)))
    report = absence_report(question, chain, no_held, split)
    outcome = verdict(report)

    assert outcome.verdict is Verdict.FAIL
    assert result_lines(report, outcome, None)[0] == (
        "Question 1: FAIL · spec 0012 AC-2 was reached at hop 2, "
        "a connection the record does not document."
    )


def test_ac_17c_a_start_not_in_the_clean_slice_is_inconclusive_for_every_item(
    no_held: Evidence, split: Any
) -> None:
    """covers: AC-17c (the first cause), AC-17 (never PASS without its start)."""
    question = absence_question(("spec 0012 AC-1", 20), ("spec 0012 AC-2", 21))
    report = absence_report(question, None, no_held, split)
    outcome = verdict(report)

    assert outcome.verdict is Verdict.INCONCLUSIVE
    assert result_lines(report, outcome, None)[:3] == (
        "Question 1: INCONCLUSIVE · absence not provable.",
        f"  spec 0012 AC-1 · {SPEC_0012}:20 · start not in the clean slice",
        f"  spec 0012 AC-2 · {SPEC_0012}:21 · start not in the clean slice",
    )


def test_ac_17c_each_item_gets_the_first_cause_that_applies(
    evidence: Evidence, no_held: Evidence, split: Any
) -> None:
    """covers: AC-17c (a reason other than no_link, then no accepted entity)."""
    question = absence_question(
        ("spec 0012 AC-3", 22),  # held for review
        ("spec 0012 preamble", 2),  # a section never extracted
        ("spec 0012 a line with no entity", 19),
        ("spec 0012 AC-1", 20),  # its absence holds
    )
    report = absence_report(question, Chain("0012/AC-7", 3, (START_STEP,)), no_held, split)
    outcome = verdict(report)

    assert outcome.verdict is Verdict.INCONCLUSIVE
    assert result_lines(report, outcome, None)[1:5] == (
        f"  spec 0012 AC-3 · {SPEC_0012}:22 · held_for_review",
        f"  spec 0012 preamble · {SPEC_0012}:2 · section_not_extracted",
        f"  spec 0012 a line with no entity · {SPEC_0012}:19 · no accepted entity at the line",
        f"  spec 0012 AC-1 · {SPEC_0012}:20 · none, its absence holds",
    )


def test_ac_17c_an_item_only_the_held_walk_reaches_is_held_only(
    no_held: Evidence, split: Any
) -> None:
    """covers: AC-17c (the last cause)."""
    question = absence_question(("spec 0012 AC-1", 20), ("spec 0012 AC-2", 21))
    clean = Chain("0012/AC-7", 3, (START_STEP,))
    held = Chain("0012/AC-7", 3, (START_STEP, step_at("0012/AC-2", 21, 1)))
    report = absence_report(question, clean, no_held, split, with_held=True, held=held)
    outcome = verdict(report)

    assert outcome.verdict is Verdict.INCONCLUSIVE
    assert outcome.causes[1][1] == "held only"


def _held_link(source: str, target: str) -> HeldLink:
    reason = ReviewReason(ReviewReasonName.ENDPOINT_NOT_ACCEPTED, target)
    return HeldLink("0012", "Requirements", ReviewItem(("satisfies", source, target), (reason,)))


def test_ac_17d_a_held_link_counts_when_its_other_end_was_visited(
    no_held: Evidence, split: Any
) -> None:
    """covers: AC-17d (the other endpoint, 0012/AC-6, is on the walk)."""
    results, corpus = no_held
    linked = (results, dataclasses.replace(corpus, held=(_held_link("0012/AC-6", "0012/AC-1"),)))
    question = absence_question(("spec 0012 AC-1", 20))
    chain = Chain("0012/AC-7", 3, (START_STEP, step_at("0012/AC-6", 25, 1)))

    report = absence_report(question, chain, linked, split)

    assert report.findings[0].reason is Reason.LINK_HELD
    assert verdict(report).verdict is Verdict.INCONCLUSIVE


def test_ac_17d_a_held_link_whose_other_end_was_not_visited_is_ignored(
    no_held: Evidence, split: Any
) -> None:
    """covers: AC-17d (ignored for an absence item), and the trace rule kept as it was."""
    results, corpus = no_held
    linked = (results, dataclasses.replace(corpus, held=(_held_link("0012/AC-6", "0012/AC-1"),)))
    chain = Chain("0012/AC-7", 3, (START_STEP,))

    absence = absence_report(absence_question(("spec 0012 AC-1", 20)), chain, linked, split)
    traced = score(
        fixture_question(
            {"record": "spec 0012 AC-7", "file": f"docs/{SPEC_0012}", "line": 26},
            {"record": "spec 0012 AC-1", "file": f"docs/{SPEC_0012}", "line": 20},
        ),
        chain,
        *linked,
        FULL,
        split,
    )

    assert absence.findings[0].reason is Reason.NO_LINK
    assert verdict(absence).verdict is Verdict.PASS
    assert traced.findings[1].reason is Reason.LINK_HELD


def test_ac_17d_a_line_endpoint_names_a_visited_entity_of_its_own_unit(
    evidence: Evidence, split: Any
) -> None:
    """covers: AC-17d (a derived endpoint, `line:N`, read as `_reason()` reads it)."""
    results, corpus = evidence
    build = next(r for r in results if r.unit.section == "Build plan")
    nine = next(e for e in build.routed.accepted_entities if e.canonical_id == "0012#build-plan:9")
    assert nine.location is not None
    link = HeldLink(
        "0012",
        "Build plan",
        ReviewItem(("satisfies", f"line:{nine.location.line}", "ref:0012/AC-1"), ()),
    )
    stripped = tuple(
        dataclasses.replace(r, routed=dataclasses.replace(r.routed, review=())) for r in results
    )
    linked = (stripped, dataclasses.replace(corpus, held=(link,)))
    visited = Chain("0012/AC-7", 3, (START_STEP, step_at("0012#build-plan:9", 90, 2)))

    report = absence_report(absence_question(("spec 0012 AC-1", 20)), visited, linked, split)

    assert report.findings[0].reason is Reason.LINK_HELD


def test_ac_17e_question_4_is_an_absence_question_inconclusive_with_no_start(
    split: Any,
) -> None:
    """covers: AC-17e (both items unextracted or held: never PASS today)."""
    eval_set = read_eval_set(ROOT / EVAL_FILE)
    sidecar = read_sidecar(ROOT, ROOT / EVAL_FILE)
    assert sidecar is not None
    question = question_from(eval_set.entries, 4, absence=sidecar.questions[4].absence)
    results = committed_units(ROOT, SNAPSHOT)
    corpus = resolve_accepted(results, records_for_units(results, SNAPSHOT, "2e40bcf"))
    files = holding_units(SNAPSHOT, [i.file for i in question.items])

    report = score(question, None, results, corpus, settled_run_counts(ROOT), files)

    assert question.start == "0008/AC-14"
    assert verdict(report).verdict is Verdict.INCONCLUSIVE


# AC-3: question 3 reproduced from the run files as committed at `36a6bc5`.

RECORDED = Path(__file__).parent / "fixtures" / "experiment-0009-q3-report.txt"


@pytest.fixture(scope="module")
def root_at_36a6bc5(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A root holding only `artifacts/` as committed at `36a6bc5`, made by `git archive`."""
    root = tmp_path_factory.mktemp("at-36a6bc5")
    archive = subprocess.run(
        ["git", "-C", str(ROOT), "archive", "36a6bc5", "artifacts"],
        capture_output=True,
        check=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(root)], input=archive, check=True)
    return root


def test_ac_3_question_3_at_36a6bc5_prints_experiment_0009s_recorded_block(
    root_at_36a6bc5: Path,
) -> None:
    """covers: AC-3, AC-2 (scored with no chain, no Neo4j, no API call)."""
    q3 = question_from(read_eval_set(ROOT / EVAL_FILE).entries, 3)
    results = committed_units(root_at_36a6bc5, SNAPSHOT)
    corpus = resolve_accepted(results, records_for_units(results, SNAPSHOT, "2e40bcf"))
    files = holding_units(SNAPSHOT, [i.file for i in q3.items])

    report = score(q3, None, results, corpus, settled_run_counts(root_at_36a6bc5), files)

    assert "\n".join(report_lines(report)) + "\n" == RECORDED.read_text()
