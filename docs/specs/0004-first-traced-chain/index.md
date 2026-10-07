# 0004. First traced chain

**Date**: 2026-10-05
**Status**: In Progress

## Summary

This spec builds the walking skeleton: three new terminal commands that take four sections of JobHunt's specs from text to a printed chain, with every step real. `extract` runs the model on the sections the chain needs, `load` rebuilds the graph from the saved run files, and `trace` walks from one item along whatever links exist and prints each step with its source and the prompt version that produced it. The test is eval question 3 ("Why is password sign in impossible on production?"), chosen because no worked example in the prompt touches it. The rules for the walk, the start item, the pass rule and the predicted result are written down and locked here, before any paid call, so a pass means the mechanism works and not that the test was fitted to one question. An amendment on 2026-10-06, after the first result, makes the spending ceiling a hard guarantee per call, lets a dry run price units already extracted, and lets `extract --resume` complete a unit whose one pass was cut short. It revises the locked AC-48, and the Held out discipline section says why.

## Requirements

**User stories**:
- As the project's author and only user, I want to run one command and see the chain behind a "why" question, each step citing its record, so I can judge the answer by eye.
- As the person who will trust this result, I want the walk's rules, the pass rule and my prediction fixed before the run, so a good result cannot come from adjusting the test.
- As the person paying for extraction, I want a measured estimate, a spending ceiling and a stop before any paid call that could collide with an existing file, so no run costs more than I approved.
- As the person reading a chain, I want every step to say which prompt version made it, so a failing chain is not blamed on the walk when an older prompt section is the cause.

**Acceptance criteria** (the contract, one independently checkable claim each):

**The question and its record**

