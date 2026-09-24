# Scope: tracepath

A terminal tool that answers "why was this built this way?" from a project's own decision records. It walks a chain across records instead of retrieving passages. The corpus is JobHunt's specs, pinned at commit `2e40bcf`. There is one user: the author.

**Build approach:** Tracer Bullet (one thin, fully real thread through extract, resolve, store, and traverse; each later slice thickens one strand of that same thread).
**Workflow:** Beta (`/check verify`, then `/test`; `/test` may record a typecheck gate instead of a runner, on purpose). The project's default rigor tier; a feature's own tier tag (e.g. `· GA`) overrides it.

**Timebox:** about one week. This is an aim, not a deadline. If a decision would make this much bigger than a week, say so when it comes up.

**Standing rules:** no verification layer, because the visible chain is the check. Keep the eval small: a handful of questions and one script, never a harness or a dashboard.

_You are in charge. Every box below is a **suggestion**, not a gate: run any, skip any, and mark a feature `done` when you decide it is. The workflow records what you actually did (including "skipped"), it never requires a step. The one thing it asks is that a load bearing decision be written down (a spec), not that any check be run._

## At a glance

| # | Feature | Phase | Status |
| --- | --- | --- | --- |
| 1 | Stack & architecture | Foundation | done |
| 2 | Coding standards & tooling | Foundation | done |
| 3 | Corpus snapshot & eval set | Foundation | done |
| 4 | Data model | Foundation | in-progress |
| 5 | First traced chain | Slice 1 | planned |
| 6 | Eval runner | Slice 2 | planned |
| 7 | Name resolution | Slice 3 | planned |
| 8 | History aware traversal | Slice 4 | planned |
| 9 | Whole corpus | Slice 5 | planned |
| 10 | Rationale extraction and alternatives | Slice 6 | planned |
| 11 | Review volume and routing policy | after Slice 2, before Slice 5 | planned |
| 12 | Extraction stability on heterogeneous units | before feature 11 | planned |

## Foundations

### 1. Stack & architecture
Decide the language, graph store, and model access for extraction, then scaffold a runnable project. Leanings and the evidence behind them are in `reference/tracepath-for-scope.md`. They are inputs, not decisions.
**Done when:** the stack is recorded in a spec, and the empty project installs and runs one command from the terminal.
spec [0001](../specs/0001-stack-and-architecture/index.md) · code in `src/tracepath/`
- [x] Decide the stack (spec): `/architect stack & architecture`
- [x] Scaffold from the decision: `/develop stack & architecture`

### 2. Coding standards & tooling
Record conventions and tooling from the real scaffolded project, then install them. This includes the two standing rules above.
**Done when:** root `AGENTS.md` reflects the real stack, the standing rules, the git workflow, and the test choice (runner or typecheck gate); lint, format, and typecheck run clean, locally and in CI on push.
- [x] Capture conventions + tooling choices: `/audit`
- [x] Install the tooling: `/develop tooling`

### 3. Corpus snapshot & eval set
Bring in JobHunt's `docs/` pinned at `2e40bcf`, and the finished eval file (five why questions with verified expected chains). Bring both in as they are. Nothing gets regenerated.
**Done when:** the snapshot and eval file are in the repo, the snapshot's commit is recorded next to it, and each expected chain cites records that exist in the snapshot.
code in `corpus/jobhunt/` (commit in `SNAPSHOT.md`) and `eval/` · checked by `tests/test_corpus.py`
- [x] Bring them in: `/develop corpus snapshot & eval set`

