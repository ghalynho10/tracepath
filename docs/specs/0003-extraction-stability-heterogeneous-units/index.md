# 0003. Extraction stability on heterogeneous units

**Date**: 2026-09-24
**Status**: Proposed

## Summary

This spec settles feature 12's two open questions before any paid extraction run. First, why the labelled reference round trip in experiment 0004 actually failed: not a missing worked example, but a real gap in AC-7 (spec 0002), since binding rule 6 has no verbatim label anywhere in its own text. The fix is a small piece of deterministic code, not a prompt change, and it amends spec 0002. Second, how the prompt gets its first worked examples at all, since none exist today, what actually reaches the model from each example file, and how the before and after experiment that tests whether examples fix run to run disagreement is measured honestly, including a real, independently verified failure mode this spec found along the way: the model already invents entity labels today, anchored on a bad sample string in the schema itself.

## Requirements

**User stories**:
- As the project's own author and sole user, I want a reference like "spec 0001's binding rule 6" to resolve to the entity it names, so a traced chain does not lose a link it should have kept.
- As the person who will run and read the before and after experiment, I want the disagreement rate measured on units the prompt's own examples never saw, so a falling rate means the fix generalises rather than that the model memorised a demonstration.
- As the person who will read the after run's numbers, I want to know whether a falling disagreement rate means the model converged on a right answer or a wrong one, not just that it converged.

**Acceptance criteria** (the contract, each criterion is independently checkable):

**The label pre check (closes the round trip defect)**

- **AC-1**: A deterministic pre check, run where AC-5 and AC-6 (spec 0002) already run, inserted after `locate_output` and before `route_runs`, scoped to a `## Binding rules` heading whose items are bold `**N.**` list entries: it finds each such item's span by the regex `^\*\*(\d+)\.` (reusing the existing fenced block masking), and, once entities are located, finds the one entity, if any, whose located offset falls inside rule `N`'s own leading span (from its `**N.**` marker to the next `**M.**` marker or the section end), and sets that entity's `label` to `binding rule N`. It runs in code, never asks the model, the same "taken from the text by code" pattern AC-5 and AC-6 use for struck ranges and checkboxes. It is computed fresh wherever a run or a rebuild needs it (both `pipeline.py` and `rebuild.py` call the same function); it is never written into the stored run artifacts, which stay exactly what the model returned.
- **AC-2**: When more than one entity's offset falls inside the same rule's leading span, no label is set for that rule; an ambiguous case is left unlabelled, not guessed. Entities located outside every rule's leading span (elsewhere in the unit) are never labelled by this pre check.
- **AC-3**: When no entity is located inside a rule's leading span, no label is set. The existing AC-11e comparison signature (spec 0002) still catches any resulting cross run disagreement; this pre check adds no new routing reason.
- **AC-4**: Inside a `## Binding rules` unit, the pre check's label is final: any model produced `label` on the entity it targets is overwritten. Every other entity in the same unit has its model produced `label` cleared too, unless that label string appears verbatim inside that entity's own span, since a `## Binding rules` unit is a uniform list of Constraints with no author named sub items, and a stray label surviving there is, on the evidence in `## Follow up`, invented rather than found.
- **AC-5**: The pre check applies only to `## Binding rules` sections with bold numbered items. Other ordinal patterns in the corpus (`step N`, `invariant N`, `revision N`) are explicitly out of scope for this spec; see Follow up.

**The prompt content (closes the "no examples at all" gap, and a bad schema sample)**

