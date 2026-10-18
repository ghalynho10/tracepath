# 0014 · Review volume and routing policy: which default, if either, does the eval support?

**Date**: 2026-10-17 to 2026-10-18
**Feeds**: feature 11, spec [0008](../../docs/specs/0008-review-volume-and-routing-policy/index.md) (build plan steps 1 to 8)
**Status**: run 2026-10-17; both defaults flipped 2026-10-18 under the rule committed before the run

## Question

The review queue held 990 rows against 237 accepted entities across 29 units. Spec 0008
committed two yes or no rules before any measurement: whether a narrower hold rule
(`--narrow-hold`) should become the default (AC-9), and whether the held item view of
spec 0005 (`--with-held`) should become the default (AC-11). Both are decided from one
table: each expected step of the five eval questions, under four configurations.

## Method

No API call anywhere. Two scripts, both beside this README.

- `measure_hold_ratio.py` rebuilds routing fresh from `artifacts/runs/` without the
  narrow hold rule and counts accepted entities, held entity rows and held link rows per
  unit and per unit kind (spec 0008 AC-7). Output: `data/hold-ratio.md`.
- `compare_four_ways.py` runs `tracepath load` and `tracepath eval` under four
  configurations, `--code-pass` off in all of them: baseline, `--with-held` alone,
  `--narrow-hold` alone, and both. It scores the five questions of
  `eval/linked-records-research.json` in process from the graph each load wrote, through
  the same `_score_question()` `eval` uses, and records each expected step as reached as
  accepted, reached only as held, or not reached (AC-8c), plus the visited steps
  matching no expected item, split held and accepted where held items show (AC-8d). It
  ends with a plain `load` whatever happened (AC-8e) and stops before any adoption fact
  if a step is worse with both flags than with the better single flag (AC-8f).
  Output: `data/four-way.md`, with every load's and eval's printed output in
  `data/four-way/`. `eval/held-out.json` is never opened.

## Configuration

- Corpus: JobHunt at `2e40bcf`.
- Run artifacts: `artifacts/runs/` at `8c778e960d74667f9749355619b12f8f5ef372dc`, 29 units.
- Code: the ratio at `bac65cc`; the four way run at `9110147`, after the flag count fix
  and the `RELEASED: narrow_hold` marker at `3c31584`, and after spec 0008's amendment
  `5458d8e` replaced the blind ruling with that marker, before any measurement.

## Result

### The ratio (AC-7)

Without the narrow hold rule: 237 accepted entities against 990 held rows (535 entity,
455 link), 1 : 4.18 overall. By unit kind it runs from 1 : 2.98 (`Requirements`) to
1 : 11.00 (`Decision`), and `Preamble` and the scope's `Resolved` section have no
accepted entity at all. The full per unit and per unit kind tables are in
`data/hold-ratio.md`.

### What the narrow hold rule releases (AC-5)

257 entities and 207 links. By hold reason, an item counted under each reason that held
it: `known_trap_flag` 316, `endpoint_not_accepted` 185, 37 held for both. By flag, the
union of the flags all three runs raised on the item: `multi_condition_split` 212,
`rationale_boundary_call` 121, `relationship_type_ambiguous` 59, `embedded_second_claim`
35, `granularity_boundary_call` 8. Queue rows fall from 990 to 526, and links held
across units from 37 to 0.

### The four way table (AC-8)

Steps not listed are not reached under any configuration (16 of 22).

| Q | expected step | baseline | `--with-held` | `--narrow-hold` | both |
|---|---|---|---|---|---|
| 1 | 0008 AC-7, the start | not reached | held only | accepted, via release | accepted, via release |
| 2 | 0011 AC-12, the start | accepted | accepted | accepted | accepted |
| 3 | 0002 AC-10 (struck), the start | not reached | held only | accepted, via release | accepted, via release |
| 3 | 0007 AC-13 | not reached | held only | not reached | held only, via release |
| 3 | 0002 test scenario (struck) | not reached | held only | accepted, via release | accepted, via release |
| 5 | 0007 Consequences | not reached | held only | not reached | held only |

Visited steps matching no expected item, all five questions summed: baseline 0;
`--with-held` 26 (26 among held steps, 0 among accepted); `--narrow-hold` 20; both 26
(5 held, 21 accepted).

Verdicts: question 4, the absence question, moves from INCONCLUSIVE to PASS under
`--narrow-hold` and under both, its two items staying not reached. No question with a
trace list passes under any configuration.

### The committed rule, read off the table

- AC-8f: no step is worse with both flags than with the better single flag.
- AC-9(a), met: three steps newly reach accepted under `--narrow-hold` (Q1 0008 AC-7,
  Q3 0002 AC-10, Q3 0002 test scenario). Two of the three are their question's start.
- AC-9(b), met: no step baseline reached as accepted drops under `--narrow-hold`.
- AC-11, met: five steps move from not reached to reached only as held under
  `--with-held` (Q1 0008 AC-7, Q3 0002 AC-10, Q3 0007 AC-13, Q3 0002 test scenario,
  Q5 0007 Consequences).

## Outcome

Both defaults flipped, each after its own dated amendment, under the rule exactly as
committed (AC-14):

1. `73f16c9` amends spec 0002 AC-11 for the narrow hold rule (AC-9b) and adds the
   `--no-narrow-hold` opt out, the default still off.
2. `cb28c68` turns the narrow hold rule on by default and regenerates
   `artifacts/review-queue.json` and `artifacts/graph-build.json` under it.
3. `aca05de` amends spec 0002 AC-11 and AC-11(f), and spec 0005 AC-1 to AC-5 and its
   key invariant 1, for the held view (AC-11b); the tests tied to them state
   `--no-with-held`, which the commit before added.
4. `5c9c9f4` turns the held view on by default and regenerates
   `artifacts/graph-build.json` under both defaults.

AC-12 does not apply: both candidates resulted in a default flip.

**Feature 9 is unblocked (AC-13)**, because both adoptions landed: AC-9 with its
amendment AC-9b, and AC-11 with its amendment AC-11b. The narrow hold rule cuts the
queue from 990 rows to 526 at the current units, and every item it releases is stamped
`accepted_by` `narrow_hold` and prints `RELEASED: narrow_hold`; every item still held
now shows in a chain with `HELD:` instead of stopping it.

## Caveats

- Two of the three newly accepted steps are question starts. A start reached as accepted
  lets the walk begin; it is not a later step of the chain.
- The release rests on runs agreeing, which shows repeatability, not correctness. The
  marker is what keeps a released step visible, in place of the blind ruling the
  amendment `5458d8e` removed.
- A `known_trap_flag` hold is raised by the first run's flags only, so an item flagged
  only in a later run is accepted outright and never reaches the rule (spec 0008's
  corrections note, 2026-10-18).