### 4. Data model · in-progress
Entities and relationships for decision records: what a record, a claim, and a link are. It must represent the same thing named several ways, an "unresolved, don't guess" marker for entities, and a "real relationship, unclassified" value for links. Test the draft against several real files (a spike inside the spec) before locking it.
**Done when:** the schema holds real extractions from several snapshot files, and both "not confident" values exist, so nothing gets forced into the nearest type or silently dropped.
spec [0002](../specs/0002-data-model/index.md) · code in `src/tracepath/extract/`, `src/tracepath/resolve/`, `src/tracepath/graph/`
- [x] Design it (spec): `/architect data model`
- [ ] Build it: `/develop data model` · reopened 2026-09-23: spec 0002 build plan tasks 16 and 17 are unbuilt code, added by the same day's AC-7 `label` amendment
  - [x] Pydantic schema and the five fixture runs copied fresh into `tests/` (AC-1, AC-12)
  - [x] Unit splitting (preamble, sections, scope rows and intros) plus the deterministic pre-checks for struck ranges and checkboxes (AC-2, AC-5, AC-6)
  - [x] Identity, citations and run comparison: verbatim and derived ids, line location, `compare_runs()` (AC-3, AC-4, AC-11) · AC-3 and AC-4 stand; the AC-11 part was built against the criterion as it read before the 2026-09-23 amendment and is reopened by the milestone below
  - [x] Graph load: constraints, `MERGE` upserts, a counter assertion on every write (AC-9, AC-13)
  - [x] Real runs: the thin thread, then endpoint resolution, review routing and the seven section kinds (AC-7, AC-10, AC-14) · 24 calls over 8 units, all four new entity types exercised in a section that is about them
  - [x] Amendments from the first real runs, 2026-09-23: the agreement signature (located line, no flags, counts not sets), the review queue entry shape, the held link rule that unblocked the graph load, and a `## Feature design` run for `TestScenario` (AC-7, AC-11, AC-14) · spec 0002 build plan tasks 11 to 14
  - [x] AC-11(d), from measurement over the committed artifacts: a derived entity whose `line` is null routes to review under `span_not_located` instead of accepting on its signature's count alone. Both routing paths, including the leftovers branch. Adds no queue rows today (all 26 already route under `runs_disagree`); it makes the rule hold by construction rather than by luck (AC-11, AC-4) · spec 0002 build plan task 15 · built: accepted entities stay 71 and queue rows stay 403, with 10 rows newly labelled, 6 from the first run path and 4 from the leftovers branch
  - [x] Spec 0001's artifact storage row, the two surfaces it requires that the build had not built: token usage per attempt on every run artifact, failures included, and `artifacts/review-queue.json` plus `artifacts/review-log.json` written by the pipeline and tracked in git, so the 97 held links have somewhere durable to live (AC-11c, spec 0001 artifact storage) · found by `/check verify`
  - [ ] A `label` on a reference endpoint: the comparison signature gains it (AC-11e), `ReferenceEndpoint` and `resolve_endpoints()` gain the label match path with the held entity, struck exclusion, and id precedence rules, and the prompt gains its first worked example (AC-7, AC-10, AC-11c) · spec 0002 build plan tasks 16 and 17 · needs a real run against spec 0001's `## Binding rules` section and 0008's `Preamble` before it can be marked built
- [x] Verify it: `/check verify data model`
- [x] Test it: `/test data model`

## Slice 1: First traced chain

### 5. First traced chain · needs a decision
The walking skeleton. Take a few hand picked records, match them by explicit identifiers only, store them, and walk a chain. The terminal prints the answer to one eval question, with each link citing its record. Every layer is real, and the scope is narrow.
**Done when:** one eval question whose answer spans three records returns that chain in the terminal, each link cites its source record, and running it again gives the same chain.
- [ ] Design it (spec): `/architect first traced chain`

## Slice 2: Eval runner

### 6. Eval runner
One small script that runs the five eval questions and compares each returned chain to its expected chain. From here on, every later slice is measured by it.
**Done when:** one command prints pass or fail per question with the difference shown, and the slice 1 question passes.
- [ ] Build it: `/develop eval runner`

## Slice 3: Name resolution

