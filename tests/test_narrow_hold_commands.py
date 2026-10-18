"""The narrow hold rule through the commands (spec 0008 AC-3 to AC-5e).

The queue and refusal tests need no database. The load tests run against a real Neo4j
over a copy of committed run files under `tmp_path`, so the repository's own
`artifacts/` is never rewritten. Only `eval/linked-records-research.json` is copied
into a temporary root; the held out file is never opened.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests.test_code_pass_commands import (
    COMMIT,
    ROOT,
    SNAPSHOT,
    eval_root,
    flat,
    invoke_unreachable,
    runs_root,
)
from tracepath.artifacts import (
    GRAPH_BUILD,
    REVIEW_QUEUE,
    REVIEW_QUEUE_CODE_PASS,
    review_queue_file,
)
from tracepath.cli import NARROW_HOLD_DEFAULT, _committed, app
from tracepath.config import Neo4jSettings
from tracepath.graph import connect
from tracepath.graph.schema import clear
from tracepath.pipeline import resolve_accepted
from tracepath.rebuild import (
    apply_code_pass,
    apply_narrow_hold,
    committed_units,
    narrow_hold_tally,
    narrow_link_keys,
    records_for_units,
)

runner = CliRunner()

#: The queue files a run without the rule, and one with the code pass, write, now the
#: narrow hold rule is the default (spec 0008 AC-9b).
WITHOUT_NARROW = review_queue_file(
    code_pass=False, narrow_hold=False, narrow_default=NARROW_HOLD_DEFAULT
)
CODE_PASS = review_queue_file(code_pass=True, narrow_hold=True, narrow_default=NARROW_HOLD_DEFAULT)


# AC-5b, AC-5e, AC-9b: the queues.


@dataclass(frozen=True)
class Queues:
    root: Path
    default: bytes
    after: bytes
    codes: tuple[int, ...]


@pytest.fixture(scope="module")
def queues(tmp_path_factory: pytest.TempPathFactory) -> Queues:
    """`review-queue`, then `--no-narrow-hold`, then `--code-pass`, over every run file."""
    root = runs_root(tmp_path_factory.mktemp("queues"))
    args = ["review-queue", "--root", str(root), "--snapshot", str(SNAPSHOT)]
    first = runner.invoke(app, args)
    default = (root / REVIEW_QUEUE).read_bytes()
    second = runner.invoke(app, [*args, "--no-narrow-hold"])
    third = runner.invoke(app, [*args, "--code-pass"])
    after = (root / REVIEW_QUEUE).read_bytes()
    return Queues(root, default, after, (first.exit_code, second.exit_code, third.exit_code))


@pytest.mark.slow
def test_ac_9b_the_default_queue_is_the_narrow_hold_queue(queues: Queues) -> None:
    """covers: AC-9b (the default flipped: the default file holds fewer rows than without it)."""
    assert queues.codes == (0, 0, 0)
    assert NARROW_HOLD_DEFAULT is True
    without = json.loads((queues.root / WITHOUT_NARROW).read_text())
    assert 0 < len(json.loads(queues.default)) < len(without)
    assert queues.default == (ROOT / REVIEW_QUEUE).read_bytes(), "the committed queue"


@pytest.mark.slow
def test_ac_5e_a_queue_off_the_default_leaves_the_default_queue_alone(queues: Queues) -> None:
    """covers: AC-5e (each other routing writes its own file, never over the default one)."""
    assert queues.after == queues.default
    assert WITHOUT_NARROW.name == "review-queue-without-narrow-hold.json"


@pytest.mark.slow
def test_ac_5e_the_code_pass_writes_its_own_file_with_the_rule_on(queues: Queues) -> None:
    """covers: AC-5e, spec 0007 AC-8 (`--code-pass` still writes review-queue-code-pass.json)."""
    assert CODE_PASS == REVIEW_QUEUE_CODE_PASS
    both = json.loads((queues.root / CODE_PASS).read_text())
    assert len(both) <= len(json.loads(queues.default))


# AC-5b, AC-5d: the refusal before any connection.


def narrow_root(root: Path, narrow_hold: bool | None) -> Path:
    """A root holding the eval file and a manifest; `None` writes no `narrow_hold` key."""
    eval_root(root, None)
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    manifest.pop("narrow_hold", None)
    if narrow_hold is not None:
        manifest["narrow_hold"] = narrow_hold
    (root / GRAPH_BUILD).write_text(json.dumps(manifest))
    return root


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_5d_the_rule_on_against_a_graph_loaded_without_it_is_refused(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-5b (eval and trace --eval take the option), AC-5c (absent means false), AC-5d."""
    root = narrow_root(tmp_path, None)

    code, stderr = invoke_unreachable(*command, "--narrow-hold", "--root", str(root))

    assert code == 1
    assert "the narrow hold rule is on for this command, but artifacts/graph-build.json" in stderr
    assert "localhost:1" not in stderr, "refused before any connection was tried"


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_9b_the_rule_is_on_by_default_so_a_graph_without_it_is_refused(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-9b (no flag given means the rule is on), AC-5d."""
    root = narrow_root(tmp_path, None)

    code, stderr = invoke_unreachable(*command, "--root", str(root))

    assert code == 1
    assert "the narrow hold rule is on for this command" in stderr
    assert "localhost:1" not in stderr


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_5d_the_rule_off_against_a_graph_loaded_with_it_is_refused(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-5d (the other direction)."""
    root = narrow_root(tmp_path, True)

    code, stderr = invoke_unreachable(*command, "--no-narrow-hold", "--root", str(root))

    assert code == 1
    assert "artifacts/graph-build.json says the graph was loaded with the narrow hold rule" in (
        stderr
    )
    assert "localhost:1" not in stderr


@pytest.mark.parametrize("command", [("trace", "--eval", "3"), ("eval",)])
def test_ac_5d_a_matching_setting_goes_on_to_connect(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """covers: AC-5d (no refusal when the settings match; the unreachable graph says so)."""
    root = narrow_root(tmp_path, True)

    code, stderr = invoke_unreachable(*command, "--narrow-hold", "--root", str(root))

    assert code == 1
    assert "graph-build.json" not in stderr


def test_trace_with_the_rule_needs_an_eval_question() -> None:
    """covers: AC-5b (`trace` takes `--narrow-hold` only with `--eval`, as with --code-pass)."""
    code, stderr = invoke_unreachable("trace", "0002/AC-1", "--narrow-hold")

    assert code == 1
    assert "--narrow-hold changes the routing scored, so it needs --eval N." in stderr


def test_the_scoring_routes_with_the_rule() -> None:
    """covers: AC-5b (what `eval` and `trace --eval` score is the narrow hold routing)."""
    on = _committed(ROOT, SNAPSHOT, COMMIT, False, True)

    assert any(result.routed.narrow_released for result in on.results)
    assert on.results == apply_narrow_hold(committed_units(ROOT, SNAPSHOT))


# AC-3, AC-3b, AC-4, AC-5, AC-5c: the load.


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        yield opened
        clear(opened, neo4j_settings.database)


def run_load(root: Path, *extra: str) -> tuple[int, str, str]:
    """A load with the held view off (on by default since spec 0008 AC-11b): stamps only."""
    result = runner.invoke(
        app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT), "--no-with-held", *extra]
    )
    return result.exit_code, result.stdout, result.stderr


