"""The `ask` command (spec 0009), with a hand built graph and no paid call.

The graph read is swapped for `tests/ask_fixture.py`'s slice, so these run without
Neo4j. The integration tests at the end read the real graph through `_ask_graph()`.
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests import ask_fixture as fx
from tests import test_held_walk_graph as held_graph
from tests import test_walk_graph as trace_graph
from tests.test_ask_metered import REPLY, answered, failed
from tracepath import cli
from tracepath.ask.record import ASKS_DIR
from tracepath.ask.retrieve import Pack
from tracepath.config import DEFAULT_MODEL, Neo4jSettings, SettingsInvalid
from tracepath.extract.cost import ask_bound
from tracepath.extract.metered import AskAttempt, CountUnreadable
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


#: What the fake token count endpoint counts for any ask request.
COUNTED = 6_000
BOUND = ask_bound(COUNTED, DEFAULT_MODEL)


@dataclass
class FakeApi:
    """A fake client for the free count, and a scripted ask call; nothing leaves the process."""

    replies: list[AskAttempt] = field(default_factory=lambda: [answered()])
    counts: list[dict[str, object]] = field(default_factory=list)
    packs: list[Pack] = field(default_factory=list)
    built: int = 0
    count_error: Exception | None = None

    def count_tokens(self, **request: object) -> SimpleNamespace:
        self.counts.append(request)
        if self.count_error is not None:
            raise self.count_error
        return SimpleNamespace(input_tokens=COUNTED)


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> FakeApi:
    """The model and effort pinned, `build_client` and the ask call swapped for fakes."""
    monkeypatch.setenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    monkeypatch.setenv("ANTHROPIC_EFFORT", "medium")
    state = FakeApi()

    def build(_: object) -> object:
        state.built += 1
        return SimpleNamespace(messages=state)

    def through(client: object, settings: object) -> Callable[[Pack], AskAttempt]:
        assert client is not None

        def call(pack: Pack) -> AskAttempt:
            state.packs.append(pack)
            return state.replies[len(state.packs) - 1]

        return call

    monkeypatch.setattr(cli, "build_client", build)
    monkeypatch.setattr(cli, "ask_calls_through", through)
    return state


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api: FakeApi) -> Iterator[Path]:
    """A root with a build manifest, and the graph read swapped for the fixture slice."""
    write_manifest(tmp_path)
    monkeypatch.setattr(cli, "_ask_graph", fx.graph)
    yield tmp_path


def records(root: Path) -> list[Path]:
    directory = root / ASKS_DIR
    return sorted(directory.iterdir()) if directory.is_dir() else []


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


def test_ac_4_a_dry_run_prints_words_items_count_and_bound_and_makes_no_call(
    repo: Path, api: FakeApi
) -> None:
    """covers: AC-4."""
    code, out, err = ask(repo, QUESTION, "--ceiling", "1", "--dry-run")

    assert code == 0, err
    assert "Search words: landing, rule, read, profile, row" in out
    assert f"  9101/AC-1  AcceptanceCriterion  accepted  {fx.FILE}:10  hit" in out
    assert f"Input: 6,000 tokens counted. Bound: ${BOUND:.4f}" in out
    assert out.rstrip().endswith("Dry run: no call made, no record written.")
    assert len(api.counts) == 1
    assert api.packs == []
    assert records(repo) == []


def test_ac_4_a_dry_run_says_when_the_bound_is_above_the_ceiling(repo: Path) -> None:
    """covers: AC-4, AC-22 (a dry run reports the stop a real run would make)."""
    code, out, _ = ask(repo, QUESTION, "--ceiling", "0.01", "--dry-run")

    assert code == 0
    assert "a real run would stop before the call" in out


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
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings, api: FakeApi
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


# Build plan step 3: the guarded call, the cost line and the record, with a scripted call.


def test_ac_1_ask_prints_the_items_then_the_answer_then_one_cost_line(
    repo: Path, api: FakeApi
) -> None:
    """covers: AC-1, AC-26 (one client, from `build_client()`, for the count and the call)."""
    code, out, err = ask(repo, QUESTION, "--ceiling", "1")
    lines = out.splitlines()

    assert code == 0, err
    items = lines.index("  9101/AC-1  AcceptanceCriterion  accepted  " + fx.FILE + ":10  hit")
    answer = lines.index("Answer (verdict: answered):")
    cost = next(n for n, line in enumerate(lines) if line.startswith("Cost: "))
    assert items < answer < cost
    assert lines[answer + 1] == "  1. It is amended. [9101/AC-1] [9101/AC-2 held] link"
    assert lines[answer + 2].endswith("CITATION REJECTED: 0001/AC-1 read from text")
    assert sum(line.startswith("Cost: ") for line in lines) == 1
    assert lines[-1].startswith("Record: artifacts/asks/")
    assert api.built == 1
    assert len(api.packs) == 1


def test_ac_27_ask_writes_one_record_holding_the_raw_reply(repo: Path) -> None:
    """covers: AC-27, AC-28 (a typed question's name ends in its slug)."""
    ask(repo, QUESTION, "--ceiling", "1")

    (path,) = records(repo)
    assert path.name.endswith("-why-does-the-landing-rule.json")
    saved = json.loads(path.read_text())
    assert saved["raw_response"] == REPLY
    assert saved["corpus_commit"] == "2e40bcf"
    assert saved["counted_input_tokens"] == COUNTED


def test_ac_22_a_ceiling_below_the_bound_stops_before_the_call_with_exit_1(
    repo: Path, api: FakeApi
) -> None:
    """covers: AC-22."""
    code, _, err = ask(repo, QUESTION, "--ceiling", "0.01")

    assert code == 1
    assert "stopping here before the call: ceiling" in err
    assert api.packs == []
    assert records(repo) == []


def test_ac_24_a_failed_call_is_saved_at_its_bound_and_exits_1(repo: Path, api: FakeApi) -> None:
    """covers: AC-24, AC-25."""
    api.replies = [failed(), answered()]

    code, out, err = ask(repo, QUESTION, "--ceiling", "1")

    assert code == 1
    assert "Answer: none, the call failed (overloaded)." in out
    assert f"${BOUND:.4f} by the guard's rule" in out
    assert "not retried" in flat(err)
    assert len(api.packs) == 1
    (path,) = records(repo)
    assert json.loads(path.read_text())["settled"] is False


def test_ac_27c_a_record_that_cannot_be_written_still_prints_the_answer_and_exits_1(
    repo: Path,
) -> None:
    """covers: AC-27c."""
    (repo / ASKS_DIR).write_text("in the way")

    code, out, err = ask(repo, QUESTION, "--ceiling", "1")

    assert code == 1
    assert "Answer (verdict: answered):" in out
    assert "Cost: 1 call, 6,000 in, 900 out" in out
    assert "Record: lost." in out
    assert "could not be written" in flat(err)


def test_ac_6_a_record_already_at_the_path_exits_1_before_the_call(
    repo: Path, api: FakeApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-6 (`ArtifactCollisionError`), AC-27b, with the clock held still."""
    fixed = datetime(2026, 10, 20, 9, 12, 31, tzinfo=UTC)
    monkeypatch.setattr(cli, "datetime", SimpleNamespace(now=lambda tz: fixed))
    ask(repo, QUESTION, "--ceiling", "1")
    api.replies.append(answered())

    code, out, err = ask(repo, QUESTION, "--ceiling", "1")

    assert code == 1
    assert "already exists" in err
    assert len(api.packs) == 1
    assert "Traceback" not in out + err


def test_ac_23_an_unpriced_model_exits_1_before_the_count(
    repo: Path, api: FakeApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-23, AC-6 (`EstimateUnavailable`)."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-unpriced-1")

    code, _, err = ask(repo, QUESTION, "--ceiling", "1")

    assert code == 1
    assert "no rates are recorded for the model claude-unpriced-1" in flat(err)
    assert api.counts == []


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=httpx2.Request("POST", "http://localhost:1")),
        CountUnreadable("its answer could not be read"),
    ],
)
def test_ac_6_a_failed_token_count_exits_1_with_no_traceback(
    repo: Path, api: FakeApi, error: Exception
) -> None:
    """covers: AC-6 (an API error from the token count, `CountUnreadable`)."""
    api.count_error = error

    code, out, err = ask(repo, QUESTION, "--ceiling", "1")

    assert code == 1
    assert "the token count endpoint failed, so nothing is priced" in flat(err)
    assert api.packs == []
    assert "Traceback" not in out + err


def test_ac_6_no_api_key_exits_1_before_the_graph_is_read(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-6 (`SettingsInvalid` for the Anthropic key)."""
    monkeypatch.setattr(cli, "_ask_graph", no_graph_read)
    monkeypatch.setattr(cli, "load_anthropic_settings", _no_key)

    code, _, err = ask(repo, QUESTION, "--ceiling", "1")

    assert code == 1
    assert "ANTHROPIC_API_KEY" in err


def _no_key() -> object:
    raise SettingsInvalid("ANTHROPIC_API_KEY is not set. Add it to `.env`.")
