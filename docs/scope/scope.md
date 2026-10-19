# Scope: tracepath

A terminal tool that answers "why was this built this way?" from a project's own decision records. It walks a chain across records instead of retrieving passages. Today an item id goes in and the cited chain comes out. _Changed 2026-10-19:_ for the rest of v1, the question is typed in plain English and the tool prints an answer whose claims each cite a graph item (feature 16, see the v1 finish line). The corpus is JobHunt's specs, pinned at commit `2e40bcf`. There is one user: the author.

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
| 4 | Data model | Foundation | done |
| 5 | First traced chain | Slice 1, closes after v1 | in-progress |
| 6 | Eval runner | Slice 2 | done |
| 7 | Name resolution | Slice 3, after v1 | planned |
| 8 | History aware traversal | Slice 4, after v1 | planned |
| 9 | Whole corpus | Slice 5 | done |
| 10 | Rationale extraction and alternatives | Slice 6 | planned |
| 11 | Review volume and routing policy | after Slice 2, before Slice 5 | done |
| 12 | Extraction stability on heterogeneous units | before feature 11 | done |
| 13 | Extraction accuracy | after feature 6, before feature 11 | in-progress |
| 14 | Held item view | Slice 1, before Slice 2 | done |
| 15 | Question to start item | folded into feature 16 on 2026-10-19 | dropped |
| 16 | Answer at question time | v1, replaces the remaining v1 needs | in-progress |

## v1 finish line

### Change of direction, recorded 2026-10-19 (this replaces the line below for the rest of v1)

**New v1 line:** "You ask tracepath a why question in plain English and it prints an answer whose every claim cites an item in the graph, with any link it inferred rather than read marked as inferred."

**Evidence for the change:**
1. All seven questions run so far (the five eval questions and two held out) fail on today's walk at a document boundary ([experiment 0015](../../experiments/0015-whole-corpus-run/README.md), PR #40).
2. A hand prototype of answering at question time, 2026-10-19: the five eval questions, the session playing the model's part, no API call. The engineer's marks: question 1 right, question 2 right, question 3 partly right (retrieval missed 0007 AC-12), question 4 right, question 5 right. This is a hint from one hand run, not a measurement of the built feature.

**Success bar, set now, before any design or build:**
- At least 4 of the 5 eval questions and at least 3 of the 4 held out questions are answered right, each judged by the engineer against its expected answer.
- Eval questions 1 to 5 may be used to adjust the prompt.
- The four held out questions run once, at the end, and are never used to adjust anything.
- If the bar is not met, v1 still finishes, reported as it is, with each failing question's cause.

**Limit of the held out set:** all four of its questions sit in a small cluster of records (0004, 0010, 0016 to 0018). A pass there says little about the rest of the corpus.

**What moves:** feature 15 folds into the new feature 16. Features 8 and 7 move to after v1 as retrieval improvements. Feature 5 (first traced chain) also moves to after v1: it closes only when the walk itself passes a question that spans two or more records, which is now the job of features 8 and 7.

**History kept:** everything below this block is the earlier plan, left as recorded. Its 2026-10-19 fallback lines still stand as history, and its "v1 needs" list is superseded by feature 16.

### Earlier v1 finish line (superseded 2026-10-19, kept as history)

_Recorded 2026-10-13._ v1 is done when: "You ask tracepath a why question about JobHunt and it prints a chain of cited steps across documents for at least 3 of the 5 eval questions, over the whole corpus. Question 4 (an absence question) is expected to stay inconclusive and question 5 is expected to need feature 7."

**v1 needs, in this order:**
1. Feature 13 step one closed after the engineer's stage one rulings, whatever their result. There is no fourth unit, and the code pass stays off. _Done._
2. Feature 11. _Done 2026-10-18 (spec 0008 accepted, merged in `c4b9970`)._
3. Feature 9, as a full re extraction of the whole corpus (see feature 9). _Done._
4. The two held out questions: the engineer checks their expected chains against the corpus at `2e40bcf` and commits any correction, then they are run. The run is free once feature 9's extraction exists.
5. Feature 5, which closes with the first passing question that spans two or more Records, then its `/check verify`.
6. Feature 15 step one, which still needs `/architect`.

_Order after feature 9 confirmed by the engineer 2026-10-18._ The held out run goes before features 5 and 15 so that no result of theirs can shape the check.

**After v1:** feature 13's later steps, features 7, 8 and 10, and the cross model experiment (see Deferred). _Added 2026-10-19: feature 5 also moves here, and features 7 and 8 are now retrieval improvements; the needs list above is superseded by feature 16._

**How v1 counts the questions, decided 2026-10-18.** Two readings are reported, side by side, never as one rate:
- **Strict reading (the one the finish line above is measured by):** a question counts when `eval` prints `PASS`, so every expected step is reached through accepted items only. A step reached only as held is not reached (spec [0006](../specs/0006-eval-runner/index.md) AC-6b, spec [0005](../specs/0005-held-item-view/index.md) condition 4).
- **Second reading, added 2026-10-18 after seeing [experiment 0014](../../experiments/0014-review-volume-and-routing-policy/README.md)'s four way table:** the same, but a step reached only as held also counts. This is read by hand from the `held only` lines `eval` already prints for each item. It needs no eval change and no spec amendment, because spec 0006 AC-7 forbids totals and the runner stays as it is. It was added after the data was seen, and it never replaces the strict reading.
- Today, with both defaults on, no question with a trace list passes under either reading: questions 1, 3 and 5 each have at least one step no configuration reaches. Only question 4, the absence question, reads `PASS`.

**Question 4, corrected 2026-10-18.** The finish line above expects question 4 to stay inconclusive. Under the narrow hold default it reads `PASS`, its two items staying not reached (experiment 0014). The 2026-10-13 wording is left as recorded.

**Question 4's count, 2026-10-19, written before feature 9's remaining units run.** Question 4's PASS (a proven absence) counts toward the 3 of 5, reported as "3 of 5, one of them a proven absence", strict reading first.

**Fallback, 2026-10-19, decided before the full corpus run.** If fewer than 3 of 5 pass after feature 9 (counting question 4), v1 is still finished; the eval is reported as it is, with each failing question's cause from the 2026-10-19 diagnosis (a link the text does not state: questions 1 and 2; a link ending on a whole spec rather than an item: question 3; name resolution, feature 7: question 5), and those causes become the after v1 work.

**Result after feature 9, 2026-10-19.** 1 of 5 under both readings, the one a proven absence (question 4); questions 1, 2, 3 and 5 fail, so the fallback above applies and v1 is finished, with the eval reported as it is and each failing question's cause as the fallback names it ([experiment 0015](../../experiments/0015-whole-corpus-run/README.md)).

**Held out run, 2026-10-19.** On `ddd6e51`, after `tracepath load` with both defaults, `tracepath eval --eval-file eval/held-out.json --release-held-out`: held out question 1 FAIL, 0 of 2 expected items reached besides the start (spec 0010 AC-14: `link_held`; spec 0010 Build plan step 2: `no_link`); held out question 2 FAIL, 3 of 7 expected items reached besides the start (spec 0018 Review findings, caution: `held_for_review`; spec 0018 Review findings, caution (also): `no_link`; spec 0018 AC-4: `link_held`; spec 0018 Follow-up: `no_link`).

Held out check, 2026-10-19: both expected chains checked by the engineer against 2e40bcf, no corrections; a cross check from the JobHunt author confirmed all 13 quotes verbatim and found two answer prose claims slightly overstated (one causal link inferred, one claim about test code not checkable from docs), which the runner does not read.

**Reconciled 2026-10-18:** feature 9's Done when used to say all five eval questions pass, which is stricter than this line. The engineer chose to match this line. Feature 9 no longer promises five of five, and the 3 of 5 bar lives here only.

**Tripwire, before feature 9 starts:** look at how the released entity marks were ruled.
- If most are ruled disagree (a wrong cut or type), the engineer revisits the order before feature 9 starts. A prompt change after the whole corpus run would force a re extraction.
- If most are ruled agree, the hold itself is the problem, and it belongs to feature 11.

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

