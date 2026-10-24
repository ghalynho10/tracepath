"""The gallery page as one self contained HTML string (spec 0010). Pure.

Every stored text is escaped, so markup in a record shows as text (AC-24). The page
has inline styles only and refers to no other file of the site (AC-58).
"""

from collections.abc import Mapping
from datetime import UTC
from html import escape
from urllib.parse import quote

from tracepath.ask.answer import claim_marks
from tracepath.gallery.citations import (
    JOBHUNT_COMMIT,
    JOBHUNT_REPO_URL,
    SHORT_COMMIT,
    ItemLine,
    item_link,
)
from tracepath.gallery.records import Entry, Section, StoredClaim

#: This repository on GitHub; each marks entry links back to the file it was copied from.
TRACEPATH_REPO_URL = "https://github.com/ghalynho10/tracepath"

#: The records folder on GitHub (AC-50).
ASKS_URL = f"{TRACEPATH_REPO_URL}/tree/main/artifacts/asks"

#: JobHunt's tree at the pinned commit (AC-54).
JOBHUNT_TREE_URL = f"{JOBHUNT_REPO_URL}/tree/{JOBHUNT_COMMIT}"

#: Where the `ask-1` marks of eval questions 1 to 5 are recorded (AC-52).
SCOPE_URL = f"{TRACEPATH_REPO_URL}/blob/main/docs/scope/scope.md"

#: Where experiment 0018 records how its questions were set and run (AC-53).
EXPERIMENT_0018_URL = (
    f"{TRACEPATH_REPO_URL}/blob/main/experiments/0018-realistic-usage-questions/README.md"
)

#: Which questions the page shows (AC-51). The marks file is the list; this says it in words.
SHOWN_SET = "eval questions 1 to 5, held out questions 1 to 4, and experiment 0018's 22."

#: The line the development section carries (AC-52), checked against `docs/scope/scope.md`
#: line 238 and the v1 finish line on 2026-10-24.
ASK_1_LINE = (
    "Shown here are the prompt ask-2 runs at 2 hops. Earlier runs of eval questions 1 to 5 "
    "on prompt ask-1, from 2026-10-19: I also marked them right"
)

#: The line the held out section carries (AC-8).
HELD_OUT_LINE = "Asked once at the end of v1, never used to tune the tool."

#: What each of the engineer's marks means, in the engineer's words (spec 0010 Follow-up).
MARK_KEY = (
    ("right", "Answers the question with the points it needs, even if it leaves out some detail."),
    (
        "partly right",
        "Right as far as it goes, but misses a point the question needs, such as the reason "
        "for a choice.",
    ),
    (
        "wrong",
        "Fails to answer a question the records do answer, for example by saying no record "
        "supports it.",
    ),
    (
        "declined",
        "For a question the records don't cover: says no record supports an answer, and "
        "invents nothing.",
    ),
)

#: What each label code set on a claim at ask time means (spec 0009 AC-16 to AC-20),
#: in the wording the engineer settled on 2026-10-24.
LABEL_KEY = (
    ("held", "After a cited id: that item was held for review when the graph was built."),
    ("HISTORY", "The claim cites an item that is struck, or replaced by a later one."),
    (
        "INFERRED",
        "The claim is the model's own connection between items: either the model said so, "
        "or it said link and code found no sent link joining its items.",
    ),
    (
        "CITATION REJECTED",
        "The claim cited an id that was not among the items sent, so code rejected it.",
    ),
    ("UNCITED", "The claim cites no item."),
    ("unsupported", "Every id the claim cites was rejected."),
    (
        "link",
        "Code found that each item the claim cites is joined to another cited item by a sent link.",
    ),
    ("read from text", "The claim is read from the text of the items it cites."),
    (
        "N of M claims failed a check",
        "After the model's verdict: a claim failed when an id it cites was rejected, when it "
        "cites none, or when the model claimed a link that code did not find. A claim the "
        "model itself marked inferred does not count as failed.",
    ),
)

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


