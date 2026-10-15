"""The model switch of spec 0007: per model rates, rows that name their own model, and
`extract --expect-model`.

Each test names the criterion it covers. No API call: the command tests run on the
fake client of `tests/test_extract_command.py`.
"""

import inspect
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from tests.test_extract_command import (
    BOUND,
    SNAPSHOT,
    Script,
    fake_api,
    first_call,
    flat,
    invoke,
    settled,
    targets,
)
from tests.test_review_queue import QUEUED_AT, rebuilt
from tracepath import cli
from tracepath.artifacts import RUNS_DIR
from tracepath.config import DEFAULT_MODEL, AnthropicSettings
from tracepath.extract.client import PROMPT_VERSION
from tracepath.extract.cost import (
    CACHED_PREFIX_TOKENS,
    RATES,
    EstimateUnavailable,
    Rates,
    UnitCount,
    estimate,
    estimate_lines,
    recorded_cost,
)
from tracepath.extract.metered import Plan, fresh_runs, run_metered
from tracepath.pipeline import review_rows

__all__ = ["fake_api"]

ROOT = Path(__file__).resolve().parents[1]

runner = CliRunner()


def test_ac_1_the_default_model_is_sonnet_5_5() -> None:
    """covers: AC-1."""
    assert DEFAULT_MODEL == "claude-sonnet-5-5"


def test_ac_3_the_prompt_version_is_unchanged() -> None:
    """covers: AC-3 (the version this spec found, so no prompt text was meant to differ)."""
    assert PROMPT_VERSION == "0003.1"


def test_ac_5f_the_rates_per_million_tokens() -> None:
    """covers: AC-5f."""
    assert {
        "claude-sonnet-5": Rates(input=2.00, output=10.00, cache_write=4.00, cache_read=0.20),
        "claude-sonnet-5-5": Rates(input=2.00, output=10.00, cache_write=4.00, cache_read=0.10),
    } == RATES


def test_ac_5c_the_estimate_prices_at_the_model_it_is_given() -> None:
    """covers: AC-5c (the cache read rate is the one place the two rows differ)."""
    counts = [UnitCount("0002:Requirements", "Requirements", 62_000, 3)]

    old = estimate(counts, "claude-sonnet-5")
    new = estimate(counts, "claude-sonnet-5-5")

    # Three calls, the first writing the cache and the other two reading it.
    saved = 2 * CACHED_PREFIX_TOKENS * (0.20 - 0.10) / 1e6
    assert old.central_usd is not None and new.central_usd is not None
    assert old.central_usd - new.central_usd == pytest.approx(saved)


def test_ac_5c_the_command_prices_at_the_settings_model(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-5c, AC-31e (an older model in the settings is priced at its own row)."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    code, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run")

    assert code == 0
    assert (
        "Rates assumed for claude-sonnet-5, standard interactive pricing, not Batch: "
        "input $2.00, output $10.00, 1 hour cache write $4.00, cache read $0.20"
    ) in flat(stdout)


def test_ac_31e_the_estimate_line_names_the_model_it_prices() -> None:
    """covers: AC-31e."""
    priced = estimate([UnitCount("0002:Requirements", "Requirements", 62_000, 3)], DEFAULT_MODEL)

    assert estimate_lines(priced, 20.0)[0].startswith(f"Rates assumed for {DEFAULT_MODEL},")


def test_ac_5d_recorded_spend_is_priced_at_the_model_given() -> None:
    """covers: AC-5d (the function)."""
    attempt = settled()

    old = recorded_cost(attempt, "claude-sonnet-5")
    new = recorded_cost(attempt, "claude-sonnet-5-5")

    assert old - new == pytest.approx(CACHED_PREFIX_TOKENS * (0.20 - 0.10) / 1e6)


def test_ac_5d_the_run_prices_each_attempt_at_its_artifacts_model(tmp_path: Path) -> None:
    """covers: AC-5d (through the metered run: the artifact's model prices its spend)."""
    settings = AnthropicSettings(
        api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort="medium"
    )
    script = Script([first_call(), settled(), settled()])

    outcome = run_metered(
        [Plan(target=t, runs=fresh_runs(3), bound=BOUND) for t in targets("0002:Requirements")],
        script,
        settings,
        tmp_path,
        "2e40bcf",
        "2026-10-11T00:00:00+00:00",
        100.0,
        lambda _: None,
    )

    for written, attempt in zip(outcome.written, script.attempts, strict=False):
        assert json.loads(written.path.read_text())["model"] == "claude-sonnet-5"
        assert written.recorded_usd == pytest.approx(recorded_cost(attempt, "claude-sonnet-5"))
        assert written.cost_usd == pytest.approx(recorded_cost(attempt, "claude-sonnet-5"))