### 4. Data model · done
Entities and relationships for decision records: what a record, a claim, and a link are. It must represent the same thing named several ways, an "unresolved, don't guess" marker for entities, and a "real relationship, unclassified" value for links. Test the draft against several real files (a spike inside the spec) before locking it.
**Done when:** the schema holds real extractions from several snapshot files, and both "not confident" values exist, so nothing gets forced into the nearest type or silently dropped.
spec [0002](../specs/0002-data-model/index.md) · code in `src/tracepath/extract/`, `src/tracepath/resolve/`, `src/tracepath/graph/`
- [x] Design it (spec): `/architect data model`
- [x] Build it: `/develop data model` · reopened 2026-09-23: spec 0002 build plan tasks 16 and 17, added by the same day's AC-7 `label` amendment; done, including the real run the milestone below once owed
  - [x] Pydantic schema and the five fixture runs copied fresh into `tests/` (AC-1, AC-12)
  - [x] Unit splitting (preamble, sections, scope rows and intros) plus the deterministic pre-checks for struck ranges and checkboxes (AC-2, AC-5, AC-6)
  - [x] Identity, citations and run comparison: verbatim and derived ids, line location, `compare_runs()` (AC-3, AC-4, AC-11) · AC-3 and AC-4 stand; the AC-11 part was built against the criterion as it read before the 2026-09-23 amendment and is reopened by the milestone below
  - [x] Graph load: constraints, `MERGE` upserts, and on every batched write a returned row count (`RETURN count(...) AS written`) asserted against the rows given (AC-9, AC-13)
  - [x] Real runs: the thin thread, then endpoint resolution, review routing and the seven section kinds (AC-7, AC-10, AC-14) · 24 calls over 8 units, all four new entity types exercised in a section that is about them
  - [x] Amendments from the first real runs, 2026-09-23: the agreement signature (located line, no flags, counts not sets), the review queue entry shape, the held link rule that unblocked the graph load, and a `## Feature design` run for `TestScenario` (AC-7, AC-11, AC-14) · spec 0002 build plan tasks 11 to 14
  - [x] AC-11(d), from measurement over the committed artifacts: a derived entity whose `line` is null routes to review under `span_not_located` instead of accepting on its signature's count alone. Both routing paths, including the leftovers branch. Adds no queue rows today (all 26 already route under `runs_disagree`); it makes the rule hold by construction rather than by luck (AC-11, AC-4) · spec 0002 build plan task 15 · built: accepted entities stay 71 and queue rows stay 403, with 10 rows newly labelled, 6 from the first run path and 4 from the leftovers branch
  - [x] Spec 0001's artifact storage row, the two surfaces it requires that the build had not built: token usage per attempt on every run artifact, failures included, and `artifacts/review-queue.json` plus `artifacts/review-log.json` written by the pipeline and tracked in git, so the 97 held links have somewhere durable to live (AC-11c, spec 0001 artifact storage) · found by `/check verify`
  - [x] A `label` on a reference endpoint: the comparison signature gains it (AC-11e), `ReferenceEndpoint` and `resolve_endpoints()` gain the label match path with the held entity, struck exclusion, and id precedence rules (AC-7, AC-10, AC-11c) · spec 0002 build plan tasks 16 and 17 · built and unit tested 2026-09-23, code in `src/tracepath/extract/schema.py`, `src/tracepath/extract/compare.py`, `src/tracepath/resolve/endpoints.py`, `src/tracepath/pipeline.py`; rebuilding `artifacts/review-queue.json` under the new signature moved accepted entities 71 to 67 and queue rows 403 to 436, all from entity labels that genuinely varied across runs. **Real run done the same day**, [experiment 0004](../../experiments/0004-label-round-trip/README.md), $1.0185 for six calls: the mechanism is confirmed correct against real data, but the entity side never writes `label` at all, so no reference of this shape has matched yet in the corpus. Not fixed here; carried to feature 12 as concrete evidence. The prompt's rule text was updated for `label`; a full worked example was deliberately not added, flagged for feature 12 instead of preempting its own undecided question
- [x] Verify it: `/check verify data model` · full suite (296 unit + 20 integration) green, mypy strict clean, ruff clean; live Neo4j confirms 3 uniqueness constraints (AC-9), a full committed-artifact reload with zero phantom nodes (AC-13), and the committed review queue (464 rows) holding the `0008` Preamble's `binding rule 6` reference under `endpoint_not_accepted`, matching experiment 0004 exactly. The label match path itself (an entity actually carrying a matching `label`) is still unexercised by real data, as experiment 0004 already found and feature 12 already carries forward; not a new gap, not reverified as new
- [x] Test it: `/test data model` · closed 3 real gaps the label extension left untested: `unresolved_row()`'s new `record`/`label` mapping had no direct test (only indirect, through real data that never populates them), `normalize_label()`'s punctuation-preserving claim was untested, and `build_label_index()` had only its exclusion branches (struck, tied) covered, not its baseline single-match case. Added `tests/test_graph_model.py` (2 tests) plus tests in `tests/test_extract_schema.py` (5) and `tests/test_records_and_resolve.py` (1); full suite 324 passed (316 + 8 new), mypy strict clean, ruff clean

## Slice 1: First traced chain

