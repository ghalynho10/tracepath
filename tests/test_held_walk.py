"""The held marker, the filter and the printed `HELD:` over a hand built fixture (spec 0005).

The fixture (`tests/held_fixture.py`) is not an eval chain. The held walk's expected
output is written out by hand in `tests/fixtures/held-fixture-expected.txt`, so the
test holds the print to a reading of the rules, not to its own earlier output.
"""

import hashlib
from pathlib import Path
from typing import Any

import pytest

from tests import held_fixture as fx
from tests import trace_fixture
from tracepath.traverse.graph_slice import (
    GraphSlice,
    Link,
    Node,
    NodeKind,
    drop_held,
    graph_slice,
    link_from_properties,
    node_from_properties,
)
from tracepath.traverse.render import render_chain
from tracepath.traverse.walk import walk

EXPECTED = Path(__file__).parent / "fixtures" / "held-fixture-expected.txt"
WALK = Path(__file__).resolve().parents[1] / "src" / "tracepath" / "traverse" / "walk.py"

#: `walk.py` as spec 0005 found it, at its design commit `74e8406`.
WALK_SHA256 = "ee7f01765a42e685b0abfc3a35feb781c0a57cd7430b1314292221dbcce75a6b"


def nodes_of(
    records: tuple[dict[str, Any], ...],
    entities: tuple[dict[str, Any], ...],
    unresolved: tuple[dict[str, Any], ...],
) -> list[Node]:
    nodes = [node_from_properties(["Record"], row) for row in records]
    nodes += [node_from_properties(["Entity", row["type"]], row) for row in entities]
    nodes += [node_from_properties(["Unresolved"], row) for row in unresolved]
    return nodes


def links_of(links: tuple[tuple[str, dict[str, Any]], ...]) -> list[Link]:
    return [
        link_from_properties(link_type, row["from_id"], row["to_id"], row["properties"])
        for link_type, row in links
    ]


def held_slice(*, with_held: bool) -> GraphSlice:
    """The fixture, held items and all, as a slice built the way `read_graph()` builds it."""
    return graph_slice(
        nodes_of(fx.RECORDS, fx.ENTITIES, fx.UNRESOLVED), links_of(fx.LINKS), with_held=with_held
    )


def clean_slice() -> GraphSlice:
    """The same graph as a default load writes it: no held row at all."""
    return graph_slice(
        nodes_of(fx.RECORDS, fx.accepted_rows(fx.ENTITIES), fx.accepted_rows(fx.UNRESOLVED)),
        links_of(fx.accepted_links(fx.LINKS)),
    )


def held_ids(graph: GraphSlice) -> set[str]:
    return {n.canonical_id for n in graph.nodes if n.held} | {
        f"{k.source} -[{k.type}]-> {k.target}" for k in graph.links if k.held
    }


# The marker: read off the stored properties.


def test_a_held_entity_reads_back_held_with_its_reasons_in_stored_order() -> None:
    node = node_from_properties(["Entity"], fx.ENTITIES[1])

    assert node.held is True
    assert node.held_reasons == ("runs_disagree", "known_trap_flag")


def test_a_held_link_reads_back_held_with_its_reasons() -> None:
    [link] = links_of((fx.LINKS[0],))

    assert link.held is True
    assert link.held_reasons == ("known_trap_flag",)


def test_an_item_with_no_held_property_reads_back_not_held() -> None:
    node = node_from_properties(["Entity"], fx.ENTITIES[0])

    assert node.held is False
    assert node.held_reasons == ()


def test_a_held_unresolved_node_reads_back_held_with_no_reasons() -> None:
    node = node_from_properties(["Unresolved"], fx.UNRESOLVED[0])

    assert node.held is True
    assert node.held_reasons == ()


@pytest.mark.parametrize("stored", [False, "true", 1, None, [True]])
def test_only_a_stored_true_reads_as_held(stored: object) -> None:
    """`held` is stored as `true` or not at all (spec 0002 AC-11f); anything else is not held."""
    row = {**fx.ENTITIES[0], "held": stored, "held_reasons": ["runs_disagree"]}

    assert node_from_properties(["Entity"], row).held is False


