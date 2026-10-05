# Check verify, extraction stability on heterogeneous units, 2026-10-04

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/extraction-stability-on-heterogeneous-units` at `80c9135`
**Spec**: [0003](../specs/0003-extraction-stability-heterogeneous-units/index.md), checked against its [verify.md](../specs/0003-extraction-stability-heterogeneous-units/verify.md)
**Verdict**: PASS. 38 of 39 acceptance criteria met with recorded evidence; AC-37 not met as measured, and covered by AC-39, which the spec provides for exactly that outcome.

This is a runtime check, not a code review. No API call was made: every criterion was
judged from the committed run artifacts, the real pipeline functions, the CLI and the
test suite.

## What was run

- `uv run pytest`: 383 passed, Neo4j integration tests included. `ruff check`, `ruff format --check` and `mypy` (strict) clean.
- `uv run tracepath status`: Neo4j 5.26.30 reachable. `uv run tracepath review-queue`: 416 held items from 14 units, byte identical to the committed `artifacts/review-queue.json`.
- A scratch script through the pipeline's own functions (`read_binding_rules`, `locate_output`, `label_binding_rules`, `assign_ids`, `build_label_index`, `committed_units`):
  - AC-1, AC-12: in each of the three committed `0002.3` runs of `0001 ## Binding rules`, rule 6's leading span holds one entity, labelled `binding rule 6`, and the label index resolves it (`0001#binding-rules:10`, `:12`, `:6`). 23 of 24 rule spans hold exactly one entity.
  - AC-2: with a second entity added inside rule 6's span, rule 6 gets no label; the other rules keep theirs. AC-3: rule 4 in run 3 holds no entity and gets no label.
  - AC-4: on the `0002.2` `0006 ## Feature design` run that invented `key invariant 1` to `6`, all six are cleared; only `Logo`, verbatim in its own span, survives.
  - AC-5: across every committed unit, the pre check changes labels only in `0001 ## Binding rules`.
  - AC-6 to AC-10, AC-21 to AC-29: in the assembled `SYSTEM_PROMPT`, each new rule appears once; the seven examples are in filename order, each Input and Output once; no Reasoning notes or per example Rules sections reach the prompt; the `0006` excerpt note is present; `schema.py:149` reads `Happy path`, `schema.py:120` keeps `binding rule 6`; `PROMPT_VERSION` is `0003.1` with a `1h` cache.
  - AC-31: `0015 ## Feature design` entities 35 / 35 / 36, spread 1. AC-33: no artifact carries a prompt version after `0003.1`.
  - AC-36 to AC-38, rebuilt from the committed runs: `Consequence` 16 / 16 / 16, `FollowUp` 11 / 11 / 11, `BuildStep` 9 / 9 / 9 pass all three; `TestScenario` 16 / 16 / 16 passes AC-36 and AC-38 and fails AC-37 (`Consequence` in run 1 only).
- Experiment 0005 at `201fae4`, in a throwaway worktree: `report.py` rebuilt `heldout-table.json` byte for byte (AC-14 to AC-17, the label invention check: all 27 labels verbatim in their own spans), and `report.py tally` rebuilt `ruling-tally.json` unchanged (AC-16).
- AC-19: in every `0003.x` session, the first call wrote the cache and every later call read it. AC-13: one `0002.3` baseline for `0021`, its `0002.2` runs moved aside. AC-30: experiment 0006's entity and relationship items are all ruled; the 44 unmarked lines are the dropped link samples, unruled by decision (AC-30, amended). AC-35: feature 12's Done when names no accuracy bar.

## Notes

1. **AC-20 for experiment 0006 is provable only from its README.** Its `data/cost-estimate.json` was committed in the same commit as its runs (`5142169`), so git cannot show the estimate came first; the README states it was planned before any call. For experiments 0005 and 0008, the estimate commit is an ancestor of the run commit (`906e669` before `4cae467`, `8c7e71f` before `ba1f81a`).
2. **AC-27's `verify.md` wording is stricter than the rule it checks.** `verify.md` says "each new rule appears once, no example file repeats one". The assembled prompt holds the AC-27 rule once, but `examples/feature-21-scope-row.md` restates it in its own "Rules this example demonstrates" section, which never reaches the prompt. Judged on the assembled prompt, as the line's own "Inspection of the assembled `0003.1` prompt" says. For the next `/architect` amendment: reword the line to say the prompt, not every example file.
3. **Two milestones and `Build it` were unticked in the scope** although their work was done (the ruling and AC-17 decision; the type coverage rerun with the graph and queue rebuild). Ticked by `/develop` on 2026-10-04, citing their commits, in the same commit as this file.

## Scope

`Verify it` ticked for feature 12 (`f61c15a`). The feature stays `in-progress`; at the Beta tier, `/test` closes it.
