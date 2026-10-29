# Check verify, answer graph files, 2026-10-28

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/gallery-graph-files` at `13fd2e5`, resuming the run at `7663a55`
**Spec**: [0011](../specs/0011-answer-graph/index.md) task 11 (graph files, AC-104 to AC-127a, AC-126 dropped 2026-10-28), checked against its [verify.md](../specs/0011-answer-graph/verify.md); also spec [0012](../specs/0012-gallery-readability/index.md) AC-84 and AC-111 to AC-116, and spec [0010](../specs/0010-answer-gallery/index.md) AC-58 and AC-63
**Verdict**: **pass**. Every criterion run in this session was met, and the two checks by hand passed. Nothing failed. One observation is recorded below. It is not a failure: it is spec 0012's existing design, to be decided separately after this merge.

This is a runtime check, not a code review. No code and no spec text was changed, no paid call was made, no model or subagent was started, and `eval/held-out.json` was never opened. The only repo edits are the ticks in `verify.md` and this file.

## Carried over from the run at 7663a55

As the engineer reported them, not rerun here: AC-55, AC-75, AC-78, AC-104, AC-105, AC-108 to AC-111, AC-109a, AC-115, AC-115a, AC-120, AC-123, AC-124. AC-104 and AC-105 were also seen again here (E1, E2). AC-126 is dropped by the spec (note under it in `index.md`), so it was not run.

## How it was run

- The page: `uv run tracepath gallery build --out <scratchpad>/site-13fd2e5` (exit 0, `✓ 31 entries`), served from that folder by `python3 -m http.server 8731 --bind 127.0.0.1`, and driven in Playwright's Chromium (build 1243) at 1400 by 900.
- A slow or failing file: Playwright request routing held a graph file back for a set time, or answered 404. For AC-112 to AC-114 and AC-122/122a, the file itself was moved out of the build, so the real server answered 404, and then put back.
- By hand, by the engineer, in Chrome: AC-118, and the typed address with Back.

Screenshots are in `/private/tmp/claude-501/-Users-ghaly-Documents-Work-Personal-tracepath/45c22fd0-4912-4f1b-a0d0-283e396a8487/scratchpad/`: `ac112-failed.png`, `ac114-retry.png`, `ac116-eval1-late.png`, `ac116-eval1-first.png`, `ac121-fail-after.png`, `ac121-fail-before.png`, `ac117-loading.png`, `ac117-drawn.png`. None shows a failure.

## Evidence

- **E1** Build: `graphs/` holds 31 files, `eval-1.js` … `q9.js`, nothing else (AC-105). The built `index.html` has no `<link>` and no `<script>` with a `src` (spec 0010 AC-58). The only site file any tag names is `https://ghalynho10.github.io/tracepath/preview.png` in a `meta` tag; every other address is the page itself or a GitHub link (spec 0010 AC-63).
- **E2** Tests: `uv run pytest tests/test_gallery_graph.py -k "no_graph_data_in_the_page or graph_file_shape or no_request_api or adds_a_script_for_a_graph_file or dialog_holds_the_status_words or writes_the_page_last"` → 8 passed (AC-104, AC-106, AC-107, AC-119, AC-119a, AC-125, AC-127, AC-127a).
- **E3** Failure (AC-112, AC-112a, AC-113, AC-122, AC-122a): with `eval-3.js` moved out, Graph on Eval 3 made one request, answered 404. The window stayed open with "This graph did not load. Close the window and open it again to try." The heading read "Graph", the counter was empty, there were 0 dots and an empty panel, previous, next, the switch, zoom in, zoom out and reset were all disabled, and the address read `#eval-3`. After close the address was empty. The console showed only the 404s for the file and `favicon.ico`.
- **E4** Retry (AC-114): file put back, same page, Graph pressed again → one new request for `eval-3.js`, then "Eval 3", "3 / 31", 37 dots.
- **E5** Newest graph wins (AC-116, AC-116a): `#eval-1`, then 100 ms later `#eval-3`, both files held back. Eval 1's file was served at 3.0 s with Eval 3's at 0.9 s, and the other way round, 0.8 s and 3.1 s. Both times the window ended on "Eval 3", "3 / 31", 37 dots, and stayed so after Eval 1's file arrived. While Eval 3 was still pending, the window stayed loading with 0 dots.
- **E6** Earlier failure (AC-121): Graph on Eval 1 with `eval-1.js` held back and then answered 404, `#eval-3` set while it waited. The 404 came after Eval 3 drew (2.5 s) and before it (0.6 s). Both times the failure words stayed hidden and Eval 3 drew, "3 / 31", 37 dots.
- **E7** Opening by address (AC-117, spec 0012 AC-84): a fresh tab at `#q9` with `q9.js` held 3 s. At 486 ms the window was open, showing "Loading the graph…", heading "Graph", 0 dots. At about 4 s it showed "Q9", "18 / 31", 90 dots, after one request. A first try waited for the page's load event, which also waits for the graph script, so its snapshot came after the draw. It was run again with `domcontentloaded`.
- **E8** The address on an open page (spec 0012 AC-111 to AC-114, AC-116), one page with a `hashchange` counter. Open Eval 2, next, previous and close fired 0 `hashchange` events and left `history.length` at 13. `#q4` opened Q4, "13 / 31", and `#q7` replaced it with Q7, "16 / 31", one `dialog.gw`, one open. `#not-an-entry` left Q7 open with no page error. `#q7`, then an empty fragment, closed the window.
- **E9** Back (spec 0012 AC-115): navigating to `#q4`, then `#q7`, then Back returned to `#q4` with Q4 drawn (its first labels `feature-5#5-design-system-ui-foundation-done:8 …`, different from Q7's `0015/AC-11 …`). A second Back left the address empty and the window closed.
- **E10** By hand, AC-118 (engineer, Chrome): the scratch build's `index.html`, opened by double click as `file://`, Graph on Eval 3 → "3 / 31", the graph drew, the panel started "Why is password sign in impossible on production?". The script file choice over `fetch()` holds, so the Follow up "run AC-118 by hand once" is answered.
- **E11** By hand, the typed address (engineer, Chrome, served page): open Eval 3 by its Graph button, type `#q4` (Q4 opened), type `#q7` (Q7 replaced it in the same window). Back showed Q4, Back again showed Eval 3, and a third Back left the gallery for the blank tab the engineer started from. This matches spec 0012 AC-85: a click adds no history step, it replaces the current entry, so the gallery's own entry had become `#eval-3`.

## Observation (not a failure)

- On desktop, Back with a graph open that was opened by a click leaves the gallery instead of closing the graph (E11). This is spec 0012's existing design (AC-85, a click adds no history step). The engineer will decide it separately after this merge.

## Not recorded elsewhere

- The spec 0012 and spec 0010 results above (E1, E7 to E9, E11) are recorded here only. Their own `verify.md` files were not touched, since this run verified spec 0011's task 11.
- The ticks in spec 0011's `verify.md` for the carried over steps say so, and name the run at `7663a55`.
- The live site steps under "After the merge" stay open until task 11 merges and the Pages run finishes.
