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

### 4. Data model
Entities and relationships for decision records: what a record, a claim, and a link are. It must represent the same thing named several ways, an "unresolved, don't guess" marker for entities, and a "real relationship, unclassified" value for links. Test the draft against several real files (a spike inside the spec) before locking it.
**Done when:** the schema holds real extractions from several snapshot files, and both "not confident" values exist, so nothing gets forced into the nearest type or silently dropped.
spec [0002](../specs/0002-data-model/index.md) · code in `src/tracepath/extract/`, `src/tracepath/resolve/`, `src/tracepath/graph/`
- [x] Design it (spec): `/architect data model`
- [ ] Build it: `/develop data model`
  - [x] Pydantic schema and the five fixture runs copied fresh into `tests/` (AC-1, AC-12)
  - [x] Unit splitting (preamble, sections, scope rows and intros) plus the deterministic pre-checks for struck ranges and checkboxes (AC-2, AC-5, AC-6)
  - [x] Identity, citations and run comparison: verbatim and derived ids, line location, `compare_runs()` (AC-3, AC-4, AC-11)
  - [x] Graph load: constraints, `MERGE` upserts, a counter assertion on every write (AC-9, AC-13)
  - [ ] Real runs: the thin thread, then endpoint resolution, review routing and the six section kinds (AC-7, AC-10, AC-14) · endpoint resolution and review routing are built and tested; the real runs need `ANTHROPIC_API_KEY`, so AC-14 is not met yet
- [ ] Verify it: `/check verify data model`
- [ ] Test it: `/test data model`

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
- [ ] Design it (spec): `/architect history aware traversal`

## Slice 5: Whole corpus

### 9. Whole corpus
Extend extraction from the hand picked records to every record in the snapshot, rebuilt in one run.
**Done when:** the full snapshot is ingested in one rebuild, all five eval questions pass, and relationships that fit no named type appear as unclassified, not dropped.
- [ ] Build it: `/develop whole corpus`

## Slice 6: Rationale and alternatives

### 10. Rationale extraction and alternatives · needs a decision · from spec 0002
Widen extraction to each spec's `rationale.md`, with an `Alternative` entity type for an option a spec weighed: what it was, whether it was chosen, and the reason. A census inside spec 0002 found that 9 of 20 plausible questions across four specs need `rationale.md`, and every one of them asked about an alternative the spec rejected. Two limits to settle here rather than assume: an outcome is not only chosen or rejected (spec 0012's rationale says "Anthropic is parked, not rejected"), and `Alternative` answers "why this one over that one" but not "what was the decision before, and why did it change" (0012's vendor pick was re-decided in place and the old version is kept nowhere else). That second shape stays open alongside a `Claim` type.
**Done when:** a "why not X" question returns a chain that reaches the rejected option and its reason, each link citing its record, and an option whose outcome fits neither chosen nor rejected is visible as such rather than forced into one.
- [ ] Design it (spec): `/architect rationale extraction`

## Deferred
Out of scope for the current build pass, kept so the plan stays honest.
- **Prose answers**: generated prose written over the chain · needs a decision
- **Visual UI**: a graphical view of chains · needs a decision
- **Dashboard**: none planned for a single user project
- **Agentic traversal comparison**: a separate later experiment set against this traversal · needs a decision

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
