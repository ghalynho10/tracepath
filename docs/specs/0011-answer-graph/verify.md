# Verify: answer graph · spec 0011 · updated 2026-10-25 (after the code review)
_Note 2026-10-26: steps here that name the old pill, the old verdict line ("Model's own verdict: answered"), "My mark", "Missing, as the answer says", the Graph button or a source link to `docs/` are superseded by spec 0012's `verify.md`._
_Steps derived from spec 0011's acceptance criteria, one step per criterion, plus the live check after the merge. `/check verify` runs these; `/test` locks the durable ones. The pytest steps already run in `uv run pytest -m "not integration"`._

Build the page once for the browser steps: `uv run tracepath gallery build --out /tmp/gallery`, then open `/tmp/gallery/index.html`. Desktop steps use a window of 1440 by 900 pixels; phone steps use the browser's device mode at 390 by 844 with touch on. No step makes a paid call, and none opens `eval/held-out.json`.

Facts these steps lean on, measured 2026-10-25 on the 31 shown records: Eval 3 has 37 items and 27 links; Eval 2 has 90 items and 114 links, two of them from an item to itself; Q11 and Q16 cite no item; no shown record has a rejected id or an item with no file, so those two steps use a copy of the repo.

## Opening and closing (browser, desktop)
- [ ] Load the page with scripts on → every one of the 31 entries shows a Graph button → AC-1
- [ ] Load the page with scripts off → no Graph button shows, and the 31 entries read as before → AC-2
- [ ] Press Eval 3's Graph button → a window fills the screen, headed "Eval 3", with its graph → AC-3
- [ ] Press Esc → the window closes → AC-4
- [ ] Open Eval 3 again and press the round × button → the window closes → AC-5
- [ ] Open Eval 1, press next to reach Eval 2, then close → focus is on Eval 2's Graph button → AC-6
- [ ] Open Held out 1 → the heading row reads "Held out 1" and "6 / 31" → AC-7
- [ ] On Eval 1, press next → Eval 2 opens, "2 / 31" → AC-8
- [ ] On Eval 2, press previous → Eval 1 opens, "1 / 31" → AC-9
- [ ] On Eval 1 → the previous button is disabled → AC-10
- [ ] On Q22 → "31 / 31", and the next button is disabled → AC-11

## What the graph shows (browser, desktop)
- [ ] On Eval 3, count the dots in the canvas (not the key) → 37, one per stored item → AC-12
- [ ] On Eval 2, count the lines in the canvas → 112: 114 stored links less the 2 from an item to itself → AC-13
- [ ] On Eval 2, look at a cited item such as `0014/AC-20a` → a large dot (radius 9) in solid ink → AC-14
- [ ] On Eval 2, with nothing selected → each cited dot carries its id as a label, except a crowded one AC-90 hides → AC-15
- [ ] On Eval 2, look at an item that is not cited → a small pale dot (radius 3.5, ink at 50 percent) → AC-16
- [ ] On Eval 2, an item that is not cited shows no label until you hover near it, select it, or select a neighbour → AC-17
- [ ] On Eval 2 → each of its 13 held items has a dashed ring → AC-18
- [ ] On Eval 2 → each of its 16 held links is dashed, at 50 percent ink; other links are solid at 30 percent → AC-19
- [ ] On Eval 3 → its one unresolved name is a square; every other dot is a circle → AC-20
- [ ] Select any dot → it gains a cyan ring → AC-21
- [ ] `uv run pytest tests/test_gallery_graph.py -k "no_mark_colour and yellow"` → passes: no yellow → AC-22
- [x] `uv run pytest tests/test_gallery_graph.py -k "no_mark_colour and pink"` → passes: no pink → AC-95
- [x] `uv run pytest tests/test_gallery_graph.py -k cyan_only` → passes: cyan only on the selection ring → AC-96
- [ ] Look at the strip under the canvas → a key with the six drawings: cited, not cited, held item, held link, unresolved name, selected → AC-23
- [ ] Open Q11 (and Q16) → the panel says "This answer cites no item." → AC-24
- [ ] Open Eval 2, Eval 3 and Q6 → every dot sits inside the canvas → AC-25
- [ ] On Eval 2, turn the mouse wheel over the canvas → the graph zooms about the pointer, and the page does not scroll → AC-26
- [ ] On Eval 2, drag empty canvas → the graph pans by the drag → AC-27
- [ ] Press + and then − → the graph zooms in by 1.25 times and back → AC-28
- [ ] Drag a dot on Eval 2, then press the reset button → every dot is back at its first place → AC-29
- [ ] Zoom and pan Eval 2, then press reset → the view is the first view again → AC-29a
- [ ] On Eval 3, turn on "Cited and neighbours only" → every item that is neither cited nor next to a cited item is hidden (29 of 37) → AC-30
- [ ] With the switch on → every line that touches a hidden item is hidden too (22 of 27) → AC-31
- [ ] Turn the switch off → all 37 dots and 27 lines show again → AC-32
- [ ] Open Q11 → the switch is disabled → AC-33
- [ ] On Eval 3, select a dot with two neighbours → all but it, its neighbours and its own lines dim to 20 percent → AC-34
- [ ] Click empty canvas → the selection clears and the panel shows the answer again → AC-35

