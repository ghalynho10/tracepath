"""`load --with-held` and `trace --with-held` against a real Neo4j (spec 0005).

Every command runs over a copy of the committed artifacts under a temporary root, so the
repository's own `artifacts/graph-build.json` is never rewritten by a test. The eval
question here is the synthetic spec 0012 one of `test_trace_eval.py`, not an eval
question, so nothing here says anything about question 3.

One module fixture loads the corpus three times, once without the flag and twice with
it, and keeps what each load wrote, so each test reads one fact.
"""

import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests.test_trace_eval import QUESTIONS
from tracepath import cli
from tracepath.artifacts import GRAPH_BUILD, RUNS_DIR
from tracepath.cli import app
from tracepath.config import Neo4jSettings
from tracepath.graph import connect
from tracepath.graph.load import LINK_TYPES
from tracepath.graph.schema import clear
from tracepath.pipeline import HeldViewIncomplete, build_held_view, resolve_accepted
from tracepath.rebuild import committed_units, records_for_units
from tracepath.report import EVAL_FILE, HELD_LABEL, HELD_MEANING

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
TYPED = sorted(LINK_TYPES.values())

#: The real eval question 3 under the held view, the second result's exact command.
QUESTION_3 = ("trace", "--eval", "3", "--with-held", "--eval-file", str(ROOT / EVAL_FILE))

#: What that command printed when experiment 0010 recorded the second result.
RECORDED = ROOT / "experiments" / "0010-held-item-view" / "data" / "trace-1.txt"

runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


def invoke(*args: str) -> tuple[int, str, str]:
    result = runner.invoke(app, list(args))
    return result.exit_code, result.stdout, result.stderr


def load(root: Path, *flags: str) -> tuple[int, str, str]:
    return invoke("load", "--root", str(root), "--snapshot", str(SNAPSHOT), *flags)


def trace(root: Path, *args: str) -> tuple[int, str, str]:
    return invoke(
        "trace", *args, "--eval-file", "eval/questions.json", "--root", str(root),
        "--snapshot", str(SNAPSHOT),
    )  # fmt: skip


def rows(driver: Driver, database: str, query: str) -> list[dict[str, Any]]:
    found, _, _ = driver.execute_query(query, types=TYPED, database_=database)
    return [record.data() for record in found]


@dataclass(frozen=True)
class Written:
    """What one load wrote, read back from the graph, and what it printed."""

    stdout: str
    manifest: bytes
    held_nodes: int
    held_links: int
    accepted_entities: list[dict[str, Any]]
    accepted_links: list[dict[str, Any]]
    held_entities: list[dict[str, Any]]
    held_typed_links: list[dict[str, Any]]
    held_unresolved: list[dict[str, Any]]
    unresolved: list[dict[str, Any]]
    held_unresolved_accepted_links: int
    shared_unresolved: list[str]


def read_back(driver: Driver, database: str, stdout: str, manifest: bytes) -> Written:
    def q(query: str) -> list[dict[str, Any]]:
        return rows(driver, database, query)

    return Written(
        stdout=stdout,
        manifest=manifest,
        held_nodes=q("MATCH (n) WHERE n.held IS NOT NULL RETURN count(n) AS n")[0]["n"],
        held_links=q("MATCH ()-[r]->() WHERE r.held IS NOT NULL RETURN count(r) AS n")[0]["n"],
        accepted_entities=q(
            "MATCH (e:Entity) WHERE e.held IS NULL "
            "RETURN e.canonical_id AS id, properties(e) AS p, labels(e) AS labels "
            "ORDER BY id"
        ),
        accepted_links=q(
            "MATCH (a)-[r]->(b) WHERE type(r) IN $types AND r.held IS NULL "
            "RETURN type(r) AS type, a.canonical_id AS a, b.canonical_id AS b, "
            "properties(r) AS p ORDER BY type, a, b"
        ),
        held_entities=q(
            "MATCH (e:Entity {held: true}) "
            "OPTIONAL MATCH (e)-[:PART_OF]->(r:Record) "
            "RETURN e.canonical_id AS id, e.held_reasons AS reasons, "
            "e.accepted_by AS accepted_by, r.canonical_id AS record ORDER BY id"
        ),
        held_typed_links=q(
            "MATCH (a)-[r]->(b) WHERE type(r) IN $types AND r.held = true "
            "RETURN type(r) AS type, a.canonical_id AS a, b.canonical_id AS b, "
            "r.held_reasons AS reasons ORDER BY type, a, b"
        ),
        held_unresolved=q(
            "MATCH (u:Unresolved {held: true}) "
            "RETURN u.canonical_id AS id, u.held_reasons AS reasons ORDER BY id"
        ),
        unresolved=q(
            "MATCH (u:Unresolved) WHERE u.held IS NULL "
            "RETURN u.canonical_id AS id, properties(u) AS p ORDER BY id"
        ),
        held_unresolved_accepted_links=q(
            "MATCH (u:Unresolved {held: true})-[r]-() WHERE r.held IS NULL RETURN count(r) AS n"
        )[0]["n"],
        shared_unresolved=[
            row["id"]
            for row in q(
                "MATCH (u:Unresolved) WHERE u.held IS NULL "
                "AND EXISTS { (u)-[h]-() WHERE h.held = true } "
                "RETURN u.canonical_id AS id ORDER BY id"
            )
        ],
    )