def test_ac_5e_a_model_with_no_rate_row_refuses_the_estimate() -> None:
    """covers: AC-5e (the estimate)."""
    with pytest.raises(EstimateUnavailable, match="no rates are recorded for the model claude-x"):
        estimate([UnitCount("0002:Requirements", "Requirements", 62_000, 3)], "claude-x")


def test_ac_5e_a_model_with_no_rate_row_refuses_the_spend_figure() -> None:
    """covers: AC-5e (the spend figure)."""
    with pytest.raises(EstimateUnavailable, match="no rates are recorded for the model claude-x"):
        recorded_cost(settled(), "claude-x")


def test_ac_5e_the_command_refuses_a_model_with_no_rate_row_before_any_call(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-5e (through the command: exit 1, no extraction call)."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-x")

    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert "no rates are recorded for the model claude-x" in flat(stderr)
    assert fake_api.script.calls == []


def test_ac_29_extract_refuses_before_any_call_when_the_model_differs(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-29 (an old `ANTHROPIC_MODEL` left in the settings)."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    code, _, stderr = invoke(
        tmp_path, "0002:Requirements", "--ceiling", "20", "--expect-model", "claude-sonnet-5-5"
    )

    assert code == 1
    assert "--expect-model claude-sonnet-5-5, but the settings name claude-sonnet-5" in flat(stderr)
    assert fake_api.built == 0, "no client, so no call of any kind, count included"
    assert fake_api.script.calls == []


def test_ac_29_extract_runs_when_the_model_matches(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-29 (the matching case is not refused)."""
    code, stdout, _ = invoke(
        tmp_path,
        "0002:Requirements",
        "--ceiling",
        "20",
        "--dry-run",
        "--expect-model",
        DEFAULT_MODEL,
    )

    assert code == 0
    assert "Dry run: no extraction call made." in flat(stdout)


def test_ac_5_every_row_names_the_model_its_units_artifacts_name() -> None:
    """covers: AC-5 (two units on two models; the fallback names neither)."""
    run = rebuilt()
    first = run.results[0]
    moved = replace(
        first, artifacts=tuple(replace(a, model="claude-sonnet-5-5") for a in first.artifacts)
    )
    results = (moved, *run.results[1:])

    rows = review_rows(results, run.corpus.held, "fallback-model", QUEUED_AT)

    by_unit = {(r.unit.record_id, r.unit.section) for r in results}
    assert all((row["record"], row["section"]) in by_unit for row in rows)
    moved_key = (first.unit.record_id, first.unit.section)
    assert {row["model"] for row in rows if (row["record"], row["section"]) == moved_key} == {
        "claude-sonnet-5-5"
    }
    # The other units keep the model their own committed artifacts name, whichever it is.
    own = {(r.unit.record_id, r.unit.section): r.artifacts[0].model for r in results}
    assert all(
        row["model"] == own[(row["record"], row["section"])]
        for row in rows
        if (row["record"], row["section"]) != moved_key
    )
    assert "fallback-model" not in {row["model"] for row in rows}


def test_ac_5b_the_model_option_defaults_to_the_default_model() -> None:
    """covers: AC-5b (the default; the orphan row it names is in `test_review_queue.py`)."""
    option = inspect.signature(cli.review_queue).parameters["model"].default

    assert option.default == DEFAULT_MODEL


@pytest.mark.integration
def test_ac_4_load_prints_the_units_per_model(tmp_path: Path) -> None:
    """covers: AC-4 (read from each unit's artifacts, beside the prompt version line)."""
    for unit in ("0002", "0021"):
        shutil.copytree(ROOT / RUNS_DIR / unit, tmp_path / RUNS_DIR / unit)
    for path in (tmp_path / RUNS_DIR / "0021").glob("*/*.json"):
        payload = json.loads(path.read_text())
        payload["model"] = "claude-sonnet-5-5"
        path.write_text(json.dumps(payload))
    units_0002 = len({p.parent for p in (tmp_path / RUNS_DIR / "0002").glob("*/run-*.json")})
    units_0021 = len({p.parent for p in (tmp_path / RUNS_DIR / "0021").glob("*/run-*.json")})

    result = runner.invoke(cli.app, ["load", "--root", str(tmp_path), "--snapshot", str(SNAPSHOT)])

    assert result.exit_code == 0, result.stderr
    lines = result.stdout.splitlines()
    versions = next(i for i, line in enumerate(lines) if line.startswith("Units per prompt"))
    assert lines[versions + 1] == (
        f"Units per model: claude-sonnet-5: {units_0002}, claude-sonnet-5-5: {units_0021}."
    )
