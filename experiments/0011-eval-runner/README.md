# 0011. Eval runner: the first full run

**Date**: 2026-10-07
**Question**: what does `tracepath eval` say about all five eval questions, once the eight sections questions 1, 2, 4 and 5 need are extracted (spec 0006 build step 9)?
**Config**: model `claude-sonnet-5`, effort `medium`, prompt `0003.1` for the eight new units, corpus `2e40bcf`, Neo4j 5.26. No API call in this step: `eval` reads the committed run files and the graph `load` rebuilt from them.

## Commits, in order (spec 0006 AC-33c)

1. **Spec**: `5c8bda4` designed spec 0006, and `dacc314` amended it (predictions, extraction range, start marker) before this record was written.
2. **Code**: `e24801d`, build steps 1 to 6. Nothing under `src/` changed from it to this record's commit (AC-34: `git diff e24801d HEAD -- src` is empty).
3. **Extraction**: the range `282b9a4` to `8fd0436`, eight commits, one per unit: `282b9a4` 0008 Requirements, `4d015e5` 0003 Requirements, `3420bc7` 0007 Consequences, `b6560a1` 0011 Requirements, `8845d8f` 0014 Decision, `42994ed` 0007 Follow-up, `f014a43` scope Resolved, `8fd0436` 0009 Summary. Then `ffc64e8` rebuilt the review queue (933 held items from 26 units) and the graph build. Nothing under `examples/` or `src/tracepath/extract/` changed from `5c8bda4` to `8fd0436` (AC-32).
4. **Result**: the commit that adds this file. A file cannot carry its own commit's hash; `git log -1 -- experiments/0011-eval-runner/README.md` names it.

The predictions were locked at `a8da2bc` (questions 1, 2, 4 and 5) and `9c53144` (question 5 relocked to one count), both before the first extraction commit `282b9a4` (AC-33b). They are in [predictions.md](predictions.md) and scored below.

## Found before the results were read

**Question 2 spans two prompt versions.** Its items at spec 0001 lines 133 and 143 sit in `0001 ## Binding rules`, whose three runs were extracted under prompt `0002.3`. Every other unit it touches is at `0003.1`: `0011 ## Requirements` (line 37, the start), `0014 ## Decision` (line 69), `0014 ## Requirements` (line 51, the `also` line, which sits in Requirements and not in Decision), and `0008 ## Requirements` (line 62). Read from the `prompt_version` field of each unit's run files. So question 2's result cannot be pinned on one prompt, the limitation the session notes record for mixed prompt graphs.

**The extraction cost against its estimate.** The spec's central figure (rationale.md) took each unit's output per call as its uncached input times the median ratio of the nearest measured kind. The run files give the real figures, at the rates the tool assumes (input $2.00, output $10.00, cache write $4.00, cache read $0.20 per million tokens):

| Unit | Uncached in | Ratio assumed | Ratio per run (output ÷ uncached in) | Mean ratio | Central estimate | Actual, 3 runs |
|---|---|---|---|---|---|---|
| `0008:Requirements` | 6,787 | 4.71 | 4.43, 4.91, 5.23 | 4.85 | $1.25 | $1.2822 |
| `0003:Requirements` | 1,567 | 4.71 | 4.96, 5.26, 3.38 | 4.53 | $0.27 | $0.2571 |
| `0007:Consequences` | 2,403 | 1.51 | 10.33, 11.93, 12.29 | 11.51 | $0.16 | $0.8790 |
| `0011:Requirements` | 4,096 | 4.71 | 4.68, 4.08, 4.81 | 4.52 | $0.64 | $0.6150 |
| `0014:Decision` | 1,434 | 4.22 | 5.49, 9.45, 5.66 | 6.86 | $0.23 | $0.3384 |
| `0007:Follow-up` | 1,605 | 1.51 | 6.75, 8.36, 12.66 | 9.26 | $0.12 | $0.4898 |
| `scope:Resolved` | 532 | 4.22 | 17.01, 15.47, 19.70 | 17.39 | $0.11 | $0.3153 |
| `0009:Summary` | 268 | 1.20 | 8.64, 16.41, 7.79 | 10.95 | $0.05 | $0.1241 |
| **Eight units** | | | | | **about $2.8** | **$4.3007** |

The total is 1.5 times the central figure and well under the tool's wider $30.10. The four Requirements units landed within about 10% of their estimates. The misses are the small prose sections: `0007:Consequences` came in at 5.5 times its estimate and `0007:Follow-up` at 4.1 times, because the spec 0012 Consequences and Follow-up ratio (1.51) did not carry over to spec 0007's (11.51 and 9.26). `scope:Resolved` set a new highest ratio, 19.70, above the 13.39 the rationale recorded as the highest measured. All 24 calls settled on their first attempt, none failed or dropped, and every call stayed under its per call bound ($0.87 to $0.89). The spend, $4.3007, is the same by the running total's rule and by the usage the artifacts recorded.

## Method

```
uv run tracepath load                      # 26 units
uv run tracepath eval                      # data/eval.txt, exit 0
uv run tracepath load --with-held          # data/load-with-held.txt
uv run tracepath eval --with-held          # data/eval-with-held.txt, exit 0
uv run tracepath load                      # data/load-default-after.txt
```

The last plain `load` puts the graph and `artifacts/graph-build.json` back to the default view; the rebuilt file is byte identical to the one `ffc64e8` committed. `load` reported 26 units, 17 records, 197 entities, 52 unresolved, 90 links written (14 collapsed into an existing relationship) and 23 links held across units; units per prompt version `0002.3`: 1, `0003.0`: 2, `0003.1`: 23. No evidence flag was unchecked: the digest of `examples/` still matches `eval/runner.json`.

## Result (spec 0006 AC-33)