- **AC-1**: Feature 5 runs on eval question 3 (`eval/linked-records-research.json`, shape `superseded_criterion`), whose chain touches no worked example under `examples/` (none of those files is drawn from spec 0002 or spec 0007).
- **AC-2a**: The result record states that "record" in the scope row's Done when is read as a Record node as spec 0002 defines it (a spec, the scope document, or one feature row), and that question 3 spans two Records, spec 0002 and spec 0007.
- **AC-2b**: The reword of the scope row's Done when from "three records" to "two or more Records" is carried in this spec's Follow up for `/scope` (this spec does not edit another feature's contents).

**Extraction command**

- **AC-3**: `tracepath extract RECORD:SECTION ...` builds the extraction prompt before any paid call, and a failing worked example (`ExampleError`) prints a clear message to stderr and exits 1, with no traceback and no API call made.
- **AC-4**: Before the first paid call, the command checks `ensure_attempt_unwritten()` for attempt 1 of every run of every requested unit, and one collision stops the whole command with exit 1 and no spend.
- **AC-5**: Before every retry attempt, the command checks `ensure_attempt_unwritten()` for that attempt's paths, and a collision stops the command with exit 1 before that call is paid for.
- **AC-6a**: `extract --dry-run` makes no extraction call (only the free token count endpoint).
- **AC-6b**: `extract --dry-run` prints, per unit, the input tokens counted by the token count endpoint and the cached prefix.
- **AC-6c**: `extract --dry-run` prints the output assumption with its named source, the rates it assumed (stated as standard interactive pricing, not Batch), the central USD figure (3 runs per unit, 12 calls for question 3) and the wider USD figure (the heaviest measured output on every call, with a retry on every run, 24 calls for question 3), then the totals.
- **AC-6d** (added 2026-10-06): `extract --dry-run` does not stop at AC-4's collision check: it prints the estimate and exits 0 even when a requested unit already has an artifact.
- **AC-6e** (added 2026-10-06): `extract --dry-run` names every requested unit that a real run would refuse at AC-4's collision check.
- **AC-7**: `extract` without `--ceiling USD` exits 1 and names the flag, before any call.
- **AC-7b** (added 2026-10-06): a `--ceiling` that is not a finite number above 0 (including `nan`, `inf` and `0`) makes `extract` exit 1, naming the flag, before any call.
- **AC-8** (amended 2026-10-06): `extract` exits 1 before any paid call when `--ceiling` is below the largest per call bound (AC-55) among the requested units.
- **AC-8c** (added 2026-10-06): with `--dry-run`, a ceiling below that bound does not refuse: the dry run prints the bound and a warning, and exits 0.
- **AC-8b** (added 2026-10-06): when the wider total (AC-6c) is above `--ceiling`, `extract` does not refuse. It prints that the run may stop partway at the ceiling (AC-9).
- **AC-9** (amended 2026-10-06): Before every call, if the running total plus the per call bound (AC-55) of that call's unit would pass the ceiling, the command does not make the call. It stops there by structure, says plainly "stopping here before RECORD:SECTION run N attempt M: ceiling", and exits 1.
- **AC-10a** (amended 2026-10-06): A failed or dropped attempt counts in the running total at its unit's per call bound (AC-55), never at its recorded tokens.
- **AC-10b**: A settled attempt counts in the running total at its own recorded usage priced at the stated rates, cache write and cache read included.
- **AC-55** (added 2026-10-06): A unit's per call bound is 64,000 output tokens (`MAX_TOKENS`) at the output rate, plus the unit's uncached input (its counted input less the 57,494 token cached prefix) at the input rate, plus one write of the cached prefix at the cache write rate. At today's figures it is $0.8701 for `0010 Context` and $0.8907 for `0007 ## Feature design`.
- **AC-11** (amended 2026-10-06): After any call that is not the command's first call, the command stops with a plain message ("stopping: call N read no cache") and exit 1 when that call read no cache, unless no earlier call of the command reported usage (then nothing in this command could have written the cache yet, and the call that writes it is not a fault). Calls on units 2 to 4 are held to the same rule, since they should read the prefix the first call wrote.
- **AC-12a**: Each attempt's artifact is written as the attempt settles, before the next call starts.
- **AC-12b**: A failed or dropped attempt is written under its own `failed-run-N-attempt-M.json` name, null usage included.
- **AC-13** (amended 2026-10-06): A run with two model failures (AC-67) is blocked. The command stops before the next call and names the unit, and no later command, resume included, makes another attempt for that run.
- **AC-67** (added 2026-10-06): Every failed attempt is one of two kinds. A transport failure is an attempt whose response never completed: an HTTP error status, or a stream that ended before `message_stop` (a dropped connection or an error event mid stream). A model failure is a complete response that is malformed, fails validation, or stopped at `max_tokens`.
- **AC-67b** (added 2026-10-06, its reading rule corrected the same day during the build): Every failed attempt records its kind as `failure_kind` in its artifact. A failed artifact with no such field is read as `model`, by the rule in the Value sourcing table.
- **AC-68** (added 2026-10-06): Only model failures count toward spec 0001's single retry and toward blocking a run. A run whose failures are all transport failures stays owed.
- **AC-69** (added 2026-10-06): One command makes at most two attempts per run, of any kind. A run still not settled after two attempts in one command, and not blocked, stops the command before the next call, naming the unit as owed and resumable with `--resume`.
- **AC-70** (added 2026-10-06): The client is built with the SDK's automatic retries off (`max_retries=0`), so each attempt is exactly one request.
- **AC-14**: The command's final summary names every attempt with null usage.
- **AC-14b** (added 2026-10-06): The final summary prints two totals: the running total by the guard's rule (failed attempts at their bound), and the cost of the usage the artifacts recorded.
- **AC-48** (amended 2026-10-06, see Held out discipline): Without `--resume`, running `extract` again on a unit with fewer than three settled runs stops at AC-4's collision check.
- **AC-48b** (split out of AC-48 2026-10-06, unchanged): A unit with fewer than three settled runs stays `section_not_extracted` in the report, and is not loaded, until it has three.
- **AC-56** (added 2026-10-06): A run is owed when it has no settled attempt and fewer than two model failures. `extract --resume` makes attempts only for owed runs, numbered on from the run's highest attempt number, at most two per run in one command (AC-69).
- **AC-57** (added 2026-10-06): A run with no artifact at all, in a unit that has artifacts, is owed and gets its first attempt from a resume.
- **AC-58** (added 2026-10-06): `extract --resume` makes no attempt for a run that is settled (it has `run-N.json`, whatever failed files sit beside it) or blocked (AC-13).
- **AC-58b** (added 2026-10-06): A unit whose artifacts break the naming pattern (a failed attempt number missing below a higher one, or `run-N.json` for a run beyond the policy's three) is unplannable. `extract --resume` exits 1 naming the file, before any call.
- **AC-59** (added 2026-10-06): If any listed unit has no owed run (all settled, or a run blocked), `extract --resume` exits 1 before any call, naming every such unit and which it is.
- **AC-60** (added 2026-10-06): If any listed unit has no artifact at all, `extract --resume` exits 1 before any call, naming every such unit and saying a plain `extract` starts it.
- **AC-60b** (added 2026-10-06): `extract --resume` exits 1 before any call when a unit's settled artifacts name a `prompt_version`, `model`, `commit` or `effort` other than the current ones, naming the unit and the difference.
- **AC-61** (added 2026-10-06): Before its first call, a resume checks that the next attempt's paths are unwritten for every owed run of every listed unit, and stops on one collision with exit 1, as AC-4 does.
- **AC-61b** (added 2026-10-06): A resume never replaces or deletes an artifact: before each attempt it runs AC-5's collision check on that attempt's paths.
- **AC-62** (added 2026-10-06): A resume checks the ceiling before each attempt with the per call bound, as AC-9 does.
- **AC-63** (added 2026-10-06): A resume's estimate prices only the attempts it plans: each owed run counts 1 call central and 2 wider, the most one command can make for it (AC-69).
- **AC-64** (added 2026-10-06): `extract --dry-run --resume` prints, per unit, the attempts the resume would make, with the AC-6b counts, the AC-63 totals and the AC-8b warning, and makes no extraction call.
- **AC-64b** (added 2026-10-06): `extract --dry-run --resume` exits 1 for a unit AC-58b, AC-59, AC-60 or AC-60b would refuse, as a real resume does.
- **AC-49**: `extract` calls the interactive streaming API, not the Batch API that spec 0001's storage row assigns to corpus extraction, because no batch path is built, and the estimate uses standard (not Batch) rates.

**Load command and the build record**

- **AC-15**: `tracepath load` rebuilds the graph from `artifacts/runs/` with no API call: it clears the graph, creates the constraints, and loads every committed unit, with every write asserting its own row count (spec 0002 AC-13).
- **AC-16**: Every relationship the load writes carries `prompt_version`, `model` and `commit`, read from the run artifacts of the unit it was written in. Two links of the same type between the same pair of nodes, written from different units, collapse into one relationship (the Cypher is a `MERGE`), and the last write sets its `file`, `section`, `line` and provenance.
- **AC-17a**: `load` writes `artifacts/graph-build.json`, listing for every unit its run files, model and prompt version.
- **AC-17b**: `graph-build.json` lists for every unit its accepted entity count, accepted link count and held link count.
- **AC-17c**: `graph-build.json` lists the prompt versions in use and the number of entries in `artifacts/review-log.json`.
- **AC-18**: Two `load` runs over unchanged artifacts write byte identical `graph-build.json` files (the file holds no value from the load's own clock: the only times in it are the artifacts' own `extracted_at` values, AC-65; reworded 2026-10-06).
- **AC-19**: `load` prints how many units sit at each prompt version, plainly, and does not refuse a mix.
- **AC-65** (added 2026-10-06): `graph-build.json` lists for every loaded unit the sorted, distinct `extracted_at` values of all its artifacts, failed attempts included, so a resumed unit shows more than one.
- **AC-50**: Every entity the load writes carries `file_line`, the line in the source file, equal to `unit.start_line + line - 1` (absent when `line` is null). The stored `line` stays relative to its section, as spec 0002 AC-4 defines it.
- **AC-51**: `load` prints how many resolved links collapsed into an existing relationship (AC-16).

**The walk**

- **AC-20**: `tracepath trace START` takes one canonical id (an Entity or a Record) and exits 1 naming the id when the graph does not hold it, adding that an entity held for review is not in the graph.
- **AC-21**: The walk follows every relationship of the seven typed relationship types in both directions, so a scenario that verifies the start item is reached from it. (`SPECIFIED_BY` is left out: `load()` does not write it today.)
- **AC-22**: The walk never follows `PART_OF`.
- **AC-23**: The walk stops at 3 hops from the start, and a step at the limit says so when it has typed links (not `PART_OF`) whose other end is not visited.
- **AC-24**: A Record or Unresolved node is printed and never expanded, including when it is the start, and the step says so ("whole document, not expanded" or "unresolved, not expanded").
- **AC-25**: The walk is breadth first and visits each node once, by the first path to it, so a cycle ends. The queue order is the parent order.
- **AC-26**: Neighbours are taken in one fixed order: relationship type name, then direction (outgoing before incoming), then the other node's canonical id, all lexical. Because a type, a direction and the other node are unique after AC-16's collapse, no tie remains.
- **AC-27**: An entity step prints the stored `struck` flag as it is, with no current or history label and no change to what the walk follows.
- **AC-28a**: An entity step prints its file, section, file line (AC-50) and commit, and a link step prints its file, section, line and commit. A link's `line` is its section's heading line (the unit start), and is printed as that.
- **AC-28b**: A Record step prints its file and commit.
- **AC-28c**: An Unresolved step prints its mention, file, section and line, and states "no commit, no model".
- **AC-29**: Every entity and link step prints its prompt version, and a Record step prints "code, no model".
- **AC-30**: The output ends with whether every model made step shares one prompt version, and if not, how many steps sit at each. A model made step is an entity step or the link a step was reached by, each counted once.
- **AC-31**: The walk is a pure function over an immutable graph slice, and neither the walk nor the Cypher read that feeds it reads or names `eval/`.
- **AC-32**: A hand built fixture graph, which is not an eval chain, exercises both directions, a cycle, a Record stop (also as the start), an Unresolved stop, the depth limit, a struck entity, an UNCLASSIFIED link and the fixed order, and the walk's output over it matches a hand written expectation (unit test, no Neo4j).
- **AC-33**: The same fixture loaded into real Neo4j and read back gives the same output as AC-32 (integration test).

**The report step (the only step that reads `eval/`)**

- **AC-34**: `tracepath trace --eval N` derives the start item by one rule: the first entry of question N's `trace` list, whose `record` string must match the regex `^spec (\d{4}) (AC-\d+[a-z]?)\b` (trailing text such as " (struck)" is ignored) and gives the canonical id `NNNN/AC-N`. If it does not match, the command exits 1 naming the question and does not guess.
- **AC-35**: The expected items of a question are every `trace` entry and every `also` entry under it, each taken as `(file, line)`. An entry's AC token (the `AC-N` its `record` string matches, if any) belongs to that entry's own `line` only, never to an `also` line.
- **AC-36**: An expected item counts as reached when a visited entity's `file`, with the eval file's leading `docs/` stripped from the item's file, is the same, and the entity's `file_line` (AC-50) equals the item's line.
- **AC-37**: The report lists every expected item as reached or not reached.
- **AC-38**: Every item not reached names exactly one reason, chosen by this fixed priority: `section_not_extracted` (fewer than three settled runs for the unit holding that line), `held_for_review` (an identified entity whose `file_line` is the item's line exists in some run and none is accepted), `unresolved_endpoint` (a visited Unresolved node's `record` is the item's record and its mention contains the item's AC token; an item with no token cannot take this reason), `record_not_expanded` (the item's Record was reached and stopped at), `link_held` (a link held for review, read from the same rebuilt results as `load`, names the item's entity as an endpoint), else `no_link`.
- **AC-39**: The report prints how many visited steps match no expected item, as information and not as a verdict.
- **AC-40**: The report prints how many accepted links, written outside the sections that hold expected items, touch a Record that holds an expected item, and lists them. A link touches a Record when either endpoint's canonical id, read up to its first `/` or `#`, is that Record, or an Unresolved endpoint's `record` is.
- **AC-41**: For question 3, an expected item in spec 0007 is reached under AC-36 from the start item in spec 0002. Reaching the Record `0007`, or an entity in 0007 that is not an expected item, does not count.
- **AC-52**: When the start item is not in the graph, `trace --eval N` still prints the expected items report with every item not reached and its AC-38 reason, then exits 1, and AC-41 does not hold.

**Repeatability, errors, provenance of the result**

- **AC-42**: Running `trace --eval 3` twice against the same graph prints identical output.
- **AC-43**: Running `load` again from the same artifacts and then `trace --eval 3` prints the same output as before the reload.
- **AC-44**: Every typed failure in the three new commands (`ExampleError`, `ArtifactCollisionError`, `UnitFailed`, `GraphUnavailable`, `SettingsInvalid`, `RebuildFailed`, `GraphWriteFailed`, `ProvenanceMismatch`, a missing start, an unusable eval entry) prints a message to stderr and exits 1, never a traceback.
- **AC-45**: `artifacts/review-log.json` holds 0 entries when the result is recorded, so no review decision touched the chain's items before the run was scored.
- **AC-46a**: The result record (`experiments/0009-first-traced-chain/README.md`) names the commit of this spec.
- **AC-46b**: The result record names the commit that holds all of `src/` and the commit of the first run artifact, and git history orders them: this spec's commit, then the `src/` commit, then the first run artifact.
- **AC-47**: From the `src/` commit to the result record, nothing under `src/`, `examples/` or the prompt text changes (no change to a prompt rule, a worked example, the schema, or an entity or relationship type), and the four units' run files never change.
- **AC-53**: The scored result uses the `src/` commit of AC-46b. If a real defect in the walk or report code shows up afterwards, the frozen result is recorded first, as it came. A fix is a separate commit, and its rescoring on the same unchanged run files is reported as a second, labelled result, never in place of the first.
- **AC-54**: The result record compares the summed artifact usage (failed attempts included) with the Console's usage for the day of the run, with no other tracepath API use that day, and states any gap without explaining it away.
- **AC-71** (added 2026-10-06, second amendment): `run_with_retry()` raises `RetryPathRetired` as its first statement, before any call, so `run_unit()`, `extract_unit()` and `extract_units()`, which reach the API only through it, can no longer spend.
- **AC-71b** (added 2026-10-06, second amendment): The `RetryPathRetired` message names `tracepath extract` as the way to extract.
- **AC-71c** (added 2026-10-06, second amendment): `RetryPathRetired` derives from `Exception` only, not from `ExtractionFailed` or `UnitFailed`, so it passes through `run_unit()` unchanged and no experiment script's `except` clause swallows it.
- **AC-72** (added 2026-10-06, second amendment, simplified on acceptance): A test fails when a tracked Python file outside `tests/` and outside the allowlist contains, as plain text, `import anthropic`, `from anthropic`, `build_client` or `extract_once`. The allowlist is the sixteen files that match today: `src/tracepath/extract/client.py`, `src/tracepath/extract/metered.py`, `src/tracepath/cli.py`, `src/tracepath/pipeline.py` (it imports `anthropic` for a type, and its paid path is fenced by AC-71), and, named one by one as frozen historical records, `experiments/0001-ac14-type-stability/calibrate_effort.py`, `experiments/0001-ac14-type-stability/run.py`, `experiments/0002-effort-low-fidelity/calibrate_effort.py`, `experiments/0003-feature-design-testscenario/run.py`, `experiments/0004-label-round-trip/real_label_run.py`, `experiments/0005-held-out-prompt-examples/baseline_0021.py`, `experiments/0005-held-out-prompt-examples/measure_prefix.py`, `experiments/0005-held-out-prompt-examples/run_units.py`, `experiments/0006-accuracy-bar-recheck/measure_recheck.py`, `experiments/0006-accuracy-bar-recheck/run_recheck.py`, `experiments/0008-type-coverage-rerun/measure_coverage.py`, `experiments/0008-type-coverage-rerun/run_coverage.py`.
- **AC-73** (added 2026-10-06, second amendment, a regression pin that passes with no code change): `committed_units()` over the repository and its snapshot returns `0021 ## Requirements` with three settled runs.
- **AC-73c** (added 2026-10-06, second amendment, a pin): Its run 2 settled artifact records attempt 3.
- **AC-73b** (added 2026-10-06, second amendment, a pin): `resume_runs()` refuses the committed `0021 ## Requirements` as owing nothing, not as blocked: its run 2 is settled, whatever model failures sit beside it (AC-58).
- **AC-74** (added 2026-10-06, second amendment): An autouse fixture in `tests/conftest.py` sets `ANTHROPIC_API_KEY` to `sk-ant-test` and `ANTHROPIC_BASE_URL` to `http://localhost:1`, where nothing listens, for every test. `load_dotenv()` keeps working, so `.env` still supplies the Neo4j settings, and since it never replaces a variable already set, `.env`'s real key never loads in a test. A test that uses the fake API sets its own base URL.
- **AC-74b** (added 2026-10-06, second amendment): A test proves the fixture is active: the key is the fake one and the base URL the unreachable one.
- **AC-74c** (added 2026-10-06, second amendment): A test proves `load_anthropic_settings()` returns the fake key even when a `.env` beside it holds another.
- **AC-66** (added 2026-10-06): A result record names every resumed unit (a unit whose artifacts, failed attempts included, carry more than one `extracted_at`) with those values.

## Decision

**Chosen option**: Option 1: a general breadth first walk over typed links, run on question 3 under written, locked rules.

Build `extract`, `load` and `trace` as thin shell commands over the existing pure pipeline. The walk is a pure function in `src/tracepath/traverse/`, fed by one Cypher read in `src/tracepath/graph/`. A separate report step reads `eval/` and is the only code that does. The rules in `## Held out discipline` are locked before any paid call.

**Implementation skills**: `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `neo4j-driver-python-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-driver-python-skill/`) · `neo4j-cypher-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-cypher-skill/`, Cypher 5 syntax only) · `claude-api` (`anthropics/skills`, bundled with Claude Code)

## Rationale

Reasoning, the options, the weighing of each requirement and the cost arithmetic: see [rationale.md](rationale.md).

## Held out discipline

This section exists so a pass means the mechanism works, not that the test was fitted to question 3. Everything in it is **locked at the commit that adds this spec, before any paid call**. The run is scored against it as written. Nothing here is revised after results are seen. Feature 6 applies the same rules to all five questions unchanged.

**Locked before any paid call**, and the code is frozen too (AC-46b, AC-47): all of `src/` is committed before the first run artifact, and the scored result uses that commit. A later fix to a real defect is a separate commit, and its rescoring on the same run files is a second, labelled result (AC-53).

1. **The pass rule**: AC-34 to AC-41 and AC-42 to AC-54 as written above. Feature 5 passes when AC-41 holds (an expected item in spec 0007 is reached from the start item in spec 0002) and every other criterion holds. Items not reached are not failures, they are findings with a reason.
2. **The start item rule** (AC-34): the first entry of the question's `trace` list. It is never chosen by which item gives the best chain. For question 3 it gives `0002/AC-10`.
3. **The walk rules** (AC-20 to AC-30): both directions, the seven typed relationship types, no `PART_OF`, 3 hops, Record and Unresolved nodes terminal, fixed order, struck flag printed and nothing more. They are stated without reference to question 3 and tested on a fixture that is not an eval chain (AC-32, AC-33).
4. **The matching and reason rules** (AC-35, AC-36, AC-38): how an expected item counts as reached (same file after stripping `docs/`, and `file_line` equal to the item's line) and how a missed one is explained.
5. **The prediction for question 3**, to be scored as written:

| Expected item (file, line) | Predicted | Reason if not reached |
|---|---|---|
| spec 0002 AC-10, struck (`0002` index.md:31) | reached, hop 0 (the start) | none |
| spec 0002 struck test scenario (`0002` index.md:232) | reached, hop 1, by `VERIFIES` pointing at `0002/AC-10` | none |
| spec 0007 AC-13 (`0007` index.md:36) | reached, hop 1, by any typed link outgoing from `0002/AC-10` whose other end is `0007/AC-13`, because AC-10's unstruck note names "spec 0007 AC-13" (`0002` index.md:31) | none |
| spec 0007 AC-12 (`0007` index.md:35) | **not reached** | `no_link` or `record_not_expanded`, whichever AC-38's rule gives. Both mean no explicit identifier points at the item |
| spec 0007 key invariant 1 (`0007` index.md:142) | **not reached** | the same |

   Hop counts and the link direction in the table are part of the prediction. The result states which reason code fired for each miss. If an expected item's own entity is held, the reason is `held_for_review` instead, and that is a finding, not a revision of the prediction. A wrong prediction is reported as wrong.

   **Risks named now, so they cannot be explained afterwards.** (a) The prompt splits a struck claim from its replacement, so the entity at line 31 may be AC-10's unstruck "SUPERSEDED" note and the struck text may get a derived id. Row 1 is scored by the line (AC-36), not by the id, so it is reached either way, but the printed `struck` flag on the start step may read false. That is not a miss. (b) Row 2 needs three run agreement on a derived, struck entity inside a 23.7K character Feature design unit, and spec 0002 measured null located lines for that unit kind, so `held_for_review` on row 2 is a real possibility and is scored as it comes. (c) The scenario's "verifies AC-10" sits inside struck text, so its link may be absent or held (`link_held`).

**The walk never reads `eval/`** (AC-31). The expected chain is read only by the report step, after the walk has finished.

**One extraction pass per section.** Each of the four sections gets three runs plus spec 0001's single retry, recorded as the attempts come back (AC-12a, AC-13). There are no paid reruns to get a better result (AC-48). If a section fails, the finding is that it failed.

**Amendment of 2026-10-06, a revision of a locked rule.** AC-48 sits inside the pass rule above (AC-42 to AC-54), so changing it after experiment 0009 revises a locked rule, and this note says so. What changed: a unit cut short may now be completed with `extract --resume` (AC-56 to AC-64, AC-66), where before it could never be. Why: two confirmed ways can each burn a unit permanently. A first call that drops before any usage arrives on a cold cache stops the command after its retry (finding 1 of `docs/reviews/2026-10-06-check-verify-first-traced-chain.md`), and a ceiling stop between calls (AC-9) can leave any unit short of three runs. Under the old AC-48, a unit an eval question needs could then never be extracted. A resume completes the one pass that was cut short, under the run policy as amended the same day: only a model failure uses up a run's single retry (AC-67, AC-68), so a run cut short by transport failures is attempted again, and a run that settled or has two model failures never is. A resume never replaces or discards an attempt and never runs a settled run again, so it cannot buy a better result. Experiment 0009 had no partial unit, so AC-48 played no part in its scored result, which stands as recorded. The amendment applies only to runs after 2026-10-06. One unit already in the corpus has this history. In experiment 0008 (its README, lines 45 to 48), `0021 ## Requirements` run 2 failed schema validation on its attempt and its retry, two model failures, and the engineer resumed it at attempt 3, where it settled. That came before this rule, under which two model failures block a run (AC-13), and the rule applies only to runs after 2026-10-06. So `0021` stays as committed: it loads with three settled runs (AC-73), and a resume reads it as settled, not blocked (AC-73b). The same day's changes to AC-6d, AC-6e, AC-7b, AC-8, AC-8b, AC-8c, AC-9, AC-10a, AC-11, AC-13, AC-14b, AC-55, AC-67, AC-67b and AC-68 to AC-70 touch the extract command's cost controls and run policy, which sit outside the pass rule.

**No manual review decisions** on the chain's items before the run is recorded (AC-45). An item held for review is reported as held (AC-38).

**No tuning to this question** (AC-47): no prompt, rule, example, schema or type change for question 3, and no change to `src/` after the frozen commit. The vocabulary revisit already done (the `0006` ruling in `docs/session-notes.md`) is the only one owed.

**What the result must state.** The result record (AC-46a) states the count from AC-40. Today, over the 14 committed units, no accepted link outside the four sections touches 0002 or 0007 (checked in design: 85 resolved links, none with an endpoint naming either record). The result states whether that still holds after the load. If it does, the walk chooses only among sibling items inside the chain's own four sections, and not among other records, so a pass says nothing about choosing between records.

**What happens if AC-41 fails.** The result is recorded as it came. Feature 5 is not marked done on a retuned run. The engineer decides the next step in a new decision, and nothing about the prompt, the walk rules or the prediction is revised to fit.

## Feature design

**Data model sketch**:

No new node kind and no new entity type. Four additions to what already exists.

- **Link properties** (amends spec 0002's relationships table): every relationship gains `prompt_version`, `model` and `commit`, read from the unit it was written in. Written by `load()`; a link with no matching unit raises `ProvenanceMismatch`. Records and `PART_OF` links are made by code and carry none. Two same type links between one pair from different units collapse into one relationship, and the last write wins (AC-16).
- **Entity property `file_line`** (amends spec 0002's Entity table): the line in the source file, `unit.start_line + line - 1`, written by `load()` beside the unchanged section relative `line` (AC-50). Found by checking: `0014 ## Requirements` starts at file line 19 and its first entities are stored at lines 5, 6 and 7.
- **`artifacts/graph-build.json`**, one derived file, rewritten by every `load`. Not a run artifact, so spec 0001's append only rule does not apply to it.

```json
{
  "corpus_commit": "2e40bcf",
  "units": [
    {"record": "0002", "section": "Requirements", "section_slug": "requirements",
     "run_files": ["artifacts/runs/0002/requirements/run-1.json", "..."],
     "model": "claude-sonnet-5", "prompt_version": "0003.1",
     "accepted_entities": 0, "accepted_links": 0, "held_links": 0,
     "extracted_at": ["2026-10-05T21:39:44+00:00"]}
  ],
  "prompt_versions": {"0003.1": 15, "0003.0": 2, "0002.3": 1},
  "review_log_entries": 0
}
```

- **In memory**, frozen dataclasses: `GraphSlice` (tuples of nodes and links, as read), `Step` (hop, node, the link it was reached by, direction, whether it stopped there and why), `Chain` (start, steps, the stops), `ExpectedItem` and `Finding` for the report.

**State transitions**: none. Each command is a single pass.

**Commands**:

| Command | Key inputs | Key outputs | Auth | Key errors |
|---|---|---|---|---|
| `tracepath extract RECORD:SECTION ... --ceiling USD [--dry-run] [--resume] [--root] [--snapshot]` | one or more unit addresses; the ceiling, a finite number above 0 (AC-7b); `--resume` completes units cut short (AC-56 to AC-64) | run artifacts under `artifacts/runs/`; the estimate and the running total on stdout. Interactive streaming API, not Batch (AC-49) | `ANTHROPIC_API_KEY` | `ExampleError`, `ArtifactCollisionError`, `UnitFailed`, ceiling, unit not found or ambiguous, a unit a resume cannot plan or must refuse, an owed or blocked run, all exit 1 |
| `tracepath load [--root] [--snapshot] [--commit]` | the committed run artifacts | the graph, `artifacts/graph-build.json`, a count per prompt version | Neo4j settings | `GraphUnavailable`, `RebuildFailed`, `GraphWriteFailed`, `ProvenanceMismatch`, all exit 1 |
| `tracepath trace START` or `trace --eval N [--eval-file]` | a canonical id, or an eval question number | the chain on stdout | Neo4j settings | missing start, unusable eval entry, `GraphUnavailable`, all exit 1 |

A unit address is `RECORD:SECTION`, for example `0002:Requirements` or `"0007:Feature design"`. A section name that more than one unit of a record carries (spec 0007 has two `Build plan` units) is refused as ambiguous, naming the candidates, rather than guessed.

**Value sourcing**:

| Action | Value produced / displayed | Source |
|---|---|---|
| `extract --dry-run` | input tokens per unit | the free token count endpoint, on the real system blocks and `user_prompt(unit)` |
| `extract --dry-run` | cached prefix | the billed figure 57,494 (experiment 0008 README, Configuration); the command recounts experiment 0006's calibration unit (`0014 Requirements`, 61,108 tokens) and refuses to price if it differs |
| `extract --dry-run` | output tokens per call, central | named in the printed line: `0021 ## Requirements` 27,384 for a Requirements unit and `0006 ## Feature design` 26,721 for a Feature design unit (experiment 0008 `data/run.json`, the unseen unit figures) |
| `extract --dry-run` | output tokens per call, wider | 39,234, the heaviest measured call (experiment 0005, `0021` run 2) |
| `extract --dry-run` | rates | 2.00 / 10.00 / 4.00 / 0.20 USD per million (input, output, 1 hour cache write, cache read): standard interactive pricing, not Batch. The rates experiment 0005 reproduced against experiment 0004's bill |
| `extract --dry-run` | central and wider call counts | central: 3 runs times the units (12 for question 3). Wider: the same with a retry on every run (24), each priced at the heaviest output. The retry is per run (`run_with_retry`), not per unit |
| `extract` | flat failure cost | $0.4144, one heaviest call (experiment 0008's script). Replaced 2026-10-06 by the per call bound below, in AC-9 and AC-10a; kept here as the original record |
| `extract` | per call bound (AC-55) | `MAX_TOKENS` (64,000, `src/tracepath/extract/client.py`) at the output rate, plus the unit's counted input (the count endpoint, as AC-6b) less `CACHED_PREFIX_TOKENS` at the input rate, plus `CACHED_PREFIX_TOKENS` at the cache write rate. It holds because `max_tokens` caps a call's billed output, thinking included: the repo records a call that spent its whole 16,000 budget thinking and stopped at `max_tokens` (`client.py`, the `MAX_TOKENS` comment). Confirmed in Anthropic's docs on 2026-10-06: "`max_tokens` remains the hard ceiling on total output" and "thinking tokens count toward the `max_tokens` limit" (extended thinking page); a 1 hour cache write is "2 times the base input tokens price" (prompt caching page) |
| `extract` | the bound AC-8 checks | the largest per call bound among the requested units |
| `extract --dry-run` | units a real run would refuse (AC-6e) | `preflight()`'s collision check, run without stopping, one name per unit it would refuse |
| `extract --resume` | the planned attempts per unit (AC-56 to AC-58b, AC-64) | the unit's existing artifacts, per run: `run-N.json` means settled; otherwise the failed attempts' `failure_kind`, where two model failures means blocked and anything less means owed, with the next attempt numbered one above the highest; no file means owed from attempt 1 |
| `extract` | an attempt's `failure_kind` (AC-67, AC-67b) | set by `extract_once()` from how the attempt ended: `transport` for an `anthropic.APIStatusError`, an `APIConnectionError`, a transport error mid stream or an error event mid stream; `model` for a schema failure, no parsed output, or `stop_reason` `max_tokens`. A failed artifact with no `failure_kind` is read as `model`. This is exact, not a guess: every writer from 2026-10-06 records the field, so the set without it is closed, and it is exactly four files (`artifacts/runs/0021/requirements/failed-run-2-attempt-1.json` and `failed-run-2-attempt-2.json`, and `failed-run-1-attempt-1.json` under `artifacts/superseded/2026-09-24-prompt-0002.3/0021/requirements/` and `artifacts/superseded/2026-09-28-prompt-0002.3/0014/requirements/`), all schema failures by their recorded `error`. Reading them as `model` blocks rather than resumes, so a misreading could never cause a paid call. (Corrected during the build on 2026-10-06: the first rule read `stop_reason`, but all four record it as null, written before PR #15 fixed that field, and the superseded `0021` attempt's raw response is empty, not recorded as this row first said.) |
| `extract` | check order before the first call | `--ceiling` (AC-7, AC-7b), the prompt build (AC-3), unit resolution in the order given (a unit named twice refused, as today), the token counts, the collision check (AC-4, or AC-61 with `--resume`), the provenance check (AC-60b, resume only), the ceiling against the bound (AC-8), then the first call |
| `extract --resume` | central and wider call counts (AC-63) | 1 central and 2 wider per owed run |
| `extract` | which estimated calls write the cache (amended 2026-10-06) | central: the command's first call writes, every later call reads. Wider: every call writes, as the per call bound assumes, since a cache can expire between passes. Experiment 0009's recorded wider figure ($10.1903) used the earlier rule, first call only |
| `extract` | the summary's two totals (AC-14b) | the running total (AC-9, AC-10a), and the recorded usage of every attempt at the stated rates, null counted as 0 |
| `extract` | `extracted_at` of a pass | `now_utc()` once per command, as today, so every artifact of one pass carries the same value and a resume carries a new one |
| `load` | each unit's `extracted_at` list (AC-65) | the distinct `extracted_at` values of all the unit's artifacts, failed attempts included, sorted. Read from the files, so two loads still write the same bytes (AC-18) |
| `extract` | a settled attempt's cost in the running total | that attempt's recorded `input_tokens`, `output_tokens`, cache write and cache read, at the rates above |
| `extract` | the stop message and exit code | AC-9 and AC-11 name the wording; both exit 1 |
| `extract` | the ceiling | the `--ceiling` flag, set from the figure the engineer approved |
| `extract` | prompt version, model, effort, runs per unit | `PROMPT_VERSION`, `ANTHROPIC_MODEL`, `ANTHROPIC_EFFORT`, `RUNS_PER_UNIT` (existing) |
| `load` | accepted, held, per unit counts | the routed `UnitResult`s rebuilt by `committed_units()` |
| `load` | link `prompt_version`, `model`, `commit` | the unit's settled run artifacts (`unit_provenance()`), matched by the link's `(file, section)`; a `(file, section)` held by two units with different provenance raises `ProvenanceMismatch` |
| `load` | entity `file_line` | `unit.start_line + line - 1`, from the unit and the located `line` (AC-50) |
| `load` | collapsed link count | resolved links minus distinct `(type, from, to)` triples (AC-51) |
| `load` | `review_log_entries` | the length of `artifacts/review-log.json` |
| `trace` | an entity step's file, section, file line, commit, prompt version, struck flag, text | the entity node's own properties (`file`, `section`, `file_line`, `commit`, `prompt_version`, `struck`, `text`) |
| `trace` | a link's file, section, line, commit, prompt version, phrase | the relationship's own properties (AC-16). Its `line` is the section's heading line, as stored |
| `trace` | an Unresolved step's mention, file, section, line | the Unresolved node's own properties; it has no commit and no prompt version |
| `trace` | a Record step's path and commit | the Record node's `path` and `commit` |
| `trace` | "stopped at depth limit" | the walk: a step at hop 3 with typed links (not `PART_OF`) whose other end is not visited (AC-23) |
| `trace --eval` | start id | the first `trace` entry's `record` string, by AC-34 |
| `trace --eval` | expected items | each `trace` entry's `file` (leading `docs/` stripped) and `line`, and each `also.line` with its parent's `file` |
| `trace --eval` | an item's AC token | the entry's `record` string, matched by the AC-34 regex, for the entry's own `line` only |
| `trace --eval` | reason for an item not reached | the rebuilt `UnitResult`s (settled run count, identified and accepted entities), the visited steps, and the unit split of the snapshot file |
| `trace --eval` | links from outside the expected sections | the resolved links of `resolve_accepted()`, by their `(file, section)`, with AC-40's touch rule |
| `trace --eval` | whether a link was held | `resolve_accepted().held` and each unit's routed review relationships, from the same rebuilt results as `load` |

**Key invariants**:
1. The walk and its Cypher read never reference `eval/`. Only the report step does (AC-31).
2. The walk follows only what the graph holds, never a path hard coded for a question (AC-21 to AC-26).
3. A held entity is absent from the graph and reported as held, never drawn as a gap (spec 0002 key invariant 8).
4. Run artifacts are never replaced. A collision stops the command before spend (AC-4, AC-5), and a resume checks every attempt it makes the same way (AC-61).
5. The locked rules and `src/` are not edited between the frozen `src/` commit and the result record (AC-46b, AC-47, AC-53).
6. Output carries no timestamp or other value that changes between identical runs (AC-42).
7. Spend never passes the ceiling: every call is checked against the running total plus a bound that one call cannot exceed (AC-9, AC-55), resume included (AC-62).
8. No paid call is made outside `tracepath extract` or `run_metered()`: the old retry path refuses (AC-71), a test fails on any new file outside the allowlist that imports `anthropic` or names `build_client` or `extract_once` (AC-72), and no test can reach the real API with the developer's key (AC-74). Two limits, stated: edits inside an allowlisted file are not seen, since the allowlist is by path, and the match is plain text, so a new file merely naming one of the four strings in prose also fails, which errs on the safe side. The free token count endpoint (`count_tokens`) is not fenced. No paid entry point exists outside Python files (checked 2026-10-06).

**Security model**: single user, local tool. Secrets stay in `.env` (`ANTHROPIC_API_KEY`, the Neo4j settings), never written to artifacts or the manifest. Cypher uses parameters only. No compliance scope.

**Configuration required**: none new. The commands read the existing `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_EFFORT`, `NEO4J_*` settings. Neo4j must be up (`docker compose up -d`) for `load` and `trace`.

**Critical test scenarios**:
- Happy path: the fixture graph, loaded into Neo4j, walked from its start item, prints the hand written expectation, verifies **AC-21**, **AC-26**, **AC-33**.
- Happy path: `trace --eval 3` on the real graph prints the chain, each step citing its record, verifies **AC-28a**, **AC-29**, **AC-41**.
- Repeat: a second `trace --eval 3`, then a `load` and a third, print identical output, verifies **AC-42**, **AC-43**.
- Failure case: a worked example with a missing `json` fence makes `extract` exit 1 with a message and no call, verifies **AC-3**.
- Failure case: an artifact already sitting at attempt 1 of run 2 of the second unit stops `extract` before the first call is paid, verifies **AC-4**.
- Failure case: a fake client whose second call reads no cache stops the run with exit 1, verifies **AC-11**.
- Failure case: a ceiling that the running total plus $0.4144 would pass stops the command before that call, verifies **AC-9**.
- Failure case: a fake client that drops a stream writes a `failed-run` artifact with null usage and the summary names it, verifies **AC-12b**, **AC-14**.
- Failure case: a start id the graph does not hold exits 1 with a message, verifies **AC-20**.
- Failure case: `trace --eval` with a start the graph does not hold still prints the five item report and exits 1, verifies **AC-52**.
- Edge: an expected item at the file line of an entity in another file with the same line number is not reached, verifies **AC-36**.
- Edge: an eval record string `spec 0002 AC-10 (struck)` yields start `0002/AC-10`, verifies **AC-34**.
- Edge: a cycle in the fixture ends the walk and visits each node once, verifies **AC-25**.
- Edge: an expected item whose section has two settled runs is reported `section_not_extracted`, verifies **AC-38**.
- Edge: a `load` over two units at different prompt versions prints the count per version and does not refuse, verifies **AC-19**.
- Amendment of 2026-10-06, all with a fake client and no paid call:
  - Failure case: a ceiling of $0.50 on one unit exits 1 before any call, because one call's bound is above it, verifies **AC-8**.
  - Happy path: a ceiling of $1.30 on `0010 Context` (wider $2.6423) starts, prints that it may stop partway, and stops before the first call whose bound would pass $1.30, verifies **AC-8b**, **AC-9**.
  - Failure case: `--ceiling nan`, `inf`, `0` and `-1` each exit 1 naming the flag, verifies **AC-7b**.
  - Edge: a dropped first attempt counts at the unit's bound, not $0.4144, verifies **AC-10a**, **AC-55**.
  - Edge: a first call dropped before usage, then a retry that writes the cache and reads none, does not stop the command, verifies **AC-11**.
  - Edge: `--dry-run` over an already extracted unit prints the estimate, names the unit, and exits 0, verifies **AC-6d**, **AC-6e**.
  - Happy path: a unit with `run-1.json` only is resumed with runs 2 and 3; one with `run-1.json` and a model failure in `failed-run-2-attempt-1.json` gets run 2's attempt 2 and run 3's attempt 1, verifies **AC-56**, **AC-57**.
  - Edge: a run with `run-2.json` beside failed files, and a run with two model failures, get no new attempt, verifies **AC-58**.
  - Failure case: `--resume` on a unit with three settled runs, and on a unit with no artifact, each exits 1 before any call, verifies **AC-59**, **AC-60**.
  - Edge: a resumed unit's manifest entry lists two `extracted_at` values, verifies **AC-65**.
  - Edge: a run whose two attempts both end in transport failures stops the command as owed, and a later `--resume` attempts it again as attempt 3, verifies **AC-68**, **AC-69**, **AC-56**.
  - Edge: a run with two model failures stops the command as blocked, and `--resume` refuses the unit, verifies **AC-13**, **AC-59**.
  - Edge: a `failed-run-2-attempt-2.json` with no attempt 1 makes `--resume` exit 1 naming the file, verifies **AC-58b**.
  - Failure case: a unit whose settled runs are at prompt `0003.0` makes `--resume` exit 1 before any call, verifies **AC-60b**.
  - Edge: the built client's `max_retries` is 0, verifies **AC-70**.

## Build plan

Ordered for the Tracer Bullet approach: the thinnest real thread first (graph in hand, walk on real data from items that are not on the chosen chain), then the paid step, then the thickening that scores it.

1. `load` command over the existing pieces (`committed_units`, `records_for_units`, `resolve_accepted`, `load()`), with the typed failures turned into exit 1, satisfies **AC-15**, **AC-44**.
2. Provenance and file lines: `link_row()` and `load()` stamp `prompt_version`, `model` and `commit` on every relationship from the unit it was written in (refusing a link with no matching unit), and `entity_row()` adds `file_line`, satisfies **AC-16**, **AC-50**, **AC-51**.
3. `graph-build.json` and the per prompt version count, satisfies **AC-17a**, **AC-17b**, **AC-17c**, **AC-18**, **AC-19**.
4. `graph/read.py` (one deterministic Cypher read of nodes and typed links) and `traverse/walk.py` (the pure walk), with the fixture graph and its unit and integration tests, satisfies **AC-20** to **AC-27**, **AC-28a** to **AC-28c**, **AC-29** to **AC-33**.
5. `trace START` command, smoke tested on the 14 committed units from an item that is not in spec 0002 or spec 0007, satisfies **AC-20**, **AC-28a** to **AC-28c**, **AC-29**, **AC-30**, **AC-44**.
6. `extract` command: unit addresses, `ExampleError` handling, the whole command collision preflight and the per retry check, per attempt hooks so each artifact is written as it settles, the interactive streaming API, satisfies **AC-3**, **AC-4**, **AC-5**, **AC-12a**, **AC-12b**, **AC-13**, **AC-48**, **AC-49**.
7. `extract` cost controls: `--dry-run` using the count endpoint, `--ceiling`, the check before every call, flat failure cost, a settled attempt's priced cost, the no cache stop, the null usage summary, tested with a fake client before any call, satisfies **AC-6a** to **AC-6c**, **AC-7** to **AC-9**, **AC-10a**, **AC-10b**, **AC-11**, **AC-14**.
8. Report step (`src/tracepath/report.py`, the only reader of `eval/`): start rule, expected items, reached test, reason codes, outside link count, the missing start behaviour, tested on a synthetic eval file and a fixture graph, satisfies **AC-34** to **AC-40**, **AC-52**.
9. Gate, no code: commit and push all of `src/` (the `src/` commit of AC-46b) after this spec's commit. The engineer reviews the `--dry-run` output (measured, not the indicative figure in rationale.md) and gives a ceiling. Nothing paid runs before this, and `src/` does not change after it.
10. The paid run: `extract` on the four units of question 3, one pass, recorded as it comes back and committed, satisfies **AC-1**, **AC-46b**, **AC-47**.
11. `load`, `trace --eval 3`, again, then `load` and `trace --eval 3` once more. Record the result in `experiments/0009-first-traced-chain/README.md` with the scored prediction, the AC-40 statement, the cost against the estimate, the Console reconciliation and the review log count, satisfies **AC-2a**, **AC-41** to **AC-43**, **AC-45**, **AC-46a**, **AC-53**, **AC-54**.

**Amendment of 2026-10-06** (branch `fix/extract-guards`, no paid call). The cost guard first, because the resume relies on it:

12. The per call bound and the ceiling rules: compute the bound from each unit's count, use it in the check before every call and for a failed attempt's cost, refuse a ceiling below the largest bound (warn in a dry run), print the may stop partway line, validate `--ceiling`, print both totals in the summary, satisfies **AC-7b**, **AC-8**, **AC-8b**, **AC-8c**, **AC-9**, **AC-10a**, **AC-14b**, **AC-55**.
13. The run policy: record each failed attempt's `failure_kind`, count only model failures toward the retry and toward blocking, cap one command at two attempts per run, stop on an owed run, turn the SDK's retries off, and add the no cache stop's exception (finding 1's `/debug` fix), satisfies **AC-11**, **AC-13**, **AC-67**, **AC-67b**, **AC-68** to **AC-70**.
14. The dry run runs the collision check without stopping and names the units a real run would refuse, satisfies **AC-6d**, **AC-6e**.
15. `--resume`: plan the owed attempts from the unit's artifacts, refuse unplannable, finished, blocked, empty or mismatched units before any call, check every planned attempt for a collision up front and again before it, check each against the ceiling, price only the plan, and print the plan in a dry run, satisfies **AC-48**, **AC-56** to **AC-64b**.
16. The manifest's `extracted_at` list per unit, satisfies **AC-65**. **AC-48b** and **AC-66** need no code: the first is today's behaviour, and the second binds the next result record.
17. Second amendment, 2026-10-06: fence `run_with_retry()` with `RetryPathRetired`, replace `tests/test_run_unit_usage.py`'s behaviour tests with refusal tests, add the allowlist test, pin `0021 ## Requirements`, add the autouse fixture and its two tests, and add one line each to `tests/test_experiment_scripts.py`'s docstring and to the READMEs of experiments 0002 and 0003 saying their calls are now fenced, satisfies **AC-71** to **AC-71c**, **AC-72**, **AC-73**, **AC-73b**, **AC-73c**, **AC-74** to **AC-74c**. It lands after experiment 0009's result record (`18c4396`), which is where AC-47's freeze on `src/` ends, as the first amendment's build already relied on.

## Consequences

**Positive**:
- Every stage runs for real on real text, so the first end to end result exists before feature 6 builds a runner on top of it.
- The result is credible: rules and prediction are fixed first, a miss is a finding, and the walk is tested on a graph that is not an eval chain.
- The first paid call also exercises `extract_once()`'s validation and dropped stream paths (PRs #15 and #16) for the first time.
- Link provenance and the build manifest make a failing chain attributable to the walk, the extraction or an old prompt.

**Negative / tradeoffs**:
- Question 3 spans two Records, not three, so the scope row's Done when has to be read as "two or more" until `/scope` rewords it.
- The walk returns a whole neighbourhood and does not rank or prune, so a chain can include steps outside the expected chain. AC-39 counts them instead of hiding them.
- A likely result is a partial chain: spec 0007's AC-12 and key invariant 1 are named by no explicit identifier, so they are predicted not reached. That is a real limit, handed to feature 8 and feature 7, not fixed here.
- Question 3 cannot test choosing between records: today no accepted link outside its four sections touches 0002 or 0007, so the walk chooses only among siblings. The result says so.
- About $3.75 central for 12 calls, and up to about $10.20 if every run is retried at the heaviest output (24 calls; rationale.md), for one question. The extract command uses the interactive API at standard rates, not the cheaper Batch API, because no batch path is built.
- The frozen `src/` commit means a defect found after the run cannot be fixed in place: the first result stands, and a fix is rescored as a second, labelled result.
- Spec 0002's relationships table changes (three link properties), a graph schema change with no migration, since the graph is rebuilt from artifacts.

- Amendment of 2026-10-06: the per call bound ($0.87 to $0.89) is about twice the flat $0.4144, so a run stops about $0.89 short of its ceiling. To finish a run, the ceiling must cover the expected spend plus one bound of headroom.
- Amendment of 2026-10-06: a resumed unit's three runs can come from passes hours or days apart. The prompt version and model must still match, and `unit_provenance()` refuses a mix (`ProvenanceMismatch`), but nothing pins the model's behaviour behind one model id between passes. The manifest's `extracted_at` list (AC-65) and the result record (AC-66) make every such unit visible, so its agreement can be read with that in mind.
- Amendment of 2026-10-06: with the SDK's retries off (AC-70), a brief outage reaches the pipeline directly. A transport failure no longer uses up a run's retry, but one command stops after two attempts on a run (AC-69), so an outage ends a command early and the engineer resumes it, rather than the SDK riding it out silently.
- Amendment of 2026-10-06: the line between kinds is drawn by how the response ended, not by why. A server fault that still returns a complete but malformed response counts as a model failure and can block a run.
- Amendment of 2026-10-06: revising AC-48 after experiment 0009 weakens the claim that every rule here was fixed before results were seen. The Held out discipline note states what changed, why, and that the scored result is unaffected.

**Neutral**:
- `trace --eval` is the seed of feature 6's runner. Feature 6 builds on `report.py` and applies the locked rules unchanged to all five questions.
- The 14 units already extracted stay at their mixed prompt versions (one at `0002.3`, two at `0003.0`, eleven at `0003.1`). The four new units are at `0003.1`. Question 3's chain touches none of the older ones, which the result confirms from AC-30.

## Follow-up

- [ ] **`/scope` edit**: the feature 5 row's Done when says "three records". Reword to "two or more Records" (AC-2b). This spec records the need and does not edit the row's Done when.
- [ ] **Feature 8 handoff**: when a supersession link lands on a whole Record (for example AC-10 superseded by spec 0007), finding the replacement inside that Record and showing it as current is feature 8's job. This spec stops at the Record and prints the stored `struck` flag only (AC-24, AC-27).
- [ ] **Feature 6**: apply the locked rules of `## Held out discipline`, the start rule, the matching rule and the reason codes to all five questions unchanged. Start rule AC-34 refuses a question whose first entry carries no `spec NNNN AC-N` form: question 5's first entry is a Consequences paragraph (`spec 0007 Consequences`) and question 4 has no `trace` list at all (its correct answer is "no documented connection"). Feature 6 decides how those two start before it runs them.
- [ ] **Feature 7**: references written as "feature 28" or "feature 10" stay Unresolved because the resolver matches canonical ids and ignores a Record's aliases. Not fixed here.
- [ ] **Feature 6 and feature 13 evidence**: question 3's result (what was reached, what was held, the unresolved endpoints) joins the evidence they choose fixes on.
- [ ] **Duplicate section names**: `unit_for()` takes the first unit when a record has two units with the same section name (`src/tracepath/rebuild.py`), and AC-16 matches provenance by `(file, section)`. Spec 0007's two `Build plan` units are the case. Question 3 does not touch them, feature 6 and feature 9 will.
- [ ] **`SPECIFIED_BY` and feature `PART_OF` are never written**: `pipeline.load()` does not call `write_specified_by()` or `write_feature_part_of()` (only tests do). Question 5's chain passes through a feature row, so feature 6 needs them, and AC-21 leaves `SPECIFIED_BY` out until then.
- [ ] The `HeldLink` docstring says "the review step releases it", but no review step exists yet (`src/tracepath/pipeline.py:72`). Small, left for a fix branch.
- [x] After the paid run, `/sync` reconciles the scope row, `AGENTS.md` commands (`extract`, `load`, `trace`) and the layout note for `artifacts/graph-build.json`. Done 2026-10-07: the commands and the layout note in `c2d42fc`, the scope row in `1b4a4ad` and `56d131d`.

- [ ] Not confirmed by Anthropic's docs (checked 2026-10-06, the errors page is silent on it): whether a request that returns an error status, or a stream cut by an error event, is billed. The per call bound covers either case, so the guard holds, but the summary's recorded total (AC-14b) can undercount a billed error, and AC-54's Console comparison is where such a gap would show. Confirmed the same day and no longer open: `max_tokens` caps total output with thinking included, and the 1 hour cache write rate is twice the base input rate.
- [x] `verify.md` owes steps for the 2026-10-06 amendment (AC-6d, AC-6e, AC-7b, AC-8, AC-8b, AC-8c, AC-9, AC-10a, AC-11, AC-13, AC-14b, AC-48, AC-48b, AC-55 to AC-70, AC-67b), added by `/develop` with the build. Written in `ec38950`.
- [ ] The `/debug` items routed with this amendment (`docs/session-notes.md`) that the amendment does not cover: a garbled `count_tokens` response gives a raw traceback, a call the API refuses records zero usage instead of null, and a write error after a paid call gives a traceback and no summary.

- [ ] `/sync`: add to `AGENTS.md` that any new paid call goes through `tracepath extract` or `run_metered()`, never `extract_once()` or a client of its own, pointing at AC-72's test.
- [x] `verify.md` owes steps for AC-71 to AC-74c, added by `/develop` with step 17.

**Amendments made with this spec, 2026-10-05** (owed wording, no code):
- Spec 0001's artifact storage row, amendment (c): a dropped call writes a null usage too, so an errored batch result is no longer "the only case". See that row.
- Spec 0003's `verify.md` AC-27 line now says the assembled prompt holds the rule once, instead of claiming no example file repeats it (`docs/reviews/2026-10-04-check-verify-extraction-stability.md`, note 2).
- Spec 0002's relationships table gains the three link properties of AC-16, and its Entity table gains `file_line` (AC-50).
