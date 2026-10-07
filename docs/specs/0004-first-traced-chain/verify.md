# 0004. Verify

## Commands

```bash
uv run pytest -m "not integration"   # walk, report, extract controls, load provenance, no API, no Neo4j
uv run pytest -m integration         # the fixture graph in real Neo4j, and `load` over the committed artifacts
uv run mypy
uv run ruff check . && uv run ruff format --check .
uv run tracepath extract --dry-run 0002:Requirements "0002:Feature design" 0007:Requirements "0007:Feature design" --ceiling <the ceiling the engineer approves>
```

## Before any paid call (all checkable with no API spend)

1. `git log` shows this spec's commit pushed, then the commit holding all of `src/`. The rules in `## Held out discipline` are unchanged from the spec's commit, and `src/` is unchanged after its own commit (AC-46b, AC-47).
2. `artifacts/review-log.json` holds 0 entries (AC-45).
3. The `--dry-run` output shows measured input tokens, the cached prefix, the named output source and the central and wider totals (AC-6a to AC-6c). The engineer has given a ceiling.
4. The calibration recount of `0014 Requirements` matches 61,108 tokens, or the command refuses to price.

## Extraction controls, tested with a fake client

| Check | Criterion |
|---|---|
| A broken worked example makes `extract` exit 1 with a message, no traceback, no call | AC-3 |
| An artifact at attempt 1 of any run of any requested unit stops the command before any call | AC-4 |
| An artifact at a retry's path stops the command before that call | AC-5 |
| `--dry-run` makes no extraction call; it prints measured input, the output source, the standard rates and both USD figures (12 and 24 calls) | AC-6a to AC-6c |
| No `--ceiling`, or a wider total over it, exits 1 before any call | AC-7, AC-8 |
| No call is made when the running total plus $0.4144 would pass the ceiling; the message says it is a stop; exit 1 | AC-9 |
| A failed attempt counts at $0.4144; a settled one at its recorded usage and the stated rates | AC-10a, AC-10b |
| Any call after the first that reads no cache stops the run with exit 1 | AC-11 |
| Each artifact is written as the attempt settles; a dropped stream writes a `failed-run-N-attempt-M.json` with null usage and the summary names it | AC-12a, AC-12b, AC-14 |
| An interrupted unit is not resumed: a second run stops at the collision check | AC-48 |
| The command calls the interactive API, not Batch | AC-49 |
| A unit failing after its retry is not run again and the command stops before the next unit | AC-13 |

## The walk, proven on a fixture that is not an eval chain

1. Build the fixture graph in Python (invented specs and entities, a branch, a cycle, a struck entity, an UNCLASSIFIED link, a Record, an Unresolved node, a chain four hops long). Walk it and compare the printed output to a hand written expectation (AC-32).
2. Load the same fixture into a real Neo4j and walk the read back graph; the output matches step 1 (AC-33).
3. Confirm no source file under `src/tracepath/traverse/` or `src/tracepath/graph/read.py` contains `eval` as a path or import (AC-31), and that only `src/tracepath/report.py` opens the eval file.
4. Confirm the order is fixed: shuffle the input tuples and get the same output (AC-26).

## The load, no API call

1. `uv run tracepath load` over the committed artifacts: counts match `committed_units()`, writes all asserted (AC-15).
2. Every relationship in Neo4j carries `prompt_version`, `model` and `commit` (AC-16).
3. `artifacts/graph-build.json` is written, and a second `load` leaves it byte identical (AC-17a to AC-17c, AC-18).
4. The output names units per prompt version and loads a mix without refusing (AC-19).
5. Every entity carries `file_line` equal to `unit.start_line + line - 1` (AC-50), and the output states how many links collapsed (AC-51).

## The result, after the paid run (recorded in `experiments/0009-first-traced-chain/README.md`)

1. The four sections each have three settled runs, or the failure is recorded and named (AC-12a, AC-12b, AC-13, AC-14).
2. `trace --eval 3` printed the chain; every step cites file, section, line and commit, and states its prompt version (AC-28a to AC-28c, AC-29, AC-30). A line printed for an entity is a file line, which you can check by eye against the snapshot.
3. The prediction table is copied from the spec as written and scored item by item, wrong guesses marked wrong (AC-37, AC-38).
4. AC-40's count is stated, and if it is not 0 the links are listed and the "chooses only among siblings" claim is withdrawn.
5. AC-41 holds, or the result says it failed and feature 5 is not marked done.
6. A second `trace --eval 3`, then `load` and a third, print identical output (AC-42, AC-43).
7. The commits are ordered spec, then `src/`, then the first run artifact, and nothing under `src/` or `examples/` and none of the four units' run files changed after the `src/` commit (AC-46a, AC-46b, AC-47).
8. Actual cost against the estimate, and any attempt with null usage named.
9. The summed artifact usage (failed attempts included) is compared with the Console's usage for the day of the run, with no other tracepath API use that day, and any gap is stated (AC-54).
10. If a defect in the walk or report code was found afterwards, the first result stands as recorded and the fix is scored as a second, labelled result on the same run files (AC-53).

