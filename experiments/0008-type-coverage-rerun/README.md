# 0008 · Do the four entity types still come back stably under prompt `0003.1`?

**Date**: 2026-10-04
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Code commits**: run script `d60017e` (first session), `796dc2a` (resume); prompt
`0003.1` unchanged since `ef2d108`
**Spec**: [0003, AC-18 and AC-36 to AC-39](../../docs/specs/0003-extraction-stability-heterogeneous-units/index.md)
**Before half**: [experiment 0001](../0001-ac14-type-stability/README.md), the same set
under `0002.2`, which carried no worked examples. Its numbers are not edited here.

## Question

Experiment 0001 found `Consequence`, `FollowUp` and `BuildStep` stable in their own
sections under `0002.2`, and could not reach `TestScenario`. Prompt `0003.1` adds
worked examples and rewrites the rules. Do the four types still come back stably in
the sections about them, judged by AC-36 to AC-38?

This is a stability check on covered ground, not a generalisation check: several of
these units are the worked examples' own units (AC-18).

## Method

The type coverage set, 8 units, 3 runs each under `0003.1`, by
[run_coverage.py](run_coverage.py): experiment 0001's seven units plus
`0006 ## Feature design`, the section that holds test scenarios.

- **Runs moved first.** Before each unit's first call, its current runs moved to
  `artifacts/superseded/2026-10-04-prompt-<their version>/`, each folder with a
  `NOTE.md` naming this experiment:
  - `2026-10-04-prompt-0002.2/`: `0012`'s four sections, the `feature-21` row,
    `0006 ## Feature design`.
  - `2026-10-04-prompt-0002.3/0008/preamble/`: experiment 0004's evidence.
  - `2026-10-04-prompt-0003.0/0021/requirements/`: experiment 0005's group A afters.
- **Cost estimate first.** [measure_coverage.py](measure_coverage.py) priced the
  manifest from measured `0003.x` runs, with no paid call
  ([data/cost-estimate.json](data/cost-estimate.json)): $7.39 central, $12.04 wider.
  The engineer approved a $13.32 ceiling: the wider figure with `0006 ## Feature design`
  and the `feature-21` row raised to the heaviest measured call.
- **Safeguards in the script**, tested with a fake client before any call
  (`tests/test_experiment_scripts.py`): a failed or crashed attempt counts at a flat
  $0.4144 (one heaviest call) in the running total, never its recorded tokens; a
  connection that drops mid stream still writes a failed attempt artifact; every
  attempt is written as it settles; a unit does not start if the running total plus its
  wider figure would pass the ceiling; the run stops if the second call reads no cache.
- **Two sessions.** The first stopped by design at `0021` run 2, which failed schema
  validation on its attempt and its retry (see Finding). The engineer chose to resume:
  `0006 ## Feature design` first, then `0021` runs 2 and 3 with one retry each. The
  resume kept `0021` run 1 and continued run 2 at attempt 3. It settled.
- **Judgement**: [judge.py](judge.py) reads [data/run.json](data/run.json) and writes
  [data/judgement.json](data/judgement.json), with no API call.

## Configuration

| | |
|---|---|
| Model | `claude-sonnet-5` |
| Runs | 3 per unit, one retry per run |
| Prompt version | `0003.1` |
| `max_tokens` | 64000, streaming |
| Effort | `medium` |
| Caching | 1 hour breakpoint on the system prompt; call 1 wrote 57,494 tokens, every later settled call read 57,494 (AC-19 confirmed) |

## Result

From [data/run.json](data/run.json):

| Unit | Entities per run | Relationships per run | Entity rows `runs_disagree` | Relationship rows `runs_disagree` | Types per run |
|---|---|---|---|---|---|
| `0012 ## Requirements` | 14 / 14 / 14 | 2 / 2 / 1 | 0 | 1 | AcceptanceCriterion 10, Feature 4, all three |
| `0012 ## Consequences` | 16 / 16 / 16 | 3 / 3 / 3 | 0 | 0 | Consequence 16, all three |
| `0012 ## Follow-up` | 11 / 11 / 11 | 2 / 2 / 2 | 0 | 0 | FollowUp 11, all three |
| `0012 ## Build plan` | 9 / 9 / 9 | 24 / 24 / 24 | 0 | 0 | BuildStep 9, all three |
| `feature-21` row | 16 / 16 / 16 | 29 / 29 / 29 | 0 | 0 | the same six types in the same counts, all three |
| `0008 ## Preamble` | 0 / 0 / 0 | 11 / 11 / 11 | 0 | 0 | none |
| `0021 ## Requirements` | 27 / 28 / 32 | 31 / 31 / 33 | 0 | 29 | AcceptanceCriterion 25 / 26 / 30, Feature 2 |
| `0006 ## Feature design` | 54 / 46 / 50 | 31 / 32 / 31 | 23 | 16 | TestScenario 16, Constraint 37 / 30 / 34, Consequence 1 / 0 / 0 |

- The two units experiment 0001 called genuinely unstable settled completely: the
  `feature-21` row went from 15 / 38 / 14 entities to 16 / 16 / 16, and
  `0008 ## Preamble` from 16 / 17 / 27 to three identical runs.
