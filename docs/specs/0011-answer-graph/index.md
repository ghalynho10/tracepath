# 0011. Answer graph

**Date**: 2026-10-24
**Status**: In Progress

## Summary

This spec adds one interactive graph to each answer on the gallery page. A Graph button on an entry opens a full window: the answer's items and links on the left, a reading panel on the right. Cited items are large and dark, held items have a dashed ring, unresolved names are squares, and a click on any item shows its text and a link to its exact line in JobHunt. The build works out every item's state in Python and writes it into the page, and a small script only draws and toggles from those flags. The one library is d3-force (it only computes where the dots go), copied into the repository and pasted into the page.

## Requirements

**User stories**:
- As a reader of an answer, I want to see how the items it cites connect to each other and to the rest of what the model was sent, so I can judge the answer without reading a list of 90 rows.
- As that reader, I want to click any item and read its text and open its line in JobHunt, so I can check it myself.
- As that reader, I want held items and unresolved names to look different from the rest, so I know which parts of the pack were not fully trusted.
- As a reader on a phone, I want the same graph and the same panel, so the page is not a laptop only page.
- As the engineer, I want the build to decide every item's state, so the script cannot show a state the record does not hold.

**Acceptance criteria** (each holds one claim):

*Opening and closing*
- **AC-1**: With scripts running, each entry has a Graph button.
- **AC-2**: With scripts off, the page shows no Graph button.
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
- **AC-15**: An item that is cited is labelled with its id.
- **AC-16**: An item that is not cited is drawn as a small, pale dot (radius 3.5, ink at 50 percent).
- **AC-17**: An item that is not cited has no label unless it is hovered, selected, or a neighbour of the selected item.
- **AC-18**: A held item has a dashed ring.
- **AC-19**: A held link is drawn dashed.
- **AC-20**: An unresolved name is drawn as a square, and every other item as a circle.
- **AC-21**: The selected item has a cyan ring.
- **AC-22**: The styles of the canvas and the key use neither the yellow nor the pink of the marks, and use cyan only for the selection ring.
- **AC-23**: The window carries a key that shows each of the six drawings above (cited, not cited, held item, held link, unresolved name, selected).
- **AC-24**: When the answer cites no item, the panel says "This answer cites no item."
- **AC-25**: When the window opens, the graph is scaled so every dot is inside the canvas.
- **AC-26**: The mouse wheel zooms the graph.
- **AC-27**: Dragging the canvas pans the graph.
- **AC-28**: The zoom in and zoom out buttons zoom the graph.
- **AC-29**: The reset button restores the view of AC-25.
- **AC-30**: Turning on the switch "Cited and neighbours only" hides every item that is neither cited nor a neighbour of a cited item.
- **AC-31**: Turning on that switch hides every line that touches a hidden item.
- **AC-32**: Turning the switch off shows them again.
- **AC-33**: When the answer cites no item, the switch is disabled.
- **AC-34**: Selecting an item dims every item and line except that item, its neighbours and the lines between them.
- **AC-35**: A click on empty canvas clears the selection and returns the panel to the answer view.

*The reading panel*
- **AC-36**: With nothing selected, the panel shows the question as stored.
- **AC-37**: With nothing selected, the panel shows the verdict line the list shows, including "N of M claims failed a check" when spec 0010 AC-33 adds it.
- **AC-38**: With nothing selected, the panel shows the claims in stored order, each with the labels spec 0010 AC-26 to AC-32 give it.
- **AC-39**: A cited id that is not rejected, in a claim shown in the panel, selects that item.
- **AC-40**: That selection moves the view to centre the item.
- **AC-41**: A rejected id in a claim shown in the panel is text and selects nothing.
- **AC-42**: A selected item's stored text is shown in full.
- **AC-43**: A selected item's id and type are shown.
- **AC-44**: A selected item shows `HELD`, `STRUCK` or `HISTORY`, and `UNRESOLVED NAME`, for each of those that is true of it.
- **AC-45**: A selected item shows the numbers of the claims that cite it, in the two digit form the list uses (`01`).
- **AC-46**: A selected item with a file shows its location as a link built by spec 0010 AC-34 and AC-35.
- **AC-47**: A selected item with no file shows "no file stored" and no link (spec 0010 AC-36).
- **AC-48**: A selected item lists each of its links, in and out, with the link type, its direction, the other item's id, and the stored phrase it was read from.
- **AC-49**: A held link in that list shows `HELD`.
- **AC-50**: A link from an item to itself is listed in the panel, though it is drawn as no line.
- **AC-51**: The id of the other item in each listed link selects that item.
- **AC-52**: The panel has a list of all items, cited ones first, each one selecting that item.
- **AC-53**: Stored text containing markup, for example `<figure`, or `</script>`, appears in the panel as visible text and is not interpreted.