## The reading panel (browser, desktop)
- [ ] Open Eval 1 → the panel shows its question exactly as the list shows it → AC-36
- [ ] The panel shows the same verdict line as the list ("Model's own verdict: answered") → AC-37
- [ ] The panel shows Eval 1's 4 claims in stored order, numbered 01 to 04, each with the labels the list shows → AC-38
- [ ] Click `0008/AC-7` in claim 01 → that item is selected, and the page stays (it does not open JobHunt) → AC-39
- [ ] After that click → the selected dot sits at the centre of the canvas, at the same zoom → AC-40
- [ ] In a copy of the repo, add `9999/AC-1` to a claim's `cites` and its `rejected_ids` in Eval 1's record, build, open the graph and click that id in the panel → it is plain text and nothing is selected → AC-41
- [ ] Select `0008/AC-7` → the panel shows its stored text in full → AC-42
- [ ] The panel shows the id as the large title and its type ("AcceptanceCriterion") above it → AC-43
- [ ] On Eval 1, select `0021#feature-design:12` → "STRUCK"; `unresolved:feature-14:feature-32` → "UNRESOLVED NAME"; on Eval 2, `0001#binding-rules:32` → "HELD" → AC-44
- [ ] Select `0008/AC-7` on Eval 1 → "Cited by claims 01, 02" → AC-45
- [ ] Its location reads `specs/0008-app-shell-and-navigation/index.md:54` and links to that line in JobHunt at the pinned commit → AC-46
- [ ] In a copy of the repo, set an uncited item's stored location to `no file stored` in Eval 1's record, build and select it → "no file stored", with no link → AC-47
- [ ] Select `0008/AC-5b` on Eval 1 → each link is listed with its direction (in or out), type, the other id and its phrase, or "no phrase stored" → AC-48
- [ ] Select `0009/AC-14` on Eval 1 → its link from `0009#build-plan:9` shows "HELD" → AC-49
- [ ] On that same item → its link to itself is listed once, marked "self", and no line is drawn for it → AC-50
- [ ] Click the other id in one of those links → that item is selected → AC-51
- [ ] Press "Back to the answer" → the list of all items shows, cited ones first; clicking any id selects it → AC-52
- [ ] On Eval 3, select `feature-6#6-entry-page-link-metadata-done:11` → its `<figure` shows as text, and the panel holds no figure element → AC-53

## On a phone (browser, 390 by 844, touch)
- [ ] Open Eval 2 → the graph sits above the panel → AC-54
- [ ] Swipe up in the panel → the panel scrolls, while the graph and the page stay put → AC-55
- [ ] Drag one finger across empty canvas → the graph pans → AC-56

