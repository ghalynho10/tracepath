# Check verify, answer graph, 2026-10-25

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/answer-graph` at `361a0e9`
**Spec**: [0011](../specs/0011-answer-graph/index.md), checked against its [verify.md](../specs/0011-answer-graph/verify.md)
**Verdict**: **pass before merge, one step blocked until merge**. All 95 criteria (AC-1 to AC-94, plus AC-29a) were met in a real run in this session. The one step that cannot run yet is the live check on GitHub Pages (verify.md, After the merge), because the page only goes live when this branch reaches `main`. Nothing failed. Two small findings and one note for `/test` are listed below; none blocks the merge.

This is a runtime check, not a code review. No code was changed, no paid call was made, `eval/held-out.json` was never opened (the copies below were made without it), and the checkout's working tree is clean apart from this file.

How it was run:

- The page: `uv run tracepath gallery build --out /tmp/tracepath-gallery`, served from that folder on `127.0.0.1:8765` and driven in Chromium 155 through Playwright. Desktop at 1440 by 900 with a real mouse. Phone at 390 by 844 in a context with `hasTouch` and `isMobile` on, with real touch events sent through the browser's input protocol (`Input.dispatchTouchEvent`), so a swipe or a tap reaches the page as a finger would.
- The drawing against the records: a script that reads each of the 31 records and `gallery/marks.json` straight from disk, works out which items are cited, held and unresolved and which links exist from the spec's rules on its own (not by calling the code), and compares that with what the browser drew for every graph.
- The failure cases: on copies of the repo in the session scratch area (`src/`, `artifacts/` without `runs/` and `superseded/`, `gallery/`, `corpus/`, and the eval research file only: no `.git`, no `.env`, no `reference/`, no `eval/held-out.json`). Each case got a fresh copy and ran the copy's own code (`PYTHONPATH` set to the copy's `src/`; `tracepath.__file__` confirmed it). The untouched copy builds a page byte identical to the checkout's.
- Scripts off, compared with what was there before: `main`'s gallery built from `git archive main` in the scratch area.

Screenshots sit in the session scratchpad, not in the repo: `desktop-eval3.png`, `phone-eval2.png`, `phone-eval2-key.png`, `phone-q17-panned.png`, `phone-eval2-br28.png`.

## Evidence

- **E1** Build: exit 0, `✓ 31 entries → /tmp/tracepath-gallery/index.html`; the folder holds `index.html` only (3.3M). `git status --short` afterwards is empty.
- **E2** Tests: `uv run pytest tests/test_gallery_graph.py tests/test_gallery.py -q` → `151 passed in 12.55s`. Each `-k` selection that verify.md names was also run on its own, and each selected and passed at least one test: `cyan_only` 1, `one_data_block_per_entry or holds_every_stored` 3, `holds_no_stored_line` 1, `cited_is_a_citation` 1, `held_is_the_stored_held` 1, `unresolved_is_the_type` 1, `neighbours_are or two_links_between` 2, `near_cited` 1, `cited_by_is_the_numbers` 1, `link_whose_end_is_not_an_item` 1, `two_items_with_one_id` 1, `two_labels_with_one_slug` 1, `could_break_out or exits_1_naming_the_script` 13, `markup_characters_as_escapes` 1, `parses_back or survives_the_page` 2, `dependency_order` 1, `followed_by_its_licence` 1, `sources_lists` 1, `refers_to_no_script` 1, `cite_order` 1.
- **E3** Scripts on, desktop: 31 entries, 31 Graph buttons, all 31 visible, each with `aria-label="Graph: <label>"`; 31 JSON data blocks; every `script` element inline; 0 `link` elements.
- **E4** Scripts off: 31 Graph buttons in the markup, 0 visible, and no other button visible. The text of `main` is identical to `main`'s own gallery (46,275 characters, 1,276 lines, no line differs).
- **E5** Opening and closing (desktop, real clicks and keys):

  | Step | Seen |
  |---|---|
  | Eval 3's Graph button | dialog open at 0, 0, 1440 by 900, heading `Eval 3`, `3 / 31`, 37 dots, 27 lines, focus on Close |
  | Esc | closed, focus on `Graph: Eval 3` |
  | Open, then the × button | closed, focus on `Graph: Eval 3` |
  | Eval 1 | `1 / 31`, previous disabled |
  | next | `Eval 2`, `2 / 31`, 90 dots, 112 lines |
  | previous | `Eval 1`, `1 / 31` |
  | Eval 1, next, then close (button, and again with Esc) | focus on `Graph: Eval 2` (after the close event; see note 3) |
  | Eval 4, previous, Esc | focus on `Graph: Eval 3` |
  | Held out 1 | `Held out 1`, `6 / 31` |
  | Q22 | `31 / 31`, next disabled |
  | Q21, focus next, Enter | `Q22`, next disabled, focus moved to previous |

- **E6** Every graph against its record, desktop, all 31: 2,408 dots and 2,932 lines (the 2,955 stored links less the 23 from an item to itself), each line matching a stored link by source, type, target and held. **0 problems.** Checked per dot: the type in its tooltip equals the stored line's; cited dots are circles of `r="9"` at fill opacity 1, other dots `r="3.5"` at 0.5, both in ink `rgb(1, 25, 54)`; all 39 unresolved names are `rect`, every other dot a `circle`; all 270 held items carry a dashed ring and no other item does; held lines are dashed at stroke opacity 0.5, every other line solid at 0.3. Cited: 125 dots. Per entry: Eval 3 has 37 items, 27 links, 1 unresolved name, 3 held items, 9 held lines; Eval 2 has 90 items, 114 links (2 to itself), 13 held items, 16 held lines, 7 cited; Q11 and Q16 cite none.
- **E7** Labels, desktop, all 31 graphs: 121 labels shown. Every label equals its id in stored case. None crosses a canvas edge, and no two shown cited labels overlap (measured from the rendered boxes). No uncited label shows until hovered or selected. Every cited label shows unless the dot is marked crowded (4 in all at this width, none in Eval 2).
- **E8** Fit: in the first view of all 31 graphs, at 1440 by 900 and at 390 by 844, every dot lies inside the canvas and none lies under the zoom buttons.
- **E9** Selection, Eval 3: a click on `0002#feature-design:46` (neighbours `0007`, `0002/AC-10`) gives it the ring `rgb(7, 160, 195)`. Those 3 dots stay at opacity 1 and the other 34 drop to 0.2; its 2 lines stay at 1, the other 25 drop to 0.2; both neighbours' labels show. The panel title becomes the id. A click on empty canvas clears the selection, nothing is dimmed, and the panel title is `Answer`.
- **E10** Switch, Eval 3: on, it hides 29 of 37 dots, the same set the check works out from the stored links on its own, and 22 of 27 lines. Off, 0 are hidden. Q11: the switch is disabled and the panel says `This answer cites no item.`
- **E11** Key (desktop): shown under the canvas, outside the `svg`, with six entries: Cited, Not cited, Held item, Held link, Unresolved name, Selected. Screenshot `desktop-eval3.png`.
- **E12** Moving around, Eval 2: a wheel turn zooms 2.23 times about the pointer (each dot within 1.1 px of where a zoom about that point puts it). Ten wheel turns leave the page scroll (2159.5) and the dialog and panel scroll (0) unchanged. A drag on empty canvas by (50, 30) moves every dot by 50.00 and 30.00 (spread under 0.001 px) and selects nothing. Reset puts every dot back within 0 px. `+` zooms 1.25 times and `−` returns exactly. The range runs from 0.50 to 6.00 times the fit. A dragged dot (all 90 dots moved), then `+`, then reset → every dot back within 0 px, still so a second later.
- **E13** Dragging a dot, Eval 3 (`0002/AC-10`) and Eval 2 (`0001#binding-rules:25`): over 20 pointer steps and after a 400 ms hold the dot stays under the pointer (error under 0.0001 px). Every neighbour moved during the drag (4 of 4, 8 of 8, the least by 6.8 px). An item selected before the drag is still the only one selected after it. Close and open again → every dot within 0 px of the first layout. Drag, next, previous → within 0 px. A press released after 2 px selects that dot and moves nothing.
- **E14** Pressing near a dot, Eval 2, on `0004#follow-up:8` (no other dot within 24 px of the probe points). Mouse: a click 11 px away selects it and one 16 px away selects nothing; hovering at 11 px shows its label and at 16 px marks nothing; a drag from 11 px moves that dot by the full (50, 30); a drag from 16 px pans every dot by (40, 20). Touch, on the phone: a tap 16 px away selects it and one 24 px away selects nothing; a finger drag from 16 px moves that dot by (40, 24).
- **E15** Answer view, Eval 1: the panel's question and verdict text equal the list's (`Model's own verdict: answered`); the 4 claims' text, labels included, equals the list's; numbers come from the list's `decimal-leading-zero` counter. Claim 01's `0008/AC-7` carries `href` to JobHunt `…/0008-app-shell-and-navigation/index.md?plain=1#L54`. Clicking it leaves the address unchanged and opens no tab. It selects the item and puts its dot at the canvas centre (479.5, 384.5 both); the scale ratio is 1.0000003.
- **E16** Item view: `0008/AC-7` shows eyebrow `AcceptanceCriterion`, title `0008/AC-7`, its stored text equal to the record's, `specs/0008-app-shell-and-navigation/index.md:54` linked to the same JobHunt line, and `Cited by claims 01, 02`. `0008/AC-5b` lists 8 links, in the record's order, each with `in` or `out`, its type, the other id and its phrase, and `no phrase stored` where the stored phrase is null. On `0009/AC-14`, the link from `0009#build-plan:9` reads `HELD`, and its link to itself shows once as `self CORRECTED_BY 0009/AC-14` (no line drawn, E6). Clicking `0009#requirements:5` there selects it. `Back to the answer` → title `Answer`, nothing selected. The all items list has 84 rows, the 5 cited first. Eyebrows: `Constraint · STRUCK` (`0021#feature-design:12`), `unresolved · UNRESOLVED NAME` (`unresolved:feature-14:feature-32`), `Constraint · HELD` (Eval 2, `0001#binding-rules:32`). Eval 3's `feature-6#6-entry-page-link-metadata-done:11` shows `<figure>` as text, and the panel holds 0 `figure` elements.
- **E17** In copies:
  - AC-41: claim 1 of Eval 1 also cites `9999/AC-1`, listed in its `rejected_ids`. Build exit 0. In the panel the id is plain text in a `P` with no `href` and no `data-item`. Clicking it selects nothing, the panel stays on `Answer`, and the address is unchanged.
  - AC-47: `0008#feature-design:11`'s location set to `no file stored`. Build exit 0. Its item view shows `no file stored` with no link.
  - Build failures, each exit 1 with no `index.html` written:

    | Case | Message |
    |---|---|
    | AC-65, Eval 1's first link targets `no-such/item` | `…q1.json: link 1 (0001#binding-rules:26 AMENDED_BY no-such/item) names no-such/item, which is not among the record's items` |
    | AC-66, an item of Eval 1 copied whole | `…q1.json: item id repeated: feature-14#14-fit-scoring-with-shown-reasoning-done-ga:8` |
    | AC-67, Eval 2 relabelled `Eval-1` | `'Eval 1' and 'Eval-1' both make the slug 'eval-1'` |
    | AC-68, `// </SCRIPT>` added to `graph.js` | `src/tracepath/gallery/assets/graph.js: holds '</script', which an inline script cannot carry` |
    | AC-68, `/* <!-- */` added to `d3-timer.min.js` | `src/tracepath/gallery/vendor/d3-timer.min.js: holds '<!--', which an inline script cannot carry` |

    (A first AC-66 attempt changed one item's id but not its stored line, and spec 0010's line check fired first. That is a mistake in how the case was made, not a fault in the build.)
