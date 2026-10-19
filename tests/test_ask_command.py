"""The `ask` command (spec 0009), with a hand built graph and no paid call.

The graph read is swapped for `tests/ask_fixture.py`'s slice, so these run without
Neo4j. The integration tests at the end read the real graph through `_ask_graph()`.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests import ask_fixture as fx
from tests import test_held_walk_graph as held_graph
from tests import test_walk_graph as trace_graph
from tracepath import cli
from tracepath.config import Neo4jSettings
from tracepath.graph import connect
from tracepath.graph.schema import clear, create_constraints
from tracepath.traverse.graph_slice import GraphSlice, drop_held

runner = CliRunner()

MANIFEST = {"corpus_commit": "2e40bcf", "held_view": {"entities": 1}, "narrow_hold": True}
QUESTION = "Why does the landing rule read the profile row?"


def flat(text: str) -> str:
    return " ".join(text.split())


def write_manifest(root: Path, manifest: object = MANIFEST) -> None:
    path = root / "artifacts" / "graph-build.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest))


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A root with a build manifest, and the graph read swapped for the fixture slice."""
    write_manifest(tmp_path)
    monkeypatch.setattr(cli, "_ask_graph", fx.graph)
    yield tmp_path


def ask(root: Path, *args: str) -> tuple[int, str, str]:
    result = runner.invoke(cli.app, ["ask", *args, "--root", str(root)])
    return result.exit_code, result.stdout, result.stderr


def no_graph_read() -> GraphSlice:
    raise AssertionError("the graph was read")


# AC-2, AC-3: the arguments, checked before anything is read.


@pytest.mark.parametrize("args", [(), (QUESTION, "--eval", "1")])
def test_ac_2_both_or_neither_question_and_eval_exit_1_before_the_graph_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, args: tuple[str, ...]
) -> None:
    """covers: AC-2."""
    monkeypatch.setattr(cli, "_ask_graph", no_graph_read)

    code, _, err = ask(tmp_path, *args, "--ceiling", "1")

    assert code == 1
    assert "one QUESTION or --eval N" in flat(err)


@pytest.mark.parametrize(
    ("ceiling", "said"),
    [
        ((), "--ceiling USD is required"),
        (("--ceiling", "0"), "above 0"),
        (("--ceiling", "nan"), "above 0"),
        (("--ceiling", "-1"), "above 0"),
    ],
)
def test_ac_3_a_missing_or_bad_ceiling_exits_1_before_the_graph_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ceiling: tuple[str, ...], said: str
) -> None:
    """covers: AC-3."""
    monkeypatch.setattr(cli, "_ask_graph", no_graph_read)

    code, out, err = ask(tmp_path, QUESTION, *ceiling)

    assert code == 1
    assert said in flat(err)
    assert out == ""


# AC-4, AC-5b, AC-5c, AC-6, AC-12: the dry run, the graph checks, no match.


def test_ac_4_a_dry_run_prints_the_words_and_items_and_writes_no_record(repo: Path) -> None:
    """covers: AC-4 (the words and the items; the count and bound are step 3's)."""
    code, out, err = ask(repo, QUESTION, "--ceiling", "1", "--dry-run")

    assert code == 0, err
    assert "Search words: landing, rule, read, profile, row" in out
    assert f"  9101/AC-1  AcceptanceCriterion  accepted  {fx.FILE}:10  hit" in out
    assert "Dry run: no call made" in out
    assert not (repo / "artifacts" / "asks").exists()


