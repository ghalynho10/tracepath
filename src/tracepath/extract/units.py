"""Splitting a corpus document into the units one extraction call is made from.

A unit is a top level `##` section of a spec's `index.md`, the text above the first
`##` in a file (the preamble), one `### N.` feature row of the scope document, the
text above the first feature row inside one of its `##` sections, or one of its other
`##` sections. Every byte of a file belongs to exactly one unit, so nothing is skipped
without a record of it (AC-2).
"""

import re
from dataclasses import dataclass
from enum import StrEnum

#: A top level section heading, e.g. `## Requirements`.
SECTION_HEADING = re.compile(r"^## (?!#)(.*)$")

#: A scope feature row heading, e.g. `### 21. Terms & privacy notices · done · Alpha`.
FEATURE_HEADING = re.compile(r"^### (\d+)\.\s*(.*)$")

#: A fenced code block's delimiter. Headings inside a fence are text, not headings.
FENCE = re.compile(r"^\s*(```|~~~)")

#: A spec lives at `specs/<number>-<slug>/index.md` inside the snapshot.
SPEC_PATH = re.compile(r"(?:^|/)specs/(\d+)-[^/]*/index\.md$")

#: The scope document lives at `scope/scope.md`.
SCOPE_PATH = re.compile(r"(?:^|/)scope/scope\.md$")

#: The section name a preamble is cited by, since it sits above every heading.
PREAMBLE_SECTION = "Preamble"


class UnitAttributionError(Exception):
    """A file or a unit inside it belongs to no record this corpus knows."""


class UnitKind(StrEnum):
    """Which of AC-2's five shapes a unit is."""

    PREAMBLE = "Preamble"
    SECTION = "Section"
    INTRO = "Intro"
    FEATURE_ROW = "FeatureRow"


@dataclass(frozen=True)
class Unit:
    """One stretch of a document, and everything a citation from it needs."""

    kind: UnitKind
    record_id: str
    section: str
    text: str
    path: str
    start_offset: int
    start_line: int

    @property
    def has_body(self) -> bool:
        """True when the unit holds more than its own heading line."""
        body = self.text.split("\n", 1)[1] if self.kind is not UnitKind.PREAMBLE else self.text
        return bool(body.strip())


@dataclass(frozen=True)
class _Boundary:
    """A line that starts a new unit."""

    line_index: int
    kind: UnitKind
    heading: str
    feature_number: str | None


def record_id_for(path: str) -> str:
    """The canonical id of the record a file belongs to, read from its path alone.

    Raises:
        UnitAttributionError: the path is neither a spec `index.md` nor the scope document.
    """
    spec = SPEC_PATH.search(path)
    if spec:
        return spec.group(1)
    if SCOPE_PATH.search(path):
        return "scope"
    raise UnitAttributionError(
        f"{path} is not a spec `index.md` or the scope document, so no record owns it"
    )


def _line_starts(text: str) -> tuple[list[str], list[int]]:
    """The file's lines, each keeping its own newline, plus each one's start offset."""
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    running = 0
    for line in lines:
        offsets.append(running)
        running += len(line)
    return lines, offsets


def _find_boundaries(lines: list[str], is_scope: bool) -> list[_Boundary]:
    """Every line that opens a new unit, in file order, ignoring fenced code."""
    boundaries: list[_Boundary] = []
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.rstrip("\n")
        section = SECTION_HEADING.match(stripped)
        if section:
            kind = UnitKind.INTRO if is_scope else UnitKind.SECTION
            boundaries.append(_Boundary(index, kind, section.group(1).strip(), None))
            continue
        if is_scope:
            feature = FEATURE_HEADING.match(stripped)
            if feature:
                heading = f"{feature.group(1)}. {feature.group(2).strip()}"
                boundaries.append(_Boundary(index, UnitKind.FEATURE_ROW, heading, feature.group(1)))
    return boundaries


def _settle_scope_section_kinds(boundaries: list[_Boundary]) -> list[_Boundary]:
    """A scope `##` section is an `Intro` only when feature rows follow it."""
    settled: list[_Boundary] = []
    for position, boundary in enumerate(boundaries):
        if boundary.kind is not UnitKind.INTRO:
            settled.append(boundary)
            continue
        following = boundaries[position + 1 :]
        next_section = next((b for b in following if b.kind is UnitKind.INTRO), None)
        rows_before_next_section = [
            b
            for b in following
            if b.kind is UnitKind.FEATURE_ROW
            and (next_section is None or b.line_index < next_section.line_index)
        ]
        kind = UnitKind.INTRO if rows_before_next_section else UnitKind.SECTION
        settled.append(
            _Boundary(boundary.line_index, kind, boundary.heading, boundary.feature_number)
        )
    return settled


def split_units(path: str, text: str) -> tuple[Unit, ...]:
    """Split one corpus document into its units, covering every byte exactly once.

    Args:
        path: the file's path inside the snapshot, which names the record it belongs to.
        text: the file's full text.

    Returns:
        The units in file order.

    Raises:
        UnitAttributionError: the file belongs to no record, or the split lost bytes.
    """
    record = record_id_for(path)
    is_scope = record == "scope"
    lines, offsets = _line_starts(text)
    boundaries = _find_boundaries(lines, is_scope)
    if is_scope:
        boundaries = _settle_scope_section_kinds(boundaries)

    units: list[Unit] = []
    starts = [b.line_index for b in boundaries]
    # A Preamble is emitted for the scope document too, not just a spec. AC-2 names the
    # Preamble only for a spec's `index.md`, which would leave the scope document's title
    # and opening notes in no unit at all and break AC-2's own byte coverage rule. Owed as
    # an amendment to AC-2, confirmed 2026-09-22, to be written by `/architect data model`.
    if not boundaries or boundaries[0].line_index > 0:
        end = starts[0] if starts else len(lines)
        units.append(
            Unit(
                kind=UnitKind.PREAMBLE,
                record_id=record,
                section=PREAMBLE_SECTION,
                text="".join(lines[:end]),
                path=path,
                start_offset=0,
                start_line=1,
            )
        )

    for position, boundary in enumerate(boundaries):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        units.append(
            Unit(
                kind=boundary.kind,
                record_id=(
                    f"feature-{boundary.feature_number}"
                    if boundary.feature_number is not None
                    else record
                ),
                section=boundary.heading,
                text="".join(lines[boundary.line_index : end]),
                path=path,
                start_offset=offsets[boundary.line_index],
                start_line=boundary.line_index + 1,
            )
        )

    rebuilt = "".join(unit.text for unit in units)
    if rebuilt != text:
        raise UnitAttributionError(
            f"{path}: the split does not cover the file exactly "
            f"({len(rebuilt)} characters against {len(text)})"
        )
    return tuple(units)
