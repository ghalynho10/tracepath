"""The report step: start rule, expected items, reached test and reasons (spec 0004 AC-34
to AC-41, AC-52), on synthetic eval entries, with no Neo4j.

The reasons are checked against the real rebuilt results of spec 0012's committed units,
which hold each case: `0012/AC-3` (file line 22) was held for review, and a held
`satisfies` link in `## Build plan` names `0012/AC-1` (file line 20). Chains are built by
hand, so each test controls exactly what was visited.
"""

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from tracepath.extract.schema import RelationshipType
from tracepath.pipeline import CorpusResolution, UnitResult, resolve_accepted
from tracepath.rebuild import committed_units, records_for_units
from tracepath.report import (
    EVAL_FILE,
    EvalEntryUnusable,
    Holding,
    Question,
    Reason,
    holding_units,
    question_from,
    read_question,
    report_lines,
    score,
)
from tracepath.resolve.endpoints import (
    Resolution,
    ResolvedEndpoint,
    ResolvedLink,
    Target,
    UnresolvedNode,
)
from tracepath.traverse.graph_slice import Node, NodeKind
from tracepath.traverse.walk import Chain, Step

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SPEC_0012 = "specs/0012-model-client-router/index.md"
SPEC_0013 = "specs/0013-job-search-and-results-list/index.md"
FULL = {("0012", s): 3 for s in ("requirements", "build-plan", "consequences", "follow-up")}


def trace_entry(record: str, file: str, line: int, also: Any = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"record": record, "file": f"docs/{file}", "line": line}
    if also is not None:
        entry["also"] = also
    return entry


def one_question(*trace: dict[str, Any]) -> Question:
    return question_from([{"question": "Why?", "trace": list(trace)}], 1)


@pytest.fixture(scope="module")
def evidence() -> tuple[tuple[UnitResult, ...], CorpusResolution]:
    results = tuple(r for r in committed_units(ROOT, SNAPSHOT) if r.unit.record_id == "0012")
    return results, resolve_accepted(results, records_for_units(results, SNAPSHOT, "2e40bcf"))


@pytest.fixture(scope="module")
def split() -> dict[str, tuple[Holding, ...]]:
    return holding_units(SNAPSHOT, [SPEC_0012, SPEC_0013])


def entity_step(canonical_id: str, file: str, file_line: int, hop: int = 0) -> Step:
    node = Node(canonical_id=canonical_id, kind=NodeKind.ENTITY, file=file, file_line=file_line)
    return Step(hop=hop, node=node, via=None, direction=None, parent=None, stop=None)


def other_step(node: Node, hop: int = 1) -> Step:
    return Step(hop=hop, node=node, via=None, direction=None, parent="x", stop=None)


def chain_of(*steps: Step) -> Chain:
    return Chain(start=steps[0].node.canonical_id, max_hops=3, steps=steps)


def scored(
    question: Question,
    chain: Chain | None,
    evidence: tuple[tuple[UnitResult, ...], CorpusResolution],
    split: dict[str, tuple[Holding, ...]],
    runs: dict[tuple[str, str], int] = FULL,
) -> list[tuple[bool, Reason | None]]:
    results, corpus = evidence
    report = score(question, chain, results, corpus, runs, split)
    return [(f.reached_by is not None, f.reason) for f in report.findings]


# AC-34: the start rule.


def test_the_start_is_the_first_trace_entry_with_trailing_text_ignored() -> None:
    question = one_question(trace_entry("spec 0002 AC-10 (struck)", SPEC_0012, 31))

    assert question.start == "0002/AC-10"


def test_a_first_entry_with_no_spec_ac_form_is_refused_naming_the_question() -> None:
    entries = [
        {"trace": [trace_entry("spec 0012 AC-1", SPEC_0012, 20)]},
        {"trace": [trace_entry("spec 0007 Consequences", SPEC_0012, 92)]},
    ]

    with pytest.raises(EvalEntryUnusable, match="question 2") as caught:
        question_from(entries, 2)

    assert "spec 0007 Consequences" in str(caught.value)


@pytest.mark.parametrize("entry", [{"question": "x"}, {"trace": []}])
def test_a_question_with_no_trace_list_is_refused(entry: dict[str, Any]) -> None:
    with pytest.raises(EvalEntryUnusable, match="no trace list"):
        question_from([entry], 1)


@pytest.mark.parametrize("number", [0, 2])
def test_a_question_number_outside_the_set_is_refused(number: int) -> None:
    with pytest.raises(EvalEntryUnusable, match=f"question {number} is not in the eval set"):
        question_from([{"trace": [trace_entry("spec 0012 AC-1", SPEC_0012, 20)]}], number)


def test_question_3_of_the_eval_set_starts_at_0002_ac_10_with_five_items() -> None:
    question = read_question(ROOT / EVAL_FILE, 3)

    assert question.start == "0002/AC-10"
    assert [(i.line, i.token) for i in question.items] == [
        (31, "AC-10"),
        (35, "AC-12"),
        (142, None),
        (36, "AC-13"),
        (232, None),
    ]
    assert {i.file for i in question.items} == {
        "specs/0002-deployment-and-environments/index.md",
        "specs/0007-auth-and-per-user-isolation/index.md",
    }


