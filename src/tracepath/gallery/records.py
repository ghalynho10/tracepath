"""Reading the stored ask records and the marks file the gallery shows (spec 0010).

The shell's side of the build: files are read here and handed to the pure renderer
as frozen models. Nothing here writes, and nothing is looked up again.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from tracepath.ask.record import ASKS_DIR

#: The marks file, relative to the repository root: the only list of what is shown.
MARKS_FILE = Path("gallery") / "marks.json"

#: The marks the engineer gives an answer (AC-11).
Mark = Literal["right", "partly right", "wrong", "declined"]

#: Folders the build reads and must never write into (AC-57).
READ_ONLY_DIRS = (Path("artifacts"), Path("corpus"))


class GalleryError(Exception):
    """The gallery cannot be built as asked; the message names what is wrong."""


class StoredClaim(BaseModel):
    """One claim as the ask record stored it, with the marks code set at ask time."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    text: str
    cites: tuple[str, ...]
    basis: str
    rejected_ids: tuple[str, ...]
    uncited: bool
    inferred: bool
    history: bool
    held_ids: tuple[str, ...]


class StoredItem(BaseModel):
    """One item of the pack the ask call sent, as stored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    line: str
    held: bool
    history: bool
    text: str


class AskRecord(BaseModel):
    """The fields of one ask record the gallery reads; its `links` are not read."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    question: str
    eval_file: str | None = None
    eval_question: int | None = None
    prompt_version: str
    hops: int | None = None
    asked_at: datetime
    corpus_commit: str
    verdict: str
    missing: tuple[str, ...]
    claims: tuple[StoredClaim, ...]
    items: tuple[StoredItem, ...]


class MarksEntry(BaseModel):
    """One entry of `gallery/marks.json`: a record to show and the engineer's mark on it."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    record: str
    label: str
    mark: Mark
    note: str | None
    source_path: str
    source_row: str


class Section(StrEnum):
    """The page section an entry appears in, by its record's `eval_file` (AC-2 to AC-4)."""

    DEVELOPMENT = "Development questions"
    HELD_OUT = "Held out questions"
    REALISTIC = "Realistic questions"


#: Which section each eval file's records appear in; no eval file means realistic.
SECTION_BY_EVAL_FILE: Mapping[str | None, Section] = MappingProxyType(
    {
        "eval/linked-records-research.json": Section.DEVELOPMENT,
        "eval/held-out.json": Section.HELD_OUT,
        None: Section.REALISTIC,
    }
)


@dataclass(frozen=True)
class Entry:
    """One shown answer: its marks entry, the record it names, and its section."""

    marks: MarksEntry
    record: AskRecord
    section: Section


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise GalleryError(f"{path}: not found") from None
    except json.JSONDecodeError as exc:
        raise GalleryError(f"{path}: not valid JSON ({exc})") from None


def _entry_name(number: int, entry: object) -> str:
    """How an error names a marks entry: its position, and its record when it has one."""
    record = entry.get("record") if isinstance(entry, dict) else None
    return f"entry {number}" + (f" ({record})" if isinstance(record, str) else "")


def parse_marks(data: object, source: str) -> tuple[MarksEntry, ...]:
    """The marks entries, each checked, with record and label unique (AC-9 to AC-11)."""
    if not isinstance(data, list):
        raise GalleryError(f"{source}: expected a JSON list of entries")
    entries: list[MarksEntry] = []
    for number, raw in enumerate(data, start=1):
        try:
            entries.append(MarksEntry.model_validate(raw))
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in error['loc']) or 'entry'}: {error['msg']}"
                for error in exc.errors()
            )
            raise GalleryError(f"{source}: {_entry_name(number, raw)}: {problems}") from None
    for field in ("record", "label"):
        values = [getattr(entry, field) for entry in entries]
        repeated = sorted({value for value in values if values.count(value) > 1})
        if repeated:
            raise GalleryError(f"{source}: `{field}` repeated: {', '.join(repeated)}")
    return tuple(entries)


def section_of(name: str, record: AskRecord) -> Section:
    """The section a record appears in; an unknown `eval_file` is refused (AC-6)."""
    try:
        return SECTION_BY_EVAL_FILE[record.eval_file]
    except KeyError:
        raise GalleryError(
            f"{name}: eval_file {record.eval_file!r} is not one the gallery shows"
        ) from None


def read_record(root: Path, name: str) -> AskRecord:
    """One record from `artifacts/asks/`, read into the fields the gallery shows."""
    path = root / ASKS_DIR / name
    data = _read_json(path)
    try:
        return AskRecord.model_validate(data)
    except ValidationError as exc:
        raise GalleryError(f"{path}: not an ask record the gallery can read ({exc})") from None


def load_entries(root: Path) -> tuple[Entry, ...]:
    """Every entry the marks file names, in its order, each with its record (AC-1, AC-5)."""
    marks = parse_marks(_read_json(root / MARKS_FILE), MARKS_FILE.as_posix())
    entries: list[Entry] = []
    for number, entry in enumerate(marks, start=1):
        if not (root / ASKS_DIR / entry.record).is_file():
            raise GalleryError(
                f"{MARKS_FILE.as_posix()}: entry {number} ({entry.label}) names "
                f"{entry.record}, which is not in {ASKS_DIR.as_posix()}/"
            )
        record = read_record(root, entry.record)
        entries.append(Entry(entry, record, section_of(entry.record, record)))
    return tuple(entries)


def refuse_read_only_out(root: Path, out: Path) -> None:
    """Raise when the output folder lies inside a folder the build only reads (AC-57)."""
    target = out.resolve()
    for folder in READ_ONLY_DIRS:
        guarded = (root / folder).resolve()
        if target == guarded or guarded in target.parents:
            raise GalleryError(f"--out {out}: the build never writes inside {folder}/")
