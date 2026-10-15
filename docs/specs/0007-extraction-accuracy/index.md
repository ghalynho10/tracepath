# 0007. Extraction accuracy, step one: the model and the code pass

**Date**: 2026-10-09
**Status**: In Progress
**Amended**: 2026-10-12, after AC-31 stopped the build, with no paid call. The calibration count moves to the `claude-sonnet-5-5` figure (AC-31, AC-31f, AC-31g), and build plan steps 1 and 4 are written (specs 0001 and 0002 amended). Reasons and counts in [rationale.md](rationale.md).
**Amended again**: 2026-10-12, before any paid call. Step one's ruling is cut to what the gate reads, in two stages: stage one rules released entities against a few control entities, and stage two rules released links only if stage one passes and the engineer wants the pass on by default. The full bar is no longer measured in this step (AC-18b, AC-19 to AC-19i, AC-25 to AC-25f, AC-28 to AC-28e). Reasons in [rationale.md](rationale.md).
**Amended, gate fixes**: 2026-10-12, before any paid call. Both gates count over every drawn mark, so a mark not ruled agree counts against; stage two gates every unit with a released link, however few; stage two's packet mixes in 2 control links per unit, blind (AC-18c, AC-18d, AC-19, AC-19f, AC-19g, AC-25f, AC-25g, AC-26b, AC-26c, AC-28, AC-28d). Reasons in [rationale.md](rationale.md).

## Summary

This spec is the first measured step of feature 13 (extraction accuracy). It does two things. It moves the extraction model from `claude-sonnet-5` to `claude-sonnet-5-5` (same price, a base decision, not an accuracy claim). And it adds a code pass that narrows one hold: an acceptance criterion item whose three runs agree on its id and type is no longer held only because it carries the `multi_condition_split` flag. The item keeps the flag, so the engineer's ruling convention applies unchanged. The step is measured by comparing the pass off against on over the same run files, with the engineer's blind rulings. It passes on what it changed, in two stages: first the released entities reach two thirds agreement and nothing accepted before is lost; then, only if the engineer wants the pass on by default, the released links reach two thirds too. Each gate counts over every drawn mark, so only a mark ruled agree counts for it. Experiment 0005's full bar is not measured in this step; it is measured once on feature 13's final state. The pass releases items on code's authority, so it stays off by default until a measurement passes. The flag change and the type definitions stay in feature 13 and get their own spec or amendment once this step's rulings exist.

## Requirements

**User stories**:
- As the project's author, I want the accuracy of the items the pass releases measured by my own rulings, so that I know they are right, not only repeatable.
- As the person who will set the routing policy, I want to know exactly which hold the code pass narrowed and by how much, so that I start feature 11 from a known state.
- As the person reading a chain, I want the default graph to change only in ways the spec records, so that no default output changes silently.
- As the person spending API credit, I want every paid call to have a stated bound or estimate and my go ahead first, so that no step spends past what I approved.

**Acceptance criteria** (each holds one claim):

*The model switch (free)*
- **AC-1**: `DEFAULT_MODEL` in `src/tracepath/config.py` is `claude-sonnet-5-5`.
- **AC-2**: The default effort stays `medium`.
- **AC-3**: `PROMPT_VERSION` and the worked examples are unchanged by this spec, so no prompt text differs.
- **AC-4**: `load` prints one line of units per model, read from each unit's run artifacts, beside the existing units per prompt version line.
- **AC-5**: Every review queue row for a unit names the model its run artifacts name.
- **AC-5b**: The `--model` option of `review-queue` is used only for a held link whose unit has no run artifacts, and it defaults to `DEFAULT_MODEL`.
- **AC-5c**: The cost estimate prices a call at the rates of the model in the settings.
- **AC-5d**: Recorded spend is priced at the rates of the model the run artifact names.
- **AC-5e**: A model with no rate row makes the estimate and the spend figure refuse, not fall back to another model's rates.
- **AC-5f**: The rates per million tokens are: `claude-sonnet-5`, input $2, output $10, 1 hour cache write $4, cache read $0.20; `claude-sonnet-5-5`, input $2, output $10, 1 hour cache write $4, cache read $0.10.

