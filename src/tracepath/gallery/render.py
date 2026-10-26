"""The gallery page as one self contained HTML string (specs 0010, 0011 and 0012). Pure.

Every stored text is escaped, so markup in a record shows as text (AC-24); inline code
and bold are drawn from runs, each run escaped where it is written (spec 0012 AC-10).
The page has inline styles and scripts only and refers to no other file of the site
(AC-58, spec 0011 AC-74).
"""

import math
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
from tracepath.gallery.graph import (
    CITED_RADIUS,
    HELD_GAP,
    OTHER_RADIUS,
    RING_GAP,
    EntryGraph,
    data_block,
)
from tracepath.gallery.inline import runs, to_html
from tracepath.gallery.records import Entry, PageScripts, Section, StoredClaim

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

#: The page's styles, inline (AC-58), chosen in task 8 on 2026-10-24: flat paper and
#: hairlines, a large label over quiet body text, the portfolio's navy ink, and its
#: colours only as small accents. The mark is a filled pill and the note a solid bubble,
#: so the author's voice reads apart from the model's outlined verdict (AC-14).
STYLE = """\
:root { --paper: #FFFFFF; --ink: #011936; --ink-82: rgba(1, 25, 54, .82);
  --ink-64: #3F5877; --ink-46: rgba(63, 88, 119, .78);
  --rule: rgba(1, 25, 54, .14); --rule-strong: rgba(1, 25, 54, .30);
  --cyan: #07A0C3; --yellow: #F6E27F; --pink: #FFC8C2;
  --sans: "Helvetica Neue", Helvetica, Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink);
  font: 16px/1.55 var(--sans); }
main { max-width: 44rem; margin: 0 auto; padding: 48px 16px 72px; }
.stored { white-space: pre-wrap; }
a { color: inherit; text-decoration-color: var(--cyan); text-underline-offset: 3px;
  text-decoration-thickness: 1px; }
a:hover { color: var(--cyan); }
code { font-family: var(--mono); font-size: .9em; }
code .w { display: inline-block; max-width: 100%; overflow-wrap: anywhere; }
h1 { font-size: clamp(36px, 8vw, 48px); line-height: 1; font-weight: 700;
  letter-spacing: -.03em; margin: 0 0 20px; }
.intro { max-width: 36rem; color: var(--ink-82); }
.intro p { margin: 0 0 10px; }
section { margin-top: 48px; }
section > h2 { font-size: 11px; line-height: 1; font-weight: 700; letter-spacing: .2em;
  text-transform: uppercase; color: var(--ink-64); margin: 0; padding-bottom: 14px;
  border-bottom: 1px solid var(--rule); }
section > h2 + p { margin: 14px 0 0; max-width: 36rem; font-size: 14px; color: var(--ink-64); }
.key h3 { font-size: 10px; line-height: 1; font-weight: 700; letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-64); margin: 24px 0 10px; }
.key dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 10px 16px;
  align-items: baseline; font-size: 14px; }
.key dt { font: 12px/1.5 var(--mono); max-width: 10rem; }
.key dt.mark { font: 500 13px/1.5 var(--sans); margin: 0; justify-self: start; }
.key dd { margin: 0; color: var(--ink-82); }
@media (max-width: 480px) {
  .key dl { grid-template-columns: 1fr; gap: 4px; }
  .key dt { max-width: none; }
  .key dd { margin-bottom: 12px; }
}
article { padding: 28px 0 32px; border-bottom: 1px solid var(--rule); }
article > h3 { font-size: clamp(44px, 11vw, 62px); line-height: .94; font-weight: 700;
  letter-spacing: -.035em; margin: 0 0 18px; }
.question { font-size: 20px; line-height: 1.4; margin: 0 0 10px; max-width: 36rem; }
.details { font: 500 11px/1.4 var(--mono); letter-spacing: .06em;
  color: var(--ink-46); margin: 0 0 22px; }
.verdict, .mark { display: inline-flex; gap: .4em; align-items: baseline; margin: 0 8px 8px 0;
  padding: 4px 13px; border-radius: 999px; font-size: 13px; line-height: 1.5; }
.verdict { border: 1px solid var(--rule-strong); color: var(--ink-82); }
.mark { border: 1px solid var(--ink); color: var(--ink); font-weight: 500; }
.mark[data-mark="right"] { background: rgba(7, 160, 195, .18); }
.mark[data-mark="partly right"] { background: var(--yellow); }
.mark[data-mark="wrong"] { background: var(--pink); }
.mark[data-mark="declined"] { background: rgba(1, 25, 54, .06); }
.note { margin: 6px 0; max-width: 30rem; padding: 10px 14px; font-size: 14.7px; line-height: 1.5;
  border-radius: 13.6px 13.6px 13.6px 1.6px; background: var(--ink); color: var(--paper); }
.source { margin: 4px 0 0; font-size: 12px; color: var(--ink-46); }
article ol, .gw-answer ol { list-style: none; counter-reset: claim; padding: 0; margin: 26px 0 0;
  border-top: 1px solid var(--rule); }
article ol > li, .gw-answer ol > li { position: relative; counter-increment: claim;
  padding: 16px 0 16px 2.4em; border-bottom: 1px solid var(--rule); }
article ol > li::before, .gw-answer ol > li::before {
  content: counter(claim, decimal-leading-zero); position: absolute; left: 0; top: 20px;
  font: 11px/1 var(--mono); color: var(--ink-46); }
.cites { margin: 8px 0 0; font: 12.5px/1.6 var(--mono); color: var(--ink-64);
  overflow-wrap: anywhere; }
.labels { margin: 8px 0 0; font-size: 10px; line-height: 1.4; font-weight: 700;
  letter-spacing: .16em; color: var(--ink-64); }
.eyebrow, details > summary { margin: 22px 0 6px; font-size: 10px; line-height: 1;
  font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-64); }
article > ul { margin: 0; padding-left: 1.1em; color: var(--ink-82); }
details { margin-top: 22px; border-top: 1px solid var(--rule); padding-top: 4px; }
details > summary { cursor: pointer; list-style: none; padding: 14px 0 4px; }
details > summary::-webkit-details-marker { display: none; }
details > summary::after { content: " +"; color: var(--cyan); }
details[open] > summary::after { content: " \\2212"; }
details h4 { margin: 18px 0 8px; font-size: 10px; letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-46); }
details .item p, details li { font: 12px/1.6 var(--mono); color: var(--ink-64);
  overflow-wrap: anywhere; }
details ul { list-style: none; padding: 0; margin: 0; }
details li { padding: 4px 0; border-bottom: 1px solid var(--rule); }
details .item { padding: 6px 0 12px; border-bottom: 1px solid var(--rule); }
details .item p { margin: 0 0 4px; }
details .item > .stored { font-size: 14px; color: var(--ink-82); }
[hidden] { display: none !important; }
"""

