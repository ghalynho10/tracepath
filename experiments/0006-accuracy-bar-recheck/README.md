# 0006 · The accuracy bar re check

**Date**: 2026-09-28
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Before commit**: `972907b` (prompt `0002.3`, the commit group A's lost links were measured against)
**After prompt**: `0003.1`
**Spec**: [0003, AC-30, AC-31](../../docs/specs/0003-extraction-stability-heterogeneous-units/index.md), the AC-16 findings amendment (2026-09-28)

## What this is

The AC-16 method notes put five of six experiment 0005 after runs under the accuracy
bar, so prompt `0003.1` (seven rule changes, two changed examples, one new example)
shipped before any further paid run. This experiment is that re check: does the fixed
prompt clear the bar on units none of its worked examples, groups A/B/C, or the type
coverage set have ever seen?

Three fresh held out units, 18 calls: 3 before (`0002.3`) and 3 after (`0003.1`) each.

| Unit | Kind | Why it's clean |
|---|---|---|
| `0014` `## Requirements` | Section | Not group A's record, not the source of the new seventh example (`0019`) |
| `0015` `## Feature design` | Section | Not group B's record; also the record `0019`'s bundled `AC-N` pointer example is drawn from is different again |
| `feature-33` (Band anchor review) | FeatureRow | Not group C's row |

**One thing changed since AC-30 was written that is worth naming plainly**: `0014`'s
unit kind (a spec's `## Requirements` section) now has a worked example in the prompt,
`examples/0019-requirements.md`, added earlier in this same build for AC-25 and AC-28.
It is drawn from spec `0019`, not `0014` — the *record* stays genuinely held out — but
the *shape* no longer lacks a demonstration the way group A's `0021 ## Requirements`
did when it was chosen specifically for having none. `0015`'s kind (`## Feature
design`) already had `0006` as an example before this spec started; `feature-33`'s
kind (a scope feature row) already had `feature-21`. So this re check's `0014` result
is weaker evidence about "a kind with no example" than group A was, and slightly
stronger evidence about "does prompt `0003.1` hold up on a fresh record of a
demonstrated kind" than AC-30's own text anticipated. Read `0014`'s numbers with that
in mind.

## Before calls: `972907b`'s prompt and schema, today's everything else

The `0002.3` before calls do not run the old codebase (the mechanism experiment
0005's original group B/C befores used, a worktree of `972907b` on `PYTHONPATH`).
That would also run `972907b`'s `artifacts.py`, missing the four storage safeguards
spec 0001 named on 2026-09-28. Instead `run_recheck.py`'s `before_once()` mirrors
`client.extract_once()` exactly (retries, error handling, the safeguarded `Attempt`
construction) and only swaps in `972907b`'s system prompt text (read from git) and a
local schema subclass restoring `972907b`'s one differing field: `ExtractedEntity
.label`'s sample sentence, `key invariant 1` rather than AC-7's `Happy path` fix.
Verified structurally identical to today's schema otherwise (title pinned to match;
the only remaining difference is an internal `$defs` key name with no model facing
content). Every one of the 18 artifacts carries a `run_id`, `artifact_format_version`,
a `unit_sha256`, and the raw response and `stop_reason`.

## Cost: actual against the plan

Planned (`data/cost-estimate.json`, before any call): **$4.12 central, $4.69 wide**.

| Phase | Unit | Token cost | Safe cost* |
|---|---|---|---|
| before (`0002.3`) | `0014` | $0.6224 | $0.9567 |
| before | `0015` | $0.5040 | $0.5040 |
| before | `feature-33` | $0.3794 | $0.3794 |
| after (`0003.1`) | `0014` | $0.8566 | $0.8566 |
| after | `0015` | $0.8245 | $0.8245 |
| after | `feature-33` | $0.4091 | $0.4091 |
| **Total** | | **$3.5960** | **$3.9303** |

\* "Safe cost" is what the stop conditions actually gated on: a failed or crashed
attempt counts at a flat $0.35 (the heaviest measured single call this experiment
planned against), never its own recorded tokens. `0014`'s before run hit this: its
retried failed attempt recorded 2 output tokens for a ~15,000 character, nearly
complete response (the schema validation failure path snapshots usage before the
API's final usage event lands), which would have under-billed the running total by
about $0.33 had it been trusted. See Follow up.

Actual came in under both the central and the wide plan, on either accounting.

**The $3.9303 safe total excludes `0015`'s crashed first call**: the connection
dropped before any usage event arrived, so nothing was recorded for that attempt at
all (not even the undercounted figure a schema validation failure leaves behind); if
the API billed anything for it, the true total is unrecorded, bounded above by one
more flat $0.35, so the honest upper bound is about **$4.28**, still under the wide
plan.

## What happened running it

The first before call ran clean: `0014`, 3 settled runs plus one retried failure,
$0.9567 (safe cost), committed before continuing. The second unit's first call then
dropped mid stream (`httpx2.RemoteProtocolError: peer closed connection without
sending complete message body`), a real network fault, not a retry logic bug, and it
propagated past the original `except anthropic.APIError` clause uncaught, crashing the
run before it could record anything for that attempt. Fixed by widening `before_once`'s
inner exception clause to `(anthropic.APIError, httpx2.HTTPError)`, reading whatever
partial content and usage the stream snapshot held before the drop (none, in this
case) into a proper failed-attempt artifact. The run then resumed from `0015` without
re-running `0014` (`existing_before_result()` reuses the three already committed
`0002.3` runs rather than re-calling). Neither of these gaps is unique to this
experiment's own code: `client.extract_once()` has the same narrow `except
anthropic.APIError` clause, and the same usage-snapshot-before-final-event timing on
its `ValidationError` path. See Follow up.

`move_superseded()` (reused unchanged from `run_units.py`, per spec: this experiment's
own scripts and data are not `run_units.py`'s to touch) dates every move by that
module's own `SUPERSEDED_DATE` constant (`2026-09-24`, today at the time it was set).
The re check's before runs landed there mislabelled by date and were relocated by hand
afterward, into `artifacts/superseded/2026-09-28-prompt-0002.3/`, the correct date;
their `NOTE.md` files were corrected to match and to name this experiment, not 0005.

## AC-31: the reopen test

Group B's after spread (`0013 ## Feature design`, under `0003.0`) was 3, above the
trigger of 2, and the engineer decided not to re-run the heterogeneity test at
`0003.0`'s own cost, deferring to whichever `0015 ## Feature design` came back as
under `0003.1` (spec 0003, AC-31). **`0015`'s after spread is 1** (35, 35, 36 entities
across the three runs), at or below the trigger. **AC-31 does not reopen.** The AC-2
heterogeneity question (spec 0002: should a bold sub label start a new unit) stays
untested, per feature 12's scope `Done when`, which states that explicitly rather than
leaving it silently untested.

**Worth reading alongside the spread**: `feature-33`'s after run is `13/13/13`, 0
entity rows disagreeing, yet only **1** entity accepted. This is not signature drift:
every run flags 9 to 11 of its 13 entities with a trap flag (7 to 8 of them
`multi_condition_split`), and `_entity_reasons()` routes a flagged entity to review on
the `known_trap_flag` trigger alone, independently of whether it agrees across runs
(`src/tracepath/extract/compare.py:268-269`; an `unclassified` entity routes the same
way, line 271). `0014`'s accepted count fell from 16 (before) to 10 (after) the same
way, on a unit whose entity counts held flat at 27/27/27 with 0 rows disagreeing both
times: prompt `0003.1`'s added rules are raising how many items get flagged, which
lowers accepted counts while agreement holds. That is a review volume input for
feature 11 (review volume and routing policy), not instability.

## Ruling

**Complete, 2026-10-03 (`0a9e77d`). The bar fails on 3 of 6 results**, against 5 of 6
in experiment 0005. All 45 required items are ruled, counted from
`data/ruling-sheet.md`'s own marks.

The bar is experiment 0005's (`../0005-held-out-prompt-examples/data/method-notes.md`,
"Accuracy bar for AC-16"): at least two thirds of entity marks and of relationship
marks in each unit agree.

