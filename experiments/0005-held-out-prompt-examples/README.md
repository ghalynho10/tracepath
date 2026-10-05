# 0005 · Do worked examples fix run to run instability on held out units?

**Date**: 2026-09-24 (runs) to 2026-09-28 (ruling)
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Code commits**: befores `972907b` (prompt `0002.3`, no examples), afters `906e669` (prompt `0003.0`, the first with worked examples)
**Spec**: [0003, AC-13 to AC-17](../../docs/specs/0003-extraction-stability-heterogeneous-units/index.md)
**Note**: this README was written on 2026-10-01, after the fact, from the data this
experiment already committed. Every number below is copied from `data/`, not
re-measured. The run logs were not committed.
**Reproducing commit**: `201fae4`. `report.py` reads the after runs live from
`artifacts/runs/`, so it reproduces this experiment's numbers only at a commit where
those runs are still in place. At `201fae4`, checked on 2026-10-04 in a clean worktree
of that commit: it rebuilt `data/heldout-table.json` byte for byte, sampled the same 55
items for the ruling sheet, and `report.py tally` rebuilt `data/ruling-tally.json` byte
for byte. The script refuses to build while `data/ruling-sheet.md` carries a ruling, so
the check sent the new sheet to a scratch file; the script was not changed.
**Runs moved later**: experiment 0008 (spec 0003, AC-18) reruns `0021 ## Requirements`
under `0003.1` and moves group A's after runs from `artifacts/runs/0021/requirements/`
to `artifacts/superseded/<run date>-prompt-0003.0/0021/requirements/`, the date named in
experiment 0008's README. From that commit on, run `report.py` from a checkout of
`201fae4`. Groups B and C (`0013`, `feature-9`) are not in that rerun; their runs stay
in `artifacts/runs/`.
**Measurement script**: `measure_prefix.py` imports `SYSTEM_PROMPT` by name from
`tracepath.extract.client`, and the script is not changed. That name was replaced by
`system_prompt()` in `d3d106f`, so the script imports at no later commit. Run it from a
checkout of its own commit, `906e669`, where it measured the `0003.0` prompt (118,651
characters), as `report.py` runs from `201fae4`. The last commit where the name is a
module constant is `e86ca80` (the `0003.1` prompt there). A shim kept the name
importable from `2bff29d` to `9f745e6`; it was removed because it let strict mypy accept
any name imported from that module. Checked 2026-10-05 by importing the script at each
commit, with no API call.

## Question

Scope feature 12 asked whether the run to run disagreement on heterogeneous units is
a fact about the corpus or a fixable defect, and named the missing worked examples as
the first candidate cause. Prompt `0003.0` adds six worked examples. Does it lower
disagreement on units none of those examples show, and is what the runs converge on
actually right?

## Agreement is not accuracy

Every count in the result table measures **agreement**: whether three runs of one unit
produce the same items. **Entity spread**, the widest entity count minus the narrowest
across the three runs, is an agreement figure. A spread of 0 means the runs found the
same number of items. It does not mean the items are right.

Examples can raise agreement almost by construction, because a model copies the cut
it was shown. So spec 0003's AC-16 makes a hand ruling of accuracy mandatory beside
every after run, and reads falling disagreement with falling accuracy as a warning,
not a success. The ruling is reported separately below.

## Held out units

None of the three appears in the six worked examples (AC-14). Each tests a different
kind of distance from them, and each is reported on its own, never combined:

| Group | Unit | Why it was chosen |
|---|---|---|
| A | `0021` `## Requirements` | No worked example of this unit kind exists |
| B | `0013` `## Feature design` | Its kind has an example (`0006`), but the content differs |
| C | `feature-9` scope row (Profile entry) | A different scope row than the example's (`feature-21`) |

## Method

Three calls per unit before and three after, 18 calls in all.

- **Befores**: group A's is a fresh `0002.3` baseline (AC-13, `baseline_0021.py`),
  which replaced the unit's older `0002.2` runs. Groups B and C ran under `0002.3`
  from a worktree of `972907b` (`run_units.py`). All befores now sit under
  `artifacts/superseded/2026-09-24-prompt-0002.3/`.
- **Afters**: all three groups under `0003.0` (`run_units.py`). They are the
  committed runs under `artifacts/runs/`.
- **Table**: `report.py` rebuilds `data/heldout-table.json` from those artifacts with
  no API call. Before and after go through the same current code, so both are
  measured by one method.
- **Ruling**: the engineer ruled a sample of each after run (`data/ruling-sheet.md`,
  tallied in `data/ruling-tally.json`): 10 entities evenly spaced through run 1, 5
  relationships evenly spaced through the after runs' distinct links, and, for group A
  only, 10 links the befores wrote and no after wrote. The befores were not ruled,
  so there is no before accuracy to compare against.