### 7. Name resolution · needs a decision
Match records that name the same thing by number, nickname, or file name, so a chain doesn't quietly break across names. When a match isn't confident, the name is marked unresolved and shown, never guessed.
**Done when:** a chain whose links use different names for the same record resolves correctly, and an uncertain match shows up as unresolved in the output.
- [ ] Design it (spec): `/architect name resolution`

## Slice 4: History aware traversal

### 8. History aware traversal · needs a decision
Follow supersession, amendment, and correction correctly. A fact that was later replaced must never come back as current.
**Done when:** a chain that crosses a superseded or corrected record shows the replacement as current and marks the older one as history.
**Known risk, recorded 2026-09-23 from the first real extraction runs:** extraction can keep a struck claim and lose its replacement, storing both as one span marked struck, so the current fact arrives already labelled obsolete. Measured on bullet 3 of spec 0012's `## Consequences`, 1 of 3 runs at `medium` effort and 2 of 3 at `low`. Only run disagreement caught it, which is not a guarantee. This row's Done when must hold against that input, not just against a correctly split one. See spec [0002](../specs/0002-data-model/index.md) `## Consequences` and [experiment 0002](../../experiments/0002-effort-low-fidelity/README.md).
- [ ] Design it (spec): `/architect history aware traversal`

## Slice 5: Whole corpus

### 9. Whole corpus
Extend extraction from the hand picked records to every record in the snapshot, rebuilt in one run.
**Done when:** the full snapshot is ingested in one rebuild, all five eval questions pass, and relationships that fit no named type appear as unclassified, not dropped.
- [ ] Build it: `/develop whole corpus` · blocked until feature 11 decides the routing policy, because a whole corpus run at the current accept to review ratio would queue thousands of rows for one reviewer

