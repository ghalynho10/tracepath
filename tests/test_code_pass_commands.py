"""The code pass through the commands (spec 0007 AC-6 to AC-8b, AC-16, AC-17).

The queue and refusal tests need no database. The load test runs against a real Neo4j
over a copy of committed run files under `tmp_path`, so the repository's own
`artifacts/` is never rewritten. Only `eval/linked-records-research.json` is copied
into a temporary root; the held out file is never opened (AC-30).
"""

import json
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tracepath.artifacts import GRAPH_BUILD, REVIEW_QUEUE, REVIEW_QUEUE_CODE_PASS, RUNS_DIR
from tracepath.cli import _committed, app
from tracepath.config import Neo4jSettings
from tracepath.graph import connect
from tracepath.graph.schema import clear
from tracepath.pipeline import resolve_accepted
from tracepath.rebuild import (
    apply_code_pass,
    code_pass_report,
    committed_units,
    records_for_units,
    released_links,
)
from tracepath.report import EVAL_FILE

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"

runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


def runs_root(root: Path, *units: str) -> Path:
    """A root holding a copy of the named units' run files, or every unit's when none."""
    if not units:
        shutil.copytree(ROOT / RUNS_DIR, root / RUNS_DIR)
    for unit in units:
        shutil.copytree(ROOT / RUNS_DIR / unit, root / RUNS_DIR / unit)
    return root


# AC-6, AC-8, AC-8b: the two queues.


@dataclass(frozen=True)
class Queues:
    root: Path
    plain: bytes
    after_code_pass: bytes
    plain_code: int
    code_pass_code: int


@pytest.fixture(scope="module")
def queues(tmp_path_factory: pytest.TempPathFactory) -> Queues:
    """`review-queue`, then `review-queue --code-pass`, over every committed run file."""
    root = runs_root(tmp_path_factory.mktemp("queues"))
    args = ["review-queue", "--root", str(root), "--snapshot", str(SNAPSHOT)]
    first = runner.invoke(app, args)
    plain = (root / REVIEW_QUEUE).read_bytes()
    second = runner.invoke(app, [*args, "--code-pass"])
    return Queues(
        root=root,
        plain=plain,
        after_code_pass=(root / REVIEW_QUEUE).read_bytes(),
        plain_code=first.exit_code,
        code_pass_code=second.exit_code,
    )


def test_ac_6_a_plain_review_queue_reproduces_the_committed_queue(queues: Queues) -> None:
    """covers: AC-6."""
    assert queues.plain_code == 0
    assert queues.plain == (ROOT / REVIEW_QUEUE).read_bytes()


def test_ac_8_review_queue_with_the_pass_writes_its_own_file(queues: Queues) -> None:
    """covers: AC-8 (and it holds fewer rows: the pass only ever releases)."""
    assert queues.code_pass_code == 0
    rows = json.loads((queues.root / REVIEW_QUEUE_CODE_PASS).read_text())
    assert 0 < len(rows) < len(json.loads(queues.plain))


def test_ac_8b_review_queue_with_the_pass_leaves_the_default_queue_alone(queues: Queues) -> None:
    """covers: AC-8b."""
    assert queues.after_code_pass == queues.plain


# AC-7c: the refusal before any connection.


def eval_root(root: Path, code_pass: bool | None) -> Path:
    """A root holding the eval file and a manifest; `None` writes no `code_pass` key."""
    (root / EVAL_FILE).parent.mkdir(parents=True)
    shutil.copy(ROOT / EVAL_FILE, root / EVAL_FILE)
    manifest: dict[str, object] = {"corpus_commit": COMMIT, "units": []}
    if code_pass is not None:
        manifest["code_pass"] = code_pass
    (root / GRAPH_BUILD).parent.mkdir(parents=True)
    (root / GRAPH_BUILD).write_text(json.dumps(manifest))
    return root


