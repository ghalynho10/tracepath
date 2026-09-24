# Reflexes

Standing rules for how work is done here, one line each.

## Reflexes

- When you create a commit in this repo, omit the `Co-Authored-By` trailer, because the repo is portfolio facing and the engineer owns every decision. (added 2026 09 21)
- When a feature's build lands, keep its branch open and merge only after the tier's closing steps, `/check verify` and `/test` at Beta, plus `/check review` and `/document` at GA, because `/test` scopes itself to the working tree and on a clean main can only fall back to the last commit, which stops being the feature as soon as anything else lands. (added 2026 09 23)
- Stop before anything that spends API credit and give a measured estimate first, then wait for a go ahead, because an unflagged estimate of about $0.40 turned out 10 to 15 times low. Derive the estimate from a measured per call cost and the real number of calls, never from a plausible sounding round number, and say which measurement it comes from. (added 2026 09 23)
