# 0005. Held item view

**Date**: 2026-10-07
**Status**: Proposed

## Summary

This spec adds a second way to load the graph. With `load --with-held`, the items that review is holding back are written too, each one marked held with the reasons it was held. With `trace --with-held`, a chain can step through them and print each one as held, so you can see where a chain would go and where it is blocked. Without the flag nothing changes: held items stay out of load, walk and report. This is a view, not a routing policy, so no item becomes accepted by it and feature 11 still sets the real policy. The rerun of eval question 3 through this view is a second, labelled result, scored against a prediction written into this spec before any code.

## Requirements

The five conditions below were set by the engineer on 2026-10-06 (scope feature 14) and are fixed. This spec designs within them.

**User stories**:
- As the engineer, I want a chain to run through the items review holds back, each marked held, so that I can see where a chain would go and where it stops.
- As the engineer, I want default output to never contain a held item, so that a held item can never pass for a reviewed one.

**Acceptance criteria** (each holds one claim):

*Default stays clean (condition 1)*
- **AC-1**: `load` without `--with-held` writes no node and no relationship that has a `held` property.
- **AC-2**: `graph_slice()` called without `with_held` drops every held node, every held link, and every link with an end that was dropped.
- **AC-3**: The chain `trace` prints without `--with-held`, over a graph that holds held items, is byte identical to the chain over the same graph with no held items.
- **AC-4**: `trace --eval N` without `--with-held` prints a report with no held line, no held outcome and no held label.
- **AC-5**: `load` without `--with-held` writes a `graph-build.json` with no `held_view` key and prints no held line.
- **AC-6**: `load --with-held` writes the same accepted entities and the same accepted links as `load`, in number, by id, and by endpoints. The accepted rows are built exactly as today, independent of the held view.

*The walk (condition 2)*
- **AC-7**: `src/tracepath/traverse/walk.py` is not changed by this feature.
- **AC-7b**: The tests of spec 0004 AC-20 to AC-30 pass unchanged.
- **AC-8**: On a hand built fixture that is not an eval chain, a walk over a slice built `with_held` visits a held node, follows a held link, and reaches an accepted node whose only path runs through a held link.

*Held steps print as held (condition 4)*
- **AC-9**: A held entity's step heading ends with `  HELD: ` and its reasons joined by `, `, in stored order, each as `name` or `name:detail`, for example `HELD: runs_disagree, known_trap_flag`.
- **AC-9b**: A held `:Unresolved` step heading ends with `  HELD: reached only by held links`.
- **AC-10**: The link line of a step reached by a held link ends with `  HELD: ` and that link's reasons in the AC-9 form, for example `HELD: endpoint_not_accepted:0002/AC-10`.
- **AC-11**: A chain with at least one held step or held link prints, before the prompt versions line, `Held: N steps, M links`, where N counts steps whose node is held and M counts steps reached by a held link. A chain with neither prints no such line.
- **AC-12**: With `--with-held` the walk runs twice under spec 0004's rules, once over the slice with held items dropped (the clean walk, exactly as today) and once over the slice with them kept (the held walk). An expected item the clean walk reaches prints as `reached`, whatever path the held walk took to it.
- **AC-12b**: An expected item the held walk reaches and the clean walk does not prints as `held only`, and never as `reached`. A held entity is never reached by the clean walk, so it always falls here.
- **AC-13**: A `held only` line ends with `via ` and the held parts of the held walk's path to it, from the start, joined by `, `: a node as its id, a link as `SOURCE -[TYPE]-> TARGET`.
- **AC-14**: The `Across records` line counts only items the clean walk reached.
- **AC-14b**: Under `--with-held` one more line reads `Across records through held items: yes (ID, hop N, ...)` or `Across records through held items: no.`, listing each `held only` item outside the start's record.
- **AC-15**: A report made with `--with-held` opens with the line `Held item view (spec 0005): a second result. Experiment 0009 stays the first.`
- **AC-16**: A report made with `--with-held` prints the line `held_for_review keeps spec 0004's meaning: the item is held, whether or not this view wrote it.`