- **E18** Network and repeatability: with a request listener on, opening Eval 2, Held out 1 and Q6 made 0 requests. Eval 2's 90 dots sit at identical screen positions in two loads: one opened right after load, and one after a reload with Eval 3 opened first. The only console errors in the session are the local server's `favicon.ico` 404s on the copy builds, which the page never asks for.
- **E19** Phone, 390 by 844, touch:
  - Layout: the page `scrollWidth` is 390, and the dialog's is 390 too. The canvas runs from y 60 to 439.8 (379.8 px tall, 45 percent of 844) and the panel from 484.3 to 844, so the graph sits above the panel. All six round buttons measure 40 by 40.
  - Key: hidden at first (`display: none`), with the Key button shown. A tap shows all six entries and sets `aria-expanded="true"`. Screenshots `phone-eval2.png`, `phone-eval2-key.png`.
  - A finger swipe up in the panel scrolls the panel from 0 to 617.5, while the page scroll (3254.5) and every dot stay put.
  - A one finger drag on empty canvas by (40, 25) moves every dot by 40.00 and 25.00, and the page does not scroll.
- **E20** Phone labels, all 31 graphs: 110 shown. Each is in stored case, 16 sit left of their dot, none crosses a canvas edge, and no two shown cited labels overlap.
  - Q2: `unresolved:0011:the-emergency-kill-switch-built-in-feature-3` reads `unresolved:0011:the-emergency-kill-switch-…`, while its tooltip keeps the full id.
  - Q17: `feature-11#11-job-search-results-list:1` sits left of its dot (label right edge 186, dot left edge 191), shortened to `feature-11#11-job-search-result…`. Panned with a finger until its dot sits 12 px from the left edge, the full id shows right of the dot (`phone-q17-panned.png`).
  - Eval 2: `0014/AC-20a` (cite order 1) keeps its label. The three crowded cited dots, `0014#decision:7` (3), `0014/AC-20` (4) and `0001#binding-rules:25` (7), would each overlap it.
  - `0001#binding-rules:25`'s label is hidden at first. It shows on mouse hover, hides again when the pointer leaves, shows when it is tapped, and shows when its neighbour `0001#binding-rules:28` is selected from the list (`phone-eval2-br28.png`).
