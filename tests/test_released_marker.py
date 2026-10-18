"""The `RELEASED: narrow_hold` marker over a hand built fixture (spec 0008 AC-5f).

The fixture is spec 0004's walk fixture (`tests/trace_fixture.py`) with one entity,
`9001/AC-2`, and the link that reaches it stamped `accepted_by` `narrow_hold`, in the
shape `load --narrow-hold` writes. The printing reads only what the slice holds; no
function on the printing path takes the `--narrow-hold` flag, so the marker cannot
depend on it. The integration tests print it through the commands themselves.
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests import trace_fixture as fx
from tests.test_code_pass_commands import SNAPSHOT, eval_root, flat, runs_root
from tests.test_eval_runner import AC2_LINE, START_LINE, entry, fixture_question, scored
from tests.test_eval_runner import snapshot as eval_snapshot  # noqa: F401 (a fixture)
from tracepath.artifacts import GRAPH_BUILD
from tracepath.cli import app
from tracepath.config import Neo4jSettings
from tracepath.extract.schema import EntityType, RelationshipType
from tracepath.graph import connect
from tracepath.graph.load import (
    write_entities,
    write_links,
    write_part_of,
    write_records,
    write_unresolved,
)
from tracepath.graph.schema import clear, create_constraints
from tracepath.report import report_lines
from tracepath.traverse.graph_slice import (
    GraphSlice,
    graph_slice,
    link_from_properties,
    node_from_properties,
)
from tracepath.traverse.render import render_chain
from tracepath.traverse.walk import walk

RELEASED_ID = "9001/AC-2"
MARKER = "RELEASED: narrow_hold"
AC3_LINE = fx.SECTION_STARTS["Requirements"] + 5 - 1

runner = CliRunner()


def released_entities() -> tuple[dict[str, Any], ...]:
    return tuple(
        {**row, "accepted_by": "narrow_hold"} if row["canonical_id"] == RELEASED_ID else row
        for row in fx.ENTITIES
    )


def released_links() -> tuple[tuple[str, dict[str, Any]], ...]:
    found: list[tuple[str, dict[str, Any]]] = []
    for link_type, row in fx.LINKS:
        if link_type == "SUPERSEDED_BY" and row["to_id"] == RELEASED_ID:
            row = {**row, "properties": {**row["properties"], "accepted_by": "narrow_hold"}}
        found.append((link_type, row))
    return tuple(found)


def released_slice() -> GraphSlice:
    nodes = [node_from_properties(["Record"], row) for row in fx.RECORDS]
    nodes += [node_from_properties(["Entity", row["type"]], row) for row in released_entities()]
    nodes += [node_from_properties(["Unresolved"], row) for row in fx.UNRESOLVED]
    links = [
        link_from_properties(t, r["from_id"], r["to_id"], r["properties"])
        for t, r in released_links()
    ]
    return graph_slice(nodes, links)


def test_ac_5f_accepted_by_reads_back_on_a_node_and_a_link() -> None:
    """covers: AC-5f (the field the marker reads, read as stored)."""
    graph = released_slice()
    by_id = {node.canonical_id: node for node in graph.nodes}

    assert by_id[RELEASED_ID].accepted_by == "narrow_hold"
    assert by_id[fx.START].accepted_by == "auto"
    [link] = [k for k in graph.links if k.target == RELEASED_ID]
    assert link.accepted_by == "narrow_hold"
    assert all(k.accepted_by is None for k in graph.links if k is not link)


def test_ac_5f_trace_prints_the_marker_on_a_released_step_and_link_only() -> None:
    """covers: AC-5f (trace: the step heading and the link line; no marker elsewhere)."""
    lines = render_chain(walk(released_slice(), fx.START))

    marked = [line for line in lines if MARKER in line]
    assert marked == [
        f"hop 1  {RELEASED_ID}  AcceptanceCriterion  struck: false  {MARKER}",
        f"       link  {fx.START} -[SUPERSEDED_BY]-> {RELEASED_ID} "
        f"(outgoing from {fx.START})  {MARKER}",
    ]
    assert "Released by the narrow hold rule: 1 steps, 1 links" in lines


def test_ac_5f_a_chain_with_nothing_released_prints_as_before() -> None:
    """covers: AC-5f (an accepted item with no such value prints no marker or count)."""
    nodes = [node_from_properties(["Record"], row) for row in fx.RECORDS]
    nodes += [node_from_properties(["Entity", row["type"]], row) for row in fx.ENTITIES]
    nodes += [node_from_properties(["Unresolved"], row) for row in fx.UNRESOLVED]
    links = [
        link_from_properties(t, r["from_id"], r["to_id"], r["properties"]) for t, r in fx.LINKS
    ]

    lines = render_chain(walk(graph_slice(nodes, links), fx.START))

    assert not any("RELEASED" in line or "Released" in line for line in lines)


def test_ac_5f_the_eval_report_marks_items_reached_through_a_release(
    eval_snapshot: Path,  # noqa: F811
) -> None:
    """covers: AC-5f (eval and trace --eval: a reached item names the releases on its path)."""
    question = fixture_question(
        entry("spec 9001 AC-1", fx.FILE, START_LINE),
        entry("spec 9001 AC-2", fx.FILE, AC2_LINE),
        entry("spec 9001 AC-3", fx.FILE, AC3_LINE),
    )

    lines = report_lines(scored(question, released_slice(), eval_snapshot))

    via = f"{MARKER} via {fx.START} -[SUPERSEDED_BY]-> {RELEASED_ID}, {RELEASED_ID}"
    assert (
        f"  reached      spec 9001 AC-1 · {fx.FILE}:{START_LINE} · hop 0 · the start · {fx.START}"
        in lines
    )
    assert (
        f"  reached      spec 9001 AC-2 · {fx.FILE}:{AC2_LINE} · hop 1 · {RELEASED_ID} · {via}"
        in lines
    )
    assert f"  reached      spec 9001 AC-3 · {fx.FILE}:{AC3_LINE} · hop 2 · 9001/AC-3 · {via}" in (
        lines
    )


# Through the commands, against real Neo4j.


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        clear(opened, neo4j_settings.database)
        create_constraints(opened, neo4j_settings.database)
        yield opened
        clear(opened, neo4j_settings.database)


def write_fixture(driver: Driver, database: str) -> None:
    write_records(driver, database, fx.RECORDS)
    by_type: dict[EntityType, list[dict[str, object]]] = {}
    for row in released_entities():
        by_type.setdefault(EntityType(row["type"]), []).append(row)
    write_entities(driver, database, dict(by_type))
    write_unresolved(driver, database, fx.UNRESOLVED)
    write_part_of(driver, database, fx.PART_OF)
    by_link: dict[RelationshipType, list[dict[str, object]]] = {}
    for link_type, row in released_links():
        by_link.setdefault(RelationshipType[link_type], []).append(row)
    write_links(driver, database, dict(by_link))


@pytest.mark.integration
def test_ac_5f_trace_prints_the_marker_from_the_stored_graph(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-5f (`trace START` takes no --narrow-hold, and prints the marker anyway)."""
    write_fixture(driver, neo4j_settings.database)

    result = runner.invoke(app, ["trace", fx.START])

    assert result.exit_code == 0, result.stderr
    assert f"hop 1  {RELEASED_ID}  AcceptanceCriterion  struck: false  {MARKER}" in result.stdout
    assert "Released by the narrow hold rule: 1 steps, 1 links" in result.stdout


@pytest.mark.integration
def test_ac_5f_eval_and_trace_eval_print_the_marker_after_load_narrow_hold(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-5f (the commands, over a graph `load --narrow-hold` wrote from real runs)."""
    root = runs_root(tmp_path, "0002", "0007")
    eval_file = eval_root(tmp_path / "unused", None) / "eval"
    shutil.copytree(eval_file, root / "eval")
    loaded = runner.invoke(
        app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT), "--narrow-hold"]
    )
    assert loaded.exit_code == 0, loaded.stderr
    assert json.loads((root / GRAPH_BUILD).read_text())["narrow_hold"] is True
    args = ["--root", str(root), "--snapshot", str(SNAPSHOT), "--narrow-hold"]

    scored_all = runner.invoke(app, ["eval", *args])
    traced = runner.invoke(app, ["trace", "--eval", "3", *args])

    assert MARKER in flat(scored_all.stdout)
    assert MARKER in flat(traced.stdout)
    assert f"{MARKER} via" in flat(traced.stdout), "the report line names the releases too"