def _link(item: ItemLine) -> str:
    """The item's location, linked when it has a file (AC-34 to AC-36, AC-48)."""
    link = item_link(item)
    if link is None or item.file is None:
        return "no file stored"
    shown = item.file if item.line is None else f"{item.file}:{item.line}"
    whole = ", whole file" if item.line is None else ""
    return f'<a href="{escape(link)}">{escape(shown)}{whole}</a>'


def _citation(claim: StoredClaim, cited: str, items: Mapping[str, ItemLine]) -> str:
    """One cited id: linked, `held` after it when held, never linked when rejected."""
    if cited in claim.rejected_ids:
        return escape(cited)
    item = items[cited]
    whole = ", whole file" if item.line is None else ""
    held = " held" if cited in claim.held_ids else ""
    return f'<a href="{escape(item_link(item) or "")}">{escape(cited)}{whole}</a>{held}'


def _claim(claim: StoredClaim, items: Mapping[str, ItemLine]) -> str:
    cited = tuple(dict.fromkeys(claim.cites))
    cites = (
        '<p class="cites">Cites: ' + ", ".join(_citation(claim, c, items) for c in cited) + "</p>"
        if cited
        else ""
    )
    labels = " ".join(escape(label) for label in claim_marks(claim.checked()))
    return f'<li>{_text(claim.text)}{cites}<p class="labels">{labels}</p></li>'


def _claims(entry: Entry) -> str:
    items = {item.id: item for item in entry.items}
    rows = "".join(_claim(claim, items) for claim in entry.record.claims)
    return f"<ol>{rows}</ol>" if rows else "<p>No claims.</p>"


def _verdict(entry: Entry) -> str:
    """The model's verdict, and how many claims failed a check when any did (AC-33)."""
    claims = entry.record.claims
    failed = sum(1 for claim in claims if claim.checked().failed)
    tally = f"; {failed} of {len(claims)} claims failed a check" if failed else ""
    return f"<p>Model's own verdict: {_text(entry.record.verdict)}{tally}</p>"


def _details(entry: Entry) -> str:
    """The date asked, the prompt version, and the hops when stored (AC-21 to AC-23)."""
    record = entry.record
    parts = [
        f"Asked {record.asked_at.astimezone(UTC).date().isoformat()}",
        f"prompt {escape(record.prompt_version)}",
    ]
    if record.hops is not None:
        parts.append(f"{record.hops} hops")
    return f'<p class="details">{" · ".join(parts)}</p>'


def _missing(entry: Entry) -> str:
    """What the answer says is missing, when it says anything (AC-20)."""
    missing = entry.record.missing
    if not missing:
        return ""
    rows = "".join(f"<li>{_text(m)}</li>" for m in missing)
    return f"<p>Missing, as the answer says:</p><ul>{rows}</ul>"


def _item_head(item: ItemLine) -> str:
    """An item's id, type, held or accepted, its marker, and its location."""
    parts = [escape(item.id), escape(item.type), "held" if item.held else "accepted"]
    if item.marker is not None:
        parts.append(item.marker)
    return " · ".join([*parts, _link(item)])


def _items_sent(entry: Entry) -> str:
    """The pack sent, closed until opened: cited items in full, others one row each."""
    cited = {c for claim in entry.record.claims for c in claim.cites if c not in claim.rejected_ids}
    lines = dict(zip((item.id for item in entry.record.items), entry.items, strict=True))
    shown = "".join(
        f'<div class="item"><p>{_item_head(lines[item.id])}</p>{_text(item.text)}</div>'
        for item in entry.record.items
        if item.id in cited
    )
    rows = "".join(f"<li>{_item_head(line)}</li>" for line in entry.items if line.id not in cited)
    return (
        f"<details><summary>Items sent ({len(entry.items)}, {len(cited)} cited)</summary>"
        f"<h4>Cited</h4>{shown or '<p>None.</p>'}"
        f"<h4>Not cited</h4>{f'<ul>{rows}</ul>' if rows else '<p>None.</p>'}"
        "</details>"
    )


def _mark(entry: Entry) -> str:
    """The engineer's mark, note and where both were copied from (AC-12 to AC-16)."""
    marks = entry.marks
    note = "" if marks.note is None else f'<p class="note">{_text(marks.note)}</p>'
    source = f"{TRACEPATH_REPO_URL}/blob/main/{quote(marks.source_path)}"
    return (
        f'<p class="mark">My mark: {_text(marks.mark)}</p>'
        f"{note}"
        f'<p class="source">From <a href="{escape(source)}">{escape(marks.source_path)}</a>, '
        f"{_text(marks.source_row)}</p>"
    )


def _entry(entry: Entry) -> str:
    return (
        "<article>"
        f"<h3>{_text(entry.marks.label)}</h3>"
        f'<p class="question">{_text(entry.record.question)}</p>'
        f"{_details(entry)}"
        f"{_verdict(entry)}"
        f"{_mark(entry)}"
        f"{_claims(entry)}"
        f"{_missing(entry)}"
        f"{_items_sent(entry)}"
        "</article>"
    )


def _section_line(section: Section) -> str:
    """The statement under a section's heading (AC-8, AC-52, AC-53)."""
    match section:
        case Section.DEVELOPMENT:
            return (
                f'<p>{escape(ASK_1_LINE)} (<a href="{escape(SCOPE_URL)}">v1 finish line</a>).</p>'
            )
        case Section.HELD_OUT:
            return f"<p>{escape(HELD_OUT_LINE)}</p>"
        case Section.REALISTIC:
            return (
                "<p>How these questions were set and run, and what was noted about them, is "
                f'recorded in <a href="{escape(EXPERIMENT_0018_URL)}">experiment 0018\'s '
                "README</a>.</p>"
            )


def _section(section: Section, entries: tuple[Entry, ...]) -> str:
    shown = "".join(_entry(entry) for entry in entries if entry.section is section)
    if not shown:
        return ""
    return f"<section><h2>{escape(section.value)}</h2>{_section_line(section)}{shown}</section>"


def _intro(shown: int, records: int) -> str:
    """What the page is, what it shows of the records, and where citations point (AC-49 to 54)."""
    return (
        "<p>Answers recorded by <code>tracepath ask</code>, a terminal tool that answers "
        "&quot;why was this built this way?&quot; from a project's decision records, each "
        "with my own mark.</p>"
        f'<p>Every citation points into <a href="{escape(JOBHUNT_REPO_URL)}">JobHunt</a> '
        f'at commit <a href="{escape(JOBHUNT_TREE_URL)}">{JOBHUNT_COMMIT[:SHORT_COMMIT]}</a> '
        "and opens the line it cites.</p>"
        f'<p><a href="{escape(ASKS_URL)}">artifacts/asks/</a> holds {records} records. '
        f"This page shows {shown} of them: {escape(SHOWN_SET)}</p>"
    )


def _key_list(rows: tuple[tuple[str, str], ...]) -> str:
    return "<dl>" + "".join(f"<dt>{escape(t)}</dt><dd>{escape(d)}</dd>" for t, d in rows) + "</dl>"


def _key() -> str:
    """What the engineer's marks and the claim labels mean."""
    return (
        '<section class="key"><h2>Key</h2>'
        f"<h3>My marks</h3>{_key_list(MARK_KEY)}"
        f"<h3>Labels on a claim</h3>{_key_list(LABEL_KEY)}"
        "</section>"
    )


def render_page(entries: tuple[Entry, ...], records: int) -> str:
    """The whole page: each section in turn, its entries in marks file order (AC-1 to AC-4).

    `records` is how many records `artifacts/asks/` holds, counted by the build (AC-49).
    """
    body = "".join(_section(section, entries) for section in Section)
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>tracepath answer gallery</title>"
        f"<style>{STYLE}</style></head>"
        f"<body><h1>tracepath answer gallery</h1>{_intro(len(entries), records)}{_key()}"
        f"{body}</body></html>\n"
    )
