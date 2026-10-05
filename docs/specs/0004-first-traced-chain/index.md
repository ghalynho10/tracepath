# 0004. First traced chain

**Date**: 2026-10-05
**Status**: Proposed

## Summary

This spec builds the walking skeleton: three new terminal commands that take four sections of JobHunt's specs from text to a printed chain, with every step real. `extract` runs the model on the sections the chain needs, `load` rebuilds the graph from the saved run files, and `trace` walks from one item along whatever links exist and prints each step with its source and the prompt version that produced it. The test is eval question 3 ("Why is password sign in impossible on production?"), chosen because no worked example in the prompt touches it. The rules for the walk, the start item, the pass rule and the predicted result are written down and locked here, before any paid call, so a pass means the mechanism works and not that the test was fitted to one question.

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
- **AC-7**: `extract` without `--ceiling USD` exits 1 and names the flag, before any call.
- **AC-8**: `extract` exits 1 before any paid call when the wider total estimate (AC-6c) is above `--ceiling`.
- **AC-9**: Before every call, if the running total plus one flat failure figure ($0.4144, the worst a single call can add) would pass the ceiling, the command does not make the call. It stops there by structure, says plainly "stopping here before RECORD:SECTION run N attempt M: ceiling", and exits 1.
- **AC-10a**: A failed or dropped attempt counts in the running total at one flat figure (the heaviest measured call, $0.4144), never at its recorded tokens.
- **AC-10b**: A settled attempt counts in the running total at its own recorded usage priced at the stated rates, cache write and cache read included.
- **AC-11**: After any call that is not the run's first, the command stops with a plain message ("stopping: call N read no cache") and exit 1 when that call read no cache. Calls on units 2 to 4 are held to the same rule, since they should read the prefix the first call wrote.
- **AC-12a**: Each attempt's artifact is written as the attempt settles, before the next call starts.
- **AC-12b**: A failed or dropped attempt is written under its own `failed-run-N-attempt-M.json` name, null usage included.
- **AC-13**: A unit that fails after spec 0001's single retry is recorded and not run again. The command stops before the next call and names the failed unit.
- **AC-14**: The command's final summary names every attempt with null usage.
- **AC-48**: A unit with fewer than three settled runs (an interrupted or failed unit) is never resumed by the command: running it again stops at AC-4's collision check, and the unit stays `section_not_extracted` in the report. This is intended, because a resume is a second paid pass.
- **AC-49**: `extract` calls the interactive streaming API, not the Batch API that spec 0001's storage row assigns to corpus extraction, because no batch path is built, and the estimate uses standard (not Batch) rates.

**Load command and the build record**

- **AC-15**: `tracepath load` rebuilds the graph from `artifacts/runs/` with no API call: it clears the graph, creates the constraints, and loads every committed unit, with every write asserting its own row count (spec 0002 AC-13).
- **AC-16**: Every relationship the load writes carries `prompt_version`, `model` and `commit`, read from the run artifacts of the unit it was written in. Two links of the same type between the same pair of nodes, written from different units, collapse into one relationship (the Cypher is a `MERGE`), and the last write sets its `file`, `section`, `line` and provenance.
- **AC-17a**: `load` writes `artifacts/graph-build.json`, listing for every unit its run files, model and prompt version.
- **AC-17b**: `graph-build.json` lists for every unit its accepted entity count, accepted link count and held link count.
- **AC-17c**: `graph-build.json` lists the prompt versions in use and the number of entries in `artifacts/review-log.json`.
- **AC-18**: Two `load` runs over unchanged artifacts write byte identical `graph-build.json` files (the file holds no timestamp).
- **AC-19**: `load` prints how many units sit at each prompt version, plainly, and does not refuse a mix.
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
     "accepted_entities": 0, "accepted_links": 0, "held_links": 0}
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
| `tracepath extract RECORD:SECTION ... --ceiling USD [--dry-run] [--root] [--snapshot]` | one or more unit addresses; the ceiling | run artifacts under `artifacts/runs/`; the estimate and the running total on stdout. Interactive streaming API, not Batch (AC-49) | `ANTHROPIC_API_KEY` | `ExampleError`, `ArtifactCollisionError`, `UnitFailed`, ceiling, unit not found or ambiguous, all exit 1 |
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
| `extract` | flat failure cost | $0.4144, one heaviest call (experiment 0008's script) |
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
4. Run artifacts are never replaced. A collision stops the command before spend (AC-4, AC-5).
5. The locked rules and `src/` are not edited between the frozen `src/` commit and the result record (AC-46b, AC-47, AC-53).
6. Output carries no timestamp or other value that changes between identical runs (AC-42).

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
- [ ] After the paid run, `/sync` reconciles the scope row, `AGENTS.md` commands (`extract`, `load`, `trace`) and the layout note for `artifacts/graph-build.json`.

**Amendments made with this spec, 2026-10-05** (owed wording, no code):
- Spec 0001's artifact storage row, amendment (c): a dropped call writes a null usage too, so an errored batch result is no longer "the only case". See that row.
- Spec 0003's `verify.md` AC-27 line now says the assembled prompt holds the rule once, instead of claiming no example file repeats it (`docs/reviews/2026-10-04-check-verify-extraction-stability.md`, note 2).
- Spec 0002's relationships table gains the three link properties of AC-16, and its Entity table gains `file_line` (AC-50).
