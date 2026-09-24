import json
import logging
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tracepath import __version__, config
from tracepath.artifacts import REVIEW_LOG, REVIEW_QUEUE, RUNS_DIR
from tracepath.cli import app
from tracepath.config import Neo4jSettings

PROJECT_ROOT = Path(__file__).resolve().parents[1]

runner = CliRunner()


def flat(text: str) -> str:
    """Rich wraps long lines at 80 columns; compare on single spaced text."""
    return " ".join(text.split())


def test_version_prints_name_and_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"tracepath {__version__}"


def test_no_arguments_shows_help_listing_status() -> None:
    result = runner.invoke(app, [])

    assert "Usage" in result.output
    assert "status" in result.output


def test_unknown_command_is_rejected() -> None:
    result = runner.invoke(app, ["frobnicate"])

    assert result.exit_code == 2
    assert "No such command" in result.output


def test_status_without_a_password_names_the_missing_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep the developer's real .env from supplying the password.
    monkeypatch.setattr(config, "load_dotenv", lambda: False)

    result = runner.invoke(app, ["status"], env={"NEO4J_PASSWORD": None})

    assert result.exit_code == 1
    assert "NEO4J_PASSWORD" in flat(result.stderr)
    assert "Traceback" not in result.output
    assert result.stdout == ""


def test_status_when_neo4j_is_down_explains_how_to_start_it() -> None:
    result = runner.invoke(app, ["status"], env={"NEO4J_URI": UNREACHABLE_URI})

    assert result.exit_code == 1
    assert f"Neo4j is not reachable at {UNREACHABLE_URI}" in flat(result.stderr)
    assert "docker compose up -d" in flat(result.stderr)
    assert "Traceback" not in result.output
    assert result.stdout == ""


def test_debug_logs_tracepath_lines_but_not_driver_internals(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner.invoke(app, ["--debug", "status"], env={"NEO4J_URI": UNREACHABLE_URI})

    debug = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert any(r.name.startswith("tracepath.") and "connecting to" in r.message for r in debug)
    assert not [r for r in debug if r.name.startswith("neo4j")]


def test_without_debug_no_debug_lines_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    runner.invoke(app, ["status"], env={"NEO4J_URI": UNREACHABLE_URI})

    assert not [r for r in caplog.records if r.levelno == logging.DEBUG]


@pytest.mark.integration
def test_status_reports_the_running_neo4j(neo4j_settings: Neo4jSettings) -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert f"reachable at {neo4j_settings.uri}" in flat(result.stdout)
    assert "Neo4j 5." in result.stdout


@pytest.mark.integration
def test_status_with_a_wrong_password_points_at_env_file(neo4j_settings: Neo4jSettings) -> None:
    result = runner.invoke(app, ["status"], env={"NEO4J_PASSWORD": "definitely-wrong-password"})

    assert result.exit_code == 1
    assert "Neo4j rejected the credentials" in flat(result.stderr)
    assert "`.env`" in flat(result.stderr)
    assert "Traceback" not in result.output


# `review-queue`: the command that gives every held item somewhere durable to live.
#
# AC-11c promises a held link "sits in `artifacts/review-queue.json`, which is tracked
# in git". `test_review_queue.py` proves the rows are right; these prove the command a
# person actually types produces them, refuses clearly when it cannot, and never
# destroys a reviewer's work on the way.


#: The smallest committed unit, so each run here rebuilds one unit instead of eight.
#: Re-aligning every span of every run is the slow part and one unit exercises the
#: same path end to end.
UNIT = Path("0012") / "requirements"
UNIT_FILE = Path("specs/0012-model-client-router/index.md")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository root: one unit's artifacts and the file they came from.

    Built rather than pointed at the real root, because this command writes, and a
    test must never rewrite the committed queue it is checking against.
    """
    runs = tmp_path / RUNS_DIR / UNIT
    runs.parent.mkdir(parents=True)
    shutil.copytree(PROJECT_ROOT / RUNS_DIR / UNIT, runs)

    source = tmp_path / "corpus" / "jobhunt" / "docs" / UNIT_FILE
    source.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "corpus" / "jobhunt" / "docs" / UNIT_FILE, source)
    return tmp_path


def test_review_queue_writes_both_files_and_reports_what_it_queued(repo: Path) -> None:
    """The happy path, from the command line rather than from the functions."""
    result = runner.invoke(app, ["review-queue", "--root", str(repo)])

    assert result.exit_code == 0
    queue = json.loads((repo / REVIEW_QUEUE).read_text())
    assert queue, "the committed run holds held items, so the queue cannot be empty"
    assert (repo / REVIEW_LOG).exists(), "a queue with nowhere to record rulings is half a promise"
    assert f"{len(queue)} held items from 1 units" in flat(result.stdout)


def test_review_queue_needs_no_api_key_or_database(repo: Path) -> None:
    """Spec 0001 makes the artifacts the source of truth, so a rebuild must stand alone.

    A command that quietly needed a key would make the durability claim false for
    anyone who cloned the repository without one.
    """
    result = runner.invoke(
        app,
        ["review-queue", "--root", str(repo)],
        env={"ANTHROPIC_API_KEY": "", "NEO4J_PASSWORD": "", "NEO4J_URI": UNREACHABLE_URI},
    )

    assert result.exit_code == 0
    assert (repo / REVIEW_QUEUE).exists()


def test_review_queue_with_no_artifacts_exits_one_and_says_where_it_looked(
    tmp_path: Path,
) -> None:
    """A typed failure reaches the person as a message and an exit code, never a trace."""
    result = runner.invoke(app, ["review-queue", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "no run artifacts found" in flat(result.stderr)
    assert "Traceback" not in result.output


def test_review_queue_leaves_a_reviewer_s_existing_rulings_alone(repo: Path) -> None:
    """A run rules on nothing, so writing an empty log over real work would erase it."""
    log = repo / REVIEW_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    ruling = [{"canonical_id": "0012#requirements:1", "verdict": "accept"}]
    log.write_text(json.dumps(ruling))

    result = runner.invoke(app, ["review-queue", "--root", str(repo)])

    assert result.exit_code == 0
    assert json.loads(log.read_text()) == ruling


def test_review_queue_run_twice_leaves_the_same_bytes(repo: Path) -> None:
    """A file tracked in git that reorders itself on every run is not reviewable."""
    runner.invoke(app, ["review-queue", "--root", str(repo)])
    first = (repo / REVIEW_QUEUE).read_bytes()

    runner.invoke(app, ["review-queue", "--root", str(repo)])

    assert (repo / REVIEW_QUEUE).read_bytes() == first
