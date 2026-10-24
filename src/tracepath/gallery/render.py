"""The gallery page as one self contained HTML string (spec 0010). Pure.

Every stored text is escaped, so markup in a record shows as text (AC-24). The page
has inline styles only and refers to no other file of the site (AC-58).
"""

from html import escape
from urllib.parse import quote

from tracepath.gallery.records import Entry, Section

#: This repository on GitHub; each marks entry links back to the file it was copied from.
TRACEPATH_REPO_URL = "https://github.com/ghalynho10/tracepath"

#: The line the held out section carries (AC-8).
HELD_OUT_LINE = "Asked once at the end of v1, never used to tune the tool."

#: The page's styles, inline. The visual pass (task 8) replaces these.
STYLE = """\
body { font-family: system-ui, sans-serif; max-width: 46rem; margin: 2rem auto;
  padding: 0 1rem; line-height: 1.5; color: #111; background: #fff; }
article { border-top: 1px solid #ccc; padding: 1rem 0; }
.stored { white-space: pre-wrap; }
"""


def _text(value: str) -> str:
    """Stored text, escaped, with its line breaks kept by the `stored` class (AC-25)."""
    return f'<span class="stored">{escape(value)}</span>'


def _claims(entry: Entry) -> str:
    rows = "".join(f"<li>{_text(claim.text)}</li>" for claim in entry.record.claims)
    return f"<ol>{rows}</ol>" if rows else "<p>No claims.</p>"


def _mark(entry: Entry) -> str:
    """The engineer's mark, note and where both were copied from (AC-12 to AC-16)."""
    marks = entry.marks
    note = "" if marks.note is None else f'<p class="note">{_text(marks.note)}</p>'
    source = f"{TRACEPATH_REPO_URL}/blob/main/{quote(marks.source_path)}"
    return (
        f'<p class="mark">Engineer\'s mark: {_text(marks.mark)}</p>'
        f"{note}"
        f'<p class="source">From <a href="{escape(source)}">{escape(marks.source_path)}</a>, '
        f"{_text(marks.source_row)}</p>"
    )


def _entry(entry: Entry) -> str:
    record = entry.record
    return (
        "<article>"
        f"<h3>{_text(entry.marks.label)}</h3>"
        f'<p class="question">{_text(record.question)}</p>'
        f"<p>Model's own verdict: {_text(record.verdict)}</p>"
        f"{_mark(entry)}"
        f"{_claims(entry)}"
        "</article>"
    )


def _section(section: Section, entries: tuple[Entry, ...]) -> str:
    shown = "".join(_entry(entry) for entry in entries if entry.section is section)
    if not shown:
        return ""
    line = f"<p>{escape(HELD_OUT_LINE)}</p>" if section is Section.HELD_OUT else ""
    return f"<section><h2>{escape(section.value)}</h2>{line}{shown}</section>"


def render_page(entries: tuple[Entry, ...]) -> str:
    """The whole page: each section in turn, its entries in marks file order (AC-1 to AC-4)."""
    body = "".join(_section(section, entries) for section in Section)
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>tracepath answer gallery</title>"
        f"<style>{STYLE}</style></head>"
        f"<body><h1>tracepath answer gallery</h1>{body}</body></html>\n"
    )
