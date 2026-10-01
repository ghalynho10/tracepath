"""`unit_provenance()` stamps each unit from its own run artifacts, never one for all.

A graph rebuilt from the committed artifacts holds units extracted under four prompt
versions. A single provenance for the whole load labelled every node with one of them,
so the graph could not tell a prompt change from a stable result. These tests drive a
real committed unit, rebuilt with no API call, and vary only its artifacts.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from tracepath.pipeline import ProvenanceMismatch, UnitResult, unit_provenance
from tracepath.rebuild import committed_units

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"


@pytest.fixture(scope="module")
def unit() -> UnitResult:
    return next(r for r in committed_units(ROOT, SNAPSHOT) if r.unit.record_id == "0014")


def test_provenance_is_read_off_the_units_own_first_run(unit: UnitResult) -> None:
    first = min(unit.artifacts, key=lambda a: a.run)

    provenance = unit_provenance(unit, accepted_by="auto")

    assert provenance.model == first.model
    assert provenance.prompt_version == first.prompt_version == "0003.1"
    assert provenance.extracted_at == first.extracted_at
    assert provenance.accepted_by == "auto"


def test_two_units_under_different_prompts_get_different_provenance(unit: UnitResult) -> None:
    older = replace(
        unit,
        artifacts=tuple(replace(a, prompt_version="0002.2") for a in unit.artifacts),
    )

    assert unit_provenance(unit, "auto").prompt_version == "0003.1"
    assert unit_provenance(older, "auto").prompt_version == "0002.2"


def test_a_failed_attempt_does_not_count_as_a_run(unit: UnitResult) -> None:
    failed = replace(unit.artifacts[0], output=None, prompt_version="9999.9", run=0)
    with_failure = replace(unit, artifacts=(failed, *unit.artifacts))

    assert unit_provenance(with_failure, "auto").prompt_version == "0003.1"


def test_runs_that_mix_prompt_versions_raise_rather_than_pick_one(unit: UnitResult) -> None:
    first, *rest = unit.artifacts
    mixed = replace(unit, artifacts=(first, *(replace(a, prompt_version="0002.3") for a in rest)))

    with pytest.raises(ProvenanceMismatch, match="0014"):
        unit_provenance(mixed, "auto")


def test_runs_that_mix_models_raise(unit: UnitResult) -> None:
    first, *rest = unit.artifacts
    mixed = replace(unit, artifacts=(first, *(replace(a, model="claude-opus-5") for a in rest)))

    with pytest.raises(ProvenanceMismatch, match="models"):
        unit_provenance(mixed, "auto")


def test_a_unit_with_no_settled_run_raises(unit: UnitResult) -> None:
    unsettled = replace(unit, artifacts=tuple(replace(a, output=None) for a in unit.artifacts))

    with pytest.raises(ProvenanceMismatch, match="no settled run"):
        unit_provenance(unsettled, "auto")
