from pathlib import Path

import pytest

from tracepath.extract.units import (
    UnitAttributionError,
    UnitKind,
    record_id_for,
    split_units,
)

SNAPSHOT = Path(__file__).resolve().parents[1] / "corpus" / "jobhunt" / "docs"
SPECS = sorted(SNAPSHOT.glob("specs/*/index.md"))
SCOPE = SNAPSHOT / "scope" / "scope.md"


def relative(path: Path) -> str:
    return str(path.relative_to(SNAPSHOT))


def units_of(path: Path) -> tuple[object, ...]:
    return split_units(relative(path), path.read_text())


# AC-2: every byte of every extracted file belongs to exactly one unit.


@pytest.mark.parametrize("path", [*SPECS, SCOPE], ids=lambda p: p.parent.name)
def test_the_split_covers_every_byte_of_the_real_file_exactly_once(path: Path) -> None:
    units = split_units(relative(path), path.read_text())

    assert "".join(u.text for u in units) == path.read_text()


@pytest.mark.parametrize("path", SPECS, ids=lambda p: p.parent.name)
def test_every_spec_starts_with_a_preamble_then_only_sections(path: Path) -> None:
    units = split_units(relative(path), path.read_text())

    assert units[0].kind is UnitKind.PREAMBLE
    assert all(u.kind is UnitKind.SECTION for u in units[1:])


@pytest.mark.parametrize("path", SPECS, ids=lambda p: p.parent.name)
def test_every_spec_unit_belongs_to_that_spec_number(path: Path) -> None:
    expected = path.parent.name.split("-")[0]

    units = split_units(relative(path), path.read_text())

    assert {u.record_id for u in units} == {expected}


def test_a_spec_section_is_cited_by_its_own_heading() -> None:
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"

    sections = [u.section for u in split_units(relative(path), path.read_text())]

    assert sections[0] == "Preamble"
    assert "Requirements" in sections
    assert "Build plan" in sections
    assert "Follow-up" in sections


def test_the_preamble_holds_the_revision_notes_above_the_first_heading() -> None:
    path = SNAPSHOT / "specs" / "0008-app-shell-and-navigation" / "index.md"

    preamble = split_units(relative(path), path.read_text())[0]

    assert preamble.kind is UnitKind.PREAMBLE
    assert preamble.start_line == 1
    assert preamble.start_offset == 0
    assert "Revision 6" in preamble.text
    assert "## Summary" not in preamble.text


# AC-2: the scope document splits into feature rows, intros and its other sections.


def test_a_scope_feature_row_is_its_own_unit_owned_by_its_own_record() -> None:
    units = split_units(relative(SCOPE), SCOPE.read_text())

    rows = [u for u in units if u.kind is UnitKind.FEATURE_ROW]
    assert len(rows) == 33
    assert {u.record_id for u in rows} == {f"feature-{u.section.split('.')[0]}" for u in rows}


def test_a_feature_row_keeps_its_own_heading_as_its_section() -> None:
    units = split_units(relative(SCOPE), SCOPE.read_text())

    rows = {u.section: u for u in units if u.kind is UnitKind.FEATURE_ROW}
    assert "21. Terms & privacy notices · done · Alpha" in rows
    assert rows["21. Terms & privacy notices · done · Alpha"].record_id == "feature-21"


def test_exactly_the_five_sections_that_carry_feature_row_intros_are_intros() -> None:
    units = split_units(relative(SCOPE), SCOPE.read_text())

    intros = [u.section for u in units if u.kind is UnitKind.INTRO and u.has_body]
    assert intros == ["Slice 1: Core loop thread", "Slice 2: Ranking", "v1 extras", "v1.5", "v2"]


def test_the_foundation_section_carries_no_intro_text_of_its_own() -> None:
    units = split_units(relative(SCOPE), SCOPE.read_text())

    foundation = next(u for u in units if u.section == "Foundation")
    assert foundation.kind is UnitKind.INTRO
    assert not foundation.has_body


def test_a_scope_section_with_no_feature_rows_is_a_plain_section() -> None:
    units = split_units(relative(SCOPE), SCOPE.read_text())

    at_a_glance = next(u for u in units if u.section == "At a glance")
    assert at_a_glance.kind is UnitKind.SECTION
    assert at_a_glance.record_id == "scope"


def test_the_scope_head_above_the_first_heading_is_a_preamble() -> None:
    units = split_units(relative(SCOPE), SCOPE.read_text())

    assert units[0].kind is UnitKind.PREAMBLE
    assert units[0].record_id == "scope"
    assert "# Scope: JobHunt" in units[0].text


# Units locate themselves, because a citation needs the line the unit started on.


@pytest.mark.parametrize("path", [*SPECS, SCOPE], ids=lambda p: p.parent.name)
def test_every_unit_reports_the_line_and_offset_it_really_starts_at(path: Path) -> None:
    text = path.read_text()

    for unit in split_units(relative(path), text):
        assert text[unit.start_offset : unit.start_offset + len(unit.text)] == unit.text
        assert text[: unit.start_offset].count("\n") + 1 == unit.start_line


# Attribution: a file no record owns is an error, not a silent skip.


def test_a_file_outside_the_extracted_set_cannot_be_split() -> None:
    with pytest.raises(UnitAttributionError):
        split_units("specs/0012-model-client-router/rationale.md", "# anything\n")


def test_record_id_reads_the_spec_number_from_the_path() -> None:
    assert record_id_for("specs/0008-app-shell-and-navigation/index.md") == "0008"
    assert record_id_for("scope/scope.md") == "scope"


def test_a_heading_inside_a_fenced_code_block_does_not_start_a_unit() -> None:
    text = "# Title\n\n## Real\n\n```md\n## Not a heading\n```\n\ntail\n"

    units = split_units("specs/0001-x/index.md", text)

    assert [u.section for u in units] == ["Preamble", "Real"]
    assert "".join(u.text for u in units) == text
