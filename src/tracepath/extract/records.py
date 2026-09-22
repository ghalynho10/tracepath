"""Building `:Record` nodes from the file tree. Records are code's, never the model's.

A record is a whole document: a spec's `index.md`, the scope document, or one feature
row inside it. Everything about one is parsed (its number, title, status, the names the
corpus calls it by, and the spec a feature row points at), so nothing here is inferred.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from tracepath.extract.units import Unit, UnitKind

#: A spec's own title line. The corpus writes the separator two ways at the pinned
#: commit, `# 0012. Model client router` and `# 0009 · Terms and privacy notices`, so
#: both are read rather than one being treated as the shape and the other as malformed.
SPEC_TITLE = re.compile(r"^#\s+(\d+)\s*[.·]\s*(.+?)\s*$", re.MULTILINE)

#: The scope document's title line, `# Scope: JobHunt`.
SCOPE_TITLE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

#: A spec's status line, `**Status**: Accepted`.
SPEC_STATUS = re.compile(r"^\*\*Status\*\*:\s*(.+?)\s*$", re.MULTILINE)

#: A feature row's pointer line, `_spec [0008](../specs/0008-.../index.md) · code in ...`.
POINTER = re.compile(r"^_spec \[(\d+)\]\(([^)]+)\)", re.MULTILINE)

#: The pinned commit, as `SNAPSHOT.md` records it.
SNAPSHOT_COMMIT = re.compile(r"^-\s+\*\*Commit\*\*:\s*`([0-9a-f]+)`", re.MULTILINE)

#: The status words a scope row heading may carry, next to tier and approach tags.
ROW_STATUSES = frozenset(
    {"planned", "in-progress", "done", "existing", "dropped", "needs a decision"}
)


class RecordError(Exception):
    """A document does not carry what a record needs."""


class RecordKind(StrEnum):
    """The kinds of document a record stands for."""

    SPEC = "spec"
    SCOPE_DOCUMENT = "scope_document"
    SCOPE_FEATURE = "scope_feature"


@dataclass(frozen=True)
class Record:
    """One document, with every name the corpus calls it by."""

    canonical_id: str
    kind: RecordKind
    title: str
    status: str | None
    path: str
    commit: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class SpecifiedBy:
    """A feature row's pointer at the spec that designed it."""

    feature_record: str
    spec_record: str
    source_line: int


def read_commit(snapshot_text: str) -> str:
    """The pinned corpus commit, read from `SNAPSHOT.md`.

    Raises:
        RecordError: the file records no commit.
    """
    match = SNAPSHOT_COMMIT.search(snapshot_text)
    if match is None:
        raise RecordError("SNAPSHOT.md records no commit, so nothing can carry a citation")
    return match.group(1)[:7]


def _split_row_heading(heading: str) -> tuple[str, str | None]:
    """A feature row heading into its title and its status, dropping any tier tag."""
    parts = [part.strip() for part in heading.split("·")]
    title = re.sub(r"^\d+\.\s*", "", parts[0]).strip()
    status = next((part for part in parts[1:] if part.lower() in ROW_STATUSES), None)
    return title, status


def spec_record(path: str, text: str, commit: str) -> Record:
    """Build the record for one spec's `index.md`.

    Raises:
        RecordError: the file carries no `# NNNN. Title` heading.
    """
    title_match = SPEC_TITLE.search(text)
    if title_match is None:
        raise RecordError(f"{path}: no `# NNNN. Title` heading, so the record has no title")
    number, title = title_match.group(1), title_match.group(2)
    status_match = SPEC_STATUS.search(text)
    directory = path.split("/")[-2] if "/" in path else ""
    aliases = (number, title, f"spec {number}", directory)
    return Record(
        canonical_id=number,
        kind=RecordKind.SPEC,
        title=title,
        status=status_match.group(1) if status_match else None,
        path=path,
        commit=commit,
        aliases=tuple(dict.fromkeys(a for a in aliases if a)),
    )


def scope_document_record(path: str, text: str, commit: str) -> Record:
    """Build the record for the scope document itself."""
    title_match = SCOPE_TITLE.search(text)
    title = title_match.group(1) if title_match else "Scope"
    return Record(
        canonical_id="scope",
        kind=RecordKind.SCOPE_DOCUMENT,
        title=title,
        status=None,
        path=path,
        commit=commit,
        aliases=("scope", title, "scope.md"),
    )


def feature_record(unit: Unit, commit: str) -> Record:
    """Build the record for one `### N.` feature row.

    Raises:
        RecordError: the unit is not a feature row.
    """
    if unit.kind is not UnitKind.FEATURE_ROW:
        raise RecordError(f"{unit.section!r} is not a feature row, so it is no feature record")
    number = unit.record_id.removeprefix("feature-")
    title, status = _split_row_heading(unit.section)
    return Record(
        canonical_id=unit.record_id,
        kind=RecordKind.SCOPE_FEATURE,
        title=title,
        status=status,
        path=unit.path,
        commit=commit,
        aliases=tuple(dict.fromkeys((number, f"feature {number}", title, unit.record_id))),
    )


def specified_by(unit: Unit) -> SpecifiedBy | None:
    """The spec a feature row points at, or `None` when the row cites none.

    Read from the row's own pointer line, never inferred: at the pinned commit 15 of
    the 33 rows carry one, and a row with none simply has no link.
    """
    if unit.kind is not UnitKind.FEATURE_ROW:
        return None
    match = POINTER.search(unit.text)
    if match is None:
        return None
    return SpecifiedBy(
        feature_record=unit.record_id,
        spec_record=match.group(1),
        source_line=unit.start_line + unit.text.count("\n", 0, match.start()),
    )


def records_for(units: tuple[Unit, ...], text: str, commit: str) -> tuple[Record, ...]:
    """Every record one document produces: itself, plus a record per feature row."""
    if not units:
        return ()
    path = units[0].path
    if units[0].record_id == "scope":
        document = scope_document_record(path, text, commit)
        rows = tuple(
            feature_record(unit, commit) for unit in units if unit.kind is UnitKind.FEATURE_ROW
        )
        return (document, *rows)
    return (spec_record(path, text, commit),)