*What `load --with-held` writes*
- **AC-17**: Each entity that routing held and that the first run produced is written as a node with `held` true and `held_reasons` set to its reasons.
- **AC-18**: A held entity's node has no `accepted_by` property.
- **AC-19**: Each first run relationship that routing held, and each link held for an endpoint in another unit, is written as a relationship with `held` true and `held_reasons`, its endpoints resolved by spec 0002 AC-7 over every first run entity, a `{record}` endpoint landing on its Record.
- **AC-19b**: A held in unit link with no review item behind it, or a cross unit held link with no relationship, stops the load with `HeldViewIncomplete` before any write, and the load exits 1.
- **AC-20**: An `:Unresolved` node that only held links reach carries `held` true.
- **AC-20b**: An `:Unresolved` node an accepted link also reaches carries no `held` property, and a held link reaching it changes nothing on it.
- **AC-21**: A held entity whose canonical id is already taken, by an accepted entity or an earlier held one, is not written.
- **AC-21b**: The load prints how many held entities were skipped.
- **AC-22**: A held link with the same type, source and target as an accepted link is not written.
- **AC-22b**: The load prints how many held links were skipped.
- **AC-22c**: A held link with the same type, source and target as an earlier held link is not written, and counts in the same skipped figure.
- **AC-23**: A queue row no first run entity or relationship stands behind is not written.
- **AC-23b**: The load prints how many such rows it left out.
- **AC-23c**: For entities and for links, the number written plus skipped plus left out equals the number of held rows routing produced, or the load stops.
- **AC-24**: `graph-build.json` made with `--with-held` has a `held_view` object with six counts: `entities`, `links`, `unresolved`, `skipped_entities`, `skipped_links`, `not_written`.
- **AC-25**: Two `load --with-held` runs over unchanged artifacts write byte identical `graph-build.json` files.

*Trace with the flag*
- **AC-26**: `trace --with-held` over a graph with no `:Entity` or `:Unresolved` node that has `held` true exits 1, before any walk.
- **AC-26b**: That exit prints a message on stderr naming `tracepath load --with-held`, and no chain.
- **AC-27**: `trace --eval 3 --with-held` run twice prints identical output.

*The second result (conditions 3 and 5)*
- **AC-28**: The prediction in `## Held out discipline` is committed with this spec, before the code commit.
- **AC-29**: The result record names the design commit, the code commit and the result commit in that order.
- **AC-29b**: The result record says it is a second result beside experiment 0009.

## Decision

**Chosen option**: Option A, a `held` property on the node or relationship, dropped by one pure function unless the flag is given.

Held items are written into the same graph with `held: true` and `held_reasons`, and `graph_slice()`, the one place the walk's input is built, drops them unless `with_held` is set. The walk is not edited. The report and the renderer add the held outcome and the held marker.

**Implementation skills**: `neo4j-driver-python-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-driver-python-skill/`) · `neo4j-cypher-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-cypher-skill/`, Cypher 5 syntax only) · `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`)

## Rationale

Reasoning, the options and the evidence: see [rationale.md](rationale.md).

## Migration plan

**Strategy**: no migration needed. The graph is derived and `load` always clears it first, so switching between the two modes is a reload, and a reload cannot lose data.
**Rollback**: revert the code commit and run `load`.

## Feature design

**Data model sketch**. No new node kind and no new relationship type. Three properties are added, and only under `--with-held`:

| On | Property | Type | Notes |
|---|---|---|---|
| `:Entity`, `:Unresolved` | `held` | bool | `true` when the item is held. Absent otherwise, never `false`. |
| `:Entity`, every typed relationship | `held_reasons` | list[str] | One string per reason: the reason name, or `name:detail` when the reason has detail (`endpoint_not_accepted:0002/AC-10`). |
| typed relationships | `held` | bool | Same rule. |

A held `:Unresolved` node has `held` and no `held_reasons`. A held entity row is `entity_row()` without `accepted_by`, plus the two properties. `PART_OF` is written for it as for any entity. A held entity keeps the `flags`, `file_line`, `commit`, `model` and `prompt_version` it would have had.

**Interface**:

| Command | New option | What it does |
|---|---|---|
| `tracepath load` | `--with-held` | Also writes held items. Always clears first, as today. Prints the held counts. |
| `tracepath trace START` | `--with-held` | Reads the graph with held items kept, walks, prints held steps as held. Exits 1 if the graph holds no held node. |
| `tracepath trace --eval N` | `--with-held` | The same, then scores with the held outcome. |

