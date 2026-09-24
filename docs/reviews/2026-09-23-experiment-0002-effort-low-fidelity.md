# Review, experiment/0002-effort-low-fidelity, 2026-09-23

**Reviewed by**: Claude Sonnet 5 (author on Claude Opus 5, confirmed by the engineer)
**Scope**: 38 files, branch vs `main` (merge base `ee2e2643b0a8fa4d633e0de28615e3096fd0f598`)
**Verdict**: Changes requested

## Summary

This branch closes the two gaps `/check verify` found in the data model build: per-attempt
token usage on run artifacts (so a failed call's cost is never lost) and a review queue
that is actually written and byte-stable. It also rewrites `compare_runs()`/`route_runs()`
for AC-11's amended agreement rule (flags out of the signature, counts instead of sets, a
held-link outcome for an unaccepted endpoint, and `span_not_located` for an unlocatable
derived entity), adds `rebuild.py` to replay a run from committed artifacts with no API
call, and wires a `review-queue` CLI command. The spec and test work behind this is careful
and the comparator rewrite in particular is well reasoned and well tested — every
non-obvious rule change has a docstring pointing at the acceptance criterion and a named
regression test.

Three real defects survived into this diff, though, all around the edges of the new
per-attempt/failure-recovery machinery: a committed script that can no longer run because
its call site wasn't updated when `build_artifact()`'s signature changed, a promised
failure-recovery path (`UnitFailed`) that nothing in the codebase actually consumes, and a
defensive guard in `resolve_accepted()` that is evaluated in the wrong order and could
never do what it was written to do. None of the three are exercised by `mypy`/`pytest`
today, which is exactly why they survived.

## Major

### 🟠 `calibrate_effort.py` cannot run: `build_artifact()` call is missing now-required arguments, `experiments/0002-effort-low-fidelity/calibrate_effort.py:56-67`

**Problem**: `build_artifact()` was changed in this same branch to require `input_tokens`
and `output_tokens` (`src/tracepath/artifacts.py`, no default value on either parameter).
`calibrate_effort.py`'s own call site was not updated — it builds the artifact from
`result.output` alone and never passes those two keywords. Confirmed by binding the actual
signature: `TypeError: missing a required argument: 'input_tokens'`.

**Why it matters**: This experiment is the one this branch's own decision rests on — its
README states "Effort stays `medium`" and cites this script as the tool that produced the
evidence. The script's own README records it was run at an earlier code commit
(`2bed820`), before the signature changed; nothing has run it since. As committed today it
cannot be re-run to reproduce or extend that evidence, and nothing catches this: mypy's
`files` list in `pyproject.toml` is `["src", "tests"]`, so `experiments/` is untyped, and
pytest's `testpaths` is `["tests"]`, so it is never imported or executed by CI either. A
script that silently bit-rots the moment its dependency's signature moves is a trap for
whoever next tries to recalibrate effort.

**Suggested fix**: Pass `input_tokens=result.input_tokens, output_tokens=result.output_tokens`
(available on the `RunOutcome` the script already holds as `result`) into the
`build_artifact()` call.

### 🟠 `UnitFailed` carries a failed run's artifacts, but nothing in the codebase ever catches it to write them, `src/tracepath/pipeline.py:86-97`, `experiments/0001-ac14-type-stability/run.py:140`, `experiments/0003-feature-design-testscenario/run.py:85`, `experiments/0002-effort-low-fidelity/calibrate_effort.py:51`

**Problem**: `UnitFailed`'s docstring is explicit about its purpose: "The artifacts are
carried out of the failure rather than lost with it, so the shell can still write them. A
unit that dies without writing what its calls cost is the defect spec 0001's artifact
storage amendment exists to close." `tests/test_run_unit_usage.py` proves the exception
does carry the artifacts. But `grep -rn UnitFailed` across the repo shows it is raised in
exactly one place and never caught anywhere — not in `cli.py` (the only production
command, `review-queue`, never calls `run_unit`), not in either of the two experiment
scripts that do call `run_unit` (`experiments/0001-ac14-type-stability/run.py:140`,
`experiments/0003-feature-design-testscenario/run.py:85`), and the sibling exception
`ExtractionFailed` raised by `run_with_retry()` is likewise uncaught in
`experiments/0002-effort-low-fidelity/calibrate_effort.py:51`.