*The code pass (free to build and test)*
- **AC-6**: A plain `review-queue` run in a temporary root holding the committed run files writes `artifacts/review-queue.json` byte for byte as committed.
- **AC-6b**: A plain `load` writes `artifacts/graph-build.json` with no `code_pass` key.
- **AC-7**: `load`, `review-queue`, `eval` and `trace --eval` each take `--code-pass`.
- **AC-7b**: `load --code-pass` writes `"code_pass": true` into `artifacts/graph-build.json`.
- **AC-7c**: `eval` and `trace --eval` exit 1 with a clear message, before they connect to Neo4j, when their `--code-pass` setting differs from the `code_pass` setting in `artifacts/graph-build.json`, a missing key meaning false.
- **AC-7d**: With `--code-pass`, the routing that `eval` and `trace --eval` score and explain is the routing with the pass applied.
- **AC-8**: `review-queue --code-pass` writes `artifacts/review-queue-code-pass.json`.
- **AC-8b**: `review-queue --code-pass` never rewrites `artifacts/review-queue.json`.
- **AC-9**: An id is a parsed bullet when the unit's section is `Requirements`, a top level bullet begins `- **AC-N**:` (N digits, an optional lower case letter), and the text after the colon does not open with `~~`.
- **AC-10**: A parsed bullet is code decided only when, in each of the unit's three runs, exactly one entity carries the verbatim id `AC-N`, and that entity is typed `AcceptanceCriterion` and has the canonical id `record/AC-N`.
- **AC-11**: An id carried by two parsed bullets in one unit is not code decided, and the unit's report names the id.
- **AC-12**: A code decided entity is not held for `known_trap_flag` when the flags of each of the three runs' entities for that id are a subset of `multi_condition_split`, so a run with no flags qualifies.
- **AC-12b**: A code decided entity released by AC-12 keeps the flag in its `flags` property.
- **AC-12c**: The `known_trap_flag` reason is dropped only from an entity that would otherwise be accepted, so an entity held for another reason keeps its full reason list.
- **AC-13**: The pass never adds a hold: an entity accepted without `--code-pass` is accepted with it.
- **AC-14**: A code decided entity whose signature differs between runs is still held for `runs_disagree`.
- **AC-15**: With `--code-pass`, every span, rejected span, entity and link the runs wrote is exactly what it was without it; only which items are accepted can differ.
- **AC-15b**: With `--code-pass`, the queue row of an entity that stays held is what it was without it.
- **AC-15c**: With `--code-pass`, the queue row of a link that stays held names only the endpoints still unaccepted with the pass applied.
- **AC-16**: An entity accepted with the code decided set and not without it carries the node property `accepted_by` with the value `code_pass`, and every other entity keeps `auto`.
- **AC-17**: `load --code-pass` prints, per unit, the code decided ids, how many entities AC-12 released, how many links were released as a result (counted by resolving the whole corpus with and without the pass), how many parsed bullets were not code decided, how many bullets opening with `~~` after the colon were left to the model, and how many other top level `- **AC-` bullets in Requirements failed the parse of AC-9.