#: The graph window's styles (spec 0011): a split window, the graph about two thirds and
#: the panel one third, with a hairline between them; at 720 pixels or less the graph
#: sits above the panel and the key folds behind a Key button (AC-54, AC-55, AC-91).
#: Cyan only rings the selection, and the marks' yellow and pink are never used here
#: (AC-22).
GRAPH_STYLE = """\
.graph-open { display: inline-flex; margin: 18px 0 0; padding: 4px 15px; border-radius: 999px;
  border: 1px solid var(--ink); background: var(--paper); color: var(--ink);
  font: 500 13px/1.5 var(--sans); cursor: pointer; }
.graph-open:hover { background: var(--ink); color: var(--paper); }
html:has(dialog.gw[open]) { overflow: hidden; }
dialog.gw { width: 100vw; height: 100vh; height: 100dvh; max-width: none; max-height: none;
  margin: 0; padding: 0; border: 0; background: var(--paper); color: var(--ink); }
dialog.gw[open] { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); }
dialog.gw::backdrop { background: var(--paper); }
.gw-stage { position: relative; display: flex; flex-direction: column; min-height: 0;
  border-right: 1px solid var(--rule); }
.gw-head { display: flex; align-items: center; gap: 8px; padding: 16px 20px; }
.gw-heading { flex: 1; margin: 0; font: 700 10px/1.2 var(--sans); letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-64); }
.gw-count { margin-left: 10px; font-family: var(--mono); color: var(--ink-46); }
.gw-button { width: 40px; height: 40px; flex: none; border-radius: 50%;
  border: 1px solid var(--rule-strong); background: var(--paper); color: var(--ink);
  font: 18px/1 var(--sans); cursor: pointer; }
.gw-button:hover { border-color: var(--ink); }
.gw-button:disabled { border-color: var(--rule); color: var(--ink-46); cursor: default; }
.gw-button:focus-visible, .graph-open:focus-visible { outline: 2px solid var(--ink);
  outline-offset: 2px; }
.gw-view { position: relative; flex: 1; min-height: 0; }
.gw-canvas { position: absolute; inset: 0; display: block; width: 100%; height: 100%;
  touch-action: none; user-select: none; cursor: grab; }
.gw-canvas.is-dragging, .gw-canvas.is-dragging .gw-node { cursor: grabbing; }
.gw-zoom { position: absolute; right: 20px; bottom: 16px; display: flex; gap: 8px; }
.gw-link { stroke: var(--ink); stroke-opacity: .3; stroke-width: 1; }
.gw-link.is-held { stroke-opacity: .5; stroke-dasharray: 4 3; }
.gw-link.is-active { stroke-opacity: 1; }
.gw-arrow { fill: var(--ink); }
.gw-dot { fill: var(--ink); }
.is-other > .gw-dot { fill-opacity: .5; }
.gw-held { fill: none; stroke: var(--ink); stroke-width: 1; stroke-dasharray: 2 2; }
.gw-ring { fill: none; stroke: var(--cyan); stroke-width: 2; }
.gw-node:not(.is-selected) > .gw-ring { display: none; }
.gw-label { font: 500 9.5px/1 var(--mono); fill: var(--ink); stroke: var(--paper);
  stroke-width: 3px; paint-order: stroke; pointer-events: none; }
.gw-node.is-other > .gw-label { display: none; }
.gw-node.is-other:is(.is-hover, .is-selected, .is-near) > .gw-label { display: inline; }
.gw-node.is-cited.is-crowded:not(.is-hover, .is-selected, .is-near) > .gw-label {
  display: none; }
.gw-canvas.is-reach { cursor: pointer; }
.gw-node, .gw-link { transition: opacity .2s; }
.gw-canvas .is-dim { opacity: .2; }
.gw-canvas .is-out { display: none; }
@media (prefers-reduced-motion: reduce) { .gw-node, .gw-link { transition: none; } }
.gw-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 24px;
  padding: 12px 20px 16px; border-top: 1px solid var(--rule); font-size: 12px;
  color: var(--ink-82); }
.gw-switch { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.gw-switch input { width: 16px; height: 16px; margin: 0; accent-color: var(--ink); }
.gw-switch:has(input:disabled) { color: var(--ink-46); cursor: default; }
.gw-key { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 0; padding: 0;
  list-style: none; }
.gw-key li { display: inline-flex; align-items: center; gap: 6px; }
.gw-sample { width: 30px; height: 30px; overflow: visible; }
.gw-keytoggle { display: none; padding: 3px 12px; border-radius: 999px;
  border: 1px solid var(--rule-strong); background: var(--paper); color: var(--ink);
  font: 500 11px/1.5 var(--sans); cursor: pointer; }
.gw-keytoggle:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
.gw-empty { margin: 0; color: var(--ink-82); }
.gw-panel { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 24px; }
.gw-eyebrow { margin: 0 0 12px; font: 700 10px/1.2 var(--sans); letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-64); }
.gw-title { margin: 0 0 18px; font-size: clamp(30px, 4vw, 44px); line-height: 1;
  font-weight: 700; letter-spacing: -.03em; overflow-wrap: anywhere; }
@media (max-width: 720px) {
  dialog.gw[open] { grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr); }
  .gw-stage { border-right: 0; border-bottom: 1px solid var(--rule); }
  .gw-head { padding: 10px 16px; }
  .gw-view { flex: none; height: 45vh; height: 45dvh; }
  .gw-zoom { right: 16px; bottom: 12px; }
  .gw-foot { gap: 6px 14px; padding: 8px 16px 10px; font-size: 11px; }
  .gw-keytoggle { display: inline-flex; margin-left: auto; }
  .gw-foot:not(.is-key-open) > .gw-key { display: none; }
  .gw-panel { padding: 20px 16px 32px; }
}
"""

#: The reading panel's styles (spec 0011): quiet body text under the poster title, and
#: ids drawn as links that select their item.
PANEL_STYLE = """\
.gw-back { display: inline-flex; margin: 0 0 18px; padding: 3px 12px; border-radius: 999px;
  border: 1px solid var(--rule-strong); background: var(--paper); color: var(--ink);
  font: 500 12px/1.5 var(--sans); cursor: pointer; }
.gw-back:hover { border-color: var(--ink); }
.gw-answer .question { font-size: 17px; }
.gw-answer ol { margin-top: 18px; }
.gw-text { margin: 0 0 18px; font-size: 15px; line-height: 1.55; color: var(--ink-82); }
.gw-meta { margin: 0 0 6px; font: 12.5px/1.6 var(--mono); color: var(--ink-64);
  overflow-wrap: anywhere; }
.gw-sub { margin: 26px 0 8px; font: 700 10px/1.2 var(--sans); letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-64); }
.gw-list { margin: 0; padding: 0; list-style: none; }
.gw-list li { padding: 7px 0; border-bottom: 1px solid var(--rule); font: 12px/1.6 var(--mono);
  color: var(--ink-64); overflow-wrap: anywhere; }
.gw-phrase { display: block; margin-top: 2px; font: 13px/1.5 var(--sans); color: var(--ink-82); }
.gw-dir { display: inline-block; min-width: 2.6em; color: var(--ink-46); }
.gw-id { padding: 0; border: 0; background: none; color: var(--ink); font: inherit;
  text-align: left; text-decoration: underline; text-decoration-color: var(--cyan);
  text-underline-offset: 3px; text-decoration-thickness: 1px; cursor: pointer;
  overflow-wrap: anywhere; }
.gw-id:hover { color: var(--cyan); }
.gw-id:focus-visible, .gw-back:focus-visible { outline: 2px solid var(--ink);
  outline-offset: 2px; }
.gw-title:focus { outline: none; }
"""