The default view decides the result (spec 0006 AC-6, AC-17). No question passed. That is a reading of each question on its own, not a rate.

| Question | Result | Evidence | Each item not reached, with its reason |
|---|---|---|---|
| 1 | `FAIL · 0 of 2` | light | 0008 AC-7 (line 54, the start) `held_for_review`; 0003 AC-14 (line 34) `held_for_review` |
| 2 | `FAIL · 0 of 5` | weaker | 0014 line 69 `held_for_review`; 0014 line 51 (also) `held_for_review`; 0008 AC-10b (line 62) `held_for_review`; 0001 binding rule 6 (line 133) `link_held`; 0001 line 143 (also) `held_for_review` |
| 3 | `FAIL · 0 of 5` | none | 0002 AC-10 (line 31, the start) `held_for_review`; 0007 AC-12 (line 35) `held_for_review`; 0007 line 142 (also) `held_for_review`; 0007 AC-13 (line 36) `held_for_review`; 0002 test scenario (line 232) `link_held` |
| 4 | `INCONCLUSIVE · absence not provable` | light | 0007 AC-4 (line 25) and 0007 AC-19 (line 42), each `held_for_review` in the block; the first cause for each is `start not in the clean slice` |
| 5 | `FAIL · 0 of 7` | weaker | 0007 line 313 (the start) `held_for_review`; 0007 line 335 `held_for_review`; 0007 line 336 (also) `held_for_review`; scope line 179 `held_for_review`; scope line 180 (also) `no_link`; scope line 516 `no_link`; 0009 line 17 `no_link` |

Only question 2's start was reached (0011 AC-12, hop 0). Questions 1, 3 and 5 have no start in the default graph, so each M counts the start item too (AC-10b, as amended at `dacc314`).

- **Question 1**: the start, 0008 AC-7, is held for `known_trap_flag` (`artifacts/review-queue.json`), so no walk ran.
- **Question 4** is `INCONCLUSIVE`, which AC-17e expected and which is not a defect of the runner. The cause is not the one AC-17e named, though: its start, 0008 AC-14, is itself held for `known_trap_flag`, so the walk never started, and each item's first cause is the missing start, before its own hold.
- **Question 5**: three entities sit on spec 0007 line 313, and all three are held, so `Start item: none, no entity at ...:313`.
- **Question 3** prints experiment 0009's recorded block but for one line: one accepted link outside its expected sections now touches its records, `0007#consequences:4 -[unclassified]-> 0002`, written in the newly extracted `0007 ## Consequences`. Its items and reasons are unchanged. AC-3 pins the exact reproduction to the run files at `36a6bc5`, where this unit did not exist.

**Under the held item view** (a second result; the full output is in `data/eval-with-held.txt`):

- **Question 1**: `FAIL · 0 of 1`. 0008 AC-7 is `held only` at hop 0, the start. 0003 AC-14 is still `held_for_review`: the held walk does not reach it either.
- **Question 2**: `FAIL · 0 of 5`. The same as the default.
- **Question 3**: `FAIL · 0 of 4`. The same as experiment 0010's second result: 0007 AC-13 is `held only` at hop 2, through `0002#requirements:6`, and the test scenario is `held only` at hop 1. Across records through held items: yes (0007/AC-13, hop 2).
- **Question 4**: `INCONCLUSIVE`, for the same reason, a start not in the clean slice. The held walk from 0008 AC-14 ran (5 visited steps) and reached neither 0007 item, so even counting held items, nothing documented joins the return path cookie's 10 minutes to the verifier.
- **Question 5**: `FAIL · 0 of 6`. The start is `0007#consequences:19`, the lowest id of the 3 held entities on line 313, `held only` at hop 0. No other item is reached, even through held items.

## Predictions, scored as written (AC-33b)

| Question | Predicted | Came out | Result | Count | Main reason |
|---|---|---|---|---|---|
| 1 | `FAIL · 0 of 1`, `no_link`: 0008 AC-7 never names 0003 AC-14 | `FAIL · 0 of 2`, both items `held_for_review` | right | wrong | wrong |
| 2 | `FAIL · 0 of 5`, the start names no other record | `FAIL · 0 of 5`, four items `held_for_review`, one `link_held` | right | right | wrong |
| 4 | `INCONCLUSIVE`, each item's first cause `held_for_review` | `INCONCLUSIVE`, each item's first cause `start not in the clean slice` | right | not applicable | wrong |
| 5 | `FAIL · 0 of 6`, "feature 21" ends the walk | `FAIL · 0 of 7`, no start: all three entities on line 313 held | right | wrong | wrong |

- **Results**: all four were right.
- **Counts**: one of three was right. Questions 1 and 5 missed by one, because their start was held, so M counts the start item; the prediction assumed the start would be in the graph.
- **Main reasons**: none of the four was right. Each prediction reasoned about the links the text does or does not hold, and in every case review held the items first, so the walk never got the chance to test the link. That is the finding: on these four questions, at prompt `0003.1`, the review gate (`known_trap_flag` on every held expected item) decides the result before the documented links do. Whether the predicted link reasons hold can be read only once the held items are ruled on (feature 11). Question 2's start was reached, but every item it needs is held or behind a held link. Nothing about the predictions, the rules or the runner is revised to fit this result.

## Conclusion

The runner works end to end on all five questions, with no API call. It printed one block per question, the difference for each item, and no total. Every question reached a result, so `eval` exited 0. The first full run shows no chain across records under the default view, and the reason is the same in all five: the items a chain needs are held for review before any link is tried. Every held expected item, the held starts included, carries `known_trap_flag`, some with `runs_disagree` as well (read from each unit's routing over its run files). This is evidence for feature 11 (the review policy) and feature 13 (extraction accuracy). It is not a defect of the walk or the runner.
