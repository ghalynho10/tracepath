# 0005. Held item view: rationale

## Context

Experiment 0009 ran question 3 end to end and the chain never started. The start item `0002/AC-10` was held for review on a `multi_condition_split` flag, and so were `0007/AC-12`, `0007/AC-13` and the entity at line 142 of spec 0007. Each was found by all three runs. The routing rules send every flagged item to review, and spec 0002 AC-11 says only accepted items are written to the graph. So the graph held nothing a chain could start from, and the walk and the report had nothing to show except the reason each item was missing.

That left a cycle (scope, replan of 2026-10-06). The chain cannot pass while its items stay held. A routing change (feature 11) or a review of the held items would release them. Feature 11 waits on features 6 and 13, and feature 6 needed this question to pass. The engineer broke the cycle with a status view of held items, over a reorder alone, a hand review of 258 queue rows, or a provisional rule that accepts flagged items the runs agree on. The first two cost a week of review or change nothing. The last one would have put unreviewed items into the graph under the name accepted, which is the one thing spec 0002 names as unsafe.

The five conditions in scope feature 14 fix the shape: held items out of every default output and in only with a flag, spec 0004's walk rules unchanged, a prediction locked before the rerun, a held step always printed as held and never counted as reached, and experiment 0009 left as the first result. This spec designs inside them. It needs an amendment to spec 0002 AC-11, which routing says keeps held items out of the graph today.

The code that matters, read for this design: `route_runs()` keeps a review item as a signature, not the entity (`src/tracepath/extract/compare.py`). `resolve_accepted()` holds a link whose endpoint sits in another unit and keeps only its signature (`src/tracepath/pipeline.py`). `graph_slice()` is the one place the walk's input is built (`src/tracepath/traverse/graph_slice.py`). `load()` clears the graph first, so the graph is always one mode.

## Options considered

### Option A: a `held` property on the node or link, dropped by one pure function

Write held items into the same graph with `held: true` and `held_reasons`. `graph_slice()` drops them unless the flag is set. The Cypher read stays as it is.

**Pros**:
- One place decides, and it is a pure function with a plain unit test.
- The walk is not edited, so spec 0004's locked walk rules stay locked in fact, not only in wording.
- The held items are visible and marked in Neo4j Browser.

**Cons**:
- A held item is physically in the graph. A future reader that skips `graph_slice()` would see it.
- A property can be forgotten on a new write path.

### Option B: an extra `:Held` label, filtered in the Cypher read

Held entities carry a `:Held` label and the default read excludes the label.

**Pros**:
- The default read cannot see them even if the Python forgets.

**Cons**:
- A relationship has no label, so held links still need a property, and the rule lives in two places.
- It changes the read statement that spec 0004 AC-33 tests against real Neo4j, and the read is shared with every command.

### Option C: a second graph for held items

Load held items into a separate database or a separate id space.

**Pros**:
- The default graph cannot hold one.

**Cons**:
- Neo4j Community has one user database, so this means ids with a prefix and a rewrite of every endpoint, which is a second resolver.
- A chain would have to join two graphs, which the walk cannot do without being edited.

### Option E: build the held view in memory at `trace` time

Read the run artifacts in `trace`, add the held items to the slice, and write nothing held to Neo4j.

**Pros**:
- No second graph mode, no refusal on a stale graph, no id clash on write, and the default graph could never hold a held item.

**Cons**:
- Scope feature 14 and its condition 1 name a load mode that writes held items, and the engineer fixed that. This option is outside the conditions.
- Held items would not show in Neo4j Browser, and `trace` would have to rebuild from artifacts as `trace --eval` already does for scoring.

### Option D: held links left out, held nodes only

Write held entities and no held links.

**Pros**:
- Smaller. Fewer ways to mislead.

**Cons**:
- Fails the purpose. In question 3 every path from the start to a second item is a held link, so the chain would stop at hop 0.

## Rationale

