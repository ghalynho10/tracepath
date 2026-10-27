# Verify: gallery readability · spec 0012 · written 2026-10-26
_Steps derived from spec 0012's acceptance criteria. `/check verify` runs them; `/test` locks the durable ones. The pytest steps run in `uv run pytest -m "not integration"`; the browser steps are the only check of the styles and of the one `graph.js` change, because no test in CI draws a page._

Build the page once: `uv run tracepath gallery build --out /tmp/gallery`, then open `/tmp/gallery/index.html`. Desktop steps use a window of 1440 by 900; phone steps use device mode at 390 by 844. No step opens `eval/held-out.json` and none makes a paid call.

Facts these steps lean on, measured 2026-10-26 on the 31 shown records: 17 right, 2 partly right, 2 wrong, 10 declined; 25 records have a missing list; 10 entries have a note; Q11 and Q16 have no claims; 27 entries have a source under `experiments/` and the four held out entries have `docs/scope/scope.md`.

## The rule and where it runs (pytest)
- [x] `uv run pytest tests/test_gallery_inline.py` → passes: pairs, nesting, unpaired markers, line breaks, double backticks, single asterisks, escaping → AC-1 to AC-8, AC-10 · 2026-10-26: `uv run pytest tests/test_gallery*.py -q` → 273 passed
- [x] Same file, the property over the 31 records → runs rebuild all 2,602 stored texts → AC-9 · 2026-10-26: in the 273 passed
- [x] Same file, the real records: Q4 claim 3, Held out 2 items 0017#build-plan:2, 0017#build-plan:4 and 0021#feature-design:25, Eval 1 item 0021#feature-design:13 → AC-3, AC-4, AC-7, AC-8 · 2026-10-26: in the 273 passed
- [x] The page's question, claims, missing notes, note and cited item texts show the rule's output; a selected item's `runs` are in its data block only when its text has a pair, and a link's `phrase_runs` likewise; a code span keeps its spaces between its word elements → AC-11, AC-14 to AC-18, AC-79, AC-96, AC-98, AC-100, AC-101 · 2026-10-26: in the 273 passed; in the browser the spaces between `.w` elements are `" "` text nodes
- [x] The code word patterns, and the pinned list of 15 words in 5 questions and 16 in 10 claims → AC-20 to AC-26, AC-29 · 2026-10-26: in the 273 passed
- [x] A note in the missing list is read for code words, and a bare file name in item text is not → AC-27, AC-28 · 2026-10-26: in the 273 passed

## The entry (pytest)
- [x] Headings: `h3` entry title, `h4` sections in the order of AC-31, `h5` groups inside Items sent → AC-30, AC-31, AC-35 · 2026-10-26: in the 273 passed
- [x] Eval 1 shows "What the answer says the records lack" and no entry shows "Missing, as the answer says"; an entry with no missing list shows none (25 of 31 show it) → AC-32, AC-33, AC-34 · 2026-10-26: in the 273 passed
- [x] Items sent summary reads "Show all (N, M cited)"; the "Cites:" and "Labels:" lines; each label is a chip → AC-36, AC-37, AC-38 · 2026-10-26: in the 273 passed
- [x] The Answer section opens with the verdict block and then the mark block → AC-41 · 2026-10-26: in the 273 passed
- [x] The four verdict codes show their wordings; an unknown code fails the build naming the record; no wording equals a mark word → AC-42 to AC-48 · 2026-10-26: in the 273 passed
- [x] The four swipe colours, the captions, no button and no border on the mark → AC-49 to AC-54 · 2026-10-26: in the 273 passed
- [x] A note shows "My note."; Eval 3 shows none; `experiments/` paths link as "My full ruling" followed by the row as text; the four held out entries read "My full ruling: the v1 finish line in the project's scope notes (not published)." as plain text; a missing `experiments/` file fails the build; no link into this repository's `docs/`; the development section's "v1 finish line" is plain → AC-57 to AC-63, AC-105 · 2026-10-26: in the 273 passed; in the browser the 10 entries with a note in `gallery/marks.json` are the 10 that show "My note." in bold
- [x] The pinned marks test → AC-64 · 2026-10-26: in the 273 passed
- [x] The strip is a hidden direct child button of the article, after the source line and before the claims, with `data-graph`; its title, its accessible name `Explore the graph: <label>, N sent, M cited`, its counts equal the Items sent counts, one drawing for all entries with no highlighted node → AC-65 to AC-69, AC-93 to AC-95, AC-97 · 2026-10-26: in the 273 passed
- [x] The total line reads 31, 17, 2, 2, 10, sits above the mark list in the Key, draws each mark as its swipe, and the Key's mark rows draw the same swipe; a mark with no entry reads `0` → AC-71 to AC-75, AC-102 · 2026-10-26: in the 273 passed
- [x] `graph.js` finds the three parts anywhere in the entry, never sets `innerHTML`; each entry has one `.question`, one `.verdict`, at most one `ol`; no swipe colour in the graph styles → AC-76, AC-77, AC-78, AC-80, AC-103, AC-104 · 2026-10-26: in the 273 passed

