"""The units a measured step of spec 0007 is scored on, and the checks they must pass.

Pure apart from `read_step_units()`, which reads one file. The list is written by
hand and committed before any paid call (AC-22, AC-22b), and the step is scored from
no other list. Code refuses a list naming a unit the step must not use (AC-23, AC-24).
"""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

#: Records no chosen unit may come from, each with why (spec 0007 AC-23). The held out
#: records are listed by number only: the held out file itself is never opened (AC-30).
EXCLUDED_RECORDS: dict[str, str] = {
    **dict.fromkeys(
        ("0004", "0005", "0010", "0016", "0017", "0018", "0020"),
        "the held out questions may cite it",
    ),
    **dict.fromkeys(("0006", "0008", "0012", "0019", "scope"), "worked examples draw on it"),
    **dict.fromkeys(("0002", "0021"), "the code pass was checked on it"),
}

#: The experiments whose READMEs list the units they ruled (AC-24).
RULED_BY = (
    Path("experiments") / "0005-held-out-prompt-examples" / "README.md",
    Path("experiments") / "0006-accuracy-bar-recheck" / "README.md",
)

#: A unit in one of those READMEs' unit tables: a backticked record, then the backticked
#: `## Section` when the unit is a section. A feature row has no section.
_TABLE_UNIT = re.compile(r"^\|(?: [A-Z] \|)? `(\d{4}|feature-\d+)`(?: `## ([^`]+)`)?", re.MULTILINE)


class UnitsRefused(Exception):
    """The units list cannot be used for the step as it stands."""


@dataclass(frozen=True)
class StepUnit:
    """One chosen unit: its record and section, and the address `extract` takes."""

    record: str
    section: str

    @property
    def address(self) -> str:
        """`RECORD:SECTION`, as `tracepath extract` takes it."""
        return f"{self.record}:{self.section}"


@dataclass(frozen=True)
class StepUnits:
    """A step's chosen units and the model every one of their runs must name (AC-22)."""

    expected_model: str
    units: tuple[StepUnit, ...]


def ruled_units(readme: str) -> frozenset[tuple[str, str | None]]:
    """Every unit a README's unit tables list, `(record, section)`; `None` for a feature row."""
    return frozenset((match.group(1), match.group(2)) for match in _TABLE_UNIT.finditer(readme))


def check_units(units: Iterable[StepUnit], ruled: frozenset[tuple[str, str | None]]) -> None:
    """Refuse a unit from an excluded record (AC-23) or one already ruled (AC-24).

    Raises:
        UnitsRefused: naming every unit refused and why.
    """
    refused: list[str] = []
    for unit in units:
        why = EXCLUDED_RECORDS.get(unit.record)
        if why is not None:
            refused.append(f"{unit.address}: record {unit.record} is excluded, {why}")
        elif (unit.record, unit.section) in ruled or (unit.record, None) in ruled:
            refused.append(f"{unit.address}: experiments 0005 or 0006 already ruled it")
    if refused:
        raise UnitsRefused("; ".join(refused))


def read_step_units(path: Path, root: Path) -> StepUnits:
    """Read a step's `units.json` and check it against AC-23 and AC-24.

    Raises:
        UnitsRefused: the file is unreadable or not in the expected shape, or names a
            unit `check_units()` refuses.
    """
    try:
        payload = json.loads(path.read_text())
        units = tuple(StepUnit(record=u["record"], section=u["section"]) for u in payload["units"])
        expected = payload["expected_model"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise UnitsRefused(f"{path} cannot be read as a units list ({exc!r})") from exc
    if not isinstance(expected, str) or not units:
        raise UnitsRefused(f"{path} names no expected model or no units")
    ruled: frozenset[tuple[str, str | None]] = frozenset()
    for readme in RULED_BY:
        ruled |= ruled_units((root / readme).read_text())
    check_units(units, ruled)
    return StepUnits(expected_model=expected, units=units)