- **E21** Colours: in the graph styles (`render.py`), `--yellow` and `--pink` never appear, and `--cyan` appears in `.gw-ring` (the selection ring) and in the panel's id buttons (`.gw-id` underline and hover). Those buttons are outside the canvas and the key, which is all AC-22 covers. The browser drew the ring in `rgb(7, 160, 195)` (E9).

## Per criterion

| Criteria | Status | Evidence |
|---|---|---|
| AC-1 | met | E3 |
| AC-2 | met | E4 |
| AC-3 to AC-11 | met | E5 |
| AC-12, AC-13 | met on all 31 graphs | E6 |
| AC-14, AC-16, AC-18, AC-19, AC-20 | met on all 31 graphs | E6 |
| AC-15, AC-17 | met | E7, E9, E20 |
| AC-21, AC-22 | met | E2, E9, E21 |
| AC-23 | met | E11, E19 |
| AC-24 | met | E10 |
| AC-25 | met at both sizes, all 31 graphs | E8 |
| AC-26 to AC-29a | met | E12 |
| AC-30 to AC-33 | met | E10 |
| AC-34, AC-35 | met | E9 |
| AC-36 to AC-40 | met | E15 |
| AC-41 | met in a copy | E17 |
| AC-42 to AC-46 | met | E15, E16 |
| AC-47 | met in a copy | E17 |
| AC-48 to AC-53 | met | E16 |
| AC-54 to AC-56 | met | E19 |
| AC-57 to AC-64 | met | E2, and E6 for the flags as drawn |
| AC-65 to AC-68 | met in copies and in tests | E2, E17 |
| AC-69 to AC-74 | met | E2, E3 |
| AC-75, AC-76 | met | E18 |
| AC-77 to AC-83 | met on Eval 2 and Eval 3 | E13, E12 for AC-81 |
| AC-84 to AC-86 | met | E14 |
| AC-87 to AC-90 | met | E7, E20 |
| AC-91, AC-92 | met | E19 |
| AC-93 | met at both sizes, all 31 graphs | E8 |
| AC-94 | met | E2 |
| Live on GitHub Pages (verify.md, After the merge) | **blocked until merge** | the Pages workflow publishes on a push to `main` |