**Why it matters**: This is precisely the failure mode the amendment was written to close
— spec 0001's pipeline artifact storage row and `docs/specs/0002-data-model/verify.md`'s
checked-off item both frame it as solved ("This is the case that made the first 21 call
run's cost unrecoverable"). In the code as it stands, if a unit fails after its retry
during a real run, `run_unit()` raises `UnitFailed` out of an unhandled call site, the
process exits on the traceback, and the failed attempts' artifacts — the ones the whole
mechanism exists to preserve — are never written to disk, because building a `RunArtifact`
in memory is not the same as persisting it. The cost is lost exactly the way it was in the
run this amendment cites as its own motivating incident.

**Suggested fix**: Either give the shell scripts (and any future production driver) a
`try/except UnitFailed` that writes `exc.artifacts` via `write_run()` before re-raising or
exiting, or fold that persistence into `run_unit()`/a thin wrapper so every caller gets it
for free. Whichever shape, it needs a test that drives it through a real write, not just
one that shows the exception carries the data.

### 🟠 `resolve_accepted()`'s `known_ids` guard is evaluated after the access it's meant to protect, `src/tracepath/pipeline.py:203-214`

**Problem**:
```python
known_ids = frozenset(
    entity.canonical_id
    for result in results
    for entity in result.identified[0].entities
    if result.identified
)
```
In a comprehension, clauses run in the order written: `for result in results`, then
`for entity in result.identified[0].entities`, then `if result.identified`. The guard is
the *last* clause, so `result.identified[0]` is indexed before it is ever checked —
confirmed directly: `frozenset(e for r in [R(())] for e in r.identified[0] if r.identified)`
raises `IndexError: tuple index out of range` rather than skipping the empty result. Two
lines later, `identities = identities_of(result.identified[0])` (line 214) indexes the same
way inside the main loop with no guard at all.

**Why it matters**: Nothing in the current codebase constructs a `UnitResult` with an empty
`identified` tuple — `run_unit()` only returns after all `runs_per_unit` succeed, and
`rebuild.committed_units()` only groups artifacts that exist, so this is dormant today
(`tests/test_reload_artifacts.py::test_every_committed_unit_has_all_three_of_its_runs`
pins that invariant). But the guard's presence is itself evidence the author anticipated
this case and meant to handle it, and the moment the previous finding (`UnitFailed`
wiring) is built out — or any other path that can hand `resolve_accepted()` a partial
`UnitResult` — this raises an untyped `IndexError` instead of skipping the result, in
direct violation of AGENTS.md's "real failures raise typed exceptions... never a raw
traceback" rule. It is broken exactly at the case it exists for.

**Suggested fix**: Move the filter before the indexing clause (`for result in results if
result.identified for entity in result.identified[0].entities`), and guard line 214 the
same way (e.g. `continue` past a result with no identified output before computing
`identities`).

## Nits

- ⚪ `src/tracepath/rebuild.py:216`, `if a.output is not None` in `committed_units()`'s
  identify step is currently unreachable: only `run-*.json` is globbed, and `run_path()`
  guarantees a settled run's `output` is never null (a null-output artifact always writes
  to `failed-run-*` instead). Harmless, but worth a comment if it's meant as future-proofing
  rather than a leftover.
- ⚪ `src/tracepath/rebuild.py:373`, `needed & seen` in `records_for_units()` is always
  equal to `needed` at that point (`seen` already contains every id in `built`, and the
  filter is over `built`), so the `& seen` adds nothing over `needed` alone.

## Strengths

- The AC-11 comparator rewrite (`src/tracepath/extract/compare.py`) is exemplary: every
  non-obvious rule (flags out of the signature, count-based multiset comparison, the
  `span_not_located` carve-out for unlocatable derived entities, the two-code-path leftover
  branch) is explained in a module docstring that also says what naive "simplification"
  would break, and each has a named regression test in `tests/test_extract_identity.py`
  and a line in `docs/specs/0002-data-model/verify.md` tying it back to the acceptance
  criterion.
- `artifacts.py`'s handling of the failed-attempt case (nullable `output`, required
  `error`, the `failed-run-N-attempt-M.json` naming that keeps a rebuild's `run-*.json` glob
  from miscounting a failure as a fourth run) is precise and directly tested from both
  `test_artifacts.py` and `test_rebuild.py`.
- `rebuild.py` genuinely proves spec 0001's "the graph is derived and disposable, the JSON
  is the source of truth" claim rather than just asserting it — `committed_units()` really
  does replay a full run from committed files with no network or database access, and
  `test_reload_artifacts.py` exercises it against the real committed corpus data.

## Test coverage

Strong on the areas the branch's own docstrings call out as hazards (flag churn, count vs.
set comparison, held-link routing, queue stability, the null-`line` derived entity case) —
each has a named test. The three findings above are exactly the gaps that coverage misses:
no test constructs a `UnitResult` with an empty `identified` (so the misplaced guard in
`resolve_accepted()` was never exercised), no test drives `run_unit()`'s `UnitFailed` path
through an actual persistence step (only through the exception's own attributes, in
`tests/test_run_unit_usage.py`), and `experiments/` scripts sit outside both `mypy`'s
`files` list and pytest's `testpaths`, so `calibrate_effort.py`'s broken call site has no
gate that could have caught it.
