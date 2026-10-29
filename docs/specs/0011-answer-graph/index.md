# 0011. Answer graph

**Date**: 2026-10-24
**Status**: Accepted

## Summary

This spec adds one interactive graph to each answer on the gallery page. A Graph button on an entry opens a full window: the answer's items and links on the left, a reading panel on the right. Cited items are large and dark, held items have a dashed ring, unresolved names are squares, and a click on any item shows its text and a link to its exact line in JobHunt. The build works out every item's state in Python and writes it to a file for that entry, and a small script only draws and toggles from those flags. _Amended 2026-10-27: that file sits beside the page and loads when its graph opens. It used to be a block inside the page, and with 31 of them the page was too big for LinkedIn to read (AC-104 to AC-127a)._ The one library is d3-force (it only computes where the dots go), copied into the repository and pasted into the page.

## Requirements

**User stories**:
- As a reader of an answer, I want to see how the items it cites connect to each other and to the rest of what the model was sent, so I can judge the answer without reading a list of 90 rows.
- As that reader, I want to click any item and read its text and open its line in JobHunt, so I can check it myself.
- As that reader, I want held items and unresolved names to look different from the rest, so I know which parts of the pack were not fully trusted.
- As a reader on a phone, I want the same graph and the same panel, so the page is not a laptop only page.
- As the engineer, I want the build to decide every item's state, so the script cannot show a state the record does not hold.

**Acceptance criteria** (each holds one claim):

*Opening and closing*
- **AC-1** (amended 2026-10-26): With scripts running, each entry has a Graph button. _The button is the "Explore the graph" strip of [spec 0012](../0012-gallery-readability/index.md) (AC-65 to AC-69)._
- **AC-2** (amended 2026-10-26): With scripts off, the page shows no Graph button. _The strip leaves no gap ([spec 0012](../0012-gallery-readability/index.md) AC-70)._
- **AC-3**: A click on an entry's Graph button opens a full window showing that entry's graph.
- **AC-4**: The Esc key closes the window.
- **AC-5**: The window's close button closes it.
- **AC-6**: After the window closes, focus is on the Graph button of the graph that was showing.
- **AC-7**: The window shows the open graph's position in the page's order and the number of graphs, as `n / N`.
- **AC-8**: The next button opens the next entry's graph in page order.
- **AC-9**: The previous button opens the entry's graph before it.
- **AC-10**: On the first graph the previous button is disabled.
- **AC-11**: On the last graph the next button is disabled.

*What the graph shows*
- **AC-12**: The canvas has one dot for each item stored in the record, and no other dot.
- **AC-13**: The canvas has one line for each stored link between two different items, and no other line.
- **AC-14**: An item that is cited is drawn as a large dot (radius 9) filled with the ink colour.
- **AC-15**: An item that is cited is labelled with its id, unless AC-90 hides the label. _Amended 2026-10-25 for the collision rule of the visual pass._
- **AC-16**: An item that is not cited is drawn as a small, pale dot (radius 3.5, ink at 50 percent).
- **AC-17**: An item that is not cited has no label unless it is hovered, selected, or a neighbour of the selected item.
- **AC-18**: A held item has a dashed ring.
- **AC-19**: A held link is drawn dashed.
- **AC-20**: An unresolved name is drawn as a square, and every other item as a circle.
- **AC-21**: The selected item has a cyan ring.
- **AC-22**: The styles of the canvas and the key do not use the yellow of the marks. _Split 2026-10-25 after the code review; it also held AC-95 and AC-96._
- **AC-23**: The window carries a key that shows each of the six drawings above (cited, not cited, held item, held link, unresolved name, selected).
- **AC-24**: When the answer cites no item, the panel says "This answer cites no item."
- **AC-25**: When the window opens, the graph is scaled so every dot is inside the canvas.
- **AC-26**: The mouse wheel zooms the graph.
- **AC-27**: Dragging the canvas pans the graph.
- **AC-28**: The zoom in and zoom out buttons zoom the graph.
- **AC-29**: The reset button puts every dot back at the place of AC-76. _Reworded 2026-10-25 at the engineer's request; it said the button restores the view, which is now AC-29a._
- **AC-29a**: The reset button restores the view of AC-25.
- **AC-30**: Turning on the switch "Cited and neighbours only" hides every item that is neither cited nor a neighbour of a cited item.
- **AC-31**: Turning on that switch hides every line that touches a hidden item.
- **AC-32**: Turning the switch off shows them again.
- **AC-33**: When the answer cites no item, the switch is disabled.
- **AC-34**: Selecting an item dims every item and line except that item, its neighbours and the item's own lines. _Reworded 2026-10-25 after the code review; it said "the lines between them", which reads as keeping a line between two neighbours bright, which neither the code nor the Drawings table does._
- **AC-35**: A click on empty canvas clears the selection and returns the panel to the answer view.

*The reading panel*
- **AC-36**: With nothing selected, the panel shows the question as stored. _Amended 2026-10-26: markers and code words are drawn as the list draws them ([spec 0012](../0012-gallery-readability/index.md) AC-9, AC-14)._
- **AC-37** (amended 2026-10-26): With nothing selected, the panel shows the verdict block the list shows (the verdict wording and its captions, including "N of M claims failed a check" when spec 0010 AC-33 adds it), but not the mark ([spec 0012](../0012-gallery-readability/index.md) AC-81).
- **AC-38**: With nothing selected, the panel shows the claims in stored order, each with the labels spec 0010 AC-26 to AC-32 give it.
- **AC-39**: A cited id that is not rejected, in a claim shown in the panel, selects that item.
- **AC-40**: That selection moves the view to centre the item.
- **AC-41**: A rejected id in a claim shown in the panel is text and selects nothing.
- **AC-42** (amended 2026-10-26): A selected item's stored text is shown in full, with `code` and **bold** drawn from the item's `runs` ([spec 0012](../0012-gallery-readability/index.md) AC-19, AC-79).
- **AC-43**: A selected item's id and type are shown.
- **AC-44**: A selected item shows `HELD`, `STRUCK` or `HISTORY`, and `UNRESOLVED NAME`, for each of those that is true of it.
- **AC-45**: A selected item shows the numbers of the claims that cite it, in the two digit form the list uses (`01`).
- **AC-46**: A selected item with a file shows its location as a link built by spec 0010 AC-34 and AC-35.
- **AC-47**: A selected item with no file shows "no file stored" and no link (spec 0010 AC-36).
- **AC-48**: A selected item lists each of its links, in and out, with the link type, its direction, the other item's id, and the stored phrase it was read from. _Amended 2026-10-26: the phrase is drawn with `code` and **bold** formatted, from the link's `phrase_runs` ([spec 0012](../0012-gallery-readability/index.md) AC-99 to AC-101)._
- **AC-49**: A held link in that list shows `HELD`.
- **AC-50**: A link from an item to itself is listed in the panel, though it is drawn as no line.
- **AC-51**: The id of the other item in each listed link selects that item.
- **AC-52**: The panel has a list of all items, cited ones first, each one selecting that item.
- **AC-53**: Stored text containing markup, for example `<figure`, or `</script>`, appears in the panel as visible text and is not interpreted. _Amended 2026-10-26: this still holds inside a code or bold run; `graph.js` makes each run with `textContent` and never sets `innerHTML` ([spec 0012](../0012-gallery-readability/index.md) AC-10, AC-78)._

*On a phone*
- **AC-54**: At a window width of 720 pixels or less, the graph sits above the panel.
- **AC-55**: At that width the panel scrolls on its own.
- **AC-56**: At that width a one finger drag on the canvas pans the graph.

