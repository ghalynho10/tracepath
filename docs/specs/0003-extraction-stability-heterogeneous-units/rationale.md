# 0003. Rationale

## Context

Feature 12 opened with one question: is the run to run disagreement seen on some extracted units (340 of 403 queue rows, before the AC-11e label signature change; 464 rows across 9 units after it) a property of the corpus, or an artifact of a prompt that has zero worked examples for any of its seven unit kinds. A second, narrower question rode alongside it: experiment 0004 measured a real run of spec 0001's `## Binding rules` section and 0008's Preamble, and found the labelled reference never round trips, since the entity side never writes a `label` at all.

Reading `SYSTEM_PROMPT` (`client.py`), the worked examples in `examples/`, and the committed run artifacts before writing this spec changed the shape of both questions. The prompt's own rule ("labels are copied, never invented") is not a bug in the abstract; the entity the reference names, binding rule 6, is written in its source spec as `**6. Authorisation is never decided in the proxy.**`, with no occurrence of the string "binding rule 6" anywhere in that spec's own text. The model correctly found nothing to copy. Meanwhile "binding rule 6" and its siblings appear about 159 times across the corpus as an external naming convention, one only a reader who already knows the numbering can use. AC-7 (spec 0002) already anticipated the general shape (`record` plus `label`, matching a "named but unnumbered item") but its own field description samples an item, `key invariant 1`, that occurs nowhere in the corpus, and its own table already states that "matching by implication rather than by an explicit label is name resolution's job (feature 7), not this field's." Nothing in AC-7 says where a `label` value comes from when the item's own text never states it. That is the actual gap, and it sits in spec 0002, not in the prompt's example coverage.

Checking the committed `0006 ## Feature design` run artifacts against this same question surfaced something worse than a documentation nit. In 2 of 3 committed runs, the model labelled Constraint entities `key invariant 1` through `key invariant 6`, a string that occurs nowhere in the corpus as a self label; the corresponding worked example (`examples/0006-feature-design.md`) already names this exact failure mode in its own Reasoning notes ("Spec 0002's schema names `key invariant 1` as a sample label, but *this* spec's invariants are unnumbered, unnamed bullets"), but that note has never reached the model, since nothing is wired into `SYSTEM_PROMPT` yet. The same run data shows the same TestScenario item labelled `Tell #4` in one run and `Eyebrow placement (Tell #4)` in another, inconsistent even where the item genuinely is named. No committed run labelled any TestScenario correctly at all, the one case the worked example shows working. And one run (`run-2.json`) carries a garbled label, `COPY-1atch check flag placeholder`, an anomaly this spec does not explain (see Follow up). Put together, "labels are copied, never invented" describes what the worked example teaches, not what the model does today with no example and a bad schema sample to anchor on.

The disagreement rate question is real and separate from the label question, but the two interact: `PROMPT_VERSION 0002.2` and `0002.3` both carry zero worked examples for any of the seven unit kinds, against a rule vocabulary (`Feature`, `Constraint`, `AcceptanceCriterion`, `Consequence`, `FollowUp`, `BuildStep`, `TestScenario`, `unclassified`) the model is asked to apply with no demonstration, and AC-11e now puts `label` itself into the comparison signature, so a model that invents an unstable label on every run adds directly to the disagreement count. The committed data splits sharply: `0012 ## Requirements` returns 14 / 14 / 14, `0012 ## Follow-up` 9 / 9 / 9, while `0006 ## Feature design` returns 36 / 46 / 35 and the `feature-21` scope row 15 / 38 / 14. Size does not predict this; mixture does, every unstable unit holds several kinds of claim at once. Six worked examples already exist, drafted for this feature, but never wired into `SYSTEM_PROMPT`. Whatever experiment tests whether they help must not run on the same units they demonstrate, or a falling disagreement rate would show memorisation of the demonstration, not a generalising fix, and must not stop at the disagreement rate alone, since a model that converges on a confidently wrong reading looks identical to one that converged correctly if nothing else is measured.

## Options considered

### Where an entity's label comes from (the round trip defect)

