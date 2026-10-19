# Verify: review volume and routing policy · spec 0008

Run by `/check verify` on 2026-10-18, branch `feat/review-volume-and-routing-policy` at `61707df`, against the live Neo4j container and the committed artifacts (`artifacts/runs/` at `8c778e9`). No API call. `eval/held-out.json` was never opened.

Both defaults are now on (`NARROW_HOLD_DEFAULT = True`, `WITH_HELD_DEFAULT = True` in `src/tracepath/cli.py`), so a plain `tracepath load` applies the narrow hold rule and writes the held view. The old "off" state is reached with `--no-narrow-hold` and `--no-with-held`. AC-5f is withdrawn (the 2026-10-18 amendment), so no `RELEASED: narrow_hold` marker is expected anywhere.

Graph counts below are read with Cypher straight from the live graph, grouped by `accepted_by` and `held`.

## Commands

- [x] `tracepath load` (plain, both defaults on) → exit 0; 494 entities (237 `auto`, 257 `narrow_hold`), 291 link rows into 263 relationships (70 with no `accepted_by`, 193 `narrow_hold`), 0 links held across units; prints "257 entities and 207 links released", by reason `known_trap_flag` 316, `endpoint_not_accepted` 185, 37 held for both, and the five per flag counts. `artifacts/graph-build.json` is byte identical to the committed file → AC-3, AC-3b, AC-5, AC-9, AC-11
- [x] `tracepath load --no-narrow-hold` → 237 entities, all `auto`; no link carries `accepted_by`; 37 links held across units; `graph-build.json` has no `narrow_hold` key and no `narrow_hold_released` key → AC-1, AC-5c
- [x] Queue difference: `review-queue --no-narrow-hold` (990 rows) minus `review-queue` (526 rows) gives 464 released rows, 257 entities plus 207 links. Their reason sets are only `{known_trap_flag}` 279, `{endpoint_not_accepted}` 148, and both 37. None carries `runs_disagree`, `span_not_located` or `unclassified_type`. All 7 rows carrying `span_not_located` or `unclassified_type`, and all 471 carrying `runs_disagree`, are still held → AC-1b, AC-1c, AC-5
- [x] The 50 rows still held with only `known_trap_flag` and `endpoint_not_accepted` reasons are all links, and each of their 51 waits names an entity that is itself still in the queue. Cypher finds 0 `narrow_hold` links with a held endpoint, both with the rule alone and with `--code-pass` → AC-2
- [x] Every one of the 257 `narrow_hold` entities matches an entity of its unit's `run-1.json` output exactly (span, type and flags); 0 misses → AC-1d
- [x] `load --code-pass --no-narrow-hold` stamps 67 entities `code_pass`. `load --code-pass` (rule on) stamps those same 67 `code_pass` and 190 others `narrow_hold`; plain `load` (rule alone) stamps all 67 `narrow_hold` → AC-4
- [x] Accepted id sets across the four loads: nothing accepted by the rule alone, or by the code pass alone, is missing under both; nothing accepted with neither is missing under either; the rule adds only `narrow_hold` entities and restamps no plain one → AC-6
- [x] `load --code-pass` writes `"narrow_hold": true` and `narrow_hold_released` (190 entities, 169 links, by reason 249, 146, 36 for both), which equals the queue difference under the code pass (885 minus 526 = 359 rows) → AC-5, AC-5c
- [x] `eval` and `trace --eval 1` (rule on) against a graph loaded with `--no-narrow-hold`, with `NEO4J_URI` pointed at a dead port → exit 1, "the narrow hold rule is on for this command, but artifacts/graph-build.json says the graph was loaded without it". The reverse, `eval --code-pass --no-narrow-hold` against a graph loaded with the rule, also exits 1 with its own message. Control: `eval --no-narrow-hold` on the matching graph reaches the connection and fails on the dead port, so the refusal comes before connecting → AC-5d
- [x] `--narrow-hold` and `--no-narrow-hold` are accepted by `load`, `eval`, `trace` (`--eval`) and `review-queue`, both in `--help` and in real runs above → AC-5b
- [x] `review-queue` and `review-queue --narrow-hold` both write `artifacts/review-queue.json` (526 rows, byte identical to the committed file); `--no-narrow-hold` writes `review-queue-without-narrow-hold.json` (990); `--code-pass` writes `review-queue-code-pass.json` (526); `--code-pass --no-narrow-hold` writes `review-queue-code-pass-without-narrow-hold.json` (885). None touched the default file. These are the names in the spec's 2026-10-18 corrections note, item 3 → AC-5e
- [x] `uv run python experiments/0014-review-volume-and-routing-policy/measure_hold_ratio.py` → exit 0, output byte identical to the committed `data/hold-ratio.md` (237 accepted, 535 held entity rows, 455 held link rows, 1 : 4.18; `Preamble` and `Resolved` print "no accepted entities"). Hand count from the queue file for `0001 Binding rules` (15, 23), `0002 Feature design` (77, 43) and `0008 Preamble` (0, 11) matches the table → AC-7
- [x] `uv run python experiments/0014-review-volume-and-routing-policy/compare_four_ways.py` → exit 0. Every state cell of the 22 step table and every noise count (0, 26, 20, 26 split 5 and 21) matches the committed `data/four-way.md`; it names the runs commit `8c778e9`; AC-8f reports none worse under both. The only differences from the committed files are the withdrawn "via release" and `RELEASED: narrow_hold` annotations, now absent, and `restore-load.txt`, since a plain load now means both defaults on. The committed files were restored afterwards → AC-8, AC-8b, AC-8c, AC-8d, AC-8e, AC-8f, AC-9, AC-11
- [x] `tracepath eval` (defaults) → exit 0; question 4 PASS, questions 1, 2, 3 and 5 FAIL, as experiment 0014 records; no `RELEASED` or "Released by" line → AC-5f withdrawal
- [x] `tracepath trace --eval 3` and `tracepath trace 0002/AC-10` → exit 0; `0002/AC-10` (released by the rule) prints no marker; held steps print `HELD:` by default (6 in `trace --eval 3`) → AC-11, AC-5f withdrawal
- [x] `git log` order: `5458d8e` (amendment, 2026-10-17 22:05) before `9110147` (the four way run); `73f16c9` (spec 0002 AC-11 amended) before `cb28c68` (rule flip); `aca05de` (spec 0002 AC-11 and spec 0005 AC-1 to AC-5 amended) before `5c9c9f4` (held view flip). Each amendment commit changes its tests too → AC-9b, AC-11b
- [x] `git diff 5458d8e HEAD` on `index.md` → only added lines above the Summary (the Corrected note, the AC-5f withdrawal, the Outcome); no line of AC-1 to AC-14 changed → AC-14
- [x] `experiments/0014-review-volume-and-routing-policy/README.md` states AC-12 does not apply and that feature 9 is unblocked because both adoptions landed, naming AC-9 with AC-9b and AC-11 with AC-11b → AC-12, AC-13
- [x] A plain `tracepath load` at the end → exit 0, `graph-build.json` identical to the start, working tree clean

