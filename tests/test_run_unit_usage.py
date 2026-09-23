"""`run_unit()` writes one artifact per attempt, so no call's cost goes unrecorded.

The pieces are covered in `test_artifacts.py`; this covers the wiring between them,
which is where the original defect lived. Nothing here touches the network: the model
call itself is replaced, so what is exercised is the retry and recording path.
"""

import json
from pathlib import Path
from typing import cast

import anthropic
import pytest

from tracepath.artifacts import write_run
from tracepath.config import AnthropicSettings
from tracepath.extract import client as client_module
from tracepath.extract.client import Attempt, ExtractionFailed
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, split_units
from tracepath.pipeline import UnitFailed, run_unit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
FIXTURES = Path(__file__).parent / "fixtures" / "runs"

#: The model call is replaced in every test here, so the client is never used.
NO_CLIENT = cast(anthropic.Anthropic, object())
RUN_ARGS = ("requirements", "2e40bcf", "2026-09-23T00:00:00+00:00")


@pytest.fixture
def unit() -> Unit:
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"
    return next(
        u
        for u in split_units("specs/0012-model-client-router/index.md", path.read_text())
        if u.section == "Requirements"
    )


@pytest.fixture
def settings() -> AnthropicSettings:
    return AnthropicSettings(
        api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort="medium"
    )


def an_output() -> ExtractionOutput:
    return ExtractionOutput.model_validate(json.loads((FIXTURES / "run1.json").read_text()))


def scripted(
    monkeypatch: pytest.MonkeyPatch, outcomes: list[Attempt | ExtractionFailed]
) -> list[int]:
    """Replace the model call with a fixed script, and count the calls made."""
    calls: list[int] = []

    def fake(client: object, settings: object, unit: object, number: int = 1) -> Attempt:
        calls.append(number)
        result = outcomes[len(calls) - 1]
        if isinstance(result, ExtractionFailed):
            raise result
        return result

    monkeypatch.setattr(client_module, "extract_once", fake)
    return calls


def failure(number: int, used_in: int, used_out: int) -> ExtractionFailed:
    message = f"attempt {number} did not satisfy the schema"
    return ExtractionFailed(
        message,
        (Attempt(number=number, input_tokens=used_in, output_tokens=used_out, error=message),),
    )


def test_a_retried_run_writes_both_attempts_with_their_own_numbers(
    monkeypatch: pytest.MonkeyPatch, unit: Unit, settings: AnthropicSettings, tmp_path: Path
) -> None:
    """The failed attempt's cost sits beside the retry's, never added into it."""
    scripted(
        monkeypatch,
        [
            failure(1, 500, 64000),
            Attempt(number=2, input_tokens=500, output_tokens=9000, output=an_output()),
            Attempt(number=1, input_tokens=500, output_tokens=9100, output=an_output()),
            Attempt(number=1, input_tokens=500, output_tokens=9200, output=an_output()),
        ],
    )

    result = run_unit(NO_CLIENT, settings, unit, *RUN_ARGS)

    # Four calls, four artifacts: three settled runs plus the one that failed.
    assert len(result.artifacts) == 4
    names = sorted(write_run(tmp_path, a).name for a in result.artifacts)
    assert names == ["failed-run-1-attempt-1.json", "run-1.json", "run-2.json", "run-3.json"]

    failed = next(a for a in result.artifacts if a.output is None)
    retry = next(a for a in result.artifacts if a.run == 1 and a.output is not None)
    assert failed.output_tokens == 64000
    assert retry.output_tokens == 9000
    assert retry.attempt == 2


def test_the_unit_total_counts_the_failed_attempt_too(
    monkeypatch: pytest.MonkeyPatch, unit: Unit, settings: AnthropicSettings
) -> None:
    """A retry that is left out of the total is a cost the run silently did not report."""
    scripted(
        monkeypatch,
        [
            failure(1, 500, 64000),
            Attempt(number=2, input_tokens=500, output_tokens=9000, output=an_output()),
            Attempt(number=1, input_tokens=500, output_tokens=9000, output=an_output()),
            Attempt(number=1, input_tokens=500, output_tokens=9000, output=an_output()),
        ],
    )

    result = run_unit(NO_CLIENT, settings, unit, *RUN_ARGS)

    assert result.output_tokens == 64000 + 9000 * 3
    assert result.input_tokens == 500 * 4


def test_a_unit_that_fails_after_its_retry_still_hands_back_its_artifacts(
    monkeypatch: pytest.MonkeyPatch, unit: Unit, settings: AnthropicSettings, tmp_path: Path
) -> None:
    """This is the case that made the first 21 call run's cost unrecoverable."""
    scripted(monkeypatch, [failure(1, 500, 64000), failure(2, 500, 63000)])

    with pytest.raises(UnitFailed) as caught:
        run_unit(NO_CLIENT, settings, unit, *RUN_ARGS)

    artifacts = caught.value.artifacts
    assert len(artifacts) == 2
    assert all(a.output is None for a in artifacts)
    assert sum(a.output_tokens or 0 for a in artifacts) == 127000
    written = [write_run(tmp_path, a) for a in artifacts]
    assert [p.name for p in written] == [
        "failed-run-1-attempt-1.json",
        "failed-run-1-attempt-2.json",
    ]
    assert all(json.loads(p.read_text())["output"] is None for p in written)
