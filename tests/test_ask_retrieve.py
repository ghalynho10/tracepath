"""How `ask` finds its items: search words, scores, neighbours, history (spec 0009).

Pure: every graph here is hand built (`tests/ask_fixture.py`), so no database is read
and no model is called.
"""

import math

import pytest

from tests import ask_fixture as fx
from tests.ask_fixture import entity, link
from tracepath.ask import retrieve
from tracepath.ask.retrieve import (
    build_pack,
    item_line,
    pack_lines,
    scored,
    searchable,
    tokenise,
)
from tracepath.traverse.graph_slice import GraphSlice, Link, Node, graph_slice


def pack_ids(graph: GraphSlice, question: str) -> list[str]:
    return [item.node.canonical_id for item in build_pack(graph, question).items]


def fillers(count: int) -> tuple[Node, ...]:
    """Nodes holding no search word, so a word's df stays below N."""
    return tuple(entity(f"9109/AC-{n}", "nothing here") for n in range(1, count + 1))


# AC-7: the search words.


def test_ac_7_a_path_and_a_call_are_kept_whole_and_stripped() -> None:
    """covers: AC-7."""
    question = "Why does the landing rule (src/lib/landing-rule.ts) reuse readOwnProfile()?"

    assert tokenise(question) == (
        "landing",
        "rule",
        "src",
        "lib",
        "landing-rule.ts",
        "reuse",
        "readownprofile",
    )


def test_ac_7_stoplist_words_and_short_words_without_a_digit_are_dropped() -> None:
    """covers: AC-7."""
    assert tokenise("An ok q1 7 to db, with THE rather than") == ("q1", "7")


def test_ac_7_a_joined_tokens_parts_of_three_or_more_are_words_less_the_stoplist() -> None:
    """covers: AC-7."""
    assert tokenise("read-the-file_now ac-19") == (
        "read-the-file_now",
        "read",
        "file",
        "now",
        "ac-19",
    )


def test_ac_7_each_word_appears_once_in_first_seen_order() -> None:
    """covers: AC-7."""
    assert tokenise("profile row Profile, row.") == ("profile", "row")


# AC-8, AC-8b: what a node is found by, and its score.


def test_ac_8_a_question_naming_an_id_finds_the_item_through_it() -> None:
    """covers: AC-8."""
    named = entity("0007/AC-19", "Unrelated words entirely.")
    graph = graph_slice((named, *fillers(3)), (), with_held=True)

    assert pack_ids(graph, "What does 0007 AC-19 say?") == ["0007/AC-19"]


def test_ac_8_a_record_is_found_by_its_title_and_an_unresolved_node_by_its_mention() -> None:
    """covers: AC-8."""
    assert {"landing", "fixture", "9101"} <= searchable(fx.NODES[6])
    assert {"feature", "77"} <= searchable(fx.NODES[7])


def test_ac_8_there_is_no_stemming() -> None:
    """covers: AC-8."""
    assert pack_ids(fx.graph(), "profiles") == []


def test_ac_8b_a_node_scores_the_sum_of_ln_n_over_df_for_each_word_found() -> None:
    """covers: AC-8b. 8 nodes: `profile` is in 1, `row` in 3, `matter` in none."""
    ranked = scored(fx.graph(), tokenise("Why does the profile row matter?"))
    score = {node.canonical_id: value for node, value in ranked}

    assert score["9101/AC-1"] == pytest.approx(math.log(8 / 1) + math.log(8 / 3))
    assert score["9101/AC-3"] == pytest.approx(math.log(8 / 3))
    assert score["9102/AC-1"] == 0


def test_ac_8b_nodes_are_ordered_by_score_then_by_canonical_id() -> None:
    """covers: AC-8b."""
    ranked = scored(fx.graph(), tokenise("profile row"))

    assert [node.canonical_id for node, _ in ranked[:3]] == ["9101/AC-1", "9101/AC-3", "9101/AC-4"]


# AC-9 to AC-12b: hits, neighbours, order, the cut, the links sent.


