# Verify: gallery readability · spec 0012 · written 2026-10-26
_Steps derived from spec 0012's acceptance criteria. `/check verify` runs them; `/test` locks the durable ones. The pytest steps run in `uv run pytest -m "not integration"`; the browser steps are the only check of the styles and of the one `graph.js` change, because no test in CI draws a page._

Build the page once: `uv run tracepath gallery build --out /tmp/gallery`, then open `/tmp/gallery/index.html`. Desktop steps use a window of 1440 by 900; phone steps use device mode at 390 by 844. No step opens `eval/held-out.json` and none makes a paid call.

Facts these steps lean on, measured 2026-10-26 on the 31 shown records: 17 right, 2 partly right, 2 wrong, 10 declined; 25 records have a missing list; 10 entries have a note; Q11 and Q16 have no claims; 27 entries have a source under `experiments/` and the four held out entries have `docs/scope/scope.md`.

## The rule and where it runs (pytest)
- [ ] `uv run pytest tests/test_gallery_inline.py` → passes: pairs, nesting, unpaired markers, line breaks, double backticks, single asterisks, escaping → AC-1 to AC-8, AC-10
- [ ] Same file, the property over the 31 records → runs rebuild all 2,602 stored texts → AC-9
- [ ] Same file, the real records: Q4 claim 3, Held out 2 items 0017#build-plan:2, 0017#build-plan:4 and 0021#feature-design:25, Eval 1 item 0021#feature-design:13 → AC-3, AC-4, AC-7, AC-8
- [ ] The page's question, claims, missing notes, note and cited item texts show the rule's output; a selected item's `runs` are in its data block only when its text has a pair → AC-11, AC-14 to AC-19, AC-79
- [ ] The code word patterns, and the pinned list of 15 words in 5 questions and 16 in 10 claims → AC-20 to AC-26, AC-29

## The entry (pytest)
- [ ] Headings: `h3` entry title, `h4` sections in the order of AC-31, `h5` groups inside Items sent → AC-30, AC-31, AC-35
- [ ] Eval 1 shows "What the answer says the records lack" and no entry shows "Missing, as the answer says"; an entry with no missing list shows none (25 of 31 show it) → AC-32, AC-33, AC-34
- [ ] Items sent summary reads "Show all (N, M cited)"; the "Cites:" and "Labels:" lines; each label is a chip → AC-36, AC-37, AC-38
- [ ] The four verdict codes show their wordings; an unknown code fails the build naming the record; no wording equals a mark word → AC-42 to AC-48
- [ ] The four swipe colours, the captions, no button and no border on the mark → AC-49 to AC-54
- [ ] A note shows "My note."; Eval 3 shows none; `experiments/` paths link as "My full ruling"; the four held out entries read as plain text; a missing `experiments/` file fails the build; no link into this repository's `docs/`; the development section's "v1 finish line" is plain → AC-57 to AC-63
- [ ] The pinned marks test → AC-64
- [ ] The strip is a hidden direct child button after the source line; its title, its counts equal the Items sent counts, one drawing for all entries with no highlighted node → AC-65 to AC-69
- [ ] The total line reads 31, 17, 2, 2, 10, sits above the mark list in the Key, draws each mark as its swipe; a mark with no entry reads `0` → AC-71 to AC-75
- [ ] `graph.js` finds the three parts anywhere in the entry, never sets `innerHTML`; each entry has one `.question`, one `.verdict`, at most one `ol`; no swipe colour in the graph styles → AC-76, AC-77, AC-78, AC-80

## What the eye checks (browser, desktop 1440 by 900)
- [ ] On Held out 2 item 0017#build-plan:2 and Q4 claim 3, a code word with a hyphen stays on one line when it fits → AC-12
- [ ] On the entry for Eval 3, every section heading sits under a 2px dark rule, and the title, the question and the headings match the board measures → AC-39, AC-40
- [ ] On Q4, the verdict word and the mark are side by side, the verdict's words wrap balanced, and each caption is under its word → AC-55
- [ ] With scripts off (disable JavaScript), Q4 shows no strip and no gap between the source line and the claims → AC-70
- [ ] With scripts on, press Q4's strip → the graph opens, and the panel's answer view shows the list's verdict wording and captions, with the formatting on its question and claims → AC-81
- [ ] In the open graph select Held out 2 item 0021#feature-design:25 → the panel shows `skillCounts` as bold code → AC-19

## What the eye checks (browser, phone 390 by 844)
- [ ] On Q4 the mark sits under the verdict → AC-56
- [ ] On Held out 2 select an item with a long code word (for example `supabase/migrations/20260825162457_data_model.sql:168`) → the word breaks inside itself and nothing runs past the screen edge → AC-13
- [ ] Every entry's headings and strip match the phone column of the board measures → AC-39, AC-40

## The link to one graph (browser, desktop 1440 by 900; steps 4 to 6 also at 390 by 844)
- [ ] Open `/tmp/gallery/index.html#q4` with JavaScript turned off → the page scrolls to Q4 and shows no graph → AC-83
- [ ] Open `/tmp/gallery/index.html#q4` with JavaScript on → Q4's graph opens over the page, headed "Q4" → AC-84
- [ ] Open the page with no fragment, press Q4's strip → the address now ends `#q4`, and the back button leaves the page (it did not add a step) → AC-85
- [ ] With Q4's graph open, press next → the address ends `#q5` and the back button still leaves the page → AC-86
- [ ] Close Q4's graph with Esc, then again with the close button → each time the address has no `#…` at the end, and the back button leaves the page → AC-87
- [ ] After the close, look at the page → Q4 is still in view, as before the graph opened → AC-88
- [ ] Open `/tmp/gallery/index.html#nope` and `#Q4` → the page opens as usual, no graph, and the console shows no error → AC-89
- [ ] Open Q4's graph and select an item → the address still ends `#q4` → AC-90
- [ ] Look at the address after opening Eval 3, Held out 2 and Q22 → `#eval-3`, `#held-out-2`, `#q22`, each the entry's slug and nothing else → AC-92
- [ ] `uv run pytest tests/test_gallery_graph.py -k "slug_is_article_id or replace_state"` → passes: the slug is each article's `id`, and `graph.js` uses only `replaceState` → AC-82, AC-91