@dataclass(frozen=True)
class Loads:
    root: Path
    default: Written
    held: Written
    second_manifest: bytes
    default_trace: tuple[int, str, str]
    default_eval: tuple[int, str, str]
    refused: tuple[int, str, str]
    held_graph_trace: tuple[int, str, str]
    held_graph_eval: tuple[int, str, str]
    held_eval: tuple[tuple[int, str, str], tuple[int, str, str]]
    question_3: tuple[tuple[int, str, str], tuple[int, str, str]]
    missing_start: tuple[int, str, str]


@pytest.fixture(scope="module")
def loads(
    tmp_path_factory: pytest.TempPathFactory, neo4j_settings: Neo4jSettings
) -> Iterator[Loads]:
    root = tmp_path_factory.mktemp("held")
    shutil.copytree(ROOT / RUNS_DIR, root / RUNS_DIR)
    (root / "eval").mkdir()
    (root / "eval" / "questions.json").write_text(json.dumps(QUESTIONS))
    database = neo4j_settings.database
    with connect(neo4j_settings) as driver:
        code, stdout, stderr = load(root)
        assert code == 0, stderr
        default = read_back(driver, database, stdout, (root / GRAPH_BUILD).read_bytes())
        default_trace = trace(root, "0012/AC-7")
        default_eval = trace(root, "--eval", "1")
        refused = trace(root, "0012/AC-7", "--with-held")

        code, stdout, stderr = load(root, "--with-held")
        assert code == 0, stderr
        held = read_back(driver, database, stdout, (root / GRAPH_BUILD).read_bytes())
        held_graph_trace = trace(root, "0012/AC-7")
        held_graph_eval = trace(root, "--eval", "1")
        held_eval = (
            trace(root, "--eval", "1", "--with-held"),
            trace(root, "--eval", "1", "--with-held"),
        )
        # Question 3's result is recorded (experiment 0010), so running it is no longer
        # a held out run; every other real question stays untouched here.
        question_3 = (
            invoke(*QUESTION_3, "--root", str(root), "--snapshot", str(SNAPSHOT)),
            invoke(*QUESTION_3, "--root", str(root), "--snapshot", str(SNAPSHOT)),
        )
        missing_start = trace(root, "9999/AC-1", "--with-held")

        code, _, stderr = load(root, "--with-held")
        assert code == 0, stderr
        second = (root / GRAPH_BUILD).read_bytes()
        yield Loads(
            root, default, held, second, default_trace, default_eval, refused,
            held_graph_trace, held_graph_eval, held_eval, question_3, missing_start,
        )  # fmt: skip
        clear(driver, database)


@pytest.fixture(scope="module")
def view_counts() -> dict[str, int]:
    results = committed_units(ROOT, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, "2e40bcf")
    return build_held_view(results, resolve_accepted(results, records), records).counts()


# AC-1, AC-5: a default load writes nothing held and says nothing about it.


def test_ac_1_a_default_load_writes_no_node_with_a_held_property(loads: Loads) -> None:
    """covers: spec 0005 AC-1 (nodes)."""
    assert loads.default.held_nodes == 0


def test_ac_1_a_default_load_writes_no_relationship_with_a_held_property(loads: Loads) -> None:
    """covers: spec 0005 AC-1 (relationships)."""
    assert loads.default.held_links == 0


