# Review, feat/first-traced-chain, 2026-10-06

**Reviewed by**: Sonnet 5.5 (author model not stated)
**Scope**: 24 code files (14 source, 10 test), branch vs main (merge base d2c2e7b)
**Verdict**: Changes requested

## Summary

The branch adds the `extract`, `load` and `trace` commands, link provenance, `file_line`, the build manifest, the pure walk and the report step. The walk, the renderer and the Cypher read are clean: small, pure, ordered as AC-26 asks, and well tested. The headline problem is in the build manifest: `held_links` counts held entities as held links, so `artifacts/graph-build.json` is wrong for eight units, and the unit test copies the same mistake so it passes. The rest is error handling and robustness at the edges. I did not re-report the four findings already recorded in `docs/reviews/2026-10-06-check-verify-first-traced-chain.md`.

How I checked: I read the spec, then each changed source file in full, then ran a read only script over the committed artifacts to confirm the manifest problem (verified, below). Test files were read selectively, the walk, load provenance and extract tests, not line by line. I did not run the test suite myself, I relied on the stated result of 591 passing.

## Major

### 🟠 The manifest counts held entities as held links, `src/tracepath/pipeline.py:503`
**Problem**: `graph_build()` computes `held_inside` as every review item whose `canonical_id is None`. A held relationship has no id, but so does a held entity that only some runs produced and that has no located line (`compare.py` builds those review items from `leftovers` with a two part signature). The report step already knows this and filters on `len(item.signature) == 3` (`report.py:257`). The manifest does not.
**Why it matters**: Verified by running `committed_units()` over the committed artifacts: the two counts differ in eight units (0001 Binding rules 31 vs 23, 0002 Feature design 62 vs 36, 0006 Feature design 28 vs 15, 0007 Feature design 32 vs 22, 0013 Feature design 13 vs 6, 0015 Feature design 24 vs 19, 0021 Requirements 50 vs 44, feature-9 section 9 18 vs 16). The committed `artifacts/graph-build.json` therefore overstates `held_links` for 0002 Feature design as 69 when the real figure is lower. AC-17b asks for the held link count, and this file is the record someone will use to explain a missing link in the chain.
**Suggested fix**: Count only items with a three part signature, ideally by sharing one helper with `held_relationships()` in `report.py` so the two cannot drift. Rewrite `graph-build.json` afterwards. The test below must change too.

## Minor

### 🟡 The manifest test repeats the bug, `tests/test_load_provenance.py:218`
**Problem**: `test_the_manifest_counts_accepted_entities_and_accepted_and_held_links` computes its expected value with the same `canonical_id is None` filter, so it agrees with the code by construction. It also runs only on 0014 Requirements, a unit with no held entities, so no input could expose the difference.
**Why it matters**: A test that mirrors the implementation proves nothing, and AC-17b is untested for any unit that holds an unlocated entity.
**Suggested fix**: Assert against a fixed number, and include a unit that has unlocated held entities (0002 Feature design, 0001 Binding rules).

### 🟡 `--ceiling` accepts `nan` and `inf`, `src/tracepath/cli.py:302`
**Problem**: Typer parses any float. With `nan`, both `priced.wider_usd > ceiling` (`cli.py:350`) and `total + FLAT_FAILURE_USD > ceiling` (`metered.py:175`) are false, so neither the AC-8 gate nor the AC-9 stop can ever fire. `inf` has the same effect. A zero or negative ceiling is refused, which is fine.
**Why it matters**: The ceiling is the whole spending control, and the project has a standing rule about spend. It takes a deliberate mistake to hit, but the failure is silent.
**Suggested fix**: Refuse a ceiling that is not finite and positive, with the same plain message and exit 1, before any call.

### 🟡 An error during the paid loop loses the summary and prints a traceback, `src/tracepath/cli.py:356`
**Problem**: `run_metered()` is called outside any `try`. `write_run()` can still raise `ArtifactCollisionError` or `OSError` after a call has been paid for (for example a file created between the preflight and the write, or a full disk), and `extract_once()` can raise something other than `ExtractionFailed`. The exception escapes, so there is no `summary_lines()` output and AC-44 is broken (traceback, not a message).
**Why it matters**: This is the one place where output is most valuable, since money has just been spent. The attempt's result is lost with no line saying what was spent.
**Suggested fix**: Catch typed failures around the loop and still print what was written so far. That needs `run_metered` to return its partial outcome, for example by catching inside the loop and returning it as a stop value, as the other stops are.

### 🟡 Failed calls that return zeros are not named in the null usage summary, `src/tracepath/extract/client.py:533` (read by `src/tracepath/extract/metered.py:123`)
**Problem**: An `anthropic.APIError` becomes an attempt with `input_tokens=0, output_tokens=0`, not null. `_null_usage()` only tests for `None`, so such an attempt is counted as failed in the totals but is not listed by AC-14's "Attempts with null usage" line. AC-12b asks for null usage on a failed or dropped attempt. Only a mid stream drop gives nulls.
**Why it matters**: The summary can say "none" when an attempt failed with unknown billing, which is the case the AC exists for. The flat cost still protects the total.
**Suggested fix**: Either record null usage for an APIError attempt, or have the summary list every failed attempt and say which ones reported usage.

