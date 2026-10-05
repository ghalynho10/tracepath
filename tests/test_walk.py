"""The walk and its rendering over a hand built fixture graph, no Neo4j (spec 0004 AC-32).

The fixture (`tests/trace_fixture.py`) is not an eval chain. Its expected output is
written out by hand in `tests/fixtures/trace-fixture-expected.txt`, so the test compares
the walk against a reading of the rules, not against the walk's own earlier output.
"""

import dataclasses
from pathlib import Path

import pytest

from tests import trace_fixture as fx
from tracepath.traverse.graph_slice import (
    GraphSlice,
    Link,
    Node,
    NodeKind,
    graph_slice,
    link_from_properties,
    node_from_properties,
)
from tracepath.traverse.render import model_made_versions, render_chain
from tracepath.traverse.walk import Direction, StartNotInGraph, Stop, walk

EXPECTED = Path(__file__).parent / "fixtures" / "trace-fixture-expected.txt"
SOURCE = Path(__file__).resolve().parents[1] / "src" / "tracepath"


def fixture_slice(*, keep_part_of: bool = False) -> GraphSlice:
    """The fixture as a slice, built from the very rows the loader would write."""
    nodes = [node_from_properties(["Record"], row) for row in fx.RECORDS]
    nodes += [node_from_properties(["Entity", row["type"]], row) for row in fx.ENTITIES]
    nodes += [node_from_properties(["Unresolved"], row) for row in fx.UNRESOLVED]
    links = [
        link_from_properties(link_type, row["from_id"], row["to_id"], row["properties"])
        for link_type, row in fx.LINKS
    ]
    part_of = [
        Link(type="PART_OF", source=row["from_id"], target=row["to_id"]) for row in fx.PART_OF
    ]
    if keep_part_of:
        # Bypasses `graph_slice()`, which drops them, to prove the walk ignores them too.
        return GraphSlice(nodes=tuple(nodes), links=(*links, *part_of))
    return graph_slice(nodes, (*links, *part_of))


def ids(slice_: GraphSlice, start: str = fx.START) -> list[str]:
    return [step.node.canonical_id for step in walk(slice_, start).steps]


# AC-32: the whole output over the fixture matches the hand written expectation.


def test_the_walk_over_the_fixture_prints_the_hand_written_expectation() -> None:
    lines = render_chain(walk(fixture_slice(), fx.START))

    assert "\n".join(lines) + "\n" == EXPECTED.read_text()


# AC-21: both directions, the seven typed types.


def test_the_walk_follows_links_in_both_directions() -> None:
    steps = {s.node.canonical_id: s for s in walk(fixture_slice(), fx.START).steps}

    assert steps["9001/AC-2"].direction is Direction.OUTGOING
    assert steps["9001#build-plan:1"].direction is Direction.INCOMING
    assert steps["9001#build-plan:1"].via is not None
    assert steps["9001#build-plan:1"].via.source == "9001#build-plan:1"


def test_a_scenario_that_verifies_the_start_is_reached_from_it() -> None:
    only_verifies = graph_slice(
        fixture_slice().nodes,
        [k for k in fixture_slice().links if k.type == "VERIFIES"],
    )

    [_, scenario] = walk(only_verifies, fx.START).steps

    assert scenario.node.canonical_id == "9001#feature-design:1"
    assert scenario.hop == 1
    assert scenario.via is not None and scenario.via.type == "VERIFIES"
    assert scenario.direction is Direction.INCOMING


# AC-22: never PART_OF.


def test_the_walk_never_follows_part_of_even_when_the_slice_holds_it() -> None:
    reached = ids(fixture_slice(keep_part_of=True))

    assert "9001" not in reached, "9001 is reachable only by PART_OF"
    assert reached == ids(fixture_slice())


# AC-23: three hops, and the step at the limit says what it did not follow.


def test_the_walk_stops_at_three_hops_and_says_so() -> None:
    steps = {s.node.canonical_id: s for s in walk(fixture_slice(), fx.START).steps}

    assert max(s.hop for s in steps.values()) == 3
    assert "9001/AC-5" not in steps
    assert steps["9001/AC-4"].stop is Stop.DEPTH_LIMIT
    assert steps["9001/AC-4"].unfollowed == 1


def test_a_step_at_the_limit_with_nothing_beyond_it_is_not_marked() -> None:
    graph = fixture_slice()
    without_tail = graph_slice(
        graph.nodes, [k for k in graph.links if (k.source, k.target) != ("9001/AC-4", "9001/AC-5")]
    )

    steps = {s.node.canonical_id: s for s in walk(without_tail, fx.START).steps}

    assert steps["9001/AC-4"].stop is None


# AC-24: Record and Unresolved nodes are printed and never expanded, even as the start.


def test_a_record_and_an_unresolved_node_are_stops() -> None:
    steps = {s.node.canonical_id: s for s in walk(fixture_slice(), fx.START).steps}

    assert steps["9002"].stop is Stop.RECORD
    assert steps["unresolved:9001:feature-99"].stop is Stop.UNRESOLVED


@pytest.mark.parametrize(
    ("start", "stop"), [("9002", Stop.RECORD), ("unresolved:9001:feature-99", Stop.UNRESOLVED)]
)
def test_a_record_or_unresolved_start_is_printed_and_not_expanded(start: str, stop: Stop) -> None:
    [only] = walk(fixture_slice(), start).steps

    assert only.node.canonical_id == start
    assert only.stop is stop


