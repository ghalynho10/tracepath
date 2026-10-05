# 0009 · Does the first traced chain reach spec 0007 from spec 0002 on question 3?

**Date**: 2026-10-05
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Spec**: [0004](../../docs/specs/0004-first-traced-chain/index.md), committed at `7bd6c48`
**Code commit**: `f12892d`, the commit holding all of `src/` that this result is scored on
**First run artifact**: `fda25e1`
**Prompt version**: `0003.1`, unchanged

Git history orders the three as spec 0004's held out discipline asks: the spec at
`7bd6c48`, then `src/` at `f12892d`, then the run artifacts at `fda25e1` (AC-46a,
AC-46b). Nothing under `src/` or `examples/` changed between `f12892d` and this record,
and the four units' run files were written once and not touched again (AC-47).

## Question

Eval question 3, "Why is password sign in impossible on production?" (shape
`superseded_criterion`). Its chain touches no worked example under `examples/` (AC-1).
Run under spec 0004's locked rules: does `trace --eval 3` reach an expected item in spec
0007 from the start item in spec 0002 (AC-41)?

"Record" in the scope row's Done when is read as a Record node as spec 0002 defines it (a
spec, the scope document, or one feature row). Question 3 spans two Records, spec 0002
and spec 0007 (AC-2a). The reword of the Done when to "two or more Records" was carried
to the scope by `/scope` (AC-2b, `468f05f`).

## Method

1. **Before any paid call.** The full suite passed on the `src/` of `f12892d`: 549 tests,
   47 of them integration tests against Neo4j. `artifacts/review-log.json` held 0
   entries (AC-45). The branch was pushed.
2. **The estimate**, from the free token count endpoint, with the calibration unit
   `0014 Requirements` recounted at exactly 61,108 tokens:

   | Unit | Counted input | Uncached per call | Central | Wider |
   |---|---|---|---|---|
   | `0002 ## Requirements` | 59,090 | 1,596 | $1.0841 | $2.6607 |
   | `0002 ## Feature design` | 65,967 | 8,473 | $0.8870 | $2.5247 |
   | `0007 ## Requirements` | 60,363 | 2,869 | $0.8732 | $2.4575 |
   | `0007 ## Feature design` | 67,865 | 10,371 | $0.8984 | $2.5475 |
   | **Total** | | | **$3.7426, 12 calls** | **$10.1903, 24 calls** |

   The engineer approved a ceiling of $11.
3. **One extraction pass**: `tracepath extract 0002:Requirements "0002:Feature design"
   0007:Requirements "0007:Feature design" --ceiling 11`, interactive streaming API, no
   paid rerun (AC-48, AC-49).
4. **Scoring**: `tracepath load`, `tracepath trace --eval 3`, `trace --eval 3` again,
   then `load` and `trace --eval 3` once more.

## Extraction

Every one of the 12 calls settled on its first attempt. None failed, none dropped, none
needed a retry, and no attempt has null usage (AC-14). The first call wrote the 57,494
token cache and every later call read 57,494.

| Unit | Output tokens, runs 1 / 2 / 3 | Cost |
|---|---|---|
| `0002 ## Requirements` | 6,996 / 5,168 / 6,806 | $0.4523 |
| `0002 ## Feature design` | 42,582 / 50,877 / 50,849 | $1.5284 |
| `0007 ## Requirements` | 17,992 / 12,178 / 13,526 | $0.4887 |
| `0007 ## Feature design` | 34,701 / 40,654 / 39,467 | $1.2450 |

## Result

`trace --eval 3` printed no chain. Its start item `0002/AC-10` is not in the graph,
because it was held for review. As AC-52 says, the command still printed every expected
item with its reason, then exited 1:

```text
Question 3: Why is password sign in impossible on production?
Start item: 0002/AC-10, from the first trace entry "spec 0002 AC-10 (struck)".

Expected items:
  not reached  spec 0002 AC-10 (struck) · specs/0002-deployment-and-environments/index.md:31 · held_for_review
  not reached  spec 0007 AC-12 and key invariant 1 · specs/0007-auth-and-per-user-isolation/index.md:35 · held_for_review
  not reached  spec 0007 AC-12 and key invariant 1 (also) · specs/0007-auth-and-per-user-isolation/index.md:142 · held_for_review
  not reached  spec 0007 AC-13 · specs/0007-auth-and-per-user-isolation/index.md:36 · held_for_review
  not reached  spec 0002 test scenario (struck) · specs/0002-deployment-and-environments/index.md:232 · link_held

Visited steps matching no expected item: 0 (information, not a verdict).
Accepted links written outside the expected sections that touch 0002 or 0007: 0.
Across records: no. No expected item outside 0002 was reached from the start.
✗ 0002/AC-10 is not in the graph. An entity held for review is not in the graph.
```

**AC-41 does not hold.** No item in spec 0007 was reached, because no walk started.
Feature 5 is not marked done on this result, and nothing about the prompt, the walk
rules or the prediction is revised to fit it. The next step is the engineer's, in a new
decision.

**Repeatability.** The second `trace --eval 3`, and the third after a second `load`,
printed byte identical output, and the two loads printed identical summaries (AC-42,
AC-43). `load` reported 18 units (15 at `0003.1`, 2 at `0003.0`, 1 at `0002.3`), 166
entities, 89 links written, 14 collapsed, and 22 links held across units.

**The prediction, scored as written**:

| Expected item (file, line) | Predicted | Came out | Prediction |
|---|---|---|---|
| spec 0002 AC-10, struck (`0002` index.md:31) | reached, hop 0 | not reached, `held_for_review` | wrong |
| spec 0002 struck test scenario (`0002` index.md:232) | reached, hop 1, by `VERIFIES` at `0002/AC-10` | not reached, `link_held` | wrong |
| spec 0007 AC-13 (`0007` index.md:36) | reached, hop 1 | not reached, `held_for_review` | wrong |
| spec 0007 AC-12 (`0007` index.md:35) | not reached, `no_link` or `record_not_expanded` | not reached, `held_for_review` | right that it is not reached; the reason is the held case the spec names as a finding |
| spec 0007 key invariant 1 (`0007` index.md:142) | not reached, the same | not reached, `held_for_review` | the same |

Three of the five rows are wrong. The two misses that were predicted came out as misses,
but for a different reason than predicted.

## Why each item was held

Read from the rebuilt results, with no API call:

- **Four items held for one reason, `known_trap_flag`.** `0002/AC-10`, `0007/AC-12`,
  `0007/AC-13` and the entity at `0007` line 142 were each found by all three runs, at
  the same line and, for the three verbatim ones, under the same id. Each was held only
  because at least one run set `multi_condition_split` on it: all three runs for
  `0002/AC-10`, runs 1 and 2 for `0007/AC-12` and `0007/AC-13`, and runs 1 and 3 for line
  142. Spec 0002's routing sends every flagged item to review, so this is routing
  working as designed, not a defect in the walk or the report.
- **The scenario at line 232 was accepted, but its link was held.** Run 1's
  `0002#feature-design:71` (`TestScenario`) was accepted. Its `verifies` link to
  `0002/AC-10` was held as `endpoint_not_accepted`, waiting on the held `0002/AC-10`, and
  its `superseded-by` link to spec 0007 was held for `runs_disagree`. So the one held
  start caused the other miss too.
- **Risk (a), as named in the spec, came true in part.** All three runs typed line 31
  as `0002/AC-10` with `struck` false. The struck claim and its "SUPERSEDED" note were not
  split into two items. That did not decide the result: the item was held either way.

## What the result must state

- **AC-40.** No accepted link written outside the four sections touches 0002 or 0007.
  The count is 0 before the run and still 0 after the load. So even if the walk had
  started, it could have chosen only among sibling items inside the chain's own four
  sections, never among other records. This result says nothing about choosing between
  records.
- **AC-30 and AC-29.** No chain was printed, so there is no prompt version line to
  report. The manifest shows the four new units at `0003.1`.
- **AC-45.** `artifacts/review-log.json` holds 0 entries: no review decision touched
  the chain's items before scoring.
- **AC-53.** No defect in the walk or the report code was found. This is the only
  result, and it is not relabelled.

## Cost

| | |
|---|---|
| Estimate, central | $3.7426, 12 calls |
| Estimate, wider | $10.1903, 24 calls |
| Ceiling | $11.00 |
| Spent, by the running total | $3.7143, 12 calls |
| Summed artifact usage | 69,927 input, 321,796 output, 57,494 cache write, 632,434 cache read: $3.7143 |

**Console reconciliation (AC-54).** Read by the engineer from the Console's Usage page
for 2026-10-05 UTC, model Sonnet 5, all workspaces and API keys:

| | Console | Artifacts | Gap |
|---|---|---|---|
| Tokens in | 759,855 | 759,855 (69,927 input + 57,494 cache write + 632,434 cache read) | 0 |
| Tokens out | 321,796 | 321,796 | 0 |

No call reached the API that the artifacts do not record. The day's other tracepath API
use was free token counting only (the dry runs), which does not appear on the Usage page.
The Cost page did not yet show the day's USD figure when read; at the rates in
`src/tracepath/extract/cost.py` these tokens price at $3.7143.

One difference in timing, stated as found: the engineer read both usage bars as falling
between 21:00 and 22:00 UTC, while the artifacts were written from 21:39:44 to 22:24:11
UTC, so part of the run ran in the 22:00 hour. The token totals match exactly whatever
the bars' labels mean, so this does not change the reconciliation.

## Findings on the spec's own figures

- **The flat $0.4144 is not the worst a single call can add (AC-9, AC-10a).** A failed
  first call writes the cache, which costs about $0.63
  (39,234 × $10 + 1,596 × $2 + 57,494 × $4, per million). And five of this run's
  calls passed the 39,234 output tokens the figure assumes as the heaviest: 42,582,
  50,877, 50,849, 40,654 and 39,467. A failure at 50,877 output would cost about $0.54.
  The ceiling's margin absorbed this for this run, because nothing failed. The figure was
  not changed before the run, and is not changed here.
- **`0002 ## Feature design` ran far heavier than the central figure.** It averaged
  48,103 output tokens against the 26,721 measured on `0006 ## Feature design`, while
  both Requirements units ran far lighter than 27,384. The central total still landed
  within $0.03 of the spend, because the two errors cancelled.

## Conclusion

Every layer ran for real: extraction, rebuild, load, walk and report. It also ran
repeatably and within budget. But the chain was never walked, because the start item was
held for review on a `multi_condition_split` flag. So were the two spec 0007 criteria
the answer needs. AC-41 fails and feature 5 stays in progress. The evidence goes to
feature 11 (review volume and routing policy: one flag on one run of three holds an item
all three runs agree on) and to feature 13 (extraction accuracy). What to do about
feature 5 next is a new decision for the engineer.