- **AC-6**: `SYSTEM_PROMPT` gains a general, model wide rule on entity labelling, not scoped to one example: a `label` is set only when the unit's own text gives that item a name standing in place of a number (a bold lead in, a quoted or otherwise clearly delimited name used as the item's own heading), copied verbatim. An unnamed, unnumbered item (a plain bullet, a `Key invariants` entry) gets no label, regardless of any sample text shown elsewhere in this prompt, including its own field descriptions. This closes the entity side of AC-7's `label` amendment (spec 0002, 2026-09-23), which stated the rule for the reference side and assumed, wrongly, that an equivalent entity side instruction already existed.
- **AC-7**: `schema.py`'s `ExtractedEntity.label` field description sample (`schema.py:149`) replaces `key invariant 1`, which appears nowhere in the corpus, with a real, corpus grounded example already proven correct by a worked example (`Happy path`, `0006`). `ReferenceEndpoint.label`'s own sample (`schema.py:120`, `binding rule 6`) is a real mention the corpus actually writes (0008's preamble) and is kept as is. This is a prompt content change, not only a documentation fix; it lands under the same `PROMPT_VERSION` bump as AC-6, AC-8 and AC-9.
- **AC-8**: `SYSTEM_PROMPT` gains a general rule that a reference or lookup table's row is not itself a claim (keyed by its first cell, answering no type question on its own); a whole unit run returns no entity and no relationship from such a row.
- **AC-9**: `SYSTEM_PROMPT` gains a few shot block built from `examples/*.md`, one block per file in a fixed, deterministic order (filename sorted), each holding only that file's Input and Output sections plus a prompt facing Rules list assembled once (not duplicated between `SYSTEM_PROMPT` and the example file) from: each file's own "Rules this example demonstrates" section, generalised and stripped of project history references (task numbers, spec numbers, dates); three further rules that today live only in Reasoning notes and so never reach the model at all, lifted and generalised the same way: type an item by what it claims, not by where it sits (`feature-21-scope-row.md`); a pointer to something that is not one of the three Record kinds, such as a cited review file, produces no link at all (`0008-preamble.md`); a "Resolved..." follow up is linked unclassified, carrying the verbatim "Resolved" phrase and its date (`0012-follow-up.md`); the excerpt statement from `0006`'s "What this example covers" section ("this input is a contiguous verbatim excerpt; everything inside it is extracted, nothing is skipped"), attached next to that one example's Input so the model does not learn to extract only part of a `## Feature design` section; and AC-6 and AC-8 above, generalised the same way, not example specific. Reasoning notes, and any per file editorial commentary, are never sent to the model. `PROMPT_VERSION` bumps to `0003.0`, covering AC-6 through AC-9 as one change.
- **AC-10**: `examples/0008-preamble.md`'s Validation caveat is removed; the condition it described (build plan task 17 unbuilt) no longer holds.
- **AC-11**: A test validates every worked example's Input and Output JSON against `extraction_json_schema()`, so a stale example cannot teach an invalid shape silently.

**Proof with no paid call**

- **AC-12**: The label pre check is proven by rebuilding from the committed `0002.3` artifacts for spec 0001's `## Binding rules` section, no API call: the resulting label index resolves `("0001", "binding rule 6")` to exactly one entity, the same one in all three committed runs.

**The held out experiment (closes the disagreement rate question, honestly)**

- **AC-13**: A fresh `0002.3` baseline for `0021 ## Requirements` (3 calls) is the single before measurement for that unit, used both to replace the mixed prompt version comparison and as held out group A's before; it is not run twice. Superseded `0002.2` runs for that unit, if any are committed, move to `artifacts/superseded/`, per `experiments/README.md`, never deleted.
- **AC-14**: The before and after disagreement rate experiment runs on held out units only, none of which appear in the six worked examples: `0021 ## Requirements` (group A, no example exists of that kind), `0013 ## Feature design` (group B, a kind with an example, `0006`, but different content), and the `Profile entry` scope row (group C, a different row than `feature-21`, the one already used as an example). Each group is reported separately, with raw counts (one unit per group, not a rate), never combined into one number.
- **AC-15**: Each group's report carries an entity column (count spread, entity rows under `runs_disagree`) and a relationship column (relationship rows under `runs_disagree`, held separately from relationship rows under `endpoint_not_accepted`), since relationships are 308 of the review queue's 464 committed rows, roughly two thirds.
- **AC-16**: For each after run, a fixed sample of about 10 items is ruled on by the engineer against HANDOFF's three question test (atomicity, referenceability, right sizing) and the deletion trick. Both the run to run disagreement rate and the engineer's agreement rate with the model are reported side by side for that sample; a falling disagreement rate with a falling engineer agreement rate is reported as a warning, not a success, since it means the examples taught convergence on a wrong reading. This is mandatory for every after run this feature makes, not optional.
- **AC-17**: Group B's (`0013 ## Feature design`) after run entity count spread is compared to 2, the widest spread any stable committed unit showed (`0021 ## Requirements`, `19 / 21 / 21`; unstable committed units spread `11` to `24`). A spread of 2 or less means the prompt fix already closed the gap on this heterogeneous unit, and this is recorded in the experiment's README with the actual numbers; the AC-2 unit definition question (spec 0002: should a bold sub label start a new unit) is not tested, and the scope's Done when for feature 12 states this explicitly rather than leaving it silently untested. A spread greater than 2 triggers a measured cost estimate (splitting one `## Feature design` unit at its bold sub labels can run up to 39 calls) presented for a fresh go ahead before any further run. Group B's relationship rows under `runs_disagree`, before and after, are reported regardless as a new baseline measurement; no trigger threshold exists yet for that column.
- **AC-18**: The type coverage set (24 calls across the 8 committed units, spec 0002 AC-14) is run again under `PROMPT_VERSION 0003.0`, confirming `Consequence`, `FollowUp`, `BuildStep` and `TestScenario` still come back stably. It deliberately reuses units the worked examples demonstrate (it is a stability check on already covered ground, not a generalisation check, unlike AC-14 through AC-17 above). Recorded as a new experiment with a forward pointer added to experiment 0001, never by editing experiment 0001's own numbers.

**Caching and spend**

- **AC-19**: Every `0003.0` call (the label round trip's proof needs none; the fresh `0002.3` baseline predates the examples block and cannot use it) uses standard prompt caching with a 1 hour breakpoint on the system prompt, since a single call's output can exceed the 5 minute default cache lifetime (experiment 0004 averaged about 15,700 output tokens per call, and cache lifetime is measured from the start of the request that reads or writes it, not from the end of its response). The second call of each session confirms `cache_read_input_tokens` is above zero before the remaining calls in that session are trusted to be cheap.
- **AC-20**: No paid call runs until the exact configuration count (42 calls: 3 fresh baseline / group A before, 3 group A after, 3 + 3 group B, 3 + 3 group C, 24 type coverage; plus the conditional AC-17 run if triggered) and its cost, computed from the formula and the measured token count of the assembled few shot block (not estimated), is presented and confirmed. See `verify.md`, Spends money.

## Decision

**Chosen option**: fix the label gap in code, scoped to `## Binding rules`, with the pre check clearing stray model produced labels in that unit rather than merely overriding the one it targets (Option 1 in rationale.md); keep model set entity labelling enabled elsewhere, guarded by a real instruction, a fixed schema sample, and the worked examples, measured under the held out after run rather than disabled outright (Option 1 in the label reliability question); wire the six worked examples into the prompt at Input, Output and a once assembled Rules list; and measure the disagreement rate experiment on held out units, reported by kind, with a stated, evidence based trigger for whether the AC-2 heterogeneity question needs testing at all.

Full reasoning and the options weighed: see [rationale.md](rationale.md).

## Rationale

Reasoning, the options weighed, and the evidence tables, including the verified model labelling failure modes this spec found while drafting it: see [rationale.md](rationale.md).

## Feature design

**Mechanism: the label pre check**

1. For a `## Binding rules` unit, find each bold numbered list item's span (`^\*\*(\d+)\.` to the next such marker or the section end).
2. After entities are located (existing citation logic), find the one entity, if any, whose offset falls inside rule `N`'s span.
3. Set that entity's `label` to `binding rule N`, overwriting any model produced value on it.
4. Clear every other entity's model produced `label` in the same unit, unless that label string is verbatim inside that entity's own span.
5. Two or more entities inside one rule's span, or none, leaves that rule's label unset.

**Data model touched**: no schema change. `ExtractedEntity.label` (spec 0002) already exists; this is a new deterministic writer of that field for one unit shape, plus a field description text fix (AC-7). The pre check is pure and computed fresh at read time (`model_copy` on the frozen extraction models), never persisted into stored artifacts.

**Prompt content assembly**:

| Source | Goes into `SYSTEM_PROMPT` | Reason |
|---|---|---|
| Each example's Input and Output | Yes, filename order | The demonstrated shape is what a few shot example is for. |
| A generalised, once assembled Rules list (AC-9) | Yes | Rules the model needs are meaningless to it sitting only in a human facing file, or duplicated where the two copies can drift. |
| `0006`'s excerpt statement | Yes, attached to that one Input | Without it the model can learn to extract only part of a `## Feature design` section. |
| Each example's Reasoning notes and per file commentary | No | Authoring commentary and project history, not extraction guidance. |
| `0008-preamble.md`'s Validation caveat | No, and deleted from the file (AC-10) | Describes a now shipped, no longer true condition. |

**Value sourcing**:

| Action | Value produced | Source |
|---|---|---|
| Extract a `## Binding rules` unit | The entity `label` for the rule's headline claim | The pre check, from the unit's own heading and numbered list structure, never the model |
| Extract any unit | Whether an item gets a label at all | AC-6's general rule: only when the unit's own text names the item directly, verbatim |
| Resolve a `{record, label}` reference | The canonical id it resolves to | The label index built over accepted entities (AC-7, spec 0002), unchanged by this spec |
| Assemble the few shot block | The cached prefix's exact token count | Measured with the token counting endpoint before the first paid call (AC-20), never estimated |
| Report a held out group | Entity and relationship agreement counts | `artifacts/review-queue.json`, filtered to that unit's rows after the after run |
| Decide whether AC-2 needs testing | Group B's after run entity spread vs. 2 | `compare_runs()`'s existing count, no new code |
| Rule on the fixed sample (AC-16) | The engineer's own judgement, not derived | HANDOFF's three question test and the deletion trick, applied by the engineer, recorded in the experiment README |

**Key invariants**:
- A model produced `label` on a `## Binding rules` entity never survives past the pre check unless it is the entity the pre check itself targets.
- The pre check names only `## Binding rules`. No other heading shape triggers it until a future spec extends it on real evidence (AC-5, Follow up).
- The examples block, once assembled, is byte identical across every call in a run, so the cache prefix actually hits.
- A disagreement rate is never read alone as success; it is read next to the engineer agreement rate on the same fixed sample (AC-16).

**Security model**: not applicable, single user local tool, no new surface exposed.

**Configuration required**: none. No new environment variable; `PROMPT_VERSION`, the assembled Rules list, and the cache breakpoint are code constants in `client.py`.

**Critical test scenarios** (each maps to an acceptance criterion above):
- Rebuild from committed `0002.3` artifacts for spec 0001's `## Binding rules` section and confirm the label index resolves `("0001", "binding rule 6")` to one entity, no API call, verifies **AC-1**, **AC-12**.
- A rule with two entities inside its span, or none, sets no label for that rule, verifies **AC-2**, **AC-3**.
- A model produced `key invariant N` style label on a `## Binding rules` entity that is not the pre check's target is cleared, replayed against the committed `0006` run artifacts as a regression fixture even though `0006` is not itself a `## Binding rules` unit, adapted to a `## Binding rules` fixture built for this test, verifies **AC-4**.
- Every committed and newly authored example's Input and Output validates against `extraction_json_schema()`, verifies **AC-11**.
- The second call of the first paid `0003.0` run shows `cache_read_input_tokens` greater than zero, verifies **AC-19**.
- Group B's after run entity spread is computed and compared to 2, with the resulting decision (test AC-2, or record why not) written to the experiment README either way, verifies **AC-17**.

## Build plan

Ordered as one thin thread (Tracer Bullet, the project default): prove the free, code only fix first, then wire the prompt content, then run the fresh baseline that must predate the prompt change, then spend on the experiments that need it.

1. Add the `## Binding rules` label pre check to the extraction pipeline (where AC-5/AC-6, spec 0002, already run), including the stray label clearing rule, satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-5**.
2. Add a unit test rebuilding from the committed `0002.3` artifacts proving the label index resolves `("0001", "binding rule 6")` to one entity, no API call, satisfies **AC-12**.
3. Add a regression fixture, adapted from the committed `0006` run showing an invented `key invariant N` style label, confirming the clearing rule removes it, satisfies **AC-4**.
4. Amend spec 0002's AC-7 to record the label source rule (done as part of this spec, see the edit to `docs/specs/0002-data-model/index.md`).
5. **Run the fresh `0021 ## Requirements` `0002.3` baseline (3 calls) now, before the prompt changes below, since it is a measurement of the current prompt, not the new one; move any superseded `0002.2` runs**, satisfies **AC-13**.
6. Replace `schema.py:149`'s `ExtractedEntity.label` sample, `key invariant 1`, with `Happy path` (or another real, corpus grounded, already proven label); leave `ReferenceEndpoint.label`'s sample (`schema.py:120`, `binding rule 6`, a real mention) unchanged, satisfies **AC-7**.
7. Remove the stale Validation caveat from `examples/0008-preamble.md`, satisfies **AC-10**.
8. Write the two new general rules (entity labelling, reference tables yield nothing); lift and generalise the per example "Rules this example demonstrates" sections, the three rules that today live only in Reasoning notes (typing by claim not position; a non Record kind citation yields no link; a "Resolved..." follow up links unclassified with phrase and date), and the `0006` excerpt statement into one assembled, prompt facing Rules list, stripped of project history references, satisfies **AC-6**, **AC-8**, **AC-9**.
9. Build the few shot block assembler (Input, Output, the one assembled Rules list, filename order) and wire it into `SYSTEM_PROMPT`; bump `PROMPT_VERSION` to `0003.0`, satisfies **AC-9**.
10. Add the example JSON validation test, satisfies **AC-11**.
11. Wire the 1 hour prompt cache breakpoint on the system prompt block in `client.py`, scoped to `0003.0` calls, satisfies **AC-19**.
12. Measure the assembled few shot block's exact token count with the token counting endpoint (no cost), compute the full run manifest's cost from the formula in `verify.md`, and get the go ahead before any paid call, satisfies **AC-20**.
13. Run the held out before and after set: `0021 ## Requirements` after, `0013 ## Feature design` before and after, and the `Profile entry` scope row before and after; report entity and relationship columns per group, satisfies **AC-14**, **AC-15**.
14. Add a free check, run over the held out after runs just paid for (no new cost): count every model set entity `label`, split into those that appear verbatim inside their own entity's span and those that do not, so AC-6's effect on the invention pattern found in the committed `0006` runs (`key invariant 1` through `key invariant 6`) is measured directly rather than assumed fixed.
15. Rule on each after run's fixed ~10 item sample against HANDOFF's three question test and the deletion trick; report the engineer agreement rate beside the disagreement rate, satisfies **AC-16**.
16. Compute group B's after run entity spread against the threshold of 2; either record why AC-2 was not tested (spread ≤ 2) or bring a fresh, measured cost estimate for splitting the unit before running that test (spread > 2); report group B's relationship rows under `runs_disagree` as a new baseline either way, satisfies **AC-17**.
17. Re run the type coverage set (24 calls) under `PROMPT_VERSION 0003.0`; record as a new experiment with a forward pointer from experiment 0001, satisfies **AC-18**.
18. Rebuild the full graph and review queue from all committed artifacts under the new label rule and the new prompt version; confirm the queue's composition figures are re measured, not carried over from before this spec.

## Consequences

**Positive**:
- The labelled reference defect closes with no ongoing model dependency, a deterministic rule that cannot regress on rerun.
- A real, previously unknown failure mode (the model inventing labels anchored on the schema's own bad sample text) was found and verified against committed artifacts while drafting this spec, and this spec fixes its cause, not only its symptom on one unit.
- The disagreement rate experiment can no longer be accused of measuring memorisation, since it never touches a unit the model has seen demonstrated, and a falling rate is checked against an engineer ruling before it is trusted as improvement.

**Negative / tradeoffs**:
- The `## Binding rules` pre check is narrow by design; `step N`, `invariant N` and `revision N` references stay unresolved until a later spec extends it, so some real references will still fall to `:Unresolved` after this ships.
- Adding the examples block adds a fixed token cost to every extraction call from here on; caching keeps this small in dollars but the prompt is now materially larger and slower to iterate on by hand.
- The held out before and after set uses only one unit per group; a single unit's result is suggestive, not a statistically strong sample, and the spec says so rather than overstating it.
- One anomaly this spec found (a garbled label string, `COPY-1atch check flag placeholder`, in a committed `0006` run) is not explained or fixed here; it is flagged in Follow up as a possible structured output edge case unrelated to prompt content.

**Neutral**:
- `PROMPT_VERSION` moves to `0003.0`, a new numbering root tied to this spec rather than a further `0002.x` increment, since spec 0002 no longer owns the prompt's content, this spec does.
- The graph and review queue are disposable and rebuilt from committed artifacts (AGENTS.md); this spec's changes mean a full rebuild is expected, not a migration.

## Follow up

- [ ] Extend the label pre check to other ordinal reference patterns (`step N`, about 83 occurrences in the corpus; `invariant N`, about 67; `revision N`, about 63) once evidence shows each pattern's references and structure line up the way `binding rule N` does. Not built here (AC-5).
- [ ] Investigate the garbled label `COPY-1atch check flag placeholder`, found in a committed `0006 ## Feature design` run while drafting this spec (`artifacts/runs/0006/feature-design/run-2.json`). Looks like two label strings concatenated; may be a structured output edge case unrelated to prompt content. Watch the held out after run's label agreement numbers for a recurrence before deciding whether it needs its own fix.
- [ ] If the held out after runs' engineer agreement rate (AC-16) comes back poor even after the fixes here, consider a variant that also includes Reasoning notes in the few shot block, held out the same way, measuring the engineer's ruling on the same fixed sample rather than the disagreement rate. Estimated at 6 calls, about $1 to $1.50, plus about 10 more engineer rulings. Not run as part of this spec.
- [ ] Feature 11 (review volume and routing policy) reads this spec's before and after result before setting a routing policy, per the scope's own ordering.
- [ ] For feature 9 (whole corpus, the 564 call run where the Batch API is actually meant to pay off): the fetched pricing docs confirm the Batch API discount stacks with prompt caching multipliers, but not the resulting combined rate for a cached read or write inside a batch request. Verify the exact combined number before budgeting feature 9's run, rather than assuming a simple 50% off the already discounted cache rate.