*On a phone*
- **AC-54**: At a window width of 720 pixels or less, the graph sits above the panel.
- **AC-55**: At that width the panel scrolls on its own.
- **AC-56**: At that width a one finger drag on the canvas pans the graph.

*The build and its data*
- **AC-57**: The build writes, for each entry, a data block that holds every item and every link of its record.
- **AC-58**: The data block holds no item's stored `line`.
- **AC-59**: An item's `cited` flag is true when some claim cites its id and that claim does not list it in `rejected_ids`, and false otherwise.
- **AC-60**: An item's `held` flag equals the record's stored `held` for it.
- **AC-61**: An item's `unresolved` flag is true when the type in its stored line is `unresolved`, and false otherwise.
- **AC-62**: An item's `neighbours` are the distinct ids at the other end of each stored link that touches it, in the order their first link appears, leaving out itself.
- **AC-63**: An item's `near_cited` flag is true when it is cited or one of its neighbours is, and false otherwise.
- **AC-64**: An item's `cited_by` is the numbers, in stored order, of the claims that cite it and do not reject it.
- **AC-65**: The build fails, exit 1, naming the record and the link, when a stored link's source or target is not among the record's items.
- **AC-66**: The build fails, exit 1, naming the record and the id, when two items of one record share an id.
- **AC-67**: The build fails, exit 1, naming both entries, when two entries make the same slug.
- **AC-68**: The build fails, exit 1, naming the script, when an inlined script holds `</script` or `<!--`, in any letter case.
- **AC-69**: In a data block, the characters `<`, `>`, `&`, U+2028 and U+2029 are written as `\u` escapes.
- **AC-70**: Parsing a data block gives back each stored text exactly.
- **AC-71**: The page inlines d3-dispatch, d3-quadtree, d3-timer and d3-force, in that order.
- **AC-72**: Each inlined library file is followed by the licence text its package ships, copied word for word.
- **AC-73**: `src/tracepath/gallery/vendor/SOURCES.md` lists each of the four files in one row: package, version, file name and where it was taken from.
- **AC-74**: The page refers to no script, style or font file.
- **AC-75**: Opening a graph makes no network request.
- **AC-76**: Two loads of the same graph in the same browser put every dot at the same place.

## Decision

**Chosen option**: Option 1: d3-force for layout only, vendored and inlined, with a hand written SVG drawing and a full window `<dialog>`.

`tracepath gallery build` computes each item's state and each item's neighbours in Python, writes them as JSON beside each entry, and pastes in four small ISC licensed files (d3-force 3.0.0, d3-dispatch 3.0.1, d3-quadtree 3.0.1, d3-timer 3.0.1) plus about 300 lines of script, which place the dots with d3-force and draw, highlight and toggle from the flags.

**Follows**: functional core with an imperative shell, as the project's own rule (the flags are pure functions of the record) · progressive enhancement (the list of spec 0010 works with scripts off, the graph adds to it) · vendoring a pinned dependency (copy a known version into the repository, record its version and where it came from; git records any later change to the files).