# AC-35: every trace and also entry is an item; a token belongs to its own line only.


@pytest.mark.parametrize("also", [{"line": 22}, [{"line": 22}, {"line": 23}]])
def test_also_entries_are_items_in_the_parents_file_without_its_token(also: Any) -> None:
    question = one_question(trace_entry("spec 0012 AC-1 and others", SPEC_0012, 20, also))

    parent, *extra = question.items
    assert parent.token == "AC-1"
    assert extra and all(i.token is None and i.file == SPEC_0012 for i in extra)


# AC-36, AC-37: the reached test, and every item listed.


def test_an_item_is_reached_by_a_visited_entity_at_its_file_and_file_line(
    evidence: Any, split: Any
) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))

    assert scored(question, chain_of(entity_step("0012/AC-1", SPEC_0012, 20)), evidence, split) == [
        (True, None)
    ]


def test_an_entity_at_the_same_line_of_another_file_does_not_reach_the_item(
    evidence: Any, split: Any
) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))
    elsewhere = chain_of(entity_step("0013/AC-1", SPEC_0013, 20))

    [(reached, _)] = scored(question, elsewhere, evidence, split)

    assert not reached


# AC-38: one reason, by fixed priority.


def test_an_item_in_a_section_never_extracted_is_section_not_extracted(
    evidence: Any, split: Any
) -> None:
    question = one_question(
        trace_entry("spec 0012 AC-1", SPEC_0012, 20),
        trace_entry("spec 0012 preamble", SPEC_0012, 2),
    )

    assert scored(question, None, evidence, split)[1] == (False, Reason.SECTION_NOT_EXTRACTED)


def test_an_item_whose_section_has_two_settled_runs_is_section_not_extracted(
    evidence: Any, split: Any
) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))
    two_runs = {**FULL, ("0012", "requirements"): 2}

    assert scored(question, None, evidence, split, two_runs) == [
        (False, Reason.SECTION_NOT_EXTRACTED)
    ]


def test_an_item_whose_entity_exists_in_a_run_but_was_not_accepted_is_held(
    evidence: Any, split: Any
) -> None:
    question = one_question(trace_entry("spec 0012 AC-3", SPEC_0012, 22))

    assert scored(question, None, evidence, split) == [(False, Reason.HELD_FOR_REVIEW)]


def test_a_visited_unresolved_node_naming_the_items_token_is_unresolved_endpoint(
    evidence: Any, split: Any
) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))
    gap = Node(
        canonical_id="unresolved:0013:spec-0012-ac-1",
        kind=NodeKind.UNRESOLVED,
        record="0012",
        mention="spec 0012 AC-1",
    )
    chain = chain_of(entity_step("0013/AC-1", SPEC_0013, 20), other_step(gap))

    assert scored(question, chain, evidence, split) == [(False, Reason.UNRESOLVED_ENDPOINT)]


def test_a_token_is_matched_whole_so_ac_1_is_not_found_in_ac_13(evidence: Any, split: Any) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))
    gap = Node(
        canonical_id="unresolved:0013:spec-0012-ac-13",
        kind=NodeKind.UNRESOLVED,
        record="0012",
        mention="spec 0012 AC-13",
    )
    chain = chain_of(entity_step("0013/AC-1", SPEC_0013, 20), other_step(gap))

    [(_, reason)] = scored(question, chain, evidence, split)

    assert reason is not Reason.UNRESOLVED_ENDPOINT


def test_an_item_with_no_token_cannot_be_unresolved_endpoint(evidence: Any, split: Any) -> None:
    question = one_question(
        trace_entry("spec 0013 AC-1", SPEC_0013, 20),
        trace_entry("spec 0012 the first criterion", SPEC_0012, 20),
    )
    gap = Node(
        canonical_id="unresolved:0013:spec-0012",
        kind=NodeKind.UNRESOLVED,
        record="0012",
        mention="spec 0012 AC-1",
    )
    chain = chain_of(entity_step("0013/AC-1", SPEC_0013, 20), other_step(gap))

    _, (_, reason) = scored(question, chain, evidence, split)

    assert reason is Reason.LINK_HELD, "the next reason in the order, not the token one"


def test_an_item_whose_record_was_reached_and_stopped_at_is_record_not_expanded(
    evidence: Any, split: Any
) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))
    record = Node(canonical_id="0012", kind=NodeKind.RECORD)
    chain = chain_of(entity_step("0013/AC-1", SPEC_0013, 20), other_step(record))

    assert scored(question, chain, evidence, split) == [(False, Reason.RECORD_NOT_EXPANDED)]


def test_an_item_a_held_link_names_as_an_endpoint_is_link_held(evidence: Any, split: Any) -> None:
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))

    assert scored(question, None, evidence, split) == [(False, Reason.LINK_HELD)]


def test_an_item_nothing_points_at_is_no_link(evidence: Any, split: Any) -> None:
    results, corpus = evidence
    no_held = (
        tuple(
            dataclasses.replace(r, routed=dataclasses.replace(r.routed, review=())) for r in results
        ),
        dataclasses.replace(corpus, held=()),
    )
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))

    assert scored(question, None, no_held, split) == [(False, Reason.NO_LINK)]