*The build and its data*
- **AC-57** (amended 2026-10-27): The build writes, for each entry, a graph file that holds every item and every link of its record. _It was a data block inside `index.html`; see the note under AC-104 to AC-127a._
- **AC-58** (amended 2026-10-27): The graph file holds no item's stored `line`.
- **AC-59**: An item's `cited` flag is true when some claim cites its id and that claim does not list it in `rejected_ids`, and false otherwise.
- **AC-60**: An item's `held` flag equals the record's stored `held` for it.
- **AC-61**: An item's `unresolved` flag is true when the type in its stored line is `unresolved`, and false otherwise.
- **AC-62**: An item's `neighbours` hold every other item joined to it by a stored link, and no item that is not. _Split 2026-10-25 after the code review; it also held AC-97, AC-98 and AC-99._
- **AC-63**: An item's `near_cited` flag is true when it is cited or one of its neighbours is, and false otherwise.
- **AC-64**: An item's `cited_by` is the numbers, in stored order, of the claims that cite it and do not reject it.
- **AC-65**: The build fails, exit 1, naming the record and the link, when a stored link's source or target is not among the record's items.
- **AC-66**: The build fails, exit 1, naming the record and the id, when two items of one record share an id.
- **AC-67**: The build fails, exit 1, naming both entries, when two entries make the same slug.
- **AC-68**: The build fails, exit 1, naming the script, when an inlined script holds `</script` or `<!--`, in any letter case.
- **AC-69** (amended 2026-10-27): In a graph file, the characters `<`, `>`, `&`, U+2028 and U+2029 are written as `\u` escapes. _They are no longer needed to keep a block from ending its script tag, but the same writer is kept, so one rule covers the data._
- **AC-70** (amended 2026-10-27): Parsing the data object in a graph file gives back each stored text exactly.
- **AC-71**: The page inlines d3-dispatch, d3-quadtree, d3-timer and d3-force, in that order.
- **AC-72**: Each inlined library file is followed by the licence text its package ships, copied word for word.
- **AC-73**: `src/tracepath/gallery/vendor/SOURCES.md` lists each of the four files in one row: package, version, file name and where it was taken from.
- **AC-74** (amended 2026-10-27): No tag in the HTML the build writes names a script, style or font file. _`graph.js` adds a script element for a graph file when a graph opens (AC-119); that element is not in the HTML the build writes._
- **AC-75** (amended 2026-10-27, _browser_): Opening a graph for the first time makes one network request, for that entry's file under `graphs/` on the page's own site, and no other. _It said "no network request". Opening it a second time makes none (AC-115)._
- **AC-76**: Two loads of the same graph in the same browser put every dot at the same place.

