"""The experiment scripts, driven with the model call replaced, so no API key is used.

These are the shells that actually call the pipeline, and two defects lived in them
rather than in `src/`:

* `calibrate_effort.py` called `build_artifact()` without the `input_tokens` and
  `output_tokens` this branch made required, so the script raised `TypeError` on its
  first run. Nothing caught it because mypy is configured over `src` and `tests` only.
* Neither script caught the failure its own call can raise. `run_unit()` raises
  `UnitFailed` carrying every artifact built so far, and `run_with_retry()` raises
  `ExtractionFailed` carrying every attempt, precisely so the shell can still write
  what the calls cost. A shell that lets the exception past writes nothing, which is
  the unrecoverable cost spec 0001's artifact storage row exists to close.

Scope: the two **live** scripts only, `0002-effort-low-fidelity/calibrate_effort.py`
and `0003-feature-design-testscenario/run.py`. Experiment 0001 is frozen, so its
`run.py` keeps the same uncaught `UnitFailed` and is deliberately never driven here;
its README records the defect and points at the fix. It is still imported, because
0002's script takes `find()` from it, but nothing in this file runs it.

Nothing here reaches the network: the model call is replaced in every test. Each one
patches the script's own output directory, because these scripts write real artifacts
and a test must never touch the committed evidence under `experiments/*/data/` or
`artifacts/`.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tracepath.artifacts import RunArtifact, build_artifact
from tracepath.config import AnthropicSettings
from tracepath.extract.client import Attempt, ExtractionFailed, RunOutcome
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit
from tracepath.pipeline import UnitFailed

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def load_script(path: Path, name: str) -> ModuleType:
    """Import one experiment script under its own module name.

    Given its own name because two experiments both hold a `run.py`, and importing
    either as plain `run` would shadow the other.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def an_output() -> ExtractionOutput:
    """A real validated extraction, reused so the scripts have something to identify."""
    return ExtractionOutput.model_validate(json.loads((FIXTURES / "run1.json").read_text()))


def settings_for(effort: str = "medium") -> AnthropicSettings:
    """Settings with a fake key: every test here replaces the call before it is made."""
    return AnthropicSettings(
        api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort=effort
    )


def an_artifact(unit: Unit, run: int, attempt: int) -> RunArtifact:
    """One failed attempt's artifact, the kind a failure carries out with it."""
    return build_artifact(
        unit=unit,
        section_slug="feature-design",
        run=run,
        attempt=attempt,
        output=None,
        model="claude-sonnet-5",
        prompt_version="0002.2",
        commit="2e40bcf",
        extracted_at="2026-09-23T00:00:00+00:00",
        max_output_tokens=64000,
        effort="medium",
        input_tokens=4211,
        output_tokens=64000,
        error=f"attempt {attempt} did not satisfy the schema",
    )


# `experiments/0003-feature-design-testscenario/run.py`, which calls `run_unit()`.


def test_a_failed_unit_still_writes_its_artifacts_before_the_failure_escapes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The defect: `write_run` sat after the call, so a raise skipped it entirely.

    This is the exact shape of the run whose cost went unrecoverable the first time.
    The exception still propagates, because the run really did fail; what must not
    happen is it taking the record of the spend with it.
    """
    script = load_script(EXPERIMENTS / "0003-feature-design-testscenario" / "run.py", "exp0003_run")
    unit, _ = script.target()
    lost = (an_artifact(unit, run=1, attempt=1), an_artifact(unit, run=1, attempt=2))

    def fails(*args: Any, **kwargs: Any) -> None:
        raise UnitFailed("run 1 failed again after its retry", lost)

    monkeypatch.setattr(script, "run_unit", fails)
    monkeypatch.setattr(script, "load_anthropic_settings", settings_for)
    monkeypatch.setattr(script, "ROOT", tmp_path)

    with pytest.raises(UnitFailed):
        script.main()

    written = sorted(p.name for p in (tmp_path / "artifacts" / "runs").rglob("*.json"))
    assert written == ["failed-run-1-attempt-1.json", "failed-run-1-attempt-2.json"]
    assert all(
        json.loads(p.read_text())["output"] is None
        for p in (tmp_path / "artifacts" / "runs").rglob("*.json")
    )


# `experiments/0002-effort-low-fidelity/calibrate_effort.py`, which calls
# `run_with_retry()` directly and builds its own artifacts.


def test_the_calibration_writes_an_artifact_per_attempt_rather_than_raising_typeerror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The regression test for the missing token arguments.

    Before the fix this call raised `TypeError: build_artifact() missing 2 required
    positional arguments`, so the script could not complete a single run. Reaching the
    summary at all is the assertion; the artifacts prove it wrote what each call cost.
    """
    script = load_script(
        EXPERIMENTS / "0002-effort-low-fidelity" / "calibrate_effort.py", "exp0002"
    )
    settled = RunOutcome(
        attempts=(Attempt(number=1, input_tokens=4211, output_tokens=9012, output=an_output()),)
    )

    monkeypatch.setattr(script, "run_with_retry", lambda *a, **k: settled)
    monkeypatch.setattr(script, "load_anthropic_settings", settings_for)
    monkeypatch.setattr(script, "build_client", lambda settings: None)
    monkeypatch.setattr(script, "DATA", tmp_path)

    assert script.main("medium") == 0

    runs = sorted(p.name for p in (tmp_path / "effort-medium").rglob("run-*.json"))
    assert runs == ["run-1.json", "run-2.json", "run-3.json"]
    payload = json.loads(next((tmp_path / "effort-medium").rglob("run-1.json")).read_text())
    assert payload["input_tokens"] == 4211
    assert payload["output_tokens"] == 9012


def test_a_calibration_that_fails_still_writes_every_attempt_it_paid_for(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`run_with_retry()` carries its attempts out in the exception; the shell writes them.

    A calibration that crashes without recording its spend is the same defect as a
    unit that does, and this script is the one that measures cost for a living.
    """
    script = load_script(
        EXPERIMENTS / "0002-effort-low-fidelity" / "calibrate_effort.py", "exp0002_fail"
    )
    attempts = (
        Attempt(number=1, input_tokens=4211, output_tokens=64000, error="malformed output"),
        Attempt(number=2, input_tokens=4211, output_tokens=63000, error="malformed output"),
    )

    def fails(*args: Any, **kwargs: Any) -> RunOutcome:
        raise ExtractionFailed("run 1 failed again after its retry", attempts)

    monkeypatch.setattr(script, "run_with_retry", fails)
    monkeypatch.setattr(script, "load_anthropic_settings", settings_for)
    monkeypatch.setattr(script, "build_client", lambda settings: None)
    monkeypatch.setattr(script, "DATA", tmp_path)

    with pytest.raises(ExtractionFailed):
        script.main("medium")

    written = sorted(p.name for p in (tmp_path / "effort-medium").rglob("*.json"))
    assert written == ["failed-run-1-attempt-1.json", "failed-run-1-attempt-2.json"]
    costs = [
        json.loads(p.read_text())["output_tokens"]
        for p in sorted((tmp_path / "effort-medium").rglob("*.json"))
    ]
    assert costs == [64000, 63000], "each attempt's own cost, never a running total"
