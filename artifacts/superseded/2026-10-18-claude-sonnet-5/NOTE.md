# Superseded 2026-10-18: the claude-sonnet-5 units

**What produced them.** 26 units, each with 3 settled runs (78 run files), plus 2 failed
attempt files of `0021 ## Requirements`. Every file names model `claude-sonnet-5`, effort
`medium`, corpus commit `2e40bcf`. Prompt versions: `0003.1` for 23 units, `0003.0` for
`0013 ## Feature design` and the `feature-9` scope row, `0002.3` for `0001 ## Binding rules`.
They sat under `artifacts/runs/` until this move; the paths below this folder mirror theirs.

**Why superseded.** Feature 9 (whole corpus) re extracts every unit on one model and one
prompt, `claude-sonnet-5-5` with `0003.1` (scope, feature 9, shape decided 2026-10-18).
These 26 units are the first group of that run. The three units already on
`claude-sonnet-5-5` with `0003.1` (`0009`, `0013` and `0015` `## Requirements`) stay in
`artifacts/runs/` unchanged.

Before this move the 29 units held 526 review queue rows under the narrow hold default
(`artifacts/review-queue.json` at `ceafd9f`). Kept as evidence, never deleted
(`experiments/README.md`).

**Added later on 2026-10-18.** `0014/decision-claude-sonnet-5-5-before-fix/` holds `0014 ## Decision`'s
4 files from feature 9's first group, on `claude-sonnet-5-5` with `0003.1` (run 1 settled on
attempt 2, run 2 blocked after two schema failures, run 3 never ran). Run 2 blocked before
`5b45113`, which keeps an `entity_type_ambiguous` flag on a typed entity instead of rejecting
the output. They sit in their own folder because `0014/decision/run-1.json` above is the
`claude-sonnet-5` run.

**Added 2026-10-19.** `0001/directory-layout-claude-sonnet-5-5-before-fix/` holds `0001 ## Directory layout`'s
2 failed attempt files of run 3, on `claude-sonnet-5-5` with `0003.1` (runs 1 and 2 settled and stay in
`artifacts/runs/`). Run 3 blocked after two schema failures before `6e47eee`, which keeps an
`unclassified_note` on a typed entity instead of rejecting the output. The folder name follows the
`0014` one above.