*Dragging a dot* (added 2026-10-25 at the engineer's request)
- **AC-77**: Dragging a dot moves that dot with the pointer.
- **AC-78**: Every neighbour moves while the dot is dragged. _Reworded 2026-10-25: it said the neighbours "move after it", but in the browser 2 of 13 settled further from the dropped dot._
- **AC-79**: A press on a dot released after moving less than 4 pixels selects that dot.
- **AC-80**: Dragging a dot 4 pixels or more neither selects an item nor clears the selection.
- **AC-81**: Dragging empty canvas moves every dot by the same distance in the same direction.
- **AC-82**: After a dot is dragged, closing and reopening the window puts every dot back at the place of AC-76.
- **AC-83**: After a dot is dragged, going to another answer by previous or next and coming back puts every dot back at the place of AC-76.

*Pressing a dot* (added 2026-10-25 at the engineer's request; the drawings are unchanged)
- **AC-84**: A mouse press whose nearest dot centre is within 12 pixels selects or drags that dot.
- **AC-85**: A touch press whose nearest dot centre is within 20 pixels selects or drags that dot.
- **AC-86**: A drag that starts with no dot centre within that reach pans the graph.

*Visual pass* (added 2026-10-25 at the engineer's request)
- **AC-87**: A dot's label shows the item id in its stored case. _Split 2026-10-25 after the code review; it also held AC-100, AC-101 and AC-102._
- **AC-88**: A label that would cross the canvas's right edge is drawn to the left of its dot when the left side has more room.
- **AC-89**: Where two cited items' labels would overlap, the label of the item cited first in claim order is shown.
- **AC-90**: The other cited item's label is hidden unless that item is hovered, selected, or a neighbour of the selected item.
- **AC-91**: At a window width of 720 pixels or less, the key shows only after its Key button is pressed.
- **AC-92**: At that width the canvas is 45 percent of the window's height.
- **AC-93**: In the view of AC-25, no dot lies under the zoom buttons.
- **AC-94**: An item's `cite_order` is its place in the order of first citation (claims in stored order, each claim's cites in stored order, rejected ids left out), and null when it is not cited.

*Split from AC-22, AC-62 and AC-87* (added 2026-10-25 after the code review, so each criterion holds one claim; the behaviour is unchanged)
- **AC-95**: The styles of the canvas and the key do not use the pink of the marks.
- **AC-96**: The styles of the canvas and the key use cyan only for the selection ring.
- **AC-97**: An item's `neighbours` list each id once.
- **AC-98**: An item's `neighbours` are in the order their first link appears among the stored links.
- **AC-99**: An item with a link to itself is not among its own `neighbours`.
- **AC-100**: A dot's label is shortened with "…" when it fits on neither side of its dot.
- **AC-101**: A dot's tooltip gives the item's full id.
- **AC-102**: The panel's title for a selected item gives its full id.

*The panel's source link* (added 2026-10-25 after the code review)
- **AC-103**: In the panel, a selected item's JobHunt link opens in a new tab. _So the open graph stays; the list's links, which spec 0010 governs, still open in the same tab._

*Graph files* (added 2026-10-27, ruled by the engineer). _Why: LinkedIn's Post Inspector refused the live page with "Maximum size for this input stream is 3145728 bytes". `index.html` was 4,817,451 bytes, and the 31 graph blocks were 3,834,664 of them (rebuilt and measured again on 2026-10-27 at 747365c: the same two numbers, 982,787 for the rest). Each entry's data now lives in its own file. This reverses spec 0010 AC-58's "nothing loaded separately" for graph data only; the styles, libraries and script stay inline._

- **AC-104**: `index.html` holds no graph data: it has no `<script type="application/json">` element.
- **AC-105**: A build into an empty folder writes `graphs/<slug>.js` for each entry and no other file under `graphs/`.
- **AC-106**: A graph file is one call, `tracepathGraph(<the slug as a JSON string>,<the data object>);`, followed by one newline, and nothing else.
- **AC-107**: In a graph file, the slug in the call, the `slug` field of the data object and the slug in the file's name are the same.
- **AC-108** (_browser_): A press on a Graph button opens the window at once, before the file has arrived, with the words "Loading the graph…" in the canvas's place.
- **AC-109** (_browser_): While the file loads, previous, next, the switch, zoom in, zoom out and reset are disabled.
- **AC-109a** (_browser_): While the file loads, the close button and Esc close the window.
- **AC-110** (_browser_): When the file arrives, the loading words go and the graph is drawn as AC-12 to AC-25 describe.
- **AC-111** (_browser_): When the file arrives, the controls of AC-109 are enabled, except where AC-10, AC-11 or AC-33 disables one.
- **AC-112** (_browser_): When the file fails to load, because it is missing or the reader is offline, the canvas's place reads "This graph did not load. Close the window and open it again to try."
- **AC-112a** (_browser_): After a failed load the window stays open.
- **AC-113** (_browser_): After a failed load, the address still reads `#<slug>` until the window closes.
- **AC-114** (_browser_): After a failed load, closing the window and pressing the same Graph button asks for the file again.
- **AC-115** (_browser_): A graph that has loaded is kept; opening it again makes no request.
- **AC-115a** (_browser_): Reaching a graph that has loaded again by previous or next makes no request.
- **AC-116** (_browser_): When the address fragment changes to another entry's slug while a graph is loading, the window ends on the graph of the newer slug.
- **AC-116a** (_browser_): In that case the earlier file's arrival draws nothing.
- **AC-117** (_browser_): Opening the page at `#<slug>` of an entry opens the window in the loading state, then draws that entry's graph.
- **AC-118** (_by hand_): With `index.html` and `graphs/` opened as plain files (`file://`), a graph opens. _Inferred to work because a script tag is not held to the cross origin rule that stops `fetch()` on `file://` in Chrome; not tested in this spec's session, and the Playwright tool there refuses `file:` URLs, so the engineer opens it by hand once at `/check verify`._
- **AC-119**: `graph.js` uses none of `fetch(`, `XMLHttpRequest`, `import(`, `new Image` or `sendBeacon`.
- **AC-119a**: `graph.js` adds a script element for a graph file. _The test looks for `createElement("script")` and `graphs/` in the script._
- **AC-120** (_browser_): When the window is closed while a graph's file is loading, the file's arrival draws nothing and does not reopen the window.
- **AC-121** (_browser_): When an earlier graph's file fails after the window has moved to another graph, the failure words are not shown over the newer graph.
- **AC-122** (_browser_): In the failed state the heading row reads "Graph" with no counter.
- **AC-122a** (_browser_): In the failed state previous, next, the switch, zoom in, zoom out and reset are disabled.
- **AC-123** (_browser_): When previous or next has focus and the window enters the loading state, focus moves to the close button.
- **AC-124** (_browser_): Entering the loading state empties the dots, lines and panel of the graph shown before, and unchecks the switch.
- **AC-125**: The dialog's markup holds the loading words, the failure words and the word "Graph" for the loading heading.
- ~~**AC-126** (_browser_): After the window closes with a file still pending, opening the same graph adds a new request for it.~~ _Dropped 2026-10-28, ruled by the engineer. `/check verify` at 7663a55 closed the window with a graph file still pending and pressed Graph again. `graph.js` added a second script element for the same file (`document.head` held `["eval-4.js","eval-4.js"]`), but Chromium handed it the download already running and sent no new request: one `GET /graphs/held-out-1.js` in a plain server's log with every graph request held 4 s, and one request under Playwright interception too. The graph still drew when that one download finished. The number stays so the others do not move. AC-114, a retry after a failed load, is unaffected._
- **AC-127**: The build writes `index.html` after every graph file.
- **AC-127a**: A build that cannot write a graph file exits 1 naming that file's path.

## Decision

**Chosen option**: Option 1: d3-force for layout only, vendored and inlined, with a hand written SVG drawing and a full window `<dialog>`.

`tracepath gallery build` computes each item's state and each item's neighbours in Python, writes them as one file per entry under `graphs/` (amended 2026-10-27; they were JSON blocks in the page), and pastes in four small ISC licensed files (d3-force 3.0.0, d3-dispatch 3.0.1, d3-quadtree 3.0.1, d3-timer 3.0.1) plus about 300 lines of script, which place the dots with d3-force and draw, highlight and toggle from the flags.

_Note on the Decision: Amended 2026-10-27, ruled by the engineer. Each entry's data moves out of `index.html` into its own file, loaded by a script element that `graph.js` adds when that graph opens (Option A of the amendment in [rationale.md](rationale.md)). Wherever this spec still says "data block", it now means that entry's graph file._

**Follows**: functional core with an imperative shell, as the project's own rule (the flags are pure functions of the record) · progressive enhancement (the list of spec 0010 works with scripts off, the graph adds to it) · vendoring a pinned dependency (copy a known version into the repository, record its version and where it came from; git records any later change to the files).

**Implementation skills**: `pydantic` (`pydantic/skills`, `.agents/skills/pydantic/`) · `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `uv` (`astral-sh/claude-code-plugins`, `.agents/skills/uv/`)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Mode and platform**: FEATURE, extending the gallery of spec [0010](../0010-answer-gallery/index.md). A static web page built by the Python CLI, now with a small inline script. No server, no database, no model call.

**Where it lives**: all in `src/tracepath/gallery/`.

| File | What it holds |
|---|---|
| `graph.py` (new, pure) | Frozen models and the functions that turn one `Entry` and its stored links into an entry's graph data, written as its graph file: flags, neighbours, `cited_by`, the slug, the position and the total |
| `records.py` (changed) | A frozen `StoredLink` model (`type`, `source`, `target`, `phrase`, `held`); `AskRecord` gains `links`; `StoredItem` gains `hop: int`; the build checks AC-65 to AC-67 |
| `render.py` (changed) | The Graph button, the one `<dialog>`, the two hidden loading and failure elements in the dialog, the vendored files and the script inlined, the new styles, and a `data-item` attribute on each cited, unrejected id in a claim's citation link |
| `assets/graph.js` (new) | The script: position, draw, select, pan, zoom, switch, previous and next. It decides nothing about an item's state |
| `vendor/` (new) | `d3-dispatch.min.js`, `d3-quadtree.min.js`, `d3-timer.min.js`, `d3-force.min.js`, each package's `LICENSE`, and `SOURCES.md` |

The files in `assets/` and `vendor/` are read in the command's shell (`cli.py` or a small loader beside `load_entries`) and handed to `render_page`, so `render.py` stays pure. `SOURCES.md` is a table with the columns package, version, file, url, which the AC-73 test parses.

**Data model sketch**: nothing is stored beyond the records that exist. Each entry gets one graph file, `graphs/<slug>.js`, loaded only when its graph is opened (see *The graph files*). _Amended 2026-10-27: it was a block, `<script type="application/json" id="graph-<slug>">`, inside `index.html`, parsed when the graph opened._

| Field | Type | Rule |
|---|---|---|
| `slug` | string | The label lowercased, each run of characters other than ASCII letters and digits turned into one `-`, no `-` at either end. `Eval 3` gives `eval-3`, `Held out 2` gives `held-out-2`, `Q7` gives `q7`. Unique across entries (AC-67), and never empty (the build fails if a label gives an empty one). It names the graph file and the entry; it is not in the address | _Note 2026-10-26: the slug is also in the address: `#<slug>`, and the `id` of each entry's `article` ([spec 0012](../0012-gallery-readability/index.md) AC-82 to AC-92)._
| `label` | string | The marks entry's label, shown in the window's heading row |
| `position`, `total` | integers | This entry's place in page order (sections in `Section` order, entries in marks file order), counted from 1, and the number of entries |
| `previous`, `next` | slug or null | The entries either side in that order; null at either end |
| `cited_count` | integer | How many items have `cited` true |
| `items` | list | One per stored item, cited items first, then by `hop`, then by id in Python string order; the order is fixed so the layout is repeatable (AC-76) |
| `links` | list | One per stored link, in stored order |

Each item: `id`, `type` (from the stored line), `text`, `hop`, `cited`, `held`, `unresolved`, `radius`, `marker` (`STRUCK`, `HISTORY` or null), `cited_by` (claim numbers), `cite_order` (its place in the order of first citation, or null; AC-94), `neighbours` (distinct ids), `near_cited`, `link_ids` (positions in `links`), `source` (the link of spec 0010 AC-34 and AC-35, or null), `location` (the shown words, such as `specs/0008/index.md:54`, `specs/0008/index.md, whole file` when it has a file and no line, or `no file stored`). There is no `shape` field: the script draws a square when `unresolved` is true.

Each link: `type`, `source`, `target`, `phrase`, `held`, `drawn` (false for a link from an item to itself).

`radius` is a constant per state in `graph.py`, so a test can read it: cited 9, not cited 3.5, in pixels at the starting scale. These are starting values, tuned once in the visual pass on the three largest packs (Eval 2, Eval 4, Held out 1, each at 90 items).

The data block never holds an item's stored `line` (AC-58); everything the script needs from it, the type, the marker, the location and the link, is a field above, computed once by the grammar of spec 0010.

**Link grammar and the checks it reuses**: unchanged. `graph.py` takes `ItemLine` and `item_link` from `citations.py`, so a graph link is built by the same function, from the same checked file and line, as a list link (AC-46).

**The graph files** (added 2026-10-27, ruled by the engineer):

- *What a file holds.* `graph.py` gains a pure function that turns an `EntryGraph` into the file's text: `tracepathGraph(<slug as JSON>,<data>);` and a newline, where `<data>` is what `data_block` writes today (same fields, same `\u` escapes of AC-69). The shell writes one file per entry into `DIR/graphs/` (creating the folder), as UTF-8 since the data keeps its non ASCII text as typed, and writes `index.html` last, so a failure partway leaves no page that points at missing files. A write error names the path that failed, not always `index.html`. `render.py` stays pure. A file is JavaScript, not a JSON document; the wrapper is why (a script tag cannot hand back bare JSON).
- *How it loads (Q1, ruled).* `graph.js` first defines `window.tracepathGraph`, which keeps the object it is given in a map by slug. To load a slug it adds a script element whose address is `graphs/<slug>.js` resolved against `document.baseURI`, so the page works at any path. On the element's `load` event the script checks the map holds that slug; on `error`, or a `load` with nothing in the map, the load has failed. The element is removed either way. Two loads of one slug at once share one element; but once a load has failed or the window has closed with the file still pending, the next open of that slug adds a fresh element. After a close with a load pending that fresh element may not make a new request: Chromium can hand it the download already running (seen 2026-10-28; AC-126 was dropped, see the note under it), so a load stuck pending ends only when the browser gives up or the page reloads. Accepted: it was never seen in real output, it cannot lose money or data, and it is visible, because the window keeps reading "Loading the graph…". A retry after a failed load is a real new request (AC-114). There is no timeout of the script's own. A loaded graph stays in the script's memory (`laid`), so a second open makes no request (AC-115); a failed load stores nothing, so the next press asks again (AC-114).
- *Why not `fetch()`.* Chrome refuses `fetch()` of a `file://` address (inferred from how the browser behaves; not tested here), so a page opened by double click would show Graph buttons that cannot open. A script tag has no such rule (inferred), so AC-118 is expected to hold. The graph data is not private, so a script file costs no secrecy. `fetch()` would give a clean `.json` file and an HTTP status; the cost of losing both is accepted.
- *Opening (Q2 and Q4, ruled).* `open(slug)` sets `state` first (with `slug` set and `graph` null), replaces the address with `#<slug>` as today, shows the window if it is shut, and puts the window in its *loading state*, which also stops any live layout (`stopLive()`), clears a drag in progress, runs `hover(null)`, empties both SVG layers and the panel, and unchecks the switch (AC-124): the heading row reads "Graph" with no counter, the canvas and the panel are empty, the words "Loading the graph…" show in the canvas's place, and previous, next, the switch, zoom in, zoom out and reset are disabled (AC-108, AC-109). When the graph is already in memory, `open` skips the loading state and draws at once. There is no `wanted` token. When the file arrives, `open` draws only if the window is open, `state.slug` is still this slug and `state.graph` is null; otherwise the graph stays in memory and nothing is drawn. That one test covers a typed slug that came later (AC-116, AC-116a) and a window closed meanwhile (AC-120), because `open` always sets `state` first and `close` leaves it as it was, with the window shut. Then the heading, counter, previous and next come from the file as before (AC-7 to AC-11 are unchanged), and the controls are enabled (AC-110, AC-111).
- *Failing.* The same spot reads "This graph did not load. Close the window and open it again to try." and the window stays open, with the address still `#<slug>` until it closes (AC-112, AC-112a, AC-113). The failed state keeps the loading state's heading ("Graph", no counter) and keeps all six controls disabled, because previous and next come from the file; the canvas and panel stay empty (AC-122, AC-122a). A failure is judged by the same test as an arrival: if the window has moved to another slug or shut, a late `error` shows nothing (AC-121). There is no Try again button, because no load failure has been seen; closing and pressing the Graph button again is the retry. There is no timeout of the script's own; the browser's decides.
- *The words.* Both sentences are written in the dialog's markup in `render.py`, as `<p class="gw-status" data-gw="loading" hidden>` and `data-gw="failed"`, placed inside `.gw-view` after the `</svg>` (the key test at `tests/test_gallery_graph.py` line 424 keeps passing), and the word "Graph" for the loading heading is a `data-loading-heading` attribute on the dialog. The script only shows one of them and reads the heading word from the attribute, so the page's words stay in Python (AC-125).
- *What stays inline.* The list, with the question, verdict and claims the panel's answer view clones; the buttons; the dialog; the four libraries; `graph.js`; the preview tags. Only the data of the 31 graphs leaves the page. The answer view needs the file only for its all items list, so it too waits for the file.
- *Build notes for the code.* `close` restores focus from `state.slug`, so `state` is set before the window is shown, with `graph` null until the file arrives. Every handler that reads `state.graph` returns while `graph` is null: pointerdown, pointermove, pointerup, pointercancel, wheel, resize and the panel click; the disabled controls cover the buttons (the key button reads no `state.graph`). Entering the loading state moves focus to the close button when focus sat on previous or next, because both become disabled; arrival leaves focus where it is (AC-123). The `swapped` test in today's `open` is read at the start of `open`, before the window shows, and not again at arrival.
- *On page load and the typed address (Q4, ruled).* A page opened at `#q9` registers the buttons and then calls `open("q9")`, which now opens the window in the loading state (AC-117; spec 0012 AC-84 holds, its "opens" now means "opens, then fills"). A `hashchange` to a slug calls `open` the same way, so the newest slug wins (AC-116; spec 0012 AC-111 and AC-112 hold). A `hashchange` to an empty fragment closes the window, loading or not (spec 0012 AC-116). Previous and next cannot be pressed while loading, so a swap never races a load.
- *Size (spec 0010 AC-78).* `index.html` falls to about 982,787 bytes, which leaves 2,162,941 bytes under LinkedIn's 3,145,728. The 31 files together hold the 3,834,664 bytes the blocks held, plus about 30 bytes of wrapper each; the largest block was 156,649 bytes. The inline part per entry was not measured, so this spec does not say how many more entries fit.
- *Stale files.* GitHub Pages serves a file with a cache lifetime of its own (inferred from how Pages behaves; not checked on its docs here). For a short while after a deploy that changes an entry, a reader's browser may hold the older graph file beside the newer page. The records are append only and the graph files change only when the build code changes, so this is accepted, with no version number in the file name (the filter below).
- *Filter applied to this amendment.* A load failure, a stale file and a lost race were not seen in real output, so none gets a guard beyond the words above and the newest wins rule, which costs one check of `state.slug`. The one failure seen in real output is the size, and it gets AC-78 in spec 0010.

**Layout**: d3-force runs once, in the browser, to the end, before anything is drawn: `simulation.stop()` and then 300 `tick()` calls, the number d3's own cooling schedule uses. It lays out around (0, 0) and the view transform fits the result to the canvas, so positions never depend on the window size. The forces, as starting values: `forceLink` (distance 40), `forceManyBody` (strength -60), `forceCollide` (the item's radius plus 2), and a weak `forceX` and `forceY` (0.06) toward (0, 0), so the 9 percent of items with no link stay near the rest. Nothing is random: d3 places the first positions on a fixed spiral and breaks ties with a fixed seed, which I checked on 2026-10-24 by running two 300 tick layouts of a 90 node graph with 89 links and getting identical positions (in Node's `vm` sandbox, not in a browser). A different browser engine may compute the spiral's sine and cosine in the last digits differently, so AC-76 holds within one browser. Positions are never stored. The layout does not run again when the switch flips: hidden items keep their place, and the fit and the reset always cover every dot. The pan and zoom range is from half of the fitted scale to six times it.

**Drawing**: plain SVG made by the script from the flags, so each dot and line is a real page element with a native `<title>` tooltip (its id and type). SVG, not canvas, because there are at most 90 dots and 138 lines, and elements give hit testing and screenshots for free. Pan and zoom are the script's own, on pointer events, the wheel and three buttons; d3-zoom and d3-selection are not used. Pinch to zoom is not supported in this version; the zoom buttons cover a phone.

**Drawings** (every state is carried by size, fill, line or shape, never by one of the marks' colours):

| State | Drawing |
|---|---|
| Cited | Radius 9, filled with the ink colour, mono label (its id, in its stored case); where cited labels overlap, the one cited first keeps its label (AC-89, AC-90) |
| Not cited | Radius 3.5, ink at 50 percent, no label until hovered, selected, or next to the selection |
| Held item | A dashed ring 2.5 pixels outside the dot, in ink |
| Held link | A dashed line in ink at 50 percent |
| Unresolved name | A square with the same area, not a circle |
| Selected | A solid cyan ring 6 pixels outside the dot, and its neighbours stay full strength while the rest dim to 20 percent |
| Other link | A hairline in ink at 30 percent; on the selected item, its links turn full ink and carry an arrowhead at the target end |

Contrast against the white page, by my calculation: ink at 50 percent is about 3.4 to 1, and cyan about 3.1 to 1, both above the 3 to 1 that graphics need. Links at 30 percent ink are about 2.0 to 1, below it. They are accepted at that strength because they are the quiet background connections and the panel lists every link of a selected item; the held links, which carry a meaning of their own, are drawn at 50 percent. `UNCLASSIFIED` links (640 of 2,955 in the shown records, about 22 percent) are drawn like any other of their kind; the type is in the panel. Where two items have more than one link between them (25 pairs in the shown records), the lines lie on top of one another, so a held dashed link can be hidden under a solid one; this is accepted, and the panel lists each link.

**Style**: spec 0010's design B tokens, unchanged (`--paper`, `--ink`, `--cyan`, `--rule`, the Helvetica stack and mono stack). From the local reference `design-notes/aicodingdictionary.com.md` (kept out of git; this spec cites it, code and CI never read it) only layout and type ideas are taken: a split window with the graph about two thirds and the panel one third, a hairline between them and none within the panel, a large poster title (the item id, or "Answer" for the answer view) over quiet body text, small uppercase eyebrow labels with the entry's label and the `n / N` counter in the same row, round 40 pixel buttons with a hairline border (close, previous, next, zoom), and mono labels on the dots, ids in their stored case (the reference's capitals are not used, the engineer's ruling of 2026-10-25). A label that would cross the canvas's right edge sits left of its dot, and the fit keeps the dots clear of the zoom buttons. Its greys, grain and branding are not used. Reduced motion: nothing moves on its own; the only transition is a 0.2 second opacity fade, switched off under `prefers-reduced-motion`.

**The window**: one native `<dialog>`, opened with `showModal()`, so Esc, focus trapping and the backdrop come from the browser. Its content is replaced when another entry is shown. Build notes, settled by the cross check on 2026-10-25:
- The dialog's own default size, margin, padding and border are reset so it fills the window; body scrolling is locked while it is open, and the panel uses `overscroll-behavior: contain`.
- Focus goes to the close button on open. Focus restore on close runs in the dialog's `close` event, not in the buttons' handlers, so Esc, the button and the browser's own back gesture take one path (AC-6).
- If the focused previous or next button becomes disabled (AC-10, AC-11), focus moves to the other one.
- The heading row shows the entry's `label` beside the counter, and the dialog takes `aria-labelledby` pointing at that heading. Each Graph button carries `aria-label="Graph: <label>"`.
- The Graph buttons are written hidden in the HTML, the page has `[hidden] { display: none !important }`, and the script shows them only when `HTMLDialogElement` exists (AC-1, AC-2).
- Switch and selection reset (switch off, nothing selected) on every open and every swap by next or previous.
- Selecting an item that the switch has hidden, from a panel link or the all items list, first turns the switch off.
- Item ids contain `#`, `:` and `/` (for example `0008#build-plan:6`). The script keeps a `Map` from id to element and never puts an id in an element `id` or a selector.
- The key's sample drawings sit outside the canvas, so the dot and line counts of AC-12 and AC-13 count the canvas only.
- The graph has no tab stop on dots. The all items list (AC-52) and the claim ids are the keyboard route.

**The panel**: two views in one scrolling column.
- *Answer view* (nothing selected; _amended 2026-10-26: `graph.js` finds the three parts anywhere inside the entry, because the new layout no longer makes them direct children, [spec 0012](../0012-gallery-readability/index.md) AC-76, AC-77_): a clone of the entry's own question, verdict block and claim list from the list on the page, so labels (AC-38) cannot differ from the list's. Each cited, unrejected id in the list's citation link carries `data-item="<id>"`, which does nothing on the list. Clicks on a `[data-item]` link inside the panel are caught, the browser's navigation to JobHunt is stopped, and that item is selected (AC-39). The JobHunt link of that item is reached from the item view (AC-46). Then the all items list (AC-52).
- *Item view*: eyebrow (type and state words), poster title (the id), the stored text, the location or its link, the claim numbers, then the links in and out. The script fills it from the data block with `textContent`, never `innerHTML`, so stored text stays text (AC-53). Links are listed in stored order, each marked `out` when the item is the link's source, `in` when it is the target and `self` for a loop, which is listed once.

**Previous and next**: they read `previous` and `next` from the data block and swap the open graph (AC-8, AC-9).

**Moving around**: a pointer that moves under 4 pixels between down and up is a click; more is a pan and never selects or clears. The wheel zooms about the pointer, from a listener that is not passive so the page does not scroll or the browser zoom on a trackpad pinch. The zoom buttons zoom by 1.25 times about the canvas centre. A selection made from the panel centres the item without changing the scale (AC-40); a click on the canvas does not move the view.

**On a phone** (720 pixels and under): the dialog fills the screen; a grid of two rows puts the canvas on top (45 percent of the dynamic viewport height, set in the visual pass of 2026-10-25; it was 55) and the panel below it, scrolling on its own. The key folds behind one Key button, so the panel keeps more of the screen. The canvas ignores page scrolling for touches (`touch-action: none`), so a one finger drag pans it.

**Command surface**: `uv run tracepath gallery build --out DIR` writes `DIR/index.html`, `DIR/preview.png` and, since 2026-10-27, `DIR/graphs/<slug>.js` for each entry (AC-105). The options are unchanged. _It used to write the single `DIR/index.html`._ The build does not delete anything already in `DIR/graphs/`; a file left from an earlier build under a slug that no longer exists is not read by the page and is not published by the workflow, which builds into an empty folder.

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| Draw a dot | Which items exist; each item's `id` and `text` | The record's stored `items`, one dot each (AC-12) |
| Draw a dot | `hop` (also the order of `items`) | The item's stored `hop`, now read by `StoredItem` (it agrees with the stored line's reach on all 2,408 shown items, checked 2026-10-25) |
| Draw a line | Which links exist, their type, ends and phrase | The record's stored `links` (new for the gallery, read by `StoredLink`) |
| Draw a line | `drawn` | False when the link's source equals its target, else true |
| Draw a dot | `cited` | The record's `claims`: an id in a claim's `cites` and not in that claim's `rejected_ids` |
| Draw a dot | `held` | The item's stored `held` |
| Draw a dot | `unresolved`, `type`, `marker`, `location` | Parsed from the item's stored `line` by `parse_item_line` of spec 0010 (the line is not shipped to the browser); `location` words follow the list's `_link` ("whole file" for a file with no line) |
| Draw a dot | `neighbours`, `link_ids`, `near_cited`, `cited_by` | Derived in `graph.py` from the links and claims above (AC-59 to AC-64) |
| Draw a dot | `radius` | A constant per state in `graph.py` |
| Draw a dot | Its position | d3-force, run in the browser from the order of `items` and the `links` (AC-76); never stored |
| Show the switch state | `cited_count` | The number of items with `cited` true |
| Show a source link | `source`, `location` | `item_link` and the parsed line of spec 0010 (AC-46, AC-47) |
| Show the answer view | Question, verdict, claims, labels and their two digit numbers | The entry's own rendered list, cloned (AC-36 to AC-38, AC-45) |
| Show the heading row | `label`, `position`, `total`, `previous`, `next` | `label` of the marks entry; the rest computed in `graph.py` from page order |
| Name a data block | `slug` | Computed from `label` by the rule in the data model (AC-67) |
| Request a graph file | The address `graphs/<slug>.js` | The Graph button's `data-graph` (the slug) and `document.baseURI` (amended 2026-10-27) |
| Write a graph file | The file's text and its place `DIR/graphs/<slug>.js` | The entry's `EntryGraph` and `--out`, by the shell (AC-105, AC-106) |
| Show the loading and failure words | Two sentences | Constants in the dialog's markup in `render.py` (AC-108, AC-112) |
| Decide whether to draw after a load | whether the window is open, `state.slug`, `state.graph` | `state`, set by the newest `open(slug)` call, from a click, the address on load, or a typed fragment (AC-116, AC-120) |
| Show the key | The six drawings | A constant fragment of SVG and words in `render.py` |
| Inline the library | The four files, their licences and `SOURCES.md` | `src/tracepath/gallery/vendor/`, read by the shell (AC-71 to AC-73) |

**Key invariants**:
- The script decides nothing about an item's state. It reads `cited`, `held`, `unresolved`, `radius`, `neighbours` and `near_cited` and draws them (AC-57 to AC-64).
- The graph holds exactly the stored items and links of the record: no item added, none dropped, and a link whose end is missing fails the build rather than being skipped (AC-12, AC-13, AC-65).
- Every source link on the graph is built by spec 0010's `item_link` from a file and line the build already checked against the snapshot.
- Stored text reaches the page only escaped in the data block (AC-69, AC-70) and only through `textContent` or the page's own escaped list in the panel (AC-53).
- With scripts off, the page is the list of spec 0010, with no dead control (AC-2).
- The page carries no timestamp of the build, and opening a graph makes one request, for its own file on the page's own site, and no other (AC-75). _Amended 2026-10-27; it said the graph makes no request._
- `index.html` holds no graph data (AC-104), and the script adds no element that loads a resource other than the one script for a graph file (AC-119a).

**Security model**: the page is public and holds only stored records, the engineer's marks and links to public repositories. The new risk is the inline script reading stored text: it is covered by AC-53, AC-68, AC-69 and AC-70. GitHub Pages cannot set a Content Security Policy header, so there is no second line of defence; that is acceptable because the page loads no third party content and the script never turns stored text into markup. No secret is read; no compliance scope applies. _Added 2026-10-27: a graph file is JavaScript the browser runs, so stored text reaches an executing script, not only a parsed block. The wrapper is a constant, the data is one object literal, and the escapes of AC-69 are kept, so the rule that keeps stored text as text is the same one (AC-70). The graph files come from the same origin as the page; no third party file is added._

**Configuration required**: none. The Pages workflow is unchanged: its `src/tracepath/**` path filter already covers the new code and the vendored files, so a change to either deploys the page on a push to `main`. Pages action versions are as in spec 0010.

**Critical test scenarios** (each maps to acceptance criteria in ## Requirements; the browser steps run at `/check verify`, the rest in pytest):
- Happy path on real data: build from `artifacts/asks/` and `gallery/marks.json`; every entry has a graph file, and its items and links equal its record's, verifies **AC-12, AC-13, AC-57, AC-58**. _Amended 2026-10-27: the tests in `tests/test_gallery_graph.py` that read the inline blocks (the `_BLOCK` pattern and the `blocks` fixture, the one block per entry test, the no stored line test, `refers_to_no_script`, the escape and round trip tests, the hostile text test and the helper that reads `[0][1]`) read `DIR/graphs/*.js` instead: strip the constant wrapper, then `json.loads`. A new module fixture `site` (the output folder, a Path) is added and `page` is derived from it, so about twenty tests keep a `str` page. The escape and round trip tests (lines 661 and 671) call the new file text function and strip the wrapper._
- Flags against the record: for each of the 31 records, every item's `cited`, `held`, `unresolved`, `neighbours`, `near_cited` and `cited_by` equal an independent recomputation from the record, verifies **AC-59 to AC-64, AC-97, AC-98**.
- Edge: a record that cites no item (Q11 and Q16 cite none) has `cited_count` 0 and no cited item, verifies **AC-24, AC-33**.
- Edge: a link from an item to itself (23 exist) has `drawn` false and is in its item's `link_ids`, verifies **AC-13, AC-50**.
- Edge: an item with a link to itself is not among its own neighbours, verifies **AC-99**.
- Edge: two items with two links between them (25 such pairs exist) list that neighbour once, verifies **AC-97**.
- Styles: the graph's styles and script name neither the yellow nor the pink of the marks, and cyan only in the selection ring's rule, verifies **AC-22, AC-95, AC-96**.
- Failure: a fixture link whose target is not an item, two items with one id, and two labels with one slug each exit 1 with the record named, verifies **AC-65, AC-66, AC-67**.
- Failure: a fixture script holding `</script` and another holding `<!--` each exit 1, verifies **AC-68**.
- Edge: stored text containing `</script>`, `<figure`, `&` and U+2028 survives a write and a parse of the data block unchanged, verifies **AC-53, AC-69, AC-70**.
- Guard: `SOURCES.md` has one row per vendored file, the page holds each licence text verbatim, and the files are in dependency order, verifies **AC-71, AC-72, AC-73**.
- Isolation: the built page has no `src=` or `<link` pointing at another file, and the build still passes with sockets blocked, verifies **AC-74**.
- Browser: open Eval 3 (37 items), then Eval 2 (90 items, 114 links) at 1440 and at 390 pixels wide; check every drawing, select an item, follow its link, use the switch, previous and next, and the network log, verifies **AC-1 to AC-11, AC-14 to AC-21, AC-23, AC-25 to AC-32, AC-34 to AC-52, AC-54 to AC-56, AC-75, AC-76**.
- Browser, the panel's source link: on Eval 1, select `0008/AC-7` and follow its location link; JobHunt opens in a new tab and the graph stays open with the item selected, verifies **AC-103**. A static check that the script gives that link `target="_blank"` and `rel="noopener"` runs in pytest.
- Browser, scripts off: the page shows no Graph button and the list is unchanged, verifies **AC-2**.
- Browser, reset after a drag: drag a dot in Eval 2, zoom in, then press reset; every dot is back at its first place and the view is the first view, verifies **AC-29, AC-29a**.
- Browser, dragging a dot: on Eval 3 and Eval 2, drag a cited dot; it stays under the pointer, every neighbour moves, a press that moves under 4 pixels selects instead, a drag keeps the selection as it was, a drag on empty canvas moves every dot alike, and closing and reopening, or next then previous, restores the first layout, verifies **AC-77 to AC-83**.
- Browser, pressing near a dot: on Eval 2, press 9 pixels from each small dot, between crowded dots at the smallest zoom, 11 and 16 pixels away with a mouse, and 16 and 24 pixels away with a finger; the nearest dot within reach is chosen, and a drag from further away pans, verifies **AC-84 to AC-86**.
- Browser, visual pass: every graph at 1440 and at 390 pixels wide; labels in stored case, none cut at an edge, shortened with "…" only when they fit on neither side, with the full id in the tooltip and the panel's title, no two shown cited labels overlapping, a hidden one shown on hover, selection or next to the selection; on a phone the key behind its Key button and the canvas at 45 percent; no dot under the zoom buttons in the first view, verifies **AC-87 to AC-93, AC-100 to AC-102**.
- Data: every item's `cite_order` equals an independent recomputation from its record's claims, verifies **AC-94**.
- Graph files, added 2026-10-27, on the real build: `index.html` has no `application/json` element; `graphs/` holds one `<slug>.js` per entry and nothing else; each file is the wrapper, the slug, the object and a newline, with the slug equal in the call, the object and the file name, verifies **AC-104, AC-105, AC-106, AC-107**.
- Static, added 2026-10-27: `graph.js` adds a script element for a graph file and holds none of `fetch(`, `XMLHttpRequest`, `import(`, `new Image` or `sendBeacon`, verifies **AC-119, AC-119a**. This replaces `test_script_makes_no_request`, which forbade `src` and so cannot stay as written.
- Static, added 2026-10-27, verifies **AC-125, AC-127, AC-127a**: the dialog's markup holds both sentences and the heading word; a build whose `graphs/` cannot be written (a file standing where the folder should be) exits 1 naming the path, and no `index.html` is left behind from that run.
- Existing tests that stay as they are: the inline script break out refusal (AC-68) still covers the scripts the page inlines; the graph files are not inlined, so it does not read them. `tests/test_gallery.py` line 636 (`<script(?! type="application/json")[^>]`) changes to forbid every `<script` that has an attribute, since the page no longer has a JSON block (spec 0010 AC-58).
- Browser, added 2026-10-27, over `127.0.0.1` (the Playwright tool refuses `file:`): press Graph on Eval 3 with the network throttled → the window opens at once with "Loading the graph…", the six controls disabled and close working, then the graph draws and the controls enable; exactly one request, for `graphs/eval-3.js`, verifies **AC-75, AC-108, AC-109, AC-110, AC-111**. Open it again, and reach it again by next then previous → no request, verifies **AC-115**.
- Browser, failure, added 2026-10-27: build into a folder, delete `graphs/eval-3.js`, press Graph → the failure words show, the window stays open, the address reads `#eval-3`; close, restore the file, press again → it loads, verifies **AC-112, AC-113, AC-114**.
- Browser, the address, added 2026-10-27: open `…/#q9` with the network throttled → the window opens loading, then draws Q9; with a throttled network, set the fragment to `#eval-1` and at once to `#eval-3` → the window ends on Eval 3 and Eval 1's late file draws nothing, verifies **AC-116, AC-117**.
- By hand, added 2026-10-27: double click the built `index.html` (a `file://` address) and press Graph on Eval 3 → it opens, verifies **AC-118**. If Chrome refuses, record that here and decide again; AC-118 is the one claim of this amendment resting on an inference.

## Build plan

Approach: Tracer Bullet (the project default). The first slice is one real entry, from record to a graph that opens, so the whole route (stored links read, flags computed, library inlined, dialog, drawing, click) is proven on a small pack before it is thickened and before it reaches the 90 item packs.

1. [x] Slice 1, the thread. Read `links` into `AskRecord` and `hop` into `StoredItem`; add `graph.py` with the flags for one entry; add `vendor/` (the four files from the npm packages at the versions in the Decision, each `LICENSE`, `SOURCES.md` with the version and source) and `assets/graph.js`; render a Graph button, the dialog, the data block and the inlined script for Eval 3 first, then every entry; the dots and lines are drawn and a click selects a dot. Satisfies **AC-1, AC-2, AC-12, AC-13, AC-57, AC-58, AC-71, AC-72, AC-73, AC-74**
2. [x] Slice 1, check it in a browser. Build to a scratch folder and open Eval 3: the dialog opens and closes, the dots are placed, a click selects. The Pages workflow needs no change; the page goes live on merge. Satisfies **AC-3, AC-4, AC-5, AC-6, AC-25**
3. [x] Slice 2, the states. Cited, not cited, held, held link, unresolved and selected drawings, the dim on select, the key, the switch, and the no cited item case. Satisfies **AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-30, AC-31, AC-32, AC-33, AC-34, AC-35, AC-59, AC-60, AC-61, AC-62, AC-63, AC-64, AC-95 to AC-99** (AC-95 to AC-99 split from AC-22 and AC-62 on 2026-10-25)
4. [x] Slice 3, the panel. The `data-item` attribute on the list's citation links, the cloned answer view, the item view with its link, claim numbers, links in and out, and the all items list. Satisfies **AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50, AC-51, AC-52, AC-53**
5. [x] Slice 4, moving around. Pan, wheel, zoom buttons, reset, previous and next with the counter, a repeatable layout. Satisfies **AC-7, AC-8, AC-9, AC-10, AC-11, AC-26, AC-27, AC-28, AC-29, AC-75, AC-76**
   - [x] Added 2026-10-25: dragging a dot, with d3-force running live so its neighbours follow, on a fresh copy of the layout each open; reset restores that layout too. Satisfies **AC-29, AC-29a, AC-77, AC-78, AC-79, AC-80, AC-81, AC-82, AC-83**
6. [x] Slice 5, the phone layout. Stacked window, touch pan, the 40 pixel buttons. Satisfies **AC-54, AC-55, AC-56**
   - [x] Added 2026-10-25: a press acts on the nearest dot centre within 12 pixels (20 for a touch), found with d3-quadtree's `find`; the dot within reach also shows as hovered. Satisfies **AC-84, AC-85, AC-86**
7. [x] Slice 6, the guards. The three build failures, the inline script check, the escaping and its round trip test, the vendor table test, the self contained test. Satisfies **AC-65, AC-66, AC-67, AC-68, AC-69, AC-70**
8. [x] Visual pass, settled before it starts: build to a scratch folder, screenshot Eval 3, Eval 2, Held out 1 and Q16 at 1440, 768 and 390 pixels, tune the layout constants and the radii once against the three 90 item packs, and compare to the reference's layout; screenshots stay in the scratchpad, never committed. Satisfies **AC-23, AC-25** (no new criterion)
9. [x] Amend spec 0010's three lines that say no JavaScript or no graph, and its Follow up and scope rows 17 and 18, as a dated note pointing here (see Follow up). Satisfies the spec record, no AC
10. [x] Fixes from the code review of 2026-10-25 (`docs/reviews/2026-10-25-feat-answer-graph.md`): split AC-22, AC-62 and AC-87 into one claim each, reword AC-34 to match the code, and open the panel's JobHunt link in a new tab. Satisfies **AC-103** (AC-100 to AC-102 split from AC-87, already built by the visual pass)

11. [x] Graph files (added 2026-10-27, ruled by the engineer; branch `feat/gallery-graph-files`). In `graph.py`, a pure function for a graph file's text; in `cli.py`, write `DIR/graphs/<slug>.js` for each entry; in `render.py`, drop the data block and add the two hidden loading and failure elements to the dialog; in `graph.js`, define `tracepathGraph`, load a file by a script element on open, add the loading state, the failure state, the draw test on `state` (AC-116, AC-120, AC-121) and the null `graph` guards (see *The graph files*). Change the tests named under Critical test scenarios, and update `verify.md`. Satisfies **AC-57, AC-58, AC-69, AC-70, AC-74, AC-75, AC-104 to AC-127a except the dropped AC-126**. Done when the built `index.html` is under 3,145,728 bytes (spec 0010 AC-78), and after the merge and the Pages run the engineer checks the live URL in LinkedIn's Post Inspector.

## Consequences

**Positive**:
- A reader sees how the cited items connect, what else the model was sent, and which parts were held or unresolved, without reading 90 rows.
- Every state on the graph is computed and tested in Python against the record, so the script cannot show a state the record does not hold.
- The list stays in one file and still works with scripts off. _Amended 2026-10-27: it no longer holds the graphs; each graph is a file beside it. The list and its links work offline as before; a graph opens when its file can be reached._
- The one library is small (17 KB raw, about 7 KB gzipped), has an ISC licence, and its version and source are recorded.

**Negative / tradeoffs**:
- The page grows. Today it is 776 KB raw and 81 KB gzipped. The data for 31 graphs adds about 1.5 MB raw (measured on 2026-10-24: 1.8 MB of JSON with the stored lines, from which the `line` field and the repeated link lists come out), roughly 0.4 MB gzipped. Each graph's data is parsed only when opened. _Corrected 2026-10-27: that estimate was wrong. The blocks came to 3,834,664 bytes, the page to 4,817,451, and LinkedIn refused it. The data now sits in 31 files, so the page is about 983 KB again (AC-104)._
- _Added 2026-10-27:_ a graph needs a second request. If a file cannot be reached, the graph does not open and the window says so (AC-112); the list is unaffected. The page and its files must be published together, which the Pages workflow does because it uploads the whole `site` folder (`pages.yml`, `path: site`, read on 2026-10-27).
- _Added 2026-10-27:_ for a short time after a deploy a browser may hold an older graph file beside a newer page (see *The graph files*). Accepted.
- _Added 2026-10-27:_ `index.html` is no longer one self contained file, so saving the page from a browser or sending the one file by email loses the graphs. The list stays whole.
- A third party file lives in git. d3-force's last release is 3.0.0 from 2021 and its repository was last pushed on 2023-12-30 (researcher check, 2026-10-24); it is still what d3 7.9.0 (2024-03-12) ships. Pinning makes this a non issue until the project wants a newer one.
- There is no JavaScript test runner. pytest covers the page the build writes and the flags; the script's own behaviour (click, pan, switch, the window) is checked in a browser at `/check verify`, and nothing re runs it on every push. A regression in the script is not caught by CI.
- No pinch to zoom on a phone. The zoom buttons and one finger pan cover it.
- There is no address for a graph: a reader cannot send a link that opens one graph. It was cut on 2026-10-25 as outside the Done when and the most failure prone part of the script (see Follow up).
- The layout settles in the browser from d3's cooling schedule, so a change to d3-force, the starting values or the order of `items` moves every dot. Pinning the files and fixing the order keep it repeatable within one browser, and the visual pass is the only judge of how it looks.
- Links at 30 percent ink are about 2.0 to 1 against the page, below the 3 to 1 for graphics. They are the quiet connections and the panel lists each link, so this is accepted; held links, which carry a meaning, are at 50 percent.
- About 22 percent of links are `UNCLASSIFIED` and are drawn like the rest; the graph says no more about them than the stored type does. Where two items have two links between them, one line can hide the other.
- A graph of 90 items is still dense on a phone. Labels only on cited items, the switch, and the zoom buttons are what keep it readable.

**Neutral**:
- Spec 0010's page statements about "no JavaScript" and its Follow up for this slice are updated by a dated note (Build plan task 9). Its AC-58 still holds, since scripts are inline.
- The list's citation links gain a `data-item` attribute that does nothing outside the panel.
- New folders `src/tracepath/gallery/assets/` and `src/tracepath/gallery/vendor/`; no change to `pyproject.toml`, the workflow, or the command.
- The dialog element and `touch-action` are supported by current browsers (inferred from the platform, not checked against browser data here).

## Follow-up

- [x] Amend spec 0010: its Feature design says "no JavaScript", its Decision says "with no JavaScript", its Consequences say "no search, filter or graph", its Feature design says the build does not read the records' `links`, and its Follow up lists this slice as open. Add a dated amendment note on each pointing at this spec, and tick the Follow up. The build task 9 does it.
- [ ] Reconcile scope features 17 and 18 and the Deferred "Visual UI" entry once built: feature 18's Done when is this spec's AC-3, AC-14 to AC-21, AC-42, AC-46 and AC-48.
- [ ] Shareable link to one graph: an address fragment that opens a graph and selects an item. Cut from this spec on 2026-10-25. _Note 2026-10-26: the part that opens a graph is taken into [spec 0012](../0012-gallery-readability/index.md) (AC-82 to AC-92), written as `#<slug>`, set by `history.replaceState`, with an unknown slug opening the page as usual. Selecting an item by the link stays deferred._ If it comes back, settle first how the address is written (replace, not push, and the close path), how a bad slug or item is handled, and how an id holding `#`, `:` and `/` is encoded.
- [x] Read the four LICENSE files from the packages when vendoring, and copy each word for word. This spec checked the licence of `d3-force` and `d3` from their repositories, but did not read the four packages' own LICENSE files. _Done 2026-10-25 (task 1): each LICENSE was read from its npm tarball after the tarball's sha1 matched the registry's `dist.shasum`; all four are the same 731 byte ISC text, copied unchanged with `cp`._
- [x] Check in a real browser that the four UMD files load from plain script tags in the order given. This spec checked it in Node's `vm` sandbox only (task 2 does it). _Done 2026-10-25 (task 2, and every slice after): in Chromium through Playwright the four files load from plain inline script tags in that order and every graph lays out. Other browser engines were not checked._
- [ ] Decide later whether the other data (the 13 records the page does not show) deserves a graph, and whether a link between two entries' shared items is worth drawing. Neither is in this spec.
- [ ] Pinch to zoom, if a reader asks for it.
- [ ] Added 2026-10-27: run AC-118 by hand once (the built page as a plain file) when task 11 is built, and write the result beside the criterion. If Chrome refuses a script file on `file://`, the choice of a script file over `fetch()` loses its one advantage and should be decided again.
- [ ] Added 2026-10-27: after the merge and the Pages run, run LinkedIn's Post Inspector on https://ghalynho10.github.io/tracepath/ and on `…/#q9`, and write the result in spec 0010's Follow up.
- [ ] Goal: one shared graph of every shown answer's items, where picking a question zooms to its items. Deferred until link resolution improves (scope features 7 and 8): today the 947 items of the 31 packs form 224 separate pieces, 173 with no link, so answers have no section to zoom to. Revisit then; the drawing, flags, panel and d3 setup carry over. _Recorded 2026-10-25 by the engineer, who kept one graph per answer for now._
- [x] Visual pass (task 8): show item ids in their stored case, never in capitals. This replaces "mono uppercase" for the dot labels in Drawings and Style. _Engineer's ruling, 2026-10-25._

## References

**Project sources** (verifiable, in this repo):
- `AGENTS.md`: the functional core rule, the stack and the Tracer Bullet approach.
- Spec [0010](../0010-answer-gallery/index.md): the page, design B tokens, AC-24, AC-26 to AC-36, AC-56 and AC-58, and its Follow up naming this slice.
- `docs/scope/scope.md`, feature 18: the intent, the Done when and the open questions this spec answers.
- `src/tracepath/gallery/render.py` and `citations.py`: the styles, the claim and verdict functions (`_citation`, `_claims`, `_verdict`), `_link` and `item_link`.
- Measured on 2026-10-24 and 2026-10-25 from `artifacts/asks/` and `gallery/marks.json`: 31 entries, up to 90 items and 138 links in a pack, 2,408 items and 2,955 links in all, 39 unresolved names, 270 held items, 522 held links, 23 links from an item to itself, 25 item pairs with more than one link, no duplicate item id, no link whose end is not an item, stored `hop` equal to the line's reach on every item, item ids holding `#`, `:` and `/`.
- `design-notes/aicodingdictionary.com.md` and its screenshot: a local style reference, git ignored, layout and type ideas only.
- Cross check of 2026-10-25, a read only pass by another model, whose gaps are settled in the Feature design.
- Measured on 2026-10-27 by rebuilding the page at 747365c (`uv run tracepath gallery build`, no API call): 4,817,451 bytes in all, 31 blocks of 3,834,664 bytes (largest 156,649, smallest 40,155), 982,787 for the rest. The same numbers as the engineer's live measure.
- LinkedIn Post Inspector, run by the engineer on 2026-10-27: "We did not scrape the content because it's size was larger than our threshold. Maximum size for this input stream is 3145728 bytes".
- `.github/workflows/pages.yml`, read on 2026-10-27: the build step is `uv run tracepath gallery build --out site` and the upload step's `path` is `site`.

**Practices & standards**:
- Progressive enhancement: the page works without scripts and the graph adds to it.
- Vendoring a pinned dependency, with its licence and where it came from.
- Native `<dialog>` for modal windows (inferred from the platform; no browser documentation was opened for this spec).
- Non text contrast of 3 to 1 for graphics that carry meaning (WCAG 2.2, success criterion 1.4.11; cited from memory, the standard was not opened for this spec).

**Links** (web verified by the researcher on 2026-10-24 unless marked):
- d3-force licence (ISC): https://raw.githubusercontent.com/d3/d3-force/main/LICENSE
- d3 licence (ISC), version 7.9.0 released 2024-03-12: https://raw.githubusercontent.com/d3/d3/main/LICENSE
- d3-force 3.0.0 minified file, 8,300 bytes (also fetched and run by me): https://cdn.jsdelivr.net/npm/d3-force@3.0.0/dist/d3-force.min.js
- React Flow licence (MIT), version 12.12.0, requires React: https://raw.githubusercontent.com/xyflow/xyflow/main/LICENSE
- vis-network licence (Apache 2.0 or MIT), version 10.1.2: https://raw.githubusercontent.com/visjs/vis-network/master/LICENSE-MIT
- Cytoscape.js licence (MIT), version 3.34.4: https://raw.githubusercontent.com/cytoscape/cytoscape.js/master/LICENSE
- Sigma.js licence (MIT), version 4.0.3, needs graphology: https://raw.githubusercontent.com/jacomyal/sigma.js/main/LICENSE.txt
