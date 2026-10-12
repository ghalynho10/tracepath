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

The gate and its reason are spec 0007's AC-19 to AC-19g, committed in `501ee17` before
any paid call (AC-19e). In short: in every chosen unit, at least two thirds of the ruled
released entity marks agree; nothing accepted without the pass is lost with it; a unit
with fewer than 5 released entities is inconclusive; released link marks are gated at
two thirds only where a unit has at least 5 of them. Experiment 0005's full bar is
reported for both arms and is not this step's gate.

## Configuration

Model `claude-sonnet-5-5`, effort `medium`, prompt `0003.1`, corpus commit `2e40bcf`.
One paid extraction serves both arms: the control is the run files read without
`--code-pass`, the treatment the same files read with it (AC-20).

## Result

Not yet run.