*The measure*
- **AC-18**: The full bar is experiment 0005's, with three clauses per unit: at least two thirds of ruled entity marks agree, at least two thirds of ruled relationship marks agree, and no more than 1 in 5 sampled dropped links is real.
- **AC-18b**: The full bar is not computed in this step. It is measured once, on feature 13's final state, as feature 13's Done when requires. **Amended 2026-10-12**: it was computed and reported for both arms; the pass creates and drops no links, so the relationship and dropped link marks could not move with it.
- **AC-18c**: A mark the engineer rules `unsure` is counted on its own and is neither agree nor disagree, except in the gates of AC-19 and AC-19f, where it counts against. **Amended 2026-10-12**: the gate exception.
- **AC-18d**: A disagreement that comes only from knowledge not in the text is reported apart and does not fail a unit under the full bar; in the gates of AC-19 and AC-19f it counts against like any mark not ruled agree. **Amended 2026-10-12**: the gate exception.
- **AC-18e**: A sampled item left unruled is reported apart from the counts.
- **AC-19**: The gate of stage one: in every chosen unit, at least 4 of the 5 drawn released entity marks are ruled agree, a mark ruled `unsure`, ruled disagree or left unruled counting against. The pass changes only the released items, so the step is judged on what it changed. **Amended 2026-10-12**: over the 5 released entity marks of AC-25b, not up to 10; and two thirds of every drawn mark, not of the ruled ones, so ruling hard items `unsure` can never make a unit pass.
- **AC-19b**: No regression: every entity and link accepted without `--code-pass` is accepted with it, checked by code over the chosen units.
- **AC-19c**: A chosen unit with fewer than 5 released entities is inconclusive, and stage one passes only when no chosen unit is inconclusive.
- **AC-19d**: When either stage fails or is inconclusive, the pass stays off, the result is recorded, and what comes next is the engineer's decision.
- **AC-19e**: The gate (AC-19 to AC-19i) and its reason are committed before the first paid call.
- **AC-19f**: The gate of stage two: in every chosen unit with at least one released link, at least two thirds of its drawn released link marks are ruled agree, however few are drawn, a mark not ruled agree counting against (1 of 1, 2 of 2, 2 of 3, 3 of 4, 4 of 5). **Amended 2026-10-12**: it gated only units where 5 were drawn, over the ruled ones.
- **AC-19g**: A chosen unit with no released link is reported as having none, and the result says so. **Amended 2026-10-12**: a unit with fewer than 5 drawn was reported, not gated.
- **AC-19h**: Stage two runs only after stage one passes and the engineer says they want the pass on by default; otherwise no link is drawn or ruled. **Added 2026-10-12.**
- **AC-19i**: A stage one pass alone never turns the default of the pass on; that needs stage two to pass. **Added 2026-10-12.**
- **AC-20**: The control is the run files read without `--code-pass` and the treatment is the same run files read with it.
- **AC-21**: A dropped link is a relationship, keyed by `relationship_signature`, that at least one of the three runs wrote and that is not accepted after the cross unit hold. It is real when the engineer rules it a true relationship stated in the text.
- **AC-22**: The chosen units are listed in `experiments/<step folder>/units.json` with the `expected_model`, and the step is scored from no other list.
- **AC-22b**: The artifacts of the chosen units were extracted after the commit date of `units.json` (shown by their `extracted_at` values), so the units were chosen first.
- **AC-23**: No chosen unit is in records 0004, 0005, 0010, 0016, 0017, 0018 or 0020 (the held out questions may cite them), in records 0006, 0008, 0012, 0019 or `scope` (worked examples draw on them), or in records 0002 or 0021 (the pass was checked on them).
- **AC-24**: No chosen unit is one experiments 0005 and 0006 ruled, read from the unit lists in those two experiments' READMEs.
- **AC-25**: Stage one draws, per unit, 3 entity marks from the control arm's accepted entities, at random, mixed blind with the marks of AC-25b. **Amended 2026-10-12**: it drew 10 entity marks, 5 relationship marks and 15 dropped links from the control arm.
- **AC-25b**: Stage one draws, per unit, 5 released entity marks, at random. **Amended 2026-10-12**: it drew up to 10.
- **AC-25c**: The seed of each draw is recorded.
- **AC-25d**: A draw that asks for more items than exist rules all there are and states the shortfall.
- **AC-25e**: Stage two draws, per unit, up to 5 released link marks, at random, the links found by resolving the corpus with and without the pass. **Added 2026-10-12.**
- **AC-25f**: This step draws no dropped links. **Added 2026-10-12. Amended 2026-10-12**: it also drew no control relationship marks, before AC-25g.
- **AC-25g**: Stage two draws, per unit, 2 relationship marks from the control arm's accepted links, at random, mixed blind with the marks of AC-25e, and ruled but not gated. **Added 2026-10-12.**
- **AC-26**: The engineer rules the drawn items mixed, each under an opaque id and in shuffled order.
- **AC-26b**: For each stage, the hash of the file naming each item's arm is committed before that stage's rulings. **Amended 2026-10-12**: per stage.
- **AC-26c**: Each stage's arm file itself is committed after that stage's rulings.
- **AC-26d**: A packet item shows its opaque id, its span (for a link, both endpoint spans and its phrase), its type and its source line, and no flag, no reason and no arm.
- **AC-26e**: After the rulings, code counts as disagree an entity the engineer tagged `gap:bundled-ac` and ruled agree whose entity carries no `multi_condition_split` flag, and reports how many it flipped.
- **AC-27**: An item present in both arms, the same canonical id with the same span text for an entity or the same signature for a link, is ruled once.
- **AC-27b**: Each arm's score is computed from the item rulings.
- **AC-28**: The result shows, for every chosen unit, the ruled released entity marks and the ruled control entity marks side by side, and the ruled released link marks and control link marks side by side when stage two ran. **Amended 2026-10-12**: it showed the full bar of both arms.
- **AC-28b**: The result shows the number of held items on the chosen units.
- **AC-28c**: The result shows eval chain reach from `tracepath eval` over `eval/linked-records-research.json`, before and after the chosen units landed in the graph.
- **AC-28d**: None of the held item count, eval chain reach, the control entity marks and the control link marks is a pass condition.
- **AC-28e**: The result states that experiment 0005's full bar was not measured in this step and is owed on feature 13's final state. **Added 2026-10-12.**
- **AC-29**: `extract` exits 1 before any call when the settings model differs from the model given by `--expect-model`.
- **AC-29b**: Scoring refuses any run whose artifact `model` differs from the `expected_model` in `units.json`.
- **AC-30**: The tests and tooling of this spec never open `eval/held-out.json`.