def test_ac_9_the_hits_are_the_sixteen_best_scoring_nodes() -> None:
    """covers: AC-9."""
    nodes = tuple(entity(f"9101/AC-{n:02}", "alpha") for n in range(1, 21))
    pack = build_pack(graph_slice((*nodes, *fillers(1)), (), with_held=True), "alpha")

    assert pack.hits == 16
    assert [item.node.canonical_id for item in pack.items] == [
        f"9101/AC-{n:02}" for n in range(1, 17)
    ]


def test_ac_9_a_node_scoring_zero_is_not_a_hit() -> None:
    """covers: AC-9. A word found in every node scores ln(1) = 0."""
    nodes = tuple(entity(f"9101/AC-{n}", "alpha") for n in range(1, 4))

    assert build_pack(graph_slice(nodes, (), with_held=True), "alpha").items == ()


def test_ac_10_neighbours_are_added_both_ways_up_to_two_hops_held_links_included() -> None:
    """covers: AC-10, AC-5 (a held item and a held link are searched and followed)."""
    pack = build_pack(fx.graph(), "profile")

    assert [(i.node.canonical_id, i.hop) for i in pack.items] == [
        ("9101/AC-1", 0),
        ("9101/AC-2", 1),
        ("unresolved:9101:feature-77", 1),
        ("9102/AC-1", 2),
    ]


@pytest.mark.parametrize(
    ("hops", "expected"),
    [
        (0, [("9101/AC-1", 0)]),
        (1, [("9101/AC-1", 0), ("9101/AC-2", 1), ("unresolved:9101:feature-77", 1)]),
    ],
)
def test_ac_10_note_hops_stops_the_neighbours_at_that_many_hops(
    hops: int, expected: list[tuple[str, int]]
) -> None:
    """covers: AC-10 note of 2026-10-20 (`ask --hops`, experiment 0016)."""
    pack = build_pack(fx.graph(), "profile", hops)

    assert [(i.node.canonical_id, i.hop) for i in pack.items] == expected
    assert pack.hops == hops
    assert pack_lines(pack)[1].endswith(f"; hops {hops}).")


def test_ac_10_note_two_hops_is_the_default() -> None:
    """covers: AC-10 note of 2026-10-20: no `hops` given makes the same pack as before."""
    assert build_pack(fx.graph(), "profile") == build_pack(fx.graph(), "profile", 2)
    assert build_pack(fx.graph(), "profile").hops == 2


def test_ac_10_note_at_zero_hops_a_history_hit_still_brings_its_replacement() -> None:
    """covers: AC-10 note of 2026-10-20 with AC-14b: replacements are not hops."""
    nodes = (entity("9101/AC-1", "alpha"), entity("9101/AC-2", "nothing"), *fillers(1))
    links = (link("SUPERSEDED_BY", "9101/AC-1", "9101/AC-2"),)
    pack = build_pack(graph_slice(nodes, links, with_held=True), "alpha", 0)

    assert [(i.node.canonical_id, i.hop) for i in pack.items] == [
        ("9101/AC-1", 0),
        ("9101/AC-2", 1),
    ]


@pytest.mark.parametrize("hops", [-1, 3])
def test_ac_10_note_a_hop_count_outside_0_to_2_is_refused(hops: int) -> None:
    """covers: AC-10 note of 2026-10-20."""
    with pytest.raises(ValueError, match="hops"):
        build_pack(fx.graph(), "profile", hops)


def test_ac_10_part_of_is_never_followed() -> None:
    """covers: AC-10."""
    part_of = Link(type="PART_OF", source="9101/AC-1", target="9101")

    assert "9101" not in pack_ids(fx.graph(links=(*fx.LINKS, part_of)), "profile")


def test_ac_11_each_hop_is_ordered_by_the_highest_ranked_hit_that_reached_it() -> None:
    """covers: AC-11."""
    nodes = (
        entity("9101/AC-1", "alpha beta"),
        entity("9101/AC-2", "alpha"),
        entity("9102/AC-1", "nothing"),
        entity("9102/AC-9", "nothing"),
        *fillers(2),
    )
    links = (
        link("BLOCKED_BY", "9101/AC-1", "9102/AC-9"),
        link("VERIFIES", "9102/AC-1", "9101/AC-2"),
    )

    assert pack_ids(graph_slice(nodes, links, with_held=True), "alpha beta") == [
        "9101/AC-1",
        "9101/AC-2",
        "9102/AC-9",
        "9102/AC-1",
    ]


