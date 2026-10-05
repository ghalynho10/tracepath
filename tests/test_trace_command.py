"""The `trace START` command against a real Neo4j (spec 0004 AC-20, AC-42, AC-44).

The graph holds the hand built fixture, not an eval chain, so the expected output is
the same hand written file the walk's unit test reads.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tests.test_walk_graph import write_fixture
from tests.trace_fixture import START
from tracepath.cli import app
from tracepath.config import Neo4jSettings
from tracepath.graph import connect
from tracepath.graph.schema import clear, create_constraints

pytestmark = pytest.mark.integration

EXPECTED = Path(__file__).parent / "fixtures" / "trace-fixture-expected.txt"

runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture
def fixture_graph(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        clear(opened, neo4j_settings.database)
        create_constraints(opened, neo4j_settings.database)
        write_fixture(opened, neo4j_settings.database)
        yield opened
        clear(opened, neo4j_settings.database)


def test_trace_prints_the_chain_unwrapped_on_stdout(fixture_graph: Driver) -> None:
    result = runner.invoke(app, ["trace", START])

    assert result.exit_code == 0, result.stderr
    assert result.stdout == EXPECTED.read_text()
    assert result.stderr == ""


def test_trace_twice_against_the_same_graph_prints_the_same_output(fixture_graph: Driver) -> None:
    first = runner.invoke(app, ["trace", START]).stdout
    second = runner.invoke(app, ["trace", START]).stdout

    assert first == second


def test_trace_from_a_start_the_graph_does_not_hold_names_it_and_exits_1(
    fixture_graph: Driver,
) -> None:
    result = runner.invoke(app, ["trace", "9001/AC-99"])

    assert result.exit_code == 1
    assert "9001/AC-99 is not in the graph" in flat(result.stderr)
    assert "held for review" in flat(result.stderr)
    assert "Traceback" not in result.output
    assert result.stdout == ""


def test_trace_when_neo4j_is_down_says_how_to_start_it() -> None:
    result = runner.invoke(app, ["trace", START], env={"NEO4J_URI": UNREACHABLE_URI})

    assert result.exit_code == 1
    assert "docker compose up -d" in flat(result.stderr)
    assert "Traceback" not in result.output