**Implementation skills**: `pydantic` (`pydantic/skills`, `.agents/skills/pydantic/`) · `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `uv` (`astral-sh/claude-code-plugins`, `.agents/skills/uv/`)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Mode and platform**: FEATURE, extending the gallery of spec [0010](../0010-answer-gallery/index.md). A static web page built by the Python CLI, now with a small inline script. No server, no database, no model call.

**Where it lives**: all in `src/tracepath/gallery/`.

| File | What it holds |
|---|---|
| `graph.py` (new, pure) | Frozen models and the functions that turn one `Entry` and its stored links into the page's graph data: flags, neighbours, `cited_by`, the slug, the position and the total |
| `records.py` (changed) | A frozen `StoredLink` model (`type`, `source`, `target`, `phrase`, `held`); `AskRecord` gains `links`; `StoredItem` gains `hop: int`; the build checks AC-65 to AC-67 |
| `render.py` (changed) | The Graph button, the one `<dialog>`, one data block per entry, the vendored files and the script inlined, the new styles, and a `data-item` attribute on each cited, unrejected id in a claim's citation link |
| `assets/graph.js` (new) | The script: position, draw, select, pan, zoom, switch, previous and next. It decides nothing about an item's state |
| `vendor/` (new) | `d3-dispatch.min.js`, `d3-quadtree.min.js`, `d3-timer.min.js`, `d3-force.min.js`, each package's `LICENSE`, and `SOURCES.md` |

The files in `assets/` and `vendor/` are read in the command's shell (`cli.py` or a small loader beside `load_entries`) and handed to `render_page`, so `render.py` stays pure. `SOURCES.md` is a table with the columns package, version, file, url, which the AC-73 test parses.

**Data model sketch**: nothing is stored beyond the records that exist. Each entry gets one JSON data block, `<script type="application/json" id="graph-<slug>">`, parsed only when its graph is opened.

| Field | Type | Rule |
|---|---|---|
| `slug` | string | The label lowercased, each run of characters other than ASCII letters and digits turned into one `-`, no `-` at either end. `Eval 3` gives `eval-3`, `Held out 2` gives `held-out-2`, `Q7` gives `q7`. Unique across entries (AC-67), and never empty (the build fails if a label gives an empty one). It names the data block and the entry; it is not in the address |
| `label` | string | The marks entry's label, shown in the window's heading row |
| `position`, `total` | integers | This entry's place in page order (sections in `Section` order, entries in marks file order), counted from 1, and the number of entries |
| `previous`, `next` | slug or null | The entries either side in that order; null at either end |
| `cited_count` | integer | How many items have `cited` true |
| `items` | list | One per stored item, cited items first, then by `hop`, then by id in Python string order; the order is fixed so the layout is repeatable (AC-76) |
| `links` | list | One per stored link, in stored order |

Each item: `id`, `type` (from the stored line), `text`, `hop`, `cited`, `held`, `unresolved`, `radius`, `marker` (`STRUCK`, `HISTORY` or null), `cited_by` (claim numbers), `neighbours` (distinct ids), `near_cited`, `link_ids` (positions in `links`), `source` (the link of spec 0010 AC-34 and AC-35, or null), `location` (the shown words, such as `specs/0008/index.md:54`, `specs/0008/index.md, whole file` when it has a file and no line, or `no file stored`). There is no `shape` field: the script draws a square when `unresolved` is true.

Each link: `type`, `source`, `target`, `phrase`, `held`, `drawn` (false for a link from an item to itself).

`radius` is a constant per state in `graph.py`, so a test can read it: cited 9, not cited 3.5, in pixels at the starting scale. These are starting values, tuned once in the visual pass on the three largest packs (Eval 2, Eval 4, Held out 1, each at 90 items).

The data block never holds an item's stored `line` (AC-58); everything the script needs from it, the type, the marker, the location and the link, is a field above, computed once by the grammar of spec 0010.

**Link grammar and the checks it reuses**: unchanged. `graph.py` takes `ItemLine` and `item_link` from `citations.py`, so a graph link is built by the same function, from the same checked file and line, as a list link (AC-46).

**Layout**: d3-force runs once, in the browser, to the end, before anything is drawn: `simulation.stop()` and then 300 `tick()` calls, the number d3's own cooling schedule uses. It lays out around (0, 0) and the view transform fits the result to the canvas, so positions never depend on the window size. The forces, as starting values: `forceLink` (distance 40), `forceManyBody` (strength -60), `forceCollide` (the item's radius plus 2), and a weak `forceX` and `forceY` (0.06) toward (0, 0), so the 9 percent of items with no link stay near the rest. Nothing is random: d3 places the first positions on a fixed spiral and breaks ties with a fixed seed, which I checked on 2026-10-24 by running two 300 tick layouts of a 90 node graph with 89 links and getting identical positions (in Node's `vm` sandbox, not in a browser). A different browser engine may compute the spiral's sine and cosine in the last digits differently, so AC-76 holds within one browser. Positions are never stored. The layout does not run again when the switch flips: hidden items keep their place, and the fit and the reset always cover every dot. The pan and zoom range is from half of the fitted scale to six times it.

**Drawing**: plain SVG made by the script from the flags, so each dot and line is a real page element with a native `<title>` tooltip (its id and type). SVG, not canvas, because there are at most 90 dots and 138 lines, and elements give hit testing and screenshots for free. Pan and zoom are the script's own, on pointer events, the wheel and three buttons; d3-zoom and d3-selection are not used. Pinch to zoom is not supported in this version; the zoom buttons cover a phone.

**Drawings** (every state is carried by size, fill, line or shape, never by one of the marks' colours):

| State | Drawing |
|---|---|
| Cited | Radius 9, filled with the ink colour, mono uppercase label (its id) |
| Not cited | Radius 3.5, ink at 50 percent, no label until hovered, selected, or next to the selection |
| Held item | A dashed ring 2.5 pixels outside the dot, in ink |
| Held link | A dashed line in ink at 50 percent |
| Unresolved name | A square with the same area, not a circle |
| Selected | A solid cyan ring 6 pixels outside the dot, and its neighbours stay full strength while the rest dim to 20 percent |
| Other link | A hairline in ink at 30 percent; on the selected item, its links turn full ink and carry an arrowhead at the target end |

Contrast against the white page, by my calculation: ink at 50 percent is about 3.4 to 1, and cyan about 3.1 to 1, both above the 3 to 1 that graphics need. Links at 30 percent ink are about 2.0 to 1, below it. They are accepted at that strength because they are the quiet background connections and the panel lists every link of a selected item; the held links, which carry a meaning of their own, are drawn at 50 percent. `UNCLASSIFIED` links (640 of 3,114 in the shown records) are drawn like any other of their kind; the type is in the panel. Where two items have more than one link between them (25 pairs in the shown records), the lines lie on top of one another, so a held dashed link can be hidden under a solid one; this is accepted, and the panel lists each link.

**Style**: spec 0010's design B tokens, unchanged (`--paper`, `--ink`, `--cyan`, `--rule`, the Helvetica stack and mono stack). From the local reference `design-notes/aicodingdictionary.com.md` (kept out of git; this spec cites it, code and CI never read it) only layout and type ideas are taken: a split window with the graph about two thirds and the panel one third, a hairline between them and none within the panel, a large poster title (the item id, or "Answer" for the answer view) over quiet body text, small uppercase eyebrow labels with the entry's label and the `n / N` counter in the same row, round 40 pixel buttons with a hairline border (close, previous, next, zoom), and mono uppercase labels on the dots. Its greys, grain and branding are not used. Reduced motion: nothing moves on its own; the only transition is a 0.2 second opacity fade, switched off under `prefers-reduced-motion`.

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
- *Answer view* (nothing selected): a clone of the entry's own question, verdict line and claim list from the list on the page, so labels (AC-38) cannot differ from the list's. Each cited, unrejected id in the list's citation link carries `data-item="<id>"`, which does nothing on the list. Clicks on a `[data-item]` link inside the panel are caught, the browser's navigation to JobHunt is stopped, and that item is selected (AC-39). The JobHunt link of that item is reached from the item view (AC-46). Then the all items list (AC-52).
- *Item view*: eyebrow (type and state words), poster title (the id), the stored text, the location or its link, the claim numbers, then the links in and out. The script fills it from the data block with `textContent`, never `innerHTML`, so stored text stays text (AC-53). Links are listed in stored order, each marked `out` when the item is the link's source, `in` when it is the target and `self` for a loop, which is listed once.

**Previous and next**: they read `previous` and `next` from the data block and swap the open graph (AC-8, AC-9).

**Moving around**: a pointer that moves under 4 pixels between down and up is a click; more is a pan and never selects or clears. The wheel zooms about the pointer, from a listener that is not passive so the page does not scroll or the browser zoom on a trackpad pinch. The zoom buttons zoom by 1.25 times about the canvas centre. A selection made from the panel centres the item without changing the scale (AC-40); a click on the canvas does not move the view.

**On a phone** (720 pixels and under): the dialog fills the screen; a grid of two rows puts the canvas on top (55 percent of the dynamic viewport height) and the panel below it, scrolling on its own. The canvas ignores page scrolling for touches (`touch-action: none`), so a one finger drag pans it.

**Command surface**: unchanged. `uv run tracepath gallery build --out DIR` writes the same single `DIR/index.html`.

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
| Show the key | The six drawings | A constant fragment of SVG and words in `render.py` |
| Inline the library | The four files, their licences and `SOURCES.md` | `src/tracepath/gallery/vendor/`, read by the shell (AC-71 to AC-73) |

**Key invariants**:
- The script decides nothing about an item's state. It reads `cited`, `held`, `unresolved`, `radius`, `neighbours` and `near_cited` and draws them (AC-57 to AC-64).
- The graph holds exactly the stored items and links of the record: no item added, none dropped, and a link whose end is missing fails the build rather than being skipped (AC-12, AC-13, AC-65).
- Every source link on the graph is built by spec 0010's `item_link` from a file and line the build already checked against the snapshot.
- Stored text reaches the page only escaped in the data block (AC-69, AC-70) and only through `textContent` or the page's own escaped list in the panel (AC-53).
- With scripts off, the page is the list of spec 0010, with no dead control (AC-2).
- The page carries no timestamp of the build, and the graph makes no network request (AC-75), as spec 0010 requires of the page.

**Security model**: the page is public and holds only stored records, the engineer's marks and links to public repositories. The new risk is the inline script reading stored text: it is covered by AC-53, AC-68, AC-69 and AC-70. GitHub Pages cannot set a Content Security Policy header, so there is no second line of defence; that is acceptable because the page loads no third party content and the script never turns stored text into markup. No secret is read; no compliance scope applies.

**Configuration required**: none. The Pages workflow is unchanged: its `src/tracepath/**` path filter already covers the new code and the vendored files, so a change to either deploys the page on a push to `main`. Pages action versions are as in spec 0010.

**Critical test scenarios** (each maps to acceptance criteria in ## Requirements; the browser steps run at `/check verify`, the rest in pytest):
- Happy path on real data: build from `artifacts/asks/` and `gallery/marks.json`; every entry has a data block, and its items and links equal its record's, verifies **AC-12, AC-13, AC-57, AC-58**.
- Flags against the record: for each of the 31 records, every item's `cited`, `held`, `unresolved`, `neighbours`, `near_cited` and `cited_by` equal an independent recomputation from the record, verifies **AC-59 to AC-64**.
- Edge: a record that cites no item (Q11 and Q16 cite none) has `cited_count` 0 and no cited item, verifies **AC-24, AC-33**.
- Edge: a link from an item to itself (23 exist) has `drawn` false and is in its item's `link_ids`, verifies **AC-13, AC-50**.
- Edge: two items with two links between them (25 such pairs exist) list that neighbour once, in first link order, verifies **AC-62**.
- Failure: a fixture link whose target is not an item, two items with one id, and two labels with one slug each exit 1 with the record named, verifies **AC-65, AC-66, AC-67**.
- Failure: a fixture script holding `</script` and another holding `<!--` each exit 1, verifies **AC-68**.
- Edge: stored text containing `</script>`, `<figure`, `&` and U+2028 survives a write and a parse of the data block unchanged, verifies **AC-53, AC-69, AC-70**.
- Guard: `SOURCES.md` has one row per vendored file, the page holds each licence text verbatim, and the files are in dependency order, verifies **AC-71, AC-72, AC-73**.
- Isolation: the built page has no `src=` or `<link` pointing at another file, and the build still passes with sockets blocked, verifies **AC-74**.
- Browser: open Eval 3 (37 items), then Eval 2 (90 items, 114 links) at 1440 and at 390 pixels wide; check every drawing, select an item, follow its link, use the switch, previous and next, and the network log, verifies **AC-1 to AC-11, AC-14 to AC-23, AC-25 to AC-32, AC-34 to AC-52, AC-54 to AC-56, AC-75, AC-76**.
- Browser, scripts off: the page shows no Graph button and the list is unchanged, verifies **AC-2**.

## Build plan

Approach: Tracer Bullet (the project default). The first slice is one real entry, from record to a graph that opens, so the whole route (stored links read, flags computed, library inlined, dialog, drawing, click) is proven on a small pack before it is thickened and before it reaches the 90 item packs.

1. [x] Slice 1, the thread. Read `links` into `AskRecord` and `hop` into `StoredItem`; add `graph.py` with the flags for one entry; add `vendor/` (the four files from the npm packages at the versions in the Decision, each `LICENSE`, `SOURCES.md` with the version and source) and `assets/graph.js`; render a Graph button, the dialog, the data block and the inlined script for Eval 3 first, then every entry; the dots and lines are drawn and a click selects a dot. Satisfies **AC-1, AC-2, AC-12, AC-13, AC-57, AC-58, AC-71, AC-72, AC-73, AC-74**
2. [x] Slice 1, check it in a browser. Build to a scratch folder and open Eval 3: the dialog opens and closes, the dots are placed, a click selects. The Pages workflow needs no change; the page goes live on merge. Satisfies **AC-3, AC-4, AC-5, AC-6, AC-25**
3. [x] Slice 2, the states. Cited, not cited, held, held link, unresolved and selected drawings, the dim on select, the key, the switch, and the no cited item case. Satisfies **AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-30, AC-31, AC-32, AC-33, AC-34, AC-35, AC-59, AC-60, AC-61, AC-62, AC-63, AC-64**
4. [x] Slice 3, the panel. The `data-item` attribute on the list's citation links, the cloned answer view, the item view with its link, claim numbers, links in and out, and the all items list. Satisfies **AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50, AC-51, AC-52, AC-53**
5. [ ] Slice 4, moving around. Pan, wheel, zoom buttons, reset, previous and next with the counter, a repeatable layout. Satisfies **AC-7, AC-8, AC-9, AC-10, AC-11, AC-26, AC-27, AC-28, AC-29, AC-75, AC-76**
6. [ ] Slice 5, the phone layout. Stacked window, touch pan, the 40 pixel buttons. Satisfies **AC-54, AC-55, AC-56**
7. [ ] Slice 6, the guards. The three build failures, the inline script check, the escaping and its round trip test, the vendor table test, the self contained test. Satisfies **AC-65, AC-66, AC-67, AC-68, AC-69, AC-70**
8. [ ] Visual pass, settled before it starts: build to a scratch folder, screenshot Eval 3, Eval 2, Held out 1 and Q16 at 1440, 768 and 390 pixels, tune the layout constants and the radii once against the three 90 item packs, and compare to the reference's layout; screenshots stay in the scratchpad, never committed. Satisfies **AC-23, AC-25** (no new criterion)
9. [ ] Amend spec 0010's three lines that say no JavaScript or no graph, and its Follow up and scope rows 17 and 18, as a dated note pointing here (see Follow up). Satisfies the spec record, no AC

## Consequences

**Positive**:
- A reader sees how the cited items connect, what else the model was sent, and which parts were held or unresolved, without reading 90 rows.
- Every state on the graph is computed and tested in Python against the record, so the script cannot show a state the record does not hold.
- The page stays one file, works offline, and still works with scripts off.
- The one library is small (17 KB raw, about 7 KB gzipped), has an ISC licence, and its version and source are recorded.

**Negative / tradeoffs**:
- The page grows. Today it is 776 KB raw and 81 KB gzipped. The data for 31 graphs adds about 1.5 MB raw (measured on 2026-10-24: 1.8 MB of JSON with the stored lines, from which the `line` field and the repeated link lists come out), roughly 0.4 MB gzipped. Each graph's data is parsed only when opened.
- A third party file lives in git. d3-force's last release is 3.0.0 from 2021 and its repository was last pushed on 2023-12-30 (researcher check, 2026-10-24); it is still what d3 7.9.0 (2024-03-12) ships. Pinning makes this a non issue until the project wants a newer one.
- There is no JavaScript test runner. pytest covers the page the build writes and the flags; the script's own behaviour (click, pan, switch, the window) is checked in a browser at `/check verify`, and nothing re runs it on every push. A regression in the script is not caught by CI.
- No pinch to zoom on a phone. The zoom buttons and one finger pan cover it.
- There is no address for a graph: a reader cannot send a link that opens one graph. It was cut on 2026-10-25 as outside the Done when and the most failure prone part of the script (see Follow up).
- The layout settles in the browser from d3's cooling schedule, so a change to d3-force, the starting values or the order of `items` moves every dot. Pinning the files and fixing the order keep it repeatable within one browser, and the visual pass is the only judge of how it looks.
- Links at 30 percent ink are about 2.0 to 1 against the page, below the 3 to 1 for graphics. They are the quiet connections and the panel lists each link, so this is accepted; held links, which carry a meaning, are at 50 percent.
- 20 percent of links are `UNCLASSIFIED` and are drawn like the rest; the graph says no more about them than the stored type does. Where two items have two links between them, one line can hide the other.
- A graph of 90 items is still dense on a phone. Labels only on cited items, the switch, and the zoom buttons are what keep it readable.

**Neutral**:
- Spec 0010's page statements about "no JavaScript" and its Follow up for this slice are updated by a dated note (Build plan task 9). Its AC-58 still holds, since scripts are inline.
- The list's citation links gain a `data-item` attribute that does nothing outside the panel.
- New folders `src/tracepath/gallery/assets/` and `src/tracepath/gallery/vendor/`; no change to `pyproject.toml`, the workflow, or the command.
- The dialog element and `touch-action` are supported by current browsers (inferred from the platform, not checked against browser data here).

## Follow-up

- [ ] Amend spec 0010: its Feature design says "no JavaScript", its Decision says "with no JavaScript", its Consequences say "no search, filter or graph", its Feature design says the build does not read the records' `links`, and its Follow up lists this slice as open. Add a dated amendment note on each pointing at this spec, and tick the Follow up. The build task 9 does it.
- [ ] Reconcile scope features 17 and 18 and the Deferred "Visual UI" entry once built: feature 18's Done when is this spec's AC-3, AC-14 to AC-21, AC-42, AC-46 and AC-48.
- [ ] Shareable link to one graph: an address fragment that opens a graph and selects an item. Cut from this spec on 2026-10-25. If it comes back, settle first how the address is written (replace, not push, and the close path), how a bad slug or item is handled, and how an id holding `#`, `:` and `/` is encoded.
- [ ] Read the four LICENSE files from the packages when vendoring, and copy each word for word. This spec checked the licence of `d3-force` and `d3` from their repositories, but did not read the four packages' own LICENSE files.
- [ ] Check in a real browser that the four UMD files load from plain script tags in the order given. This spec checked it in Node's `vm` sandbox only (task 2 does it).
- [ ] Decide later whether the other data (the 13 records the page does not show) deserves a graph, and whether a link between two entries' shared items is worth drawing. Neither is in this spec.
- [ ] Pinch to zoom, if a reader asks for it.
- [ ] Goal: one shared graph of every shown answer's items, where picking a question zooms to its items. Deferred until link resolution improves (scope features 7 and 8): today the 947 items of the 31 packs form 224 separate pieces, 173 with no link, so answers have no section to zoom to. Revisit then; the drawing, flags, panel and d3 setup carry over. _Recorded 2026-10-25 by the engineer, who kept one graph per answer for now._
- [ ] Visual pass (task 8): show item ids in their stored case, never in capitals. This replaces "mono uppercase" for the dot labels in Drawings and Style. _Engineer's ruling, 2026-10-25._

## References

**Project sources** (verifiable, in this repo):
- `AGENTS.md`: the functional core rule, the stack and the Tracer Bullet approach.
- Spec [0010](../0010-answer-gallery/index.md): the page, design B tokens, AC-24, AC-26 to AC-36, AC-56 and AC-58, and its Follow up naming this slice.
- `docs/scope/scope.md`, feature 18: the intent, the Done when and the open questions this spec answers.
- `src/tracepath/gallery/render.py` and `citations.py`: the styles, the claim and verdict functions (`_citation`, `_claims`, `_verdict`), `_link` and `item_link`.
- Measured on 2026-10-24 and 2026-10-25 from `artifacts/asks/` and `gallery/marks.json`: 31 entries, up to 90 items and 138 links in a pack, 2,408 items and 3,114 links in all, 39 unresolved names, 270 held items, 522 held links, 23 links from an item to itself, 25 item pairs with more than one link, no duplicate item id, no link whose end is not an item, stored `hop` equal to the line's reach on every item, item ids holding `#`, `:` and `/`.
- `design-notes/aicodingdictionary.com.md` and its screenshot: a local style reference, git ignored, layout and type ideas only.
- Cross check of 2026-10-25, a read only pass by another model, whose gaps are settled in the Feature design.

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