| Unit | Entities (10) | Relationships (5) |
|---|---|---|
| `0014` `## Requirements` | 7 agree, 3 disagree: **pass** | 5 agree: **pass** |
| `0015` `## Feature design` | 2 agree, 8 disagree: **fail** | 5 agree: **pass** |
| `feature-33` | 5 agree, 5 disagree: **fail** | 3 agree, 2 disagree: **fail** |

- **Beside it, the blind self agreement check**: 7 of 10 matched, an upper bound, since
  memory makes a blind re-read look more consistent than an independent one would
  (method notes, candidate 4).
- **No disagreement is set aside as knowledge not in the text**, which the bar would
  report separately: 0 by keyword search of the reasons, the same check experiment
  0005 made.
- **Not ruled, by decision** (option A, 2026-10-02): the 44 dropped links (14, 15, 15)
  and the 9 cold read passages (3 per unit). The bar already fails on entity and
  relationship marks, so they cannot change the verdict. The bar's third clause, no
  more than 1 in 5 sampled dropped links real, is therefore unmeasured here.
- **Not like for like with 0005**: different units, and 0005 ruled 5 to 7 entities per
  group against 10 here. `0014`'s kind gained a worked example before this run, so its
  pass is weaker held out evidence than the other two units' results (see above).

Three pieces, none of them pass or fail on their own (AC-30):