## Acceptance criteria coverage

- AC-1 ✅ the flag exists; its default is now on by AC-9's flip (`cb28c68`), and `--no-narrow-hold` gives the original off state
- AC-1b ✅ · AC-1c ✅ · AC-1d ✅ · AC-2 ✅
- AC-3 ✅ released entities carry `narrow_hold`. Note: a plain accepted entity carries `auto`, not the `""` the spec text names; that value predates this feature
- AC-3b ✅ a link carries `accepted_by` only when the rule released it (corrections note, item 2)
- AC-4 ✅ · AC-5 ✅ · AC-5b ✅ · AC-5c ✅ · AC-5d ✅
- AC-5e ✅ under the file names of the corrections note, item 3
- AC-5f withdrawn 2026-10-18; confirmed no marker prints in `trace`, `eval` or `trace --eval`, and `accepted_by: narrow_hold` is still stored
- AC-6 ✅ · AC-7 ✅
- AC-8 ✅ · AC-8b ✅ · AC-8c ✅ · AC-8d ✅ · AC-8f ✅
- AC-8e ✅ the script ends with a plain `load` and checks its manifest against the defaults. Since the flip, a plain load means both defaults on, not "neither flag" as the text says; it still leaves no nonstandard state
- AC-9 ✅ (a) three steps newly accepted, (b) none regress · AC-9b ✅
- AC-11 ✅ five steps move to held only; the default is on for `load`, `trace` and `eval` · AC-11b ✅
- AC-12 not applicable, both defaults flipped, as the record says · AC-13 ✅ · AC-14 ✅
