"""`trace --eval` on the real committed graph, against a synthetic eval file (spec 0004
AC-34, AC-42, AC-43, AC-44, AC-52).

The questions here are not eval questions: they cite spec 0012, which no eval chain
touches, so these runs say nothing about question 3. The graph is the committed corpus,
loaded through the `load` command from a copy of its artifacts.
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tracepath.artifacts import RUNS_DIR
from tracepath.cli import app
from tracepath.config import Neo4jSettings
from tracepath.graph import connect

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SPEC_0012 = "docs/specs/0012-model-client-router/index.md"

QUESTIONS = {
    "entries": [
        {
            "question": "Why does the router span open first?",
            "trace": [
                {"record": "spec 0012 AC-7", "file": SPEC_0012, "line": 26},
                {
                    "record": "spec 0012 build step registering the span",
                    "file": SPEC_0012,
                    "line": 88,
                    "also": {"line": 2},
                },
            ],
        },
        {
            "question": "A start that is not in the graph",
            "trace": [
                {"record": "spec 0002 AC-10 (struck)", "file": SPEC_0012, "line": 26},
                {"record": "spec 0012 AC-3", "file": SPEC_0012, "line": 22},
            ],
        },
        {
            "question": "A first entry with no start",
            "trace": [{"record": "spec 0012 Consequences", "file": SPEC_0012, "line": 95}],
        },
    ]
}

runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture(scope="module")
def corpus_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("corpus")
    shutil.copytree(ROOT / RUNS_DIR, root / RUNS_DIR)
    (root / "eval").mkdir()
    (root / "eval" / "questions.json").write_text(json.dumps(QUESTIONS))
    return root


def load(root: Path) -> None:
    result = runner.invoke(app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT)])
    assert result.exit_code == 0, result.stderr


@pytest.fixture
def loaded(corpus_root: Path, neo4j_settings: Neo4jSettings) -> Iterator[Path]:
    """The committed corpus in the graph, loaded again whenever another test replaced it."""
    with connect(neo4j_settings) as driver:
        if not _holds_corpus(driver, neo4j_settings.database):
            load(corpus_root)
    yield corpus_root


def _holds_corpus(driver: Driver, database: str) -> bool:
    found, _, _ = driver.execute_query(
        "MATCH (e:Entity {canonical_id: '0012/AC-7'}) RETURN count(e) AS n", database_=database
    )
    return bool(found[0]["n"])


def trace_eval(root: Path, number: int) -> tuple[int, str, str]:
    result = runner.invoke(
        app,
        [
            "trace",
            "--eval",
            str(number),
            "--eval-file",
            "eval/questions.json",
            "--root",
            str(root),
            "--snapshot",
            str(SNAPSHOT),
        ],
    )
    return result.exit_code, result.stdout, result.stderr


def test_trace_eval_prints_the_chain_then_the_scored_items(loaded: Path) -> None:
    code, stdout, stderr = trace_eval(loaded, 1)

    assert code == 0, stderr
    lines = stdout.splitlines()
    assert lines[0].startswith("Chain from 0012/AC-7:")
    assert "Question 1: Why does the router span open first?" in lines
    assert 'Start item: 0012/AC-7, from the first trace entry "spec 0012 AC-7".' in lines
    assert (
        "  reached      spec 0012 AC-7 · specs/0012-model-client-router/index.md:26 · hop 0 · "
        "0012/AC-7"
    ) in lines
    assert (
        "  reached      spec 0012 build step registering the span · "
        "specs/0012-model-client-router/index.md:88 · hop 1 · 0012#build-plan:7"
    ) in lines
    assert (
        "  not reached  spec 0012 build step registering the span (also) · "
        "specs/0012-model-client-router/index.md:2 · section_not_extracted"
    ) in lines
    assert lines[-1].startswith("Across records: no.")


def test_trace_eval_twice_prints_identical_output(loaded: Path) -> None:
    first = trace_eval(loaded, 1)
    second = trace_eval(loaded, 1)

    assert first == second


def test_a_reload_from_the_same_artifacts_leaves_the_output_unchanged(loaded: Path) -> None:
    before = trace_eval(loaded, 1)

    load(loaded)

    assert trace_eval(loaded, 1) == before


def test_a_start_not_in_the_graph_still_prints_every_item_then_exits_1(loaded: Path) -> None:
    code, stdout, stderr = trace_eval(loaded, 2)

    assert code == 1
    assert "0002/AC-10 is not in the graph" in flat(stderr)
    assert "Chain from" not in stdout
    assert (
        "  not reached  spec 0012 AC-3 · specs/0012-model-client-router/index.md:22 · "
        "held_for_review"
    ) in stdout.splitlines()
    assert "Traceback" not in stdout + stderr


def test_a_first_entry_with_no_start_exits_1_naming_the_question(loaded: Path) -> None:
    code, stdout, stderr = trace_eval(loaded, 3)

    assert code == 1
    assert "question 3" in flat(stderr)
    assert "no start item is guessed" in flat(stderr)
    assert stdout == ""


def test_a_start_and_eval_together_are_refused() -> None:
    result = runner.invoke(app, ["trace", "0012/AC-7", "--eval", "1"])

    assert result.exit_code == 1
    assert "not both" in flat(result.stderr)