- **The sample**: `prepare_ruling.py` (no API call) rebuilds `data/ruling-sheet.md`:
  10 entities evenly spaced through each unit's after run 1, 5 relationships evenly
  spaced through each unit's distinct after links, and up to 15 dropped links
  (written by a before run, by no after run) per unit, drawn at random (seed
  `20260928`, recorded and reproducible). AC-30 allows no unruled item in the entity
  or relationship samples once ruled (`unsure` is a real value, skipping is not); the
  dropped link sample follows the same rule experiment 0005's ruling method notes
  already set for a bundled `AC-N`, applied here to the draw instead of an even
  spread.
- **The cold read**: `prepare_cold_read.py` (no API call) rebuilds `data/cold-read.md`:
  3 passages per unit (one paragraph or bulleted item each, the same boundary
  `source_text()` uses), drawn at random (seed `20260928001`). Each passage's own text
  comes first; every link the before and after runs actually wrote from it, classified
  accepted, held or dropped, sits below a divider, read only after forming a cold
  answer. The question is whether a real link is missing from all three buckets alike.
- **The blind self agreement check**: `prepare_blind_reread.py` (no API call) draws
  10 items at random (seed `20260928002`) from experiment 0005's own already ruled
  `ruling-sheet.md` (42 ruled items across groups A, B, C) and writes `data
  /blind-reread.md`, each item's own text with no mark and no reason, next to `data
  /blind-reread-answers.md`, the same 10 items' original mark and reason, meant to
  stay closed until every item in the first file is re-marked cold.

Experiment 0005's own data and scripts are unchanged by any of this.

## Follow up

- [ ] `client.extract_once()`'s `except anthropic.APIError` clause does not catch a
  connection dropped mid stream (a raw `httpx2`/`httpcore2` error propagates past it
  uncaught), so a transient network fault crashes a pipeline run rather than being
  recorded as a failed, retriable attempt the way spec 0001's storage row intends.
  Worth a `/debug` pass on `src/tracepath/extract/client.py`; not fixed here, since
  this experiment's own `before_once()` needed the narrower fix and got it.
- [ ] The same function's `ValidationError` path (and the mirrored path here) snapshots
  usage before the API's final usage event lands, so a schema validation failure can
  record a wildly undercounted `output_tokens` (observed: 2, for a response one token
  short of validating). The artifact is not wrong to keep what the API reported; the
  gap is that nothing downstream (a cost report, a budget check) should trust a failed
  attempt's recorded tokens without knowing this. `run_recheck.py`'s stop conditions
  correct for it (`FAILED_ATTEMPT_FLAT_USD`); nothing in `src/` does yet.
