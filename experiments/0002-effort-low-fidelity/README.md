# 0002 · Does effort=low keep extraction faithful?

**Date**: 2026-09-23
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Code commit**: `2bed820`
**Extends**: [0001, the AC-14 type stability run](../0001-ac14-type-stability/README.md)

## Question

[Experiment 0001](../0001-ac14-type-stability/README.md) chose `effort = medium` on cost
and on AC-14's type question, and measured `low` afterwards only by counts. On counts
low looked best of the three: cheapest, fastest, 11 entities in each of three runs
against a section holding exactly 11 bullets, and the fewest differing signatures.

That reading assumed count matching means fidelity. This experiment tests the
assumption: when low produces one entity where medium produces several, is low keeping
the document's own granularity, or is it losing content?

One case decides it. Bullet 3 of the section holds a struck claim **and its
replacement**:

> `- ~~This feature's migration and its integration tests cannot run until feature 10 … merges into main.~~ **Resolved 2026-09-04**: feature 10 merged to main at 5b01b4c … This feature's build, migration included, is unblocked.`

That is the shape AC-5 and AC-8 exist for. A single entity covering both cannot carry
the supersession, so what low does here matters more than any count.

## Method

Re-run `effort = low` on the same section, three runs, with spans persisted. Experiment
0001's calibration script recorded only counts, never spans, which is why 0001 could not
answer this; `calibrate_effort.py` now calls `write_run()`.

Low's artifacts are written under this experiment's data, never into `artifacts/`, so
the committed production run they are compared against is not overwritten.

Then map every entity's located span onto the 11 source bullets, for low and for the
committed medium run, and read bullets 3 and 9 directly.

## Configuration

| | low (this run) | medium (comparison) |
|---|---|---|
| Model | `claude-sonnet-5` | `claude-sonnet-5` |
| Runs | 3 | 3 |
| Prompt version | `0002.2` | `0002.2` |
| `max_tokens` | 64000, streaming | 64000, streaming |
| Effort | `low` | `medium` |
| Artifacts | `data/effort-low/artifacts/runs/0012/consequences/` | `artifacts/runs/0012/consequences/` (experiment 0001's production run) |

Section: `0012 Consequences`, 5,925 characters, 11 top level bullets.

Cost of this run: **$0.1798**, 116 seconds, output 5,866 / 5,068 / 3,550 tokens.

## Result

### Counts are not stable, and 0001's count reading was luck

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| low, this run | 12 | 11 | 13 |
| low, 0001's calibration | 11 | 11 | 11 |
| medium, production run | 15 | 16 | 15 |

0001 reported low at 11 / 11 / 11 against 11 bullets and read that as low tracking the
document's own structure. Re-run, low gives 12 / 11 / 13. **The alignment was a
coincidence of one sample**, and the argument built on it does not hold.

### Bullet 3, the deciding case

| | entity count per run | replacement kept as its own entity |
|---|---|---|
| **low** | 1, 1, 2 | **no, no**, yes |
| medium | 1, 2, 2 | no, **yes, yes** |

In two of three low runs the bullet yields one entity, and that entity's span **swallows
the replacement into text marked struck**. Low run 1:

> "This feature's migration and its integration tests cannot run until feature 10 …
> merges into main. **Resolved 2026-09-04: feature 10 merged to main at 5b01b4c (pull
> request 86)**" — with `struck = True`

The pre-check is right: the span begins inside the `~~…~~` range, so AC-5's rule marks
the entity struck. The model is what merged two claims into one span. The effect is that
**the current fact is stored and labelled obsolete**.

That is worse than losing it. A chain asking what is current would find the replacement
filed as superseded text. Feature 8's Done when says a replaced fact must never come back
as current; this is the mirror image, the replacement never coming back at all.

Medium fails on the same bullet once in three runs, and fails more mildly: run 1 drops
the replacement rather than mislabelling it, and runs 2 and 3 split correctly.

### Bullet 9, the dense one

Low produced **2, 1, 2** entities; medium produced **5, 5, 4**.

Reading medium's five in 0001, three were genuinely separate testable claims, one was
rationale that belonged in `rejected_spans`, and one was borderline and flagged as such.
Low run 2 produced a single entity, keeping only the alias repointing risk and losing the
rest, including the `temperature: 0` rejection and the reasoning token budget claim.

### Why low's stability number was misleading

Low reported the fewest differing signatures of the three levels (1, against medium's 5
and default's 8). It is stable because it consistently produces fewer and coarser
entities. Agreeing about less is not agreeing better, and the agreement signature cannot
tell those apart.

## Conclusion

**Effort stays `medium`.** Low is cheaper and faster, and on counts it looked like the
best of the three, but it loses content in the one place this tool cannot afford to lose
it: in two of three runs it merged a correction into a span marked struck, filing the
current fact as obsolete. Its apparent stability came from extracting less, and its
apparent fidelity to the document's structure came from a single lucky sample.

Medium is not clean either. It failed the same bullet once in three runs by dropping the
replacement. The difference is the failure's direction: medium loses the correction,
low mislabels it as superseded. The review queue caught every instance in both, because
the runs disagreed on the signature, and that is the only reason none of it reached the
graph.

Recorded as amendment item 7 for `/architect data model`: extraction can keep a struck
claim and lose its replacement, which belongs in spec 0002's `## Consequences` as a known
failure mode and on feature 8's scope row.

## Data

- `data/bullet-split-comparison.json`: per bullet counts and the full bullet 3 and 9
  spans, for all three low runs and all three medium runs.
- `data/effort-low/artifacts/runs/0012/consequences/run-{1,2,3}.json`: this run's
  artifacts, spans included.
- Medium's side is experiment 0001's committed production artifacts at
  `artifacts/runs/0012/consequences/`.
- Script: [calibrate_effort.py](calibrate_effort.py), this experiment's own copy, which
  persists spans. Experiment 0001's copy is left as it ran, without that call.
