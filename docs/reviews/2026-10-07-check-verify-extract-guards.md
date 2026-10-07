# Check verify, extract guards (spec 0004's two amendments of 2026-10-06), 2026-10-07

**Run by**: `/check verify`, Claude Opus 5.5, on branch `fix/extract-guards` at `51a30db`
**Spec**: [0004](../specs/0004-first-traced-chain/index.md), the criteria added or amended on 2026-10-06, checked against [verify.md](../specs/0004-first-traced-chain/verify.md)'s two amendment sections
**Verdict**: **pass with gaps**. Of the 45 criteria in scope, 29 are verified live, 15 are tested only, and 1 is not verified. No criterion failed. Feature 5 as a whole stays open, because AC-41 still fails, as experiment 0009 recorded ([the first verify](2026-10-06-check-verify-first-traced-chain.md)).

**Scope and limits.** Free paths only: no paid call was made. Every request to the real API went through the logging proxy of the first verify, in relay mode (the port checked free, the mode read from its log's first line, and no key or credential in any log). It saw 35 calls to the free count endpoint and **0 to `/v1/messages`**. A path that needs a model response cannot run live without spend. So those paths ran through the real command and the real SDK over real HTTP, against the fake local API and fault proxy in `tests/fake_api.py`, and they are labelled **tested only**. All scratch roots sat outside the repository, and `git status` stayed clean.

Statuses, as before:
- **verified live**: the real command or code run here against the real API, the real graph or the committed files, with its output cited.
- **tested only**: shown by a test with a fake client or the fake API, not by a real call.
- **not verified**: neither.

## Evidence

- **L1** `extract --dry-run 0002:Requirements 0010:Context --ceiling 1` from the repository root, exit 0. It printed:
  - The estimate, though `0002 Requirements` is extracted.
  - `per call bound: $0.8701` for `0010 Context` and `$0.8732` for `0002 Requirements`.
  - Wider lines saying "every call writing the cache".
  - `0002:Requirements: a real run would refuse it at the collision check (artifacts/runs/0002/requirements/run-1.json exists).`, with `0010:Context` not named.
- **L2** `extract --dry-run 0010:Context --ceiling 0.5 --root <scratch>`, exit 0: `The ceiling $0.50 is below the largest per call bound $0.8701, so a real run would refuse to start.`
- **L3** The same without `--dry-run`, exit 1: `✗ the ceiling $0.50 is below the largest per call bound $0.8701, so no call is made.`
- **L4** `extract 0010:Context "0007:Feature design" --ceiling 0.88`, exit 1: `✗ … below the largest per call bound $0.8907`. The first unit's bound, $0.8701, fits under that ceiling; the second unit's does not.
- **L5** `--ceiling=nan`, `inf`, `0` and `-1`, each exit 1: `✗ --ceiling USD must be a finite number above 0, not nan.` (and so on for the others). The proxy saw no request from any of the four.
- **L6** `extract --dry-run 0010:Context --ceiling 3`: `Wider total: 6 calls, $3.7347, above the ceiling of $3.00.` followed by `The wider total is above the ceiling, so the run may stop partway at the ceiling…`
- **L7** `extract 0002:Requirements --ceiling 3`, exit 1: `✗ an artifact already exists at artifacts/runs/0002/requirements/run-1.json`
- **R1** `extract --resume 0002:Requirements 0007:Requirements --ceiling 3`, exit 1: `✗ --resume refuses, before any call: 0002:Requirements owes nothing…; 0007:Requirements owes nothing…`
- **R2** `--resume 0010:Context` in the repository, exit 1: `… has no artifact: a plain \`extract\` starts it`
- **R3** `--resume` on a scratch unit holding only `failed-run-2-attempt-2.json`, exit 1: `… cannot be planned: …failed-run-2-attempt-2.json has no attempt 1 before it`
- **R4** `--resume` on a scratch unit whose `run-1.json` is at prompt `0003.0`, exit 1: `… run-1.json was written with prompt_version 0003.0 (now 0003.1)`
- **R5** `--resume 0021:Requirements`, exit 1: `0021:Requirements owes nothing: all 3 runs are settled` (not blocked)
- **R6** `--resume` on a scratch unit whose run 1 holds two model failures, exit 1: `… is blocked: run 1 holds 2 model failures and is not run again`
- **R7** `--dry-run --resume` on a scratch unit with `run-1.json` only, exit 0: `Central total: 2 calls`, `Wider total: 4 calls, $2.4898`, `0010:Context resume: run 2 from attempt 1, run 3 from attempt 1.`
- **R8** The same on a scratch unit whose run 2 holds two transport failures: `0010:Context resume: run 2 from attempt 3.`
- **R9** The same on a scratch unit whose run 1 has a model failure beside its `run-1.json`: `resume: run 2 from attempt 1, run 3 from attempt 1.` (run 1 is left alone)
- **R10** `--dry-run --resume` on a unit with no artifact, exit 1: `… has no artifact`
- Across L1 to R10, the proxy saw 35 calls to `count_tokens` and 0 to `/v1/messages`. Every scratch unit's files were the same after as before.
- **G1** `tracepath load`, twice, on the real graph:
  - `Loaded 18 units …`, and the two manifests are byte identical.
  - The repository's `graph-build.json` is unchanged. The `0021 Requirements` entry lists `['2026-10-04T05:03:37+00:00', '2026-10-04T05:32:04+00:00']`, and these are exactly the `extracted_at` values in its files.
  - `committed_units()` gives `0021 Requirements` three settled runs, and its `run-2.json` records `attempt: 3`.
  - `load --root <scratch with one settled run>` printed `Not loaded: 0010 Context has 1 settled runs of 3, so it is not extracted.` The real graph was reloaded after.
- **F1** A Python snippet with the real settings and the real key, `build_client()` then `run_unit()` on `0010 Context`:
  - `max_retries: 0`.
  - It raised `RetryPathRetired`, not an `ExtractionFailed` or a `UnitFailed`, with the message `… the old retry path is closed, it has no per call ceiling. Extract with \`tracepath extract\` …`.
  - The proxy saw 0 requests.
  - `read_run()` on the four committed failed attempts with no `failure_kind` returned `model` for each.
- **F2** A probe file `src/tracepath/zz_verify_probe.py` containing `import anthropic` was staged, and `pytest tests/test_spend_fence.py -k ac_72` failed: `['src/tracepath/zz_verify_probe.py'] can reach the model outside \`tracepath extract\` …`. With the probe unstaged and deleted, `git status` was clean, and `tests/test_spend_fence.py` plus `tests/test_run_unit_usage.py` passed (14).
- **T1** The fake API tests: `tests/test_extract_guards.py`, `test_extract_failures.py`, `test_extract_command.py` and `test_extract_client.py` all passed, 126 tests. Eight of them ran the real command over real HTTP through the fault proxy:
  - The AC-11 drop before usage, which did not stop the command.
  - Each fault (dropped before usage, cut after output, a 529) recorded as `transport`.
  - AC-70: one request per attempt on a 529.
  - AC-69: two transport failures stopping with the run owed.
  - AC-56: a resume completing run 1 at attempt 3.
  - AC-9: the ceiling stopping before a second call.

## Status per criterion

| AC | Status | Evidence |
|---|---|---|
| AC-6d | verified live | L1 |
| AC-6e | verified live | L1 |
| AC-7b | verified live | L5 (no request made) |
| AC-8 | verified live | L3, L4 (the largest bound is the one checked) |
| AC-8b | tested only | Live: the warning line (L6). Not live: a real run starting with the wider total above the ceiling, which would spend. T1 |
| AC-8c | verified live | L2 |
| AC-9 | tested only | T1 (`test_ac_9_over_http…`) |
| AC-10a | tested only | T1 |
| AC-11 | tested only | T1 (`test_ac_11_over_http…`, finding 1) |
| AC-13 | tested only | T1. A blocked run refused at resume is AC-58, live |
| AC-14b | tested only | T1 |
| AC-18 (reworded) | verified live | G1 |
| AC-48 | verified live | L7 |
| AC-48b | verified live | G1 (`Not loaded …`) |
| AC-55 | verified live | L1 ($0.8701), L4 ($0.8907) |
| AC-56 | tested only | Live: the plan numbers on, `run 2 from attempt 3` (R8). Not live: the attempts being made. T1 |
| AC-57 | tested only | Live: the plan owes a run with no artifact from attempt 1 (R7). Not live: the attempt being made. T1 |
| AC-58 | verified live | R6 (blocked), R9 (settled beside a failure) |
| AC-58b | verified live | R3 |
| AC-59 | verified live | R1 (every unit named), R5 |
| AC-60 | verified live | R2 |
| AC-60b | verified live | R4 |
| AC-61 | tested only | A real plan never collides by construction, so it cannot be triggered live. T1 |
| AC-61b | tested only | T1 |
| AC-62 | tested only | T1 |
| AC-63 | verified live | R7 |
| AC-64 | verified live | R7 |
| AC-64b | verified live | R10 |
| AC-65 | verified live | G1 |
| AC-66 | not verified | It binds the next result record, and none has been written since the amendment |
| AC-67 | tested only | T1 (three faults over HTTP, plus model failures over a mocked transport) |
| AC-67b | tested only | Live: the four committed artifacts read as `model` (F1). Not live: a new failed attempt recording its kind, which needs a call. T1 |
| AC-68 | tested only | T1 |
| AC-69 | tested only | T1 |
| AC-70 | verified live | F1 (the real client's `max_retries` is 0). T1 shows one request per attempt |
| AC-71 | verified live | F1 |
| AC-71b | verified live | F1 |
| AC-71c | verified live | F1 |
| AC-72 | verified live | F2 |
| AC-73 | verified live | G1 |
| AC-73b | verified live | R5 |
| AC-73c | verified live | G1 |
| AC-74 | verified live | F2 (the suite passes under the fixture), G1 (`.env` still supplies Neo4j) |
| AC-74b | verified live | F2 |
| AC-74c | verified live | F2 |

## Gaps (why the verdict is not "pass")

1. **Tested only:** AC-8b, AC-9, AC-10a, AC-11, AC-13, AC-14b, AC-56, AC-57, AC-61, AC-61b, AC-62, AC-67, AC-67b, AC-68 and AC-69. Each needs a model response, or a collision a real plan never produces, and this run made no paid call. They are covered by tests that drive the real command over real HTTP against the fake API.
2. **Not verified:** AC-66, until the next result record is written.
3. **Out of scope here:** feature 5's other criteria were verified on 2026-10-06. This run only checked that `load` and the manifest still behave (G1). AC-41 remains failed.

## Scope

Nothing ticked. Feature 5's `Verify it` covers the whole feature, which stays open while AC-41 fails.
