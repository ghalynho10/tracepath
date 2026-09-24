# 0001 · Do the four new entity types come back stably?

**Date**: 2026-09-22
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Code commit**: `ab8c2ea`
**Spec**: [0002, AC-14](../../docs/specs/0002-data-model/index.md)
**Note**: Agreement figures here were measured under the comparator as it stood before the 2026-09-23 AC-11 amendment (flags in the signature, set comparison), and are not comparable with anything measured after it. See [spec 0002 AC-11](../../docs/specs/0002-data-model/index.md).
**Also measured under prompt `0002.2`, which carries no worked examples.** Scope feature 12 is testing whether adding examples is what fixes the run to run instability on heterogeneous units. If it does, `PROMPT_VERSION` bumps and AC-14's verdict below has to be re-earned under the new prompt, because every type stability figure here is a fact about the exampleless prompt and not about the vocabulary on its own. That re-run lands as its own experiment and this file is **not** edited to match: it is the before half of that comparison, and rewriting its numbers would destroy the only record of what the old prompt did.

## Question

Spec 0002 added four entity types that the tested extraction pipeline never had:
`Consequence`, `FollowUp`, `BuildStep` and `TestScenario`. Its own Consequences
section calls this a real risk rather than a formality, because the tested prompt says
plainly that consequences and follow up items are **not** requirements and should be
`unclassified`, and the tested few shot examples cover none of the four.

AC-14 therefore asks: before the schema is treated as settled, do the new types come
back stably across three runs over six section kinds, or is the disagreement recorded
and the vocabulary revisited before feature 5 builds on it?

## Method

