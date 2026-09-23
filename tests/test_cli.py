import logging

import pytest
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tracepath import __version__, config
from tracepath.cli import app
from tracepath.config import Neo4jSettings

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
