"""Reading the stored ask records and the marks file the gallery shows (spec 0010).

The shell's side of the build: files are read here and handed to the pure renderer
as frozen models. Nothing here writes, and nothing is looked up again.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from tracepath.ask.record import ASKS_DIR

#: The marks file, relative to the repository root: the only list of what is shown.
MARKS_FILE = Path("gallery") / "marks.json"

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


@dataclass(frozen=True)
class Entry:
    """One shown answer: the record's file name and what it stores."""

    record_name: str
    record: AskRecord


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise GalleryError(f"{path}: not found") from None
    except json.JSONDecodeError as exc:
        raise GalleryError(f"{path}: not valid JSON ({exc})") from None


def marked_records(root: Path) -> tuple[str, ...]:
    """The record names `gallery/marks.json` lists, in its order."""
    path = root / MARKS_FILE
    data = _read_json(path)
    if not isinstance(data, list):
        raise GalleryError(f"{path}: expected a JSON list of entries")
    names: list[str] = []
    for number, entry in enumerate(data, start=1):
        if not isinstance(entry, dict) or not isinstance(entry.get("record"), str):
            raise GalleryError(f"{path}: entry {number} has no `record` file name")
        names.append(entry["record"])
    return tuple(names)


def read_record(root: Path, name: str) -> AskRecord:
    """One record from `artifacts/asks/`, read into the fields the gallery shows."""
    path = root / ASKS_DIR / name
    data = _read_json(path)
    try:
        return AskRecord.model_validate(data)
    except ValidationError as exc:
        raise GalleryError(f"{path}: not an ask record the gallery can read ({exc})") from None


def load_entries(root: Path) -> tuple[Entry, ...]:
    """Every entry the marks file names, in its order, each with its record."""
    return tuple(Entry(name, read_record(root, name)) for name in marked_records(root))


def refuse_read_only_out(root: Path, out: Path) -> None:
    """Raise when the output folder lies inside a folder the build only reads (AC-57)."""
    target = out.resolve()
    for folder in READ_ONLY_DIRS:
        guarded = (root / folder).resolve()
        if target == guarded or guarded in target.parents:
            raise GalleryError(f"--out {out}: the build never writes inside {folder}/")
