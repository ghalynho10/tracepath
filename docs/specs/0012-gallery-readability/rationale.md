# 0012. Gallery readability: rationale

## Context

The gallery page of spec 0010 shows 31 answers with the engineer's marks, and spec 0011 adds a graph window. A reader who has never seen the tool meets four problems. Stored text shows raw markers: on 2026-10-26, 43 of 107 claims hold backticks and, of 125 cited items, 94 hold backticks and 86 hold bold. Nothing marks where the answer starts: the question is 20px regular text near the claim text, and the only break is a hairline (basis: `render.py` lines 155 and 169 to 170). The model's verdict and my mark are two pills of the same shape side by side, so the reader cannot tell the model's word from mine (basis: `render.py` lines 158 to 161). And the claim labels look like section headings and share their style with the Missing and Items sent headings (basis: `render.py` lines 178 to 181).

Three forces shape the answer. The project has no JavaScript test or linter in CI (basis: `AGENTS.md`, Layout), and `graph.js` already draws every stored text with `textContent` so that markup stays text (basis: spec 0011 AC-53). The marks are the engineer's rulings, and a note rewritten for the public must not change a mark. And `docs/specs`, `docs/scope` and `docs/reviews` leave the public repository after this feature merges, so a public page cannot point into them.

The notes on the page were copied word for word from experiment READMEs and `docs/scope/scope.md` (basis: spec 0010 `index.md` line 132). They read as private working notes, and four of them point at a file the public cannot reach once `docs/` is gone.

## Options considered

### Option 1: Format in Python, send the panel plain runs, follow canvas direction B

One pure module turns a stored string into runs. The list writes escaped HTML from them. The panel's selected item text arrives as runs in the data block, and `graph.js` makes one element per run.

**Pros**:
- All parsing sits in pytest, with the real records as test data.
- The script keeps its `textContent` rule, so the escape guard stays one place deep.
- The list and the panel cannot disagree about what is code, because they use one function.

**Cons**:
- The data block grows by up to about 1 MB.
- `graph.js` still needs a small change to map runs to elements, which only a browser checks.

### Option 2: Format in Python for the list, parse markers again in `graph.js` for the panel

The list is as in Option 1. The script gets its own small parser for an item's text.

**Pros**:
- The data block does not grow.

**Cons**:
- A second parser in the one file with no test in CI, and it must agree with the first on double backticks, `**` inside code and bold code, three shapes the real records hold.
- The two parsers can drift, and a reader would see it only by opening a graph.

### Option 3: Python writes HTML for the panel and the script inserts it

The data block carries ready made, escaped HTML for an item's text, and `graph.js` sets `innerHTML`.

**Pros**:
- Smallest script change, and the same HTML as the list.

**Cons**:
- Breaks the rule that stored text reaches the panel only through `textContent` (basis: spec 0011, The panel). A later escaping mistake would execute in the page instead of showing as text.

### The layout

The canvas holds three directions for the top of the Answer section: A "Ledger", B "Highlighter" and C "Scale". The engineer chose B on 2026-10-26: the verdict in mono and the mark in bold on a swipe of its colour, so the two read as different voices at equal weight, with a graph strip that says what it opens. The earlier mockups (three entry layouts and three block layouts, screenshots of Eval 3, Q4 and Held out 1 at 1440 and 390) led to this direction.

## Rationale

**Reversibility**: two way door (the change is presentation only; a revert restores the old page, and `gallery/marks.json` notes are in git history).

Option 1 wins because the forces point one way. The script has no test in CI, so every line of parsing it holds is a line nothing checks, and Option 2 would put a second parser there. Option 3 gives up the one security rule the graph window has. Option 1 spends about 1 MB of page size, which the page can afford, to keep the parser in one tested place and the script a mapper. Measured on 2026-10-26, the rule needs real care (double backticks, `**` inside code, bold code, single asterisks all occur), and pytest with the real records is where that care can be checked.

The one line rule is chosen over whole text pairing because it is the safer failure: a stray marker can spoil only its own line. It costs nothing today (9 of 2,602 texts run over a line and none pairs differently).

Code words are styled by a fixed pattern list rather than by guessing because the list is short, the hits are pinned by a test, and a change shows in the test. The five regular expressions find 31 words in 15 of the 138 questions and claims; the engineer asked for file names, `$` names, CAPITAL_SNAKE, `name()` and lower_snake (basis: the design conversation of 2026-10-26).

**The open question on code words.** The engineer asked whether the same rule should cover the "records lack" list and item text. Recommendation: yes for the list, no for item text. The list is model prose like a claim, and the patterns find 0 words in its 46 notes today, so covering it costs nothing and keeps the page consistent if a future record has one. Item text is JobHunt's own words, where the author already marked code (1,857 of 2,408 item texts hold backticks), and the patterns would add bare file names and snake case words that the author chose not to mark, which would show them as marked when they were not. The runner up, covering item text too, would style bare file names the author left plain. A note of mine carries only the markers I type, because a note is my voice and the patterns are for model text.

The verdict words are fixed and never equal a mark word, because the page must keep the model's word and my word apart. "partly answered" differs from "partly right" and "answered" from "right". A test asserts it.

The public note lives in the existing `note` field rather than a new field: the field's meaning changes, nothing else does, and the original wording stays where it was written (the experiment READMEs), reachable by "My full ruling" for the 27 entries whose source is under `experiments/`. A second field would make every entry carry two notes. The pinned marks test (AC-64) guards the one real risk of rewriting 10 notes by hand: a mark changed by accident.

## References

**Project sources**:
- `src/tracepath/gallery/render.py`, `src/tracepath/gallery/assets/graph.js`, `src/tracepath/ask/answer.py`.
- [spec 0010](../0010-answer-gallery/index.md), [spec 0011](../0011-answer-graph/index.md), `AGENTS.md`.
- Measurements of 2026-10-26 on the 31 shown records, made by read only scripts over `gallery/marks.json` and `artifacts/asks/` (not kept in the repository).
- The Claude Design canvas "tracepath answer block", read 2026-10-26.

**Practices & standards**:
- Output encoding at the point where HTML is written.
- Parse in a tested core; keep the untested shell to mapping data to elements.