# AC-39: visited steps that match no item are counted, not judged.


def test_visited_steps_matching_no_item_are_counted(evidence: Any, split: Any) -> None:
    results, corpus = evidence
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))
    chain = chain_of(
        entity_step("0012/AC-1", SPEC_0012, 20),
        other_step(Node(canonical_id="0013", kind=NodeKind.RECORD)),
        entity_step("0012/AC-2", SPEC_0012, 21, hop=1),
    )

    report = score(question, chain, results, corpus, FULL, split)

    assert report.unmatched_steps == 2
    assert "Visited steps matching no expected item: 2 (information, not a verdict)." in (
        report_lines(report)
    )


# AC-40: accepted links outside the expected sections that touch the items' records.


def link(source: str, target: str, kind: Target, section: str) -> ResolvedLink:
    return ResolvedLink(
        type=RelationshipType.VERIFIES,
        source=ResolvedEndpoint(source, Target.ENTITY),
        target=ResolvedEndpoint(target, kind),
        phrase=None,
        date=None,
        source_record="0013",
        file=SPEC_0013 if section != "Requirements" else SPEC_0012,
        section=section,
        line=1,
    )


def test_links_outside_the_expected_sections_touching_their_records_are_listed(
    split: Any,
) -> None:
    gap = UnresolvedNode(
        canonical_id="unresolved:0013:spec-0012-ac-1",
        mention="spec 0012 AC-1",
        source_record="0013",
        file=SPEC_0013,
        section="Feature design",
        line=1,
        record="0012",
    )
    links = (
        link("0013/AC-1", "0012/AC-1", Target.ENTITY, "Feature design"),  # by entity id
        link("0013/AC-1", "0012", Target.RECORD, "Feature design"),  # by record
        link("0013/AC-1", gap.canonical_id, Target.UNRESOLVED, "Feature design"),  # by gap
        link("0013/AC-1", "0013/AC-2", Target.ENTITY, "Feature design"),  # touches 0013 only
        link("0012/AC-2", "0012/AC-1", Target.ENTITY, "Requirements"),  # inside a section
    )
    corpus = CorpusResolution(resolution=Resolution(links=links, unresolved=(gap,)), held=())
    question = one_question(trace_entry("spec 0012 AC-1", SPEC_0012, 20))

    report = score(question, None, (), corpus, FULL, split)

    assert [(k.target, k.section) for k in report.outside_links] == [
        ("0012/AC-1", "Feature design"),
        ("0012", "Feature design"),
        ("unresolved:0013:spec-0012-ac-1", "Feature design"),
    ]
    assert (
        "Accepted links written outside the expected sections that touch 0012: 3."
        in report_lines(report)
    )


# AC-41: the line on reaching an item in another record.


def test_reaching_an_item_in_another_record_is_said_with_its_hop(evidence: Any, split: Any) -> None:
    question = one_question(
        trace_entry("spec 0013 AC-1", SPEC_0013, 20), trace_entry("spec 0012 AC-1", SPEC_0012, 20)
    )
    results, corpus = evidence
    chain = chain_of(
        entity_step("0013/AC-1", SPEC_0013, 20), entity_step("0012/AC-1", SPEC_0012, 20, hop=1)
    )

    lines = report_lines(score(question, chain, results, corpus, FULL, split))

    assert lines[-1] == (
        "Across records: yes. An expected item outside 0013 was reached from the start: "
        "spec 0012 AC-1 (hop 1)."
    )


def test_reaching_only_the_start_record_is_not_across_records(evidence: Any, split: Any) -> None:
    question = one_question(
        trace_entry("spec 0013 AC-1", SPEC_0013, 20), trace_entry("spec 0012 AC-1", SPEC_0012, 20)
    )
    results, corpus = evidence
    chain = chain_of(entity_step("0013/AC-1", SPEC_0013, 20))

    lines = report_lines(score(question, chain, results, corpus, FULL, split))

    assert lines[-1].startswith("Across records: no.")


# AC-52: with no start in the graph, every item is reported, each with its reason.


def test_with_no_chain_every_item_is_not_reached_with_a_reason(evidence: Any, split: Any) -> None:
    question = one_question(
        trace_entry("spec 0012 AC-1", SPEC_0012, 20),
        trace_entry("spec 0012 AC-3", SPEC_0012, 22),
        trace_entry("spec 0012 preamble", SPEC_0012, 2),
    )

    assert scored(question, None, evidence, split) == [
        (False, Reason.LINK_HELD),
        (False, Reason.HELD_FOR_REVIEW),
        (False, Reason.SECTION_NOT_EXTRACTED),
    ]


# AC-31 and key invariant 1: the report step is the only reader of the eval set.


def test_only_the_report_step_names_the_eval_file() -> None:
    sources = sorted((ROOT / "src" / "tracepath").rglob("*.py"))

    naming = [p.relative_to(ROOT).as_posix() for p in sources if "linked-records" in p.read_text()]

    assert naming == ["src/tracepath/report.py"]
