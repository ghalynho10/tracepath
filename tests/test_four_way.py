"""The four way comparison of spec 0008 (AC-8 to AC-8f).

The states, the noise split and the checks are tested on crafted findings and tables,
no database. The script itself runs once against real Neo4j over a copy of two units'
run files under `tmp_path`, so the repository's own `artifacts/` is never rewritten.
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver

from tests.test_code_pass_commands import ROOT, SNAPSHOT, runs_root
from tests.test_eval_runner import held_slice
from tests.test_experiment_scripts import load_script
from tracepath.artifacts import GRAPH_BUILD
from tracepath.config import Neo4jSettings
from tracepath.four_way import (
    BASELINE,
    BOTH,
    CONFIGS,
    NARROW_HOLD,
    WITH_HELD,
    Cell,
    Noise,
    State,
    StepRow,
    cell_of,
    newly_accepted,
    newly_held_only,
    noise_of,
    regressed,
    summed,
    table_lines,
    worse_under_both,
)
from tracepath.graph import connect
from tracepath.graph.schema import clear
from tracepath.report import EVAL_FILE, SIDECAR_FILE, ExpectedItem, Finding, Question, Report, Start
from tracepath.traverse.walk import walk

SCRIPT = ROOT / "experiments" / "0014-review-volume-and-routing-policy" / "compare_four_ways.py"
ACCEPTED, HELD, NOT = State.ACCEPTED, State.HELD_ONLY, State.NOT_REACHED


def row(*states: State, question: int = 1, label: str = "step") -> StepRow:
    """One step with a state per configuration, in `CONFIGS` order."""
    return StepRow(question, False, label, "specs/x/index.md:1", tuple(Cell(s) for s in states))


# AC-8: the four configurations.


def test_ac_8_four_configurations_with_the_code_pass_never_among_their_flags() -> None:
    """covers: AC-8."""
    assert [c.flags for c in CONFIGS] == [
        (),
        ("--with-held",),
        ("--narrow-hold",),
        ("--with-held", "--narrow-hold"),
    ]
    assert not any("--code-pass" in c.flags for c in CONFIGS)


# AC-8c: one of three states per step.


ITEM = ExpectedItem("spec 9003 AC-1", "specs/9003-fixture-held/index.md", 12, "AC-1")


def test_ac_8c_a_finding_reads_as_one_of_three_states() -> None:
    """covers: AC-8c (clean walk reached, held walk only, neither)."""
    chain = walk(held_slice(with_held=True), "9003/AC-1")
    step = chain.steps[0]

    assert cell_of(Finding(ITEM, "9003", step, None)).state is ACCEPTED
    assert cell_of(Finding(ITEM, "9003", None, None, held_by=step)).state is HELD
    assert cell_of(Finding(ITEM, "9003", None, None)).state is NOT
    assert cell_of(Finding(ITEM, "9003", step, None, released_parts=("9003/AC-1",))).released


# AC-8d: the noise count and its split.


def test_ac_8d_without_held_items_the_count_is_not_split() -> None:
    """covers: AC-8d (no split where --with-held is not in effect)."""
    question = Question(1, "q", "9003/AC-1", "start", (ITEM,))
    report = Report(question, (), 4, (), (), Start("9003/AC-1"), True)

    assert noise_of(report, None, with_held=False) == Noise(4)


def test_ac_8d_with_held_items_the_count_splits_by_held_step() -> None:
    """covers: AC-8d (a step is held when its node is, or the link that reached it is)."""
    chain = walk(held_slice(with_held=True), "9003/AC-1")
    item = ExpectedItem("spec 9003 AC-1", chain.steps[0].node.file or "", 12, "AC-1")
    question = Question(1, "q", "9003/AC-1", "start", (item,))
    unmatched = len(chain.steps) - 1
    report = Report(question, (), unmatched, (), (), Start("9003/AC-1"), True)

    noise = noise_of(report, chain, with_held=True)

    held = [s.node.canonical_id for s in chain.steps[1:] if s.node.held or (s.via and s.via.held)]
    # AC-6 is reached first by its held CORRECTED_BY shortcut, before the clean path.
    assert held == [
        "9003/AC-4",
        "9003/AC-6",
        "9003/AC-2",
        "9003/AC-3",
        "unresolved:9003:feature-77",
    ]
    assert noise == Noise(7, held=5, accepted=2), "9003/AC-5 and 9004/AC-1 are accepted"


def test_ac_8d_summed_noise_keeps_the_split_only_when_every_part_has_it() -> None:
    """covers: AC-8d (all five questions summed)."""
    assert summed([Noise(2, 1, 1), Noise(3, 0, 3)]) == Noise(5, 1, 4)
    assert summed([Noise(2), Noise(3)]) == Noise(5)


# AC-8f: the both flags check.


def test_ac_8f_a_step_worse_with_both_flags_than_either_alone_is_named() -> None:
    """covers: AC-8f."""
    fine = row(NOT, HELD, ACCEPTED, ACCEPTED)
    worse = row(NOT, HELD, ACCEPTED, HELD, label="worse")

    assert worse_under_both([fine, worse]) == (worse,)


def test_ac_8f_a_failed_check_stops_before_any_adoption_fact() -> None:
    """covers: AC-8f (the table says so and reads no AC-9 or AC-11 fact)."""
    rows = [row(NOT, HELD, ACCEPTED, NOT)]
    noise = {c.name: Noise(0) for c in CONFIGS}

    lines = table_lines(rows, noise, "abc123", "e.json")

    assert any(line.startswith("STOPPED:") for line in lines)
    assert not any(line.startswith(("AC-9", "AC-11")) for line in lines)


# AC-8b and the facts AC-9 and AC-11 read off the table.


def test_ac_8b_the_table_names_the_runs_commit() -> None:
    """covers: AC-8b."""
    lines = table_lines(
        [row(NOT, NOT, NOT, NOT)], {c.name: Noise(0) for c in CONFIGS}, "abc123", "e.json"
    )

    assert lines[0].startswith("Run against `artifacts/runs/` at abc123;")


def test_the_facts_ac_9_reads() -> None:
    """covers: AC-9 (a) newly accepted, (b) a regression, read from a synthetic table."""
    newly = row(NOT, NOT, ACCEPTED, ACCEPTED, label="newly")
    lost = row(ACCEPTED, ACCEPTED, HELD, ACCEPTED, label="lost")
    same = row(ACCEPTED, ACCEPTED, ACCEPTED, ACCEPTED, label="same")

    assert newly_accepted([newly, lost, same]) == (newly,)
    assert regressed([newly, lost, same]) == (lost,)
    assert newly_accepted([same]) == ()


def test_the_fact_ac_11_reads() -> None:
    """covers: AC-11 (not reached at baseline, held only under --with-held)."""
    moved = row(NOT, HELD, NOT, HELD, label="moved")
    still = row(NOT, NOT, NOT, NOT, label="still")

    assert newly_held_only([moved, still]) == (moved,)


def test_a_row_reads_each_configurations_state_by_name() -> None:
    """covers: AC-8c (the cells are in `CONFIGS` order)."""
    one = row(ACCEPTED, HELD, NOT, ACCEPTED)

    assert [one.state(c) for c in (BASELINE, WITH_HELD, NARROW_HOLD, BOTH)] == [
        ACCEPTED,
        HELD,
        NOT,
        ACCEPTED,
    ]


# The script, against real Neo4j: AC-8, AC-8b, AC-8e.


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        yield opened
        clear(opened, neo4j_settings.database)


@pytest.mark.integration
def test_the_script_runs_four_ways_and_restores_a_plain_load(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    """covers: AC-8, AC-8b, AC-8c, AC-8d, AC-8e (over two units' committed runs)."""
    root = runs_root(tmp_path / "root", "0002", "0007")
    (root / EVAL_FILE).parent.mkdir(parents=True)
    shutil.copy(ROOT / EVAL_FILE, root / EVAL_FILE)
    shutil.copy(ROOT / SIDECAR_FILE, root / SIDECAR_FILE)
    script = load_script(SCRIPT, "compare_four_ways")
    out = tmp_path / "data"

    code = script.compare(root, SNAPSHOT, "commit-under-test", out, say=lambda _: None)

    table = (out / "four-way.md").read_text()
    assert code == 0
    assert "Run against `artifacts/runs/` at commit-under-test;" in table
    assert "| Q | expected step | baseline | --with-held | --narrow-hold | both |" in table
    for slug in ("baseline", "with-held", "narrow-hold", "both"):
        assert (out / "four-way" / f"{slug}-load.txt").exists()
        assert (out / "four-way" / f"{slug}-eval.txt").exists()
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    assert not {"narrow_hold", "held_view", "code_pass"} & set(manifest)
    held, _, _ = driver.execute_query(
        "MATCH (n) WHERE n.held = true OR n.accepted_by = 'narrow_hold' RETURN count(n) AS n",
        database_=neo4j_settings.database,
    )
    assert held[0]["n"] == 0, "the plain load after leaves no held or released item"