*Money*
- **AC-31**: The free token count under `claude-sonnet-5-5` runs before any paid call, and the work stops with a report when it differs from the calibration count. **Amended 2026-10-12**: it differed (61,110 against 61,108) and the work stopped. Every unit counted differs by the same 2 tokens, so the figures are moved as AC-31f and AC-31g say.
- **AC-31f**: The calibration count in `cost.py` is 61,110, the count of `0014:Requirements` under `claude-sonnet-5-5`. **Added 2026-10-12.**
- **AC-31g**: The cached prefix in `cost.py` stays 57,494 until a paid call on `claude-sonnet-5-5` reports its cache write. **Added 2026-10-12.**
- **AC-31b**: The first paid call on `claude-sonnet-5-5` runs only on the engineer's go, given after its per call bound is stated.
- **AC-31c**: After that call, a measured estimate for the remaining calls is given and the engineer's go waited for again.
- **AC-31d**: No paid call runs without the engineer's go.
- **AC-31e**: The estimate line names the model it prices.
- **AC-32**: The paid extraction of the chosen units runs with the repository as root, so the units join the default graph.

*Boundaries*
- **AC-33**: This spec writes no routing policy; the code pass narrows one hold only.
- **AC-33b**: This spec runs no question of the held out file.
- **AC-34**: Spec 0002 is amended so that `accepted_by` may also read `code_pass`, so that line 199 and its flag churn test (line 234) say what the pass changes.

## Decision

**Chosen option**: Option 1: Fix in place, one change per measured step, code first.

Switch the model and add an off by default code pass that narrows one hold, then measure it by comparing the pass off and on over the same runs. Later steps of feature 13 are designed afterwards, from the rulings made here.

## Feature design

**Where the pass lives**: a new pure function in `src/tracepath/extract/codepass.py`, `code_decided_ids(unit, identified_outputs) -> frozenset[str]`, called only from `rebuild.py` (`committed_units`, which gains a `code_pass` parameter, also reached from `_committed` in `cli.py` so `eval` and `trace --eval` score the same routing). `route_runs(outputs, code_decided=frozenset())` receives the set. It already has all three outputs, so it computes the flag union itself: for a first run entity whose canonical id is in the set and whose reasons are exactly `[known_trap_flag]`, it accepts the entity when the flags of every run's entity with that id are only `multi_condition_split`, and lists it in a new `RoutedUnit.released`. It never adds a hold, because today only the first run's flags hold an entity (`compare.py:342`, `:268`). `pipeline.py:run_unit` has no command line caller (`extract` runs through `run_metered`), so extraction is untouched and the pass applies at rebuild only.

**Data model**: no new node or link type. One new value, `accepted_by = code_pass`, carried by a `UnitResult.released` set that the entity row reads for the entity's own id (the rest of the unit keeps `auto`). No trace display is added. A link the pass releases carries no marker, which is a known gap (Follow up).

**Interface**:
| Command | Change |
|---|---|
| `load` | `--code-pass`, per unit report (AC-17), units per model line (AC-4), `code_pass` key only when applied |
| `review-queue` | `--code-pass`, writes to a separate file (AC-8); rows read the artifact's model (AC-5) |
| `eval`, `trace --eval` | `--code-pass`, refuse a mismatch with the graph's manifest (AC-7c), score the pass routing (AC-7d) |
| `extract` | `--expect-model` (AC-29); the estimate line names the model (AC-31e) |

