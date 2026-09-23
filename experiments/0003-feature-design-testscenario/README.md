# 0003 · Does `TestScenario` come back, now that AC-14 can reach it?

**Date**: 2026-09-23
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Code commit**: `3bbfb9b` plus the effort default fix in this run
**Spec**: [0002, AC-14](../../docs/specs/0002-data-model/index.md), amended 2026-09-23
**Note**: This run uses the **amended** comparator (no flags in the signature, derived
entities identified by located line, runs compared by count). Its agreement figures are
not comparable with [experiment 0001](../0001-ac14-type-stability/README.md) or
[experiment 0002](../0002-effort-low-fidelity/README.md), which measured the old one.

## Question

AC-14 named six section kinds and none of them could hold a test scenario: in this
corpus every scenario sits under a bold `**Critical test scenarios**` label inside
`## Feature design`, which the coverage set omitted. Across experiment 0001's 21 calls
`TestScenario` appeared twice, both incidental. A quarter of the vocabulary was
therefore unexercised while the schema was being treated as settled.

The amendment of 2026-09-23 added `## Feature design` as a seventh kind. This is the
run it asks for: does `TestScenario` come back stably, or does it collapse to
`unclassified` the way spec 0002's own Consequences warned the new types might?

## Method

One unit, `0006 ## Feature design`, three runs under spec 0001's run policy, by
[run.py](run.py). Artifacts land in `artifacts/runs/0006/feature-design/`, the source
of truth for a rebuild, because this is real pipeline output rather than a side
measurement.

**Why 0006 and not 0012.** 0012 was the obvious pick for comparability, since it
already supplies four of the seven AC-14 units. That argument does not survive the
amendment: every earlier section's agreement figures were measured under the old
comparator, so nothing here is comparable with them either way. Once comparability
falls away, 0012 is simply the weaker test, 4 scenario bullets at 6,742 characters
against 0006's 16 at 14,311. 0006 also sits closer to the mean `## Feature design`
size of 15,407 that the spec names as the risky heterogeneous case.

## Configuration

| | |
|---|---|
| Model | `claude-sonnet-5` |
| Runs | 3 |
| Prompt version | `0002.2` |
| `max_tokens` | 64000, streaming |
| Effort | `medium` |
| Sampling parameters | none. Rejected outright on this model |

Every run artifact records all of the above.

**A bug this run caught before spending.** `load_anthropic_settings()` returned
`effort=None` when `ANTHROPIC_EFFORT` was unset, and unset means the model's own
default, `high`. Spec 0001's run policy decides `medium`, but nothing in the code
carried that: experiment 0001 passed the level explicitly from its own runner, so the
default was never exercised. At `high` this run would have cost roughly $1.20 rather
than $0.66, and it would have measured the wrong configuration. Fixed by making
`medium` the default in `config.py`, with a test that unset does not mean `high`.

## Result

| Section | agree | entities per run | new types (per run) | accepted | review |
|---|---|---|---|---|---|
| 0006 `Feature design` | no | 36 / 46 / 35 | `TestScenario` 16/16/16, `Consequence` 0/2/0, `FollowUp` 0/0/1 | 16 | 53 |

Types per run in full:

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| `TestScenario` | 16 | 16 | 16 |
| `Constraint` | 16 | 19 | 17 |
| `Feature` | 3 | 5 | 1 |
| `AcceptanceCriterion` | 1 | 0 | 0 |
| `Consequence` | 0 | 2 | 0 |
| `FollowUp` | 0 | 0 | 1 |
| `unclassified` | 0 | 4 | 0 |

Cost: **$0.6595**, 26,670 input and 60,614 output tokens across the three calls,
against an estimate of $0.49 to $0.79. Data: [per-section.json](data/per-section.json),
[review-queue.json](data/review-queue.json).

## Conclusion

**`TestScenario` comes back, and it is the most stable thing in the section.**

- 16 in every one of the three runs, against exactly 16 `**Critical test scenarios**`
  bullets in the source. The count is not approximately right, it is exact, three
  times over.
- **14 of the 16 accepted entities are `TestScenario`.** Acceptance under the amended
  rule needs all three runs to agree on both the located line and the type, so those
  14 are scenarios all three runs found in the same place and called the same thing.
- None collapsed to `unclassified`. The specific risk spec 0002 named for the four new
  types does not materialise for this one, in the section that is about it.

That closes AC-14's gap. All four new types have now been exercised in a section that
is about them: `Consequence` 15/16/15, `FollowUp` 9/9/9 and `BuildStep` 9/9/9 in
experiment 0001, and `TestScenario` 16/16/16 here.

**The section is heterogeneous, as predicted, and that is where the disagreement is.**
Entity counts run 36 / 46 / 35, a spread of 11, the second widest measured after the
`feature-21` scope row. The spread is not in the scenarios, which are identical across
runs; it is in `Constraint` (16/19/17), `Feature` (3/5/1) and run 2's 4 `unclassified`,
which the other two runs did not produce at all. Spec 0002's amended Consequences
predicted exactly this for `## Feature design`, on size alone, before the run.

**53 rows routed to review**, for 40 `runs_disagree`, 16 `known_trap_flag` and 10
`endpoint_not_accepted`. The last is the amended rule working: those are links whose
endpoint entity did not survive the three way comparison, held beside the entity they
wait on rather than written against a node that was never created.

## What this owes the specs

Nothing new. AC-14's coverage set now reaches every type it names, and the answer is
the one the amendment hoped for. Two things worth carrying forward:

1. Acceptance is now dominated by whichever type the section is actually about.
   `TestScenario` reached 14 accepted because its 16 instances are stable and land on
   stable lines; everything else in this section mostly did not.
2. `## Feature design` is the largest unit kind in the corpus and this one is not even
   the largest instance (14,311 characters against a maximum of 38,663). A whole corpus
   run will spend more here than on any other section kind.
