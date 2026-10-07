# 0010 · Where does question 3's chain go through the items review holds back?

**Date**: 2026-10-07
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Design commit**: `74e8406`, spec [0005](../../docs/specs/0005-held-item-view/index.md) with its locked prediction and the spec 0002 AC-11(f) amendment
**Code commit**: `8ef5de4`, the commit holding the `src/` this result is scored on
**Result commit**: `2bef321`, the rerun's outputs in [`data/`](data/)
**Prompt version**: `0003.1`, unchanged. No extraction ran: the run artifacts are experiment 0009's.

**This is a second result. [Experiment 0009](../0009-first-traced-chain/README.md) stays the first**, and nothing here changes it (spec 0005 condition 5, AC-29b).

Git history orders the three as spec 0005 asks: the spec at `74e8406`, then `src/` and `tests/` at `8ef5de4`, then the outputs at `2bef321` (AC-28, AC-29). Nothing under `src/` changed between `8ef5de4` and `2bef321`.

## Question

Experiment 0009 printed no chain for eval question 3, "Why is password sign in impossible on production?", because its start item `0002/AC-10` was held for review. With held items written into the graph and marked held (`load --with-held`), where does the chain go, and where is it blocked?

## Method

1. **Before the rerun.** The full suite passed on the `src/` of `8ef5de4`: 758 tests, Neo4j up. Ruff, the format check and mypy strict were clean.
2. **The rerun**, no API call and no cost: `tracepath load --with-held`, `tracepath trace --eval 3 --with-held`, the trace again, `load --with-held` again, the trace once more, then a plain `tracepath load` to put the graph back to default. The plain load wrote `artifacts/graph-build.json` back to its committed bytes.
3. **Scoring** by two walks, as spec 0005 AC-12 says: an item the clean walk reaches is `reached`, and one only the held walk reaches is `held only`. Then the prediction table, row by row, as written.

## Result

The held walk, as printed ([`data/trace-1.txt`](data/trace-1.txt), cut to the step headings and link lines):

```text
Chain from 0002/AC-10: 7 steps, at most 3 hops, typed links both ways, PART_OF not followed.

hop 0  0002/AC-10  AcceptanceCriterion  struck: false  HELD: known_trap_flag
hop 1  0002#requirements:6  Consequence  struck: false  HELD: runs_disagree, known_trap_flag
       link  0002/AC-10 -[SUPERSEDED_BY]-> 0002#requirements:6 (outgoing from 0002/AC-10)  HELD: runs_disagree, known_trap_flag, endpoint_not_accepted:0002/AC-10, endpoint_not_accepted:0002#requirements:6
hop 1  0002#feature-design:71  TestScenario  struck: false
       link  0002#feature-design:71 -[VERIFIES]-> 0002/AC-10 (incoming to 0002/AC-10)  HELD: endpoint_not_accepted:0002/AC-10
hop 2  0007/AC-13  AcceptanceCriterion  struck: false  HELD: known_trap_flag
       link  0002#requirements:6 -[UNCLASSIFIED]-> 0007/AC-13 (outgoing from 0002#requirements:6)  HELD: runs_disagree, endpoint_not_accepted:0002#requirements:6
hop 2  0002#feature-design:72  unclassified  struck: false  HELD: runs_disagree, known_trap_flag, unclassified_type
       link  0002#feature-design:71 -[SUPERSEDED_BY]-> 0002#feature-design:72 (outgoing from 0002#feature-design:71)  HELD: runs_disagree, endpoint_not_accepted:0002#feature-design:72
hop 3  0002  Record
       link  0007/AC-13 -[UNCLASSIFIED]-> 0002 (outgoing from 0007/AC-13)  HELD: endpoint_not_accepted:0007/AC-13
hop 3  0007  Record
       link  0002#feature-design:72 -[UNCLASSIFIED]-> 0007 (outgoing from 0002#feature-design:72)  HELD: runs_disagree, endpoint_not_accepted:0002#feature-design:72

Held: 4 steps, 6 links
Prompt versions: all 11 model made steps share prompt 0003.1.
```

The report that follows it, in full:

```text
Held item view (spec 0005): a second result. Experiment 0009 stays the first.
held_for_review keeps spec 0004's meaning: the item is held, whether or not this view wrote it.

Question 3: Why is password sign in impossible on production?
Start item: 0002/AC-10, from the first trace entry "spec 0002 AC-10 (struck)".

Expected items:
  held only    spec 0002 AC-10 (struck) · specs/0002-deployment-and-environments/index.md:31 · hop 0 · 0002/AC-10 · via 0002/AC-10
  not reached  spec 0007 AC-12 and key invariant 1 · specs/0007-auth-and-per-user-isolation/index.md:35 · held_for_review
  not reached  spec 0007 AC-12 and key invariant 1 (also) · specs/0007-auth-and-per-user-isolation/index.md:142 · held_for_review
  held only    spec 0007 AC-13 · specs/0007-auth-and-per-user-isolation/index.md:36 · hop 2 · 0007/AC-13 · via 0002/AC-10, 0002/AC-10 -[SUPERSEDED_BY]-> 0002#requirements:6, 0002#requirements:6, 0002#requirements:6 -[UNCLASSIFIED]-> 0007/AC-13, 0007/AC-13
  held only    spec 0002 test scenario (struck) · specs/0002-deployment-and-environments/index.md:232 · hop 1 · 0002#feature-design:71 · via 0002/AC-10, 0002#feature-design:71 -[VERIFIES]-> 0002/AC-10

Visited steps matching no expected item: 2 (information, not a verdict).
Accepted links written outside the expected sections that touch 0002 or 0007: 0.
Across records: no. No expected item outside 0002 was reached from the start.
Across records through held items: yes (0007/AC-13, hop 2)
```

**Repeatability.** All three traces printed byte identical output and exited 0 (AC-27). The two flagged loads printed identical summaries and wrote byte identical manifests (AC-25).

**The load** ([`data/load-1.txt`](data/load-1.txt)). The accepted graph is the one experiment 0009 loaded: 18 units, 14 records, 166 entities, 53 unresolved, 89 links (14 collapsed), 22 links held across units. Beside it, marked held: 301 entities, 205 links and 83 `:Unresolved` nodes. 0 held entities and 3 held links were skipped, as already written. **165 queue rows were not written** (AC-23), because no first run item stands behind them: 77 entity rows and 88 link rows that only run 2 or run 3 produced. One of them is the direct `superseded-by 0002/AC-10 → 0007/AC-13` the spec named.

**The view accepted nothing.** No item changed routing. The review log is untouched, and every item this chain stepped through is printed `HELD:` or reached by a held link.

## The prediction, scored as written

The walk table:

| Hop | Step | Predicted | Came out | Prediction |
|---|---|---|---|---|
| 0 | `0002/AC-10` | held, known_trap_flag, the start | held, known_trap_flag, the start | right |
| 1 | `0002#requirements:6`, Consequence, line 31 | held, runs_disagree and known_trap_flag, by a held `SUPERSEDED_BY` out of AC-10 | the same | right |
| 1 | `0002#feature-design:71`, TestScenario, line 232 | accepted, by a held `VERIFIES` into AC-10, endpoint_not_accepted `0002/AC-10` | the same | right |
| 2 | `0007/AC-13`, line 36 | held, known_trap_flag, by a held `UNCLASSIFIED` out of `0002#requirements:6` | the same | right |
| 2 | `0002#feature-design:72`, unclassified, line 232 | held, runs_disagree, known_trap_flag, unclassified_type, by a held `SUPERSEDED_BY` out of `:71` | the same | right |
| 3 | Record `0002`, not expanded | by a held `UNCLASSIFIED` out of `0007/AC-13` | the same | right |
| 3 | Record `0007`, not expanded | by a held `UNCLASSIFIED` out of `:72` | the same | right |

Seven steps, four held nodes, one accepted node behind a held link, two Records, six links all held: as predicted.

The expected items:

| Expected item (file, line) | Predicted | Came out | Prediction |
|---|---|---|---|
| spec 0002 AC-10, struck (`0002` index.md:31) | `held only`, hop 0 | `held only`, hop 0 | right |
| spec 0002 struck test scenario (`0002` index.md:232) | `held only`, hop 1 | `held only`, hop 1, `0002#feature-design:71` | right |
| spec 0007 AC-13 (`0007` index.md:36) | `held only`, hop 2 | `held only`, hop 2 | right |
| spec 0007 AC-12 (`0007` index.md:35) | not reached, `held_for_review` | not reached, `held_for_review` | right |
| spec 0007 key invariant 1 (`0007` index.md:142) | not reached, `held_for_review` | not reached, `held_for_review` | right |