**Value sourcing**:
| Action | Value produced | Source |
|---|---|---|
| Code pass | the set of code decided ids | AC-9 to AC-11, from the unit text and the three runs |
| Code pass | whether the flag holds | the flags of the three runs' entities and `route_runs` (AC-12 to AC-14) |
| Code pass | `accepted_by` | the constant `code_pass`, for entities in `RoutedUnit.released` (AC-16) |
| Report | the counts of AC-17 | routing each unit twice and resolving the corpus twice, with and without the pass |
| Manifest | `code_pass` | the flag passed to `load` |
| Units list | expected model, chosen units | written by hand into `units.json` (AC-22) |
| Measure | the sample | stage one: the control arm's accepted entities and the released entities of the chosen units; stage two: the released links and the control arm's accepted links; each drawn with a recorded seed (AC-25 to AC-25g) |
| Measure | the arm key | a file written by the draw, hashed before rulings (AC-26b) |
| Estimate | rates per model | the model in the settings (AC-5c), recorded spend at the artifact's model (AC-5d), the first paid call's measured cost (AC-31c) |
| Estimate | calibration count, cached prefix | the free count of `0014:Requirements` under `claude-sonnet-5-5`, 61,110 (AC-31f); the cache write billed on `claude-sonnet-5` in experiment 0008, 57,494, until the first paid call on `claude-sonnet-5-5` reports its own (AC-31g). **Added 2026-10-12** |

**Key invariants**:
- With the flag off, the output is what it was for the same run files (AC-6, AC-6b). `code_pass` is absent from the manifest when off, like `held_view`. The default graph gains the chosen units when they land (AC-32).
- The run files under `artifacts/runs/` are never edited, and a `load --code-pass` rewrites the tracked `artifacts/graph-build.json` (a plain `load` restores it).
- Code decides no span, no type, no link. It decides only that the `multi_condition_split` flag alone does not hold an item whose three runs agree on id and type.
- Items released this way are still not known to be correct. Their accuracy is what the measure tests (AC-19, AC-19f), and the default is turned on only after stage two passes (AC-19i).

**Failure and edge cases**:
- A run without the bullet's entity, or with it under another type, or with two claimants of its id: the id is not code decided and the report counts it (AC-10, AC-17).
- An old `.env` with `ANTHROPIC_MODEL=claude-sonnet-5` would silently override the default (`config.py:74`): `extract --expect-model` stops before any call (AC-29) and scoring refuses such runs (AC-29b).
- A struck bullet, or a bullet opening with `~~` after the colon, stays with the model (AC-9, AC-17).

**Critical test scenarios**:
- Pure test, crafted runs: a plain parsed bullet, a struck bullet, a bullet in a non Requirements section, a duplicate id, a run with another type, a run with two claimants of the id, a run with another flag, a signature that differs. Verifies **AC-9** to **AC-14**.
- Pure test: an entity with no flag in run 1 and another flag in run 2 is accepted with and without the pass. Verifies **AC-13**.
- Pure test: an entity flagged `multi_condition_split` in run 1 and unflagged in runs 2 and 3 is released, and one flagged `multi_condition_split` in run 1 and another flag in run 3 is not. Verifies **AC-12**.
- Pure test: the packet of a drawn sample holds none of the fields AC-26d forbids, and the flip of AC-26e counts an unflagged bundled criterion ruled agree. Verifies **AC-26d**, **AC-26e**.
- Pure test: routing with and without the set differs only in the acceptance set, the queue rows of entities that stay held, and the endpoint reasons of links. Verifies **AC-15**, **AC-15b**, **AC-15c**.
- CLI test: a plain `review-queue` in a temporary root reproduces the committed queue, and `review-queue --code-pass` leaves it untouched. Verifies **AC-6**, **AC-8b**.
- CLI test: `trace --eval 3` exits 1 against a manifest whose `code_pass` differs, before connecting. Verifies **AC-7c**.
- Pure test: a `units.json` with a unit in AC-23's records is refused. Verifies **AC-23**.
- Pure test: a run naming another model is refused by scoring, and `extract --expect-model` exits 1. Verifies **AC-29**, **AC-29b**.

## Build plan

Approach: Tracer Bullet. The free changes first, then one real extraction measured both ways over the same runs.