## Acceptance checklist

- [ ] AC-1, AC-2a, AC-2b: question 3, Record meaning recorded, scope reword carried
- [ ] AC-3 to AC-14, AC-48, AC-49: extract
- [ ] AC-15 to AC-19, AC-50, AC-51: load and the build record
- [ ] AC-20 to AC-33: the walk and its fixture
- [ ] AC-34 to AC-41, AC-52: the report step and the question 3 result
- [ ] AC-42 to AC-47, AC-53, AC-54: repeatability, errors, discipline

## Build notes · updated 2026-10-05 (/develop)

_Where each criterion is tested, and one step per row of the spec's Value sourcing table. Added after the build; the steps above are unchanged._

### Where each criterion is tested

| Criteria | Test file |
|---|---|
| AC-3 to AC-14, AC-48, AC-49 | `tests/test_extract_command.py` (fake client, scripted calls, a mocked transport for AC-49) |
| AC-15, AC-16, AC-19, AC-44 (load), AC-50 | `tests/test_load_command.py` (real Neo4j, a copy of the committed artifacts) |
| AC-16, AC-17a to AC-17c, AC-18, AC-48 (load side), AC-50, AC-51 | `tests/test_load_provenance.py` (no database) |
| AC-20 to AC-32 | `tests/test_walk.py` against `tests/fixtures/trace-fixture-expected.txt` |
| AC-33 | `tests/test_walk_graph.py` |
| AC-20, AC-42, AC-44 (trace START) | `tests/test_trace_command.py` |
| AC-34 to AC-41, AC-52, AC-31 (report side) | `tests/test_report.py` |
| AC-34, AC-42, AC-43, AC-44, AC-52 through the command | `tests/test_trace_eval.py` (real graph, a synthetic eval file citing spec 0012 only) |

### One step per Value sourcing row

- [ ] `extract --dry-run`, input tokens per unit: each printed count changes when the unit changes; the four question 3 units counted 59,090, 65,967, 60,363 and 67,865 on 2026-10-05.
- [ ] `extract --dry-run`, cached prefix: point the fake count for `0014 Requirements` at 61,000 and the command refuses to price (`test_a_calibration_count_that_moved_refuses_to_price`); the real count matched 61,108.
- [ ] Output per call, central: the printed line names `0021 ## Requirements` 27,384 for a Requirements unit and `0006 ## Feature design` 26,721 for a Feature design unit; a section with no measured figure prints "not priced".
- [ ] Output per call, wider: every unit's wider line names 39,234 and experiment 0005.
- [ ] Rates: the first printed line says standard interactive pricing, not Batch, at 2.00, 10.00, 4.00 and 0.20.
- [ ] Call counts: 12 central and 24 wider for the four question 3 units.
- [ ] Flat failure cost: a failed attempt adds exactly $0.4144 whatever it recorded.
- [ ] A settled attempt's cost: recorded input, output, cache write and cache read at the rates above.
- [ ] Stop wording and exit code: "stopping here before RECORD:SECTION run N attempt M: ceiling" and "stopping: call N read no cache", both exit 1.
- [ ] The ceiling: only the `--ceiling` flag sets it, and `extract` without it exits 1 naming the flag.
- [ ] Prompt version, model, effort, runs per unit: every new artifact carries `0003.1`, `claude-sonnet-5`, `medium`, and each unit has three settled runs.
- [ ] `load`, per unit counts: `graph-build.json` counts match the rebuilt `UnitResult`s.
- [ ] `load`, link provenance: every link's `prompt_version` equals the manifest's version for its `(record, section)`; a link from a `0003.0` unit shows `0003.0`.
- [ ] `load`, entity `file_line`: `0014 ## Requirements` entities at section lines 5, 6 and 7 sit at file lines 23, 24 and 25.
- [ ] `load`, collapsed count: 14 of 85 resolved links collapsed over the 14 committed units on 2026-10-05.
- [ ] `load`, `review_log_entries`: equals the length of `artifacts/review-log.json` (0).
- [ ] `trace`, entity, link, Unresolved and Record steps: each prints the properties the table names, checked line by line in `trace-fixture-expected.txt`.
- [ ] `trace`, depth limit: the fixture's hop 3 step says "1 typed link not followed".
- [ ] `trace --eval`, start id: "spec 0002 AC-10 (struck)" gives `0002/AC-10`.
- [ ] `trace --eval`, expected items: question 3 gives lines 31, 35, 142, 36 and 232, with tokens only on 31, 35 and 36.
- [ ] `trace --eval`, AC token: matched whole, so `AC-1` is not found inside `AC-13`.
- [ ] `trace --eval`, reasons: each of the six codes fires on its own case in `tests/test_report.py`.
- [ ] `trace --eval`, outside links: 0 over the 14 committed units before the paid run.
- [ ] `trace --eval`, held links: a held `satisfies` link naming `0012/AC-1` gives `link_held`.