@pytest.mark.parametrize("stored", ["runs_disagree", None, 3, {"runs_disagree": 1}])
def test_held_reasons_that_are_not_a_list_read_as_none(stored: object) -> None:
    row = {**fx.ENTITIES[1], "held_reasons": stored}

    assert node_from_properties(["Entity"], row).held_reasons == ()


def test_a_non_text_reason_inside_the_list_is_left_out() -> None:
    row = {**fx.ENTITIES[1], "held_reasons": ["runs_disagree", 7, "known_trap_flag"]}

    assert node_from_properties(["Entity"], row).held_reasons == (
        "runs_disagree",
        "known_trap_flag",
    )


# AC-2: the default slice drops every held item.


def test_ac_2_the_default_slice_drops_every_held_node_and_link() -> None:
    """covers: spec 0005 AC-2 (held nodes and held links are gone)."""
    graph = held_slice(with_held=False)

    assert held_ids(graph) == set()
    assert "9003/AC-2" not in {n.canonical_id for n in graph.nodes}
    assert "unresolved:9003:feature-77" not in {n.canonical_id for n in graph.nodes}


def test_ac_2_a_link_with_a_dropped_end_is_dropped_even_when_not_itself_held() -> None:
    """covers: spec 0005 AC-2 (a link left pointing at a dropped node goes too)."""
    graph = GraphSlice(
        nodes=(
            Node(canonical_id="9100/AC-1", kind=NodeKind.ENTITY),
            Node(canonical_id="9100/AC-2", kind=NodeKind.ENTITY, held=True),
        ),
        links=(Link(type="BLOCKED_BY", source="9100/AC-1", target="9100/AC-2"),),
    )

    assert drop_held(graph) == GraphSlice(
        nodes=(Node(canonical_id="9100/AC-1", kind=NodeKind.ENTITY),), links=()
    )


def test_ac_2_the_default_slice_equals_the_slice_of_a_graph_with_no_held_items() -> None:
    """covers: spec 0005 AC-2 (nothing but held items is dropped)."""
    assert held_slice(with_held=False) == clean_slice()


def test_with_held_the_slice_keeps_every_held_item() -> None:
    graph = held_slice(with_held=True)

    assert held_ids(graph) == {
        "9003/AC-2",
        "unresolved:9003:feature-77",
        "9003/AC-1 -[AMENDED_BY]-> 9003/AC-4",
        "9003/AC-1 -[CORRECTED_BY]-> 9003/AC-6",
        "9003/AC-1 -[SUPERSEDED_BY]-> 9003/AC-2",
        "9003/AC-2 -[BLOCKED_BY]-> 9003/AC-3",
        "9003/AC-2 -[UNCLASSIFIED]-> unresolved:9003:feature-77",
    }


def test_drop_held_over_the_held_slice_gives_the_default_slice() -> None:
    assert drop_held(held_slice(with_held=True)) == held_slice(with_held=False)


# AC-3: the default chain is byte identical to the chain over a graph with no held items.


def test_ac_3_the_default_chain_over_a_graph_with_held_items_is_byte_identical() -> None:
    """covers: spec 0005 AC-3."""
    with_held_items = render_chain(walk(held_slice(with_held=False), fx.START))
    without = render_chain(walk(clean_slice(), fx.START))

    assert "\n".join(with_held_items).encode() == "\n".join(without).encode()
    assert not any("HELD" in line for line in with_held_items)


# AC-7, AC-7b: the walk is not edited, and spec 0004's walk still prints as it did.


def test_ac_7_walk_py_is_byte_for_byte_the_file_spec_0005_found() -> None:
    """covers: spec 0005 AC-7."""
    assert hashlib.sha256(WALK.read_bytes()).hexdigest() == WALK_SHA256


