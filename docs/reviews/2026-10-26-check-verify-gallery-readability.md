# Check verify, gallery readability, 2026-10-26

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/gallery-readability` at `b6ccc1a`
**Spec**: [0012](../specs/0012-gallery-readability/index.md), checked against its [verify.md](../specs/0012-gallery-readability/verify.md); scope row 19
**Verdict**: **pass in Chromium**. Every browser criterion of verify.md (AC-12, AC-13, AC-19, AC-39, AC-40, AC-55, AC-56, AC-70, AC-81, AC-83 to AC-90, AC-92, AC-99, AC-110) was met in a real run, at 1440 by 900 and at 390 by 844, and the pytest steps pass. Nothing failed. AC-110 was not checked in WebKit, because this machine's Playwright has no WebKit build. Two small findings are listed below; neither blocks the merge.

This is a runtime check, not a code review. No code was changed, no paid call was made, no model or subagent was started, `eval/held-out.json` was never opened, and no note or mark in `gallery/marks.json` was written or changed (notes were checked for rendering only, not wording).

How it was run:

- The page: `uv run tracepath gallery build --out <scratchpad>/gallery`, served from that folder on `127.0.0.1:8765` and driven in Chromium 155.0.8059.85 through Playwright, with real clicks, keys and mouse presses on graph dots. Each check loaded the page fresh (from `about:blank`), because a fragment typed into a page that is already open is not handled, by the spec's design.
- Scripts off: a separate browser context with JavaScript disabled.
- Measures: read from the rendered page (computed styles and element boxes), for all 31 entries at each width, not only the ones verify.md names.

Screenshots sit in the session scratchpad, folder `/private/tmp/claude-501/-Users-ghaly-Documents-Work-Personal-tracepath/09c63778-b3d2-4631-888c-d81c2889d8a7/scratchpad/shots/`: `390-held-out-1-question.png`, `390-q14-panel-0013-follow-up-13.png`, `1440-held-out-2-panel-0017-build-plan-2.png`, `1440-held-out-2-panel-0021-feature-design-25.png`, `1440-held-out-2-panel-skillCounts.png`, `1440-held-out-2-panel-0017-AC-8-wrap.png`, `390-held-out-2-panel-0017-AC-8-wrap.png`, `1440-q4-claim-3.png`, `1440-q1-list-wrapped-code.png`, `1440-eval-3-entry.png`, `390-eval-3-entry.png`, `1440-q4-verdict-mark.png`, `390-q4-verdict-mark.png`, `1440-nojs-q4-ruling-to-claims.png`, `390-nojs-q4-ruling-to-claims.png`, `1440-nojs-fragment-q4.png`, `390-nojs-fragment-q4.png`, `1440-q4-panel-answer-view.png`, `1440-eval-1-panel-binding-rules-26.png`. None shows a failure.

## Evidence

- **E1** Build: exit 0, `✓ 31 entries → …/scratchpad/gallery/index.html`; the folder holds `index.html` only (4.6M). 31 `article` elements, ids `eval-1` … `q22`. No console error or page error in the whole session.
- **E2** Tests: `uv run pytest tests/test_gallery*.py -q` → `273 passed in 17.13s` (six files). `uv run pytest tests/test_gallery_graph.py -k "slug_is_article_id or replace_state"` → 2 passed. `uv run pytest tests/test_gallery.py -k code_tint` → **0 selected** (124 deselected); the tint tests live in `tests/test_gallery_code_tint.py`, and `uv run pytest tests/test_gallery_code_tint.py` → 7 passed (finding 1).
- **E3** Every code word on the page, with every Items sent list opened: 718 visible `.w` words at each width.
  - At 1440: none renders on more than one line; none runs past its block; page `scrollWidth` 1440.
  - At 390: one word renders on two lines, `test/integration/profile-form.test.ts` in Held out 1's question, as `test/integration/profile-` and `form.test.ts`. Its unbroken width at its own computed font is 380.9px; the line it sits on is 358px. Nothing runs past the edge; page `scrollWidth` 390. Screenshot `390-held-out-1-question.png`.
- **E4** Q14's graph at 390, dot `0013#follow-up:13` pressed: the panel shows `supabase/migrations/20260825162457_data_model.sql:168` on two lines, broken inside the word (`…data_mode` / `l.sql:168`), right edge 374 against its block's 374, dialog `scrollWidth` 390. Screenshot `390-q14-panel-0013-follow-up-13.png`.
- **E5** Held out 2's graph at 1440 (opened from `#held-out-2`): dot `0017#build-plan:2` pressed → 25 words in the panel, none split, including `["./test/setup/require-stack.ts"]` and `--project`; its code `include: ["test/eval/**/*.test.ts"]` shows the `**` as typed. Dot `0017/AC-8` → 20 words, none split.
- **E6** The code tint, computed in the browser on every `code` checked, list and panel alike: background `rgba(1, 25, 54, 0.07)`, radius `3px`, `box-decoration-break: clone`; each `.w` inside has a transparent background and `display: inline-block`; the spaces between words are text nodes `" "`.
  - List: Q4 claim 3's `--font-mono` and `--font-sans` are one word each, so they show no space; 44 code spans of several words exist in the list. Q1's item `Result<{ allowed: true, value: T } or { allowed: false, reason: UsageGateReason }>` wraps over two lines at 1440 with the tint unbroken across its spaces and on both lines (`1440-q1-list-wrapped-code.png`).
  - Panel, 1440: in `0017/AC-8`, `pnpm eval -t control-direct-match` wraps (`pnpm` / `eval -t control-direct-match`), tinted on both lines and across every space (`1440-held-out-2-panel-0017-AC-8-wrap.png`).
  - Panel, 390: the same item wraps `${pair.id} [${pair.tags.join(" ")}]` over two lines, tint on both; `control-direct-match` and `stability-probe-generic` stay whole (`390-held-out-2-panel-0017-AC-8-wrap.png`).
- **E7** Board measures, every entry, read from the rendered page: **4,386 checks at 1440 and 4,262 at 390, 0 mismatches.** Covered: title size, weight, line height and letter spacing; the details line (mono 11px, .04em, `#3F5877`, 6px under the title); every `h4` (2px solid `#011936` rule, 24 or 20 above, 28 or 24 for the missing section, 14 or 12 padding, 18 or 17px bold); question (22 or 19px, line 1.35, 8 or 6 under its heading); verdict and mark block (18 or 14 above; two equal columns 32px apart, or one column 14px apart); verdict word (mono 22 or 18, line 1.3, `text-wrap: balance`); mark (bold 22 or 18; swipe padding 6 or 5, left margin −6 or −5, the board radius, `clone`); both captions (12.5 or 12px, `#3F5877`, 8 or 6 under the word); ruling block (18 or 14 above, 14 or 12 padding, 1px `rgba(1,25,54,.14)` rule; "My note." bold, 15px, line 24px, at most 576px; source 12px `#3F5877`); strip (20 or 16 above, full width, 1.5px ink border, radius 10, drawing 176 by 72 or 96 by 64, title 16px bold, the sentence at 13px on desktop and hidden on the phone, counts mono 11.5px, round ink button 40 or 36px with a white arrow); claims (12 above, 1px rules, padding 22 or 18, number mono 11px, text 16 or 15px line 1.6, "Cites:" mono 12px 8 above, "Labels:" mono 12px 6 above, chips 11px with a 1px `rgba(1,25,54,.35)` border, radius 3); missing list (16 or 15px, line 1.6, `#3F5877`). Screenshots `1440-eval-3-entry.png`, `390-eval-3-entry.png`.
- **E8** Verdict and mark: Q4 shows `partly answered` and `partly right` side by side at 1440, 561 and every desktop entry (E7); at 560 and 390 the mark sits under the verdict (`390-q4-verdict-mark.png`). Q4's verdict fits one line, so the balanced wrap was seen on `not supported by the records` (Q1 and others), which wraps as `not supported` / `by the records` in its 320px column, where a greedy wrap would leave `records` alone.
- **E9** Scripts off, both widths: 0 of 31 strips shown, Q4's strip `hidden`; from the bottom of Q4's source line block to the top of its claims is 12px, which is the claim list's own 12px margin, so the strip leaves no gap (`1440-nojs-q4-ruling-to-claims.png`). Opening `#q4` scrolls so Q4's top sits at 0 (scrollY 19,748 at 1440, 23,764 at 390), no dialog open.
- **E10** Panel content, 1440:
  - Q4's strip → dialog open, headed `Q4 13 / 31`. Nothing selected: the panel's `.verdict` text equals the list's (`partly answered— the model's verdict on its own answer`); its question and claim list HTML equal the list's exactly; 7 `code` elements in its claims, no backtick left, tint as in the list (`1440-q4-panel-answer-view.png`).
  - Held out 2, dot `0021#feature-design:25` → `skillCounts` is a `code` inside `strong`, weight 700, mono, with no `**` and no backtick around it (`1440-held-out-2-panel-skillCounts.png`).
  - Eval 1, dot `0001#binding-rules:26` → its link `out AMENDED_BY 0001#binding-rules:30 HELD` shows the phrase `Two, the authorisation rule this spec asks for is hereby written.` in `strong`, with no `**` (`1440-eval-1-panel-binding-rules-26.png`).
