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
- **Rule once** (AC-27): an item both arms contain is ruled once. The runner up, ruling each arm fully, doubles the work for no new information. With the narrow pass, the arms differ only in which entities are accepted. Since the cut of 2026-10-12 no drawn item is in both arms (a released entity is by definition not accepted in the control, and stage two draws no control links), so the rule does no work in this step; it stays for the full bar measure on feature 13's final state.
- **The gate** (AC-19): a cross check of the third draft pointed out that experiment 0005's full bar mostly measures things the pass does not change (other accepted entities, relationship marks, links held for disagreement), and that bar failed 5 of 6 results in experiment 0005 (`README.md:133`). The engineer chose to gate this step on the released entities and the released links (each at the full bar's own two thirds, the links only in units with at least 5 ruled released link marks, so no new number is invented) plus a no regression check. Links are gated because switching the pass on by default puts the released links into the chains `eval` and `trace` show, and wrong ones would mislead, committed before any paid call, and to report the full bar every time. Feature 13's Done when still requires its final state to meet the full bar. The ruling was cut on 2026-10-12, below: the full bar is no longer reported in this step, and the links are gated in a second stage.
- **After the cross unit hold** (AC-21): a dropped link is taken after it, because that is what a chain sees.
- **Scope of this spec**: the engineer cut the flag change, the type definitions and all machinery for comparing two prompt states (separate roots, per arm checks) from this spec. They come back in a later spec or amendment, designed from this step's rulings. The cross checks' findings about that machinery are kept in the Follow up as inputs.

**The calibration count, amended 2026-10-12.** AC-31 stopped the build: under `claude-sonnet-5-5` the calibration unit counts 61,110 tokens, against the 61,108 experiment 0006 measured and `claude-sonnet-5` still counts. The engineer asked for every chosen unit to be counted under both models before deciding, with a rule set in advance: one constant difference is an overhead per request, and differences that vary mean a tokenizer change and stop the work. All four differ by exactly 2 tokens (Evidence), across units from 59,433 to 62,028 tokens with different texts, so the text is tokenized the same and the new model adds 2 tokens to each request. The calibration count moves to the new model's figure, 61,110 (AC-31f), so the check keeps its job: it still catches a prompt that changed under the measured figures. The runner up, a calibration figure per model, would keep `claude-sonnet-5` priced too, but nothing in this spec extracts on it, and without it a run on that model refuses before any call, which spends nothing.

The cached prefix stays 57,494 (AC-31g). It was measured from a billed cache write on `claude-sonnet-5` (experiment 0008), not from the count endpoint, which counts the whole request and cannot split it into its cached and uncached parts. So no free count can say whether the 2 tokens sit in the prefix. It cannot be checked until the first paid call on `claude-sonnet-5-5` reports its cache write, and build plan step 6 compares it then. The engineer chose to keep the figure rather than move it by 2, because moving it would assume where the overhead sits. Either way the effect is at most 2 tokens at the $4 cache write rate, $0.000008 per call.

**The cut ruling, amended 2026-10-12.** Before any paid call, the engineer cut step one's ruling to what the gate reads. The draw as written asked for about 135 marks over the three units (per unit, 30 control items: 10 entity marks, 5 relationship marks and 15 dropped links; and up to 15 released items), while the gate reads only the released items. The relationship marks and the dropped links cannot move with the pass: it creates no link and drops none (AC-13, AC-15), so both arms hold the same links apart from the ones it releases, and those marks measure the model, not the pass. The full bar is still owed, once, on feature 13's final state (AC-18b, AC-28e), which is where its Done when puts it.

The ruling now runs in two stages. Stage one draws, per unit, 5 released entity marks and 3 control entity marks, mixed blind as before, about 24 marks in all, and gates on AC-19's two thirds over the 5 released ones; a unit with fewer than 5 released entities stays inconclusive (AC-19c). The 3 control marks are there to keep the packet blind, so the engineer cannot tell a released entity by its place in the packet; at 3 per unit they say little about the control arm, and they are reported, not gated (AC-28d). Stage two runs only if stage one passes and the engineer wants the pass on by default (AC-19h): it draws up to 5 released link marks per unit and gates on AC-19f's two thirds where 5 are drawn. Links are gated only on the way to the default because the reason for gating them is the default: a released link reaches the chains `eval` and `trace` show only once the pass is on by default. Gating a unit by the number drawn, not the number ruled, means a mark ruled `unsure` cannot move a unit out of the gate.

What the cut costs, stated in the spec's Consequences: 5 marks per unit make a coarse gate (4 of 5 passes, 3 of 5 fails), and stage two's packet is not blind to the arm, since every item in it is a released link.

Where the pass lives (a pure function that returns a set of ids, called from rebuild only, read by `route_runs`) is the author's call. `run_unit` has no command line caller, so extraction does not need it. The runner up, hiding the logic inside `route_runs`, would mix the pass into the comparison with no way to switch it off.

## Evidence

- Held item counts: the table above, from `load --with-held` and `trace --eval N --with-held` on 2026-10-09, with the graph restored by a plain `load` after.
- The scarcity of fresh units: from `split_units` over the corpus specs, minus the records in AC-24, 2026-10-09. Never extracted sections with acceptance criteria in Requirements: 0009 (24), 0013 (12), 0015 (17).
- The free token counts of 2026-10-12, `messages.count_tokens` only, no extraction call, the same request `count_input()` builds (`src/tracepath/extract/metered.py`), prompt `0003.1`:

  | Unit | `claude-sonnet-5` | `claude-sonnet-5-5` | Difference |
  |---|---|---|---|
  | `0014:Requirements` (calibration) | 61,108 | 61,110 | +2 |
  | `0009:Requirements` | 62,028 | 62,030 | +2 |
  | `0013:Requirements` | 59,433 | 59,435 | +2 |
  | `0015:Requirements` | 61,284 | 61,286 | +2 |
- Estimated cost is not given here. It is measured at step 5 from a per call cost and the real number of calls, as `docs/reflexes.md` requires.