def entity_stamps(driver: Driver, database: str) -> dict[str, list[str]]:
    records, _, _ = driver.execute_query(
        "MATCH (e:Entity) RETURN e.accepted_by AS by, collect(e.canonical_id) AS ids",
        database_=database,
    )
    return {record["by"]: sorted(record["ids"]) for record in records}


def link_stamps(driver: Driver, database: str) -> dict[str | None, int]:
    records, _, _ = driver.execute_query(
        "MATCH ()-[r]->() WHERE type(r) <> 'PART_OF' RETURN r.accepted_by AS by, count(r) AS n",
        database_=database,
    )
    return {record["by"]: record["n"] for record in records}


UNITS = ("0002", "0007")


@pytest.mark.integration
def test_load_with_and_without_the_rule(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-9b, AC-3, AC-3b, AC-5, AC-5c, then spec 0002 AC-11 as amended 2026-10-18.

    The second load is the amended criterion's opt out: `--no-narrow-hold` holds every
    flag only item again, so no stamp and no manifest key is left.
    """
    root = runs_root(tmp_path, *UNITS)
    results = committed_units(root, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, COMMIT)
    before = resolve_accepted(results, records)
    narrowed = apply_narrow_hold(results)
    after = resolve_accepted(narrowed, records)
    tally = narrow_hold_tally(before, narrowed, after)
    released = sorted(i for r in narrowed for i in r.routed.narrow_entities)
    keys = narrow_link_keys(before, after)
    assert released and keys, "these two records hold flag only items the rule releases"

    code, stdout, stderr = run_load(root)  # the default: the rule is on (AC-9b)

    assert code == 0, stderr
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    assert manifest["narrow_hold"] is True
    assert manifest["narrow_hold_released"] == tally.counts()
    entities = entity_stamps(driver, neo4j_settings.database)
    assert entities["narrow_hold"] == released
    assert set(entities) == {"auto", "narrow_hold"}
    assert link_stamps(driver, neo4j_settings.database)["narrow_hold"] == len(keys)
    reasons = ", ".join(f"{name} {n}" for name, n in tally.by_reason)
    assert (
        f"Narrow hold (spec 0008): {tally.entities} entities and {tally.links} links released"
    ) in flat(stdout)
    assert f"{reasons} ({tally.held_for_both} held for both)" in flat(stdout)
    flags = ", ".join(f"{flag} {n}" for flag, n in tally.by_flag)
    by_flag = (
        "known_trap_flag releases by flag, an item counted under each flag any of its runs raised"
    )
    assert f"{by_flag}: {flags}." in flat(stdout)

    code, stdout, stderr = run_load(root, "--no-narrow-hold")

    assert code == 0, stderr
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    assert "narrow_hold" not in manifest
    assert "narrow_hold_released" not in manifest
    assert "Narrow hold" not in stdout
    assert set(entity_stamps(driver, neo4j_settings.database)) == {"auto"}
    assert set(link_stamps(driver, neo4j_settings.database)) == {None}


@pytest.mark.integration
def test_load_with_both_rules_stamps_each_release_once(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-4 (both given: code_pass wins), AC-6 (every release of either alone kept)."""
    root = runs_root(tmp_path, *UNITS)
    results = committed_units(root, SNAPSHOT)
    code_pass = sorted(i for r in apply_code_pass(results) for i in r.released)
    narrow_alone = {i for r in apply_narrow_hold(results) for i in r.routed.narrow_entities}
    assert code_pass, "these two records hold criteria the code pass releases"

    code, _, stderr = run_load(root, "--narrow-hold", "--code-pass")

    assert code == 0, stderr
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    assert manifest["narrow_hold"] is True
    assert manifest["code_pass"] is True
    stamped = entity_stamps(driver, neo4j_settings.database)
    assert stamped["code_pass"] == code_pass
    assert set(stamped["narrow_hold"]) == narrow_alone - set(code_pass)
    assert set(stamped) == {"auto", "code_pass", "narrow_hold"}


@pytest.mark.integration
def test_a_load_given_no_flag_applies_both_defaults(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-9b and AC-11b (the narrow hold rule and the held view are both on)."""
    root = runs_root(tmp_path, *UNITS)

    result = runner.invoke(app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT)])

    assert result.exit_code == 0, result.stderr
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    assert manifest["narrow_hold"] is True
    assert manifest["held_view"]["entities"] > 0
    assert "narrow_hold" in entity_stamps(driver, neo4j_settings.database)
    held, _, _ = driver.execute_query(
        "MATCH (n) WHERE n.held = true RETURN count(n) AS n", database_=neo4j_settings.database
    )
    assert held[0]["n"] > 0
    assert "Held item view (spec 0005)" in result.stdout
