"""Locating a span back in its own unit, so a citation can carry a line (AC-4).

A verbatim id is located at its definition line. Every other span is aligned against
the unit's text deterministically, because the model drops rationale clauses mid
sentence and so a span is often not a verbatim substring of the source. Alignment
below the threshold returns nothing, and `line` stays null rather than guessed.

No embedding or vector search is used on purpose: near identical criterion wording
recurs across this corpus, so a nearest neighbour hit would return a confident wrong
line, which is worse than null.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from tracepath.extract.units import Unit

#: The lowest alignment score that counts as located, fixed by measurement over the
#: pinned snapshot rather than picked. Measured across the corpus's 316 real acceptance
#: criteria, mutated the way extraction mutates them (a rationale clause dropped,
#: wrapping collapsed, inline markup stripped), each scored against its own unit and
#: against the 20 other `Requirements` sections, which are the most confusable
#: documents here. Together with `MINIMUM_ANCHOR` this locates 99.4% of genuine spans
#: and returns the true line for 99.4% of those, while no wrong unit reached it at all
#: (the closest scored 0.954). Raising it further only turns genuine spans into nulls,
#: so this is the point where locating more and locating wrongly stop trading off.
ALIGNMENT_THRESHOLD = 0.96

#: The shortest contiguous run of characters that may anchor a span. This, not the
#: score, is the first line of defence: on the measurement above it rejected roughly
#: 97% of wrong unit pairings outright, before any score was computed. Coverage alone
#: cannot do that job, because a long document contains most short character
#: subsequences of anything in order (a wrong unit reached 0.990 without this floor).
MINIMUM_ANCHOR = 24


@dataclass(frozen=True)
class Location:
    """Where a span was found in its unit, and how confidently."""

    offset: int
    line: int
    score: float
    method: str


def _definition_pattern(entity_id: str) -> re.Pattern[str]:
    """The bullet that defines a verbatim id, e.g. `- **AC-10b**:`."""
    token = re.escape(entity_id)
    return re.compile(rf"^[ \t]*[-*][ \t]+\**{token}\**[ \t]*:", re.MULTILINE)


def _line_of(text: str, offset: int) -> int:
    """The 1-based line number an offset falls on."""
    return text.count("\n", 0, offset) + 1


def locate_verbatim(unit: Unit, entity_id: str) -> Location | None:
    """The definition line of a verbatim id inside its unit, or `None` if it has none."""
    match = _definition_pattern(entity_id).search(unit.text)
    if match is None:
        return None
    return Location(
        offset=match.start(),
        line=_line_of(unit.text, match.start()),
        score=1.0,
        method="definition",
    )


def align(source: str, span: str) -> tuple[int, float] | None:
    """Align a span against a source text deterministically.

    Returns the span's start offset in the source and a score between 0 and 1, the
    fraction of the span found in the source in order. Returns `None` when no anchor
    long enough to trust was found.
    """
    if not span.strip() or not source:
        return None
    matcher = SequenceMatcher(None, source, span, autojunk=False)
    blocks = [block for block in matcher.get_matching_blocks() if block.size > 0]
    if not blocks:
        return None
    longest = max(blocks, key=lambda block: block.size)
    if longest.size < min(MINIMUM_ANCHOR, len(span)):
        return None
    covered = sum(block.size for block in blocks)
    score = covered / len(span)
    # Anchor on the longest run, then step back by how far into the span that run
    # sits, which is where the span itself begins. Reporting the run's own position
    # instead would land a line low whenever the span opens with markup extraction
    # strips, and a criterion here usually opens with bold or a code span.
    return max(0, longest.a - longest.b), min(score, 1.0)


def locate_line(unit: Unit, span: str) -> Location | None:
    """Locate a span in its unit: exact match first, then alignment above the threshold.

    Returns `None` when nothing scores above `ALIGNMENT_THRESHOLD`, so the citation's
    `line` is null rather than approximated.
    """
    exact = unit.text.find(span)
    if exact != -1:
        return Location(offset=exact, line=_line_of(unit.text, exact), score=1.0, method="exact")
    aligned = align(unit.text, span)
    if aligned is None:
        return None
    offset, score = aligned
    if score < ALIGNMENT_THRESHOLD:
        return None
    return Location(offset=offset, line=_line_of(unit.text, offset), score=score, method="aligned")
