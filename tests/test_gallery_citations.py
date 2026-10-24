"""Reading an item's location out of its stored line, and its link (spec 0010). Pure."""

import pytest

from tracepath.gallery.citations import (
    JOBHUNT_COMMIT,
    ItemLine,
    is_pinned_commit,
    item_link,
    parse_item_line,
)

BLOB = f"https://github.com/ghalynho10/JobHunt/blob/{JOBHUNT_COMMIT}/docs/"


def test_five_field_line_parses() -> None:
    """AC-37."""
    line = "  0008/AC-7  AcceptanceCriterion  accepted  specs/0008-x/index.md:54  hit"

    assert parse_item_line(line) == ItemLine(
        "0008/AC-7", "AcceptanceCriterion", False, None, "specs/0008-x/index.md", 54, "hit"
    )


@pytest.mark.parametrize("marker", ["STRUCK", "HISTORY"])
def test_six_field_line_keeps_its_marker(marker: str) -> None:
    """AC-37, AC-47: `hop 1` keeps its one space inside it."""
    line = f"0021#f:12  Constraint  held  {marker}  specs/0021/index.md:314  hop 1"

    parsed = parse_item_line(line)

    assert parsed is not None
    assert (parsed.held, parsed.marker, parsed.reach) == (True, marker, "hop 1")


@pytest.mark.parametrize(
    "line",
    [
        "a  T  accepted  f.md:1",
        "a  T  accepted  f.md:1  hit  extra  more",
        "a  T   accepted  f.md:1  hit",
        "a  T  accepted  f.md:1  hit ",
        "a  T  maybe  f.md:1  hit",
        "a  T  accepted  DRAFT  f.md:1  hit",
        "a  T  accepted  f.md:1  hop",
        "a  T  accepted  f.md:1  hops 2",
        "a T  accepted  f.md:1  hit",
    ],
)
def test_line_of_any_other_shape_is_refused(line: str) -> None:
    """AC-37."""
    assert parse_item_line(line) is None


def test_link_goes_to_the_line_at_the_pinned_commit() -> None:
    """AC-34."""
    item = parse_item_line("a  T  accepted  specs/0008-x/index.md:54  hit")
    assert item is not None

    assert item_link(item) == f"{BLOB}specs/0008-x/index.md?plain=1#L54"


def test_link_to_a_file_with_no_line_has_no_anchor() -> None:
    """AC-35."""
    item = parse_item_line("a  T  accepted  scope/scope.md  hop 2")
    assert item is not None

    assert item_link(item) == f"{BLOB}scope/scope.md"


@pytest.mark.parametrize("location", ["no file stored", "no path stored"])
def test_item_with_no_location_gets_no_link(location: str) -> None:
    """AC-36."""
    item = parse_item_line(f"unresolved:x  Entity  held  {location}  hit")
    assert item is not None

    assert item.file is None
    assert item_link(item) is None


@pytest.mark.parametrize(
    ("commit", "pinned"),
    [("2e40bcf", True), (JOBHUNT_COMMIT, True), ("2e40bc", False), ("abcdef1", False)],
)
def test_pinned_commit_in_full_or_short(commit: str, pinned: bool) -> None:
    """AC-7."""
    assert is_pinned_commit(commit) is pinned