The other figures: `reached` (clean) 0, predicted 0. `held only` 3, predicted 3. Not reached 2, predicted 2. Visited steps matching no expected item 2, predicted 2 (the two Records). Accepted links outside the expected sections touching 0002 or 0007: 0, predicted 0. `Across records` (clean): no, predicted no. Across records through held items: yes, `0007/AC-13` at hop 2, predicted yes, AC-13 at hop 2.

**Every row and every figure came out as predicted.** The prediction was made from experiment 0009's recorded result, the committed review queue and run 1's items, not by running the view, so this checks that reading against the code that implements it.

## Do the held links read as sensible chains?

Each of the six links cites a phrase from its own unit, and each phrase is in the text. None is a link with no words behind it:

- `0002/AC-10 -[SUPERSEDED_BY]-> 0002#requirements:6` cites "**SUPERSEDED 2026-08-30 by spec 0007.**". The superseding note is real. But the link lands on the note itself, a Consequence at the same file line, not on spec 0007. The model split the struck criterion and its note into two items and linked them, which is risk (a) of experiment 0009 resolving one way.
- `0002#requirements:6 -[UNCLASSIFIED]-> 0007/AC-13` cites "which is now the session mint's guarantee (spec 0007 **AC-13**)". It names the right target, but the model did not commit to a type.
- `0002#feature-design:71 -[VERIFIES]-> 0002/AC-10` cites "verifies **AC-10**". This is the plainest link of the six.
- `0002#feature-design:71 -[SUPERSEDED_BY]-> 0002#feature-design:72` cites "**UNRUNNABLE SINCE 2026-08-30**". This is the same split as AC-10's: the scenario and its struck note became two items, joined by a link the model typed as a supersession.
- The two `UNCLASSIFIED` links to Records `0002` and `0007` cite "spec 0002's configuration table matches" and "Spec 0007 deleted the Server Action this scenario posts to". Both name the whole document, not an item in it.

So the chain is grounded in text at every link. It is not the model inventing links on flagged items. But it reaches spec 0007 through a note the model split off, by a link it left untyped. Two of six links are `UNCLASSIFIED` and two more are supersessions between an item and its own note. Whether that counts as an answer to question 3 is not this record's call.

## What the result must state

- **Spec 0004 AC-41 stays failed** (risk (c) of spec 0005). A `held only` item is not reached, and the clean walk reached nothing, because its start is held and so not in the graph it reads (risk (d) held as stated).
- **`held_for_review` on the two misses** says only that `0007/AC-12` and the line 142 entity are held, and this view did write both. It does not say why no path reached them (risk (b)). Run 1 links `0007/AC-12` only from `0007#feature-design:64`, outside the start's component, and gives the line 142 entity no link at all. That is read from run 1 in the rebuilt results, not from this report.
- **165 queue rows were not written**, so the view shows run 1 only. A held item only runs 2 or 3 found is missing from it.
- **The view accepted nothing**, and the default graph, walk and report are unchanged. The plain `load` at the end printed the same summary as experiment 0009 ([`data/load-default.txt`](data/load-default.txt)).

## Cost

None. No extraction call, no token count call. Every command read the committed artifacts and the local Neo4j.

## Conclusion

Through held items the chain from `0002/AC-10` reaches spec 0007's AC-13 in two hops, exactly as predicted. All six links are held, and four of its five entities are. Every link cites real text, but the crossing into spec 0007 runs through a split off note and an untyped link. The answer to question 3 is in the extracted graph; routing holds it back. That is evidence for feature 11 (routing policy) and feature 13 (extraction accuracy). It does not close feature 5: whether any later result can is a separate `/architect` decision, as the scope says.

## Data

- [`data/load-1.txt`](data/load-1.txt), [`data/load-2.txt`](data/load-2.txt): the two `load --with-held` summaries, identical.
- [`data/graph-build-held-1.json`](data/graph-build-held-1.json), [`data/graph-build-held-2.json`](data/graph-build-held-2.json): the manifests both flagged loads wrote, byte identical, with `held_view`.
- [`data/trace-1.txt`](data/trace-1.txt), [`data/trace-2.txt`](data/trace-2.txt), [`data/trace-3.txt`](data/trace-3.txt): the three `trace --eval 3 --with-held` outputs, byte identical. Each printed nothing on stderr and exited 0.
- [`data/load-default.txt`](data/load-default.txt): the plain `load` that put the graph back.
