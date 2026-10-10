# 0007. Extraction accuracy, step one: rationale

The decision record for [index.md](index.md). `/develop` skips this file.

## Context

Prompt `0003.1` makes the three runs agree more often, but agreement is not accuracy. Prompt `0003.1` failed the engineer's bar on 3 of 6 results in experiment 0006 and 5 of 6 in experiment 0005. Spec 0003 closed feature 12 without fixing this and listed the candidate causes. The eval shows the cost: four of the five questions fail, and in both views the items that break them are mostly held for review.

A read only count on 2026-10-09 (no API call) classed the held items on eval questions 1, 2, 3 and 5, from `load --with-held` and `trace --eval N --with-held`, matched to `artifacts/review-queue.json` by entity id:

| Question | Entities, runs disagree | Entities, flag only | Links, runs disagree | Links, flag only |
|---|---|---|---|---|
| 1 | 1 | 11 | 3 | 9 |
| 2 | 0 | 3 | 3 | 3 |
| 3 | 2 | 4 | 4 | 2 |
| 5 | 2 | 3 | 1 | 0 |
| Total | 5 | 21 | 11 | 14 |

Twenty of the 21 flag only entities carry `multi_condition_split`. Question 3's middle step (`0002#requirements:6` and both its links) is held because the runs disagree, so routing alone cannot open that path. "Runs agree" here means the three runs share the item's signature (id, line, label, type), not its span text or its flags: for `0007/AC-13` the three runs differ on the flag and the span prefix, and for `0002/AC-10` they differ on rejected spans. The engineer ruled `0002/AC-10` agree and `0007/AC-13` unsure, both tagged `gap:bundled-ac`, because a criterion that bundles several conditions is one item under the engineer's card.

A second read only check (the engineer's, 2026-10-09) found that the parser and all nine model runs agree exactly on acceptance criterion entities in the Requirements sections of 0002, 0008 and 0021, while in two of those units only 7 of 38 and 10 of 23 entities were accepted (the third unit's figure was not given). Spec 0002's principle is that what a parser can decide, a parser decides. The pipeline already does this for struck text, checkboxes and binding rule labels (`precheck.py`, `label_binding_rules`).

## Options considered

### Option 1: Fix in place, one change per measured step, code first

Switch the model, add an off by default code pass that narrows one hold, and measure it by comparing the pass off and on over the same runs with the engineer's blind rulings. The flag change and the type definitions are later steps of feature 13, each designed after this step's rulings and judged alone on fresh units chosen beforehand.

**Pros**:
- One cause per measured difference, which is the project's rule for this kind of work.
- The first two changes cost no API credit to build, and one paid extraction serves as baseline and after.
- Matches the engineer's card (a criterion with an `AC-N` id is one item, kept whole and flagged, ruled agree).

**Cons**:
- Slow: feature 13 takes several measured steps, each with its own units and rulings, and only the first is designed here.
- Fresh acceptance criterion units are scarce: only 0009, 0013 and 0015 `## Requirements` remain, and this step uses them all, so later steps measure on sections with fewer flags.
- The pass releases items on code's authority while runs agreeing shows repeatability, not correctness, so its result must be measured before its default is turned on.

### Option 2: Routing policy first (feature 11)

Write the policy that releases items held only by a flag while the runs agree, then fix what is left.

**Pros**:
- Opens question 1 almost at once, since 11 of its 12 held entities are flag only.

**Cons**:
- Runs agreeing shows repeatability, not correctness, so it would release items whose accuracy was never measured.
- The scope's own reason: setting routing first risks tuning thresholds around a defect. Question 3's path is held for disagreement, which a policy cannot open.

### Option 3: Prompt first (type definitions and rules together)

Write the eight type definitions and the splitting rules now, and measure the whole prompt change at once.

**Pros**:
- Targets the causes named in spec 0003's Follow up directly.

**Cons**:
- Several changes at once, so a difference has no single cause.
- The definitions are meant to be written from this round's rulings, which do not exist yet.

## Rationale