def test_ac_5_a_default_load_writes_no_held_view_key(loads: Loads) -> None:
    """covers: spec 0005 AC-5 (the manifest)."""
    assert "held_view" not in json.loads(loads.default.manifest)


def test_ac_5_a_default_load_prints_no_held_line(loads: Loads) -> None:
    """covers: spec 0005 AC-5 (the output)."""
    assert "held" not in loads.default.stdout.lower().replace("links held across units", "")


# AC-6: the accepted graph is the same either way.


def test_ac_6_a_held_load_writes_the_same_accepted_entities(loads: Loads) -> None:
    """covers: spec 0005 AC-6 (entities: number, id, every property, every label)."""
    assert loads.held.accepted_entities == loads.default.accepted_entities
    assert loads.held.accepted_entities


def test_ac_6_a_held_load_writes_the_same_accepted_links(loads: Loads) -> None:
    """covers: spec 0005 AC-6 (links: number, endpoints, every property)."""
    assert loads.held.accepted_links == loads.default.accepted_links
    assert loads.held.accepted_links


# AC-17, AC-18: held entities, marked, with no `accepted_by`.


def test_ac_17_every_held_entity_is_written_held_with_its_reasons(
    loads: Loads, view_counts: dict[str, int]
) -> None:
    """covers: spec 0005 AC-17."""
    held = {row["id"]: row for row in loads.held.held_entities}

    assert len(held) == view_counts["entities"]
    assert held["0002/AC-10"]["reasons"] == ["known_trap_flag"]
    assert all(row["reasons"] for row in held.values())


def test_ac_17_every_held_entity_hangs_from_its_record(loads: Loads) -> None:
    """covers: spec 0005 AC-17 (`PART_OF` written for it as for any entity)."""
    assert all(row["record"] is not None for row in loads.held.held_entities)


def test_ac_18_a_held_entity_has_no_accepted_by(loads: Loads) -> None:
    """covers: spec 0005 AC-18."""
    assert all(row["accepted_by"] is None for row in loads.held.held_entities)


# AC-19, AC-20, AC-20b: held links and the gap nodes they make.


def test_ac_19_every_held_link_is_written_held_with_its_reasons(
    loads: Loads, view_counts: dict[str, int]
) -> None:
    """covers: spec 0005 AC-19."""
    links = loads.held.held_typed_links

    assert len(links) == view_counts["links"]
    assert all(row["reasons"] for row in links)
    assert {
        "type": "UNCLASSIFIED",
        "a": "0007/AC-13",
        "b": "0002",
        "reasons": ["endpoint_not_accepted:0007/AC-13"],
    } in links


def test_ac_20_an_unresolved_node_only_held_links_reach_is_held(
    loads: Loads, view_counts: dict[str, int]
) -> None:
    """covers: spec 0005 AC-20."""
    assert len(loads.held.held_unresolved) == view_counts["unresolved"] > 0
    assert loads.held.held_unresolved_accepted_links == 0


def test_ac_20_a_held_unresolved_node_carries_no_reasons(loads: Loads) -> None:
    """covers: spec 0005 AC-20 (`held`, and no `held_reasons`)."""
    assert all(row["reasons"] is None for row in loads.held.held_unresolved)


def test_ac_20b_an_unresolved_node_an_accepted_link_reaches_stays_unchanged(
    loads: Loads,
) -> None:
    """covers: spec 0005 AC-20b."""
    assert loads.held.shared_unresolved
    assert loads.held.unresolved == loads.default.unresolved


# AC-21b, AC-22b, AC-23b: the counts the load prints.


def test_ac_21b_to_ac_23b_the_held_load_prints_its_skip_and_not_written_counts(
    loads: Loads, view_counts: dict[str, int]
) -> None:
    """covers: spec 0005 AC-21b, AC-22b, AC-23b."""
    out = flat(loads.held.stdout)

    assert (
        f"Skipped as already written: {view_counts['skipped_entities']} held entities, "
        f"{view_counts['skipped_links']} held links."
    ) in out
    assert (
        f"Not written, no first run item behind them: {view_counts['not_written']} queue rows."
    ) in out
    assert "nothing accepted" in out


# AC-24, AC-25: the manifest.


def test_ac_24_a_held_load_manifest_carries_the_six_held_counts(
    loads: Loads, view_counts: dict[str, int]
) -> None:
    """covers: spec 0005 AC-24."""
    assert json.loads(loads.held.manifest)["held_view"] == view_counts