### Readings taken during the build

- AC-11: the no cache stop reads only a call that reported usage. A call refused before it reached the model reports zeros, and a stream dropped before `message_start` reports nulls; neither says anything about the cache, so the run's one retry still covers it.
- AC-48: a unit with fewer than three settled runs is not loaded at all, so its items stay `section_not_extracted`. `load` names it ("Not loaded: ..."), and routing would otherwise fail on a single run.
- AC-7: `--ceiling` is required for `--dry-run` too, read literally ("exits 1 ... before any call").
- AC-17b: a unit's accepted links are the links the load writes from its section; its held links are those routing held inside it plus those held for another unit's entity.

## Verify: the 2026-10-06 amendment · updated 2026-10-06 (/develop)

_Steps derived from the amended acceptance criteria and the new Value sourcing rows. None needs a paid call: the fake local API and fault proxy in `tests/fake_api.py` stand in for Anthropic, as `/check verify` did on 2026-10-06 with a real proxy. A scratch `--root` keeps every run file out of `artifacts/`. `/check verify` runs these; `/test` locks the durable ones (most are already in `tests/test_extract_guards.py`)._

### Commands

- [ ] `uv run tracepath extract 0010:Context --ceiling nan` (then `inf`, `0`, `-1`) → exit 1 naming `--ceiling`, no request reaches the API → AC-7b
- [ ] `extract --dry-run 0002:Requirements --ceiling 1` from the repository root → the estimate prints and it exits 0, though `0002 Requirements` is extracted → AC-6d
- [ ] The same dry run with `0010:Context` added → only `0002:Requirements` is named as a unit a real run would refuse → AC-6e
- [ ] `extract --dry-run 0010:Context --ceiling 0.5 --root <scratch>` → the line "a real run would refuse to start", exit 0 → AC-8c
- [ ] `extract 0010:Context --ceiling 0.5 --root <scratch>` against the fake API → exit 1, "below the largest per call bound", no messages call → AC-8
- [ ] Two units whose counts differ, with a ceiling between their bounds → refused before any call, though the first unit's bound fits → AC-8, the "bound AC-8 checks" row
- [ ] `extract 0010:Context --ceiling 3 --root <scratch>` against the fake API → the line "may stop partway at the ceiling", and the run starts → AC-8b
- [ ] The dry run for `0010:Context` prints "per call bound: $0.8701", and `0007:Feature design` prints $0.8907 → AC-55, the per call bound row
- [ ] The dry run's wider line says "every call writing the cache", and for `0010:Context` the wider total is 6 × $0.6224 = $3.7347 → the cache write row
- [ ] `extract 0010:Context --ceiling 1 --root <scratch>` against the fake API → one call, then "stopping here before 0010:Context run 2 attempt 1: ceiling", exit 1 → AC-9
- [ ] With the proxy dropping messages call 1 before any event → the failed attempt is counted at $0.8701, not its null usage → AC-10a
- [ ] The same run → the retry writes the cache and reads 0, and the command does not stop: four calls, three settled, exit 0 → AC-11 (finding 1)
- [ ] The proxy failing messages calls 1 and 2 (a drop and a 529) → "run 1 is not settled after 2 attempts … The run is owed", exit 1, two requests only → AC-68, AC-69
- [ ] A scripted run with two schema failures on run 1 → "failed after its retry (2 model failures)", exit 1 → AC-13
- [ ] Each fault (dropped before usage, cut after the output, a 529) → the failed artifact's `failure_kind` is `transport`; a schema failure and a `max_tokens` stop give `model` → AC-67, AC-67b, the `failure_kind` row
- [ ] `read_run()` on the four committed failed attempts with no `failure_kind` → each reads `model`, and no other failed file in `artifacts/` lacks the field → AC-67b
- [ ] With the proxy answering 529 once → the proxy sees exactly one request per written attempt → AC-70
- [ ] Any run's summary → two totals, the guard's and the recorded usage's → AC-14b, the summary row
- [ ] Plain `extract 0010:Context` again on a unit cut short → stops at the collision check → AC-48
- [ ] `load` over a root holding a unit cut short → "Not loaded … settled runs of 3", and `trace --eval` with a synthetic item there names `section_not_extracted` → AC-48b
- [ ] After the two transport failures above, `extract 0010:Context --resume --ceiling 3` → run 1 resumes at attempt 3 and runs 2 and 3 run → AC-56, AC-57, the resume plan row
- [ ] `--resume` on a unit with `run-1.json` beside failed files, and a run with two model failures → no attempt for either; the second is refused as blocked → AC-58, AC-59
- [ ] `--resume` on a unit holding `failed-run-2-attempt-2.json` and no attempt 1 → exit 1 naming the file → AC-58b
- [ ] `--resume` over two fully extracted units → exit 1 before any call, naming both → AC-59
- [ ] `--resume` on a unit with no artifact → exit 1, "a plain `extract` starts it" → AC-60
- [ ] `--resume` on a unit whose settled run is at prompt `0003.0` → exit 1 before any call, naming the difference → AC-60b
- [ ] A resume plan whose next attempt is already written → the preflight stops it; a taken attempt partway through → stopped before that attempt → AC-61, AC-61b
- [ ] A resume with a ceiling one bound above its first call → stops before the second owed run → AC-62
- [ ] `--dry-run --resume` on a unit with run 1 settled → "Central total: 2 calls", "Wider total: 4 calls", and the plan line "run 2 from attempt 1, run 3 from attempt 1" → AC-63, AC-64, the resume call counts row
- [ ] `--dry-run --resume` on a unit with no artifact → exit 1 → AC-64b
- [ ] After a resume, `load` → the unit's manifest entry lists two `extracted_at` values, failed files included, and a second `load` is byte identical → AC-65, the `extracted_at` rows
- [ ] The check order: a run with a collision makes only the free count calls before it refuses → the check order row