Option 1. The count shows two different problems. Flag only items (21 entities, 14 links) are held by a flag that spec 0003 AC-28 raises on purpose for every bundled criterion, and the engineer's card rules a bundled criterion kept whole and flagged as agree. Disagreement items (5 entities, 11 links, including question 3's middle step) are an extraction problem the model must fix. Doing the code step first stops the deliberate flag from holding an item whose three runs agree on id and type, and it leaves a cleaner base to measure the later steps on.

The pass is deliberately narrow. A cross check by a second model on the first draft (a pass that also set spans, rejected spans, removed inner entities and re pointed links) found that it clashed with spec 0002 AC-5 (the unstruck text of a split id keeps the verbatim id, so a struck only span would give the struck text the id), that a partial strike is undefined, that `Location` carries no end offset, and that the ruling card would rule a flag stripped entity `disagree`. The engineer chose the narrow form: the entity keeps its flag, only the hold is lifted, spans stay with the model, struck bullets stay with the model. That form removes those problems and keeps one cause per step. It also means the code pass does release items on code's authority, which the Summary states; it is measured before its default is turned on.

The engineer asked for the model switch as an engineering decision, not an accuracy claim: measure and tune this feature and feature 11 on the model that will be kept. This was checked against Anthropic's model pages on 2026-10-09: `claude-sonnet-5-5` is $2 and $10 per million tokens, the same as `claude-sonnet-5`, its 1 hour cache write price is $4 (the same as `claude-sonnet-5`), its cache read price is $0.10 against $0.20, its cache minimum is 512 tokens, and it is not retired sooner than 2027-09-28. `claude-sonnet-5` is Active (legacy), not retired sooner than 2027-06-30, so nothing forces the switch. The pages do not state the effort recalibration, so that stays an open item in the Follow up.

Three readings in this spec are the author's, not the engineer's, and are flagged for correction:
- **Dropped link** (AC-21) is defined as a relationship some run wrote that is not in the accepted set. Experiment 0005's version compared two prompts, which has no meaning in steps that change no prompt.
- **Rule once** (AC-27): an item both arms contain is ruled once. The runner up, ruling each arm fully, doubles the work for no new information. With the narrow pass, the arms differ only in which entities are accepted, so most sampled items are shared.
- **The gate** (AC-19): a cross check of the third draft pointed out that experiment 0005's full bar mostly measures things the pass does not change (other accepted entities, relationship marks, links held for disagreement), and that bar failed 5 of 6 results in experiment 0005 (`README.md:133`). The engineer chose to gate this step on the released entities and the released links (each at the full bar's own two thirds, the links only in units with at least 5 ruled released link marks, so no new number is invented) plus a no regression check. Links are gated because switching the pass on by default puts the released links into the chains `eval` and `trace` show, and wrong ones would mislead, committed before any paid call, and to report the full bar every time. Feature 13's Done when still requires its final state to meet the full bar.
- **After the cross unit hold** (AC-21): a dropped link is taken after it, because that is what a chain sees.
- **Scope of this spec**: the engineer cut the flag change, the type definitions and all machinery for comparing two prompt states (separate roots, per arm checks) from this spec. They come back in a later spec or amendment, designed from this step's rulings. The cross checks' findings about that machinery are kept in the Follow up as inputs.

Where the pass lives (a pure function that returns a set of ids, called from rebuild only, read by `route_runs`) is the author's call. `run_unit` has no command line caller, so extraction does not need it. The runner up, hiding the logic inside `route_runs`, would mix the pass into the comparison with no way to switch it off.

## Evidence

- Held item counts: the table above, from `load --with-held` and `trace --eval N --with-held` on 2026-10-09, with the graph restored by a plain `load` after.
- The scarcity of fresh units: from `split_units` over the corpus specs, minus the records in AC-24, 2026-10-09. Never extracted sections with acceptance criteria in Requirements: 0009 (24), 0013 (12), 0015 (17).
- Estimated cost is not given here. It is measured at step 5 from a per call cost and the real number of calls, as `docs/reflexes.md` requires.
