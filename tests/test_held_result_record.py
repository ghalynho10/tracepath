"""The second result's record, as spec 0005 asks it to read (AC-29, AC-29b).

The commit order itself (AC-28) needs the git history, which CI's shallow checkout
does not hold; `/check verify` confirmed it (docs/reviews, E19). This reads the record.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "experiments" / "0010-held-item-view" / "README.md"

#: The commits spec 0005's held out discipline names, in the order they must come.
DESIGN, CODE, RESULT = "74e8406", "8ef5de4", "2bef321"


def header() -> str:
    """The record's opening lines, before its first section."""
    return RECORD.read_text().split("\n## ", 1)[0]


def test_ac_29_the_record_names_the_design_code_and_result_commits() -> None:
    """covers: spec 0005 AC-29 (all three named, each by its role)."""
    text = header()

    assert re.search(rf"\*\*Design commit\*\*: `{DESIGN}`", text)
    assert re.search(rf"\*\*Code commit\*\*: `{CODE}`", text)
    assert re.search(rf"\*\*Result commit\*\*: `{RESULT}`", text)


def test_ac_29_the_record_names_the_three_commits_in_that_order() -> None:
    """covers: spec 0005 AC-29 (design, then code, then result)."""
    text = header()

    assert text.index(DESIGN) < text.index(CODE) < text.index(RESULT)


def test_ac_29b_the_record_says_it_is_a_second_result_beside_experiment_0009() -> None:
    """covers: spec 0005 AC-29b."""
    text = " ".join(header().split())

    assert "This is a second result." in text
    assert "Experiment 0009](../0009-first-traced-chain/README.md) stays the first" in text


def test_the_record_cites_the_outputs_it_was_scored_on() -> None:
    data = RECORD.parent / "data"

    for name in ("trace-1.txt", "trace-2.txt", "trace-3.txt", "load-1.txt", "load-2.txt"):
        assert (data / name).exists(), name
    assert (data / "trace-1.txt").read_bytes() == (data / "trace-2.txt").read_bytes()