### 5. First traced chain · in progress · after v1 (moved 2026-10-19)
_Moved after v1 on 2026-10-19. It closes only when the walk itself passes a question that spans two or more records, which is now the job of features 8 and 7. Nothing else about this feature changes._
The walking skeleton. Take a few hand picked records, match them by explicit identifiers only, store them, and walk a chain. The terminal prints the answer to one eval question, with each link citing its record. Every layer is real, and the scope is narrow.
**Done when:** one eval question whose answer spans two or more Records returns that chain in the terminal, each link cites its source record, and running it again gives the same chain. _Reworded 2026-10-05 from "three records": "record" means a Record node (spec 0002), and question 3, the one chosen for held out reasons, spans two, spec 0002 and spec 0007. See spec [0004](../specs/0004-first-traced-chain/index.md) AC-2a and AC-2b._
**Before it** (spec 0002's vocabulary revisit Follow up, `8bcd9df`, decided 2026-10-04): the only revisit owed before this feature is ruling the type of experiment 0008's one `0006 ## Feature design` sentence (typed `Consequence` in run 1 only; `0006` is on no eval chain), with the ruling added to feature 13's evidence. The types on the chosen question's chain are not checked beforehand, and no prompt, rule or type change is made for any eval question. This feature reports what it finds as it runs.
**Replanned 2026-10-06, after [experiment 0009](../../experiments/0009-first-traced-chain/README.md).** AC-41 failed: `trace --eval 3` printed no chain, because the start item `0002/AC-10` was held for review on a `multi_condition_split` flag, and `0007/AC-12`, `0007/AC-13` and the line 142 invariant were held the same way, each found by all three runs. The four new sections hold 258 review queue rows against 54 accepted entities. Across all 18 units, 176 of 674 queue rows (159 entities, 17 links; 53 from the four new sections) are held only for a `known_trap_flag`, the three runs agreeing (`artifacts/review-queue.json` at `36a6bc5`). **Why the order changed:** the result exposed a cycle. This feature cannot pass while its chain's items stay held, and either a routing policy change (feature 11) or a review of held items would release them; feature 11 waits on features 6 and 13; and feature 6's Done when required this question to pass. The engineer chose a status view of held items (feature 14) to break it, over a reorder alone, a hand review of the 258 rows, or a provisional rule accepting flagged items the runs agree on. Feature 6's Done when no longer depends on this question (see feature 6). Experiment 0009 stays the first result, and spec 0004's locked rules and scored prediction are unchanged. A rerun through feature 14 is a second, labelled result; whether any later result can close this feature is a separate `/architect` decision, recorded with its reason.
**Expected to close, noted 2026-10-07:** only after feature 11's routing policy is decided and question 3 is rerun under it. Feature 14's held view cannot pass this feature, because a held step never counts as reached or as a pass (spec [0005](../specs/0005-held-item-view/index.md), condition 4).
spec [0004](../specs/0004-first-traced-chain/index.md) · code in `src/tracepath/` (`traverse/`, `graph/read.py`, `report.py`, `cli.py`)
- [x] Design it (spec): `/architect first traced chain`
- [x] Build it: `/develop first traced chain`
  - [x] `load` command, link provenance, `file_line` and the build manifest, tested over the 14 committed units with no API call (AC-15 to AC-19, AC-50, AC-51)
  - [x] The walk, its Cypher read and the fixture graph tests, then `trace START` smoke tested away from specs 0002 and 0007 (AC-20 to AC-33)
  - [x] `extract` with its error handling, collision preflight, estimate, ceiling and per attempt writes, tested with a fake client (AC-3 to AC-14, AC-48, AC-49)
  - [x] The report step, the only reader of `eval/` (AC-34 to AC-41, AC-52)
  - [x] Gate, then the paid run on question 3's four sections and the recorded result in `experiments/0009-first-traced-chain/` (AC-41 to AC-47, AC-53, AC-54). The engineer approves the measured estimate and a ceiling first; `src/` is committed before the first run artifact
- [x] Build the 2026-10-06 amendment on `fix/extract-guards`, before any further paid extraction: `/develop first traced chain` (spec 0004's Build plan steps 12 to 16)
  - [x] The ceiling as a true per call bound, with `--ceiling` validated and both totals in the summary (AC-7b, AC-8, AC-8b, AC-8c, AC-9, AC-10a, AC-14b, AC-55)
  - [x] The run policy by failure kind, the SDK's retries off, and the no cache stop's exception (AC-11, AC-13, AC-67, AC-67b, AC-68 to AC-70)
  - [x] The dry run names collisions without stopping (AC-6d, AC-6e)
  - [x] `extract --resume` and the manifest's `extracted_at` list (AC-48, AC-56 to AC-65)
- [x] Build the second 2026-10-06 amendment on `fix/extract-guards`: the old retry path fenced, the allowlist test, the test fixture away from the real API, and the `0021` pins (spec 0004's Build plan step 17, AC-71 to AC-74c)
- [ ] Verify it: `/check verify first traced chain`
- [x] Test it: `/test first traced chain`

### 14. Held item view · done · from experiment 0009
A load mode that also writes held items, each marked held with its reasons, so a chain can show a step the review queue holds instead of stopping before it starts. Held items stay out of every default output, and only an explicit flag brings them in. This is a view, not a routing policy: feature 11 still sets the real policy.
**Done when:** with the flag, a rerun of `trace --eval 3` gives a second, labelled result for question 3, scored against a prediction locked before the rerun; and without the flag, load, walk and report output never contains a held item.
**Conditions, set by the engineer 2026-10-06:**
1. Held items are excluded by default everywhere and included only with an explicit flag. A test proves that default load, walk and report output never contains a held item.
2. Spec 0004's walk rules (AC-20 to AC-30) are unchanged. The only addition is that, with the flag, the walk may step through held items, tested on a hand built fixture that is not an eval chain.
3. Before the rerun, a fresh prediction for question 3 is locked and the new code is committed. The result record names the design, code and result commits in that order, as spec 0004 did.
4. A held step is always printed as held and never counts as reached or as a pass. "Reached only through held items" means an expected item whose path, or the item itself, includes at least one held node or link, and it is scored as its own outcome.
5. Experiment 0009 stays the first result; the rerun is a second, labelled result.

spec [0005](../specs/0005-held-item-view/index.md) · amends spec [0002](../specs/0002-data-model/index.md) AC-11(f) · code in `src/tracepath/pipeline.py`, `src/tracepath/traverse/`, `src/tracepath/graph/`, `src/tracepath/report.py`
- [x] Design it (spec): `/architect held item view` · the prediction for question 3 is locked in the spec, before any code
- [x] Build it: `/develop held item view`
  - [x] The marker and the filter, then the printed `HELD:` marker, on a hand built fixture (AC-2, AC-3, AC-7 to AC-11)
  - [x] The held view over the committed artifacts, then the write and the two command options, tested against Neo4j (AC-1, AC-5, AC-6, AC-17 to AC-26b)
  - [x] The report: two walks, `held only`, the label lines (AC-4, AC-12 to AC-16)
  - [x] The rerun, no API call: `load --with-held`, `trace --eval 3 --with-held`, the record in `experiments/0010-held-item-view/` naming design, code and result commits (AC-25, AC-27, AC-29)
- [x] Verify it: `/check verify held item view`
- [x] Test it: `/test held item view`

## Slice 2: Eval runner

### 6. Eval runner · done
One small script that runs the five eval questions and compares each returned chain to its expected chain. From here on, every later slice is measured by it.
**Done when:** one command prints pass or fail per question with the difference shown, and the runner reproduces experiment 0009's question 3 output from the run files as committed at `36a6bc5`.
**Changed 2026-10-06** (see feature 5): the Done when used to end "and the slice 1 question passes". That question failed on routing, not on the walk or the runner, so a finish line waiting on it would tie this feature to feature 11's policy and close the cycle again. The runner reuses feature 14's view for all five questions.
**Held out questions, a decision for `/architect` under this feature (set 2026-10-06):** one or two new held out questions, written by the method the original five used (a real "why" question whose answer spans records, with its expected chain read from the corpus at the pinned commit), committed before feature 13 starts. They are added alongside the five, which stay unchanged, since the eval set is brought in as is and never regenerated. They are not run, and their results are not looked at, by this feature, the held view (feature 14) or anyone, until features 13 and 11 have both locked their choices; they then check those choices. They are written by a fresh session that sees only the corpus at the pinned commit and this method, never `artifacts/`, `experiments/` or the review queue. They draw only on sections not yet extracted and not used by any worked example in `examples/`. They are committed in a separate file (for example `eval/held-out.json`) that no command reads unless explicitly pointed at it. Their sections are extracted once, with the prompt feature 13 settled on, only at that point, after a measured cost estimate and approval. Their results are reported one by one, never as a rate, and described as a check, not a measurement.
**Carried from spec [0004](../specs/0004-first-traced-chain/index.md) (2026-10-05):** apply its locked rules unchanged to all five questions (start rule, matching rule, reason codes). Question 4 has no `trace` list and question 5's first entry is not a `spec NNNN AC-N` item, so decide how those two start. Question 5 passes through a feature row, and `pipeline.load()` writes no `SPECIFIED_BY` or feature `PART_OF` links yet. Spec 0007's two `Build plan` units share a section name, which `unit_for()` cannot tell apart.
spec [0006](../specs/0006-eval-runner/index.md) · code in `src/tracepath/report.py`, `src/tracepath/cli.py`, `eval/runner.json`
- [x] Design it (spec): `/architect eval runner` · how questions 4 and 5 start, and the held out questions
- [x] Build it: `/develop eval runner`
  - [x] The `eval` command, the hop 0 start marker, pass and fail per question, and question 3 reproduced from the artifacts at `36a6bc5` (AC-1 to AC-10c, AC-3)
  - [x] The new start rules and absence questions (question 4 and question 5) (AC-11 to AC-17e)
  - [x] The sidecar `eval/runner.json`, the evidence flags and the examples digest test (AC-18 to AC-21)
  - [x] The held out guard: refusal without `--release-held-out`, and its file tests (AC-24 to AC-28b)
  - [x] Gate: `extract --dry-run` over the eight units, then the engineer's go and ceiling, the paid step, and the first full run recorded in `experiments/0011-eval-runner/` (AC-31 to AC-34)
  - [x] The two held out questions, written in a fresh session and committed before feature 13 starts (AC-22, AC-23, AC-30)
- [x] Verify it: `/check verify eval runner`
- [x] Test it: `/test eval runner`

### 15. Question to start item · dropped, folded into feature 16
_Folded into feature 16 on 2026-10-19. Typing a question in plain English is now part of the v1 answer feature. The text below is kept as history, and its two steps are not planned separately._
Let a person type a plain English question and get a start item for the walk, instead of typing an item id. Two steps, so the thin version ships before the whole corpus exists. Prose answers stay deferred, deliberately. Feature 6 and its spec 0006 are unchanged: the eval runner keeps the start each question gives, and the slices measured before feature 9 keep their given start.
**Step 1, right after feature 6.** The user types a question, the tool shows its top 3 candidate start items from the current graph with their text, and the user picks one (or it takes the first) before the walk runs. Simple matching, not tuned on any eval question.
**Done when (step 1):** typing a plain English question shows the top 3 candidate start items from the current graph with their text, the user picks one or takes the first, and the walk then prints the cited chain; when no candidate matches, the output says so plainly and offers no start; the command works without the eval set; the matching is simple, was not tuned on any eval question, and the same question gives the same candidates.
**Step 2, after feature 9.** Revisit the matching against the whole corpus, then score it on the eval questions and the sealed held out questions.
**Done when (step 2):** before revisiting the matching, a written success bar is committed (for example, the right start is in the top 3); the matching is then revisited against the whole corpus and scored on the five eval questions and, once features 13 and 11 have committed their choices, on the sealed held out questions released with `--release-held-out`; every matching change is committed before the held out run; each result is reported one by one, as a check, never a rate.
- [ ] ~~Design it (spec): `/architect question to start item`~~ · folded into feature 16

## Answer at question time (v1)

### 16. Answer at question time · in progress
The engineer types a why question in plain English. The tool finds the graph items that bear on it, asks the model to answer using only those items, and prints the answer with every claim citing a graph item. A link the model inferred rather than read in the text is printed marked as inferred. This takes in feature 15 (question to start item). It does not need the walk to cross a document boundary, which is where all seven questions run so far fail.
**Done when:** the new v1 line holds: a plain English question prints an answer whose every claim cites a graph item, and any inferred link is marked as inferred; and the success bar is met or reported as missed (see the v1 finish line): at least 4 of the 5 eval questions and at least 3 of the 4 held out questions answered right, each judged by the engineer against its expected answer.
**Rules set 2026-10-19, before design:**
1. Eval questions 1 to 5 may be used to adjust the prompt. The four held out questions run once, at the end, after every adjustment is committed, and are never used to adjust anything.
2. If the bar is missed, v1 still finishes, reported as it is with each failing question's cause.
3. The hand prototype's one partial result (question 3, retrieval missed 0007 AC-12) is a hint about retrieval, not a decision. How items are found is for `/architect`.
4. No paid call without a measured estimate from a measured per call cost and the real number of calls, then the engineer's go. Every paid call goes through the existing guards.
5. The held out set's limit stands: its four questions sit in records 0004, 0010 and 0016 to 0018, so a pass there is a narrow check.

spec [0009](../specs/0009-answer-at-question-time/index.md) · code in `src/tracepath/ask/`, `src/tracepath/extract/metered.py`, `src/tracepath/cli.py`
_Design decided 2026-10-19: one call to Claude Sonnet 5.5 over one pack of up to 90 items; code picks the search words; the second look is dropped and kept as a Follow-up in the spec._
- [x] Design it (spec): `/architect answer at question time` · decide how items are found, how the model is asked, how a claim cites an item, and how an inferred link is marked
- [ ] Build it: `/develop answer at question time`
  - [x] Retrieval and `ask --dry-run`, no model (spec 0009 AC-2 to AC-14b) · built 2026-10-19, code in `src/tracepath/ask/retrieve.py` and the `ask` command in `src/tracepath/cli.py`; `ask --eval N` exits 1 as not built until the eval wiring milestone
  - [x] The answer type, prompt and claim checks (AC-15 to AC-20) · built 2026-10-19, code in `src/tracepath/ask/answer.py`, prompt version `ask-1`
  - [x] The guarded call and the record in `metered.py` (AC-21 to AC-28) · built 2026-10-19, code in `src/tracepath/extract/metered.py` (`ask_metered()`), `ask_bound()` in `src/tracepath/extract/cost.py`, `src/tracepath/ask/record.py`; tested with a fake call, no paid call made
  - [x] Gate: dry run over the five eval questions, the engineer's go and ceiling, then question 1 alone to measure one call's cost · done 2026-10-19: dry run bounds $0.1741 to $0.2086 (inputs 7,045 to 24,315 tokens); question 1 run once at ceiling $0.25, 22,681 in, 402 out, $0.0494 against its $0.2054 bound, record `artifacts/asks/2026-10-19T21-08-46Z-why-does-the-landing-rule.json` (`f7dbc7c`)
  - [ ] Eval wiring (`--eval`, the held out refusals, the one run guard; AC-29 to AC-33)
  - [ ] Eval questions 1 to 5, one per command, prompt tuning allowed; the engineer freezes the prompt
  - [ ] Held out questions, once each, after the freeze; result reported against the bar
- [ ] Verify it: `/check verify answer at question time`
- [ ] Test it: `/test answer at question time`

## Slice 3: Name resolution

### 7. Name resolution · needs a decision · after v1 (moved 2026-10-19)
_Moved after v1 on 2026-10-19 as a retrieval improvement._
Match records that name the same thing by number, nickname, or file name, so a chain doesn't quietly break across names. When a match isn't confident, the name is marked unresolved and shown, never guessed.
**Done when:** a chain whose links use different names for the same record resolves correctly, and an uncertain match shows up as unresolved in the output.
**Eval count, 2026-10-08** (see feature 13): not measurable from eval output, which prints no chain (spec 0006 AC-9c); question 5's three `no_link` items are the likely cases, to confirm with `trace --eval 5 --with-held`. Spec [0006](../specs/0006-eval-runner/index.md) expects question 5's "feature 21" reference to need it once the held items are released.
- [ ] Design it (spec): `/architect name resolution`

## Slice 4: History aware traversal

### 8. History aware traversal · needs a decision · after v1 (moved 2026-10-19)
_Moved after v1 on 2026-10-19 as a retrieval improvement._
Follow supersession, amendment, and correction correctly. A fact that was later replaced must never come back as current.
**Done when:** a chain that crosses a superseded or corrected record shows the replacement as current and marks the older one as history.
**Known risk, recorded 2026-09-23 from the first real extraction runs:** extraction can keep a struck claim and lose its replacement, storing both as one span marked struck, so the current fact arrives already labelled obsolete. Measured on bullet 3 of spec 0012's `## Consequences`, 1 of 3 runs at `medium` effort and 2 of 3 at `low`. Only run disagreement caught it, which is not a guarantee. This row's Done when must hold against that input, not just against a correctly split one. See spec [0002](../specs/0002-data-model/index.md) `## Consequences` and [experiment 0002](../../experiments/0002-effort-low-fidelity/README.md).
**Handoff from spec [0004](../specs/0004-first-traced-chain/index.md) (2026-10-05):** the first walk stops at a whole Record and prints only the stored `struck` flag. Finding the replacement inside a Record that a supersession link lands on, and showing it as current, is this feature's job.
**Eval count, 2026-10-08** (see feature 13): one question touches it, question 3, through its struck test scenario in the default view; none in the held view's `not reached` items.
- [ ] Design it (spec): `/architect history aware traversal`

## Slice 5: Whole corpus

### 9. Whole corpus · done
Extend extraction from the hand picked records to every record in the snapshot, rebuilt in one run. **Shape decided 2026-10-18: a full re extraction.** The whole corpus is extracted again, the 29 existing sections included, in one run on `claude-sonnet-5-5` with prompt `0003.1`. The old runs move to `artifacts/superseded/<date>-prompt-<version>/` with a `NOTE.md`, never deleted. Why: today 26 sections are on `claude-sonnet-5` across three prompt versions, so the graph mixes models and prompts, and the three `claude-sonnet-5-5` Requirements sections show zero run disagreements against 1 to 29 on `claude-sonnet-5`. That is a hint from 3 sections, not proof. Extracting only the missing records was the other candidate.
**Paid step:** no paid call is made until the build reports a measured estimate, from a measured per call cost and the real number of calls, and the engineer gives a go and a ceiling. Do not use a round number.
**Done when:** the full snapshot, less the 12 listed units, is ingested in one rebuild on one model and one prompt version, relationships that fit no named type appear as unclassified, not dropped, and the five eval questions are run and each result reported one by one under both readings in the v1 finish line. _Reworded 2026-10-18 from "all five eval questions pass": that was stricter than the v1 line, which asks for at least 3 of 5._ _Reworded again 2026-10-18 from "the full snapshot": the engineer chose to leave out the 12 units with text that `tracepath extract` cannot address today (see Deferred, unit address fix)._
**The 12 units left out, decided 2026-10-18.** The snapshot holds 254 units (spec 0002 AC-2); 240 are addressable, and 2 more are a heading only (`0007`'s first `## Build plan`, the scope's `## Foundation`). The 12 below hold text but cannot be addressed:
- Seven sections whose name repeats inside one spec, refused as ambiguous by `resolve_address()`: `0007`'s second `## Build plan` (4,717 characters, the real build plan), `0011`'s first `## Rationale` (1,263 characters), `0011`'s second `## Rationale`, and both `## Rationale` sections of `0013` and of `0014` (each a one line pointer to `rationale.md`).
- Five scope `Intro` units, which `resolve_address()` skips by design: the text above the first feature row in `Slice 1: Core loop thread`, `Slice 2: Ranking`, `v1 extras`, `v1.5` and `v2`.
- [x] Build it: `/develop whole corpus` · unblocked 2026-10-18 by spec [0008](../specs/0008-review-volume-and-routing-policy/index.md) AC-13: feature 11 adopted the narrow hold rule and the held view, and the queue holds 526 rows at 29 units, against 990 before

### 13. Extraction accuracy · in progress · from spec 0003
**Step one closed, later steps paused (2026-10-15).** Step one (spec 0007) is merged and accepted. The later steps wait until after v1, so this feature stays in progress, per the v1 finish line.
Whether extracted items are right, not only repeatable. Prompt `0003.1` failed the accuracy bar (experiment 0005's `data/method-notes.md`: at least two thirds of entity marks and of relationship marks per unit agree) on 3 of 6 results in [experiment 0006](../../experiments/0006-accuracy-bar-recheck/README.md) (`0015` entities 2/10, `feature-33` entities 5/10 and relationships 3/5), after 5 of 6 in experiment 0005; the bar's dropped link clause is unmeasured. Spec 0003 closed feature 12 without fixing this (AC-32 to AC-35) and lists the candidate causes in its Follow up: no written definitions for the eight entity types, splitting and label refinements, checkable facts left in rejected text, the workflow stage question, and the deliberate decision link. Its fix ladder: rules the model was never given, then prompt or example quality, then vocabulary gaps.
**Ordering:** after feature 6, so fixes are chosen by which gaps actually break eval chains. Before feature 11, because accuracy fixes change the prompt and so the review volume, and setting the routing policy first risks tuning thresholds around a defect, the same reason feature 11 waits on feature 12. Its order against features 7 (name resolution) and 8 (history aware traversal) is decided by feature 6's results: fix first whichever of unresolved names, history, or extraction accuracy breaks the most eval questions. Feature 5 is not blocked by it, and feature 10 (Slice 6) is unaffected. Spec 0002's vocabulary revisit Follow up (`8bcd9df`) is split (decided 2026-10-04): only the ruling of experiment 0008's one `0006 ## Feature design` sentence happens before feature 5, and it joins this feature's evidence; the full written definitions for the eight types stay here, after feature 6, chosen on evidence across all five eval questions.
**Evidence from feature 6, counted 2026-10-08.** Source: `experiments/0011-eval-runner/data/eval.txt` and `eval-with-held.txt` only. Each item that prints `not reached` is classed by its printed reason: `held_for_review` counts toward feature 13; an Unresolved node at the end of the walk toward feature 7; a `SUPERSEDED_BY` step or a struck item toward feature 8. When the printed reason is `held_for_review`, the reason decides, so a struck item with that reason counts toward 13. A struck item with any other reason counts toward 8. Anything else is listed as fitting none. Question 4 is `INCONCLUSIVE` and its two `not reached` items are the wanted outcome of an absence question, so it is listed but not counted.

Default view (`eval.txt`), items by class:

| Question | Result | Feature 13 | Feature 7 | Feature 8 | Fits none |
| --- | --- | --- | --- | --- | --- |
| 1 | FAIL | 2 | not measurable | 0 | 0 |
| 2 | FAIL | 4 | not measurable | 0 | 1 (`link_held`) |
| 3 | FAIL | 4 | not measurable | 1 (the struck test scenario, `link_held`) | 0 |
| 4 | INCONCLUSIVE | not counted (2 `held_for_review`) | not counted | not counted | not counted |
| 5 | FAIL | 4 | not measurable | 0 | 3 (`no_link`) |
| Items | | 14 | not measurable | 1 | 4 |
| Questions broken | | 4 | not measurable | 1 | |

Held view (`eval-with-held.txt`), `not reached` items only:

| Question | Result | Feature 13 | Feature 7 | Feature 8 | Fits none |
| --- | --- | --- | --- | --- | --- |
| 1 | FAIL | 1 | not measurable | 0 | 0 |
| 2 | FAIL | 4 | not measurable | 0 | 1 (`link_held`) |
| 3 | FAIL | 2 | not measurable | 0 | 0 |
| 4 | INCONCLUSIVE | not counted (2 `held_for_review`) | not counted | not counted | not counted |
| 5 | FAIL | 3 | not measurable | 0 | 3 (`no_link`) |
| Items | | 10 | not measurable | 0 | 4 |
| Questions broken | | 4 | not measurable | 0 | |

Corrected 2026-10-09: the feature 7 column is not evidence. `eval` prints no chain (spec [0006](../specs/0006-eval-runner/index.md) AC-9c), so an Unresolved node can never appear in `eval.txt` or `eval-with-held.txt`, and a count of 0 there would be true whatever the graph holds. Feature 7 is not measurable from eval output. Question 5's three `no_link` items are the likely feature 7 cases (its prediction names the unresolved "feature 21" node). Confirm with `uv run tracepath trace --eval 5 --with-held`, which prints the chain, before features 7 and 8 are ordered. In the held view, question 3's three `held only` items (two struck, one reached through a `SUPERSEDED_BY` step) are not `not reached`, so they are outside this count. Counted anyway, feature 8 would touch question 3 only, one question, and the order would not change.

**Queued next, 2026-10-08:** this feature, by the rule above. It breaks 4 of the 5 questions in both views, against 1 for feature 8 (default view only); feature 7 is not measurable from eval output (see the correction above). The queue is unchanged. One caution carried with it: `held_for_review` is the output of the routing rules, so the count shows that held items break the chains, not yet that an extraction defect holds them. Whether the cause is accuracy or the routing policy of feature 11 is part of the design question here, and the committed numeric criterion (Guard, below) must say which it is testing.

**Order decided 2026-10-09: this feature goes before feature 11.** The engineer chose it after a read only count (no API call) of the held items on eval questions 1, 2, 3 and 5, from `load --with-held` and `trace --eval N --with-held`, matched to `artifacts/review-queue.json` by entity id. Reasons: (1) the scope's own reason above, routing set first risks tuning thresholds around a defect. (2) The count: 21 held entities and 14 held links are held only by a flag while the three runs agree, against 5 entities and 11 links where the runs disagree; 20 of the 21 flag only entities carry `multi_condition_split`. (3) Question 3's middle step, `0002#requirements:6` and both of its links, is held because the runs disagree, so a routing policy alone cannot open that path. (4) Runs agreeing shows repeatability, not correctness, so flag only items are released only once their accuracy is measured. Engineer rulings on question 3's two flag only items: `0002/AC-10` agreed, `0007/AC-13` unsure (both `gap:bundled-ac`, detail in the engineer's ruling card). Steps in order, each measured alone on fresh units: first the model switch to `claude-sonnet-5-5` and the code pass below (decided and designed in spec [0007](../specs/0007-extraction-accuracy/index.md), measured by comparing the pass off and on over the same runs), then the flag question (whether `multi_condition_split` is raised too often, not decided), then type definitions and splitting rules, the last two designed in a later spec or amendment from the rulings made in 0007, each with fresh units chosen beforehand. This feature's Done when still requires its final state to meet the bar. Candidates: whether `multi_condition_split` is raised too often; and a code pass, decided 2026-10-09 and designed in spec [0007](../specs/0007-extraction-accuracy/index.md) (a read only check found the parser and all 9 model runs agree exactly on criterion entities in `0002`, `0008` and `0021` Requirements). **The code pass narrows a hold, so feature 11 starts from it:** for a parsed, unstruck bullet in a Requirements section whose three runs agree on its id and type `AcceptanceCriterion`, a `multi_condition_split` flag alone no longer holds the entity; the entity keeps the flag and is stamped `accepted_by` `code_pass`. Any other flag, and `runs_disagree`, still hold it. Spans, rejected spans, other entities, links and struck bullets stay with the model. It is off by default (`--code-pass`) until a measured result passes, and the count of items it releases is in each report. `struck: false` on `0002/AC-10` is a separate `/debug`. A routing policy is still written from review queue evidence across all units and committed before any question is rerun.

**Guard, set 2026-10-06** (see feature 5): this feature may still choose which causes to fix from feature 6's results, but it commits a written, numeric criterion for when a fix succeeds before trying any fix; git order proves it came first. The held out questions (feature 6) are committed before it starts and stay unrun and unread until this feature and feature 11 have both locked their choices.

**Held out questions, noted 2026-10-07 from spec [0006](../specs/0006-eval-runner/index.md):** no worked example and no prompt change may draw on a section cited by `eval/held-out.json` (spec 0006 AC-25 tests the examples). This feature re checks the evidence flags in `eval/runner.json` whenever it edits `examples/`, because spec 0006 AC-20's digest test fails until they are re checked. Running the held out questions is `tracepath eval --eval-file eval/held-out.json --release-held-out`, and only once this feature and feature 11 have both committed their choices. Extracting their sections is the one paid step: a measured estimate first, then the engineer's go.
**Done when:** each cause in spec 0003's Follow up is fixed, ruled out, or carried as a recorded decision; any prompt change is re checked on fresh held out units against the same bar, with the dropped link clause measured this time; and either the bar passes, or the remaining gap is measured on the eval questions and accepted in a spec.
**Paused decision, recorded 2026-10-13 (v1 finish line):** this feature's later steps (the flag change and the type definitions) are paused. For v1, step one closes after the engineer's stage one rulings, whatever their result, with no fourth unit and the code pass left off. Whether the later steps run, and when, is decided after v1. Until then this Done when is not required for v1.
spec [0007](../specs/0007-extraction-accuracy/index.md) (step one: the model switch and the code pass) · amends spec [0001](../specs/0001-stack-and-architecture/index.md) and spec [0002](../specs/0002-data-model/index.md) · code in `src/tracepath/extract/`, `src/tracepath/rebuild.py`, `src/tracepath/cli.py`
- [x] Design it (spec): `/architect extraction accuracy` · step one only; the flag change and the type definitions are designed in a later spec or amendment from this step's rulings
- [x] Build it: `/develop extraction accuracy`
  - [x] The model switch, with its spec 0001 amendment, per model rates and `--expect-model` (AC-1 to AC-5f, AC-29, AC-31e)
  - [x] The code pass, behind `--code-pass`, with its spec 0002 amendment (AC-6 to AC-17, AC-34)
  - [x] The units list, the committed gate and the free token count, then the engineer's go for the first paid call (AC-19 to AC-19i, AC-22 to AC-24, AC-31 to AC-32)
  - [x] The sampler, the blind packet and the scoring, after the paid extraction (AC-18 to AC-28e, AC-29b, AC-30)
- [x] Verify it: `/check verify extraction accuracy`
- [x] Test it: `/test extraction accuracy`
- [ ] Later steps (flag change, type definitions): `/architect extraction accuracy, later steps` · after step one's rulings, each with fresh units chosen beforehand

### 11. Review volume and routing policy · done · from spec 0002
How much the routing rules should hold back, decided on logged evidence rather than on feel. Measured over the 8 units extracted so far: **403 queue rows against 71 accepted entities**, by reason `runs_disagree` 340, `endpoint_not_accepted` 98, `known_trap_flag` 77, `unclassified_type` 1, and concentrated in the heterogeneous units (0012 122, feature-21 114, 0021 76, 0006 53, 0008 38). Extrapolated across 188 sections that is thousands of rows with one reviewer, which is not a workable review step. HANDOFF's own plan was always to loosen routing once logged review decisions showed where it over flags; `artifacts/review-log.json` now exists and is empty, so that evidence can finally start accumulating. Measure the accept to review ratio **per unit kind**, since the counts above say the problem is concentrated rather than uniform, then decide a loosening policy. Two things this must not do: loosen the comparison itself, which spec 0002 names as the one change that would put unverified items into the graph, and treat near duplicate queue entries from AC-11a's line sensitivity as extraction defects. Spec 0002's AC-11(d) adds no rows today and is not the cause. **Added 2026-09-23**: neither is AC-11(e), but it is not nothing either. Spec 0002's AC-7 amendment puts a `label` into the comparison signature, model produced text and a new source of run to run disagreement the same way flags were; the 403 against 71 count above was measured before that lands (feature 4's build plan tasks 16 and 17, unbuilt). Re measure after those land, not before, or this feature's per unit kind ratio is measuring a signature that no longer exists.
**Two candidate framings, both open.** Weigh them against each other rather than starting from the first.

1. **Tune the routing.** The queue is the right mechanism and its thresholds are wrong. Measure the ratio per unit kind, loosen where the evidence says it over flags, keep a person in the loop.
2. **Question whether the queue belongs here at all.** This project's standing rule is "no verification layer, because the visible chain is the check", and a human queue of this size is a verification layer. It came from the reference pipeline, which was hand run in a learning workspace at a scale where a person really could rule on every row, rather than from this project's own rules. The alternative to weigh is writing items with their confidence recorded and letting a chain display a disputed step, which is exactly how `unclassified`, `:Unresolved` and `UNCLASSIFIED` links already work: uncertainty is visible in the chain instead of blocking it. Note the tension to resolve either way, spec 0001 currently lists the review queue as _matching_ the visible chain rule, but does so on the grounds that its files are plain diffable JSON, which is a claim about the file format and not about whether a person must clear a queue before a chain can be read.

**Feature 12 comes first.** 340 of these 403 rows are `runs_disagree`, and feature 12 tests whether that rate is an artifact of an exampleless prompt and an over broad unit definition rather than a property of the corpus. Setting a policy before that answer risks tuning thresholds around a defect, so weigh this one knowing whether the disagreement is fixable at source.

**Decided on eval evidence, not on argument.** Both framings are arguable from first principles and neither wins that way, so the tie breaker is what the eval actually returns. This needs feature 6 first: once the eval runner exists, run the five eval questions under **both** policies, review gated and write everything with its status recorded, and record which chains break under each and how. A chain that is right under one and wrong or absent under the other is the evidence; a chain that is identical under both says the queue is not what decides that answer. Run it before writing the spec, not after, so the spec records a measurement rather than a preference.

**Guard, set 2026-10-06** (see feature 5): the order stays feature 6, then 13, then this one, and this feature still sets the real policy. It commits its decision rule before running either policy; git order proves it came first. A status view of held items (feature 14) now exists while framing 1 has no build, so the committed rule must weigh both framings on equal terms, not favour the one already built. The held out questions (feature 6) check the chosen policy only after this feature and feature 13 have both locked their choices.

**Held out questions, noted 2026-10-07 from spec [0006](../specs/0006-eval-runner/index.md):** the held out questions are run with `tracepath eval --eval-file eval/held-out.json --release-held-out`, only once this feature and feature 13 have both committed their choices. Extracting their sections is the one paid step: a measured estimate first, then the engineer's go.

Before the held out questions are run (eval --eval-file eval/held-out.json --release-held-out, once features 13 and 11 have locked their choices), the engineer reads both questions and checks each expected chain step against the corpus at 2e40bcf, the way extracted items are ruled; any correction is committed before the first run, so the result cannot shape it. Until then the tests verify only their form (AC-22, AC-24 to AC-26, AC-30), not whether their expected chains are right.

**Done when:** the accept to review ratio is measured per unit kind, the five eval questions have been run under both policies with the broken chains recorded, both framings are weighed on that evidence, a policy is decided and recorded in a spec, and feature 9 is unblocked or explicitly allowed to run at the current ratio.
spec [0008](../specs/0008-review-volume-and-routing-policy/index.md) · code in `src/tracepath/extract/compare.py`, `src/tracepath/rebuild.py`, `src/tracepath/hold_ratio.py`, `src/tracepath/cli.py`
- [x] Design it (spec): `/architect review volume and routing policy` · the decision rule and both candidates' exact conditions are committed; which, if either, is adopted is recorded in a later amendment once `/develop` measures them
- [x] Build it: `/develop review volume and routing policy`
  - [x] The per unit kind ratio script and the narrow hold release mechanism, wired through `load`, `eval`, `trace --eval`, and `review-queue` (AC-1 to AC-7)
  - [x] The four way comparison script, run with `--code-pass` off throughout, producing the per step table and noise counts (AC-8 to AC-8f)
  - ~~The gated blind ruling, only if the comparison table triggers it (AC-9, AC-10 to AC-10e)~~ · withdrawn, see the 2026-10-17 dated note in spec [0008](../specs/0008-review-volume-and-routing-policy/index.md)
  - [x] Whichever default flips, each preceded by its own spec amendment commit, or the explicit fallback statement (AC-10f, AC-11, AC-11b, AC-12, AC-13)
  - [x] The result recorded in `experiments/`, and this spec amended with the outcome (AC-14)
- [x] Verify it: `/check verify review volume and routing policy`
- [x] Test it: `/test review volume and routing policy`

## Slice 6: Rationale and alternatives

### 10. Rationale extraction and alternatives · needs a decision · from spec 0002
Widen extraction to each spec's `rationale.md`, with an `Alternative` entity type for an option a spec weighed: what it was, whether it was chosen, and the reason. A census inside spec 0002 found that 9 of 20 plausible questions across four specs need `rationale.md`, and every one of them asked about an alternative the spec rejected. Two limits to settle here rather than assume: an outcome is not only chosen or rejected (spec 0012's rationale says "Anthropic is parked, not rejected"), and `Alternative` answers "why this one over that one" but not "what was the decision before, and why did it change" (0012's vendor pick was re-decided in place and the old version is kept nowhere else). That second shape stays open alongside a `Claim` type.
**Done when:** a "why not X" question returns a chain that reaches the rejected option and its reason, each link citing its record, and an option whose outcome fits neither chosen nor rejected is visible as such rather than forced into one.
- [ ] Design it (spec): `/architect rationale extraction`

### 12. Extraction stability on heterogeneous units · done · from spec 0002
**Two questions now, not one.** Whether the run to run disagreement is a fact about the corpus or a fixable defect in how units are cut and prompted, and whether a worked example fixes the AC-7 labelled reference path specifically, since [experiment 0004](../../experiments/0004-label-round-trip/README.md) found a concrete, separate cause for that one: `SYSTEM_PROMPT` (`client.py` lines 65 to 66) mentions `label` only from the reference side, "the same `label` you would give that item as an entity", which assumes an entity labelling instruction that exists nowhere in the prompt. That is why a real run of spec 0001's binding rule 6 and its reference from `0008`'s preamble never matched: the reference wrote `label: "binding rule 6"` stably three times, the entity that is binding rule 6 never wrote a `label` at all.

It is the single largest cost in the pipeline: 340 of the 403 queue rows were `runs_disagree`, before feature 4's build plan tasks 16 and 17 landed. **Added 2026-09-23**: those tasks are built, `AC-11e` now puts a `label` into the comparison signature, and the queue stands at **464 rows across 9 units** (`artifacts/review-queue.json`, rebuilt the same day). Run the prompt examples experiment this feature is built on against the current 464, not the pre amendment 403; the earlier figure was recorded under a signature that no longer exists.

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

**The second question: does a worked example make the labelled reference path round trip.** Not a candidate cause of the disagreement rate, a separate, concrete defect experiment 0004 already isolated: nothing in `SYSTEM_PROMPT` positively instructs the model to set `label` on an entity, only on a reference naming one. Six worked examples already exist at [`examples/`](../../examples/), one per unit kind, and two demonstrate entity labelling directly: `0006-feature-design.md` sets `label` on `TestScenario` entities named `Happy path` and `Font licence`, and `0008-preamble.md` uses the reference side's `label` for binding rule 6, the exact pairing this feature needs. So the fix (an explicit entity label instruction) and its test (these examples) arrive together, rather than needing separate authorship.

**What running this owes, concretely, once designed:**
1. Add an explicit entity label instruction to `SYSTEM_PROMPT`, not only the reference side's, so the two halves of AC-7's contract are both asked for.
2. Add the worked examples (the six already drafted, entity labelling among them).
3. Bump `PROMPT_VERSION` from `0002.3`.
4. Wire prompt caching for the fixed prefix: the examples block measures about 27,000 tokens, roughly **$0.054 per call uncached**, about **$30** across a 564 call whole corpus run (feature 9) against roughly **$3 cached**. Caching is not optional at that spread.
5. Run spec 0001's `## Binding rules` section and `0008`'s `Preamble` again, the same two units [experiment 0004](../../experiments/0004-label-round-trip/README.md) used, to prove the round trip against the same evidence base rather than a new one. Budget **about $1**, the same measured figure that run cost, plus a cushion: that run's own output ran 94,264 tokens against 38,000 input, output heavy enough that size based interpolation underestimated it by about 10%; the worked examples block will add further fixed input cost on top.
6. Add a test that validates every worked example's JSON against `extraction_json_schema()`, so a stale example cannot teach an invalid shape silently.

**Two methodological constraints on every before and after run this feature makes, not only the label question.**

1. **Held out measurement.** The six worked examples are drawn from `0012 ## Follow-up`, `0012 ## Build plan`, `0012 ## Consequences`, `0008`'s Preamble, the `feature-21` scope row, and `0006 ## Feature design`. Any before and after comparison must run on units that appear in **none** of them, or it measures memorisation rather than learning: the model would be scored on how well it copies a demonstration it already saw, not on whether the rubric generalises. Pick equivalents from other specs, for example `0021 ## Requirements` (confirmed present, unused elsewhere in the examples), a `## Feature design` from `0013` or `0014` (both confirmed present), and a different scope row than `feature-21`. State in the experiment's own README which units were held out and why, the same way experiment 0004 named its two units.
2. **Agreement is not accuracy.** Adding examples will reduce run to run disagreement almost by construction, because the model copies the demonstrated cut, not because the cut is right. The examples encode one authoring session's reading of the rubric, and three runs agreeing on a wrong reading is not progress. So the disagreement rate cannot be the only measure: take a fixed sample of items from the after run, about 10, and have the engineer rule on each against HANDOFF's three question test (atomicity, referenceability, right sizing, `reference/HANDOFF.md`) and the deletion trick, recording how often the engineer's own ruling agrees with the model's. Report both numbers side by side. **The failure case this guards against**: a disagreement rate that falls while the engineer's agreement also falls, meaning the examples taught the model to converge on the wrong answer more confidently, which a disagreement rate alone would read as success.

**Ordering: this runs before feature 11 decides.** Feature 11 is choosing a policy for a disagreement rate whose cause is unknown, and the two answers differ. If the rate is largely an artifact of an exampleless prompt and an over broad unit, the honest fix is at source and the policy question shrinks with it; if the rate survives both fixes, it is a real property of the corpus and feature 11 is choosing how to live with it. Deciding the policy first would risk tuning thresholds around a defect. This feature needs no eval runner, so it is not blocked behind feature 6 the way feature 11 is, and it can start now.

**If examples change the prompt, AC-14's verdict has to be re-earned.** `PROMPT_VERSION` bumps from `0002.2`, and every agreement figure behind AC-14 was measured under the no examples prompt, so it says nothing about the new one. Re-run AC-14's coverage set under the new prompt to confirm the four new types (`Consequence`, `FollowUp`, `BuildStep`, `TestScenario`) still come back stably. Budget **about $3.30**, not the $2.70 the older figure suggests: the coverage set is 8 units and 24 calls since `## Feature design` joined it in the 2026-09-23 amendment, and that unit costs about $0.22 per call against $0.1268 for the rest (21 calls at $0.1268 is $2.66, plus 3 at $0.2198 is $0.66). Record the result as a new experiment with a forward pointer added to experiment 0001, never by editing experiment 0001's own numbers: it is the record of what the old prompt did, and overwriting it would destroy the only before half of the comparison.

**Done when:** both causes are tested against a real second run of one unstable unit, with a before and after table in `experiments/`, and the result either changes the prompt, changes AC-2's unit definition, or is recorded as not the cause. If the prompt changed, AC-14's coverage set has been run again under the new `PROMPT_VERSION` and the four new types still come back stably, **and** spec 0001's `## Binding rules` section and `0008`'s `Preamble` have been run again and the labelled reference now resolves to the entity, with the result recorded against experiment 0004's evidence rather than as a fresh, disconnected measurement. Spends API money: roughly $0.70 per three run configuration at `medium` on `0006 ## Feature design`, measured, plus about $3.30 if the AC-14 set is run again, plus about $1 for the label round trip check, plus the prompt caching setup cost noted above, so confirm the number of configurations before running.

> **AMENDED, 2026-09-24, by spec [0003](../specs/0003-extraction-stability-heterogeneous-units/index.md).** Kept in full above rather than rewritten, since it recorded real evidence at the time. Two things changed once the spec was actually designed. First, the labelled reference defect turned out not to be a missing worked example at all: binding rule 6 carries no verbatim self label anywhere in its own text, so AC-7 (spec 0002) was missing a rule, not the prompt missing a demonstration. The fix is a deterministic pre check, proven by rebuilding the committed `0002.3` artifacts, no paid re-run of spec 0001's `## Binding rules` section and `0008`'s Preamble needed for that part. Second, the AC-2 heterogeneity cause is now conditional rather than unconditionally run: spec 0003 tests it only if the heterogeneous held out unit's after run entity count spread exceeds 2 (the widest spread any stable committed unit showed); at or below that, the experiment README records the prompt fix as sufficient, with the numbers, and AC-2's unit definition is not touched by this feature. Spec 0003's own `verify.md` carries the current, formula based cost estimate; the dollar figures above are what was known before design, not a live number to run against.
- [x] Design it (spec): `/architect extraction stability on heterogeneous units` · spec [0003](../specs/0003-extraction-stability-heterogeneous-units/index.md)
- [x] Build it: `/develop extraction stability on heterogeneous units`
  - [x] Label pre check for `## Binding rules`, proven with no paid call, spec 0002 amended (AC-1 to AC-5, AC-12) · spec 0003 build plan tasks 1 to 4 · built 2026-09-24, code in `src/tracepath/extract/precheck.py` (`read_binding_rules`), `src/tracepath/extract/ids.py` (`label_binding_rules`), called from `pipeline.py` and `rebuild.py`; tests in `tests/test_binding_rule_labels.py` and `tests/test_extract_precheck.py`. Rebuilt from the committed `0002.3` runs, `binding rule 6` resolves to one entity on the rule's opening line in all three runs, and is accepted as `0001#binding-rules:10`. `0008`'s reference to it now matches that entity, but the link stays held under `endpoint_not_accepted` on its other endpoint, `0008/AC-10b`, which is not accepted. The review queue was rebuilt and still holds 464 rows; 2 signatures gained a label (rules 1 and 4)
  - [x] Prompt content: schema sample fix, stale caveat removed, rules lifted and assembled, few shot block wired, `PROMPT_VERSION` bumped, example validation test, 1 hour cache breakpoint (AC-6 to AC-11, AC-19) · spec 0003 build plan tasks 6 to 11 · built 2026-09-24: `PROMPT_VERSION` `0003.0`, one assembled `RULES` list plus the six examples' Input and Output in filename order (`src/tracepath/extract/examples.py`, `client.py`), the `0006` excerpt note, a 1 hour cache breakpoint on the system block, and cache write and read counts recorded on every attempt and artifact; tests in `tests/test_extract_examples.py`. The assembled system prompt is 118,651 characters and **45,899 tokens**, measured with the token counting endpoint, not the 27,000 the scope estimated. AC-19's live check (the second call reads the cache) is owed by the first paid `0003.0` run
  - [x] Fresh `0021` baseline, the run manifest cost confirmed, held out before/after runs (AC-13, AC-14, AC-15, AC-20) · **baseline done 2026-09-24** (build plan task 5): 21 / 21 / 21 entities, relationships 33 / 41 / 35 with 26 relationship rows under `runs_disagree`; $0.6918 recorded for 4 attempts (one schema failure, retried), and that figure undercounts, since the failed attempt's artifact records 5 output tokens (an `extract_once` defect, to go to `/debug` on its own `fix/` branch after this feature). The `0002.2` runs moved to `artifacts/superseded/2026-09-24-prompt-0002.2/`. Manifest measured (task 12, `experiments/0005-held-out-prompt-examples/data/prefix-count.json`, calibrated 7,252 counted against 7,254 billed): 39 remaining calls, $9.28 central, $10.57 wider margin; the engineer approved the 15 held out calls only ($3.60 central, $4.46 wider). **Held out runs done 2026-09-24**, $3.3652 spent against that $3.60 (befores B $0.4776, C $0.4276; afters A $1.2139, B $0.6693, C $0.5768), AC-19 confirmed live (call 1 wrote 49,114 cached tokens, every later call read 49,114). Before → after, `experiments/0005-held-out-prompt-examples/data/heldout-table.json`: A `0021` entities 21/21/21 → 29/29/28, relationships 33/41/35 → 9/7/8, relationship `runs_disagree` 26 → 10; B `0013 ## Feature design` entity spread 14 → 3, relationship `runs_disagree` 63 → 9; C `feature-9` entity spread 6 → 3, relationship `runs_disagree` 44 → 15. The 24 call type coverage set is not yet approved
  - [x] Label invention check, engineer accuracy ruling, AC-2 heterogeneity trigger decided (AC-16, AC-17) · label invention check done 2026-09-24: 0 model set labels outside their own span across all nine held out after runs (B's 27 are all verbatim). AC-17 **triggered**: group B's after spread is 3, above 2; the AC-2 test is not run, its measured estimate awaits a fresh go ahead. Engineer ruling owed on `experiments/0005-held-out-prompt-examples/data/ruling-sheet.md`, 55 items tallied in three separate sections: 10 entities and 5 relationships per group, plus, for group A only, 10 of the 50 links the `0002.3` befores wrote and no `0003.0` after wrote, each with its source text (`report.py tally` counts them). **Held until that ruling is in**: the AC-2 test and the type coverage set. **Done**: the ruling finished and tallied (`5dd4913`, `3458661`), the bar set (`f010066`); AC-17 decided, the AC-2 test not run (spec 0003 AC-31, `c066e19`; experiment 0005's README, `92d401a`); the type coverage set has since run (next milestone)
  - [x] Type coverage set re run, graph and review queue rebuilt (AC-18) · done 2026-10-04: experiment 0008 (estimate `8c7e71f`, runs `ba1f81a` and `184ad34`, README `78a5570`), judged by AC-36 to AC-38: three sections pass, `0006 ## Feature design` fails AC-37, routed by AC-39 to spec 0002's Follow-up (`8bcd9df`); review queue rebuilt to 416 rows (`da5005d`), graph rebuilt through `tests/test_reload_artifacts.py`, CI green on `da5005d`
- [x] Verify it: `/check verify extraction stability on heterogeneous units`
- [x] Test it: `/test extraction stability on heterogeneous units`

## Deferred
Out of scope for the current build pass, kept so the plan stays honest.
- **Prose answers**: generated prose written over the chain · needs a decision · _2026-10-19: no longer deferred; feature 16 prints a cited answer for v1_
- **Visual UI**: a graphical view of chains · needs a decision
- **Dashboard**: none planned for a single user project
- **Agentic traversal comparison**: a separate later experiment set against this traversal · needs a decision
- **Two stage typing**: can a calibrated classifier (e.g. typesafe.ai's Jev, classifier.dev) reduce type and flag churn? Claude segments a unit into spans and relationships; a classifier assigns the entity type from the closed enum with a confidence, and low confidence maps onto unclassified and the review queue. Would amend spec 0001's extraction row and add a second provider. Revisit after feature 5, measured by the eval, as an experiment under `experiments/` · needs a decision
- **Cross model extraction experiment**: can another model (candidates named by the engineer: Luna 6 or 6.1, GLM 5.3 Flash) do the same extraction cheaper, at the accuracy feature 13 sets? Run zero shot with the same prompt and schema, scored against the engineer's rulings and the eval, never against Claude's output, and never trained on Claude's extractions (Commercial Terms D.4, see `docs/session-notes.md`). Measured as cost per accurate unit, not per token. Needs: every paid call goes through the same ceiling and per call bound as `tracepath extract`, and the vendor's own docs are checked for price, structured output support, and terms. After feature 13 · needs a decision
- **Routing gap, after v1 (from the 2026-10-15 to 17 advisor notes):** a `known_trap_flag` hold comes only from the first run's flags (`compare.py`), so an item flagged only in run 2 or 3 is accepted outright. Mostly moot now that the narrow hold rule is the default. Fix it, or document it, after v1.
- **Unit address fix, from feature 9 (2026-10-18):** two of the 12 units feature 9 leaves out carry real content, `0007`'s second `## Build plan` (4,717 characters) and `0011`'s first `## Rationale` (1,263 characters). Extracting them needs an address that can name one of two same named sections, for example by its section slug (`0007:build-plan-2`), which changes spec 0004's Commands table and `resolve_address()` · needs a decision
- **Random audit of auto accepted items, after v1:** a small, periodic, random sample of items accepted by `narrow_hold` and by plain agreement, ruled by the engineer, to track accuracy over time (the pattern behind AWS A2I's random sampling). Feature 13's 20 item check is below the roughly 100 that error analysis guidance suggests. Not v1, and it must pass the filter for new checks before it is built · needs a decision

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