#### Option 1: A deterministic pre check derives it from document structure

Code reads a `## Binding rules` heading's bold numbered items and sets `label: "binding rule N"` on the one entity whose located offset falls inside that item's own span, the same pattern already used for struck ranges (AC-5) and checkbox state (AC-6): taken from the text by code, never asked of the model.

**Pros**:
- No paid model call needed to prove the mechanism; a rebuild from committed artifacts is enough.
- No new dependency on feature 7 (name resolution), which is unbuilt.
- The model's own rule ("labels are copied, never invented") stays true for the model; code, not the model, is doing something different, and it does so from the document's own visible structure, not by guessing what the author meant.

**Cons**:
- Narrow by construction: only fixes `## Binding rules`, not `step N`, `invariant N` or `revision N`, each a real, separately occurring pattern in the corpus.
- A second, non trivial decision rides inside it: which entity, of possibly several inside one rule's span, gets the label, what exactly bounds that span, and what happens to a stray model produced label on a different entity in the same unit. All three answered by measurement, not assumption: the span must end at the rule's first blank line, not at the next `**M.**` marker (see the span evidence below), and a stray label is more likely invented than found (see the `0006` findings above).

#### Option 2: The model constructs the label from the heading and the number

Change the prompt, the schema description and the example rules to instruct the model to build `"binding rule N"` itself from context, relying on AC-11e's comparison signature to catch cross run disagreement on the construction.

**Pros**:
- Generalises to any heading shape without new code, in principle.

**Cons**:
- Asks the model to construct rather than copy, which directly contradicts the rule the existing example already teaches, and the evidence now shows the model needs less encouragement toward inventing labels, not more.
- Reopens exactly the stability question this feature exists to close, now for the label field specifically, with no code level guarantee the construction is even correct, only that three runs agree, and agreement is exactly what AC-16 warns is not the same as correctness.

#### Option 3: Labels stay verbatim only; ordinal references defer to feature 7 (name resolution)

Treat this as out of scope for extraction entirely. AC-7's own text already says matching by implication is feature 7's job.

**Pros**:
- Architecturally the cleanest long run placement; feature 7 exists precisely to match records named several ways.
- No change to AC-7 or the extraction pipeline at all.

**Cons**:
- Feature 7 is Slice 3, unbuilt, and has no scope row decision yet. Choosing this option means feature 12's own round trip criterion (spec 0002, the Labeled reference match found scenario) cannot close until a separate, unscoped feature ships, which the project's own scope does not currently record as a dependency.
- Defers a fix the corpus already shows is needed 159 times over, for no cost saving, since Option 1 is free to prove.

**Chosen: Option 1.** See Rationale below.

### Whether model set entity labelling should stay enabled at all

Found mid design, once the `0006` run artifacts were checked: the model does not only fail to label binding rule 6, it actively invents labels elsewhere, anchored on the schema's own bad sample text, and is inconsistent even on a genuinely named item.

#### Option 1: Keep it enabled, fix what is actually broken, measure the result

Replace the bad schema sample (AC-7), add an explicit, general entity labelling rule the prompt currently lacks (AC-6), and let the already drafted `0006` worked example, once wired in, demonstrate the correct behaviour it was written to demonstrate. Measure the held out after run's label agreement as part of AC-16.

**Pros**:
- The worked example already shows this working correctly (`Happy path`, `Font licence`, both genuinely verbatim in the corpus); the failure mode traced is specifically "no instruction, anchored on a bad sample", not "the model cannot do this task".
- AC-11e already routes a label disagreement to review rather than writing an unstable value to the graph, so the downside of leaving it enabled while unproven is bounded.
- Disabling it would also remove a capability spec 0002's AC-7 and its `:Entity` table were built around, a larger change than this spec's scope.

**Cons**:
- Not proven yet; the after run could still show the same invention pattern, in which case this spec's fix would need revisiting.
- The garbled label anomaly (`COPY-1atch check flag placeholder`) is not explained by this diagnosis and is not fixed by it either.

#### Option 2: Entity labels set by code only, disable the model's own labelling