#: Half the side of an unresolved name's square, which has a cited dot's area (AC-20).
_HALF = round(CITED_RADIUS * math.sqrt(math.pi) / 2, 2)


def _sample(drawing: str) -> str:
    return f'<svg class="gw-sample" viewBox="-15 -15 30 30" aria-hidden="true">{drawing}</svg>'


#: The key's six drawings, drawn outside the canvas with the canvas's own classes (AC-23).
KEY = (
    ("Cited", f'<g class="is-cited"><circle class="gw-dot" r="{CITED_RADIUS}"/></g>'),
    ("Not cited", f'<g class="is-other"><circle class="gw-dot" r="{OTHER_RADIUS}"/></g>'),
    (
        "Held item",
        f'<g class="is-other"><circle class="gw-dot" r="{OTHER_RADIUS}"/>'
        f'<circle class="gw-held" r="{OTHER_RADIUS + HELD_GAP}"/></g>',
    ),
    ("Held link", '<line class="gw-link is-held" x1="-14" y1="0" x2="14" y2="0"/>'),
    (
        "Unresolved name",
        f'<g class="is-cited"><rect class="gw-dot" x="-{_HALF}" y="-{_HALF}" '
        f'width="{2 * _HALF}" height="{2 * _HALF}"/></g>',
    ),
    (
        "Selected",
        f'<g class="is-cited"><circle class="gw-dot" r="{CITED_RADIUS}"/>'
        f'<circle class="gw-ring" r="{CITED_RADIUS + RING_GAP}"/></g>',
    ),
)

#: The one graph window, filled by the script for whichever graph is open (spec 0011).
DIALOG = (
    f'<dialog class="gw" aria-labelledby="gw-heading" data-held-gap="{HELD_GAP}" '
    f'data-ring-gap="{RING_GAP}">'
    '<div class="gw-stage"><div class="gw-head">'
    '<p class="gw-heading"><span id="gw-heading"></span> <span class="gw-count"></span></p>'
    '<button type="button" class="gw-button" data-gw="previous" aria-label="Previous graph">'
    "&larr;</button>"
    '<button type="button" class="gw-button" data-gw="next" aria-label="Next graph">'
    "&rarr;</button>"
    '<button type="button" class="gw-button" data-gw="close" aria-label="Close graph">'
    "&times;</button></div>"
    '<div class="gw-view">'
    '<svg class="gw-canvas" role="img" aria-label="The items sent and their links">'
    '<defs><marker id="gw-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
    'markerHeight="7" orient="auto"><path class="gw-arrow" d="M0 0L10 5L0 10z"/></marker></defs>'
    '<g class="gw-links"></g><g class="gw-nodes"></g></svg>'
    '<div class="gw-zoom">'
    '<button type="button" class="gw-button" data-gw="zoom-in" aria-label="Zoom in">+</button>'
    '<button type="button" class="gw-button" data-gw="zoom-out" aria-label="Zoom out">'
    "&minus;</button>"
    '<button type="button" class="gw-button" data-gw="reset" aria-label="Reset the view">'
    "&#x21BA;</button></div></div>"
    '<div class="gw-foot"><label class="gw-switch"><input type="checkbox" role="switch" '
    'data-gw="switch"> Cited and neighbours only</label>'
    '<button type="button" class="gw-keytoggle" data-gw="key" aria-expanded="false" '
    'aria-controls="gw-key">Key</button>'
    '<ul class="gw-key" id="gw-key" aria-label="Key">'
    + "".join(f"<li>{_sample(drawing)}{escape(words)}</li>" for words, drawing in KEY)
    + "</ul></div></div>"
    '<div class="gw-panel"></div>'
    "</dialog>"
)


def _text(value: str) -> str:
    """Stored text, escaped, with its line breaks kept by the `stored` class (AC-25)."""
    return f'<span class="stored">{escape(value)}</span>'


def _formatted(value: str, code_words: bool) -> str:
    """Stored text with its `code` and **bold** drawn by the inline rule (spec 0012).

    `code_words` also shows code looking words as code: for a question, a claim and a
    missing note, never for the note or item text (AC-20 to AC-29).
    """
    return f'<span class="stored">{to_html(runs(value, code_words))}</span>'


def _link(item: ItemLine) -> str:
    """The item's location, linked when it has a file (AC-34 to AC-36, AC-48)."""
    link = item_link(item)
    if link is None or item.file is None:
        return "no file stored"
    shown = item.file if item.line is None else f"{item.file}:{item.line}"
    whole = ", whole file" if item.line is None else ""
    return f'<a href="{escape(link)}">{escape(shown)}{whole}</a>'


def _citation(claim: StoredClaim, cited: str, items: Mapping[str, ItemLine]) -> str:
    """One cited id: linked, `held` after it when held, never linked when rejected.

    The link's `data-item` names the item for the graph's panel (spec 0011 AC-39); it
    does nothing in the list.
    """
    if cited in claim.rejected_ids:
        return escape(cited)
    item = items[cited]
    whole = ", whole file" if item.line is None else ""
    held = " held" if cited in claim.held_ids else ""
    link = escape(item_link(item) or "")
    return f'<a href="{link}" data-item="{escape(cited)}">{escape(cited)}{whole}</a>{held}'


def _claim(claim: StoredClaim, items: Mapping[str, ItemLine]) -> str:
    cited = tuple(dict.fromkeys(claim.cites))
    cites = (
        '<p class="cites">Cites: ' + ", ".join(_citation(claim, c, items) for c in cited) + "</p>"
        if cited
        else ""
    )
    labels = " ".join(escape(label) for label in claim_marks(claim.checked()))
    return (
        f'<li>{_formatted(claim.text, code_words=True)}{cites}<p class="labels">{labels}</p></li>'
    )


def _claims(entry: Entry) -> str:
    items = {item.id: item for item in entry.items}
    rows = "".join(_claim(claim, items) for claim in entry.record.claims)
    return f"<ol>{rows}</ol>" if rows else "<p>No claims.</p>"


def _verdict(entry: Entry) -> str:
    """The model's verdict, and how many claims failed a check when any did (AC-33)."""
    claims = entry.record.claims
    failed = sum(1 for claim in claims if claim.checked().failed)
    tally = f"; {failed} of {len(claims)} claims failed a check" if failed else ""
    return f'<p class="verdict">Model\'s own verdict: {_text(entry.record.verdict)}{tally}</p>'


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
    rows = "".join(f"<li>{_formatted(m, code_words=True)}</li>" for m in missing)
    return f'<p class="eyebrow">Missing, as the answer says</p><ul>{rows}</ul>'


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
        f'<div class="item"><p>{_item_head(lines[item.id])}</p>'
        f"{_formatted(item.text, code_words=False)}</div>"
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
    note = (
        ""
        if marks.note is None
        else f'<p class="note">{_formatted(marks.note, code_words=False)}</p>'
    )
    source = f"{TRACEPATH_REPO_URL}/blob/main/{quote(marks.source_path)}"
    return (
        f'<p class="mark" data-mark="{escape(marks.mark)}">My mark: {_text(marks.mark)}</p>'
        f"{note}"
        f'<p class="source">From <a href="{escape(source)}">{escape(marks.source_path)}</a>, '
        f"{_text(marks.source_row)}</p>"
    )


