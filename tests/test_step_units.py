"""The units spec 0007's step is scored on, checked against AC-23 and AC-24.

Reads `experiments/0012-extraction-accuracy-step-one/units.json` and the two READMEs
AC-24 names, nothing else: the held out file is never opened (AC-30).
"""

from pathlib import Path

import pytest

from tracepath.measure import (
    EXCLUDED_RECORDS,
    RULED_BY,
    StepUnit,
    UnitsRefused,
    check_units,
    read_step_units,
    ruled_units,
)

ROOT = Path(__file__).resolve().parents[1]
UNITS = ROOT / "experiments" / "0012-extraction-accuracy-step-one" / "units.json"


def test_ac_22_the_committed_list_names_its_model_and_three_units() -> None:
    """covers: AC-22, and AC-23 and AC-24 on the committed list."""
    step = read_step_units(UNITS, ROOT)

    assert step.expected_model == "claude-sonnet-5-5"
    assert [u.address for u in step.units] == [
        "0009:Requirements",
        "0013:Requirements",
        "0015:Requirements",
    ]


@pytest.mark.parametrize("record", sorted(EXCLUDED_RECORDS))
def test_ac_23_a_unit_in_an_excluded_record_is_refused(record: str) -> None:
    """covers: AC-23."""
    with pytest.raises(UnitsRefused, match=f"record {record} is excluded"):
        check_units([StepUnit(record, "Requirements")], frozenset())


def test_ac_23_names_every_record_the_spec_lists() -> None:
    """covers: AC-23 (the list itself)."""
    assert set(EXCLUDED_RECORDS) == {
        *("0004", "0005", "0010", "0016", "0017", "0018", "0020"),
        *("0006", "0008", "0012", "0019", "scope"),
        *("0002", "0021"),
    }


def test_ac_24_the_units_the_two_experiments_ruled_are_read_from_their_readmes() -> None:
    """covers: AC-24 (read from the READMEs, not written out here)."""
    ruled: frozenset[tuple[str, str | None]] = frozenset()
    for readme in RULED_BY:
        ruled |= ruled_units((ROOT / readme).read_text())

    assert ruled == {
        ("0021", "Requirements"),
        ("0013", "Feature design"),
        ("feature-9", None),
        ("0014", "Requirements"),
        ("0015", "Feature design"),
        ("feature-33", None),
    }


@pytest.mark.parametrize(
    "unit", [StepUnit("0014", "Requirements"), StepUnit("feature-9", "Profile entry")]
)
def test_ac_24_a_unit_already_ruled_is_refused(unit: StepUnit) -> None:
    """covers: AC-24 (a section unit, and a feature row under any section name)."""
    ruled = frozenset({("0014", "Requirements"), ("feature-9", None)})

    with pytest.raises(UnitsRefused, match="already ruled"):
        check_units([unit], ruled)


def test_ac_24_another_section_of_a_ruled_record_is_allowed() -> None:
    """covers: AC-24 (it names units, not records)."""
    check_units([StepUnit("0013", "Requirements")], frozenset({("0013", "Feature design")}))


@pytest.mark.parametrize(
    "text",
    [
        None,
        "{not json",
        '{"units": [{"record": "0009", "section": "Requirements"}]}',
        '{"expected_model": "claude-sonnet-5-5", "units": [{"record": "0009"}]}',
        '{"expected_model": "claude-sonnet-5-5", "units": []}',
        '{"expected_model": 5, "units": [{"record": "0009", "section": "Requirements"}]}',
    ],
    ids=["missing", "not json", "no model", "no section", "no units", "model not text"],
)
def test_ac_22_a_list_that_cannot_name_its_model_and_units_is_refused(
    tmp_path: Path, text: str | None
) -> None:
    """covers: AC-22 (the step is scored from this list only, so a broken one stops it)."""
    path = tmp_path / "units.json"
    if text is not None:
        path.write_text(text)

    with pytest.raises(UnitsRefused, match=r"units\.json"):
        read_step_units(path, ROOT)
