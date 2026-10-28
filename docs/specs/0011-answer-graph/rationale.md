# 0011. Answer graph: rationale

## Context

The gallery of spec 0010 shows 31 answers as a list. Each entry shows the question, the claims, the engineer's mark, and a closed "Items sent" fold: cited items in full, every other item as one row. A reader who wants to know how the cited items connect has to read the claims and then match ids by eye.

The ask records already hold what a graph needs. Each stores the pack the model was sent: `items` and `links` (type, source, target, the phrase it was read from, held or not). Measured on 2026-10-24 across the 31 shown records: 2,408 items and 2,955 links, packs of up to 90 items and 138 links, 270 held items, 522 held links, 39 unresolved names, 23 links from an item to itself, 214 items with no link at all, and no link whose end is missing from the items. Two records cite no item, because their answer declines (Q11 and Q16 in the gallery's labels). No new extraction or model call is needed.

Several forces shape the design. The page is one self contained file (spec 0010 AC-58), hosted free on GitHub Pages, and the project has no JavaScript toolchain: CI runs `uv` and `pytest` only. The page is public and reads stored text that can contain markup. The rule of spec 0010 that the page has no JavaScript was written for a plain list and has to give way to an interactive graph, but the list must keep working without it. The engineer wants the colours of design B kept, with cyan, yellow and pink reserved for the marks. A reference page, kept locally and out of git, supplies layout and type ideas: a split window with a graph and a reading panel, a poster title over quiet text, hairlines instead of cards, and the selection kept in the address.

## Options considered

The choice is the one part of this spec with real alternatives to a library. The other choices were made in the conversation or settled by the recommendations below.

### Option 1: d3-force for layout only, vendored and inlined, SVG drawn by hand

d3-force 3.0.0 (with d3-dispatch, d3-quadtree and d3-timer 3.0.1) places the dots. A script of about 300 lines draws SVG from flags the build computed, and handles selection, pan, zoom, the switch and the address.

**Pros**:
- 17 KB raw and about 7 KB gzipped in all, ISC licence, plain script tags with no build step (checked on 2026-10-24, see References).
- Dots and lines are real page elements, so they take the page's CSS, show native tooltips and can be tested and screenshotted.
- The look can follow the reference (round dots, mono labels, hairlines) without fighting a library's own styling.
- Layout is repeatable: I ran two 300 tick layouts of a 90 node graph and got identical positions.

**Cons**:
- Drawing, pan, zoom and hit testing are about 300 lines of my own script with no test runner behind them.
- d3-force's last release is from 2021 (see Consequences); pinned, this does not matter until a newer one is wanted.
- Four files to keep in dependency order, and four licences to carry.

### Option 2: vis-network

vis-network 10.1.2 is a complete network drawing library on a canvas, with physics, dragging and zoom built in. Licence Apache 2.0 or MIT, your choice.

**Pros**:
- One file, no build step, no dependency, and the most to show for the least code: layout, pan, zoom and drag work from the first line.
- Maintained: version 10.1.2 was released 2026-08-19.

**Cons**:
- 425 KB, about 25 times the size of Option 1, for a page that is 776 KB today.
- It draws on a canvas, so dots are not page elements. Dashed rings, square nodes for unresolved names, labels shown only on hover and the reference's look all need its own options and custom drawing.
- Its physics animates continuously, so positions are not the same on every load, which makes the page harder to test and to screenshot.
- Needs its copyright and permission notice kept under either licence.

### Option 3: React Flow (`@xyflow/react` 12.12.0)

A React library for node and edge editors. MIT licence.

**Pros**:
- Polished interaction, minimap and accessibility work done by a team.
- Maintained: version 12.12.0 was released 2026-09-24.

**Cons**:
- It requires React and ReactDOM (its peer dependencies), which this project does not have, plus a bundler to build one file. That adds a JavaScript toolchain to a Python project for one page.
- 184 KB for the library alone, and its stylesheet and React are extra.
- It is made for boxes and arrows you edit, not for 90 dots you read.

### Option 4: no library, layout computed in Python at build time

A seeded force layout written in Python, run by the build, with the positions written into the SVG. The script then only handles clicks, pan and zoom.

**Pros**:
- No third party code, no licence to carry, nothing to pin.
- The layout is a pure function that pytest can test, in the project's own language, and the dots appear with no layout step in the browser.
- Smallest page of the four.

**Cons**:
- A force algorithm of my own to write and maintain, in place of 17 KB that others wrote and many projects use.
- A fixed picture with no way to try a layout in the browser: tuning the forces means rebuilding, where a browser layout can be tuned live in the visual pass.
- Layout quality is the whole product here, and this is where a hand written version is most likely to look worse.

Cytoscape.js (MIT, 425 KB) and Sigma.js (MIT, needs graphology as a second package) were checked and not offered: they are the same class as vis-network on size and need as much custom drawing.

## Rationale

**Reversibility**: two way door. Nothing is stored beyond the page, no record changes, and the library is behind one function (`layout(items, links)`) in the script. Swapping the library, or moving layout into Python, changes one file and the pinned vendor folder.

**Option 1** was chosen, and the engineer picked it. The deciding forces from Context are the file size and the look. The page is 776 KB and a library of 425 KB would more than half again its size to give a canvas whose dots are not page elements, which is the opposite of what the reference's look and the test plan need. A library that only computes positions leaves every drawing choice, the dashed ring, the square, the label rule, in CSS and a few lines, where spec 0010's tokens already live. React Flow is ruled out by the stack, not by quality: it needs React and a bundler in a project that has neither. Option 4 is the runner up and stays open as the cleaner end state if the layout code ever has to be tested harder than a browser check allows; it loses today because writing a layout is the riskiest part to write by hand and the cheapest part to borrow.

The engineer made six more calls in the conversation, each recorded in the spec:
- *Placement*: a full window split view opened from each entry, over an inline fold or a page per answer. A 90 item pack needs room a 700 pixel column does not give, and a page per answer breaks AC-58.
- *Big packs*: the whole pack is drawn, with cited items loud and the rest quiet, over showing only cited items and their neighbours. What the model was sent is itself something a reader may want to judge. One switch hides the rest.
- *Accents*: cyan, yellow and pink stay with the marks, and no colour means two things on the page. Every graph state is carried by size, fill, line or shape; cyan appears only as the selection ring, the page's existing link and selection colour. This is AC-24.
- *Shipping*: the library is vendored and inlined, not loaded from a CDN, so the page keeps working offline and AC-58 stays true.
- *Testing*: pytest on the page the build writes, a browser check at `/check verify`, and the rule that the build computes every state in Python so the script only draws. This was the engineer's wording: the flags are checked against each record, so the one place a wrong state could be shown is in code a test can read.
- *Previous and next*: included, because the reference has them and they make comparing two answers a click.

**Calls I made, with the runner up** (RECOMMEND items, each settled here and not asked):
- *SVG over canvas*: at most 90 dots and 138 lines, SVG elements give hit testing, tooltips, CSS and screenshots. Runner up: canvas, only if packs grew past about 1,000 items.
- *Hand written pan and zoom over d3-zoom*: d3-zoom needs d3-selection, d3-drag, d3-interpolate, d3-ease and d3-color besides, roughly doubling the vendored code for about 60 lines saved. Runner up: d3-zoom, if pinch to zoom is wanted.
- *No address state*: the engineer cut it on 2026-10-25 after the cross check called the address script the most failure prone part and not part of the Done when. It is a Follow up. Runner up: a fragment such as `#graph=<slug>&item=<id>`, written with `replaceState`.
- *Answer view cloned from the entry's own list*: the engineer took the cross check's simpler build. The list's citation links gain a `data-item` attribute, and the panel clones the question, verdict and claims already on the page, so labels cannot drift from the list and no claim text is written twice. Runner up: a build written `<template>` per entry with its own citation renderer, which doubles the claim text in the page.
- *One data block per entry, parsed when opened*: 31 blocks parse nothing at load. Runner up: one block for the page, which parses 1.5 MB at load.
- *Layout run once, in full, before drawing*: stops the dots moving under the reader and makes the picture repeatable. Runner up: an animated settle, which the reference has and which costs repeatability and a reduced motion rule.
- *No tab stop on dots*: 90 tab stops are not keyboard access. The panel's "All items" list (AC-52) and the claim buttons are the keyboard route. Runner up: arrow key movement between dots, which is a larger piece of script.
- *Self links listed, not drawn*: 23 exist, a loop on a dot adds clutter, and the panel still lists them (AC-50). Runner up: a small loop drawn.
- *720 pixels as the phone break and 55 percent for the canvas*: starting values for the visual pass to confirm. Runner up: a bottom sheet over the canvas.
- *Held links at 50 percent, other links at 30*: the cross check found links at 30 percent ink to be about 2.0 to 1 against the page, under the 3 to 1 this spec cites for graphics that carry meaning. Held links carry a meaning, so they are drawn at 50 percent (3.4 to 1); the other links are quiet background that the panel also lists. Runner up: every link at 50 percent, heavier on a 90 item pack.
- *Held ring outside the dot*: a dashed outline on a 3.5 pixel dot is not readable, so the ring sits 2.5 pixels out. Runner up: a dashed outline on a larger uncited dot.
- *Guards kept to what can mislead or break the build*: AC-65 to AC-70 each are a few lines and catch a link to nowhere, a clashing id, a clashing slug, a script that could end its own tag, and a broken data block. No hash check guards the vendored files: git records any change to them. No guard was added for misuse that is only imagined.

**Premise note**: none. The topic is one decision on a feature the scope already enrolled, and the data and the existing code settled most of it.

### Amendment of 2026-10-27: where each graph's data lives

**Why it came up.** The page was 4,817,451 bytes and LinkedIn refused it (limit 3,145,728). The 31 blocks were 3,834,664 of that. The first estimate for this data, 1.5 MB, was wrong by a factor of 2.5; this spec says so in its Consequences. The engineer ruled that each entry's data moves into its own file loaded when that graph opens. Three ways to load such a file were put to them as candidates.

**Options for how the file is loaded.**
- *Option A, a script file per graph (chosen).* `graphs/<slug>.js` calls `tracepathGraph(slug, data)`; `graph.js` adds a script element on open. Opens on `file://` (inferred: a script tag is not held to the cross origin rule), works at any path, and the page's only new request is the one file. Cost: the data is JavaScript, not a plain `.json` file, and a failure shows only as an `error` event with no HTTP status.
- *Option B, `fetch()` of `graphs/<slug>.json`.* Cleaner file and a real status code, and a test reads it with `json.loads`. Chrome refuses `fetch()` on `file://` (inferred), so a double clicked page would show Graph buttons that cannot open. Local preview and `/check verify` would need a server. This is the runner up; it wins if AC-118 fails when tried by hand, and the Follow up says to decide again then.
- *Option C, one combined `graphs.json` fetched on the first open.* Moves the weight (3.8 MB on the first press) rather than splitting it, and has B's `file://` problem. Not chosen.
- Not offered: shrinking the data. The engineer had already ruled for separate files; the largest block, 156,649 bytes, shows nothing needs shrinking.

**How `/check verify` and a local preview open it.** Every earlier verify served the build from `127.0.0.1:8765` and drove it in Chromium (reviews of 2026-10-25 and 2026-10-26, read on 2026-10-27), and the Playwright tool in this session refuses `file:` addresses, so browser steps run over a local server under all three options. Only Option A is expected to also open by double click, which is why AC-118 exists as a by hand step.

**Other rulings.**
- *While loading and when it fails.* The window opens at once with "Loading the graph…" and fails with a sentence that tells the reader to close and reopen. Runners up: a Try again button (more script and one more state, for a failure not yet seen), and not opening the window until loaded (no feedback inside the window on a slow connection).
- *During a load.* Previous, next, the switch and the zoom buttons are disabled; the newest slug wins. Runner up: put label, position, previous and next on each button in the page, so navigation works during a load; it adds bytes to every entry and a second copy of facts `graph.py` already computes.
- *The size check.* A test on the real build, spec 0010 AC-78. Runner up: a build failure, which adds an exit 1 path and a constant for a limit that is 2.1 MB away. The deploy job already waits on the build job, and a pull request must pass `check`.

**Bias check.** Nothing here lets a result be shaped after it is seen: the limit is a fixed number from LinkedIn's own message, the test reads the committed records, and no mark, note or record changes. **What could break later:** the page and its files must be published together (the workflow uploads the whole `site` folder, so they are); a browser may hold an old graph file for a short while after a deploy; the user, not CI, runs AC-118. **Guards:** the size test and the file shape tests; none for the stale file or the lost race beyond the newest slug rule, because neither was seen in real output.

**Reversibility**: two way door. Nothing stored changes; a switch to Option B changes the build writer, one loader in `graph.js` and the tests that read the files.

## References

See [index.md](index.md) References for the sources and the web verified links. Library facts (version, release date, licence, size, whether a bundler or React is needed) were fetched from each package's own registry entry and repository on 2026-10-24. Not confirmed: gzip sizes of the larger libraries, React Flow's stylesheet size, Sigma's graphology size, and a real browser run of any library. The d3-force layout and its repeatability were run once, in Node's `vm` sandbox, by me.