Option A. Option E is simpler but sits outside the fixed conditions, and is the one to revisit if the conditions are ever reopened. Condition 2 says the walk is untouched, and Option A is the only one that keeps it so: the walk reads a slice, and the slice is the whole difference. Condition 1 asks for a test that default output never has a held item, and one pure function is a thing a test can cover completely. Option B protects against a mistake the code would need to make twice to matter, and costs a change to a shared read. Option C needs a second resolver to save a property. Option D keeps the feature from working on the only chain it was built for.

Three smaller calls, each made for a named cost:

**First run items only.** The engineer chose this. `route_runs()` takes accepted items from the first run, so the first run is already the run the graph trusts. A queue row with no first run item behind it has no text, no type and no stable id, and writing one would mean choosing a run and a second id rule. The load prints how many rows this leaves out, so the gap is a number and not a silence. The engineer's answer on the prediction adds a check: each link relied on is named with its run, and every one is run 1.

**Skip, never merge, on a clash.** A held entity whose id is taken, and a held link that an accepted link already makes, are skipped and counted. The write is a `MERGE` on id, and a `MERGE` of a held row onto an accepted node would set `held` on a node routing accepted. That is the one way this view could remove an accepted item from the default output, so it is closed at the cost of a few lines and a count.

**Two walks, not a redefined word.** A held shortcut could otherwise become the first path to an item a fully accepted path also reaches, and label it held. Walking once clean and once with held items keeps condition 4's meaning, "reached" means reached without a held item, and changes no walk rule. It costs one more walk and a second chain passed to the report.

**Refuse a stale graph.** `trace --with-held` over a graph loaded without held items would print a normal chain under a held label, which looks like a second result and is not one. The engineer chose to refuse, about three lines.

Guards that were weighed and not added, because they cost more than the risk: a check that the flag was used on both commands in the same shell session, a manifest field that `trace` reads to confirm the mode (the held node check does the same job), and a new reason code for an unreached held item (left to feature 6, noted in Follow up).

## Evidence

Read for this design, not run.

- Experiment 0009, `experiments/0009-first-traced-chain/README.md`: the result, the five rows, and why each item was held. Four items were held on `known_trap_flag` alone, all three runs agreeing on the item.
- `artifacts/review-queue.json` at the committed state: 674 rows across 18 units. For the four question 3 units, the rows for the five expected items and for the links that touch them.
- The first run in the committed run files, for the same items and links, read through the repository's own rebuild (`committed_units()`) and nothing else. Across all 18 units, seven first run links name `0002/AC-10`, `0007/AC-12`, `0007/AC-13`, the line 142 entity, the Consequence at 0002 line 31, or the two scenarios at 0002 line 232. Six are in the predicted walk. The seventh is `verifies 0007#feature-design:64 → 0007/AC-12`, which does not join the start's component. None of the seven items has a `label`, so no link can reach one by label.
- Spec 0004's AC-20 to AC-30 and AC-34 to AC-41, to confirm what this feature may and may not change.

## References

**Project sources**:
- `docs/scope/scope.md`, feature 14 and its five conditions; the replan note of 2026-10-06
- `docs/specs/0002-data-model/index.md`, AC-11 (including 11c) and AC-13, the `:Unresolved` and relationship tables
- `docs/specs/0004-first-traced-chain/index.md`, AC-15 to AC-30, AC-34 to AC-41, `## Held out discipline`
- `experiments/0009-first-traced-chain/README.md`
- `src/tracepath/pipeline.py`, `src/tracepath/traverse/graph_slice.py`, `src/tracepath/graph/load.py`, `src/tracepath/report.py`
- `docs/reflexes.md`, the stop before spend rule (this view makes no paid call)

**Practices & standards**:
- Fix the pass rule and the prediction before the result is seen.
- Functional core, imperative shell: one pure filter, edges pass it in.
- Skip and count rather than merge when two writes can claim one key.