### 11. Review volume and routing policy · needs a decision · from spec 0002
How much the routing rules should hold back, decided on logged evidence rather than on feel. Measured over the 8 units extracted so far: **403 queue rows against 71 accepted entities**, by reason `runs_disagree` 340, `endpoint_not_accepted` 98, `known_trap_flag` 77, `unclassified_type` 1, and concentrated in the heterogeneous units (0012 122, feature-21 114, 0021 76, 0006 53, 0008 38). Extrapolated across 188 sections that is thousands of rows with one reviewer, which is not a workable review step. HANDOFF's own plan was always to loosen routing once logged review decisions showed where it over flags; `artifacts/review-log.json` now exists and is empty, so that evidence can finally start accumulating. Measure the accept to review ratio **per unit kind**, since the counts above say the problem is concentrated rather than uniform, then decide a loosening policy. Two things this must not do: loosen the comparison itself, which spec 0002 names as the one change that would put unverified items into the graph, and treat near duplicate queue entries from AC-11a's line sensitivity as extraction defects. Spec 0002's AC-11(d) adds no rows today and is not the cause. **Added 2026-09-23**: neither is AC-11(e), but it is not nothing either. Spec 0002's AC-7 amendment puts a `label` into the comparison signature, model produced text and a new source of run to run disagreement the same way flags were; the 403 against 71 count above was measured before that lands (feature 4's build plan tasks 16 and 17, unbuilt). Re measure after those land, not before, or this feature's per unit kind ratio is measuring a signature that no longer exists.
**Two candidate framings, both open.** Weigh them against each other rather than starting from the first.

1. **Tune the routing.** The queue is the right mechanism and its thresholds are wrong. Measure the ratio per unit kind, loosen where the evidence says it over flags, keep a person in the loop.
2. **Question whether the queue belongs here at all.** This project's standing rule is "no verification layer, because the visible chain is the check", and a human queue of this size is a verification layer. It came from the reference pipeline, which was hand run in a learning workspace at a scale where a person really could rule on every row, rather than from this project's own rules. The alternative to weigh is writing items with their confidence recorded and letting a chain display a disputed step, which is exactly how `unclassified`, `:Unresolved` and `UNCLASSIFIED` links already work: uncertainty is visible in the chain instead of blocking it. Note the tension to resolve either way, spec 0001 currently lists the review queue as _matching_ the visible chain rule, but does so on the grounds that its files are plain diffable JSON, which is a claim about the file format and not about whether a person must clear a queue before a chain can be read.

**Feature 12 comes first.** 340 of these 403 rows are `runs_disagree`, and feature 12 tests whether that rate is an artifact of an exampleless prompt and an over broad unit definition rather than a property of the corpus. Setting a policy before that answer risks tuning thresholds around a defect, so weigh this one knowing whether the disagreement is fixable at source.

**Decided on eval evidence, not on argument.** Both framings are arguable from first principles and neither wins that way, so the tie breaker is what the eval actually returns. This needs feature 6 first: once the eval runner exists, run the five eval questions under **both** policies, review gated and write everything with its status recorded, and record which chains break under each and how. A chain that is right under one and wrong or absent under the other is the evidence; a chain that is identical under both says the queue is not what decides that answer. Run it before writing the spec, not after, so the spec records a measurement rather than a preference.

**Done when:** the accept to review ratio is measured per unit kind, the five eval questions have been run under both policies with the broken chains recorded, both framings are weighed on that evidence, a policy is decided and recorded in a spec, and feature 9 is unblocked or explicitly allowed to run at the current ratio.
- [ ] Design it (spec): `/architect review volume and routing policy` · blocked until feature 6 ships, because the eval runner is what produces the evidence this decision rests on

## Slice 6: Rationale and alternatives

### 10. Rationale extraction and alternatives · needs a decision · from spec 0002
Widen extraction to each spec's `rationale.md`, with an `Alternative` entity type for an option a spec weighed: what it was, whether it was chosen, and the reason. A census inside spec 0002 found that 9 of 20 plausible questions across four specs need `rationale.md`, and every one of them asked about an alternative the spec rejected. Two limits to settle here rather than assume: an outcome is not only chosen or rejected (spec 0012's rationale says "Anthropic is parked, not rejected"), and `Alternative` answers "why this one over that one" but not "what was the decision before, and why did it change" (0012's vendor pick was re-decided in place and the old version is kept nowhere else). That second shape stays open alongside a `Claim` type.
**Done when:** a "why not X" question returns a chain that reaches the rejected option and its reason, each link citing its record, and an option whose outcome fits neither chosen nor rejected is visible as such rather than forced into one.
- [ ] Design it (spec): `/architect rationale extraction`

### 12. Extraction stability on heterogeneous units · needs a decision · from spec 0002
Whether the run to run disagreement is a fact about the corpus or a fixable defect in how units are cut and prompted. It is the single largest cost in the pipeline: 340 of the 403 queue rows are `runs_disagree`. **Added 2026-09-23**: that count predates spec 0002's AC-7 amendment, which puts a `label` into the comparison signature (AC-11e), a new source of run to run disagreement (feature 4's build plan tasks 16 and 17, unbuilt). Run the prompt examples experiment this feature is built on after those land, not against the current 340, or it will be diagnosing a signature that no longer exists.

**The split is sharp.** Some units are near perfectly repeatable: `0012 ## Requirements` returns 14 / 14 / 14 entities, `0012 ## Follow-up` 9 / 9 / 9, and `TestScenario` in `0006 ## Feature design` returns 16 / 16 / 16 against exactly 16 `**Critical test scenarios**` bullets in the source, a count that is exact three times over rather than approximately right. Others swing wildly: `0006 ## Feature design` 36 / 46 / 35, the `feature-21` scope row 15 / 38 / 14, `0008 ## Preamble` 16 / 17 / 27.

**Two candidate causes, both testable, and the evidence already narrows the second.**

