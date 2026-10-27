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

from tracepath.ask.answer import Basis, CheckedClaim, Claim, Verdict
from tracepath.ask.record import ASKS_DIR
from tracepath.gallery.citations import (
    JOBHUNT_COMMIT,
    ItemLine,
    is_pinned_commit,
    parse_item_line,
)
from tracepath.report import EVAL_FILE

#: The marks file, relative to the repository root: the only list of what is shown.
MARKS_FILE = Path("gallery") / "marks.json"

#: The link preview image, relative to the repository root; the build copies it (AC-75).
PREVIEW_FILE = Path("gallery") / "preview.png"

#: The pinned JobHunt snapshot every linked item is checked against (AC-38, AC-39).
SNAPSHOT_DOCS = Path("corpus") / "jobhunt" / "docs"

#: The marks the engineer gives an answer (AC-11).
Mark = Literal["right", "partly right", "wrong", "declined"]

#: The section the engineer puts an answer in (AC-2 to AC-4, AC-9).
SectionName = Literal["development", "held out", "realistic"]

#: Folders the build reads and must never write into (AC-57).
READ_ONLY_DIRS = (Path("artifacts"), Path("corpus"))

#: The vendored libraries, in the order the page inlines them (spec 0011 AC-71).
VENDOR_PACKAGES = ("d3-dispatch", "d3-quadtree", "d3-timer", "d3-force")

#: The vendored files and their record (AC-73), shipped beside this module.
VENDOR_DIR = Path(__file__).parent / "vendor"

#: The page's own script (spec 0011).
GRAPH_SCRIPT = Path(__file__).parent / "assets" / "graph.js"


#: Where a ruling the page may link to lives; any other source path is not published
#: (spec 0012 AC-59 to AC-61).
RULINGS_DIR = "experiments/"


class GalleryError(Exception):
    """The gallery cannot be built as asked; the message names what is wrong."""


class StoredClaim(BaseModel):
    """One claim as the ask record stored it, with the marks code set at ask time."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    text: str
    cites: tuple[str, ...]
    basis: Basis
    rejected_ids: tuple[str, ...]
    uncited: bool
    inferred: bool
    history: bool
    held_ids: tuple[str, ...]

    def checked(self) -> CheckedClaim:
        """The claim as `ask` checked it, so the page reads `ask`'s own rules (AC-31 to AC-33)."""
        return CheckedClaim(
            claim=Claim(text=self.text, cites=self.cites, basis=self.basis),
            rejected_ids=self.rejected_ids,
            uncited=self.uncited,
            inferred=self.inferred,
            history=self.history,
            held_ids=self.held_ids,
        )


class StoredItem(BaseModel):
    """One item of the pack the ask call sent, as stored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    line: str
    held: bool
    history: bool
    hop: int
    text: str


class StoredLink(BaseModel):
    """One link of the pack the ask call sent, as stored (spec 0011)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    type: str
    source: str
    target: str
    phrase: str | None
    held: bool


class AskRecord(BaseModel):
    """The fields of one ask record the gallery reads."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    question: str
    eval_file: str | None = None
    eval_question: int | None = None
    prompt_version: str
    hops: int | None = None
    asked_at: datetime
    corpus_commit: str
    verdict: Verdict
    missing: tuple[str, ...]
    claims: tuple[StoredClaim, ...]
    items: tuple[StoredItem, ...]
    links: tuple[StoredLink, ...]


class MarksEntry(BaseModel):
    """One entry of `gallery/marks.json`: a record to show and the engineer's mark on it."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    record: str
    label: str
    section: SectionName
    mark: Mark
    note: str | None
    source_path: str
    source_row: str


class Section(StrEnum):
    """The page section an entry appears in, as its marks entry names it (AC-2 to AC-4)."""

    DEVELOPMENT = "Development questions"
    HELD_OUT = "Held out questions"
    REALISTIC = "Realistic questions"


#: The page section each marks file `section` value names.
SECTION_BY_NAME: Mapping[SectionName, Section] = MappingProxyType(
    {
        "development": Section.DEVELOPMENT,
        "held out": Section.HELD_OUT,
        "realistic": Section.REALISTIC,
    }
)


