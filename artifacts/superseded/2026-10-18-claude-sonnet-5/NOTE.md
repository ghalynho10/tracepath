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
