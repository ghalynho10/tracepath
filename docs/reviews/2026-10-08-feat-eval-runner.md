# Review, feat/eval-runner, 2026-10-08

**Reviewed by**: Sonnet 5.5 (author on a different session; model not recorded in the diff)
**Scope**: 54 files (held-out file and held-out-record excluded; run artifacts and the three `*held*` data files not read), branch vs main
**Verdict**: Approve with nits

## Summary
Adds `tracepath eval` (all five questions, PASS/FAIL/INCONCLUSIVE, no totals), the two new start rules, absence questions, the `eval/runner.json` sidecar with an examples digest, and the held-out refusal guard, plus eight extracted units and the experiment 0011 record. The core in `report.py` is pure, frozen and fully typed; ruff, ruff format and mypy are clean (run on src and tests). The headline issues are two paths that can still end in a raw traceback in `eval`, and some stale or quiet test and doc wording. No blocker or major found. The held-out content was never opened; the held-out test file was read only for its helpers.

## Minor
### 🟡 `eval` leaks a raw traceback on an unreadable snapshot, `src/tracepath/cli.py:540`
**Problem**: `_committed()` calls `records_for_units()`, which does an unguarded `(snapshot / path).read_text()` (`src/tracepath/rebuild.py:168`). `eval` catches only `RebuildFailed` and `RecordError` there. `trace --eval` catches `OSError` and `UnicodeDecodeError` for the same call (`cli.py:478`). A wrong `--snapshot` or a snapshot missing a file the run files cite (inferred from the code; not run) escapes as a traceback.
**Why it matters**: AGENTS.md says failure is a typed exception and the CLI never shows a raw traceback; AC-8c promises message plus exit 1 before any question. `eval` and `trace` now disagree on the same call. A bad `--snapshot` is a plausible slip.
**Suggested fix**: catch `OSError` and `UnicodeDecodeError` around `_committed()` in `eval`, as `trace` does, and add a test with a bad `--snapshot`. `test_eval_command.py` covers a non-UTF-8 cited file (per question) but not this run-level path.

### 🟡 `examples_digest` can raise out of `eval`, `src/tracepath/report.py:470`
**Problem**: `git ls-files` lists a tracked file that is deleted in the work tree, then `(root / path).read_bytes()` raises `FileNotFoundError`. The call at `cli.py:550` is outside any try, so `eval` shows a traceback. Only the `git` subprocess errors are handled.
**Why it matters**: same convention as above; it costs a couple of lines to treat it as `None` (flags unchecked) or to catch `OSError`.
**Suggested fix**: catch `OSError` around the read loop and return `None`, or let the unchecked line print.

### 🟡 Held-out tests skip silently when the file is missing, `tests/test_held_out.py:180`
**Problem**: `real_held_out()` calls `pytest.skip(...)` if `eval/held-out.json` is absent, and the module docstring (lines 4-5) still says "until then those tests skip". The file now exists, so the skip only matters if the file is deleted or moved.
**Why it matters**: deleting the sealed file would turn AC-22, AC-24, AC-25, AC-26 and AC-30 real-file tests into skips, which read as green. verify.md line 63 relies on "none skipped" as a manual check.
**Suggested fix**: replace the skip with a failing assert now that step 10 is done, and update the docstring.

### 🟡 `misplaced_quotes` checks later pieces of a quote loosely, `tests/test_held_out.py:118-122`
**Problem**: only the first `[...]`-separated piece must start inside the cited line. Later pieces need only appear anywhere in the file (`p in whole`).
**Why it matters**: AC-26 says the quoted passage is at its cited line exactly. A multi-piece quote whose tail was lifted from elsewhere would pass. Single-line quotes are fully checked, so the risk is limited to multi-piece quotes.
**Suggested fix**: require later pieces to follow the first, in order, within the remainder of the file, or state in the docstring that only the opening piece is pinned.

## Nits
- ⚪ `src/tracepath/cli.py:298-303`, `_Committed.settled` is a `dict` in a frozen dataclass; AGENTS.md prefers immutable containers (a `Mapping` annotation would at least not invite mutation). `Mapping[str, Any]` in `_question` and `report.py` is a bare `Any` use, though it was already the shape for JSON entries.
- ⚪ `src/tracepath/cli.py:448-455` and `528-535`, the same six-exception tuple is repeated in `trace` and `eval`; one named constant would keep them in step.
- ⚪ `src/tracepath/report.py:380`, `read_question()` is now used only by `tests/test_report.py`; it is dead in `src/`. Keep it as a test seam or fold the test into `read_eval_set` + `question_from`.
- ⚪ `src/tracepath/report.py:366`, `held_out` is read as `payload.get("held_out") is True`, so a held-out file with a truthy non-bool (for example a string) is treated as ordinary and runs without the flag. Low risk, one line to refuse any non-bool `held_out` key.
- ⚪ `CLAUDE.md:35-37`, three advisor-mode rules are bundled into a feature branch and unrelated to spec 0006 (separate commit `17b8dd5`, so easy to keep). Line 37 has a double space before "The build session's reports".
- ⚪ `docs/scope/scope.md` row 6 is still `in-progress` with every box ticked, and `docs/specs/0006-eval-runner/index.md` Status is "In Progress" with open Follow-up items; `verify.md` leaves three held-out steps unticked on purpose (commit `a1ffd21` says so). Fine for now, but `/sync` and the status flip are owed before or at merge.
- ⚪ `_absence_cause` and `_reason` index `ends[1 - i]` (`report.py:708-709`) and assume exactly two link endpoints after the type. `held_relationships` guards the in-unit case with `len(signature) == 3`, but `corpus.held` items are not filtered. Inferred safe; not verified for the across-units case.

## Strengths
- Pure core, edges at the shell: `verdict`, `result_lines`, `resolve_start`, `question_from` take everything as arguments; the shared body `_score_question` is used by both `trace --eval` and `eval`, so AC-2 (identical block text) holds by construction.
- Uncertainty is a value: INCONCLUSIVE never becomes PASS, absence needs an accepted entity, no reaching walk and `no_link`, and each cause is printed (AC-17c). No total or rate is printed anywhere.
- The held-out guard sits in the one shared reader (`read_eval_set`), runs before any graph read, and no file in `src/` names `held-out.json` (grep of `src/` for that name returns only the flag spelling `--release-held-out`).
- Scope discipline: `git log main..HEAD -- src examples` shows `src/` changed only in the code commit `e24801d`, and nothing under `examples/` or `src/tracepath/extract/` changed anywhere on the branch (AC-32, AC-34).
- Experiment 0011 scores its own predictions honestly (all four results right, counts and reasons mostly wrong) and records the spend ($4.30 against about $2.8 central) without adjusting rules afterwards.
- No `Co-Authored-By` trailer in any commit on the branch, as docs/reflexes.md requires. Conventional commit prefixes throughout.

## Test coverage
TESTS = configured. Not run (hard constraint: the suite could release held-out content). By reading: `test_eval_runner.py` (717 lines) covers AC-3 from `git archive 36a6bc5`, start rules, hop-0 marker, K/M, absence outcomes and causes; `test_eval_command.py` drives the CLI over a synthetic root with a real graph for AC-1, 2b, 5-9c, 8b-8d and the undecodable-file case; `test_eval_sidecar.py` covers the digest and unchecked line; `test_held_out.py` runs each file check on a good and a bad synthetic file before the real one, with messages limited to counts. Gaps: a bad `--snapshot` on `eval` (first Minor), a deleted tracked example file (second Minor), and the silent skip above. Integration tests use a real Neo4j fixture per project rule; I saw no driver mocking. Existing `trace --eval` and report tests were updated for AC-4 and AC-10 as the spec says. Generated data (`artifacts/runs/**`, `review-queue.json`, `graph-build.json`) was skimmed by diff stat only.
