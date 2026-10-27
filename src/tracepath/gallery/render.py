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
from types import MappingProxyType
from urllib.parse import quote

from tracepath.ask.answer import Verdict, claim_marks
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
from tracepath.gallery.records import (
    RULINGS_DIR,
    Entry,
    Mark,
    PageScripts,
    Section,
    StoredClaim,
)

#: This repository on GitHub; a ruling under `experiments/` links to its file there.
TRACEPATH_REPO_URL = "https://github.com/ghalynho10/tracepath"

#: The records folder on GitHub (AC-50).
ASKS_URL = f"{TRACEPATH_REPO_URL}/tree/main/artifacts/asks"

#: JobHunt's tree at the pinned commit (AC-54).
JOBHUNT_TREE_URL = f"{JOBHUNT_REPO_URL}/tree/{JOBHUNT_COMMIT}"

#: Where the page is served and the image Pages serves beside it (AC-66, AC-67).
PAGE_URL = "https://ghalynho10.github.io/tracepath/"
PREVIEW_NAME = "preview.png"

#: The link preview text, ruled 2026-10-27; the `og:description` and the meta description
#: carry the same words (AC-70, AC-71).
PREVIEW_DESCRIPTION = (
    "Answers recorded by tracepath, a tool that answers questions about a project's "
    "decisions from its specs and decision records, each with my own mark and a graph "
    "of what the model was given."
)

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
MARK_KEY: tuple[tuple[Mark, str], ...] = (
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

#: The headings of an entry's sections, in order (spec 0012 AC-31).
QUESTION_HEADING = "Question"
ANSWER_HEADING = "Answer"
MISSING_HEADING = "What the answer says the records lack"
ITEMS_HEADING = "Items sent"

#: The graph strip's title and its sentence (spec 0012 AC-66, board measures).
STRIP_TITLE = "Explore the graph"
STRIP_LINE = "Every item the model was sent and how they link, the cited ones labelled"

#: The strip's drawing, the same in every entry and highlighting no node (spec 0012
#: AC-68, AC-69), copied from the spec: the board's drawing, its inline style a class,
#: cropped to its middle on a phone.
STRIP_DRAWING = (
    '<svg class="strip-drawing" width="176" height="72" viewBox="0 0 176 72" preserveAspe'
    'ctRatio="xMidYMid slice" aria-hidden="true"><rect width="176" height="72" rx="6" fil'
    'l="#F2F4F7"></rect><g stroke="rgba(1,25,54,.18)" stroke-width="1"><path d="M26 30 46'
    " 30M46 30 70 36M52 40 70 36M78 26 98 24M98 24 122 16M116 44 128 40M116 44 118 52M92 "
    "50 88 60M92 50 84 48M108 34 116 44M138 28 128 40M40 18 46 30M14 12 24 20M24 20 26 30"
    'M148 46 158 40M156 14 144 8M138 28 156 14"></path></g><g fill="rgba(1,25,54,.3)"><ci'
    'rcle cx="14" cy="12" r="1.8"></circle><circle cx="26" cy="30" r="1.8"></circle><circ'
    'le cx="12" cy="52" r="1.8"></circle><circle cx="34" cy="60" r="1.8"></circle><circle'
    ' cx="40" cy="18" r="1.8"></circle><circle cx="52" cy="40" r="1.8"></circle><circle c'
    'x="30" cy="44" r="1.8"></circle><circle cx="60" cy="10" r="1.8"></circle><circle cx='
    '"66" cy="58" r="1.8"></circle><circle cx="78" cy="26" r="1.8"></circle><circle cx="8'
    '4" cy="48" r="1.8"></circle><circle cx="96" cy="10" r="1.8"></circle><circle cx="100'
    '" cy="64" r="1.8"></circle><circle cx="108" cy="34" r="1.8"></circle><circle cx="118'
    '" cy="52" r="1.8"></circle><circle cx="122" cy="16" r="1.8"></circle><circle cx="134'
    '" cy="62" r="1.8"></circle><circle cx="138" cy="28" r="1.8"></circle><circle cx="148'
    '" cy="46" r="1.8"></circle><circle cx="156" cy="14" r="1.8"></circle><circle cx="162'
    '" cy="58" r="1.8"></circle><circle cx="168" cy="32" r="1.8"></circle><circle cx="20"'
    ' cy="64" r="1.8"></circle><circle cx="46" cy="30" r="1.8"></circle><circle cx="112" '
    'cy="8" r="1.8"></circle><circle cx="128" cy="40" r="1.8"></circle><circle cx="144" c'
    'y="8" r="1.8"></circle><circle cx="158" cy="40" r="1.8"></circle><circle cx="56" cy='
    '"24" r="1.8"></circle><circle cx="88" cy="60" r="1.8"></circle><circle cx="24" cy="2'
    '0" r="1.8"></circle><circle cx="140" cy="54" r="1.8"></circle><circle cx="76" cy="8"'
    ' r="1.8"></circle></g><path d="M70 36 98 24 116 44 92 50Z" fill="none" stroke="rgba('
    '1,25,54,.18)" stroke-width="1"></path><g fill="rgba(1,25,54,.3)"><circle cx="70" cy='
    '"36" r="1.8"></circle><circle cx="98" cy="24" r="1.8"></circle><circle cx="116" cy="'
    '44" r="1.8"></circle><circle cx="92" cy="50" r="1.8"></circle></g></svg>'
)

#: How each stored verdict code reads on the page; none equals a mark word (spec 0012
#: AC-42 to AC-47).
VERDICT_WORDS: Mapping[Verdict, str] = MappingProxyType(
    {
        "answered": "answered",
        "partly": "partly answered",
        "not_supported": "not supported by the records",
        "no_documented_link": "no documented link",
    }
)

#: The caption under the model's verdict (spec 0012 AC-46).
VERDICT_CAPTION = "\u2014 the model's verdict on its own answer"

#: The caption under the engineer's mark (spec 0012 AC-53).
MARK_CAPTION = "\u2014 my mark"

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

#: The page's styles, inline (AC-58): flat paper and hairlines in the portfolio's navy
#: ink, laid out by the board measures of spec 0012 at two widths, the phone layout at
#: 560 pixels and narrower. The mark is a bold word on its swipe, beside the model's
#: verdict in mono type, so the two read apart (spec 0012 AC-41 to AC-56).
STYLE = """\
:root { --paper: #FFFFFF; --ink: #011936; --ink-82: rgba(1, 25, 54, .82);
  --ink-64: #3F5877; --ink-46: rgba(63, 88, 119, .78);
  --rule: rgba(1, 25, 54, .14); --rule-strong: rgba(1, 25, 54, .30);
  --cyan: #07A0C3;
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
code { font-family: var(--mono); font-size: .9em; background: rgba(1, 25, 54, .07);
  border-radius: 3px; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
code .w { display: inline-block; max-width: 100%; overflow-wrap: anywhere; white-space: pre-wrap; }
.g { white-space: nowrap; }
.g code { white-space: pre-wrap; }
.g code:has(> .w:only-child) { white-space: nowrap; }
.g .w { max-width: calc(100% - 2ch); }
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
.key .total { margin: 0 0 14px; font-size: 14px; color: var(--ink-82); }
.key dd { margin: 0; color: var(--ink-82); }
@media (max-width: 480px) {
  .key dl { grid-template-columns: 1fr; gap: 4px; }
  .key dt { max-width: none; }
  .key dd { margin-bottom: 12px; }
}
article { padding: 28px 0 32px; border-bottom: 1px solid var(--rule); }
article > h3 { font-size: 44px; line-height: 1.05; font-weight: 700;
  letter-spacing: -.02em; margin: 0; }
.details { font: 11px/1.4 var(--mono); letter-spacing: .04em; color: var(--ink-64);
  margin: 6px 0 0; }
article > h4 { margin: 24px 0 0; padding-top: 14px; border-top: 2px solid var(--ink);
  font-size: 18px; line-height: 1.3; font-weight: 700; }
.question { font-size: 22px; line-height: 1.35; margin: 8px 0 0; max-width: 36rem; }
.verdict-mark { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 32px; margin: 18px 0 0; }
.verdict p, .mark p { margin: 0; }
.verdict-word { font: 22px/1.3 var(--mono); text-wrap: balance; }
.mark-word { font-size: 22px; line-height: 1.3; }
.caption { margin-top: 8px !important; font-size: 12.5px; line-height: 1.4; color: var(--ink-64); }
.caption + .caption { margin-top: 2px !important; }
.swipe { padding: 0 6px; border-radius: 3px 8px 4px 9px / 8px 3px 9px 4px; font-weight: 700;
  font-family: var(--sans); color: var(--ink); -webkit-box-decoration-break: clone;
  box-decoration-break: clone; }
.mark-word .swipe { margin-left: -6px; }
.swipe[data-mark="right"] { background: #B9E3EE; }
.swipe[data-mark="partly right"] { background: #F6E27F; }
.swipe[data-mark="wrong"] { background: #FFC8C2; }
.swipe[data-mark="declined"] { background: #CBD3DC; }
@media (max-width: 560px) {
  .verdict-mark { grid-template-columns: minmax(0, 1fr); gap: 14px; margin-top: 14px; }
  .verdict-word, .mark-word { font-size: 18px; }
  .caption { margin-top: 6px !important; font-size: 12px; }
  .swipe { padding: 0 5px; }
  .mark-word .swipe { margin-left: -5px; }
}
.ruling { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--rule); }
.note { margin: 0; max-width: 36rem; font-size: 15px; line-height: 1.6; }
.source { margin: 8px 0 0; font-size: 12px; color: var(--ink-64); }
.strip { display: flex; align-items: center; gap: 16px; width: 100%; margin: 20px 0 0;
  padding: 10px; border: 1.5px solid var(--ink); border-radius: 10px; background: var(--paper);
  color: var(--ink); font: inherit; text-align: left; cursor: pointer; }
.strip-drawing { flex: none; display: block; width: 176px; height: 72px; }
.strip-text { flex: 1; min-width: 0; }
.strip-text > span { display: block; }
.strip-title { font-size: 16px; line-height: 1.3; font-weight: 700; }
.strip-line { margin-top: 2px; font-size: 13px; line-height: 1.4; color: var(--ink-82); }
.strip-counts { margin-top: 4px; font: 11.5px/1.4 var(--mono); color: var(--ink-64); }
.strip-go { flex: none; display: grid; place-items: center; width: 40px; height: 40px;
  border-radius: 50%; background: var(--ink); color: var(--paper); font-size: 18px; }
.strip:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
article ol, .gw-answer ol { list-style: none; counter-reset: claim; padding: 0; margin: 12px 0 0;
  border-top: 1px solid var(--rule); }
article ol > li, .gw-answer ol > li { position: relative; counter-increment: claim;
  padding: 22px 0 22px 2.4em; border-bottom: 1px solid var(--rule); font-size: 16px;
  line-height: 1.6; }
article ol > li::before, .gw-answer ol > li::before {
  content: counter(claim, decimal-leading-zero); position: absolute; left: 0; top: 27px;
  font: 11px/1 var(--mono); color: var(--ink-46); }
.cites { margin: 8px 0 0; font: 12px/1.6 var(--mono); color: var(--ink-64);
  overflow-wrap: anywhere; }
.labels { margin: 6px 0 0; font: 12px/1.8 var(--mono); color: var(--ink-64); }
.chip { padding: 0 5px; border: 1px solid rgba(1, 25, 54, .35); border-radius: 3px;
  font-size: 11px; white-space: nowrap; }
article > h4.lack { margin-top: 28px; }
article > ul.lack { margin: 10px 0 0; padding-left: 1.1em; font-size: 16px; line-height: 1.6;
  color: var(--ink-64); }
details { margin-top: 10px; }
details > summary { cursor: pointer; list-style: none; padding: 4px 0; font-size: 14px;
  color: var(--ink-82); }
details > summary::-webkit-details-marker { display: none; }
details > summary::after { content: " +"; color: var(--cyan); }
details[open] > summary::after { content: " \\2212"; }
details h5 { margin: 18px 0 8px; font-size: 13px; font-weight: 700; color: var(--ink-64); }
details .item p, details li { font: 12px/1.6 var(--mono); color: var(--ink-64);
  overflow-wrap: anywhere; }
details ul { list-style: none; padding: 0; margin: 0; }
details li { padding: 4px 0; border-bottom: 1px solid var(--rule); }
details .item { padding: 6px 0 12px; border-bottom: 1px solid var(--rule); }
details .item p { margin: 0 0 4px; }
details .item > .stored { font-size: 14px; color: var(--ink-82); }
[hidden] { display: none !important; }
@media (max-width: 560px) {
  article > h3 { font-size: 36px; }
  article > h4 { margin-top: 20px; padding-top: 12px; font-size: 17px; }
  .question { font-size: 19px; margin-top: 6px; }
  .ruling { margin-top: 14px; padding-top: 12px; }
  .strip { margin-top: 16px; }
  .strip-drawing { width: 96px; height: 64px; }
  .strip-line { display: none !important; }
  .strip-go { width: 36px; height: 36px; }
  article ol > li { padding: 18px 0 18px 2.4em; font-size: 15px; }
  article ol > li::before { top: 23px; }
  article > h4.lack { margin-top: 24px; }
  article > ul.lack { font-size: 15px; }
}
"""

#: The graph window's styles (spec 0011): a split window, the graph about two thirds and
#: the panel one third, with a hairline between them; at 720 pixels or less the graph
#: sits above the panel and the key folds behind a Key button (AC-54, AC-55, AC-91).
#: Cyan only rings the selection, and the marks' yellow and pink are never used here
#: (AC-22).
GRAPH_STYLE = """\
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
.gw-button:focus-visible { outline: 2px solid var(--ink);
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
.gw-answer .verdict { margin-top: 24px; }
.gw-answer ol { margin-top: 18px; }
@media (max-width: 560px) {
  .gw-answer .verdict { margin-top: 20px; }
}
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
    labels = " ".join(
        f'<span class="chip">{escape(label)}</span>' for label in claim_marks(claim.checked())
    )
    return (
        f"<li>{_formatted(claim.text, code_words=True)}{cites}"
        f'<p class="labels">Labels: {labels}</p></li>'
    )


def _claims(entry: Entry) -> str:
    items = {item.id: item for item in entry.items}
    rows = "".join(_claim(claim, items) for claim in entry.record.claims)
    return f"<ol>{rows}</ol>" if rows else "<p>No claims.</p>"


def _swipe(mark: Mark) -> str:
    """A mark word, bold on its own colour (spec 0012 AC-49 to AC-52)."""
    return f'<span class="swipe" data-mark="{escape(mark)}">{escape(mark)}</span>'


def _verdict(entry: Entry) -> str:
    """The model's verdict in words, under it its caption (spec 0012 AC-42 to AC-46).

    When any claim failed a check, the tally is a second caption (spec 0010 AC-33).
    """
    claims = entry.record.claims
    failed = sum(1 for claim in claims if claim.checked().failed)
    tally = (
        f'<p class="caption">{failed} of {len(claims)} claims failed a check</p>' if failed else ""
    )
    return (
        '<div class="verdict">'
        f'<p class="verdict-word">{escape(VERDICT_WORDS[entry.record.verdict])}</p>'
        f'<p class="caption">{escape(VERDICT_CAPTION)}</p>{tally}</div>'
    )


def _verdict_and_mark(entry: Entry) -> str:
    """One block: the model's verdict first, the engineer's mark second (spec 0012 AC-41)."""
    return (
        f'<div class="verdict-mark">{_verdict(entry)}'
        f'<div class="mark"><p class="mark-word">{_swipe(entry.marks.mark)}</p>'
        f'<p class="caption">{escape(MARK_CAPTION)}</p></div></div>'
    )


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
    """What the answer says the records lack, when it says anything, whatever the mark.

    AC-20, spec 0012 AC-32, AC-33.
    """
    missing = entry.record.missing
    if not missing:
        return ""
    rows = "".join(f"<li>{_formatted(m, code_words=True)}</li>" for m in missing)
    return f'<h4 class="lack">{escape(MISSING_HEADING)}</h4><ul class="lack">{rows}</ul>'


def _item_head(item: ItemLine) -> str:
    """An item's id, type, held or accepted, its marker, and its location."""
    parts = [escape(item.id), escape(item.type), "held" if item.held else "accepted"]
    if item.marker is not None:
        parts.append(item.marker)
    return " · ".join([*parts, _link(item)])


def _cited(entry: Entry) -> frozenset[str]:
    """The ids some claim cites without rejecting: the M of the strip and of Items sent."""
    return frozenset(
        c for claim in entry.record.claims for c in claim.cites if c not in claim.rejected_ids
    )


def _items_sent(entry: Entry) -> str:
    """The pack sent, closed until opened: cited items in full, others one row each."""
    cited = _cited(entry)
    lines = dict(zip((item.id for item in entry.record.items), entry.items, strict=True))
    shown = "".join(
        f'<div class="item"><p>{_item_head(lines[item.id])}</p>'
        f"{_formatted(item.text, code_words=False)}</div>"
        for item in entry.record.items
        if item.id in cited
    )
    rows = "".join(f"<li>{_item_head(line)}</li>" for line in entry.items if line.id not in cited)
    return (
        f"<h4>{escape(ITEMS_HEADING)}</h4>"
        f"<details><summary>Show all ({len(entry.items)}, {len(cited)} cited)</summary>"
        f"<h5>Cited</h5>{shown or '<p>None.</p>'}"
        f"<h5>Not cited</h5>{f'<ul>{rows}</ul>' if rows else '<p>None.</p>'}"
        "</details>"
    )


def _source(entry: Entry) -> str:
    """Where the full ruling is (spec 0012 AC-59, AC-60, AC-105).

    A link for a file under `experiments/`, else plain words naming the row in the
    unpublished scope notes.
    """
    marks = entry.marks
    if marks.source_path.startswith(RULINGS_DIR):
        link = f"{TRACEPATH_REPO_URL}/blob/main/{quote(marks.source_path)}"
        return (
            f'<p class="source"><a href="{escape(link)}">My full ruling</a>, '
            f"{_text(marks.source_row)}</p>"
        )
    return (
        f'<p class="source">My full ruling: the {_text(marks.source_row)} in the '
        "project&#x27;s scope notes (not published).</p>"
    )


def _ruling(entry: Entry) -> str:
    """The engineer's note, when there is one, then the source line (spec 0012 AC-57)."""
    note = entry.marks.note
    shown = (
        ""
        if note is None
        else f'<p class="note"><strong>My note.</strong> {_formatted(note, code_words=False)}</p>'
    )
    return f'<div class="ruling">{shown}{_source(entry)}</div>'


def _strip(entry: Entry, graph: EntryGraph) -> str:
    """The entry's graph strip, hidden until the script runs (spec 0012 AC-65 to AC-69).

    Its counts and accessible name carry the same N and M as Items sent (AC-93 to AC-97).
    """
    sent = len(entry.items)
    cited = len(_cited(entry))
    name = f"{STRIP_TITLE}: {graph.label}, {sent} sent, {cited} cited"
    return (
        f'<button type="button" class="strip" data-graph="{graph.slug}" '
        f'aria-label="{escape(name)}" hidden>{STRIP_DRAWING}'
        f'<span class="strip-text"><span class="strip-title">{escape(STRIP_TITLE)}</span>'
        f'<span class="strip-line">{escape(STRIP_LINE)}</span>'
        f'<span class="strip-counts">{sent} sent · {cited} cited</span></span>'
        '<span class="strip-go" aria-hidden="true">&rarr;</span></button>'
    )


def _graph_data(graph: EntryGraph) -> str:
    """The entry's graph data, parsed only when its graph is opened (AC-57)."""
    return f'<script type="application/json" id="graph-{graph.slug}">{data_block(graph)}</script>'


def _entry(entry: Entry, graph: EntryGraph) -> str:
    """One entry, flat: its title, details, then each section's `h4` and its parts.

    Spec 0012 AC-30, AC-31, AC-65; its `id` is its slug, so `#<slug>` reaches it (AC-82).
    """
    return (
        f'<article id="{graph.slug}">'
        f"<h3>{_text(entry.marks.label)}</h3>"
        f"{_details(entry)}"
        f"<h4>{escape(QUESTION_HEADING)}</h4>"
        f'<p class="question">{_formatted(entry.record.question, code_words=True)}</p>'
        f"<h4>{escape(ANSWER_HEADING)}</h4>"
        f"{_verdict_and_mark(entry)}"
        f"{_ruling(entry)}"
        f"{_strip(entry, graph)}"
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
            return f"<p>{escape(ASK_1_LINE)} (v1 finish line).</p>"
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
        "questions about a project's decisions from its specs and decision records, each "
        "with my own mark.</p>"
        f'<p>Every citation points into <a href="{escape(JOBHUNT_REPO_URL)}">JobHunt</a> '
        f'at commit <a href="{escape(JOBHUNT_TREE_URL)}">{JOBHUNT_COMMIT[:SHORT_COMMIT]}</a> '
        "and opens the line it cites.</p>"
        f'<p><a href="{escape(ASKS_URL)}">artifacts/asks/</a> holds {records} records. '
        f"This page shows {shown} of them: {escape(SHOWN_SET)}</p>"
        "</div>"
    )


def _key_list(rows: tuple[tuple[str, str], ...]) -> str:
    return "<dl>" + "".join(f"<dt>{t}</dt><dd>{escape(d)}</dd>" for t, d in rows) + "</dl>"


def _total(entries: tuple[Entry, ...]) -> str:
    """How many answers are shown and how many carry each mark (spec 0012 AC-71 to AC-75)."""
    counts = " · ".join(
        f"{_swipe(mark)} {sum(1 for entry in entries if entry.marks.mark == mark)}"
        for mark, _ in MARK_KEY
    )
    return f'<p class="total">My marks on the {len(entries)} shown answers: {counts}</p>'


def _key(entries: tuple[Entry, ...]) -> str:
    """What the engineer's marks and the claim labels mean, with the total of the marks."""
    marks = tuple((_swipe(mark), meaning) for mark, meaning in MARK_KEY)
    labels = tuple((escape(label), meaning) for label, meaning in LABEL_KEY)
    return (
        '<section class="key"><h2>Key</h2>'
        f"<h3>My marks</h3>{_total(entries)}{_key_list(marks)}"
        f"<h3>Labels on a claim</h3>{_key_list(labels)}"
        "</section>"
    )


def _scripts(scripts: PageScripts) -> str:
    """The libraries in order, each followed by its licence, then the graph script (AC-71)."""
    libraries = "".join(
        f"<script>{code}\n/*\n{licence}*/</script>" for code, licence in scripts.libraries
    )
    return f"{libraries}<script>{scripts.graph}</script>"


def _preview_tags() -> str:
    """The link preview meta tags, written before the styles (AC-65 to AC-72)."""
    description = escape(PREVIEW_DESCRIPTION)
    tags = (
        ("property", "og:title", "tracepath answer gallery"),
        ("property", "og:type", "website"),
        ("property", "og:url", PAGE_URL),
        ("property", "og:image", f"{PAGE_URL}{PREVIEW_NAME}"),
        ("property", "og:image:width", "1200"),
        ("property", "og:image:height", "627"),
        ("property", "og:description", description),
        ("name", "description", description),
    )
    return "".join(f'<meta {kind}="{name}" content="{content}">' for kind, name, content in tags)


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
        f"{_preview_tags()}"
        f"<style>{STYLE}{GRAPH_STYLE}{PANEL_STYLE}</style></head>"
        f"<body><main><h1>tracepath answer gallery</h1>{_intro(len(entries), records)}"
        f"{_key(entries)}{body}</main>{DIALOG}{_scripts(scripts)}</body></html>\n"
    )