**Pros**:
- Removes the failure mode outright, with certainty, rather than a bet on measurement.

**Cons**:
- A larger change: every unit kind with a genuinely author named item (TestScenario's `Happy path`, `Font licence`) loses a real capability, not only the broken cases.
- No code exists that could derive those labels the way the `## Binding rules` pre check does; they have no structural marker to read, only the author's own prose, which is exactly what only the model can recognise.

**Chosen: Option 1**, with Option 2 as the fallback if AC-16's held out measurement shows the invention pattern surviving the fix.

### What goes into the prompt from each worked example

#### Option 1: Input, Output and one assembled Rules list, plus the excerpt statement

**Pros**: the model needs the demonstrated shape and the rules it is meant to follow, not authoring commentary; keeps the fixed prefix smaller (measured, not estimated, before the first paid call, AC-20); a stale note (the Validation caveat) cannot mislead a run it is never sent to; assembling the Rules list once, rather than duplicating it in `SYSTEM_PROMPT` and each example file, removes a place the two copies could drift apart.

**Cons**: several rules already written down (in Reasoning notes and the `## What this example covers` sections) need a deliberate lift and generalisation first, or the model never sees them either; the excerpt statement needs to travel with its one example specifically, not the general rule set.

#### Option 2: Whole files, Reasoning notes included

**Pros**: nothing is lost; a rule stated only in prose still has a chance of being inferred by the model from the worked case.

**Cons**: roughly 35% more fixed tokens on every call, for prose that narrates this project's own build history ("until build plan task 17 lands"), which risks reading as task relevant when it is not.

**Chosen: Option 1**, after first lifting and generalising the rules that would otherwise be lost.

### Amended 2026-09-28: what to do with a bundled criterion that carries a verbatim `AC-N` id

The trigger: the engineer ruled `0021` AC-12 and AC-17 "should split" (`ruling-sheet.md`, lines 58 to 59 and 74 to 75). The prompt's id rule (`client.py`, the "Ids and spans" bullet at line 58) tells the model to use the verbatim `AC-N` token as the id. Three facts weigh against splitting. Verified by reading: `_verbatim_keepers` in `src/tracepath/extract/ids.py` (lines 198 to 213) gives a verbatim id to one entity only, the unstruck one earliest in the unit, and every other entity with that id falls through to a derived id. So a split criterion has one part called `0021/AC-17` and the rest called `0021#requirements:N`, and a reference that names `AC-17` resolves to the first part. Verified from the ruling sheet and corpus: the references that name these two criteria name them whole (`0021`'s own files mention AC-17 about 41 times and AC-12 about 19 times, counted by regular expression; the engineer's own count for AC-17 is about 40 lines). Verified from spec 0002's rationale (lines 93 and 94): `satisfies` and `verifies` lines make about 654 criterion references across 20 specs, each naming a criterion by its id.

Size does not identify a bundled criterion. My count of the corpus's criterion definitions (325 with a looser matcher than the 316 the engineer quotes, so the two are not reconciled) gives a median of 324 characters, a 90th percentile of 846, 26 over 900 and 4 over 1500. `0021` AC-12 is 342 characters, about the median, and was still ruled bundled. So a rule keyed on length would miss it, and how many of the 316 a reviewer would call bundled is not measured; only two rulings exist.

#### Option 1: keep the criterion whole, flag it, log the gap (chosen)

**Pros**: every reference to `AC-N` keeps landing on the one node it names; no change to spec 0002, the graph or the resolver; the model already behaves this way, so the prompt change only states it; the reviewer still sees `multi_condition_split` on the item; the gap is counted (`gap:bundled-ac`, 2) so the most frequent gap can drive a later spec change.

**Cons**: the graph loses the ability to point at one condition of a bundled criterion, so a chain that needs "abort on zero kept" reaches all of AC-17. The engineer's two rulings stay as disagreements in the tally, and the convention that a whole, flagged criterion is ruled `agree` from the re check on is a judgement about the ruling method, not a fix.

#### Option 2: split with sub ids and a part of link

**Pros**: keeps atomicity and referenceability both, in principle: a chain can name one condition, and a bare `AC-17` could still name the whole.

**Cons**: needs a spec 0002 amendment first. The model must not invent ids (line 58), so the sub ids would be assigned by code; that touches AC-3 and AC-4 (id shapes), AC-7 (how a bare `AC-17` resolves once parts exist), the relationship table (a new `part of` type, a closed set today), the graph model and the review queue. The corpus already uses a letter suffix (`AC-10b`) that the prompt reads as amending its numeric parent, so a part scheme cannot reuse it. Without more evidence, that cost is paid for two rulings.

#### Option 3: split freely and accept that the first part wins

**Pros**: no spec change.

**Cons**: every existing reference to the criterion lands on part 1, wherever the condition it meant actually sits, and nothing tells the reader. That is a silent graph corruption, which AGENTS.md's rules on uncertainty are written to prevent.

#### Option 4: split only blocks that carry no verbatim id

This is not a rival to Option 1; it is what Option 1 leaves open. `Done when` blocks, plain bullets and scope row bundles have derived ids, so splitting them costs no reference (AC-26). It is part of the chosen approach.

**Chosen: Option 1 with Option 4**, on the engineer's answer of 2026-09-28. Sub ids and a part of link reopen only if an eval chain or the re check needs a part of one criterion; if reopened, the design starts from a general parent `AC-N` node that bare references resolve to, with the parts listed under it and no automatic part matching.

### Amended 2026-09-28: the six rule and example candidates

Verified by reading `client.py` and the example files, and checked against `method-notes.md`, `ruling-sheet.md` and `ruling-tally.json`. Where a candidate could conflict with something already in the prompt, that is stated.

- **History link types.** `client.py:101-102` tells the model that a struck claim and its replacement are linked `superseded-by` or `corrected-by`, and `133-135` tells it a partial retirement is `amended-by`. A criterion stamped `SUPERSEDED` but only narrowed matches both, which is the conflict the runs split on (2 `superseded-by`, 1 `amended-by`). The fix states one test, what actually changed, in the Links section, and lets line 101 point there.
- **Category prefixes.** The test is whether a prefix starts more than one item in the unit, because a model can check that from the text alone and it matches the label index's own tie rule (spec 0002 AC-7: a tie resolves to `:Unresolved`). One point stays open: `0013`'s `Happy path:` and `Gate:` each appear once, so this test keeps them as labels, while the method notes call all the prefixes categories. The rule does not settle it and the re check will show whether it matters. `examples/0006` uses `Happy path` as a label, and the schema sample uses it too (AC-7), so a rule that banned every prefix would contradict the existing example.
- **Link starts from the connected item; `blocked-by` deliberate holds.** Neither has a rule today; both are additions.
- **Unclassified pointer between two criteria.** The rule already exists; what is missing is a demonstration. Excluded at the record level (AC-25): every record in group A, B or C, every re check record (`0014`, `0015`, feature 33's own record (0018)), every record an example already draws from, and every record an eval chain cites, which rules out `0011` (an eval chain cites `0011` AC-12) as well as `0013`, `0014` and `0015`. A rough search of criterion definitions that mention another criterion of their own spec leaves `0017` and `0019`, each with several candidates. That search did not read the pairs, so the build must confirm one is a real, unnamed dependency before using it.
- **Feature 21 example.** The `Done when` block was kept whole on purpose, to avoid three identical `Done when` labels tying (the example's own note). That reason no longer holds, since the current labelling rules already forbid a label on a block. Splitting removes the reason and matches the ruling on group C. The cost is that this example now teaches splitting on unnumbered blocks, which can move entity counts; the re check reports it. `Verify it` follows the ruling on group C entity 10.

### Amended 2026-09-28: the two recorded decisions

**AC-17 heterogeneity test, not run.** The trigger fired: group B's after spread was 3 (31, 34, 31; `heldout-table.json`). The engineer decided against the test. The reasons: 3 is about 9% of about 32 entities, and the stable `0021` baseline's 2 is 2 of about 20, 10%, so the relative spread is no wider; and the measured estimate was about 30 calls. That estimate replaces the "up to 39" in AC-17, which assumed 13 bold sub labels; counting `0013`'s `## Feature design` in the pinned corpus gives 10. Group C's after spread was also 3 (14, 17, 14), but AC-17's trigger names group B only. The trigger stays at 2, and the test reopens if `0015`'s `## Feature design` in the re check spreads by more than 2.

**The re check.** The accuracy bar in `method-notes.md` requires units the prompt and the tally never saw. `0014` `## Requirements`, `0015` `## Feature design` and JobHunt's feature 33 scope row appear in no worked example and in none of runs `0001`, `0006`, `0008`, `0012`, `0013`, `0021`, `feature-21`, `feature-9` (checked by listing `artifacts/runs/`). `0014` is cited by one eval chain (AC-20a of `0014`), which is not a conflict for the re check units themselves (AC-25's exclusion is about the seventh example, not the re check's own units), since the eval chains test the graph and not the prompt. The 10 entity and 5 relationship sample sizes come from `ruling-tally.json`'s counts. The $4.10 and $5.10 figures are the engineer's planning numbers, equal to experiment 0005's own measured 18 calls summed ($0.6918 + $0.4776 + $0.4276 + $1.2139 + $0.6693 + $0.5768 = $4.06, from `heldout-table.json`'s companion cost log); the `$0.22` figure in `verify.md`'s cost table is a character count estimate, not a measured figure, and is not the basis for this planning number. Per call output varied about 1.6x across experiment 0005's own runs (the `0021` after run averaged about 32k output tokens per call, `0013` about 20k), so a flat per call average is a rough basis. The recomputed go ahead figure (AC-20) should match each fresh unit to its nearest experiment 0005 twin by character count (`0014 ## Requirements` to `0021 ## Requirements`, `0015 ## Feature design` to `0013 ## Feature design`, the feature 33 row to the `0021` row, both densely enumerated scope-shaped text) rather than use one average across all three, and add one `0003.1` cache write and headroom for a retry. The reflex on API spend requires the figure to be recomputed from measured per call cost before the go ahead either way.

## Rationale

The label defect and the disagreement rate question have different root causes and different fixes, and treating them as one question was the planning error the earlier scope entry made. The defect is a missing rule in AC-7, not a missing demonstration; a worked example teaching the model to invent `binding rule 6` would have taught it to break the very rule that makes the existing example correct. Fixing it in code, scoped narrowly to the one heading shape the corpus actually shows this pattern for (`## Binding rules`, about 159 references, against `step N` at about 83, `invariant N` at about 67 and `revision N` at about 63, none yet shown to share the same structure), keeps the fix provable without spending anything.

Checking the committed artifacts rather than trusting the stated rule as fact turned up a second, more consequential problem: the model already invents labels today, and the schema's own field description is a plausible cause, since the exact invented string matches its sample text. This changes what "the model's own rule already works" means. It does not mean disabling model labelling; the one case with a real worked example (`TestScenario`, author named items) is exactly the case the corpus shows the model can do correctly once shown how, and AC-11e's existing routing already keeps an unstable label out of the graph rather than corrupting it silently. It does mean this spec cannot stop at wiring in examples and hope; it has to fix the schema sample, state the general rule explicitly, and then measure, which is what AC-6, AC-7 and AC-16 together do.

The disagreement rate question stays real and testable on its own terms once the label question is understood. The held out unit choice matters most: any before and after measurement run on `0006`, `0008`'s Preamble, `0012`'s sections or the `feature-21` row measures memorisation, since those are exactly what the examples demonstrate. `0021 ## Requirements` has no example of its kind at all; `0013 ## Feature design` has one (`0006`) but different content; a third row, `Profile entry`, distinct from `feature-21`, rounds out the set without repeating a subject already covered by `0013`'s job search content. Reporting the three groups separately, with an entity column and a relationship column each, answers what feature 11 needs: whether examples fix disagreement at all, and whether an in kind example generalises to new content of that kind. Whether the deeper AC-2 heterogeneity question also needs testing is decided by evidence rather than either assumed or silently dropped: 2 is the widest spread any stable committed unit showed (`0021`, `19 / 21 / 21`), so a heterogeneous held out unit landing at that spread or tighter after the fix means the prompt, not the unit boundary, was the cause, and splitting units is not chased on a hypothesis that measurement already answered.

Caching and cost: Anthropic's published pricing (fetched 2026-09-24, see References) confirms Claude Sonnet 5 at $2 per million input tokens and $10 per million output tokens, a cache read at 0.1x base input ($0.20/MTok), a 1 hour cache write at 2x base input ($4/MTok), and the Batch API at a flat 50% discount on both input and output, not the roughly 10x figure an earlier draft of this reasoning assumed (that 10x compares a cache read against an uncached input token, a different comparison). Prompt caching's default lifetime is 5 minutes, measured from the start of the request that last read or wrote it, not from the end of its response; experiment 0004 averaged about 15,700 output tokens per call, long enough to risk falling outside a 5 minute window between sequential calls. A 1 hour breakpoint costs more per write (2x versus 1.25x base input) but only needs to be paid once per session, since every `0003.0` call shares the identical examples prefix; it cannot help the fresh `0002.3` baseline call, which predates the examples block and stays uncached like every prior run. The Batch API's own docs (fetched 2026-09-24) confirm cache hits inside a batch are best effort, 30% to 98% observed, and recommend the 1 hour duration specifically because batch processing can outlast 5 minutes; this project's runs are already sequential and already output heavy, so the same reasoning applies without needing batch's asynchronous turnaround, which is a poor fit for a handful of calls the engineer wants to inspect immediately. Batch stays reserved for feature 9's future 564 call whole corpus run, where the 50% discount compounds over real volume.

## Evidence

**Rule 6's leading span, three definitions measured against the same data** (the committed `0002.3` runs of `0001 ## Binding rules`, `locate_line` from `src/tracepath/extract/locate.py` run against each entity's `span`, checked 2026-09-25; a "hold" count is entities whose located offset falls inside the span, per rule per run, tallied for all 8 rules across the 3 runs, 24 rule instances total):

| Span definition | Rule 6 holds (run 1 / 2 / 3) | Exact one entity, whole section | Where it misses |
|---|---|---|---|
| Marker to next `**M.**` marker | 2 / 6 / 2 | 17 of 24 | Rule 6 in every run (ambiguous, AC-2 leaves it unlabelled); rule 4 also over holds in runs 1 to 2 |
| Marker to first blank line (chosen, AC-1) | 1 / 1 / 1 | 23 of 24 | Rule 4 in run 3 only (0 entities located in the span, correctly falls to AC-3) |
| Bold headline only | 1 / 1 / 1 | 21 of 24 | Rule 4 in all three runs (0 entities; its own entity's located offset sits after the bold lead in ends) |

The earlier draft of this rationale cited "23 of 24" without stating which span it was measured on; it is the marker to first blank line span, the one AC-1 now specifies. The entity rule 6 resolves to also carries a different derived id in each run (`0001#binding-rules:10`, `:12`, `:6`), the same run to run id instability spec 0002's AC-11(a) already accounts for by comparing derived entities on their located line rather than their canonical id; AC-12 does the same.

**Ordinal reference patterns in the corpus** (`corpus/jobhunt/docs/`, grep counted 2026-09-24):

| Pattern | Occurrences | Structure confirmed to match references |
|---|---|---|
| `binding rule N` | 159 | Yes, `## Binding rules`, bold `**N.**` items; 0 occurrences of "binding rule 6" inside spec 0001's own text, confirming the entity carries no verbatim self label |
| `step N` | 83 | Not yet checked; out of scope for this spec (Follow up) |
| `invariant N` | 67 | Not yet checked; out of scope for this spec (Follow up) |
| `revision N` | 63 | Not yet checked; out of scope for this spec (Follow up) |

**Model labelling behaviour, committed `0006 ## Feature design` runs** (`artifacts/runs/0006/feature-design/run-{1,2,3}.json`, checked 2026-09-24, no example wired in yet):

| Finding | Evidence |
|---|---|
| Invented labels, zero corpus support | Runs 1 and 3 label Constraint entities `key invariant 1` through `key invariant 6`; the string occurs nowhere in the corpus as a self label, and matches `schema.py`'s own field description sample verbatim |
| Inconsistent labelling of a genuinely named item | The same item is labelled `Tell #4` in one run and `Eyebrow placement (Tell #4)` in another |
| Zero correct labels on the one case with a worked example | No committed run labels any `TestScenario`, the exact case `examples/0006-feature-design.md` demonstrates correctly |
| A garbled label | Run 2: `"label": "COPY-1atch check flag placeholder"`, not explained by this spec, see Follow up |

**Review queue composition** (`artifacts/review-queue.json`, 464 rows, rebuilt 2026-09-23 under `AC-11e`):

| Row kind | Count | Share |
|---|---|---|
| Relationship rows | 308 | 66% |
| Leftover entity signatures | 84 | 18% |
| Entity rows | 72 | 16% |

`runs_disagree` is the reason on 410 of the 464 rows. An entity only report of agreement, as the earlier scope entry framed it, would describe well under half the queue.

**Stable vs. unstable entity count spread, committed units** (source for AC-17's threshold of 2):

| Unit | Spread | Counts |
|---|---|---|
| `0021 ## Requirements` (widest stable) | 2 | 19 / 21 / 21 |
| `0012 ## Consequences` | 1 | 15 / 16 / 15 |
| `0012 ## Build plan` | 1 | 9 / 9 / 10 |
| `0008 ## Preamble` (unstable) | 11 | 16 / 17 / 27 |
| `0006 ## Feature design` (unstable) | 11 | 36 / 46 / 35 |
| `feature-21` scope row (unstable) | 24 | 15 / 38 / 14 |

**Verified pricing** (Claude Sonnet 5, fetched from Anthropic's published docs 2026-09-24):

| Item | Price |
|---|---|
| Base input | $2 / MTok |
| Output | $10 / MTok |
| 5 minute cache write | $2.50 / MTok (1.25x base input) |
| 1 hour cache write | $4 / MTok (2x base input) |
| Cache read | $0.20 / MTok (0.1x base input) |
| Batch input | $1 / MTok (50% of base) |
| Batch output | $5 / MTok (50% of base) |

Cross checked against experiment 0004's measured run: $1.0185 for 37,950 input tokens and 94,264 output tokens, uncached, no examples block, consistent with these rates at that call's actual token counts.

## References

**Project sources** (verifiable, in this repo):
- Spec 0002 (`docs/specs/0002-data-model/index.md`), AC-7, AC-11, the `:Entity` table
- `src/tracepath/extract/client.py`, `SYSTEM_PROMPT`, `PROMPT_VERSION`
- `src/tracepath/extract/schema.py`, `ExtractedEntity.label`, `ReferenceEndpoint.label`
- `src/tracepath/extract/locate.py`, `_line_of`, `Location` (offsets are unit relative, not corpus absolute)
- `examples/0006-feature-design.md`, `examples/0008-preamble.md`, `examples/0012-*.md`, `examples/feature-21-scope-row.md`
- `artifacts/runs/0006/feature-design/run-{1,2,3}.json`
- Experiments 0001 (type stability), 0002 (effort/low fidelity), 0003 (feature design TestScenario), 0004 (label round trip)
- `artifacts/review-queue.json`, `artifacts/runs/`, `experiments/README.md`
- `corpus/jobhunt/docs/specs/0001-stack-and-architecture/index.md`, binding rule 6's own text
- `corpus/jobhunt/docs/scope/scope.md`, the `Profile entry` row
- `docs/scope/scope.md`, feature 12 and feature 11

**Practices & standards**:
- Deterministic pre processing for anything code can read reliably, keeping the model's job narrow (the same principle behind AC-5 and AC-6)
- Held out evaluation, never measuring a model on the exact case it was shown
- Agreement is not accuracy: measure a human ruling alongside any agreement metric before trusting a falling disagreement rate

**Links** (fetched 2026-09-24):
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing
