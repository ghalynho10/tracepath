"""The accept to review ratio per unit and per unit kind (spec 0008 AC-7): no API call.

The counts are checked against two other sources: the committed review queue, which
`review-queue` reproduces byte for byte, counted by its own rows, and a crafted unit
with no accepted entity.
"""

import json
from collections import Counter
from dataclasses import replace

import pytest

from tests.test_code_pass import AC2, SPLIT, criterion, run, unit_of
from tests.test_code_pass_commands import COMMIT, ROOT, SNAPSHOT
from tracepath.artifacts import REVIEW_QUEUE
from tracepath.extract.compare import route_runs
from tracepath.extract.units import UnitKind
from tracepath.hold_ratio import (
    NO_ACCEPTED,
    SCOPE_ROW,
    HoldCount,
    UnitHold,
    kind_holds,
    ratio,
    ratio_lines,
    unit_holds,
    unit_kind,
)
from tracepath.pipeline import CorpusResolution, UnitResult, resolve_accepted
from tracepath.rebuild import committed_units, records_for_units
from tracepath.resolve.endpoints import Resolution


@pytest.fixture(scope="module")
def holds() -> tuple[UnitHold, ...]:
    results = committed_units(ROOT, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, COMMIT)
    return unit_holds(results, resolve_accepted(results, records))


def queue_counts() -> Counter[tuple[str, str, int]]:
    """The committed queue's rows by record, section and signature length (2 entity, 3 link)."""
    rows = json.loads((ROOT / REVIEW_QUEUE).read_text())
    return Counter((r["record"], r["section"], len(r["signature"])) for r in rows)


@pytest.mark.slow
def test_ac_7_one_named_unit_matches_a_hand_count(holds: tuple[UnitHold, ...]) -> None:
    """covers: AC-7 (0009 Requirements, counted off the committed queue's own rows)."""
    [hold] = [h for h in holds if (h.record, h.section) == ("0009", "Requirements")]
    counted = queue_counts()

    assert hold.count.held_entities == counted[("0009", "Requirements", 2)] == 10
    assert hold.count.held_links == counted[("0009", "Requirements", 3)] == 6
    assert hold.count.accepted_entities == 19
    assert ratio(hold.count) == "1 : 0.84"


@pytest.mark.slow
def test_ac_7_every_unit_matches_the_committed_queue(holds: tuple[UnitHold, ...]) -> None:
    """covers: AC-7 (rebuilt from the runs, every unit's held rows equal the queue's rows)."""
    counted = queue_counts()

    for hold in holds:
        assert hold.count.held_entities == counted[(hold.record, hold.section, 2)], hold
        assert hold.count.held_links == counted[(hold.record, hold.section, 3)], hold
    assert sum(h.count.held_rows for h in holds) == sum(counted.values())


@pytest.mark.slow
def test_ac_7_one_named_kind_sums_its_units(holds: tuple[UnitHold, ...]) -> None:
    """covers: AC-7 (the Requirements kind is the sum of every Requirements unit)."""
    kinds = dict(kind_holds(holds))
    requirements = [h.count for h in holds if h.section == "Requirements"]

    assert kinds["Requirements"] == sum(requirements, HoldCount(0, 0, 0))
    assert len(requirements) == 11
    assert kinds["Preamble"] == HoldCount(0, 0, 11)
    assert ratio(kinds["Preamble"]) == NO_ACCEPTED


def test_ac_7_unit_kinds_are_preamble_scope_row_or_the_heading() -> None:
    """covers: AC-7 (the three shapes a unit kind takes)."""
    unit = unit_of()

    assert unit_kind(unit) == "Requirements"
    assert unit_kind(replace(unit, kind=UnitKind.PREAMBLE, section="Preamble")) == "Preamble"
    assert unit_kind(replace(unit, kind=UnitKind.FEATURE_ROW, section="9. Profile")) == SCOPE_ROW


def test_ac_7_a_unit_with_no_accepted_entity_reports_so() -> None:
    """covers: AC-7 (no division by zero, in the unit row and its kind row)."""
    outputs = [run(criterion("AC-2", AC2, (SPLIT,))) for _ in range(3)]
    result = UnitResult(
        unit=unit_of(),
        section_slug="requirements",
        artifacts=(),
        identified=tuple(outputs),
        routed=route_runs(outputs),
        input_tokens=0,
        output_tokens=0,
    )

    [hold] = unit_holds([result], CorpusResolution(Resolution((), ()), ()))
    lines = ratio_lines([hold])

    assert hold.count == HoldCount(accepted_entities=0, held_entities=1, held_links=0)
    assert f"| 0099 Requirements (Requirements) | 0 | 1 | 0 | 1 | {NO_ACCEPTED} |" in lines
    assert f"| Requirements | 0 | 1 | 0 | 1 | {NO_ACCEPTED} |" in lines