1. Amend spec 0001: record the switch to `claude-sonnet-5-5`, its same price, the engineering reason (measure features 13 and 11 on the model that will be kept), that the graph mixes models until feature 9, and that `claude-sonnet-5` stays available. Satisfies **AC-1**, **AC-3**. **Written 2026-10-12.**
2. Change `DEFAULT_MODEL`; update the places that pin its name (`tests/test_extract_client.py:71`, `tests/test_extract_guards.py:835`, `AGENTS.md:10`, `.env.example:12-13`); price a call at the model's rates in `cost.py`, refusing an unknown model; make `review-queue` rows read the artifact's model; add the units per model line to `load`; add `extract --expect-model` and the model name in the estimate line. Satisfies **AC-1**, **AC-2**, **AC-4**, **AC-5** to **AC-5f**, **AC-29**, **AC-31e**. **Amended 2026-10-12**: also set `cost.py`'s calibration count to 61,110 and keep its cached prefix at 57,494; satisfies **AC-31f**, **AC-31g**.
3. Write `code_decided_ids` with its pure tests, thread it through `committed_units`, `_committed` and `route_runs`, then add `--code-pass`, the separate queue file, the manifest key, the `accepted_by` stamp, the refusal in `eval` and `trace --eval`, and the report (which resolves the corpus twice). Satisfies **AC-6** to **AC-17**.
4. Amend spec 0002: `accepted_by` may read `code_pass`, line 199 and the flag churn test (line 234) say what the pass changes. Satisfies **AC-34**. **Written 2026-10-12.**
5. Write `units.json` (0009, 0013, 0015 `## Requirements`, expected model `claude-sonnet-5-5`), check it against AC-23 and AC-24 with a test, and commit it together with the gate of AC-19 and its reason, before any paid call. Satisfies **AC-19e**, **AC-22**, **AC-23**, **AC-24**.
6. Run the free token count (AC-31). If it matches, state the per call bound and wait for the engineer's go, then run one paid call by setting the ceiling just above that bound and using `--resume` for the rest of the unit. Then give a measured estimate for the remaining calls, wait for the go again, and run `tracepath extract --expect-model claude-sonnet-5-5` with a ceiling, one unit per command, with the repository as root. Record eval chain reach before and after. Satisfies **AC-22b**, **AC-28c**, **AC-31** to **AC-32**. **Amended 2026-10-12**: after the first paid call, compare its reported cache write with the cached prefix (57,494) before giving the measured estimate (AC-31c); a difference is recorded in this spec before the estimate uses it.
7. Stage one. Build the sampler and the blind packet (opaque ids, shuffled, flags hidden, arm key hashed first), drawing 3 control entity marks and 5 released entity marks per unit. The engineer rules, then code applies the flip of AC-26e, checks no regression, scores each unit and records the result. Satisfies **AC-18c** to **AC-19e**, **AC-20**, **AC-25** to **AC-25d**, **AC-25f** to **AC-30**, and **AC-18**, **AC-18b**, **AC-21** by what it leaves out (they define the full bar owed on feature 13's final state). **Amended 2026-10-12**: it drew the full bar's sample from both arms. **Done 2026-10-14**: stage one inconclusive, `0013` short of released entities; result in experiment 0012.
8. Stage two, only if stage one passed and the engineer says they want the pass on by default: draw up to 5 released link marks and 2 control link marks per unit into a blind packet (opaque ids, shuffled, arm key hashed first), the engineer rules them, and code scores and records them. Satisfies **AC-19f** to **AC-19h**, **AC-25e**, **AC-25g**, and **AC-26** to **AC-26d** for that packet. **Added 2026-10-12.**
9. Only after stage two passes, and if the engineer says so, flip the default of the pass in its own commit. Not before. Satisfies **AC-19i**, and **AC-33**, **AC-33b** by what it leaves out.

## Consequences

**Positive**:
- Accuracy of what the pass releases is measured by the engineer's own rulings, not by agreement between runs, and the step is judged on what it changed.
- The pass narrows one hold on a rule the engineer's card already makes (a bundled criterion kept whole and flagged is ruled agree), so no ruling rule is amended.
- One paid extraction serves both arms, because the pass works on the committed run files, so no separate roots or arm machinery are needed.
- The pass never adds a hold, so the worst case is that an item is released that should not have been, which the measure is built to find.

**Negative / tradeoffs**:
- A run on `claude-sonnet-5` now stops at the calibration check, since that model counts 61,108 and the figure is 61,110 (AC-31f). It stops before any call, so nothing is spent; pricing that model again needs its own calibration figure first.
- The pass releases items on code's authority, though the runs agreeing shows repeatability and not correctness. Feature 11 starts from a hold narrowed here, and each report counts what was released.
- The graph mixes models until feature 9, so a chain can cross units made by two models. `load` says so (AC-4).
- The three chosen units join the default graph when they land, so eval reach may move once (AC-32, AC-28c).
- The flag change and the type definitions are not designed here. Feature 13 stays open until they are, and its final state must meet the full bar, which this spec does not measure.
- A pass here does not show the rest of the bar is met: the other accepted entities, the relationship marks and the dropped links are not measured in this step. The full bar is measured once, on feature 13's final state.
- The gate rests on 5 released entity marks per unit: one mark not ruled agree in five still passes (4 of 5), two fail, and an `unsure` counts as one of them. A unit near the line can go either way on one ruling.
- Stage two is strict where few links are released: a unit with 1 or 2 drawn needs every one ruled agree, so one doubtful link can keep the default off.
- The 3 control entity marks and 2 control link marks per unit say little about the control arm. They are there so the released marks are ruled blind, and their score is reported, not gated.
- Ruling is light: 8 entity marks per unit in stage one (about 24 over the three units), plus up to 7 link marks per unit in stage two when it runs (up to 5 released and 2 control), against about 135 marks before the cut.

**Neutral**:
- A second tracked queue file exists (AC-8) until the default flips.
- Spec 0002's vocabulary Follow up (`8bcd9df`) stays open.

## Follow-up

- [ ] Feature 13 continues after this spec. Its remaining steps, the `multi_condition_split` flag change and the type definitions and splitting rules, are designed in a later spec or amendment, once this step's rulings exist, each with its own fresh units chosen and committed beforehand. The definitions are written from the rulings and cite the ruled items. Feature 13's Done when still requires its final state to meet the bar.
- [ ] Design inputs for those later steps, from this spec's cross checks (read only, cited lines read by the author): a control arm of an earlier prompt state needs its own root, because `run-N.json` would collide (`artifacts.py:227-235`); an arm root resolved alone computes a different cross unit hold than the main graph (`pipeline.py:269-270`); a load of an arm clears the one Neo4j graph (`cli.py:249`); `--snapshot` is joined to `--root` (`cli.py:624`); the control must be extracted before the prompt change is committed (`examples.py:17`); `prompt_version` is the only record of an arm's state.
- [ ] Known gap: a link the pass releases carries no marker (`link_row` has no `accepted_by`, `model.py:128-140`), so a chain can grow through unmarked links. AC-17 counts them per unit.
- [ ] Verify before the paid run: Anthropic's Sonnet 5.5 migration guide on effort levels being recalibrated, and that the structured output request the client sends is accepted at `medium`. The model pages confirm the price ($2 and $10 per million tokens), the cache read rate ($0.10), the 512 token cache minimum and the retirement date; they do not state the effort recalibration. Not verified.
- [x] Verify that the tokenizer is unchanged from `claude-sonnet-5` to `claude-sonnet-5-5`, which `cost.py`'s calibration count (61,108 tokens) assumes. The free token count (AC-31) shows it before any paid call. **Checked 2026-10-12**: four units counted under both models each differ by exactly 2 tokens, so the text is tokenized the same and the request carries a fixed overhead on the new model (rationale, Evidence). The calibration count moved (AC-31f).
- [ ] Compare the first paid call's reported cache write on `claude-sonnet-5-5` with the cached prefix (57,494). The 2 token overhead may sit in the cached part or the uncached part, and no free count can tell which. At $4 per million tokens for a cache write the difference is at most $0.000008 per call, so it cannot move a bound or an estimate, but the figure is a measurement and is corrected if it differs (AC-31g).
- [ ] Eval runs made for AC-28c are report only, not a rerun for feature 11's policy. The routing policy is committed before any question is rerun for that purpose.
- [x] A separate `/debug`: `struck: false` on `0002/AC-10`. **Fixed** in PR #26 (`c0b1e9b`, fix commit `5e3703c`), which this branch includes.
- [ ] The `HeldLink` docstring in `src/tracepath/pipeline.py:72` says a review step releases a held link, and none exists (carried from `docs/session-notes.md`).
- [ ] Reconcile the two spend figures in `docs/session-notes.md` against the Console before the estimate is trusted as a running total.
- [ ] Span surgery (code deciding spans, rejected spans or struck bullets) returns only if the engineer's rulings show spans are wrong. Spec 0002 AC-5 gives the unstruck text of a split id the verbatim id, which any struck bullet rule must respect.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).
