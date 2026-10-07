"""The old retry path refuses before any call (spec 0004 AC-71 to AC-71c).

These tests once covered how `run_unit()` recorded every attempt. Since the second
amendment of 2026-10-06 that path is closed: `run_with_retry()` retried any failure
with no per call ceiling, and `run_unit()`, `extract_unit()` and `extract_units()`
reach the API only through it. Extraction runs through `tracepath extract` now, whose
recording is covered in `test_extract_command.py` and `test_extract_guards.py`.
"""

from pathlib import Path
from typing import cast

import anthropic
import pytest

from tracepath.config import AnthropicSettings
from tracepath.extract import client as client_module
from tracepath.extract.client import (
    ExtractionFailed,
    RetryPathRetired,
    extract_unit,
    extract_units,
    run_with_retry,
)
from tracepath.extract.units import Unit, split_units
from tracepath.pipeline import UnitFailed, run_unit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"

#: Never used: the refusal comes before any call.
NO_CLIENT = cast(anthropic.Anthropic, object())
RUN_ARGS = ("requirements", "2e40bcf", "2026-10-06T00:00:00+00:00")


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


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Every model call that would have been made; none should be."""
    made: list[int] = []

    def counted(*args: object, **kwargs: object) -> object:
        made.append(1)
        raise AssertionError("a model call was made")

    monkeypatch.setattr(client_module, "extract_once", counted)
    return made


def test_ac_71_run_with_retry_refuses_before_any_call(
    unit: Unit, settings: AnthropicSettings, calls: list[int]
) -> None:
    """covers: AC-71."""
    with pytest.raises(RetryPathRetired):
        run_with_retry(NO_CLIENT, settings, unit, 0)

    assert calls == []


def test_ac_71_run_unit_refuses_before_any_call(
    unit: Unit, settings: AnthropicSettings, calls: list[int]
) -> None:
    """covers: AC-71 (`run_unit()` reaches the API only through `run_with_retry()`)."""
    with pytest.raises(RetryPathRetired):
        run_unit(NO_CLIENT, settings, unit, *RUN_ARGS)

    assert calls == []


def test_ac_71_extract_unit_refuses_before_any_call(
    unit: Unit, settings: AnthropicSettings, calls: list[int]
) -> None:
    """covers: AC-71 (`extract_unit()`)."""
    with pytest.raises(RetryPathRetired):
        extract_unit(NO_CLIENT, settings, unit)

    assert calls == []


def test_ac_71_extract_units_refuses_before_any_call(
    unit: Unit, settings: AnthropicSettings, calls: list[int]
) -> None:
    """covers: AC-71 (`extract_units()`)."""
    with pytest.raises(RetryPathRetired):
        extract_units(NO_CLIENT, settings, [unit])

    assert calls == []


def test_ac_71b_the_refusal_names_tracepath_extract(
    unit: Unit, settings: AnthropicSettings
) -> None:
    """covers: AC-71b."""
    with pytest.raises(RetryPathRetired, match="`tracepath extract`"):
        run_with_retry(NO_CLIENT, settings, unit, 0)


@pytest.mark.parametrize("caught", [ExtractionFailed, UnitFailed])
def test_ac_71c_the_refusal_is_not_a_failure_any_caller_catches(caught: type) -> None:
    """covers: AC-71c (derives from `Exception` only)."""
    assert not issubclass(RetryPathRetired, caught)


def test_ac_71c_the_refusal_passes_through_run_unit_unchanged(
    unit: Unit, settings: AnthropicSettings
) -> None:
    """covers: AC-71c (`run_unit()` catches `ExtractionFailed`; this is not one)."""
    with pytest.raises(RetryPathRetired) as caught:
        run_unit(NO_CLIENT, settings, unit, *RUN_ARGS)

    assert type(caught.value) is RetryPathRetired