def _graph_button(graph: EntryGraph) -> str:
    """The entry's Graph button, hidden until the script runs (AC-1, AC-2)."""
    return (
        f'<button type="button" class="graph-open" data-graph="{graph.slug}" '
        f'aria-label="Graph: {escape(graph.label)}" hidden>Graph</button>'
    )


def _graph_data(graph: EntryGraph) -> str:
    """The entry's graph data, parsed only when its graph is opened (AC-57)."""
    return f'<script type="application/json" id="graph-{graph.slug}">{data_block(graph)}</script>'


def _entry(entry: Entry, graph: EntryGraph) -> str:
    return (
        "<article>"
        f"<h3>{_text(entry.marks.label)}</h3>"
        f'<p class="question">{_formatted(entry.record.question, code_words=True)}</p>'
        f"{_details(entry)}"
        f"{_verdict(entry)}"
        f"{_mark(entry)}"
        f"{_graph_button(graph)}"
        f"{_claims(entry)}"
        f"{_missing(entry)}"
        f"{_items_sent(entry)}"
        f"{_graph_data(graph)}"
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


def _section(section: Section, entries: tuple[Entry, ...], graphs: Mapping[str, EntryGraph]) -> str:
    shown = "".join(
        _entry(entry, graphs[entry.marks.label]) for entry in entries if entry.section is section
    )
    if not shown:
        return ""
    return f"<section><h2>{escape(section.value)}</h2>{_section_line(section)}{shown}</section>"


def _intro(shown: int, records: int) -> str:
    """What the page is, what it shows of the records, and where citations point (AC-49 to 54)."""
    return (
        '<div class="intro">'
        "<p>Answers recorded by <code>tracepath ask</code>, a terminal tool that answers "
        "&quot;why was this built this way?&quot; from a project's decision records, each "
        "with my own mark.</p>"
        f'<p>Every citation points into <a href="{escape(JOBHUNT_REPO_URL)}">JobHunt</a> '
        f'at commit <a href="{escape(JOBHUNT_TREE_URL)}">{JOBHUNT_COMMIT[:SHORT_COMMIT]}</a> '
        "and opens the line it cites.</p>"
        f'<p><a href="{escape(ASKS_URL)}">artifacts/asks/</a> holds {records} records. '
        f"This page shows {shown} of them: {escape(SHOWN_SET)}</p>"
        "</div>"
    )


def _key_list(rows: tuple[tuple[str, str], ...], marks: bool) -> str:
    """One key list; a mark's term is drawn as the same pill an entry shows."""
    pill = ' class="mark" data-mark="{}"'
    return (
        "<dl>"
        + "".join(
            f"<dt{pill.format(escape(t)) if marks else ''}>{escape(t)}</dt><dd>{escape(d)}</dd>"
            for t, d in rows
        )
        + "</dl>"
    )


def _key() -> str:
    """What the engineer's marks and the claim labels mean."""
    return (
        '<section class="key"><h2>Key</h2>'
        f"<h3>My marks</h3>{_key_list(MARK_KEY, marks=True)}"
        f"<h3>Labels on a claim</h3>{_key_list(LABEL_KEY, marks=False)}"
        "</section>"
    )


def _scripts(scripts: PageScripts) -> str:
    """The libraries in order, each followed by its licence, then the graph script (AC-71)."""
    libraries = "".join(
        f"<script>{code}\n/*\n{licence}*/</script>" for code, licence in scripts.libraries
    )
    return f"{libraries}<script>{scripts.graph}</script>"


def render_page(
    entries: tuple[Entry, ...],
    records: int,
    graphs: tuple[EntryGraph, ...],
    scripts: PageScripts,
) -> str:
    """The whole page: each section in turn, its entries in marks file order (AC-1 to AC-4).

    `records` is how many records `artifacts/asks/` holds, counted by the build (AC-49);
    `graphs` holds one graph per entry (spec 0011).
    """
    by_label = {graph.label: graph for graph in graphs}
    body = "".join(_section(section, entries, by_label) for section in Section)
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>tracepath answer gallery</title>"
        f"<style>{STYLE}{GRAPH_STYLE}{PANEL_STYLE}</style></head>"
        f"<body><main><h1>tracepath answer gallery</h1>{_intro(len(entries), records)}"
        f"{_key()}{body}</main>{DIALOG}{_scripts(scripts)}</body></html>\n"
    )
