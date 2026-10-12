# 0012 · Extraction accuracy, step one: are the items the code pass releases right?

**Date started**: 2026-10-11
**Spec**: [0007](../../docs/specs/0007-extraction-accuracy/index.md), the measure (AC-18 to AC-30)
**Status**: units chosen, nothing extracted yet

## Question

The code pass of spec 0007 stops a `multi_condition_split` flag alone from holding an
acceptance criterion whose three runs agree on its id and type. Runs agreeing shows they
repeat, not that they are right. Are the items it releases right, by the engineer's own
rulings?

## Units

Chosen before any paid call and listed in [`units.json`](units.json), the only list the
step is scored from (AC-22). Their run artifacts must carry `extracted_at` values later
than this file's commit (AC-22b).

| Unit | Why it is clean |
|---|---|
| `0009` `## Requirements` | Not a held out, worked example or pass checked record (AC-23); never ruled (AC-24) |
| `0013` `## Requirements` | Same. Experiment 0005 ruled `0013` `## Feature design`, a different unit |
| `0015` `## Requirements` | Same. Experiment 0006 ruled `0015` `## Feature design`, a different unit |

`tests/test_step_units.py` checks this list against AC-23 and AC-24 on every run.

## Gate

The gate and its reason are spec 0007's AC-19 to AC-19i, as committed in `c004a30`
before any paid call (AC-19e). The step runs in two stages. Both gates count over every
drawn mark, not only the ruled ones: a mark ruled `unsure`, ruled disagree or left
unruled counts against, so ruling hard items `unsure` can never make a unit pass.

- **Stage one** (AC-19, AC-19b, AC-19c): per unit, 5 released entity marks are drawn,
  mixed blind with 3 control entity marks that are ruled but not gated (AC-25, AC-25b).
  Every chosen unit needs at least 4 of its 5 released marks ruled agree. A unit with
  fewer than 5 released entities is inconclusive, and stage one passes only when no unit
  is inconclusive. Nothing accepted without the pass may be lost with it.
- **Stage two** (AC-19f to AC-19i): runs only after stage one passes and the engineer
  wants the pass on by default. Per unit, up to 5 released link marks are drawn, mixed
  blind with 2 control accepted links that are ruled but not gated (AC-25e, AC-25g).
  Every unit with at least one released link needs two thirds of its drawn released
  link marks ruled agree, however few are drawn (1 of 1, 2 of 2, 2 of 3, 3 of 4, 4 of 5).
  A unit with none is reported as having none. A stage one pass alone never turns the
  pass on by default.

No dropped links are drawn (AC-25f). Experiment 0005's full bar is not measured in this
step; it is owed on feature 13's final state (AC-18b, AC-28e).

## Configuration

Model `claude-sonnet-5-5`, effort `medium`, prompt `0003.1`, corpus commit `2e40bcf`.
One paid extraction serves both arms: the control is the run files read without
`--code-pass`, the treatment the same files read with it (AC-20).

## Result

Not yet run.
