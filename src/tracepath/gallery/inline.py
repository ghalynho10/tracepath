"""Inline `code` and **bold** in stored text, read as runs (spec 0012). Pure.

The rule works one line at a time: code spans first, then `**` pairs outside them. A
marker with no partner is shown as typed, and nothing else of markdown is read. The
stored text is never changed; `to_html` escapes every run where it writes it (AC-10).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from html import escape
from itertools import groupby

#: A run of backticks; only a run of exactly one is a marker (AC-7).
_TICKS = re.compile(r"`+")

#: A bold marker; a single `*` is not one (AC-8).
_BOLD = re.compile(r"\*\*")

#: Code looking words, tried together in this order at each place, leftmost first
#: (spec 0012, Feature design, "Code words").
_CODE_WORD = re.compile(
    r"(?<![\w/.$-])\w[\w.-]*(?:/[\w.()-]+)*"
    r"\.(?:tsx?|jsx?|mjs|json|md|py|css|sql|ya?ml|html|sh|toml)\b"
    r"|\$[A-Za-z_][A-Za-z0-9_]*(?::\d+)*"
    r"|\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b"
    r"|\b[A-Za-z_][A-Za-z0-9_.]*\(\)"
    r"|\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"
)

#: Product names the file name pattern would otherwise take (AC-25).
PRODUCT_NAMES = frozenset({"Next.js", "Node.js"})

#: The spaces between the words of a code run, kept as text between them (AC-96).
_SPACES = re.compile(r"( +)")

#: Whitespace in plain text: where a line may break beside a code run.
_GAPS = re.compile(r"(\s+)")


@dataclass(frozen=True)
class Run:
    """A piece of stored text with its code and bold flags."""

    text: str
    code: bool
    bold: bool


def _code_spans(line: str) -> tuple[tuple[int, int], ...]:
    """Each code span's start and end, backticks included.

    A single backtick opens and the next single backtick on the line closes (AC-1, AC-7).
    """
    singles = [m.start() for m in _TICKS.finditer(line) if m.end() - m.start() == 1]
    return tuple((singles[n], singles[n + 1] + 1) for n in range(0, len(singles) - 1, 2))


def _plain(text: str, bold: bool, code_words: bool) -> tuple[Run, ...]:
    """Text outside any code span, with its code looking words made code when asked."""
    if not code_words:
        return (Run(text, code=False, bold=bold),) if text else ()
    found: list[Run] = []
    at = 0
    for match in _CODE_WORD.finditer(text):
        if match.group() in PRODUCT_NAMES:
            continue
        if match.start() > at:
            found.append(Run(text[at : match.start()], code=False, bold=bold))
        found.append(Run(match.group(), code=True, bold=bold))
        at = match.end()
    if at < len(text):
        found.append(Run(text[at:], code=False, bold=bold))
    return tuple(found)


def _line(line: str, code_words: bool) -> tuple[Run, ...]:
    """One line's runs: code spans first, then `**` pairs outside them (AC-2 to AC-5)."""
    spans = _code_spans(line)
    # The pieces between code spans, and each code span's inner text.
    pieces: list[tuple[str, bool]] = []
    at = 0
    for start, end in spans:
        pieces.append((line[at:start], False))
        pieces.append((line[start + 1 : end - 1], True))
        at = end
    pieces.append((line[at:], False))
    # Every `**` outside code, as (piece, offset); paired first with second, and so on.
    markers = [
        (number, m.start())
        for number, (text, code) in enumerate(pieces)
        if not code
        for m in _BOLD.finditer(text)
    ]
    pairs = [
        (markers[n], markers[n + 1])
        for n in range(0, len(markers) - 1, 2)
        if _between(markers[n], markers[n + 1])
    ]
    cuts = {marker for pair in pairs for marker in pair}
    runs: list[Run] = []
    bold = False
    for number, (text, code) in enumerate(pieces):
        if code:
            runs.append(Run(text, code=True, bold=bold))
            continue
        at = 0
        for marker in sorted(offset for piece, offset in cuts if piece == number):
            runs.extend(_plain(text[at:marker], bold, code_words))
            bold = not bold
            at = marker + 2
        runs.extend(_plain(text[at:], bold, code_words))
    return tuple(runs)


def _between(first: tuple[int, int], second: tuple[int, int]) -> bool:
    """Whether at least one character sits between two `**` markers (AC-2).

    Markers in different pieces have a code span between them, never empty.
    """
    (start, start_at), (end, end_at) = first, second
    return start != end or end_at > start_at + 2


def _merged(runs: tuple[Run, ...]) -> tuple[Run, ...]:
    """Neighbouring plain runs of one boldness joined; code runs kept apart."""
    out: list[Run] = []
    for run in runs:
        last = out[-1] if out else None
        if last is not None and not last.code and not run.code and last.bold == run.bold:
            out[-1] = Run(last.text + run.text, code=False, bold=run.bold)
        else:
            out.append(run)
    return tuple(out)


def runs(text: str, code_words: bool = False) -> tuple[Run, ...]:
    """The stored text as runs; a pair never reaches across a line break (AC-6).

    `code_words` makes code looking words outside code spans code too, for a question,
    a claim and a missing note only (AC-20 to AC-29).
    """
    lines = text.split("\n")
    found: list[Run] = []
    for number, line in enumerate(lines):
        if number:
            found.append(Run("\n", code=False, bold=False))
        found.extend(_line(line, code_words))
    return _merged(tuple(found))


def has_pair(found: tuple[Run, ...]) -> bool:
    """Whether any run is code or bold, that is, the text held a marker pair."""
    return any(run.code or run.bold for run in found)


def _code(text: str) -> str:
    """A code run: one `w` element per word, the spaces between them kept as text (AC-11)."""
    words = (
        piece if index % 2 else f'<span class="w">{escape(piece)}</span>'
        for index, piece in enumerate(_SPACES.split(text))
        if piece
    )
    return f"<code>{''.join(words)}</code>"


def _glued(group: Iterable[Run]) -> str:
    """Runs of one boldness as HTML, a code run kept on one line with the text it touches.

    A code run and the text next to it with no space between, such as `(` before it or
    `),` after it, sit in one `g` element, which may break only between the code's own
    words, so a line never ends on `(` alone (spec 0012 AC-12).
    """
    atoms: list[tuple[str, bool | None]] = []  # code True, text False, a gap None
    for run in group:
        if run.code:
            atoms.append((_code(run.text), True))
            continue
        for index, piece in enumerate(_GAPS.split(run.text)):
            if piece:
                atoms.append((escape(piece), None if index % 2 else False))
    out: list[str] = []
    cluster: list[tuple[str, bool | None]] = []
    for shown, kind in [*atoms, ("", None)]:
        if kind is not None:
            cluster.append((shown, kind))
            continue
        joined = "".join(part for part, _ in cluster)
        glue = len(cluster) > 1 and any(code for _, code in cluster)
        out.append(f'<span class="g">{joined}</span>' if glue else joined)
        out.append(shown)
        cluster = []
    return "".join(out)


def to_html(found: tuple[Run, ...]) -> str:
    """The runs as HTML, every run's text escaped where it is written (AC-10)."""
    parts = []
    for bold, group in groupby(found, key=lambda run: run.bold):
        inner = _glued(group)
        parts.append(f"<strong>{inner}</strong>" if bold else inner)
    return "".join(parts)