def test_ac_5b_a_graph_holding_no_held_item_exits_1_naming_the_load(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-5b."""
    monkeypatch.setattr(cli, "_ask_graph", lambda: drop_held(fx.graph()))

    code, out, err = ask(repo, QUESTION, "--ceiling", "1", "--dry-run")

    assert code == 1
    assert "`tracepath load` without --no-with-held" in flat(err)
    assert out == ""


def test_ac_5c_one_line_names_how_the_graph_was_loaded(repo: Path) -> None:
    """covers: AC-5c."""
    _, out, _ = ask(repo, QUESTION, "--ceiling", "1", "--dry-run")

    assert out.splitlines()[:2] == [
        f"Question: {QUESTION}",
        "Graph: held view yes, narrow hold yes, corpus 2e40bcf.",
    ]


def test_ac_5c_a_graph_loaded_without_either_setting_says_no(repo: Path) -> None:
    """covers: AC-5c."""
    write_manifest(repo, {"corpus_commit": "abc1234"})

    _, out, _ = ask(repo, QUESTION, "--ceiling", "1", "--dry-run")

    assert "Graph: held view no, narrow hold no, corpus abc1234." in out


@pytest.mark.parametrize("manifest", ["not json", None])
def test_ac_6_an_unreadable_or_missing_manifest_exits_1_with_no_traceback(
    repo: Path, manifest: str | None
) -> None:
    """covers: AC-6 (an unreadable `graph-build.json`)."""
    path = repo / "artifacts" / "graph-build.json"
    if manifest is None:
        path.unlink()
    else:
        path.write_text(manifest)

    code, out, err = ask(repo, QUESTION, "--ceiling", "1", "--dry-run")

    assert code == 1
    assert "graph-build.json" in err
    assert "Traceback" not in out + err


def test_ac_12_no_matching_item_says_so_makes_no_call_and_exits_0(repo: Path) -> None:
    """covers: AC-12."""
    code, out, _ = ask(repo, "Why is the moon round?", "--ceiling", "1")

    assert code == 0
    assert "No item matches the search words, so no call is made." in out
    assert not (repo / "artifacts" / "asks").exists()


# Against a real Neo4j: the read `ask` makes.

pytest_integration = pytest.mark.integration


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        clear(opened, neo4j_settings.database)
        create_constraints(opened, neo4j_settings.database)
        yield opened
        clear(opened, neo4j_settings.database)


@pytest_integration
def test_ac_5_ask_reads_held_items_and_finds_one(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-5. 9003/AC-2 is held, and the only node holding `review`."""
    held_graph.write_fixture(driver, neo4j_settings.database)
    write_manifest(tmp_path)

    code, out, err = ask(tmp_path, "Why does review hold back?", "--ceiling", "1", "--dry-run")

    assert code == 0, err
    assert "9003/AC-2  AcceptanceCriterion  held" in out


@pytest_integration
def test_ac_5b_a_real_graph_with_no_held_item_is_refused(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-5b, over the real read."""
    trace_graph.write_fixture(driver, neo4j_settings.database)
    write_manifest(tmp_path)

    code, _, err = ask(tmp_path, QUESTION, "--ceiling", "1", "--dry-run")

    assert code == 1
    assert "holds no held item" in flat(err)


def test_ac_6_ask_with_no_neo4j_password_exits_1_naming_it(tmp_path: Path) -> None:
    """covers: AC-6 (`SettingsInvalid`)."""
    write_manifest(tmp_path)
    result = runner.invoke(
        cli.app,
        ["ask", QUESTION, "--ceiling", "1", "--root", str(tmp_path)],
        env={"NEO4J_PASSWORD": ""},
    )

    assert result.exit_code == 1
    assert "NEO4J_PASSWORD" in flat(result.stderr)
    assert "Traceback" not in result.output


def test_ac_6_ask_when_neo4j_is_down_exits_1_with_no_traceback(tmp_path: Path) -> None:
    """covers: AC-6 (`GraphUnavailable`)."""
    write_manifest(tmp_path)
    result = runner.invoke(
        cli.app,
        ["ask", QUESTION, "--ceiling", "1", "--root", str(tmp_path)],
        env={"NEO4J_URI": "bolt://localhost:1"},
    )

    assert result.exit_code == 1
    assert "docker compose up -d" in flat(result.stderr)
    assert "Traceback" not in result.output
