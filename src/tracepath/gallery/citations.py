"""Citations: where each stored item sits in JobHunt, and its link there (spec 0010). Pure.

An item's location is read back out of its stored display line, by the grammar in the
spec's Feature design. A line of any other shape is refused, never guessed (AC-37).
"""

import re
from dataclasses import dataclass
from urllib.parse import quote

#: JobHunt on GitHub, the repository every citation points into.
JOBHUNT_REPO_URL = "https://github.com/ghalynho10/JobHunt"

#: The full commit the corpus is pinned at; `corpus/jobhunt/SNAPSHOT.md` records it (AC-43).
JOBHUNT_COMMIT = "2e40bcfe1078cc93ab2f951e6c7c708e4825aa1b"

#: Where an item's file sits inside the JobHunt repository.
DOCS_PREFIX = "docs/"

#: The shortest commit prefix a record may store for the pinned commit (git's default).
SHORT_COMMIT = 7

#: Locations that name no file, so the item gets no link (AC-36).
NO_LOCATION = ("no file stored", "no path stored")

#: The optional fourth field of a stored line.
MARKERS = ("STRUCK", "HISTORY")

_REACH = re.compile(r"hit|hop \d+")
_FILE_LINE = re.compile(r"(.+):(\d+)")


@dataclass(frozen=True)
class ItemLine:
    """The fields of one stored item line; `file` is None for an item with no location."""

    id: str
    type: str
    held: bool
    marker: str | None
    file: str | None
    line: int | None
    reach: str


def parse_item_line(text: str) -> ItemLine | None:
    """The stored line's fields, or None when it is not of the known shape (AC-37)."""
    fields = text.lstrip(" ").split("  ")
    if len(fields) not in (5, 6) or any(not f or f != f.strip(" ") for f in fields):
        return None
    marker = fields[3] if len(fields) == 6 else None
    status, location, reach = fields[2], fields[-2], fields[-1]
    if status not in ("held", "accepted") or not _REACH.fullmatch(reach):
        return None
    if marker is not None and marker not in MARKERS:
        return None
    file: str | None
    line: int | None
    if location in NO_LOCATION:
        file, line = None, None
    elif found := _FILE_LINE.fullmatch(location):
        file, line = found.group(1), int(found.group(2))
    else:
        file, line = location, None
    return ItemLine(fields[0], fields[1], status == "held", marker, file, line, reach)


def item_link(item: ItemLine) -> str | None:
    """The item's address in JobHunt at the pinned commit, or None with no file (AC-34 to 36)."""
    if item.file is None:
        return None
    base = f"{JOBHUNT_REPO_URL}/blob/{JOBHUNT_COMMIT}/{DOCS_PREFIX}{quote(item.file)}"
    return base if item.line is None else f"{base}?plain=1#L{item.line}"


def is_pinned_commit(commit: str) -> bool:
    """Whether a record's stored commit names the pinned commit, in full or short (AC-7)."""
    return len(commit) >= SHORT_COMMIT and JOBHUNT_COMMIT.startswith(commit)