def invoke_unreachable(*args: str) -> tuple[int, str]:
    """Run a command with Neo4j unreachable, so a connection attempt would say so."""
    result = runner.invoke(app, list(args), env={"NEO4J_URI": UNREACHABLE_URI})
    return result.exit_code, flat(result.stderr)


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_7c_the_pass_on_against_a_graph_loaded_without_it_is_refused(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-7c (a missing key means false; refused before connecting)."""
    root = eval_root(tmp_path, None)

    code, stderr = invoke_unreachable(*command, "--code-pass", "--root", str(root))

    assert code == 1
    assert "--code-pass scores the code pass routing, but artifacts/graph-build.json" in stderr
    assert "localhost:1" not in stderr, "refused before any connection was tried"


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_7c_the_pass_off_against_a_graph_loaded_with_it_is_refused(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-7c (the other direction)."""
    root = eval_root(tmp_path, True)

    code, stderr = invoke_unreachable(*command, "--root", str(root))

    assert code == 1
    assert "artifacts/graph-build.json says the graph was loaded with --code-pass" in stderr
    assert "localhost:1" not in stderr


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_7c_a_matching_setting_goes_on_to_connect(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-7c (no refusal when the settings match; the unreachable graph says so)."""
    root = eval_root(tmp_path, True)

    code, stderr = invoke_unreachable(*command, "--code-pass", "--root", str(root))

    assert code == 1
    assert "graph-build.json" not in stderr


def test_trace_with_the_pass_needs_an_eval_question() -> None:
    """covers: AC-7 (`trace` takes `--code-pass` only with `--eval`)."""
    code, stderr = invoke_unreachable("trace", "0002/AC-1", "--code-pass")

    assert code == 1
    assert "--code-pass changes the routing scored, so it needs --eval N." in stderr


def test_ac_7d_the_scoring_routes_with_the_pass() -> None:
    """covers: AC-7d (what `eval` and `trace --eval` score is the pass routing)."""
    on = _committed(ROOT, SNAPSHOT, COMMIT, True)

    assert any(result.released for result in on.results)
    assert on.results == apply_code_pass(committed_units(ROOT, SNAPSHOT))


# AC-6b, AC-7b, AC-16, AC-17: the load.


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        yield opened
        clear(opened, neo4j_settings.database)


def run_load(root: Path, *extra: str) -> tuple[int, str, str]:
    result = runner.invoke(app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT), *extra])
    return result.exit_code, result.stdout, result.stderr


def accepted_by(driver: Driver, database: str) -> dict[str, list[str]]:
    records, _, _ = driver.execute_query(
        "MATCH (e:Entity) RETURN e.accepted_by AS by, collect(e.canonical_id) AS ids",
        database_=database,
    )
    return {record["by"]: sorted(record["ids"]) for record in records}


@pytest.mark.integration
def test_load_with_and_without_the_pass(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-7b, AC-16, AC-17, then AC-6b (a plain load after restores the manifest)."""
    root = runs_root(tmp_path, "0002", "0007")
    results = committed_units(root, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, COMMIT)
    with_pass = apply_code_pass(results)
    links = released_links(resolve_accepted(results, records), resolve_accepted(with_pass, records))
    report = {(r.record, r.section): r for r in code_pass_report(with_pass, links)}
    released = sorted(i for r in with_pass for i in r.released)
    assert released, "these two records hold flag only criteria the pass releases"

    code, stdout, stderr = run_load(root, "--code-pass")

    assert code == 0, stderr
    assert json.loads((root / GRAPH_BUILD).read_text())["code_pass"] is True
    stamped = accepted_by(driver, neo4j_settings.database)
    assert stamped["code_pass"] == released
    assert set(stamped) == {"auto", "code_pass"}
    row = report[("0002", "Requirements")]
    assert (
        f"0002 Requirements: code decided {len(row.decided)} ({', '.join(row.decided)}); "
        f"{row.released_entities} entities released, {row.released_links} links released; "
        f"{row.not_decided} parsed bullets not code decided; {row.struck} bullets opening "
        f"with ~~ after the colon left to the model; {row.unparsed} other AC bullets failed "
        "the parse."
    ) in flat(stdout)
    assert "0007 Feature design: code decided 0 (none); 0 entities released, " in flat(stdout)
    assert f"Code pass total: {len(released)} entities and {len(links)} links released" in flat(
        stdout
    )

    code, stdout, stderr = run_load(root)

    assert code == 0, stderr
    assert "code_pass" not in json.loads((root / GRAPH_BUILD).read_text())
    assert "Code pass" not in stdout
    assert set(accepted_by(driver, neo4j_settings.database)) == {"auto"}
