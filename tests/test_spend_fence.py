"""No paid call outside `tracepath extract` (spec 0004's second amendment, 2026-10-06).

The allowlist of files that may reach the model (AC-72), the history of `0021 ##
Requirements` that predates the run policy (AC-73 to AC-73c), and the fixture that
keeps every test away from the real API (AC-74 to AC-74c).
"""

import os
import subprocess
from pathlib import Path

import dotenv
import pytest

from tests.conftest import FAKE_API_KEY, UNREACHABLE_API
from tracepath import config
from tracepath.config import RUNS_PER_UNIT, load_anthropic_settings
from tracepath.extract.address import resolve_address
from tracepath.extract.metered import ResumeRefused, resume_runs
from tracepath.rebuild import committed_units

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"

#: The text that marks a file able to reach the model (AC-72).
PAID_MARKERS = ("import anthropic", "from anthropic", "build_client", "extract_once")

#: The sixteen files that match today. The experiment scripts are frozen records.
ALLOWED = frozenset(
    {
        "src/tracepath/extract/client.py",
        "src/tracepath/extract/metered.py",
        "src/tracepath/cli.py",
        "src/tracepath/pipeline.py",
        "experiments/0001-ac14-type-stability/calibrate_effort.py",
        "experiments/0001-ac14-type-stability/run.py",
        "experiments/0002-effort-low-fidelity/calibrate_effort.py",
        "experiments/0003-feature-design-testscenario/run.py",
        "experiments/0004-label-round-trip/real_label_run.py",
        "experiments/0005-held-out-prompt-examples/baseline_0021.py",
        "experiments/0005-held-out-prompt-examples/measure_prefix.py",
        "experiments/0005-held-out-prompt-examples/run_units.py",
        "experiments/0006-accuracy-bar-recheck/measure_recheck.py",
        "experiments/0006-accuracy-bar-recheck/run_recheck.py",
        "experiments/0008-type-coverage-rerun/measure_coverage.py",
        "experiments/0008-type-coverage-rerun/run_coverage.py",
    }
)


def tracked_python_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [p for p in listed.stdout.splitlines() if not p.startswith("tests/")]


def test_ac_72_no_file_outside_the_allowlist_can_reach_the_model() -> None:
    """covers: AC-72. A new paid call goes through `tracepath extract` or `run_metered()`."""
    offending = sorted(
        path
        for path in tracked_python_files()
        if path not in ALLOWED
        and any(marker in (ROOT / path).read_text() for marker in PAID_MARKERS)
    )

    assert offending == [], (
        f"{offending} can reach the model outside `tracepath extract`; route the call "
        "through `run_metered()` instead (spec 0004 AC-72)"
    )


# 0021 Requirements: resumed in experiment 0008, before the run policy of 2026-10-06.


@pytest.fixture(scope="module")
def requirements_0021_runs() -> tuple[object, ...]:
    [result] = [
        r
        for r in committed_units(ROOT, SNAPSHOT)
        if (r.unit.record_id, r.unit.section) == ("0021", "Requirements")
    ]
    return result.artifacts


def test_ac_73_0021_requirements_loads_with_three_settled_runs(
    requirements_0021_runs: tuple[object, ...],
) -> None:
    """covers: AC-73 (a regression pin)."""
    assert len(requirements_0021_runs) == RUNS_PER_UNIT


def test_ac_73c_its_run_2_settled_at_attempt_3() -> None:
    """covers: AC-73c (a pin: run 2 was resumed after two schema failures)."""
    [result] = [
        r
        for r in committed_units(ROOT, SNAPSHOT)
        if (r.unit.record_id, r.unit.section) == ("0021", "Requirements")
    ]

    assert {a.run: a.attempt for a in result.artifacts}[2] == 3


def test_ac_73b_a_resume_reads_it_as_owing_nothing_not_as_blocked() -> None:
    """covers: AC-73b (a pin: settled wins, whatever model failures sit beside it)."""
    target = resolve_address(SNAPSHOT, "0021:Requirements")

    with pytest.raises(ResumeRefused, match="owes nothing"):
        resume_runs(ROOT, target, RUNS_PER_UNIT)


# The fixture that keeps every test away from the real API.


def test_ac_74b_every_test_runs_with_the_fake_key_and_an_unreachable_api() -> None:
    """covers: AC-74b."""
    assert (os.environ["ANTHROPIC_API_KEY"], os.environ["ANTHROPIC_BASE_URL"]) == (
        FAKE_API_KEY,
        UNREACHABLE_API,
    )


def test_ac_74c_a_dotenv_holding_another_key_cannot_replace_the_fake_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-74c (`load_dotenv()` never replaces a variable already set)."""
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=sk-ant-not-the-test-key\n")
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: dotenv.load_dotenv(env))

    assert load_anthropic_settings().api_key == FAKE_API_KEY


def test_ac_74_dotenv_still_supplies_the_neo4j_settings_under_the_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-74 (`load_dotenv()` keeps working, so integration tests reach Neo4j)."""
    env = tmp_path / ".env"
    env.write_text("NEO4J_PASSWORD=from-the-dotenv-file\n")
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: dotenv.load_dotenv(env))

    assert config.load_neo4j_settings().password == "from-the-dotenv-file"