@dataclass(frozen=True)
class Entry:
    """One shown answer: its marks entry, the record, its section, and its items' lines."""

    marks: MarksEntry
    record: AskRecord
    section: Section
    items: tuple[ItemLine, ...]


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise GalleryError(f"{path}: not found") from None
    except json.JSONDecodeError as exc:
        raise GalleryError(f"{path}: not valid JSON ({exc})") from None


@dataclass(frozen=True)
class PageScripts:
    """What the page inlines: each library's code with its licence, then the graph script."""

    libraries: tuple[tuple[str, str], ...]
    graph: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise GalleryError(f"{path}: cannot be read ({exc})") from None


def read_preview(base: Path) -> bytes:
    """The link preview image's bytes, or a `GalleryError` naming the file (AC-76)."""
    path = base / PREVIEW_FILE
    try:
        return path.read_bytes()
    except OSError as exc:
        raise GalleryError(f"{path}: cannot be read ({exc.strerror or exc})") from None


#: Text that would end an inline script element or change how the browser reads it (AC-68).
SCRIPT_BREAKERS = ("</script", "<!--")


def _inline_text(path: Path) -> str:
    """A file the page pastes into a script element, refused if it could break out of it."""
    text = _read_text(path)
    for breaker in SCRIPT_BREAKERS:
        if breaker in text.lower():
            raise GalleryError(f"{path}: holds {breaker!r}, which an inline script cannot carry")
    return text


def read_scripts(vendor: Path = VENDOR_DIR, graph: Path = GRAPH_SCRIPT) -> PageScripts:
    """The vendored libraries in inline order, each with its package's licence, and the script."""
    libraries = tuple(
        (_inline_text(vendor / f"{name}.min.js"), _inline_text(vendor / f"{name}.LICENSE"))
        for name in VENDOR_PACKAGES
    )
    return PageScripts(libraries, _inline_text(graph))


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


def _section_fits(record: AskRecord) -> SectionName:
    """The one section a record may be marked in, by its `eval_file` (AC-6).

    No eval file is realistic, the development eval file is development, and any other is
    held out.
    """
    if record.eval_file is None:
        return "realistic"
    if record.eval_file == EVAL_FILE.as_posix():
        return "development"
    return "held out"


def section_of(number: int, entry: MarksEntry, record: AskRecord) -> Section:
    """The entry's section, once its record agrees with it (AC-2 to AC-4, AC-6)."""
    fits = _section_fits(record)
    if entry.section != fits:
        raise GalleryError(
            f"{MARKS_FILE.as_posix()}: entry {number} ({entry.label}) is in section "
            f"{entry.section!r}, but {entry.record} has eval_file {record.eval_file!r}, "
            f"which belongs in {fits!r}"
        )
    return SECTION_BY_NAME[entry.section]


def read_record(root: Path, name: str) -> AskRecord:
    """One record from `artifacts/asks/`, read into the fields the gallery shows."""
    path = root / ASKS_DIR / name
    data = _read_json(path)
    try:
        return AskRecord.model_validate(data)
    except ValidationError as exc:
        raise GalleryError(f"{path}: not an ask record the gallery can read ({exc})") from None


def _is_plain_name(record: str) -> bool:
    """Whether a marks `record` names a file directly inside `artifacts/asks/` (AC-1)."""
    return bool(record) and "/" not in record and "\\" not in record and ".." not in record


def _is_file_under(root: Path, name: str) -> bool:
    """Whether `name` is a file inside `root`, never outside it."""
    path = (root / name).resolve()
    return path.is_relative_to(root.resolve()) and path.is_file()