## The build and its data (commands)
- [ ] `uv run pytest tests/test_gallery_graph.py -k "one_graph_file_per_entry or holds_every_stored"` → passes: one graph file per entry with every item and link → AC-57
- [ ] `uv run pytest tests/test_gallery_graph.py -k holds_no_stored_line` → passes → AC-58
- [ ] `uv run pytest tests/test_gallery_graph.py -k cited_is_a_citation` → passes → AC-59
- [ ] `uv run pytest tests/test_gallery_graph.py -k held_is_the_stored_held` → passes → AC-60
- [ ] `uv run pytest tests/test_gallery_graph.py -k unresolved_is_the_type` → passes → AC-61
- [ ] `uv run pytest tests/test_gallery_graph.py -k neighbours_are_every_other_item` → passes → AC-62
- [x] `uv run pytest tests/test_gallery_graph.py -k "neighbours_list_each_id_once or two_links_between"` → passes → AC-97
- [x] `uv run pytest tests/test_gallery_graph.py -k first_link_order` → passes → AC-98
- [x] `uv run pytest tests/test_gallery_graph.py -k never_its_own_neighbour` → passes → AC-99
- [ ] `uv run pytest tests/test_gallery_graph.py -k near_cited` → passes → AC-63
- [ ] `uv run pytest tests/test_gallery_graph.py -k cited_by_is_the_numbers` → passes → AC-64
- [ ] `uv run pytest tests/test_gallery_graph.py -k link_whose_end_is_not_an_item` → passes: exit 1, the record and the link named → AC-65
- [ ] `uv run pytest tests/test_gallery_graph.py -k two_items_with_one_id` → passes: exit 1, the record and the id named → AC-66
- [ ] `uv run pytest tests/test_gallery_graph.py -k two_labels_with_one_slug` → passes: exit 1, both entries named → AC-67
- [ ] `uv run pytest tests/test_gallery_graph.py -k "could_break_out or exits_1_naming_the_script"` → passes: exit 1, the script named, any letter case → AC-68
- [ ] `uv run pytest tests/test_gallery_graph.py -k markup_characters_as_escapes` → passes → AC-69
- [ ] `uv run pytest tests/test_gallery_graph.py -k "parses_back or survives_the_page"` → passes → AC-70
- [ ] `uv run pytest tests/test_gallery_graph.py -k dependency_order` → passes: d3-dispatch, d3-quadtree, d3-timer, d3-force → AC-71
- [ ] `uv run pytest tests/test_gallery_graph.py -k followed_by_its_licence` → passes → AC-72
- [ ] `uv run pytest tests/test_gallery_graph.py -k sources_lists` → passes → AC-73
- [ ] `uv run pytest tests/test_gallery_graph.py -k refers_to_no_script` → passes: no tag in the HTML names a script, style or font file → AC-74 _(amended 2026-10-27)_
- [ ] In the browser's network panel, open Eval 3 for the first time → exactly one request, for `graphs/eval-3.js` on the page's own site, and none other → AC-75 _(amended 2026-10-27; it read "open three graphs → no request is made")_
- [ ] Note where Eval 2's dots sit, reload the page, open Eval 3 and then Eval 2 → every dot is in the same place → AC-76

## Dragging a dot (browser, desktop; Eval 2 and Eval 3)
- [ ] Drag a cited dot → it stays under the pointer → AC-77
- [ ] While dragging → every one of its neighbours moves → AC-78
- [ ] Press a dot and let go after moving it under 4 pixels → that dot is selected → AC-79
- [ ] Select one item, then drag another dot → the first stays selected, and the dragged one is not selected → AC-80
- [ ] Drag empty canvas → every dot moves by the same distance in the same direction → AC-81
- [ ] Drag a dot, close the window and reopen it → every dot is back at its first place → AC-82
- [ ] Drag a dot, press next, then previous → every dot is back at its first place → AC-83

## Pressing a dot (browser; Eval 2)
- [ ] With a mouse, press 11 pixels from a small dot with no other near → it is selected; 16 pixels away → nothing is → AC-84
- [ ] On the phone, tap 16 pixels from a small dot with no other near → it is selected; 24 pixels away → nothing is → AC-85
- [ ] Start a drag 13 to 20 pixels from every dot → the graph pans → AC-86

## Visual pass (browser)
- [ ] Every label shows its id in stored case (for example `0014/AC-20a`, not capitals) → AC-87
- [x] On the phone, Q2's `unresolved:0011:the-emergency-kill-switch-built-in-feature-3` → its label is shortened with "…" → AC-100
- [x] Hover that dot → its tooltip gives the full id → AC-101
- [x] Select it → the panel's title gives the full id → AC-102
- [ ] On the phone, open Q17: `feature-11#11-job-search-results-list:1` sits left of its dot, shortened; pan its dot to the left edge → the full label returns, right of the dot → AC-88
- [ ] On the phone, open Eval 2 → in the top cluster, `0014/AC-20a` (cited first) keeps its label, and no two shown cited labels overlap → AC-89
- [ ] There, `0001#binding-rules:25` has no label; hover it, select it, or select its neighbour `0001#binding-rules:28` → its label shows → AC-90
- [ ] On the phone → the key is hidden behind a Key button; press it → the six drawings show → AC-91
- [ ] On the phone at 844 pixels high → the canvas is 380 pixels tall, 45 percent → AC-92
- [ ] Open Eval 2, Eval 3 and Q6 at both sizes → no dot sits under the zoom buttons → AC-93
- [ ] `uv run pytest tests/test_gallery_graph.py -k cite_order` → passes → AC-94

