# Verify: answer at question time · spec 0009

**Run on**: 2026-10-19, branch `feat/answer-at-question-time` at `b8b092f` (PR #45).
**Verdict**: FAIL on conformance. 42 of the 44 criteria are met. In AC-11 and AC-14, the code does something the spec text does not say. In both cases the code's choice is the more sensible one, so the fix is probably a spec amendment. That choice belongs to the engineer.

**How it was run.** No billed call was made. The evidence comes from four places:

1. `tracepath ask --dry-run` against the live graph (Neo4j 5.26.30, a default `load`, 2,766 nodes). Each dry run uses the free token count endpoint.
2. The nine committed records under `artifacts/asks/`, checked by a script. The script never printed a held out question or answer.
3. The real `ask` command, driven through Typer's `CliRunner` with only the model call (`ask_calls_through`) swapped for a fake. Retrieval, the free count, the guard, the checks, printing and record writing were all real. Records went to a scratch `--root`, never to `artifacts/asks/`. The fake counted its own calls, so every "0 calls" below is measured.
4. A script that recomputes AC-7 to AC-14b on its own from the live graph, then compares the result with `build_pack()`.

`eval/held-out.json` was never opened, and `ask` never ran on it. The held out guard was exercised in two ways: on a scratch file holding `"held_out": true`, and by calling `settled_eval_record()` on the real record names, which reads no eval file.

## Commands

- [x] `ask --eval N --ceiling 0.5 --dry-run`, N = 1 to 5 → exit 0; prints question, graph line, search words, items, counted input and bound; "no call made, no record written"; `artifacts/asks/` still holds 9 files → AC-1 (order of the item part), AC-4, AC-5, AC-5c, AC-13
- [x] Each of the five dry runs prints the same search words, the same items in the same order and the same counted input tokens as the committed record for that question (q1 matched with the typed record of 21:08:46Z) → AC-27 (the record holds what was sent), and shows retrieval is repeatable
- [x] Independent recomputation over the live graph for eval 1 to 5, an id question ("spec 0007 AC-19"), a tokeniser question and a no match question: the words, the 16 hits, each item's hop (checked against a separate breadth first search over the seven types), and the full link set among items all match `build_pack()` → AC-7, AC-8, AC-8b, AC-9, AC-10, AC-12b
- [x] The slice the code reads holds the seven typed link types and no `PART_OF`; the live graph holds 2,649 `PART_OF` links → AC-10
- [x] "spec 0007 AC-19" gives the words `spec, 0007, ac-19, hold`, and `0007/AC-19` is the top hit → AC-8
- [x] `src/lib/landing-rule.ts call readOwnProfile(), and the_thing.x a-b?` gives `src, lib, landing-rule.ts, landing, rule, call, readownprofile, the_thing.x, thing, a-b` → AC-7
- [x] Packs of 90 items report cuts (q2: 19, q4: 38) → AC-11 (limit and count)
- [ ] Item order: hits, then hop 1, then hop 2 → AC-11 (order). **Not met as written**, see Gaps
- [ ] History labels match "struck, or the source of any `superseded-by` or `corrected-by` link" → AC-14. **Not met as written**, see Gaps
- [x] Each history item's replacement is in the pack, in every question run (none missing) → AC-14b
- [x] Item lines show id, type, held or accepted, `STRUCK` or `HISTORY`, `file:line`, hit or hop. A Record shows only its path (`0007  record  accepted  specs/0007-.../index.md  hop 1`). An Unresolved node shows its own file and line (`unresolved:0004:until-feature-7-deletes-it ... specs/0004-test-foundation/index.md:141`, which matches the node's stored `file` and `line`) → AC-13
- [x] `ask "Why x?" --eval 1` and `ask` with neither, run with `NEO4J_URI=bolt://localhost:1` → exit 1, "give one QUESTION or --eval N", no graph error (the graph was not read) → AC-2
- [x] No `--ceiling`, `0`, `-1`, `nan`, `inf` → exit 1, one line each, before any read → AC-3
- [x] `load --no-with-held`, then `ask ... --dry-run` → exit 1 with "ask reads held items too, but the graph holds no held item. Run `tracepath load` without --no-with-held first". Then `load`; `artifacts/graph-build.json` came back byte identical → AC-5b
- [x] Typed failures, each one line on stderr, exit 1, no traceback: Neo4j on a dead port (`GraphUnavailable`); `ANTHROPIC_API_KEY=` (`SettingsInvalid`); `--root` with no manifest; `--eval-file eval/missing.json`; a held out file without the flag (`HeldOutRefused`); `ANTHROPIC_MODEL=claude-unpriced-9` (`EstimateUnavailable`, after the items print and before the count); a bad API key (count endpoint 401); a second run on the same clock (`ArtifactCollisionError`, 0 calls). `SliceError` and `CountUnreadable` were injected into the real command: each exits 1 with its one line → AC-6
- [x] Plain `ask "zzqx qqzv vvxq?" --ceiling 0.5` (no dry run, scratch root) → "No item matches the search words, so no call is made.", exit 0, no record → AC-12
- [x] `--eval 1` of a scratch eval file whose question matches nothing, real run → exit 0, 0 calls, record `...-eval-nomatch-q1.json` with `eval_file`, `eval_question: 1`, `called: false` → AC-12, AC-29
- [x] Fake reply with seven claims, real command → answer printed after the items and before the cost line. Lines seen: `[0002/AC-10] [0002#build-plan:7] HISTORY link`; `CITATION REJECTED: 9999/AC-1 read from text`; `UNCITED read from text`; a `link` claim over two unlinked ids prints `INFERRED`; `[0007#consequences:21 held] INFERRED`; `HISTORY INFERRED CITATION REJECTED: 9999/AC-2` (order as specced); `Missing:` below the claims; verdict above them → AC-1, AC-15b, AC-16, AC-16b, AC-17, AC-17b, AC-18, AC-19, AC-20
- [x] `--ceiling 0.01`, real run → items and bound print, then "stopping here before the call: ceiling", exit 1, 0 calls, no record → AC-22
- [x] Fake failed call (`max_tokens`) → "Answer: none ... counts at its bound", cost line shows $0.1740 by usage and $0.1741 by the guard's rule, record saved with `settled: false`, exit 1, exactly 1 call (no retry) → AC-24, AC-25
- [x] Records directory made read only, settled fake reply → answer and cost line print, then "Record: lost." and exit 1 → AC-27c
- [x] Scratch held out file: q1 asked (settled) → q1 again refused before any call ("already answered by a settled call"); q10 not refused; q2 after a failed call not refused; q3 after a no call record not refused → AC-31, AC-32
- [x] `settled_eval_record()` on the real records finds a settled record for held out questions 1 to 4 and none for 5, so a rerun of any of the four is refused → AC-32
- [x] `--eval 1 --release-held-out` on the default file → refused, "not a held out file". `--release-held-out` with a typed question → refused → AC-31
- [x] `--eval 6` and `--eval 0` → "has 5 entries, numbered from 1"; an entry with an empty question → "has no question"; none of the five eval dry runs prints any part of the entry's `answer` → AC-30
- [x] No `pass`, `fail`, `total` or `rate` in any `ask` output → AC-33
- [x] All nine `raw_response` values validate as `Answer`; `ask_output_format()` is a JSON schema with `verdict`, `claims` (`text`, `cites`, `basis` in `link`/`text`/`inferred`) and `missing` → AC-15
- [x] `system_prompt()` holds "When a claim uses a HISTORY item, say so in the claim itself, and when the item says what replaced it, name that item in the claim and cite it." → AC-18b
- [x] Nine records: every claim's `rejected_ids`, `uncited`, `inferred`, `history` and `held_ids`, recomputed from the record's own items and links, match what was saved. All links in a record join two items of that record. Recorded cost equals usage at $2 and $10 per million tokens. Bound equals counted input at $2 plus 16,000 at $10. Each bound sits under its ceiling. All are `claude-sonnet-5-5`, effort `medium`, prompt `ask-1`, corpus `2e40bcf` → AC-23, AC-25, AC-27
- [x] Record names: `2026-10-19T21-08-46Z-why-does-the-landing-rule.json`, `...-eval-linked-records-research-q2.json`, scratch `...-eval-nomatch-q1.json`, `...-eval-fakeheld-q1.json` → AC-28
- [x] `build_client()` returns a client with `max_retries` 0, and `ask` opens its client with it → AC-26
- [x] `src/tracepath/ask/` names no `anthropic`, `build_client` or `extract_once`; `tests/test_spend_fence.py` is unchanged from `main` and passes → AC-21
- [x] `uv run pytest tests/test_ask_*.py tests/test_spend_fence.py` → 114 passed (with the fence test run last, see Notes)

## Gaps

**AC-11, item order.** The spec says items go hits by score, then hop 1, then hop 2. The code puts each history item's replacement right after it, at any position. You can see it in eval question 3, both in its record and in today's dry run: `0007` (hop 1) is item 2, ahead of 14 hits, because it replaces `0002/AC-10`. Likewise `0007#consequences:21` (hop 2) sits among the hop 1 items. The id question shows the same thing. The rule comes from `build_pack()` in `src/tracepath/ask/retrieve.py`, and `test_ac_14b_the_item_replacing_a_history_item_is_added_right_behind_it` asserts it. So it was chosen on purpose, but no spec line records it. It changes only the print order, plus which item falls past 90 when a pack is cut. The nine records were made with this rule. Fix: either amend AC-11 or AC-14b to say "a replacement follows the item it replaces", or change the code. A code change would alter future packs only; the nine committed records stay as they are.

**AC-14, self loops.** The spec says an item is history when it is "the source of a `superseded-by` or `corrected-by` link anywhere in the graph". The code skips a link whose source and target are the same item. The live graph holds three such `CORRECTED_BY` self loops: `0009/AC-14` (no phrase), `0011/AC-9` ("corrected 2026-09-03", held) and `0020/AC-11` ("**Rewritten 2026-09-13**", held). None of the three is marked history. `0009/AC-14` appears in the packs for eval questions 1, 2, 4 and 5, unmarked. Each loop means "this item was rewritten in place", so its text is the current one, and calling it history would tell the model it no longer stands. Fix: amend AC-14 to exclude a link from an item to itself.

## Notes (not failures)

- `--ceiling abc` exits 2 with Typer's usage error, not 1. `extract --ceiling abc` does the same, and AC-3 says "as for `extract`". No call is possible either way.
- Running `tests/test_spend_fence.py` before the first integration test leaves `NEO4J_PASSWORD=from-the-dotenv-file` in the process environment. That makes the session Neo4j fixture fail (2 setup errors in `test_ask_command.py`). The leak is in a test from `8fbaf90`, already on `main`. Run in the usual order, all pass.
- The ask integration tests write fixtures into the shared Neo4j database and leave it empty afterwards. After the test run, `tracepath load` restored it: same node counts, `graph-build.json` byte identical, and all five eval dry runs identical to the earlier ones.
- In the nine real replies, no citation was ever rejected, no claim was uncited, and no claim was marked inferred. Those printed marks are shown here only with a fake reply through the real command.

## Acceptance criteria coverage

- AC-1 met · AC-2 met · AC-3 met (see Notes) · AC-4 met · AC-5 met · AC-5b met · AC-5c met · AC-6 met
- AC-7 met · AC-8 met · AC-8b met · AC-9 met · AC-10 met · AC-11 **not met as written** (order) · AC-12 met · AC-12b met
- AC-13 met · AC-14 **not met as written** (self loops) · AC-14b met
- AC-15 met · AC-15b met · AC-16 met · AC-16b met · AC-17 met · AC-17b met · AC-18 met · AC-18b met · AC-19 met · AC-20 met
- AC-21 met · AC-22 met · AC-23 met · AC-24 met · AC-25 met · AC-26 met
- AC-27 met · AC-27b met · AC-27c met · AC-28 met · AC-29 met
- AC-30 met · AC-31 met · AC-32 met · AC-33 met

Every specced surface exists: the `ask` command with each flag in the API table, `src/tracepath/ask/` (`retrieve.py`, `answer.py`, `record.py`), `ask_metered()` and `ask_bound()`, and `artifacts/asks/`.
