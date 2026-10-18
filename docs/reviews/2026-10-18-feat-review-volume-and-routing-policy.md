# Review, feat/review-volume-and-routing-policy, 2026-10-18

**Reviewed by**: Claude Sonnet 5.5 (author model: Opus, confirmed by the engineer)
**Scope**: 42 files, branch vs main (merge base 8d866bc)
**Verdict**: Approve with nits

## Summary
The branch adds the narrow hold rule, flips two defaults (narrow hold on, held view on), and adds the hold ratio and four way comparison scripts with their tests. The routing logic in `route_runs()` holds up when traced by hand: a link releases only when every endpoint it waits on is accepted, `runs_disagree`, `span_not_located` and `unclassified_type` are never released, and a link that stays held keeps only the reasons still true. No blocker or major was found. The headline issues are a silent default on `eval` and `trace --eval` that can print a held view label over a graph with no held items, and a ratio file whose header now misdescribes what it measured.

Checks run (all free): `uv run mypy` passes (96 files), `uv run ruff check .` passes, `uv run ruff format --check .` passes. The unit test run (`pytest -m "not integration"`) finished after the review was written, rerun by the main session: 975 passed, 113 deselected. Integration tests (Neo4j) were not run in this review.

## Minor
### 🟡 The held view default can label a score "held" over a graph that holds nothing held, `src/tracepath/cli.py:764` (also `:672`)
**Problem**: The "graph holds no held item" refusal now fires only when `--with-held` is given by name (`with_held is True`). With no flag, `eval` and `trace --eval` resolve the held view to on, read the graph with `with_held=True`, and print the held label (`header.append(HELD_LABEL)`, line 783) even when the graph was loaded with `--no-with-held`.
**Why it matters**: After `tracepath load --no-with-held`, a plain `tracepath eval` reports under a heading that says held items are shown, while no held item exists. Every step then reads as "not reached" instead of "reached only as held". That is a stale default silently applied and a report that misstates what was scored. The narrow hold setting has a manifest check for exactly this reason (`_refuse_narrow_hold_mismatch`), the held view does not.
**Suggested fix**: Decide the held setting from `graph-build.json` (`held_view` key present or absent) when no flag is given, or refuse a mismatch the way the narrow hold setting does. At minimum, drop the held label when `_holds_held(graph)` is false. Add one test that loads with `--no-with-held` and then runs a bare `eval`; no current test does (`test_given_no_held_flag_eval_and_trace_eval_show_the_held_view` only covers a graph that has held items).

### 🟡 The ratio file says "default routing" but measures routing without the narrow hold rule, `experiments/0014-review-volume-and-routing-policy/measure_hold_ratio.py:49` and `data/hold-ratio.md:3`
**Problem**: The script calls `committed_units(ROOT, SNAPSHOT)`, whose `narrow_hold` default is still `False`, and writes "default routing" into the file header. Since commit cb28c68 the project default routing has the narrow hold rule on, which gives 526 rows, not the 990 the file reports.
**Why it matters**: A reader taking "default routing" at its word today would expect 526. The 990 figure is correct as the pre flip baseline the spec asked for, but the label now points the wrong way. The README states "Without the narrow hold rule", which is right.
**Suggested fix**: Change the header and docstring to say "without the narrow hold rule, no code pass" and regenerate the file, or pass the flag explicitly so the meaning cannot drift.

### 🟡 The four way script ignores the exit code of each `eval` run, `experiments/0014-review-volume-and-routing-policy/compare_four_ways.py:136`
**Problem**: The `load` return code is checked, but the `eval` subprocess result is only written to a file. The table itself comes from the in process `score_config()`, so a crashed or refused `eval` still produces a clean table while the saved `*-eval.txt` holds an error message.
**Why it matters**: The saved raw output and the table can disagree without any signal. It did not happen in the committed run (all five eval outputs look complete), so this is a guard gap, not a wrong result.
**Suggested fix**: Raise `ComparisonRefused` when the `eval` return code is not 0 or 1 (a failing question may exit 1), or compare the saved question verdicts to the in process ones.

### 🟡 `AGENTS.md` command lines still describe the old defaults, `AGENTS.md:28-31`
**Problem**: It still says `load --with-held` is an opt in, `trace --with-held` "refuses a graph not loaded --with-held", and `eval --with-held` "needs a graph from load --with-held". It also lists no `--narrow-hold` or `--no-narrow-hold`, `--no-with-held` or the four queue file names. Spec 0008's own Follow-up already owes this to `/sync`.
**Why it matters**: The next session reads AGENTS.md first and will assume held items are off by default and that the narrow rule does not exist.
**Suggested fix**: Run `/sync` on this branch before merge, as `docs/reflexes.md` requires.

### 🟡 Data files carry text from code that no longer exists, `experiments/0014-review-volume-and-routing-policy/data/four-way.md` and `README.md` Outcome section
**Problem**: `four-way.md` shows "(via release)" cell annotations, and the README Outcome says released items "print `RELEASED: narrow_hold`". Both were removed by 61707df. The README opens with a dated note saying so, and the spec carries the same note.
**Why it matters**: Low. The note is there, and the states themselves are unaffected. A rerun of the script will not reproduce the exact text.
**Suggested fix**: None needed beyond the existing note, unless the file is regenerated.

## Nits
- ⚪ `src/tracepath/cli.py:640`, `trace --no-narrow-hold` without `--eval` is silently accepted while `--narrow-hold` without `--eval` is refused; harmless, but inconsistent.
- ⚪ `experiments/0014-review-volume-and-routing-policy/compare_four_ways.py:67`, runs `tracepath` from PATH; it is the repo's build only when started through `uv run`, as the docstring says.
- ⚪ `src/tracepath/extract/compare.py:496`, the second `_relationship_reasons()` call for a still held link is computed only `elif narrow_ids`; correct, but a one line comment on why `before_narrow` is used first would help the next reader.

## Strengths
- `route_runs()` keeps the release rule tight: reason sets are checked as a subset of the two allowed reasons, the code pass is evaluated first so its stamp wins, and a link's endpoint test uses the set from before the narrow releases, so a link cannot release on an endpoint it has not yet seen released.
- The count in the load output and `graph-build.json` is cross checked in tests against a count taken from the two queues, and the 526 row queue, the manifest keys and the experiment README all agree.
- Defaults were flipped in the order the spec required (amendment commit, then flip commit), each opt out was added before its flip, and the four way script states both flags in every configuration so it never rests on a project default.
- The four way and ratio logic live in pure modules with their own unit tests, including the "both flags worse than either alone" stop.

## Test coverage
New routing logic is well covered: `tests/test_narrow_hold.py` (about 576 lines) covers AC-1 to AC-6 including cross unit links, the flag union across runs and the code pass precedence; `tests/test_narrow_hold_commands.py` covers the mismatch refusals, the four queue file names and both defaults; `tests/test_four_way.py` and `tests/test_hold_ratio.py` cover the pure comparison and ratio code. Existing tests were updated to state `--no-narrow-hold` and `--no-with-held` rather than loosened. Gaps: no test for a bare `eval` or `trace --eval` over a graph loaded with `--no-with-held` (first finding), and no test that the four way script notices a failed `eval` run.