**The pieces** (the edges and the pure core follow AGENTS.md):

| Piece | Where | Kind | Does |
|---|---|---|---|
| `build_held_view(results, corpus)` | `pipeline.py` | pure | From each unit's first run and its routing, returns the held entities, the held links with their reasons and the counts. |
| `HeldLink.relationship` | `pipeline.py` | field | A `HeldLink` also carries the relationship it holds, so a cross unit held link can be resolved. Defaults to `None`. |
| `held_entity_row()` | `graph/model.py` | pure | An entity row with `held`, `held_reasons`, and no `accepted_by`. |
| `load(..., held=None)` | `pipeline.py` | edge | With a held view, writes its entities and links through the same `_write()` calls. |
| `graph_slice(..., with_held=False)` and `drop_held(slice)` | `traverse/graph_slice.py` | pure | Drop held nodes, held links and links with a dropped end, unless `with_held`. `Node` and `Link` gain `held: bool = False` and `held_reasons: tuple[str, ...] = ()` as their last fields, so spec 0004's tests build them unchanged. |
| `read_graph(..., with_held=False)` | `graph/read.py` | edge | Passes the flag through. The Cypher read is unchanged. |
| `render_chain()` | `traverse/render.py` | pure | Prints `HELD: ...` on a held step and its held link, and the summary line. |
| `score()` | `report.py` | pure | Takes the clean chain beside the held chain, marks a finding `held only` when only the held chain reached it, and adds the held lines. |

**How a held view is built.** Units are taken sorted by (record id, section slug), items in first run order, so every choice below is repeatable. For each unit with a first run:
1. A held entity is a first run entity whose `canonical_id` is on a routing review item. Its reasons are the reasons of every review item with that id, in queue order, without repeats. Each reason is written as `name`, or `name:detail` using `ReviewReason.detail`.
2. A held in unit link is a first run relationship that is not in `routed.accepted_relationships`. Its reasons come from the review items with the same signature, in the same way. None found raises `HeldViewIncomplete`.
3. A cross unit held link is a `HeldLink` from `resolve_accepted()`. Its relationship comes from the new field, its reasons from `HeldLink.item`. A `HeldLink` with no relationship raises `HeldViewIncomplete`.
4. Every held link is resolved with `resolve_endpoints()` over all first run entity ids and the Records, by spec 0002 AC-7, in its own call. The accepted links are resolved exactly as today, in their own call, so a held entity can never change where an accepted link lands. The held result lines up one to one with the links that went in.
5. A held entity whose id an accepted entity or an earlier held entity holds is skipped and counted. A resolved held link whose type, source and target an accepted link or an earlier held link has is skipped and counted.
6. An `:Unresolved` node made by a held link takes `held` true only when no accepted link made the same node. A held link that lands on a Record or on an accepted node marks nothing on it.
7. A queue row with no first run entity or relationship behind it is counted as not written. For entities and links separately, written plus skipped plus not written must equal the held rows routing produced, or the load stops.

**Write order.** The accepted writes run first and finish, as today. Then held entities, then held `:Unresolved` nodes, then held `PART_OF`, then held links. Every `held` flag comes from the pure view, never from a `SET` on a node that exists.

**How the walk and the report use it.** The walk is unchanged. `trace --with-held` reads the graph once, keeps the held slice, and makes the clean slice from it with `drop_held()`. It walks both. The chain printed is the held walk's. The report scores each expected item by the two walks: reached by the clean walk is `reached`, reached only by the held walk is `held only`. A held shortcut can therefore never relabel an item a fully accepted path reaches. If the start is held, the clean walk has no start and reaches nothing. A step is held when its node is held, and its link is held when `via.held`. The held parts named on a `held only` line come from following `parent` from its step back to the start in the held walk. Reasons for items neither walk reaches keep spec 0004's meaning.

**Value sourcing**:

| Action | Value produced or displayed | Source |
|---|---|---|
| held view | a held entity's text, type, flags, ids | the unit's first run entity, `result.identified[0].entities`, found by `ReviewItem.canonical_id` |
| held view | a held item's reasons | `ReviewItem.reasons`, written as the reason name or `name:detail` |
| held view | a held in unit link | `result.identified[0].relationships` that are not in `routed.accepted_relationships`, reasons from the review item with the same signature |
| held view | a cross unit held link | `HeldLink.relationship` and `HeldLink.item.reasons` |
| held link write | `prompt_version`, `model`, `commit`, `file`, `section`, `line` | `link_row()` over the unit's provenance, the same function accepted links use |
| held entity write | `file_line`, `commit`, `model`, `prompt_version` | `entity_row()`, the same function accepted entities use |
| held entity write | `accepted_by` | none: absent, because no one accepted it |
| `load` | the held counts line and `held_view` | the held view's counts: entities written, links written, unresolved written, skipped entities, skipped links, rows not written |
| `trace` | whether the graph was loaded with held items | whether the read slice holds any entity or `:Unresolved` node with `held` true |
| `trace --eval` | the clean chain | `drop_held()` over the same read slice |
| report | the `held only` line text, the label and meaning lines | the exact strings of AC-13, AC-14b, AC-15, AC-16 |
| `load` | the six `held_view` counts | `entities`, `links`, `unresolved` written; `skipped_entities`, `skipped_links`; `not_written` |
| `trace --eval` | the held label | the `--with-held` flag |
| report | the held nodes and links on an item's path | the chain's steps: `step.node.held`, `step.via.held`, followed by `step.parent` |

**Key invariants**:
1. No default path (load, walk, render, report) reads a held item. The one place that decides is `graph_slice()`.
2. No held item is ever accepted, counted as accepted, or shown without `HELD:`.
3. A held item never overwrites an accepted one, and an accepted write never leaves a `held` property behind. Written items are skipped, not merged.
4. Every held write asserts its own row count through `_write()`. Where an endpoint is missing the load stops, as it does for accepted items.
5. `held_for_review` keeps spec 0004 AC-38's meaning. This view does not redefine it.

**Security model**: none. A local tool over public repository text. No new setting or secret. No API call and no model client: `tests/test_spend_fence.py` stays unchanged.

**Critical test scenarios**:
- Default graph, loaded with and without held items: the slice, the chain and the report are identical, verifies **AC-2**, **AC-3**, **AC-4**.
- A hand built fixture with a held start, a held link and an accepted node behind that link: the walk reaches all three, and the print marks the first two held, verifies **AC-8**, **AC-9**, **AC-10**, **AC-11**.
- Expected items on a fixture: one reached clean, one through a held link, one itself held, one not visited, verifies **AC-12**, **AC-13**, **AC-14**.
- The committed artifacts, built into a held view with no database: counts, one skipped id, one skipped link, rows not written, verifies **AC-17**, **AC-19**, **AC-21**, **AC-22**, **AC-23**.
- Real Neo4j, default load then flagged load: no `held` property in the first, the same accepted items in both, held items marked in the second, verifies **AC-1**, **AC-6**, **AC-17**, **AC-18**, **AC-19**, **AC-20**.
- `trace --with-held` on a default loaded graph exits 1, verifies **AC-26**, **AC-26b**.
- A fixture where a held shortcut and an accepted path both reach one item: it prints `reached`, verifies **AC-12**, **AC-14**.
- Default `load` and `trace`: no `held_view` key, no held line, no held label, verifies **AC-5**, **AC-4**.
- The report's fixed lines under `--with-held`, matched as strings, verifies **AC-14b**, **AC-15**, **AC-16**.
- `graph-build.json` after a flagged load: six counts, and the same bytes on a second load, verifies **AC-24**, **AC-25**.
- A held link with no review item behind it stops the load, verifies **AC-19b**.

## Held out discipline

This section holds the prediction for the second result. It is **locked at the commit that adds this spec, before any code**, and the rerun is scored against it as written. Nothing here changes after the result is seen.

**How it was made.** From experiment 0009's recorded result, the committed review queue (`artifacts/review-queue.json`, rows for 0002 and 0007) and the first run's items in the committed run files. It was not made by running the held view, or any walk. The view writes only items the first run produced, so each item and link below is named with the run it comes from: all of them come from **run 1**. One queue row that would have joined the two specs directly is not in the view, because no first run relationship stands behind it: `superseded-by 0002/AC-10 → 0007/AC-13`, held for `runs_disagree`, which only run 2 or run 3 produced. The prediction does not use it. This is why AC-13 is predicted at hop 2.