def test_a_record_start_renders_its_stop_line() -> None:
    lines = render_chain(walk(fixture_slice(), "9002"))

    assert "       stopped: whole document, not expanded" in lines


# AC-25: breadth first, each node once, so a cycle ends.


def test_a_cycle_ends_and_every_node_is_visited_once() -> None:
    reached = ids(fixture_slice())

    assert len(reached) == len(set(reached))
    assert reached.index("9001#feature-design:1") < reached.index("9001/AC-3")


def test_the_queue_order_is_the_parent_order() -> None:
    hops = [s.hop for s in walk(fixture_slice(), fx.START).steps]

    assert hops == sorted(hops)


# AC-26: one fixed neighbour order.


def test_neighbours_are_taken_by_type_then_outgoing_first_then_id() -> None:
    reached = ids(fixture_slice())

    assert reached[:6] == [
        "9001/AC-1",
        "9002",  # AMENDED_BY
        "9001#build-plan:1",  # SATISFIES
        "9001/AC-2",  # SUPERSEDED_BY
        "unresolved:9001:feature-99",  # UNCLASSIFIED, outgoing
        "9001#feature-design:1",  # UNCLASSIFIED, incoming, before VERIFIES
    ]


def test_neighbours_of_one_type_and_direction_are_taken_by_id() -> None:
    node = Node(canonical_id="a", kind=NodeKind.ENTITY)
    others = [Node(canonical_id=c, kind=NodeKind.ENTITY) for c in ("c", "b", "d")]
    links = [Link(type="BLOCKED_BY", source="a", target=o.canonical_id) for o in others]

    assert ids(graph_slice([node, *others], reversed(links)), "a") == ["a", "b", "c", "d"]


def test_the_input_order_of_nodes_and_links_does_not_change_the_walk() -> None:
    graph = fixture_slice()
    shuffled = GraphSlice(nodes=graph.nodes[::-1], links=graph.links[::-1])

    assert render_chain(walk(shuffled, fx.START)) == render_chain(walk(graph, fx.START))


# AC-27: the struck flag is printed as stored and changes nothing.


def test_the_struck_flag_is_printed_as_stored_and_changes_no_step() -> None:
    graph = fixture_slice()
    unstruck = GraphSlice(
        nodes=tuple(dataclasses.replace(n, struck=False) for n in graph.nodes),
        links=graph.links,
    )

    assert "hop 0  9001/AC-1  AcceptanceCriterion  struck: true" in render_chain(
        walk(graph, fx.START)
    )
    assert ids(unstruck) == ids(graph)


# AC-28a to AC-29: each step cites its record.


def test_an_entity_step_prints_file_section_file_line_commit_and_prompt() -> None:
    lines = render_chain(walk(fixture_slice(), fx.START))

    assert (
        "       specs/9001-fixture-walk/index.md · Build plan · file line 60 · "
        "commit f1x7ure · prompt 0003.1"
    ) in lines


def test_a_link_step_prints_its_section_heading_line_commit_and_prompt() -> None:
    lines = render_chain(walk(fixture_slice(), fx.START))

    assert (
        "             specs/9001-fixture-walk/index.md · Build plan · line 59 · "
        'commit f1x7ure · prompt 0003.1 · "satisfies AC-1"'
    ) in lines


def test_a_record_step_prints_its_file_commit_and_code_no_model() -> None:
    lines = render_chain(walk(fixture_slice(), fx.START))

    assert "       specs/9002-fixture-neighbour/index.md · commit f1x7ure · code, no model" in lines


def test_an_unresolved_step_prints_mention_file_section_line_and_no_commit() -> None:
    lines = render_chain(walk(fixture_slice(), fx.START))

    assert '       mention "feature 99"' in lines
    assert (
        "       specs/9001-fixture-walk/index.md · Requirements · line 10 · no commit, no model"
    ) in lines


# AC-30: the closing line on prompt versions.


def test_model_made_steps_are_entities_and_reaching_links_each_counted_once() -> None:
    versions = model_made_versions(walk(fixture_slice(), fx.START))

    assert versions == {"0003.1": 11, "0003.0": 2}


def test_one_shared_version_is_said_plainly() -> None:
    graph = fixture_slice()
    same = GraphSlice(
        nodes=tuple(dataclasses.replace(n, prompt_version="0003.1") for n in graph.nodes),
        links=tuple(dataclasses.replace(k, prompt_version="0003.1") for k in graph.links),
    )

    lines = render_chain(walk(same, fx.START))

    assert lines[-1] == "Prompt versions: all 13 model made steps share prompt 0003.1."


# AC-20: a start the graph does not hold.


def test_a_start_the_graph_does_not_hold_names_it_and_mentions_review() -> None:
    with pytest.raises(StartNotInGraph) as caught:
        walk(fixture_slice(), "9001/AC-99")

    assert "9001/AC-99" in str(caught.value)
    assert "held for review" in str(caught.value)


# AC-31: the walk and its read never reference the eval set.


@pytest.mark.parametrize(
    "path",
    [
        SOURCE / "traverse" / "walk.py",
        SOURCE / "traverse" / "graph_slice.py",
        SOURCE / "traverse" / "render.py",
        SOURCE / "graph" / "read.py",
    ],
)
def test_the_walk_and_its_read_never_name_the_eval_set(path: Path) -> None:
    """No path into `eval/`, no eval file name, and no import of the report step that
    is the one reader of it. Prose saying so is allowed; reaching for it is not."""
    text = path.read_text()

    assert "eval/" not in text
    assert "linked-records" not in text
    assert "tracepath.report" not in text
    assert "EVAL" not in text