def test_ac_11_at_most_ninety_items_are_sent_and_the_cut_is_counted() -> None:
    """covers: AC-11."""
    hub = entity("9101/AC-1", "alpha")
    around = tuple(entity(f"9102/AC-{n:03}", "nothing") for n in range(1, 101))
    links = tuple(link("BLOCKED_BY", "9101/AC-1", n.canonical_id) for n in around)
    pack = build_pack(graph_slice((hub, *around), links, with_held=True), "alpha")

    assert len(pack.items) == 90
    assert pack.cut == 11
    assert pack_lines(pack)[1] == "Items sent: 90 (1 hits, 89 neighbours, 11 cut; hops 2)."


def test_ac_12_no_node_scoring_above_zero_sends_nothing_and_says_so() -> None:
    """covers: AC-12."""
    pack = build_pack(fx.graph(), "Why is the moon round?")

    assert pack.items == ()
    assert pack_lines(pack) == (
        "Search words: moon, round",
        "No item matches the search words, so no call is made.",
    )


def test_ac_12b_every_link_between_two_items_sent_is_sent_with_its_phrase_and_held_mark() -> None:
    """covers: AC-12b. The VERIFIES link reaches 9102/AC-2, which is not sent."""
    sent = build_pack(fx.graph(), "profile").links

    assert [(k.type, k.source, k.target, k.phrase, k.held) for k in sent] == [
        ("AMENDED_BY", "9101/AC-1", "9101/AC-2", "amended by AC-2", True),
        ("BLOCKED_BY", "9101/AC-2", "9102/AC-1", None, False),
        ("UNCLASSIFIED", "9101/AC-1", "unresolved:9101:feature-77", "see feature 77", False),
    ]


# AC-13, AC-14, AC-14b: what an item line shows, and history.


def test_ac_13_each_item_line_shows_id_type_held_history_citation_and_hop() -> None:
    """covers: AC-13."""
    lines = pack_lines(build_pack(fx.graph(), "landing"))

    assert lines[2:] == (
        f"  9101  record  accepted  {fx.FILE}  hit",
        f"  9101/AC-1  AcceptanceCriterion  accepted  {fx.FILE}:10  hit",
        f"  9101/AC-3  AcceptanceCriterion  accepted  STRUCK  {fx.FILE}:12  hit",
        f"  9101/AC-4  AcceptanceCriterion  accepted  {fx.FILE}:13  hit",
        f"  9101/AC-2  AcceptanceCriterion  held  {fx.FILE}:11  hop 1",
        f"  unresolved:9101:feature-77  unresolved  held  {fx.FILE}:40  hop 1",
        f"  9102/AC-1  AcceptanceCriterion  accepted  {fx.OTHER}:20  hop 2",
    )


def test_ac_14_a_superseded_or_corrected_source_is_history_and_an_amended_source_is_not() -> None:
    """covers: AC-14."""
    nodes = (
        entity("9101/AC-1", "alpha"),
        entity("9101/AC-2", "alpha"),
        entity("9101/AC-3", "alpha"),
        entity("9101/AC-4", "alpha"),
        entity("9101/AC-5", "alpha"),
        entity("9101/AC-6", "alpha"),
        *fillers(1),
    )
    links = (
        link("CORRECTED_BY", "9101/AC-1", "9101/AC-2"),
        link("SUPERSEDED_BY", "9101/AC-3", "9101/AC-4", held=True),
        link("AMENDED_BY", "9101/AC-5", "9101/AC-6"),
    )
    pack = build_pack(graph_slice(nodes, links, with_held=True), "alpha")
    history = {i.node.canonical_id: i.history for i in pack.items}

    assert history == {
        "9101/AC-1": True,
        "9101/AC-2": False,
        "9101/AC-3": True,
        "9101/AC-4": False,
        "9101/AC-5": False,
        "9101/AC-6": False,
    }
    assert "HISTORY" in item_line(pack.items[0])