### Acceptance criteria coverage (the amendment)

- AC-6d, AC-6e, AC-7b, AC-8, AC-8b, AC-8c, AC-9, AC-10a, AC-11, AC-13, AC-14b, AC-48, AC-48b, AC-55 to AC-58b, AC-59 to AC-61b, AC-62 to AC-64b, AC-65, AC-67 to AC-70: covered by the steps above.
- AC-66 binds the next result record, so it is checked when one is written, not here.

## Verify: the second 2026-10-06 amendment · updated 2026-10-06 (/develop)

_No paid call. Locked by `tests/test_run_unit_usage.py` and `tests/test_spend_fence.py`._

- [ ] `run_with_retry()`, `run_unit()`, `extract_unit()` and `extract_units()` each raise `RetryPathRetired` with no model call made → AC-71
- [ ] The refusal's message names `tracepath extract` → AC-71b
- [ ] `RetryPathRetired` is neither an `ExtractionFailed` nor a `UnitFailed`, and passes through `run_unit()` unchanged → AC-71c
- [ ] Add a scratch `.py` file outside `tests/` that contains `import anthropic` (or `build_client`, or `extract_once`), `git add` it, run `uv run pytest tests/test_spend_fence.py` → AC-72's test fails naming the file; remove it and the test passes → AC-72
- [ ] `committed_units()` over the repository returns `0021 ## Requirements` with three settled runs → AC-73
- [ ] Its `run-2.json` records `attempt: 3` → AC-73c
- [ ] `resume_runs()` on `0021:Requirements` refuses it as owing nothing, not as blocked → AC-73b
- [ ] Inside any test, `ANTHROPIC_API_KEY` is `sk-ant-test` and `ANTHROPIC_BASE_URL` is `http://localhost:1` → AC-74, AC-74b
- [ ] With a `.env` holding another key, `load_anthropic_settings()` in a test still returns `sk-ant-test`, and the Neo4j integration tests still read their password from `.env` → AC-74, AC-74c
