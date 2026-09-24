"""Token usage per attempt, and the two review files, are what spec 0001 asks for.

Every test here is a regression guard for a defect that actually happened. The 21 call
run's cost is permanently unmeasured because usage was never in the artifact and the
run died before writing a summary, and the 97 held links had nowhere durable to live
while `write_review_queue()` sat with no caller.
"""

import json
from pathlib import Path

import pytest

from tracepath.artifacts import (
    RunArtifact,
    build_artifact,
    ensure_review_log,
    read_run,
    run_path,
    write_review_log,
    write_run,
)
from tracepath.extract.client import Attempt, ExtractionFailed, RunOutcome
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, split_units

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def a_unit() -> Unit:
    """One real unit of the pinned snapshot, so nothing here is invented."""
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"
    return next(
        u
        for u in split_units("specs/0012-model-client-router/index.md", path.read_text())
        if u.section == "Requirements"
    )


def an_output() -> ExtractionOutput:
    """One valid extraction output, from the committed fixtures."""
    return ExtractionOutput.model_validate(json.loads((FIXTURES / "run1.json").read_text()))


def artifact(**over: object) -> RunArtifact:
    """A run artifact with every field given, overridable one at a time."""
    fields: dict[str, object] = {
        "unit": a_unit(),
        "section_slug": "requirements",
        "run": 1,
        "output": an_output(),
        "model": "claude-sonnet-5",
        "prompt_version": "0002.2",
        "commit": "2e40bcf",
        "extracted_at": "2026-09-23T00:00:00+00:00",
        "max_output_tokens": 64000,
        "effort": "medium",
        "input_tokens": 7000,
        "output_tokens": 21000,
    }
    fields.update(over)
    return build_artifact(**fields)  # type: ignore[arg-type]


# Usage rides on every artifact, and counts one attempt rather than a running total.


def test_a_settled_run_carries_its_own_token_usage(tmp_path: Path) -> None:
    path = write_run(tmp_path, artifact())

    payload = json.loads(path.read_text())

    assert payload["input_tokens"] == 7000
    assert payload["output_tokens"] == 21000
    assert path.name == "run-1.json"


def test_a_call_that_raises_still_produces_an_artifact_carrying_its_usage(
    tmp_path: Path,
) -> None:
    """The defect this closes: a failure that hides its own cost."""
    failed = artifact(output=None, attempt=1, input_tokens=6800, output_tokens=64000, error="boom")

    path = write_run(tmp_path, failed)
    payload = json.loads(path.read_text())

    assert payload["output"] is None
    assert payload["input_tokens"] == 6800
    assert payload["output_tokens"] == 64000
    assert payload["error"] == "boom"


def test_a_failed_attempt_lands_beside_the_run_and_not_on_top_of_it(tmp_path: Path) -> None:
    """The retry replaces the failed attempt, so only the retry may take `run-N.json`."""
    failed = run_path(tmp_path, artifact(output=None, attempt=1, error="boom"))
    retry = run_path(tmp_path, artifact(attempt=2))

    assert failed.name == "failed-run-1-attempt-1.json"
    assert retry.name == "run-1.json"
    assert failed.parent == retry.parent


def test_a_failed_attempt_is_not_read_back_as_a_fourth_run(tmp_path: Path) -> None:
    """A rebuild globs `run-*.json`; a failure caught by that glob would be a phantom run."""
    write_run(tmp_path, artifact(run=1))
    write_run(tmp_path, artifact(run=1, output=None, attempt=1, error="boom"))

    settled = sorted((tmp_path / "artifacts" / "runs").glob("*/*/run-*.json"))

    assert [p.name for p in settled] == ["run-1.json"]


def test_usage_survives_a_round_trip(tmp_path: Path) -> None:
    path = write_run(tmp_path, artifact(input_tokens=11, output_tokens=22))

    assert read_run(path).input_tokens == 11
    assert read_run(path).output_tokens == 22


def test_an_artifact_written_before_the_field_reads_as_unmeasured(tmp_path: Path) -> None:
    """Null means unmeasured, which is what the 24 artifacts of the first runs are.

    Their numbers cannot be recovered without re-calling the model, so reading a zero
    there would report a cost that was never measured as if it had been.
    """
    path = write_run(tmp_path, artifact())
    payload = json.loads(path.read_text())
    del payload["input_tokens"]
    del payload["output_tokens"]
    path.write_text(json.dumps(payload))

    legacy = read_run(path)

    assert legacy.input_tokens is None
    assert legacy.output_tokens is None
    assert legacy.output is not None


# The retry policy keeps every attempt, so no cost disappears into the call after it.


def test_a_run_outcome_reports_the_settling_attempt_and_the_wasted_one_apart() -> None:
    outcome = RunOutcome(
        attempts=(
            Attempt(number=1, input_tokens=100, output_tokens=900, error="malformed"),
            Attempt(number=2, input_tokens=100, output_tokens=800, output=an_output()),
        )
    )

    assert outcome.input_tokens == 100
    assert outcome.output_tokens == 800
    assert outcome.wasted_output_tokens == 900
    assert outcome.output is not None


def test_a_run_that_failed_after_its_retry_still_carries_both_attempts() -> None:
    attempts = (
        Attempt(number=1, input_tokens=100, output_tokens=900, error="one"),
        Attempt(number=2, input_tokens=100, output_tokens=950, error="two"),
    )

    failure = ExtractionFailed("run 1 failed after its retry", attempts)

    assert sum(a.output_tokens for a in failure.attempts) == 1850


def test_an_outcome_with_no_successful_attempt_raises_rather_than_returning_nothing() -> None:
    outcome = RunOutcome(attempts=(Attempt(number=1, input_tokens=1, output_tokens=2, error="x"),))

    with pytest.raises(ExtractionFailed):
        _ = outcome.output


# The review log records what a person ruled on, so a pipeline run must not touch it.


def test_the_review_log_is_created_empty_when_there_is_none(tmp_path: Path) -> None:
    path = ensure_review_log(tmp_path)

    assert json.loads(path.read_text()) == []


def test_the_review_log_is_never_overwritten_by_a_later_run(tmp_path: Path) -> None:
    """A run rules on nothing, so writing `[]` over a reviewer's work would erase it."""
    ruled = [{"canonical_id": "0012/AC-1", "ruling": "accepted", "by": "a person"}]
    write_review_log(tmp_path, ruled)

    ensure_review_log(tmp_path)

    assert json.loads((tmp_path / "artifacts" / "review-log.json").read_text()) == ruled