1. **The prompt has no worked examples at all.** Not "examples drawn from the wrong unit kind", none: `PROMPT_VERSION` `0002.2` is 1,961 characters of rules with zero examples, for any of the seven unit kinds. Spec 0002's Consequences said the tested pipeline's prompt and its few shot examples "must be rewritten from the enums rather than reused as they are"; the rewrite dropped them rather than rewriting them, and nothing since has put any back. So the model is asked to apply an eight type vocabulary with no demonstration of what a `Consequence` looks like against a `Constraint`, which is exactly the boundary the unstable units are full of.
2. **Heterogeneity, which is not the same as size, and the committed data separates them.** Sorting the 8 extracted units by character count against their entity spread shows size does not predict instability:

   | chars | spread | counts | unit |
   |---|---|---|---|
   | 4,040 | **11** | 16 / 17 / 27 | `0008 ## Preamble` |
   | 4,462 | 0 | 14 / 14 / 14 | `0012 ## Requirements` |
   | 5,344 | 0 | 9 / 9 / 9 | `0012 ## Follow-up` |
   | 5,925 | 1 | 15 / 16 / 15 | `0012 ## Consequences` |
   | 6,548 | 1 | 9 / 9 / 10 | `0012 ## Build plan` |
   | 7,385 | **24** | 15 / 38 / 14 | `feature-21` scope row |
   | 12,447 | 2 | 19 / 21 / 21 | `0021 ## Requirements` |
   | 14,311 | **11** | 36 / 46 / 35 | `0006 ## Feature design` |

   The smallest unit in the set is the third least stable, and the second largest is nearly stable. What the three unstable units share is not length but **mixture**: each holds several kinds of claim at once, while every stable one is a uniform list of a single kind. `0006 ## Feature design` carries 13 bold sub labels, so it is not one section but thirteen glued together. That points at **AC-2's unit definition**, specifically whether a bold sub label inside a section should start a new unit, rather than at unit size or at the schema. Test heterogeneity directly; splitting a large homogeneous section would be effort spent on the wrong variable.

**Ordering: this runs before feature 11 decides.** Feature 11 is choosing a policy for a disagreement rate whose cause is unknown, and the two answers differ. If the rate is largely an artifact of an exampleless prompt and an over broad unit, the honest fix is at source and the policy question shrinks with it; if the rate survives both fixes, it is a real property of the corpus and feature 11 is choosing how to live with it. Deciding the policy first would risk tuning thresholds around a defect. This feature needs no eval runner, so it is not blocked behind feature 6 the way feature 11 is, and it can start now.

**If examples change the prompt, AC-14's verdict has to be re-earned.** `PROMPT_VERSION` bumps from `0002.2`, and every agreement figure behind AC-14 was measured under the no examples prompt, so it says nothing about the new one. Re-run AC-14's coverage set under the new prompt to confirm the four new types (`Consequence`, `FollowUp`, `BuildStep`, `TestScenario`) still come back stably. Budget **about $3.30**, not the $2.70 the older figure suggests: the coverage set is 8 units and 24 calls since `## Feature design` joined it in the 2026-09-23 amendment, and that unit costs about $0.22 per call against $0.1268 for the rest (21 calls at $0.1268 is $2.66, plus 3 at $0.2198 is $0.66). Record the result as a new experiment with a forward pointer added to experiment 0001, never by editing experiment 0001's own numbers: it is the record of what the old prompt did, and overwriting it would destroy the only before half of the comparison.

**Done when:** both causes are tested against a real re-run of one unstable unit, with a before and after table in `experiments/`, and the result either changes the prompt, changes AC-2's unit definition, or is recorded as not the cause. If the prompt changed, AC-14's coverage set has been re-run under the new `PROMPT_VERSION` and the four new types still come back stably. Spends API money: roughly $0.70 per three run configuration at `medium` on `0006 ## Feature design`, measured, plus about $3.30 if the AC-14 re-run is triggered, so confirm the number of configurations before running.
- [ ] Design it (spec): `/architect extraction stability on heterogeneous units`