## What the eye checks (browser, desktop 1440 by 900)
- [x] On Q4 claim 3 (`--font-mono`, `--font-sans`) a code word with a hyphen stays on one line when it fits; in the open graph of Held out 2, select item 0017#build-plan:2 and check the same for its code → AC-12 · 2026-10-26: Chromium 155, all 718 code words on the page, Items sent open, none on two lines; 0017#build-plan:2 in the panel, 25 words, none split
- [x] On the entry for Eval 3, every section heading sits under a 2px dark rule, and the title, the question and the headings match the board measures → AC-39, AC-40 · 2026-10-26: all 31 entries measured, 4,386 checks, 0 mismatches; `1440-eval-3-entry.png`
- [x] On Q4, the verdict word and the mark are side by side, the verdict's words wrap balanced, and each caption is under its word → AC-55 · 2026-10-26: side by side at 1440 and 561; Q4's verdict fits one line, and `not supported by the records` wraps balanced as `not supported` / `by the records`
- [x] With scripts off (disable JavaScript), Q4 shows no strip and no gap between the source line and the claims → AC-70 · 2026-10-26: 0 of 31 strips shown; source block to claims 12px, the claims' own margin; `1440-nojs-q4-ruling-to-claims.png`
- [x] With scripts on, press Q4's strip → the graph opens, and the panel's answer view shows the list's verdict wording and captions, with the formatting on its question and claims → AC-81 · 2026-10-26: `.verdict` text and the question and claims HTML equal the list's; 7 `code` in the claims, no backtick left
- [x] In the open graph select Held out 2 item 0021#feature-design:25 → the panel shows `skillCounts` as bold code; on Eval 1 select item 0001#binding-rules:26 → the phrase of its link to 0001#binding-rules:30 shows as bold, without its `**` → AC-19, AC-99 · 2026-10-26: `skillCounts` is `code` in `strong`, weight 700; the phrase is in `strong`, no `**`

## What the eye checks (browser, phone 390 by 844)
- [x] On Q4 the mark sits under the verdict → AC-56 · 2026-10-26: under the verdict, 14px apart, at 390 and 560; `390-q4-verdict-mark.png`
- [x] On Q14 open the graph and select item 0013#follow-up:13, whose text holds `supabase/migrations/20260825162457_data_model.sql:168` → the word breaks inside itself and nothing runs past the screen edge; check Held out 1's question the same way (`test/integration/profile-form.test.ts`) → AC-13 · 2026-10-26: Q14 word on two lines, right edge 374 of 374, dialog scrollWidth 390; Held out 1's word is 380.9px on a 358px line, breaks after `profile-`, page scrollWidth 390
- [x] Every entry's headings and strip match the phone column of the board measures → AC-39, AC-40 · 2026-10-26: all 31 entries measured, 4,262 checks, 0 mismatches

## The link to one graph (browser, desktop 1440 by 900; steps 4 to 6 also at 390 by 844)
- [x] Open `/tmp/gallery/index.html#q4` with JavaScript turned off → the page scrolls to Q4 and shows no graph → AC-83 · 2026-10-26: Q4's top at 0, no dialog, at 1440 and 390
- [x] Open `/tmp/gallery/index.html#q4` with JavaScript on → Q4's graph opens over the page, headed "Q4" → AC-84 · 2026-10-26: dialog open, `Q4 13 / 31`
- [x] Open the page with no fragment, press Q4's strip → the address now ends `#q4`, and the back button leaves the page (it did not add a step) → AC-85 · 2026-10-26: `#q4`; back went to `about:blank`
- [x] With Q4's graph open, press next → the address ends `#q5` and the back button still leaves the page → AC-86 · 2026-10-26: `#q5`, back to `about:blank`, at 1440 and 390
- [x] Close Q4's graph with Esc, then again with the close button → each time the address has no `#…` at the end, and the back button leaves the page → AC-87 · 2026-10-26: address ends `index.html` both ways, back to `about:blank`, at 1440 and 390
- [x] Open Q4's graph and close it → Q4 is in view; open Q4's graph, press next, then close it → the page is at Q5, the entry whose graph was showing → AC-88 · 2026-10-26: Q4's then Q5's strip in view and focused, at 1440 and 390
- [x] Open `/tmp/gallery/index.html#nope`, `#Q4` and `#gw-key` → each time the page opens as usual, no graph, and the console shows no error → AC-89 · 2026-10-26: no dialog, 0 console or page errors, each time
- [x] Open Q4's graph and select an item → the address still ends `#q4` → AC-90 · 2026-10-26: `feature-5#5-design-system-ui-foundation-done:8` selected, still `#q4`
- [x] Look at the address after opening Eval 3, Held out 2 and Q22 → `#eval-3`, `#held-out-2`, `#q22`, each the entry's slug and nothing else → AC-92 · 2026-10-26: exactly those three
- [x] `uv run pytest tests/test_gallery_graph.py -k "slug_is_article_id or replace_state"` → passes: the slug is each article's `id`, and `graph.js` uses only `replaceState` → AC-82, AC-91 · 2026-10-26: 2 passed

## The code tint (pytest and browser)
- [x] `uv run pytest tests/test_gallery_code_tint.py` → passes: the `code` rule has a faint background, the panel adds none of its own, and it is none of the four swipe colours and lighter than `#CBD3DC` → AC-106 to AC-109 · 2026-10-26: 7 passed (the step named `tests/test_gallery.py -k code_tint` until this date, which selected no test)
- [x] On Q4 claim 3 and in the open graph of Held out 2 (select item 0017/AC-8), look at a code span of several words → the tint is one unbroken run across its spaces, in the list and in the panel → AC-110 · 2026-10-26: Q4 claim 3's spans are one word each; in the list Q1's `Result<{ … }>` and in the panel `pnpm eval -t control-direct-match` show one unbroken tint across spaces and a line break; `.w` carry no background
- [x] At 390 by 844 make a multi word code span wrap (the same item) → the tint continues on the next line with rounded ends on each line, and no word is split at a hyphen → AC-110, AC-12 · 2026-10-26: Chromium only, `${pair.id} [${pair.tags.join(" ")}]` wraps tinted on both lines, `box-decoration-break: clone`, no word split; WebKit not checked (not installed)
