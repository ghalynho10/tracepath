# Reflexes

Standing rules for how work is done here, one line each.

## Reflexes

- When you create a commit in this repo, omit the `Co-Authored-By` trailer, because the repo is portfolio facing and the engineer owns every decision. (added 2026 09 21)
- When a feature's build lands, keep its branch open and merge only after the tier's closing steps, `/check verify` and `/test` at Beta, plus `/check review` and `/document` at GA, because `/test` scopes itself to the working tree and on a clean main can only fall back to the last commit, which stops being the feature as soon as anything else lands. (added 2026 09 23)
- Stop before anything that spends API credit and give a measured estimate first, then wait for a go ahead, because an unflagged estimate of about $0.40 turned out 10 to 15 times low. Derive the estimate from a measured per call cost and the real number of calls, never from a plausible sounding round number, and say which measurement it comes from. (added 2026 09 23)
- When a run needs to pause, stop by structure and say so plainly: one group or unit per command, a stated stop point in the script, or a plain "stopping here before X" that lets the current command finish. Never plant a file, break a path, or otherwise cause an error to halt a run, and never describe a stop you chose as a crash or a bug, because a stop disguised as a failure costs a debugging round and makes the logs lie. (added 2026 09 24)
- When designing guards or acceptance criteria, guard only what can lose money, lose data or produce a misleading result, as cheaply as possible, and add no guard against hypothetical misuse unless it costs a few lines, because specs 0004 and 0005 grew to about 70 and 42 criteria for a walking skeleton and a diagnostic view. (added 2026 10 07)
