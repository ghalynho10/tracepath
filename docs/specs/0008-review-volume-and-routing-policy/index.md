# 0008. Review volume and routing policy

**Date**: 2026-10-17
**Status**: Proposed

## Summary

This spec decides how to handle the review queue's size (990 rows against 29 units today) without arguing from feel. It commits, before any measurement runs, two separate yes or no rules: one for a narrower hold rule that would let some held items into the graph outright, one for making the existing held item view (spec 0005) the default so held items are at least visible. Both rules are measured the same way, with no paid model call, over the eval questions already committed. Building the candidates and running that measurement is `/develop`'s job; a later amendment to this same spec records the result, without touching the rule itself. Because either adopted rule changes behavior two already accepted specs promised (spec 0002's routing, spec 0005's default view), adopting either one is its own commit, preceded by a dated amendment to those specs, the same way spec 0007 already amended spec 0002 once for its own narrower rule.

## Requirements

**User stories**:
- As the engineer, I want the decision between loosening the hold rule and showing held items by default to rest on what the eval actually shows, not on which one already has code, so the choice is evidence led and not a thumb on the scale for the view that happens to exist.
- As the engineer, I want the exact release condition and the exact adoption criteria written down before any candidate is built or measured, so the result cannot shape the rule that judges it.
- As the person who will later run the two sealed held out questions, I want this feature's choice locked and recorded before that run, since it and feature 13 are the two gates on releasing them.

**Acceptance criteria** (each holds one claim):