## Deferred
Out of scope for the current build pass, kept so the plan stays honest.
- **Prose answers**: generated prose written over the chain · needs a decision
- **Visual UI**: a graphical view of chains · needs a decision
- **Dashboard**: none planned for a single user project
- **Agentic traversal comparison**: a separate later experiment set against this traversal · needs a decision
- **Two stage typing**: can a calibrated classifier (e.g. typesafe.ai's Jev, classifier.dev) reduce type and flag churn? Claude segments a unit into spans and relationships; a classifier assigns the entity type from the closed enum with a confidence, and low confidence maps onto unclassified and the review queue. Would amend spec 0001's extraction row and add a second provider. Revisit after feature 5, measured by the eval, as an experiment under `experiments/` · needs a decision

## Legend

**The decision box.** Every feature carries exactly one, the sub-task whose label ends with `(spec)`. Its wording varies (`Design it (spec)` normally, `Decide the stack (spec)` on Stack & architecture), so skills locate it by that `(spec)` suffix, never by an exact label. Every other box is an execution box and `/architect` never ticks one.

**Feature lifecycle**: the scope updates as a feature moves; each row is what it shows and who sets it:

| State | Set by | The feature shows |
| --- | --- | --- |
| `planned` · needs a decision | `/scope` | one box: `Design it (spec): /architect <feature>` |
| `in-progress` (designed) | **`/architect` at spec capture** | `Design it` ticked; spec linked; `Build it: /develop <feature>` + **2 to 5 milestones**; the tier's closing boxes (`Verify it` Alpha+, `Test it` Beta+, `Review it` + `Document it` GA); any surfaced follow up enrolled |
| `in-progress` (building) | `/develop` | milestone sub boxes tick one by one; code pointer filled |
| `in-progress` (verified) | `/check verify` | `Build it` + milestones ticked; `Verify it` ticked |
| `done` | **you, when you decide it is** (any skill sets it when you say so); `/sync` reconciles | the boxes you ran are ticked, ones you skipped are recorded as skipped; the tier's last stage (`Prototype` → after `/develop`; `Alpha` → after `/check verify`; `Beta`/`GA` → after `/test`) is the *suggested* point to call it done, never a gate; `/sync` captures conventions |

- **Next step** = the first unticked box (always a command or a tracked milestone).
- **needs a decision** = run `/architect` first; otherwise straight to `/develop` (or `/audit` for standards & tooling). The tag drops once the spec is captured.
- **Atomic build tasks live in the spec's `## Build plan`, not here**: the scope carries only the milestone rollup.
- **Status** `planned` → `in-progress` → `done`, plus `existing` (pre-workflow) and `dropped` (de-scoped, kept for history).
- **Approach tag** beside a heading (e.g. `· Facade`) overrides the project default for that feature; no tag = inherits it.
- **Workflow tier tag** beside a heading (e.g. `· GA`, `· Prototype`) overrides the project default `**Workflow:**` tier for that one feature; no tag = inherit. The **effective tier** (tag if set, else default) is the *recommended* verification depth; every skill reads it the same way to suggest the next step and to shape the closing boxes. Those boxes are suggestions you run or skip; skipping never blocks `done`. The single rigor dial (no separate "weight").
- **Workflow** (header line) is the project default tier, the stages each feature *suggests* running **after** `/develop`: **Prototype** = nothing (rely on its build time self check); **Alpha** = `/check verify`; **Beta** = `/check verify` then `/test`; **GA** = adds a fresh model `/check review` then `/document`. `done` is your call, not gated on these; a skipped stage is recorded as skipped. An `Assumed` spec is flagged on the feature (its decision still owes ratification) but does not block you from marking `done`; `/architect` still records any load bearing decision, the one thing the workflow asks. A feature's own tier tag overrides the default.
- **Pointer line** (`spec <n> · code in <path>`): the spec link added by `/architect`, the code path by `/develop`.