**How it is scored.** By two walks, as AC-12 says. The clean walk starts at `0002/AC-10`, which is held and so not in the graph it reads, so the clean walk reaches nothing. Every item the held walk reaches is therefore `held only`. The prediction below is the held walk.

**What the held walk will meet** (spec 0004's rules unchanged, start `0002/AC-10`, at most 3 hops):

| Hop | Step | Held | Reasons | Reached by | Run |
|---|---|---|---|---|---|
| 0 | `0002/AC-10`, AcceptanceCriterion, file line 31 | yes | known_trap_flag (`multi_condition_split`) | the start | 1 |
| 1 | `0002#requirements:6`, Consequence, file line 31 | yes | runs_disagree, known_trap_flag | SUPERSEDED_BY, outgoing from AC-10, held link | 1 |
| 1 | `0002#feature-design:71`, TestScenario, file line 232 | no | none, accepted | VERIFIES, incoming to AC-10, held link (endpoint_not_accepted `0002/AC-10`) | 1 |
| 2 | `0007/AC-13`, AcceptanceCriterion, file line 36 | yes | known_trap_flag (`multi_condition_split`) | UNCLASSIFIED, outgoing from `0002#requirements:6`, held link | 1 |
| 2 | `0002#feature-design:72`, unclassified, file line 232 | yes | runs_disagree, known_trap_flag, unclassified_type | SUPERSEDED_BY, outgoing from `0002#feature-design:71`, held link | 1 |
| 3 | Record `0002`, not expanded | no | none | UNCLASSIFIED, outgoing from `0007/AC-13`, held link | 1 |
| 3 | Record `0007`, not expanded | no | none | UNCLASSIFIED, outgoing from `0002#feature-design:72`, held link | 1 |

Seven steps. Four held nodes, one accepted node reached through a held link, two Records. Six links, every one of them held.

**The prediction, row by row** (scored as written):

| Expected item (file, line) | Predicted | Hop | Why |
|---|---|---|---|
| spec 0002 AC-10, struck (`0002` index.md:31) | `held only` | 0 | The start entity is itself held. |
| spec 0002 struck test scenario (`0002` index.md:232) | `held only` | 1 | The entity at line 232 reached first is `0002#feature-design:71`, accepted, but its link to AC-10 is held and so is the start. |
| spec 0007 AC-13 (`0007` index.md:36) | `held only` | **2, not 1** | Run 1 has no direct link from AC-10 to AC-13. It goes through the held Consequence `0002#requirements:6`. |
| spec 0007 AC-12 (`0007` index.md:35) | not reached, `held_for_review` | none | Its only first run link is `verifies 0007#feature-design:64 → 0007/AC-12`, which does not join the start's component. |
| spec 0007 key invariant 1 (`0007` index.md:142) | not reached, `held_for_review` | none | Entity `0007#feature-design:13`, held on `multi_condition_split`, has no first run link at all. |

Other figures predicted: `reached` (clean) items **0**. `held only` items **3**. Not reached **2**. Visited steps matching no expected item **2** (the two Records). Accepted links written outside the expected sections that touch 0002 or 0007 (spec 0004 AC-40, unchanged, read over accepted links only): **0**. Visited steps matching no expected item are counted as spec 0004 AC-39 counts them, by file and file line, so the Consequence at line 31 and the unclassified scenario at line 232 match an expected item and the two Records do not. `Across records` (clean): **no**. Across records through held items: **yes**, AC-13 at hop 2.

**Risks named now, so they cannot be explained afterwards.** (a) A link I read in run 1 may resolve to something other than what the table says, for example a reference endpoint matched by label to a different entity. Hop counts and neighbours are part of the prediction, and a wrong one is reported as wrong. (b) `held_for_review` on the two misses says only that the item is held. It does not say why no path reached it, and the result must not read it as the reason. (c) Spec 0004's AC-41 is not scored by this view: a `held only` item is not reached, and the result says AC-41 stays failed. (d) The clean walk reaches nothing only because the start is held. If I misread that, the first row is `reached` and the table is wrong.

**What the result must state.** The three commits (AC-29), the row by row table with right and wrong marked, whether the held links read as sensible chains or as the model's guesses on a flagged split, the count of queue rows the view did not write (AC-23), and that the view accepted nothing.

## Build plan

Tracer Bullet: the thinnest real thread first (the marker and the filter, on a fixture), then the printed marker, then the held view over the committed artifacts, then the write, then the report, then the real rerun.

1. The marker and the filter: `held` and `held_reasons` on `Node` and `Link` (last fields, with defaults), read by `node_from_properties()` and `link_from_properties()`; `graph_slice(..., with_held=False)`, `drop_held()` and `read_graph(..., with_held=False)`; a hand built fixture with held items that is not an eval chain; `walk.py` untouched, satisfies **AC-2**, **AC-3**, **AC-7**, **AC-7b**, **AC-8**.
2. The printed marker: `HELD: ...` on a held step heading and on its link line, and the summary line, satisfies **AC-3**, **AC-9**, **AC-9b**, **AC-10**, **AC-11**.
3. `build_held_view()` and `HeldLink.relationship`, a pure function tested over the committed artifacts with no database, with the skip and the not written counts, the stable order and `HeldViewIncomplete`, satisfies **AC-17**, **AC-19**, **AC-19b**, **AC-20**, **AC-20b**, **AC-21**, **AC-22**, **AC-22c**, **AC-23**, **AC-23c**.
4. The rows and the write: `held_entity_row()`, held properties on link rows and unresolved rows, `load(..., held=)`, the manifest's `held_view`, tested against real Neo4j, satisfies **AC-1**, **AC-5**, **AC-6**, **AC-17**, **AC-18**, **AC-19**, **AC-20**, **AC-20b**, **AC-24**.
5. The command options: `load --with-held`, `trace --with-held`, the counts line, the refusal on a graph with no held node, satisfies **AC-5**, **AC-21b**, **AC-22b**, **AC-23b**, **AC-25**, **AC-26**, **AC-26b**.
6. The report: `trace --with-held` walks twice, `score()` takes both chains, the `held only` line, the across records lines, the label and the meaning lines, satisfies **AC-4**, **AC-12**, **AC-12b**, **AC-13**, **AC-14**, **AC-14b**, **AC-15**, **AC-16**.
7. Gate, no code: the full suite, mypy strict and ruff pass, then commit `src/` and `tests/` as the code commit. Check that this spec's commit, with the prediction and the spec 0002 AC-11(f) amendment in it, comes first in `git log`, satisfies **AC-28**.
8. The rerun, no API call and no cost: `load --with-held`, `trace --eval 3 --with-held`, again, then `load --with-held` and the trace once more; then plain `load` to put the graph back to default. Record it in `experiments/0010-held-item-view/README.md` with the scored prediction and the three commits, satisfies **AC-25**, **AC-27**, **AC-29**, **AC-29b**.

## Consequences

**Good**:
- A chain can run through held items and show where it would go and where it is blocked, with nothing accepted by it.
- The default graph, walk and report are untouched, and one pure function is the whole guarantee.
- The walk, spec 0004's locked rules and experiment 0009 stay as they are.

**Costs and risks**:
- A chain through held items is made of links the model guessed, on items three runs did not agree on or flagged as risky. It looks like a chain. The `HELD:` marker and the second result label are the only protection.
- Only first run items are written. A held item only runs 2 or 3 found is missing, and the load says how many.
- `held_for_review` on an item the view did write now reads as "held", not "left out". The report says so in one line, and does not change the code.
- The graph is in one mode at a time. Switching is a full reload.
- Three more properties on the graph, only under the flag. A reader of Neo4j Browser can still see held items there, marked.
- This view does not reduce the review volume. Feature 11 still has to.

## Follow-up

- [ ] **Feature 6** reuses this view for all five questions (scope feature 6). It decides how its runner passes `--with-held`.
- [ ] **A reason for an unreached held item.** When an item is held and written but no path reaches it, the report says `held_for_review`. A reason that says "in the graph, no link within three hops" is a feature 6 choice, not made here.
- [ ] **`verify.md`** owes steps for every AC, added by `/develop` with the build.
- [ ] **`/sync`** adds `load --with-held` and `trace --with-held` to the commands in `AGENTS.md` after the build.
- [ ] **Later results.** Whether any later result can close feature 5 is a separate `/architect` decision, as the scope says. This spec does not make it.