def load_entries(root: Path) -> tuple[Entry, ...]:
    """Every entry the marks file names, in its order, each with its record (AC-1, AC-5)."""
    marks = parse_marks(_read_json(root / MARKS_FILE), MARKS_FILE.as_posix())
    entries: list[Entry] = []
    for number, entry in enumerate(marks, start=1):
        if not _is_plain_name(entry.record):
            raise GalleryError(
                f"{MARKS_FILE.as_posix()}: entry {number} ({entry.label}) names "
                f"{entry.record}, which is not a plain file name in {ASKS_DIR.as_posix()}/"
            )
        if not (root / ASKS_DIR / entry.record).is_file():
            raise GalleryError(
                f"{MARKS_FILE.as_posix()}: entry {number} ({entry.label}) names "
                f"{entry.record}, which is not in {ASKS_DIR.as_posix()}/"
            )
        if ".." in entry.source_path or "\\" in entry.source_path:
            raise GalleryError(
                f"{MARKS_FILE.as_posix()}: entry {number} ({entry.label}) names source_path "
                f"{entry.source_path}, which holds .. or a backslash (AC-62)"
            )
        if entry.source_path.startswith(RULINGS_DIR) and not _is_file_under(
            root, entry.source_path
        ):
            raise GalleryError(
                f"{MARKS_FILE.as_posix()}: entry {number} ({entry.label}) names source_path "
                f"{entry.source_path}, which is not a file under {root}"
            )
        record = read_record(root, entry.record)
        section = section_of(number, entry, record)
        entries.append(Entry(entry, record, section, checked_items(root, entry.record, record)))
    return tuple(entries)


def count_records(root: Path) -> int:
    """How many records `artifacts/asks/` holds, shown or not (AC-49)."""
    return sum(1 for _ in (root / ASKS_DIR).glob("*.json"))


def _line_count(docs: Path, name: str, file: str) -> int | None:
    """How many lines a snapshot file has, first line 1; None when it is not in the snapshot."""
    path = (docs / file).resolve()
    if not path.is_relative_to(docs.resolve()) or not path.is_file():
        return None
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError) as exc:
        raise GalleryError(
            f"{name}: {SNAPSHOT_DOCS.as_posix()}/{file} cannot be read ({exc})"
        ) from None


def checked_items(root: Path, name: str, record: AskRecord) -> tuple[ItemLine, ...]:
    """Each item's parsed line, once the record's commit, items and citations check out.

    Every item that gets a link is checked against the snapshot, cited or not
    (AC-7, AC-37 to AC-40, AC-42). Item ids are unique and every stored link's ends are
    among the items (spec 0011 AC-65, AC-66).
    """
    if not is_pinned_commit(record.corpus_commit):
        raise GalleryError(
            f"{name}: corpus_commit {record.corpus_commit!r} is not the pinned commit "
            f"{JOBHUNT_COMMIT}"
        )
    docs = root / SNAPSHOT_DOCS
    counts: dict[str, int | None] = {}
    parsed: list[ItemLine] = []
    for item in record.items:
        line = parse_item_line(item.line)
        if line is None or line.id != item.id:
            raise GalleryError(
                f"{name}: item {item.id}: stored line {item.line!r} has no known shape"
            )
        if line.file is not None:
            if line.file not in counts:
                counts[line.file] = _line_count(docs, name, line.file)
            count = counts[line.file]
            if count is None:
                raise GalleryError(
                    f"{name}: item {item.id}: {line.file} is not in {SNAPSHOT_DOCS.as_posix()}/"
                )
            if line.line is not None and not 1 <= line.line <= count:
                raise GalleryError(
                    f"{name}: item {item.id}: line {line.line} is outside {line.file} "
                    f"(lines 1 to {count})"
                )
        parsed.append(line)
    ids = [line.id for line in parsed]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise GalleryError(f"{name}: item id repeated: {', '.join(repeated)}")
    known = frozenset(ids)
    for number, link in enumerate(record.links, start=1):
        for end in (link.source, link.target):
            if end not in known:
                raise GalleryError(
                    f"{name}: link {number} ({link.source} {link.type} {link.target}) "
                    f"names {end}, which is not among the record's items"
                )
    by_id = {line.id: line for line in parsed}
    for claim in record.claims:
        for cited in claim.cites:
            if cited in claim.rejected_ids:
                continue
            if cited not in by_id:
                raise GalleryError(
                    f"{name}: a claim cites {cited}, which is neither among the record's "
                    "items nor in the claim's rejected_ids"
                )
            if by_id[cited].file is None:
                raise GalleryError(f"{name}: item {cited} is cited but has no stored file or path")
    return tuple(parsed)


def refuse_read_only_out(root: Path, out: Path) -> None:
    """Raise when the output folder lies inside a folder the build only reads (AC-57)."""
    target = out.resolve()
    for folder in READ_ONLY_DIRS:
        guarded = (root / folder).resolve()
        if target == guarded or guarded in target.parents:
            raise GalleryError(f"--out {out}: the build never writes inside {folder}/")
