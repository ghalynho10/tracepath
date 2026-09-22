"""The deterministic pre-check, run over a unit before any model call.

Struck text and checkbox state are read here, from the characters themselves, so
whether something is struck or done never depends on the model noticing it
(AC-5, AC-6).
"""

import re
from dataclasses import dataclass

from tracepath.extract.schema import FollowUpStatus

#: A struck span, `~~like this~~`. It may run across lines, so the dot matches newlines.
STRUCK = re.compile(r"~~(.+?)~~", re.DOTALL)

#: A checkbox item, `- [x]` or `- [ ]`, at the start of a line and possibly indented.
CHECKBOX = re.compile(r"^(\s*)[-*] \[([ xX])\]\s?", re.MULTILINE)

#: A fenced code block. Its contents are text, not markup.
FENCED_BLOCK = re.compile(r"^(\s*)(```|~~~).*?^\1\2.*?$", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class StruckRange:
    """One `~~struck~~` span, located by character offset inside the unit's text."""

    start: int
    end: int
    text: str

    def contains(self, offset: int) -> bool:
        """True when an offset falls inside this struck span."""
        return self.start <= offset < self.end


@dataclass(frozen=True)
class CheckboxItem:
    """One checkbox item, its state and the stretch of text it governs."""

    start: int
    end: int
    status: FollowUpStatus

    def contains(self, offset: int) -> bool:
        """True when an offset falls inside this item."""
        return self.start <= offset < self.end


def _mask_fenced_blocks(text: str) -> str:
    """Blank out fenced code, keeping every offset, so markup inside it is not read."""
    masked = list(text)
    for match in FENCED_BLOCK.finditer(text):
        for index in range(match.start(), match.end()):
            if masked[index] != "\n":
                masked[index] = " "
    return "".join(masked)


def mark_struck(text: str) -> tuple[StruckRange, ...]:
    """The character ranges of every struck span in a unit, in file order.

    A unit with no struck text returns an empty tuple.
    """
    scanned = _mask_fenced_blocks(text)
    return tuple(
        StruckRange(start=match.start(), end=match.end(), text=match.group(1))
        for match in STRUCK.finditer(scanned)
    )


def is_struck(ranges: tuple[StruckRange, ...], offset: int | None) -> bool:
    """True when a located offset falls inside any struck range.

    An offset of `None` (a span code could not locate) is never struck, because
    `struck` is set from the characters and is never guessed.
    """
    if offset is None:
        return False
    return any(struck.contains(offset) for struck in ranges)


def read_checkboxes(text: str) -> tuple[CheckboxItem, ...]:
    """Every checkbox item in a unit, each with the stretch of text it governs.

    An item runs from its own marker to the start of the next one, or to the end of
    the unit. A unit with no checkbox returns an empty tuple.
    """
    scanned = _mask_fenced_blocks(text)
    matches = list(CHECKBOX.finditer(scanned))
    items: list[CheckboxItem] = []
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        status = FollowUpStatus.DONE if match.group(2).lower() == "x" else FollowUpStatus.OPEN
        items.append(CheckboxItem(start=match.start(), end=end, status=status))
    return tuple(items)


def read_checkbox(text: str) -> FollowUpStatus | None:
    """The state of the first checkbox in a stretch of text, or `None` when it has none."""
    items = read_checkboxes(text)
    return items[0].status if items else None


def checkbox_status_at(
    items: tuple[CheckboxItem, ...], offset: int | None
) -> FollowUpStatus | None:
    """The state of the checkbox item a located offset falls inside, else `None`."""
    if offset is None:
        return None
    for item in items:
        if item.contains(offset):
            return item.status
    return None