## Configuration

| | |
|---|---|
| Model | `claude-sonnet-5` |
| Runs | 3 per unit, before and after |
| Prompt version | `0002.3` before, `0003.0` after |
| `max_tokens` | 64000, streaming |
| Effort | `medium` |
| Caching | afters only, 1 hour breakpoint on the system prompt (AC-19); 49,114 cached prefix tokens per read |
| Recorded cost | befores $1.5970 (A $0.6918, B $0.4776, C $0.4276), afters $2.4600 (A $1.2139, B $0.6693, C $0.5768), $4.0570 in all |

Group A's before figure undercounts. Its one failed attempt recorded 5 output tokens,
and a failed attempt's recorded usage can fall far short of what it used (see
experiment 0006's Follow up).

## Result: agreement, before and after

From `data/heldout-table.json`:

| Group | Entities per run | Entity spread | Entity rows `runs_disagree` | Relationships per run | Relationship rows `runs_disagree` | Relationship rows `endpoint_not_accepted` |
|---|---|---|---|---|---|---|
| A before | 21 / 21 / 21 | 0 | 0 | 33 / 41 / 35 | 26 | 22 |
| A after | 29 / 29 / 28 | 1 | 2 | 9 / 7 / 8 | 10 | 9 |
| B before | 21 / 20 / 34 | 14 | 21 | 20 / 22 / 32 | 63 | 20 |
| B after | 31 / 34 / 31 | 3 | 8 | 15 / 15 / 15 | 9 | 5 |
| C before | 13 / 19 / 15 | 6 | 4 | 13 / 29 / 17 | 44 | 10 |
| C after | 14 / 17 / 14 | 3 | 3 | 24 / 26 / 31 | 15 | 5 |

- Relationship disagreement fell in all three groups.
- Entity spread fell in B (14 to 3) and C (6 to 3), and rose slightly in A (0 to 1),
  the group whose kind has no worked example. The entity *counts* rose in A and B.
- Group A's relationship count fell from 33 to 41 per run to 7 to 9. Of the 50
  distinct links the befores wrote, no after wrote any. The ruling below checks
  whether those were junk or real.
- Label invention check (build plan task 14): all 27 labels the afters set are found
  verbatim in their own spans, all in group B. Groups A and C set none.

## Result: accuracy, the AC-16 ruling

The bar (`data/method-notes.md`, "Accuracy bar for AC-16"): at least two thirds of
entity marks and of relationship marks in each group agree, and no more than 1 in 5
of the sampled dropped links were real.

| Group | Entities agree | Relationships agree | Dropped links real |
|---|---|---|---|
| A | 4 of 7 (3 unruled) | 2 of 5 | 2 of 10 |
| B | 2 of 5 (5 unruled) | **5 of 5** | not sampled |
| C | 1 of 5 (5 unruled) | 3 of 5 | not sampled |

**The bar fails on five of the six entity and relationship results.** Only group B's
relationships reach two thirds. The dropped link sample sits exactly on its line, 2 of
10, and its 95% Wilson interval (5.7% to 51.0%) is too wide to show it is under.

Group B, the unit whose spread fell most, scored 2 of 5 on entities. On the evidence
here, the examples bought convergence without showing that what the runs converge on
is right.

Two caveats from the method notes themselves. The bar was set after seeing rough
counts, so it is descriptive, not a pre-registered test. One person ruled five to
seven entities and five relationships per group.

## The AC-17 decision

AC-17 compares group B's after spread with 2, the widest spread any stable committed
unit showed. A spread above 2 triggers a measured cost estimate for the AC-2 test:
re-extracting `0013 ## Feature design` split at its bold sub labels.

- Group B's after spread was **3**, so the trigger fired.
- The test was **not run** (spec 0003, AC-31). The estimate was about 30 calls, all
  under `0003.0`, a prompt the AC-16 findings were about to replace. Experiment 0006's
  `0015 ## Feature design` after run answers the same heterogeneity question under the
  prompt that ships, `0003.1`, at no extra cost.
- That run came back at spread **1** (35 / 35 / 36), at or below the trigger, so AC-31
  does not reopen (experiment 0006's README). The AC-2 unit definition question stays
  untested, as feature 12's Done when states.

## Conclusion

Worked examples lowered run to run disagreement on held out units, sharply on group
B's relationships and spread, but not uniformly: group A's spread rose slightly. The
accuracy ruling failed five of six results, so this experiment says **fix first**.
That produced prompt `0003.1` (spec 0003, AC-21 to AC-29: seven rule changes, two
changed examples, one new example) and the re check on fresh units,
[experiment 0006](../0006-accuracy-bar-recheck/README.md).

Nothing here is an accuracy result for the prompt that ships. The agreement numbers
stand as measured under `0003.0`. Any accuracy claim waits on experiment 0006's ruling.