def test_ac_7b_spec_0004_fixture_still_prints_its_hand_written_expectation() -> None:
    """covers: spec 0005 AC-7b (its full test file, `test_walk.py`, also runs unchanged)."""
    nodes = nodes_of(trace_fixture.RECORDS, trace_fixture.ENTITIES, trace_fixture.UNRESOLVED)
    lines = render_chain(
        walk(graph_slice(nodes, links_of(trace_fixture.LINKS)), trace_fixture.START)
    )

    expected = Path(__file__).parent / "fixtures" / "trace-fixture-expected.txt"
    assert "\n".join(lines) + "\n" == expected.read_text()


# AC-8: with held items kept, the walk steps through them.


def test_ac_8_the_held_walk_visits_a_held_node() -> None:
    """covers: spec 0005 AC-8 (a held node)."""
    steps = {s.node.canonical_id: s for s in walk(held_slice(with_held=True), fx.START).steps}

    assert steps["9003/AC-2"].node.held


def test_ac_8_the_held_walk_follows_a_held_link() -> None:
    """covers: spec 0005 AC-8 (a held link)."""
    steps = {s.node.canonical_id: s for s in walk(held_slice(with_held=True), fx.START).steps}

    via = steps["9003/AC-3"].via
    assert via is not None and via.held


def test_ac_8_the_held_walk_reaches_an_accepted_node_only_a_held_link_leads_to() -> None:
    """covers: spec 0005 AC-8 (an accepted node behind a held link)."""
    held = {s.node.canonical_id: s for s in walk(held_slice(with_held=True), fx.START).steps}
    clean = {s.node.canonical_id for s in walk(held_slice(with_held=False), fx.START).steps}

    step = held["9003/AC-4"]
    assert not step.node.held
    assert step.via is not None and step.via.held
    assert "9003/AC-4" not in clean


# AC-9 to AC-11: the printed marker.


def test_ac_9_to_ac_11_the_held_walk_prints_the_hand_written_expectation() -> None:
    """covers: spec 0005 AC-9, AC-9b, AC-10, AC-11 (the whole print, held steps and all)."""
    lines = render_chain(walk(held_slice(with_held=True), fx.START))

    assert "\n".join(lines) + "\n" == EXPECTED.read_text()


def test_ac_9_a_held_entity_heading_ends_with_its_reasons() -> None:
    """covers: spec 0005 AC-9."""
    lines = render_chain(walk(held_slice(with_held=True), fx.START))

    assert (
        "hop 1  9003/AC-2  AcceptanceCriterion  struck: false  HELD: runs_disagree, known_trap_flag"
        in lines
    )


def test_ac_9b_a_held_unresolved_heading_says_only_held_links_reach_it() -> None:
    """covers: spec 0005 AC-9b."""
    lines = render_chain(walk(held_slice(with_held=True), fx.START))

    assert (
        "hop 2  unresolved:9003:feature-77  Unresolved  HELD: reached only by held links" in lines
    )


def test_ac_10_a_held_link_line_ends_with_its_reasons_in_name_detail_form() -> None:
    """covers: spec 0005 AC-10."""
    lines = render_chain(walk(held_slice(with_held=True), fx.START))

    assert any(
        line.strip().startswith("link  9003/AC-1 -[SUPERSEDED_BY]-> 9003/AC-2")
        and line.endswith("  HELD: endpoint_not_accepted:9003/AC-2")
        for line in lines
    )


def test_ac_11_the_held_count_line_sits_just_before_the_prompt_versions_line() -> None:
    """covers: spec 0005 AC-11 (a chain with held steps and links)."""
    lines = render_chain(walk(held_slice(with_held=True), fx.START))

    assert lines[-2:] == (
        "Held: 2 steps, 5 links",
        "Prompt versions: all 14 model made steps share prompt 0003.1.",
    )


def test_ac_11_a_chain_with_nothing_held_prints_no_held_line() -> None:
    """covers: spec 0005 AC-11 (a chain with neither)."""
    lines = render_chain(walk(held_slice(with_held=True), "9003/AC-7"))

    assert not any(line.startswith("Held:") for line in lines)
