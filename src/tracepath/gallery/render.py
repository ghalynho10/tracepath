"""The gallery page as one self contained HTML string (spec 0010). Pure.

Every stored text is escaped, so markup in a record shows as text (AC-24). The page
has inline styles only and refers to no other file of the site (AC-58).
"""

from html import escape

from tracepath.gallery.records import Entry

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


def _entry(entry: Entry) -> str:
    record = entry.record
    return (
        "<article>"
        f"<h2>{_text(record.question)}</h2>"
        f"<p>Model's verdict: {_text(record.verdict)}</p>"
        f"{_claims(entry)}"
        "</article>"
    )


def render_page(entries: tuple[Entry, ...]) -> str:
    """The whole page for these entries, in their order (AC-1, AC-17 to AC-19)."""
    body = "".join(_entry(entry) for entry in entries)
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>tracepath answer gallery</title>"
        f"<style>{STYLE}</style></head>"
        f"<body><h1>tracepath answer gallery</h1>{body}</body></html>\n"
    )