- **E11** The link to one graph, with real clicks and keys. "Back leaves the page" was tested by starting each run on `about:blank`, then pressing back once and reading the address (`history.length` sits at the tab's cap of 50, so it says nothing).

  | Step | 1440 | 390 |
  |---|---|---|
  | open `#q4` | dialog open, `Q4 13 / 31` | not asked |
  | Q4's strip | `#q4`, back → `about:blank` | not asked |
  | Q4's strip, next | `#q5`, `Q5 14 / 31`, back → `about:blank` | same |
  | Esc | address ends `index.html`, closed, back → `about:blank` | same |
  | the close button | same as Esc | same |
  | open Q4, close | Q4's strip in view and focused | same |
  | open Q4, next, close | Q5's strip in view and focused | same |
  | `#nope`, `#Q4`, `#gw-key` | page as usual, no dialog, 0 errors, fragment left as typed | not asked |
  | Q4 open, press dot `feature-5#5-design-system-ui-foundation-done:8` | panel shows that item, address still `#q4` | not asked |
  | Eval 3, Held out 2, Q22 strips | `#eval-3`, `#held-out-2`, `#q22` | not asked |

- **E12** Notes: the 10 entries with a note in `gallery/marks.json` (Held out 3, Q2, Q4, Q6, Q7, Q11, Q12, Q13, Q19, Q22) are exactly the 10 that show a `.note`; each starts `My note. ` in bold, is visible, and shows no raw backtick or `**`. No other entry shows "My note.". Wording not read.

## Per criterion

| Criteria | Status | Evidence |
|---|---|---|
| AC-1 to AC-11, AC-14 to AC-18, AC-20 to AC-38, AC-41 to AC-54, AC-57 to AC-69, AC-71 to AC-80, AC-82, AC-91, AC-93 to AC-98, AC-100 to AC-109 | met by the pytest steps | E2 |
| AC-12 | met at both widths, every code word on the page and in the panels opened | E3, E5, E6 |
| AC-13 | met: Q14's panel word and Held out 1's question word | E3, E4 |
| AC-19 | met | E10 |
| AC-39, AC-40 | met at both widths, all 31 entries | E7 |
| AC-55 | met | E7, E8 |
| AC-56 | met | E7, E8 |
| AC-70 | met at both widths | E9 |
| AC-81 | met | E10 |
| AC-83 | met at both widths | E9 |
| AC-84 to AC-90, AC-92 | met; AC-86 to AC-88 at both widths | E11 |
| AC-99 | met | E10 |
| AC-110 | met in Chromium, list and panel, at both widths | E6 |
| AC-110 in WebKit | **not checked**: only Chromium builds are installed for Playwright on this machine | none |

## The hyphen break at 390 in Held out 1's question

It is the AC-13 case, not a miss of AC-12. The word `test/integration/profile-form.test.ts` is 380.9px wide unbroken and its line is 358px (E3), so it is a word wider than its line, and it breaks inside itself without running past the edge, which is what AC-13 asks. AC-12 only covers a line wide enough for the word. It breaks at the hyphen because, inside the word's own box, the hyphen is the browser's normal first place to break; `overflow-wrap: anywhere` only cuts between any two letters when a piece has no such place, which is what Q14's `…data_model.sql:168` shows (E4). At 1440 the same word sits whole on one line.

## Findings

Neither blocks the merge. Each is a recommendation you may take or skip.

1. **verify.md's tint command selects no test.** The step `uv run pytest tests/test_gallery.py -k code_tint` deselects all 124 tests in that file and exits 5, because the tint tests are in `tests/test_gallery_code_tint.py` (7 pass). A reader following verify.md would see "no tests ran" and could not tell whether AC-106 to AC-109 hold. Route: change the line to `uv run pytest tests/test_gallery_code_tint.py`, in the next spec edit or at `/sync`.
2. **The panel's answer view runs the question straight into the verdict.** With nothing selected, the cloned question and the `partly answered` verdict word sit with almost no space between them (`1440-q4-panel-answer-view.png`). No criterion covers spacing in the panel (the board measures are for the list entry), so nothing fails. Worth a look at `/check review` or the next visual pass.

Also seen, no action suggested: ids and paths that are not code spans still break at hyphens on a narrow line, for example the panel title `0001#binding-` / `rules:26` and the item location `specs/0013-job-search-and-results-` / `list/index.md:185`. AC-12 covers code words only, so this is by the spec.

## Not done in this run

- AC-110 in WebKit (see the table). To check it, you could install the WebKit build with `npx playwright install webkit` (a free download, no paid call) and run the 390 wrap of Held out 2's `0017/AC-8` in it.
- Only Chromium was driven for everything else.
