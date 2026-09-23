from pathlib import Path

from tracepath.extract.precheck import (
    checkbox_status_at,
    is_struck,
    mark_struck,
    read_checkbox,
    read_checkboxes,
)
from tracepath.extract.schema import FollowUpStatus
from tracepath.extract.units import UnitKind, split_units

SNAPSHOT = Path(__file__).resolve().parents[1] / "corpus" / "jobhunt" / "docs"


def unit_named(spec: str, section: str) -> object:
    path = next(SNAPSHOT.glob(f"specs/{spec}-*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    return next(u for u in units if u.section == section)


# AC-5: struck ranges come from the characters, never from the model noticing.


def test_a_unit_with_no_struck_text_reports_no_ranges() -> None:
    assert mark_struck("- **AC-1**: plain text with no markers.\n") == ()


def test_a_struck_span_reports_its_own_offsets_and_inner_text() -> None:
    text = "runs ~~one real Adzuna search~~ two real Adzuna searches\n"

    ranges = mark_struck(text)

    assert len(ranges) == 1
    assert ranges[0].text == "one real Adzuna search"
    assert text[ranges[0].start : ranges[0].end] == "~~one real Adzuna search~~"


def test_a_struck_span_may_run_across_lines() -> None:
    text = "- **AC-2**: ~~The page makes no external paid call\n  on any render.~~ Superseded.\n"

    ranges = mark_struck(text)

    assert len(ranges) == 1
    assert "\n" in ranges[0].text


def test_the_real_struck_criterion_in_spec_0021_is_found_with_its_replacement_outside_it() -> None:
    unit = unit_named("0021", "Requirements")

    ranges = mark_struck(unit.text)  # type: ignore[attr-defined]
    struck_text = " ".join(r.text for r in ranges)

    assert "The page makes no external paid call on any render" in struck_text
    assert "SUPERSEDED 2026-09-14" not in struck_text


def test_an_offset_inside_a_struck_range_is_struck_and_one_outside_is_not() -> None:
    text = "before ~~gone~~ after\n"
    ranges = mark_struck(text)

    assert is_struck(ranges, text.index("gone"))
    assert not is_struck(ranges, text.index("after"))


def test_a_span_that_could_not_be_located_is_never_struck() -> None:
    ranges = mark_struck("~~gone~~\n")

    assert not is_struck(ranges, None)


def test_struck_markers_inside_a_fenced_block_are_text_not_markup() -> None:
    text = "```\n~~not struck~~\n```\n"

    assert mark_struck(text) == ()


# AC-6: checkbox state is parsed, never inferred.


def test_a_unit_with_no_checkbox_reports_none() -> None:
    assert read_checkbox("plain paragraph\n") is None
    assert read_checkboxes("plain paragraph\n") == ()


def test_a_ticked_box_reads_done_and_an_empty_box_reads_open() -> None:
    assert read_checkbox("- [x] settled\n") is FollowUpStatus.DONE
    assert read_checkbox("- [ ] still open\n") is FollowUpStatus.OPEN


def test_each_item_governs_the_text_from_its_own_marker_to_the_next() -> None:
    text = "- [x] first item\n  continued\n- [ ] second item\n"

    items = read_checkboxes(text)

    assert [i.status for i in items] == [FollowUpStatus.DONE, FollowUpStatus.OPEN]
    assert checkbox_status_at(items, text.index("continued")) is FollowUpStatus.DONE
    assert checkbox_status_at(items, text.index("second")) is FollowUpStatus.OPEN


def test_an_offset_before_the_first_item_belongs_to_no_checkbox() -> None:
    text = "## Follow-up\n\n- [x] done thing\n"

    items = read_checkboxes(text)

    assert checkbox_status_at(items, text.index("Follow-up")) is None
    assert checkbox_status_at(items, None) is None


def test_the_real_follow_up_section_of_spec_0012_reads_two_done_and_seven_open() -> None:
    unit = unit_named("0012", "Follow-up")

    items = read_checkboxes(unit.text)  # type: ignore[attr-defined]

    assert [i.status for i in items].count(FollowUpStatus.DONE) == 2
    assert [i.status for i in items].count(FollowUpStatus.OPEN) == 7


def test_every_follow_up_section_in_the_corpus_parses_a_status_for_every_item() -> None:
    for path in sorted(SNAPSHOT.glob("specs/*/index.md")):
        units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
        for unit in units:
            if unit.kind is not UnitKind.SECTION or unit.section != "Follow-up":
                continue
            items = read_checkboxes(unit.text)
            bullets = sum(
                1 for line in unit.text.splitlines() if line.lstrip().startswith(("- [", "* ["))
            )
            assert len(items) == bullets, f"{path.parent.name}: {len(items)} against {bullets}"