*The narrow hold rule (`--narrow-hold`)*
- **AC-1**: `--narrow-hold` is an off by default flag.
- **AC-1b**: It releases an identified entity or relationship whose full, deduplicated set of hold reasons (`ReviewItem.reasons`, spec 0002's queue grouping, already unioned across runs) is a non empty subset of `{known_trap_flag, endpoint_not_accepted}`, with `runs_disagree` absent from that set; equivalently, `compare_runs()` found no `runs_disagree` reason for its signature.
- **AC-1c**: `span_not_located` and `unclassified_type` holds are never released by this flag, alone or in any combination with another reason.
- **AC-1d**: The written copy of a released item is the first settled run's, the same rule spec 0005 AC-17 already uses for a held entity.
- **AC-2**: An `endpoint_not_accepted` link is released under `--narrow-hold` only when every entity it is waiting on is, in the same pass, accepted outright, released by `--code-pass`, or released by `--narrow-hold` itself; otherwise the link stays held. A `--code-pass` release counts as accepted here whether or not `--narrow-hold` is itself also given.
- **AC-3**: An entity released under `--narrow-hold` is written exactly as today's per entity `accepted_by` override already allows (`code_pass` for a code pass release, spec 0007 AC-16), stamped `accepted_by: narrow_hold` instead when `--narrow-hold`, not `--code-pass`, is what released it.
- **AC-3b**: No link carries any `accepted_by` value today other than its unit's own base value (`link_row()` always takes the unit's provenance as is; no release mechanism has ever overridden it per link, spec 0007's code pass releases only entities). This feature adds that per link override: a link released under `--narrow-hold` (AC-2) is stamped `accepted_by: narrow_hold`, the first link ever to carry a value other than its unit's base `accepted_by`.
- **AC-4**: AC-3's precedence (an entity qualifying for both `--code-pass` and `--narrow-hold` is stamped `code_pass`) applies only when both flags are given in the same `load`. With `--narrow-hold` alone, an entity that would also qualify for `--code-pass`'s rule is stamped `narrow_hold`, since code pass routing did not run.
- **AC-5**: `load` run with `--narrow-hold` prints, and `graph-build.json` records, how many items the rule released, broken down by hold reason and, for `known_trap_flag`, by which flag.
- **AC-5b**: `--narrow-hold` is accepted as an option on `load`, `eval`, `trace --eval`, and `review-queue`, mirroring how `--code-pass` is wired into each (spec 0007 AC-7).
- **AC-5c**: `graph-build.json` gains a `narrow_hold` key, absent meaning false.
- **AC-5d**: `eval` and `trace --eval` exit 1 with a clear message, before connecting to Neo4j, when their `--narrow-hold` setting differs from that key, mirroring `--code-pass`'s own refusal (spec 0007 AC-7c).
- **AC-5e**: `review-queue --narrow-hold` writes `artifacts/review-queue-narrow-hold.json`, never over the default file, mirroring `--code-pass` (spec 0007 AC-17).
- **AC-6**: `--narrow-hold` and `--code-pass` compose: every item either flag releases alone is still released when both are given, for every unit (the union is monotone; neither flag's release set shrinks when the other joins it).

*The per unit kind ratio (the scope row's own measurement, owed regardless of outcome)*
- **AC-7**: A script with no API call rebuilds routing fresh from `artifacts/runs/` (not from the possibly stale `artifacts/review-queue.json`) and reports, separately for accepted entities, held entity rows, and held link rows: the count per unit (record and section) and the count per unit kind (the section's shape: `Preamble`, a named `##` heading repeated across records, or a scope row), with the ratio of accepted entities to held rows at each grouping. A unit or kind with zero accepted entities reports "no accepted entities" rather than dividing by zero.

*The four way comparison (no paid call, over the committed run artifacts as they stand)*
- **AC-8**: A script with no API call runs the eval (`eval/linked-records-research.json` only, never the held out file) under four configurations, each with `--code-pass` off throughout to hold that variable fixed: baseline (neither flag), `--with-held` alone, `--narrow-hold` alone, and both together.
- **AC-8b**: It records the exact commit of `artifacts/runs/` it ran against.
- **AC-8c**: For every expected step of all five questions, under each configuration, it records one of three states against the baseline configuration: reached as accepted (spec 0005 AC-12), reached only as held (spec 0005 AC-12b, possible only when `--with-held` is in effect), or not reached.
- **AC-8d**: For each configuration, it also records the walk's own count of visited steps matching no expected item (spec 0004 AC-39), split into "among held steps" and "among accepted steps" for a configuration where `--with-held` is in effect.
- **AC-8e**: After the four runs, the graph is restored with a plain `load` (neither flag), so no nonstandard state is left behind.
- **AC-8f**: The "both flags together" configuration is a consistency check, not a third adoption path: if any expected step's state under both flags is worse (further from accepted) than the better of its two single flag states, the script stops and reports this instead of letting AC-9 or AC-11 trigger from it.

*Adopting the narrow hold rule*
- **AC-9**: The narrow hold rule's default flips from off to on (so `load` applies it unless told not to) only when, from AC-8's table comparing `--narrow-hold` alone against baseline: (a) at least one expected step newly reaches accepted that baseline did not reach accepted, and (b) no step that baseline reached accepted is, under `--narrow-hold`, not reached or reached only as held. Both conditions are necessary but not sufficient; the default additionally requires AC-10d's share condition to hold, from the blind ruling AC-10 to AC-10d set up. If (a) or (b) fails, the flag's default stays off, though the flag itself still exists and may be turned on by hand.
- **AC-10**: When AC-9's conditions (a) and (b) both hold, a blind ruling packet is drawn, following experiments 0012 and 0013's method: seeded at draw time, a committed hash before any ruling, the engineer's blind ruling, a score script with no API call.
- **AC-10b**: The packet holds up to 20 released items: every item `--narrow-hold` released that lies on the clean walk's own recorded path (spec 0005 AC-13's parent chain, steps and links both) from the start to any step that newly reaches accepted, included first; then a seeded stratified draw of further `--narrow-hold` released items corpus wide (stratified by hold reason, by `known_trap_flag` detail, and by entity or link kind) filling the remainder up to 20. If fewer than 20 such items exist across the whole corpus, the packet holds all of them, the same shortfall handling experiments 0012 and 0013 already use.
- **AC-10c**: The packet also holds 10 control items, drawn from accepted entities or links of the same kind as the released items and, where an accepted instance of the exact same type exists, matched by type too (falling back to kind only otherwise), the exact weakness experiment 0012 recorded corrected for.
- **AC-10d**: The narrow hold rule's default flips only when: the share of released items in the packet ruled agree is at least the share of control items ruled agree, with an item ruled unsure, or left unruled, counting against agreement on whichever side (released or control) it falls on. AC-9's conditions (a) and (b) being met is necessary but not sufficient; if this share condition fails, the narrow hold rule's default does not flip to on, and there is no partial, per question adoption beyond this.
- **AC-10e**: Independent of AC-10d's aggregate share result, the result record names every question whose AC-9(a) newly accepted step rests on an on path released item (AC-10b) that was itself ruled disagree or unsure in the packet, and that question's new PASS is not claimed, even when the narrow hold rule's default otherwise flips on under AC-10d.
- **AC-10f**: Adopting the narrow hold rule (AC-9's conditions and AC-10d's share condition both satisfied) changes spec 0002 AC-11's routing rule ("an item routes to review when ... any known trap flag is present"), the same kind of change spec 0007's AC-34 already made there for the code pass. The default flip is its own commit, preceded by a dated amendment to spec 0002 AC-11 recording the new exception, with the tests tied to that criterion updated in the same amendment commit, not left broken.

*Adopting show with status as the default (`--with-held`)*
- **AC-11**: `--with-held`'s default flips from off to on, across `load`, `trace`, and `eval` alike (the flag becomes an opt out, not an opt in), when, from AC-8's table comparing `--with-held` alone against baseline, at least one expected step moves from not reached to reached only as held. The count of held steps matching no expected item is reported beside this result as information; it is not itself part of the condition.
- **AC-11b**: Adopting show with status as the default changes spec 0002 AC-11 ("only accepted items are written to the graph by default") and spec 0005 AC-1 to AC-5 and its first key invariant ("no default path reads a held item"). The default flip is its own commit, preceded by a dated amendment to those criteria in both specs recording the new default, with every test tied to them updated in the same amendment commit, not left broken.

*The outcome, whichever it is*
- **AC-12**: The result record states that the review queue does not decide these answers, and that feature 9 (scope) is explicitly allowed to proceed at the current accept to review ratio, whenever neither AC-9/AC-10d/AC-10f together, nor AC-11/AC-11b, actually results in a default flip, naming which specific condition is why in each case: no expected step changed state under either candidate; a step changed but AC-9(b)'s no regression condition failed; or a step changed but AC-10d's share condition failed.
- **AC-13**: Whatever combination of AC-9/AC-10d/AC-10f, AC-11/AC-11b, and AC-12 actually obtains, the result record states explicitly that feature 9 is unblocked, naming which of those outcomes is why.
- **AC-14**: The committed rule above (AC-1 to AC-10f, AC-11, AC-11b, AC-12) is not edited by the later amendment that records the measured result. A real change to the rule or the candidate definitions after measurement is a separate, dated change with its own stated reason, and the result is first reported under the rule exactly as committed here.

## Options considered

### Option 1: Tune the routing (the narrow hold rule)

Measure where the queue over flags and release those items by a stated rule, keeping a person in the loop for what is left. This spec's `--narrow-hold` candidate is one concrete version: release `known_trap_flag` and `endpoint_not_accepted` holds where all three runs agree, the exact condition experiment 0013's evidence supports.

**Pros**:
- Reduces review volume directly when it wins, the scope row's own stated goal.
- Builds on a release mechanism (`accepted_by`, flag composition) spec 0007 already proved out for one narrower case.

**Cons**:
- Run agreement shows repeatability, not correctness; the blind ruling (AC-10) exists exactly because experiment 0012 could not call its own unit conclusive, and experiment 0013's sample is 20 items from `claude-sonnet-5` units only.
- Touches only two of five hold reasons; `runs_disagree`, the largest reason (471 rows), is untouched by design, because 0013's evidence points the other way for it (3 of 4 one run only items were wrong).

### Option 2: Question whether the queue belongs here (show with status)

Treat a held item the way `unclassified` and `:Unresolved` already work: visible in the chain, never silently blocking it. Spec 0005 already built this as an opt in view; this spec's question is only whether it becomes the default.

**Pros**:
- Matches the project's own standing rule, that the visible chain is the check, more literally than a review queue of any size does.
- Already built and measured once (experiment 0010); adopting it as default is a flag flip, not new code.

**Cons**:
- Never reduces review volume (spec 0005's own Consequences say so); feature 9's thousands of rows stay thousands of rows, just visible with a `HELD:` marker instead of absent.
- Cannot, by spec 0006's own scoring rule (AC-6b), ever turn a question's verdict into a pass; its only measurable win is visibility, which this spec's AC-11 states as a fact about the candidate rather than treating it as a defect in the comparison.

## Decision

**Chosen option**: neither Option 1 nor Option 2 is chosen here. This spec commits the exact release condition for Option 1 (AC-1 to AC-6) and the adoption criteria for both options (AC-9 to AC-13), with no code built and no measurement run yet. `/develop` builds both candidates behind off by default flags and runs the four way comparison (AC-7, AC-8 to AC-8f); a later amendment to this spec, made once that evidence exists, records which criteria were met and what that means for feature 9.

No community skill shaped this design; it changes only the project's own routing and CLI, not a third party library or framework.

## Rationale

Reasoning, the options considered, and the evidence: see [rationale.md](rationale.md).

## Feature design

**Data model sketch**. No new node kind and no new relationship type. One field's stamping logic is extended, not its shape: `accepted_by` (spec 0007), already a string on every entity row (plain accept: `""`, spec 0007's `unit_provenance()` default; code pass release: `code_pass`), gains a third per item value, `narrow_hold`. On a link row, `accepted_by` has never varied per item before, always carrying the unit's own base value (spec 0007 never stamps a link); this feature adds the first per link override, so a released link can carry `narrow_hold` too. No schema migration: the field already exists on every written row, only which value an individual row gets is new for links.

**Interface**:

| Command | New option | What it does |
|---|---|---|
| `tracepath load` | `--narrow-hold` | Releases `known_trap_flag`/`endpoint_not_accepted` holds under the AC-1 family's condition (AC-1b to AC-1d, AC-2), stamps `accepted_by: narrow_hold` on entities and links alike (AC-3, AC-3b, AC-4), prints the release counts (AC-5). Composes with `--code-pass` (AC-6). |
| `tracepath eval`, `tracepath trace --eval` | `--narrow-hold` | Scores the narrow hold routing; refuses a mismatch against `graph-build.json`'s `narrow_hold` key (AC-5c, AC-5d), mirroring `--code-pass`'s own refusal (spec 0007 AC-7c). |
| `tracepath review-queue` | `--narrow-hold` | Writes `artifacts/review-queue-narrow-hold.json`, never over the default file (AC-5e), mirroring `--code-pass` (spec 0007 AC-17). |
| `tracepath load`, `tracepath trace`, `tracepath eval` | `--with-held` (spec 0005, unchanged flag, default decided here) | If AC-11 and AC-11b's amendment both land, its default becomes on; the flag then opts a caller *out* of the held view instead of into it. If AC-11 does not trigger, the flag's behavior and default are unchanged from spec 0005. |

**Value sourcing**:

| Action | Value produced or displayed | Source |
|---|---|---|
| `load --narrow-hold` | which items are released | the committed routing output (spec 0002 AC-11's review items, grouped by `ReviewItem.reasons`), filtered to the AC-1 family's condition |
| `load --narrow-hold` | whether an `endpoint_not_accepted` link releases | whether every entity it is waiting on is accepted, `code_pass` released, or `narrow_hold` released in the same pass (AC-2), read from the same routing pass, not a second load |
| `load --narrow-hold` | `accepted_by` value on a released entity or link | `narrow_hold`, unless an entity also qualifies for `--code-pass` with that flag given too, in which case `code_pass` wins (AC-4); a link's value comes from whether `--narrow-hold` itself released that link (AC-3b), never from its endpoints' values |
| `load --narrow-hold` | the printed and recorded release counts | a tally over the released items by reason, and by flag name for `known_trap_flag` (AC-5) |
| `eval --narrow-hold`, `trace --eval --narrow-hold` | the mismatch refusal | `graph-build.json`'s `narrow_hold` key, absent meaning false, compared to the flag given (AC-5c, AC-5d) |
| AC-8's comparison script | each expected step's state under each configuration | spec 0005's clean walk (`reached`) and held walk (`held only`) over the graph built under that configuration, read exactly as spec 0005 AC-12/AC-12b already define them, with `--code-pass` held off throughout (AC-8, AC-8c) |
| AC-8's comparison script | the noise count per configuration | spec 0004 AC-39's existing "visited steps matching no expected item" count, read per configuration, split held versus accepted where `--with-held` is in effect (AC-8d) |
| AC-9/AC-10d's adoption check | whether the narrow hold rule's default flips | the comparison table (AC-8) plus, when triggered, the blind ruling's share result (AC-10d); no other input |
| AC-10's blind ruling packet | which items are on path, the stratified pool, and the controls | the clean walk's recorded parent chain (spec 0005 AC-13) from start to each newly accepted step (AC-10b), a stratified draw over every item `--narrow-hold` released corpus wide filling the packet to 20 (AC-10b), and 10 controls matched by kind and type (AC-10c), by `prepare_held_sample.py`'s own seeding and hashing pattern |
| AC-11's adoption check | whether `--with-held`'s default flips | the comparison table (AC-8) alone |
| AC-7's ratio script | the per unit and per unit kind counts | routing rebuilt fresh from `artifacts/runs/`, grouped by (record, section) and by the section's kind |

**Key invariants**:
1. The committed release condition (AC-1 to AC-2) and the committed adoption criteria (AC-9 to AC-12) are the only things that decide what ships. No argument from feel substitutes for them, and no later amendment edits them (AC-14).
2. `--narrow-hold` never touches `runs_disagree`, `span_not_located`, or `unclassified_type` holds. Only `known_trap_flag` and `endpoint_not_accepted`, and only when `runs_disagree` is absent from the item's reasons (AC-1b, AC-1c).
3. A released link's every endpoint is accepted, `code_pass` released, or `narrow_hold` released before the link itself releases (AC-2), the same ordering spec 0002 AC-11c already uses for the plain accept path, so `GraphWriteFailed`'s counter assertion still holds by construction.
4. No measurement in this feature spends API money; AC-7 and AC-8 read only committed artifacts and the existing graph. `tests/test_spend_fence.py`'s allowlist is unchanged by this feature.
5. The eval file read throughout is `eval/linked-records-research.json` only. `eval/held-out.json` is not opened by this feature, consistent with the scope's guard that it runs only after features 11 and 13 have both locked their choices.
6. Neither adoption (AC-9/AC-10d, AC-11) ships as a silent default change to an already Accepted spec; each is gated on its own dated amendment commit landing first (AC-10f, AC-11b), with that amendment's own tests updated in the same commit.

**Security model**: none. A local tool over public repository text; no new setting or secret; no API call and no model client.

**Configuration required**: none new.

**Critical test scenarios**:
- A hand built fixture with a `known_trap_flag`-only hold where all three runs agree (no `runs_disagree` reason present): `--narrow-hold` releases it, stamped `accepted_by: narrow_hold`, verifies **AC-1**, **AC-1b**, **AC-3**.
- A fixture item held for `span_not_located` or `unclassified_type` alone, and one held for both that and `known_trap_flag` together, both stay held under `--narrow-hold`, verifies **AC-1c**.
- A fixture where two runs find a signature and a third does not (a `span_not_located` entity) is left in place rather than taking a different run's copy, since the written copy is always the first settled run's, verifies **AC-1d**.
- The same fixture with an `endpoint_not_accepted` link whose waiting on entity is not released: the link stays held; once that entity releases (by either flag), the link releases too, stamped `narrow_hold`, verifies **AC-2**, **AC-3b**.
- A fixture item qualifying for both `--code-pass` and `--narrow-hold`: stamped `code_pass` when both flags are given, stamped `narrow_hold` when `--narrow-hold` alone is given, verifies **AC-4**.
- Over the committed artifacts, `load --narrow-hold` and `load` write identical accepted sets apart from the newly released items, and the printed counts match a hand count by reason, verifies **AC-5**, **AC-6**.
- `--narrow-hold` is accepted by `load`, `eval`, `trace --eval`, and `review-queue`, verifies **AC-5b**.
- `graph-build.json` carries a `narrow_hold` key only when the flag was given, verifies **AC-5c**.
- `eval --narrow-hold` against a graph loaded without the flag exits 1 before connecting, mirroring the existing `--code-pass` mismatch test, verifies **AC-5d**.
- `review-queue --narrow-hold` writes to the separate file, leaving the default file untouched, verifies **AC-5e**.
- `measure_hold_ratio.py`, rebuilding routing fresh from `artifacts/runs/`, reproduces a hand computed per unit and per unit kind count for at least one named unit and one named kind, and reports "no accepted entities" rather than dividing by zero on a crafted zero accepted unit, verifies **AC-7**.
- The four way comparison script runs over a fixture graph under all four configurations with `--code-pass` off, verifies **AC-8**.
- It records the exact `artifacts/runs/` commit it ran against, verifies **AC-8b**.
- It reports the right state (accepted, held only, not reached) for each expected step under each configuration, verifies **AC-8c**.
- It reports the right, correctly split noise count for each configuration, verifies **AC-8d**.
- After all four runs, the graph is left exactly as a plain `load` would leave it, verifies **AC-8e**.
- A crafted "both flags" result worse than the better single flag result stops the script with a report rather than flipping a default, verifies **AC-8f**.
- A synthetic table where one step newly reaches accepted and no step regresses triggers the blind ruling path; a table where a step regresses does not trigger it, verifies **AC-9**.
- The blind ruling packet is seeded, hashed before ruling, ruled blind, and scored with no API call, verifies **AC-10**.
- A corpus with fewer than 20 released items puts all of them in the packet; a corpus with more draws a stratified 20, with every on path item included first, verifies **AC-10b**.
- The packet's 10 controls are drawn from accepted entities or links of the same kind as the released items and, where one exists, the same type, verifies **AC-10c**.
- A packet where the released share of agree matches or beats the control share of agree allows the flip (treating one unsure or unruled item as a disagree on whichever side it falls); a packet where the released share is lower does not, verifies **AC-10d**.
- A synthetic table where a newly accepted step's on path item is ruled disagree names that question in the result record and does not claim its PASS, even while another question's flip still proceeds, verifies **AC-10e**.
- The default flip for `--narrow-hold` is refused by a test until a commit amending spec 0002 AC-11 lands first, verifies **AC-10f**.
- A synthetic table where a step moves from not reached to held only triggers `--with-held`'s default flip; a table with no such move does not, verifies **AC-11**.
- The default flip for `--with-held` is refused by a test until commits amending spec 0002 AC-11 and spec 0005 AC-1 to AC-5 land first, verifies **AC-11b**.
- A table where nothing changes under either candidate, a table with a regression, and a table with a failed share condition each produce AC-12's statement naming the specific reason, and name feature 9 as explicitly allowed, verifies **AC-12**, **AC-13**.

## Build plan

Tracer Bullet, as the project default: the thinnest real thread first (the measurements that need no new routing logic), then the routing change itself, then the regression and comparison scripts that depend on it, then the one gated step that needs the engineer (the blind ruling, only if triggered), then the mechanical flag flips (each behind its own spec amendment commit) and the result record.

1. `measure_hold_ratio.py`, no API call, rebuilding routing fresh from `artifacts/runs/`: the per unit and per unit kind accept to review counts and ratios, satisfies **AC-7**.
2. `--narrow-hold`: the release condition (AC-1b to AC-1d), the endpoint check (AC-2), the `accepted_by` stamp on entities and the new per link override (AC-3, AC-3b), its precedence against `--code-pass` (AC-4), the printed and recorded counts (AC-5), tested on a hand built fixture, satisfies **AC-1**, **AC-1b**, **AC-1c**, **AC-1d**, **AC-2** to **AC-5**.
3. Wire `--narrow-hold` through `eval`, `trace --eval`, and `review-queue` the same way `--code-pass` is wired, with the `graph-build.json` key, the mismatch refusal, and the separate review queue file, satisfies **AC-5b** to **AC-5e**.
4. Composition check: `load` with both flags together against each alone and neither, over the committed artifacts, confirms no double release and no lost accept, satisfies **AC-6**.
5. The four way comparison script, no API call, over the current graph and the five eval questions, with `--code-pass` held off, recording the `artifacts/runs/` commit, producing the per step, per configuration table and the split noise counts, restoring a plain `load` afterward, and treating the "both" configuration as a consistency check, satisfies **AC-8** to **AC-8f**.
6. Gate, no code: read the table. If AC-9(a) and (b) both hold, build the blind ruling packet (every on path item first, the stratified corpus wide draw filling it to 20, 10 matched controls, seeded, hashed, committed before ruling), get the engineer's ruling, score the agree share for released against control, and name any question whose on path item was ruled disagree or unsure, satisfies **AC-9**, **AC-10** to **AC-10e**. If AC-9(a) or (b) fails, skip straight to step 7 with the narrow hold rule's default left off.
7. For whichever default would flip (AC-9 and AC-10d for `--narrow-hold`, AC-11 for `--with-held`), write and commit the dated amendment to the affected spec(s) first (spec 0002 AC-11 for the narrow hold rule; spec 0002 AC-11 and spec 0005 AC-1 to AC-5 for show with status), updating their own tests in that same commit, then flip the default in a separate, following commit. If neither triggers, record the AC-12 statement instead. Satisfies **AC-10f**, **AC-11b**, **AC-12**.
8. Record the result: the ratio table (step 1), the four way comparison table (step 5), the ruling outcome if step 6 ran, the amendment commits if step 7 made any, and the explicit feature 9 unblocked statement (AC-13), in a new `experiments/` entry naming every commit in order. A follow up `/architect` session then amends this spec's `**Status**:` line and adds a dated note pointing at that result, without editing the committed rule (AC-14).

## Consequences

**Positive**:
- The decision between the two candidates rests on a committed, pre measured rule, so neither wins by already having code.
- Whatever the result, feature 9 is explicitly unblocked (AC-13), closing the cycle the scope row names (feature 9 blocked on this feature, this feature waiting on feature 13, now closed).
- The per unit kind ratio (AC-7) is produced regardless of outcome, satisfying the scope row's own measurement requirement even in the all fallback case.
- Neither adoption can silently contradict an already Accepted spec; the amendment first ordering (AC-10f, AC-11b) keeps spec 0002 and spec 0005 internally consistent at every commit.

**Negative / tradeoffs**:
- If AC-9's conditions hold but the blind ruling's share condition (AC-10d) fails, the narrow hold rule stays off despite showing a real gain on the comparison table; that is the committed rule working as intended, not a bug, but it means a visible improvement can still not ship.
- `--with-held` becoming the default, if AC-11 and its amendment both land, changes default output for the whole project: every `load`, `trace`, and `eval` call then shows held items unless the caller opts out, a visible behavior change beyond this one feature's own commands.
- The all fallback case (AC-12) leaves the 990 row queue exactly as it is; feature 9 is allowed to proceed, but review volume itself is untouched, which is the scope's own named alternative, not a gap in this spec.
- Adopting either candidate now costs two commits instead of one (the amendment, then the flip), which is slower than a single change but is what keeps the already Accepted specs honest.

**Neutral**:
- `accepted_by: narrow_hold` is a new value on an existing field; nothing downstream that reads `accepted_by` needs to change unless it matches on a closed set of known values.
- The comparison script (AC-8) and the ratio script (AC-7) are new, standalone tools, not changes to `report.py`'s existing scoring; they read the same graph and run files `eval` already reads.

## Follow-up

- [ ] Once this feature's choice is locked (the amendment in Build plan step 7, or the AC-12 fallback) and feature 13 confirms its own, `eval --eval-file eval/held-out.json --release-held-out` may run, with the engineer's own check of both held out chains against the corpus first, per the scope's guard.
- [ ] `/scope`: feature 11's row cites 403 queue rows against 71 accepted entities; the current figure is 990 rows across 29 units (`2042871`). The row also states an ordering ("run both policies through the eval before writing the spec") that this spec resolves by committing the rule now and measuring after (see rationale.md's Context); `/scope` may want to record that resolution in the row itself.
- [ ] `verify.md` owes steps for every AC, added by `/develop` with the build.
- [ ] `/sync` adds `load --narrow-hold`, `review-queue --narrow-hold`, and the (possibly flipped) `--with-held` default to the commands in `AGENTS.md` after the build.