- `0008 ## Preamble` returns no entities and 11 reference to reference links in every
  run, exactly the output of its own worked example (`examples/0008-preamble.md`: 0
  entities, 11 links). One of the 11 is `binding rule 6` amending `0008/AC-10b`.
- `0006 ## Feature design` stayed the least stable unit. Its entity count was
  36 / 46 / 35 under `0002.2` (now in `superseded/`) and is 54 / 46 / 50 here, almost
  all of the movement in `Constraint`.

## Judgement: AC-36 to AC-38

From [data/judgement.json](data/judgement.json):

| Section | Own type per run | AC-36 (differs by at most 1) | AC-37 (same type set) | AC-38 (never zero) |
|---|---|---|---|---|
| `0012 ## Consequences` | `Consequence` 16 / 16 / 16 | pass | pass | pass |
| `0012 ## Follow-up` | `FollowUp` 11 / 11 / 11 | pass | pass | pass |
| `0012 ## Build plan` | `BuildStep` 9 / 9 / 9 | pass | pass | pass |
| `0006 ## Feature design` | `TestScenario` 16 / 16 / 16 | pass | **fail** | pass |

`0006`'s AC-37 failure is one entity: run 1 typed one sentence `Consequence` ("That is
deliberate and recorded here: spec 0005 parked logo work by the engineer's own
constraint...", flagged `embedded_second_claim`); runs 2 and 3 produced no
`Consequence`. The section's own type, `TestScenario`, came back 16 / 16 / 16, the same
count experiment 0003 measured under `0002.2`.

**Per AC-39**, this failure follows AC-14's own branch (spec 0002): it is recorded here,
and the vocabulary is revisited before feature 5 builds on it. It does not hold feature
12 open.

## Finding: one misplaced flag rejects a whole output

`0021 ## Requirements` run 2 failed schema validation twice in a row, on the same
item. Both attempts typed the paragraph beginning "**Deliberately not built by this
spec.** Recorded in `docs/scope/scope.md` on 2026-09-14..." as `FollowUp` and set
`entity_type_ambiguous` on it. The prompt says to set that flag only on an item typed
`unclassified` (`client.py:206`), and the schema enforces it, so the one misplaced flag
rejected the entire output rather than sending one item to review. The third attempt
settled. Both failed attempts are kept as
`artifacts/runs/0021/requirements/failed-run-2-attempt-{1,2}.json`, raw response
included.

Whether code should strip such a flag, as the binding rule pre check clears stray
labels (spec 0003, AC-4), is for `/debug` or feature 13, not this experiment.

## Cost

| Unit | Central | Wider | Running total's figure | Recorded tokens |
|---|---|---|---|---|
| `0012 ## Requirements` | $1.0536 | $1.8471 | $0.4653 | $0.4653 |
| `0012 ## Consequences` | $0.9589 | $1.6331 | $0.1487 | $0.1487 |
| `0012 ## Follow-up` | $0.9569 | $1.6311 | $0.1371 | $0.1371 |
| `0012 ## Build plan` | $0.9628 | $1.6370 | $0.2317 | $0.2317 |
| `feature-21` row | $0.5480 | $1.6359 | $0.2683 | $0.2683 |
| `0008 ## Preamble` | $0.9529 | $1.6272 | $0.0963 | $0.0963 |
| `0006 ## Feature design` | $1.1026 | $1.6576 | $0.8678 | $0.8678 |
| `0021 ## Requirements` | $0.8567 | $1.6502 | $1.7110 | $0.9227 |
| **Total** | **$7.3923** | **$13.3192** | **$3.9262** | **$3.1379** |

26 calls: 24 settled runs and 2 failed attempts. The running total counts each failed
attempt at the flat $0.4144; their recorded usage (2 and 5 output tokens, against
20,296 and 21,348 characters of raw response) is the known undercount, so the
true bill sits between $3.14 and $3.93.

**Calibration note for the next estimate.** Output ran far below the estimate in six
of eight units: 1,766 to 7,280 output tokens per call where the central figure assumed
12,036 to 22,378. Only `0006 ## Feature design` (26,721) and `0021 ## Requirements`
(27,384) ran near or above it. The estimate priced units from `0003.x` runs of units
the worked examples never showed; most units here are the examples' own, and the model
answers them briefly. The four units with no `0003.x` measurement were the most
overpriced.

## Conclusion

**Under `0003.1`, `Consequence`, `FollowUp` and `BuildStep` come back stably in the
sections about them, and `TestScenario` comes back with a stable count in
`## Feature design` for the first time in this set.** Three of the four sections pass
AC-36 to AC-38. The fourth, `0006 ## Feature design`, passes AC-36 and AC-38 and fails
AC-37 on one stray `Consequence` in one run, which AC-39 records and routes to the
vocabulary review before feature 5, without holding feature 12 open.

The rerun also showed a failure mode the earlier sets did not: a prompt rule the
schema enforces (`entity_type_ambiguous` only on `unclassified`) broken twice on one
item, rejecting the whole output each time.