## Findings

None of these blocks the merge. Each is a recommendation you may take or skip.

1. **The spec's total link count is off.** Spec 0011 says the shown records hold 3,114 links (Feature design, the contrast paragraph: "640 of 3,114"; References; and `rationale.md` line 7). The 31 records in `gallery/marks.json` hold 2,955. Every other figure on those lines checks out: 2,408 items, 270 held items, 522 held links, 39 unresolved names, 23 links to themselves, 25 pairs with more than one link, up to 138 links in a pack, 640 `UNCLASSIFIED`. So 640 is about 22 percent of the links, not the "20 percent" the Consequences give. This does not change what the page shows. Route: a one line spec edit, or let `/sync` carry it.
2. **A cited label can be drawn across another dot.** On the phone, Eval 2's top cluster draws `0014/AC-20a`'s label starting under a neighbouring cited dot, and `0008/AC-10b`'s across small dots (`phone-eval2.png`). AC-89 only keeps two labels apart, so nothing fails. The id stays readable in the tooltip and the panel, and nothing is hidden or misstated, so skipping this is reasonable. If you want it, the collision check in `arrangeLabels()` could also treat dots as obstacles.
3. **A note for `/test`, not a defect.** Focus goes back to the right Graph button inside the dialog's `close` event (as the spec says), which fires one task after the window closes. Read in the same instant as the click, focus is still on the button that first opened the window (Eval 1's after Eval 1, next, close), because the browser restores that on its own. My first reading caught exactly that instant. With a short wait, the button close, Esc and a keyboard opened case all land on the right button (E5). A reader never sees the gap, but a browser test of AC-6 should wait for the `close` event before it reads focus.

Also seen, no action suggested: verify.md says the phone canvas is 380 pixels tall. It measures 379.8, which is exactly 45 percent of 844.

## Not done in this run

- `verify.md` and the scope's `Verify it` box were not ticked. You asked for findings in `docs/reviews/` only, so the ticks are left for you to decide, as in the 2026-10-24 gallery run.
- The live check on GitHub Pages waits for the merge (see the table above).
- Only Chromium was driven. The spec already limits AC-76 to one browser, and other engines were not checked.