def test_ac_25_two_held_loads_write_byte_identical_manifests(loads: Loads) -> None:
    """covers: spec 0005 AC-25."""
    assert loads.second_manifest == loads.held.manifest


# AC-3, AC-4: without the flag, a graph holding held items reads as if it held none.


def test_ac_3_a_trace_without_the_flag_prints_the_same_chain_over_a_held_graph(
    loads: Loads,
) -> None:
    """covers: spec 0005 AC-3 (through the real command)."""
    assert loads.held_graph_trace == loads.default_trace
    assert loads.default_trace[0] == 0


def test_ac_4_trace_eval_without_the_flag_prints_no_held_line_outcome_or_label(
    loads: Loads,
) -> None:
    """covers: spec 0005 AC-4 (through the real command)."""
    code, stdout, stderr = loads.held_graph_eval
    lines = stdout.splitlines()

    assert code == 0, stderr
    assert (code, stdout, stderr) == loads.default_eval
    assert HELD_LABEL not in lines and HELD_MEANING not in lines
    assert not any(line.startswith("  held only") or "HELD:" in line for line in lines)
    assert not any("through held items" in line for line in lines)


# AC-26, AC-26b: the flag on a graph with nothing held is refused.


def test_ac_26_trace_with_held_on_a_default_graph_exits_1(loads: Loads) -> None:
    """covers: spec 0005 AC-26."""
    assert loads.refused[0] == 1


def test_ac_26b_the_refusal_names_load_with_held_and_prints_no_chain(loads: Loads) -> None:
    """covers: spec 0005 AC-26b."""
    _, stdout, stderr = loads.refused

    assert "tracepath load --with-held" in flat(stderr)
    assert stdout == ""
    assert "Traceback" not in stderr


# The flagged trace: labelled, and the same twice.


def test_trace_eval_with_held_twice_prints_identical_labelled_output(loads: Loads) -> None:
    """The determinism AC-27 asks of question 3, here on a synthetic question."""
    first, second = loads.held_eval

    assert first == second
    assert first[0] == 0, first[2]
    assert HELD_LABEL in first[1].splitlines()


# AC-27: question 3 under the held view, the second result itself.


def test_ac_27_trace_eval_3_with_held_twice_prints_identical_output(loads: Loads) -> None:
    """covers: spec 0005 AC-27."""
    first, second = loads.question_3

    assert first[0] == 0, first[2]
    assert first == second


def test_ac_27_question_3_still_prints_the_result_experiment_0010_recorded(loads: Loads) -> None:
    """covers: spec 0005 AC-27 (the recorded second result does not drift).

    The record is frozen, so the one wording change made since, spec 0006 AC-10's start
    marker on an item line at hop 0, is applied to it here rather than written into it.
    """
    code, stdout, stderr = loads.question_3[0]
    recorded = RECORDED.read_text().replace(" · hop 0 · ", " · hop 0 · the start · ")

    assert (code, stderr) == (0, "")
    assert recorded != RECORDED.read_text(), "the record holds a hop 0 item line"
    assert stdout == recorded


# A start the held graph does not hold.


def test_trace_with_held_from_a_start_not_in_the_graph_exits_1_naming_it(loads: Loads) -> None:
    code, stdout, stderr = loads.missing_start

    assert code == 1
    assert "9999/AC-1 is not in the graph" in flat(stderr)
    assert stdout == ""
    assert "Traceback" not in stderr


# AC-19b: a held view that cannot be accounted for stops the load before any write.


def test_ac_19b_an_incomplete_held_view_stops_the_load_before_any_write(
    loads: Loads, neo4j_settings: Neo4jSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: spec 0005 AC-19b (the load exits 1, and the graph is the one before it)."""

    def incomplete(*_: object) -> NoReturn:
        raise HeldViewIncomplete("a held link with no review item behind it")

    monkeypatch.setattr(cli, "build_held_view", incomplete)
    with connect(neo4j_settings) as driver:
        before = read_back(driver, neo4j_settings.database, "", b"")
        code, stdout, stderr = load(loads.root, "--with-held")
        after = read_back(driver, neo4j_settings.database, "", b"")

    assert code == 1
    assert "no review item behind it" in flat(stderr)
    assert "Loaded" not in stdout
    assert after == before