### 🟡 `trace --eval` can still raise a raw traceback on a malformed eval file, `src/tracepath/report.py:150`
**Problem**: `read_question()` catches only file and JSON errors. `payload["entries"]`, `step["file"]`, `step["record"]`, `int(step["line"])` and `trace[0].get(...)` raise `KeyError`, `ValueError` or `AttributeError` when the file or an entry is the wrong shape, and `_holding()` (`report.py:204`) raises `IndexError` for an expected line above the first unit of its file. Only `EvalEntryUnusable` is caught by the CLI.
**Why it matters**: AC-44 lists "an unusable eval entry" among the failures that must print a message and exit 1. The current eval file is fine, so this bites when feature 6 adds entries.
**Suggested fix**: Wrap the shape reads in `question_from()` and turn them into `EvalEntryUnusable` naming the question and the missing field. Make `_holding()` raise a typed error for a line before the first unit.

### 🟡 `load` and `trace` do not handle errors from the driver or from reading artifacts, `src/tracepath/cli.py:197` and `:261`
**Problem**: Only `GraphUnavailable` (raised at connect) is caught. A Neo4j error during `clear()` or a write (`ClientError`, a dropped connection) and a bad run artifact (`json.JSONDecodeError`, `KeyError` in `read_run()`, a bad `review-log.json` in `review_log_entries()`) surface as tracebacks.
**Why it matters**: `load` clears the graph first, so a failure partway leaves a half built graph with no message and no manifest. AC-44 says typed failures exit 1 cleanly. This also sits next to the project rule that failure is a typed exception.
**Suggested fix**: Wrap the driver errors in `GraphWriteFailed` or `GraphUnavailable` at the edge, and turn artifact read errors into `RebuildFailed`. Print a line saying the graph may be partial when the failure comes after `clear()`.

### 🟡 `held_links` and `accepted_links` double count when two units share a section name, `src/tracepath/pipeline.py:505`
**Problem**: Both are matched by `(file, section)` or `(record, section)`, so spec 0007's two `Build plan` units each get the other's links. This is the known duplicate section follow up in the spec, but the manifest now publishes the wrong numbers for it rather than just the walk being unable to tell them apart.
**Why it matters**: Low today, since only the four question 3 units are new. Feature 6 will load every unit.
**Suggested fix**: Add the unit's start line to the match once links carry it, or raise a typed error when two loaded units share a place, as `link_provenances()` already does for differing provenance.

## Nits

- ⚪ `src/tracepath/report.py:34`, `FULL_RUNS = 3` duplicates `RUNS_PER_UNIT` in `config.py`, which `rebuild.py` uses. Import the one constant so the report and the rebuild cannot disagree.
- ⚪ `src/tracepath/graph/read.py:29`, the `ORDER BY` before `collect` is not a guaranteed order in Cypher. It is harmless because `graph_slice()` sorts again, but the comment says the read is deterministic on its own. Say that the sort in Python is what guarantees it.
- ⚪ `src/tracepath/traverse/walk.py:139`, `unfollowed` counts links, not distinct unvisited nodes, so two links to one unvisited node print "2 typed links". That matches the wording of AC-23, but say "links" explicitly in the docstring.
- ⚪ `src/tracepath/extract/address.py:35`, the record is put straight into a glob pattern. A local tool, so no risk, but a record with a glob character gives a confusing "more than one spec" message. A short check for four digits or `scope` or `feature-N` would give a better error.

## Strengths

- The walk is a genuinely pure function over a frozen slice, with the neighbour order, the first path rule and the terminal stops each in one small place, and the rules are stated without reference to any question.
- `load()` settles every row and every provenance before it clears the graph, so a refused load leaves the previous graph standing. `link_provenances()` refuses an ambiguous place instead of guessing.
- `run_metered()` returns every stop as a value with plain wording, writes each attempt as it settles, and checks collisions before a retry is paid for, which keeps to the reflex about stopping by structure.
- The estimate refuses to price when the calibration unit count has moved, so a changed prompt cannot silently reuse old figures.
- The report's reason priority is implemented exactly in AC-38's order, and the AC token is kept to the entry's own line.

## Test coverage

Strong around the walk (both directions, each of the seven types, `PART_OF`, cycle, depth limit, order stability, no mention of `eval/`), the render lines, the provenance stamping, the report scoring and the metered run with a fake client. The real Neo4j round trip for the fixture covers AC-33. Gaps: the manifest held link count (finding above, the test mirrors the code), a non finite `--ceiling`, an exception raised from `write_run()` or the client mid run, a malformed eval entry, and a `trace --eval` where an expected line falls before the first unit. The suite is stated to pass (591 tests), and I did not rerun it.

Note on the frozen `src/` commit (AC-47, AC-53): the major finding changes `src/` and a committed artifact, so it belongs in the separate fix commit and a second labelled result. It does not touch the walk or report, so the question 3 result itself is unaffected.
