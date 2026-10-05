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
