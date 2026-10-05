from pathlib import Path

from tracepath.extract.precheck import (
    checkbox_status_at,
    is_struck,
    mark_struck,
    read_binding_rules,
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


# Spec 0003, AC-1: a binding rule's leading span is read from the characters.


def test_a_rule_leading_span_ends_at_the_first_blank_line_after_its_marker() -> None:
    text = "## Binding rules\n\n**1. First.** Body.\nMore body.\n\nA second paragraph.\n"

    (rule,) = read_binding_rules(text)

    assert rule.number == 1
    assert rule.label == "binding rule 1"
    assert text[rule.start : rule.end] == "**1. First.** Body.\nMore body."


def test_a_rule_with_no_blank_line_before_the_next_marker_ends_at_that_marker() -> None:
    text = "**1. First.** Body.\n**2. Second.** Body."

    first, second = read_binding_rules(text)

    assert text[first.start : first.end] == "**1. First.** Body.\n"
    assert text[second.start : second.end] == "**2. Second.** Body."


def test_a_rule_marker_inside_a_fenced_block_is_text_not_a_rule() -> None:
    text = "**1. Real.** Body.\n\n```\n**2. Not a rule.**\n```\n"

    assert [rule.number for rule in read_binding_rules(text)] == [1]


def test_a_unit_with_no_bold_numbered_item_reports_no_rules() -> None:
    assert read_binding_rules("## Binding rules\n\n- a plain bullet\n") == ()


def test_the_real_binding_rules_of_spec_0001_read_eight_rules_in_order() -> None:
    unit = unit_named("0001", "Binding rules")

    rules = read_binding_rules(unit.text)  # type: ignore[attr-defined]

    assert [rule.number for rule in rules] == list(range(1, 9))
    six = unit.text[rules[5].start : rules[5].end]  # type: ignore[attr-defined]
    assert six.startswith("**6. Authorisation is never decided in the proxy.**")
    assert "\n\n" not in six