Build plan task 7 (the thin thread: one `## Requirements` section, end to end) plus
task 10 (AC-14's six section kinds), three runs each under spec 0001's run policy,
then load the accepted items into Neo4j.

Seven units, 21 calls. Run by [run.py](run.py); effort calibrated first by
[calibrate_effort.py](calibrate_effort.py).

## Configuration

| | |
|---|---|
| Model | `claude-sonnet-5` |
| Runs per unit | 3 |
| Prompt version | `0002.2` |
| `max_tokens` | 64000, streaming |
| Effort | **medium** (decided by measurement, below) |
| Sampling parameters | none. Rejected outright on this model |

Every run artifact records all of the above: `artifacts/runs/<record>/<section-slug>/run-N.json`.

## The failed first attempt

The first attempt produced **no data at all** and is recorded here because a run that
fails for this reason is a finding about the pipeline, not noise.

**What failed.** The very first call was rejected by the schema with four validation
errors: the model set `entity_type_ambiguous` on four entities it had given named
types. Nothing was written.

**Bug one, the prompt under-specified a rule the schema enforces.** Spec 0002 is
explicit twice over: AC-1's flag gloss says `entity_type_ambiguous` is "only ever set
on an `unclassified` entity", and the spec's own follow up repeats that it "stays tied
to an `unclassified` entity". The Pydantic validator enforced exactly that. The prompt
did not state it, saying only "set a known trap flag whenever the call was genuinely a
judgement call", which left the model no way to know which flag covers a close call
*between named types*. Fixed by naming the distinction and pointing that case at
`granularity_boundary_call`. **Prompt version `0002.1` → `0002.2`.**

**Bug two, the retry policy was bypassed.** Spec 0001's run policy allows one retry on
a failed or malformed run before a unit becomes a flagged failure. `pipeline.run_unit()`
called `extract_once()` directly rather than `run_with_retry()`, so the policy was
silently skipped. Fixed.

**What it burned: unmeasured.** The call's token usage is not recorded anywhere,
because `ExtractionFailed` was raised from inside the SDK's parse helper, which raises
before the response object is returned. Estimated at roughly $0.11 to $0.21. That the
failure hid its own cost is the most useful thing it had to say, and it is why usage is
now read from `stream.current_message_snapshot` on the failure path, so every call is
measured whether it succeeds or not.

## Two further faults found on the way

**`max_tokens` was too small for a thinking model.** At 16000, the `Consequences`
section returned `stop_reason: max_tokens`, 16000 of 16000 output tokens, and a single
`thinking` block with no JSON at all. Sonnet 5 runs adaptive thinking by default and
thinking is billed as output. Fixed by streaming at 64000; the same section then
completed using 27,131 output tokens, well above the old ceiling.

**A dead end worth recording.** Moving the schema to a raw
`output_config.format.schema` was rejected by the API: `Schema type 'oneOf' is not
supported`. Pydantic renders the discriminated endpoint union as `oneOf`. The schema
must travel as `output_format=ExtractionOutput`, whose SDK path normalises it, with
`effort` alongside in `output_config`.

## Choosing the effort

Effort was never decided. Spec 0001's run policy row does not mention it, so the first
runs used the model's default (`high`) by accident rather than by choice, and thinking
is billed as output, which makes effort this pipeline's real cost dial. Both levels were
measured on the same section, 0012 `Consequences`, three runs each.

| | default (high) | medium |
|---|---|---|
| output tokens | 29,603 / 26,599 / 20,945 (avg 25,715) | 10,739 / 10,547 / 13,262 (avg 11,516) |
| seconds per run | 247 / 226 / 185 (avg 219) | 93 / 84 / 105 (avg 94) |
| entities | 18 / 16 / 17 | 12 / 16 / 15 |
| types | `Consequence` 16/15/15, `Constraint` 2/1/2 | `Consequence` 12/15/15, `Constraint` 0/1/0 |
| flags per run | 11 / 12 / 11 | 4 / 4 / 8 |
| `compare_runs()` | disagree | disagree |
| differing signatures | 8 | 5 |
| cost, 3 runs | $0.8065 | $0.3805 |

Data: [effort-default-calibration.json](data/effort-default-calibration.json),
[effort-medium-calibration.json](data/effort-medium-calibration.json).

**Chosen: medium.** AC-14's type question looks answered at both settings
(`Consequence` dominant in all six runs), neither setting reaches agreement, and medium
halves cost and time: about $2.67 and 32 minutes against about $5.65 and 76 minutes
over the full set.

This conclusion was extended by [experiment 0002](../0002-effort-low-fidelity/README.md), which measured `low` with spans persisted and confirmed medium on fidelity grounds.

Two honest qualifications on that table:

1. **Medium's lower differing signature count (5 against 8) largely reflects fewer
   flags, not better consistency.** Default sets roughly three times as many flags
   (11/12/11 against 4/4/8), and AC-11 puts sorted flags inside the agreement
   signature, so more flagging is more churn surface. The difference measures flagging
   volume at least as much as it measures stability.
2. **On entity counts, default is steadier** (18/16/17, spread 2) than medium
   (12/16/15, spread 4). Effort was chosen on cost and on AC-14's type question, not on
   count stability.

The `accepted` / `review` cell is absent for medium: that calibration was captured
before the script recorded it. `differing signatures` measures the same thing and is
present for both.

## Result, per section

All 21 calls succeeded. No unit failed, and no retry was needed.

| Section | agree | entities per run | new types (per run) | accepted | review |
|---|---|---|---|---|---|
| 0012 `Requirements` (thin thread) | no | 14 / 14 / 14 | none expected | 5 | 17 |
| 0012 `Consequences` | no | 15 / 16 / 15 | `Consequence` 15/16/15 | 8 | 37 |
| 0012 `Follow-up` | no | 9 / 9 / 9 | `FollowUp` 9/9/9 | 7 | 26 |
| 0012 `Build plan` | no | 9 / 9 / 10 | `BuildStep` 9/9/9, `Consequence` 0/0/1 | 6 | 14 |
| 0021 `Requirements` (struck text) | no | 19 / 21 / 21 | none | 7 | 114 |
| 0008 `Preamble` | no | 16 / 17 / 27 | `Consequence` 2/0/11, `TestScenario` 0/1/0 | 4 | 44 |
| `feature-21` scope row | no | 15 / 38 / 14 | `BuildStep` 6/7/6, `Consequence` 3/2/3, `FollowUp` 1/2/2, `TestScenario` 1/0/0 | 8 | 112 |

Totals: 45 accepted, 364 in the review queue. Full data:
[per-section.json](data/per-section.json).

## Conclusion

**Three of the four new types come back stably in the sections that are about them.**

- `Consequence` in `## Consequences`: **15 / 16 / 15**
- `FollowUp` in `## Follow-up`: **9 / 9 / 9**
- `BuildStep` in `## Build plan`: **9 / 9 / 9**

In all three the set of types produced was identical across runs. None of the three
collapsed to `unclassified`, which was the specific risk spec 0002 named. On the
evidence of its own sections, the vocabulary holds for these three.

**`TestScenario` is untested by this run, because AC-14's coverage set cannot reach
it.** It appeared only twice across 21 calls, incidentally, once in a `Preamble` run and
once in a scope row run. The reason is structural: in this corpus every test scenario
lives under a bold `**Critical test scenarios**` label **inside `## Feature design`**,
which 20 of the 21 specs carry, and `## Feature design` is not one of the six kinds
AC-14 names. AC-14 cannot answer its own question for a quarter of the vocabulary it
was written to check.

**No section reached agreement, in any configuration.** That is not mainly type
instability. Where a section has a dominant type, the type counts are steady; what
moves is flags, and flags sit inside AC-11's agreement signature. The two genuinely
unstable sections are the heterogeneous ones, where the runs disagree about how many
items exist at all: `0008 Preamble` at 16 / 17 / 27 entities, and the `feature-21`
scope row at 15 / 38 / 14, whose middle run also carried 56 flags against 3 and 5.

**Cost of the full run: unmeasured, estimated about $2.67.** The run crashed at the
graph load before writing its summary, and the run artifacts do not carry token usage,
so it was lost. Usage belongs in the artifact; that it is not there is a defect this
experiment exposed and the next run should close.

Measured spend elsewhere in this experiment: $0.3805 for the medium calibration,
$0.8065 for the default calibration, $0.17 for the `max_tokens` diagnostic, $0.28 for
the streaming verification.

## The load did not complete

The graph load failed on its last step, and the failure is a spec gap rather than a
bug in the write path:

```
GraphWriteFailed: UNCLASSIFIED links: asked to write 7 but the database wrote 2.
```

14 relationship endpoints pointed at entities that had been routed to review and so
were never written. AC-11 says only accepted items are written to the graph; AC-7 says
no relationship is dropped for having an endpoint that cannot be named. A relationship
can be accepted while the entity it points at is not, and the spec does not say what
happens then. Recorded as an open amendment for `/architect`; not decided here.

What did load, before the assertion stopped it: 5 Records, 45 entities across four type
labels, 13 `:Unresolved` nodes, 45 `PART_OF` and 2 `UNCLASSIFIED` relationships, and
**zero phantom nodes**. The counter assertion AC-13 requires did exactly its job: the
write failed loudly instead of silently corrupting the graph.

## What this owes the specs

Open amendments recorded for the `/architect data model` pass, none applied here:

1. **AC-2**: the `Preamble` unit applies to the scope document as well as a spec's
   `index.md`, or its byte coverage rule contradicts its own list.
2. **Spec 0001, pipeline artifact storage**: the row names the fields but no path.
   `artifacts/runs/<record>/<section-slug>/run-N.json`, tracked in git.
3. **Spec 0001, run policy**: the row justifies leaving temperature at its default for
   comparator variance, but temperature is rejected outright on this model (400). The
   row needs rewording, and should record `effort = medium`, `max_tokens = 64000` and
   streaming as decided values.
4. **AC-11**: flags sit inside the agreement signature and are the least stable thing
   the model produces. Whether flag churn should break agreement, or flags should route
   to review without entering the signature, is a decision.
5. **AC-7 against AC-11**: what happens to an accepted relationship whose endpoint
   entity was routed to review. All three available readings contradict something the
   spec states.
6. **AC-14**: the six section kinds cannot exercise `TestScenario`, because test
   scenarios live inside `## Feature design`, which the set omits.

## A note on evidence

The task 7 observations reported during the build (14/14/14 entities,
`rationale_boundary_call` 0/4/7, and the signature arithmetic 22 entity + 13
relationship signatures = 35 = 4 accepted + 31 review) came from a **superseded
configuration**: `max_tokens=16000`, non streaming, default effort, prompt `0002.2`.
**Those artifacts have no surviving copy**, because they were deleted rather than moved
when the configuration changed. The numbers stand as recorded but cannot be reproduced
from disk.

The flag churn evidence behind amendment 4 rests instead on the two committed
calibration files in `data/`, which make the same point on one section under two effort
levels, and on this run's own committed artifacts.

`experiments/README.md` now carries the rule that came out of that mistake: artifacts
are evidence, never delete them to make a set clean, move them and commit before any
run that clears them.

## A note on this experiment's runner

`run.py` here calls `run_unit()` without catching `UnitFailed`. A unit that failed
after its retry would therefore have lost the artifacts the exception carries out, and
with them the record of what those calls cost, which is the same unrecoverable spend
spec 0001's artifact storage row exists to close.

The bug is real and it is left in place on purpose. This experiment is frozen: its
script records what actually ran on the day, and editing it now would make the record
say something that was never true. The fix lives in the two scripts that are still
live, `0002-effort-low-fidelity/calibrate_effort.py` and
`0003-feature-design-testscenario/run.py`, and `tests/test_experiment_scripts.py`
holds it there. Found by `/check review`, 2026-09-23.