def test_ac_14_a_struck_item_is_history_and_prints_struck() -> None:
    """covers: AC-14, AC-13."""
    (item,) = (i for i in build_pack(fx.graph(), "landing").items if i.node.struck)

    assert item.history
    assert item.replaced_by == ("9101/AC-4",)


def test_ac_14b_the_item_replacing_a_history_item_is_added_right_behind_it() -> None:
    """covers: AC-14b. 9101/AC-3 is at hop 2, so what replaces it sits at hop 3."""
    nodes = (
        entity("9101/AC-1", "alpha"),
        entity("9101/AC-2", "nothing"),
        entity("9101/AC-3", "nothing"),
        entity("9101/AC-4", "nothing"),
        entity("9101/AC-5", "nothing"),
    )
    links = (
        link("BLOCKED_BY", "9101/AC-1", "9101/AC-2"),
        link("BLOCKED_BY", "9101/AC-2", "9101/AC-3"),
        link("SUPERSEDED_BY", "9101/AC-3", "9101/AC-4", held=True),
        link("BLOCKED_BY", "9101/AC-2", "9101/AC-5"),
    )
    pack = build_pack(graph_slice(nodes, links, with_held=True), "alpha")

    assert [(i.node.canonical_id, i.hop) for i in pack.items] == [
        ("9101/AC-1", 0),
        ("9101/AC-2", 1),
        ("9101/AC-3", 2),
        ("9101/AC-4", 3),
        ("9101/AC-5", 2),
    ]


def test_ac_14b_a_replacement_counts_against_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """covers: AC-14b, AC-11 note. With room for three, the history item and its replacement
    do not fit, and the cut counts both, the replacement reached by no hop included.
    """
    monkeypatch.setattr(retrieve, "ITEM_LIMIT", 3)
    nodes = (
        entity("9101/AC-1", "alpha"),
        entity("9101/AC-2", "nothing"),
        entity("9101/AC-3", "nothing"),
        entity("9101/AC-4", "nothing"),
    )
    links = (
        link("BLOCKED_BY", "9101/AC-1", "9101/AC-2"),
        link("BLOCKED_BY", "9101/AC-2", "9101/AC-3"),
        link("SUPERSEDED_BY", "9101/AC-3", "9101/AC-4"),
    )
    pack = build_pack(graph_slice(nodes, links, with_held=True), "alpha")

    assert [i.node.canonical_id for i in pack.items] == ["9101/AC-1", "9101/AC-2"]
    assert pack.cut == 2
    assert pack_lines(pack)[1] == "Items sent: 2 (1 hits, 1 neighbours, 2 cut; hops 2)."


def test_ac_14b_an_item_after_a_cut_history_item_is_cut_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """covers: AC-14b, AC-11 note. 9101/AC-5 alone would fit the third place, but it comes
    after 9101/AC-3 and its replacement, which do not, so it is cut and counted with them.
    """
    monkeypatch.setattr(retrieve, "ITEM_LIMIT", 3)
    nodes = (
        entity("9101/AC-1", "alpha"),
        entity("9101/AC-2", "nothing"),
        entity("9101/AC-3", "nothing"),
        entity("9101/AC-4", "nothing"),
        entity("9101/AC-5", "nothing"),
    )
    links = (
        link("BLOCKED_BY", "9101/AC-1", "9101/AC-2"),
        link("BLOCKED_BY", "9101/AC-2", "9101/AC-3"),
        link("SUPERSEDED_BY", "9101/AC-3", "9101/AC-4"),
        link("BLOCKED_BY", "9101/AC-2", "9101/AC-5"),
    )
    pack = build_pack(graph_slice(nodes, links, with_held=True), "alpha")

    assert [i.node.canonical_id for i in pack.items] == ["9101/AC-1", "9101/AC-2"]
    assert pack.cut == 3
    assert pack_lines(pack)[1] == "Items sent: 2 (1 hits, 1 neighbours, 3 cut; hops 2)."


def test_the_same_graph_and_question_always_make_the_same_pack() -> None:
    """Key invariant 3: retrieval is a pure function of the slice and the question."""
    assert build_pack(fx.graph(), "landing row") == build_pack(fx.graph(), "landing row")