## The panel's source link (browser, desktop; added 2026-10-25 after the code review)
- [x] On Eval 1, select `0008/AC-7` and click its location link → JobHunt opens in a new tab, and the graph stays open in the first tab with `0008/AC-7` selected → AC-103
- [x] `uv run pytest tests/test_gallery_graph.py -k opens_in_a_new_tab` → passes: the script gives that link `target="_blank"` and `rel="noopener"` → AC-103

## Graph files (added 2026-10-27; serve the build from `127.0.0.1`, since the Playwright tool refuses `file:` addresses)
- [x] `uv run pytest tests/test_gallery_graph.py -k no_graph_data_in_the_page` → passes: no `application/json` element in `index.html` → AC-104 · 2026-10-28: at 13fd2e5, `test_no_graph_data_in_the_page` passed; the built page has no `<link>`, no `<script src>` and no graph data
- [x] `ls DIR/graphs` after a build into an empty folder → 31 files named `<slug>.js`, nothing else → AC-105 · 2026-10-28: at 13fd2e5, a build into an empty scratch folder holds `graphs/` with 31 files, `eval-1.js` … `q9.js`, nothing else
- [x] `uv run pytest tests/test_gallery_graph.py -k graph_file_shape` → passes: one `tracepathGraph(` call, the slug as a JSON string, the object, `);` and one newline → AC-106 · 2026-10-28: at 13fd2e5, `test_graph_file_shape_is_one_call_and_one_newline` passed
- [x] Same test class → the slug is the same in the call, the object and the file name → AC-107 · 2026-10-28: at 13fd2e5, `test_graph_file_shape_names_one_slug` passed
- [x] Throttle the network, press Eval 3's Graph button → the window opens at once with "Loading the graph…" where the canvas goes → AC-108 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] During that wait → previous, next, the switch, zoom in, zoom out and reset are disabled; Esc and the close button close the window → AC-109 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] When the file arrives → the words go and the graph draws as in the steps above → AC-110 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] When the file arrives → the six controls are enabled, except previous on Eval 1, next on Q22 and the switch on Q11 → AC-111 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] Delete `graphs/eval-3.js`, press Eval 3's Graph button → "This graph did not load. Close the window and open it again to try."; the window stays open → AC-112 · 2026-10-28: at 13fd2e5, with `graphs/eval-3.js` moved out (server answered 404), Graph on Eval 3 showed "This graph did not load. Close the window and open it again to try." and the window stayed open (AC-112a)
- [x] Same state → the address reads `#eval-3` until the window closes → AC-113 · 2026-10-28: in that state `location.hash` read `#eval-3`; after close it read empty
- [x] Close, restore the file, press the button again → a request for the file is made and the graph opens → AC-114 · 2026-10-28: file put back, same page, Graph pressed again → one new request for `eval-3.js`, "Eval 3", "3 / 31", 37 dots
- [x] Open Eval 3, close it, open it again; then Eval 1 → next → previous → no request for an already loaded file → AC-115 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] Throttle, set the address fragment to `#eval-1` and at once to `#eval-3` → the window ends on Eval 3, and nothing is drawn for Eval 1 when its file arrives → AC-116 · 2026-10-28: at 13fd2e5, both files held back by Playwright, `#eval-1` then 100 ms later `#eval-3`. With Eval 1 arriving last (3 s, Eval 3 at 0.8 s) and with Eval 1 arriving first (0.8 s, Eval 3 at 3 s), the window ended on "Eval 3", "3 / 31", 37 dots, and stayed so after Eval 1's file arrived (AC-116a)
- [x] Throttle, open `…/#q9` in a fresh tab → the window opens in the loading state, then draws Q9 → AC-117 · 2026-10-28: at 13fd2e5, fresh tab at `#q9` with `q9.js` held 3 s → at 486 ms "Loading the graph…", heading "Graph", 0 dots; at about 4 s "Q9", "18 / 31", 90 dots; one request
- [x] By hand: double click the built `index.html` (a `file://` address) and press Eval 3's Graph button → it opens. Write the browser and the result here → AC-118 · 2026-10-28: by the engineer, Chrome, the scratch build's `index.html` opened by double click (`file://`), Graph on Eval 3 → "3 / 31", the graph drew, the panel started "Why is password sign in impossible on production?"
- [x] `uv run pytest tests/test_gallery_graph.py -k no_request_api` → passes: no `fetch(`, `XMLHttpRequest`, `import(`, `new Image` or `sendBeacon` in `graph.js` → AC-119 · 2026-10-28: at 13fd2e5, `test_the_script_uses_no_request_api` passed
- [x] `uv run pytest tests/test_gallery_graph.py -k adds_a_script_for_a_graph_file` → passes: `createElement("script")` and `graphs/` are in `graph.js` → AC-119a · 2026-10-28: at 13fd2e5, `test_the_script_adds_a_script_for_a_graph_file` passed
- [x] Throttled, press Eval 3's Graph button and press Esc at once; let the file arrive → nothing is drawn and the window does not reopen → AC-120 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] Throttled, open Eval 1 and, with its file failing (delete `graphs/eval-1.js`), reach Eval 3 before it settles → no failure words over Eval 3 → AC-121 · 2026-10-28: at 13fd2e5, Graph on Eval 1 with `eval-1.js` held back then answered 404, `#eval-3` set while it waited. Failing after Eval 3 drew (2.5 s) and before it (0.6 s): the failure words stayed hidden and Eval 3 drew, "3 / 31", 37 dots
- [x] In the failed state of Eval 3 → heading reads "Graph", no counter → AC-122; previous, next, switch, zoom in, zoom out and reset all disabled → AC-122a · 2026-10-28: at 13fd2e5, in the failed state of Eval 3 the heading read "Graph" with an empty counter, and previous, next, the switch, zoom in, zoom out and reset were all disabled
- [x] Focus previous on Eval 1 with Eval 2's file not yet loaded and press it → focus moves to the close button → AC-123 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] Open Eval 2 with the switch on, then reach an unloaded graph → the dots, lines and panel of Eval 2 are gone and the switch is off → AC-124 · 2026-10-28: carried over from the `/check verify` run at 7663a55, as the engineer reported it; not rerun at 13fd2e5
- [x] `uv run pytest tests/test_gallery_graph.py -k dialog_holds_the_status_words` → passes → AC-125 · 2026-10-28: at 13fd2e5, `test_dialog_holds_the_status_words` passed
- ~~Block a file's request so it stays pending, close the window, press the button again → a new request is made → AC-126~~ Dropped 2026-10-28, ruled by the engineer: Chromium shares the running download, so no new request is sent; see the note under AC-126 in `index.md`.
- [x] `uv run pytest tests/test_gallery_graph.py -k writes_the_page_last` → passes: `index.html` written after every graph file → AC-127; a build with a file standing where `graphs/` should be exits 1 naming that path → AC-127a · 2026-10-28: at 13fd2e5, `test_writes_the_page_last` and `test_writes_the_page_last_so_a_graph_file_it_cannot_write_leaves_no_page` passed (exit 1, `…/graphs/eval-1.js: could not be written`, no `index.html`)

## After the merge
- [x] The Pages workflow run on `main` succeeds, and https://ghalynho10.github.io/tracepath/ shows 31 entries, each with a Graph button; Eval 3's graph opens there with 37 dots, the network panel shows no request on opening, and the page with scripts off still shows the list with no Graph button → spec 0011 live, AC-1, AC-2, AC-12, AC-75 on the published page _(2026-10-27 note: AC-75 was checked here against its old reading, no request on opening. It now requires exactly one request, for the entry's graph file, so it is checked again on the live site after task 11 merges.)_
- [ ] After task 11 merges and the Pages run: on the live page open Eval 3 → one request, for `graphs/eval-3.js`; and run LinkedIn's Post Inspector on the live URL and on `…/#q9` → AC-75, spec 0010 AC-78
