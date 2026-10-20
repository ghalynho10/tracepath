# Verify: answer at question time · spec 0009

**Run on**: 2026-10-19, branch `feat/answer-at-question-time` at `6893685` (PR #45). This rerun covers the dated notes added in `6893685`. The first run, at `b8b092f`, found AC-11 and AC-14 differing from the code (`fe3ea5d`).
**Verdict**: PASS. All 44 criteria are met, each read together with its dated notes, and every specced surface is built.

**How it was run.** No billed call was made. The evidence comes from four places:

1. `tracepath ask --dry-run` against the live graph (Neo4j 5.26.30, 2,766 nodes). Each dry run uses the free token count endpoint.
2. The nine committed records under `artifacts/asks/`, checked by a script. The script never printed a held out question or answer.
3. The real `ask` command with only the model call (`ask_calls_through`) swapped for a fake. Retrieval, the free count, the guard, the checks, printing and record writing were all real. The fake counted its own calls, so every "0 calls" below is measured. Records went to scratch `--root` folders, never to `artifacts/asks/`. Most runs went through Typer's `CliRunner`. The Ctrl-C (SIGINT) run used a separate Python process started on the real `tracepath ask` entry point.
4. A script that recomputes AC-7 to AC-14b on its own from the live graph, then compares the result with `build_pack()`.

`eval/held-out.json` was never opened, and `ask` never ran on it. The held out guard was exercised in two ways: on a scratch file holding `"held_out": true`, and by calling `settled_eval_record()` on the real record names, which reads no eval file.

The graph was loaded at the start. After the tests (which empty the shared database), it was loaded with `--code-pass`, then with a plain `load` at the end. The final manifest is byte identical to the one before this run, and node counts match.

## Commands

- [x] `ask --eval N --ceiling 0.5 --dry-run`, N = 1 to 5 → exit 0; prints the question, the graph line, search words, items, counted input and bound; "no call made, no record written"; `artifacts/asks/` still holds 9 files. The output is identical to the first run except the graph line → AC-1 (the item part), AC-4, AC-5, AC-5c, AC-13
- [x] The graph line reads `Graph: held view yes, narrow hold yes, code pass no, corpus 2e40bcf.` after a plain `load`, and `... code pass yes ...` after `load --code-pass` (which writes `"code_pass": true` to the manifest). No `code_pass` key appears in an ask record → AC-5c and its note
- [x] Each of the five dry runs prints the same search words, the same items in the same order and the same counted input tokens as the committed record for that question → AC-27, and shows retrieval is repeatable
- [x] Independent recomputation over the live graph for eval 1 to 5, an id question, a tokeniser question, a no match question and the cut note question below. The words, the 16 hits, each item's hop (checked against a separate breadth first search over the seven types), the full link set among items, and the history labels (with self loops excluded) all match `build_pack()` → AC-7, AC-8, AC-8b, AC-9, AC-10, AC-12b, AC-14 and its note
- [x] The slice the code reads holds the seven typed link types and no `PART_OF`; the live graph holds 2,649 `PART_OF` links → AC-10
- [x] "spec 0007 AC-19" gives the words `spec, 0007, ac-19, hold`, and `0007/AC-19` is the top hit → AC-8
- [x] `src/lib/landing-rule.ts call readOwnProfile(), and the_thing.x a-b?` gives `src, lib, landing-rule.ts, landing, rule, call, readownprofile, the_thing.x, thing, a-b` → AC-7
- [x] Item order: hits, then hop 1, then hop 2, except that a history item's replacement follows right after it. Eval question 3: `0007` (hop 1) is item 2, right after `0002/AC-10`, which it replaces → AC-11 and its order note
- [x] Packs of 90 items report cuts (q2: 19, q4: 38) → AC-11 (limit and count)
- [x] Cut note: the question "Why " + the text of `0021#requirements:4` prints `Items sent: 90 (16 hits, 74 neighbours, 64 cut).` The independent count is also 64. The old rule would give 63. The extra one is `0020#follow-up:3`, a replacement no hop reached, cut together with its history item and absent from the items sent. In eval 1 to 5 the new and old counts agree, so no recorded cut changes there → AC-11 cut note
- [x] The three `CORRECTED_BY` self loops (`0009/AC-14`, `0011/AC-9`, `0020/AC-11`) do not make their items history. `0009/AC-14` prints without `HISTORY` in the packs for eval 1, 2, 4 and 5 → AC-14 note
- [x] Each history item's replacement is in the pack, in every question run (none missing) → AC-14b
- [x] Item lines show id, type, held or accepted, `STRUCK` or `HISTORY`, `file:line`, hit or hop. A Record shows only its path. An Unresolved node shows its own stored `file` and `line` (`unresolved:0004:until-feature-7-deletes-it ... specs/0004-test-foundation/index.md:141`) → AC-13
- [x] `ask "Why x?" --eval 1` and `ask` with neither, run with `NEO4J_URI=bolt://localhost:1` → exit 1, "give one QUESTION or --eval N", no graph error → AC-2
- [x] No `--ceiling`, `0`, `-1`, `nan`, `inf` → exit 1, one line each, before any read → AC-3
- [x] (first run) `load --no-with-held`, then `ask ... --dry-run` → exit 1 with "the graph holds no held item. Run `tracepath load` without --no-with-held first". This code is unchanged since → AC-5b
- [x] Typed failures, each one line on stderr, exit 1, no traceback: Neo4j on a dead port; `ANTHROPIC_API_KEY=`; `--root` with no manifest; `--eval-file eval/missing.json`; a held out file without the flag; `ANTHROPIC_MODEL=claude-unpriced-9`; a bad API key (count endpoint 401). `ArtifactCollisionError`: a second run on the same clock exits 1 with 0 calls. `SliceError` and `CountUnreadable` were injected into the real command in the first run, each giving exit 1 and one line; this code is unchanged since → AC-6
- [x] Plain `ask "zzqx qqzv vvxq?" --ceiling 0.5` → "No item matches the search words, so no call is made.", exit 0, no record (first run, code unchanged) → AC-12
- [x] `--eval 1` of a scratch eval file whose question matches nothing, real run → exit 0, 0 calls, record `...-eval-nomatch-q1.json` with `eval_file`, `eval_question: 1`, `called: false` → AC-12, AC-29
- [x] Fake reply with ten claims, real command. The answer prints after the items and before the cost line:
  - `Answer (verdict: partly; 6 of 10 claims failed a check):`. The six are: two with a rejected id, one uncited, one `link` with no link, one `link` with an unjoined id, and one `link` with an unsent id. The claim the model itself marked `inferred` is not counted. The record stores the verdict `partly` as it came → AC-20 note
  - `[0002/AC-10] [0002#build-plan:7] HISTORY link` → AC-17b, AC-18
  - `[9999/AC-1] CITATION REJECTED: 9999/AC-1 unsupported` (every citation rejected) → AC-16, AC-17b note
  - `UNCITED read from text` → AC-16b
  - a `link` claim over two unlinked ids prints `INFERRED` → AC-17
  - `[0008/AC-2] [0007/AC-16] [0007] INFERRED` (a linked pair plus one unjoined id) → AC-17 note
  - `[0008/AC-2] [0007/AC-16] [9999/AC-3] INFERRED CITATION REJECTED: 9999/AC-3` (a linked pair plus one id never sent) → AC-17 note
  - `[0008/AC-2] [0007/AC-16] link` (the linked pair alone) → AC-17b
  - `[0007#consequences:21 held] INFERRED` → AC-19, AC-17b
  - `HISTORY INFERRED CITATION REJECTED: 9999/AC-2` (marks in the specced order; one citation kept, so no `unsupported`) → AC-20
  - `Missing:` below the claims, verdict above them → AC-1, AC-15b, AC-20
- [x] `--ceiling 0.01`, real run → "stopping here before the call: ceiling", exit 1, 0 calls, no record → AC-22
- [x] Fake failed call (`max_tokens`) → "Answer: none ... counts at its bound"; cost line shows $0.1740 by usage and $0.1741 by the guard's rule; record saved with `settled: false`; exit 1; exactly 1 call → AC-24, AC-25
- [x] Ctrl-C during the call. A separate process ran the real entry point, and SIGINT arrived while the fake call was sleeping. Exit code 130. The record `...-eval-fakeheld-q4.json` was saved with `settled: false`, `error: "the call raised KeyboardInterrupt ()"`, usage `null` (unmeasured), and `cost_usd` equal to `bound_usd` ($0.16913). A dry run of that held out question afterwards is not refused → AC-24 note, AC-32
- [x] A fake call that raises `RuntimeError` → record saved with `settled: false` and `error: "the call raised RuntimeError (the fake transport broke)"`, cost at its bound, exit 1. The traceback ends with `The call counts at its bound and is saved as failed:` and the record's path → AC-24 note
- [x] Records directory made read only, settled fake reply → answer and cost line print, then "Record: lost." and exit 1 → AC-27c
- [x] Scratch held out file: q1 asked (settled) → q1 again refused before any call; q10 not refused; q2 after a failed call not refused; q3 after a no call record not refused → AC-31, AC-32
- [x] `settled_eval_record()` on the real records finds a settled record for held out questions 1 to 4 and none for 5 → AC-32
- [x] `--eval 1 --release-held-out` on the default file → refused; `--release-held-out` with a typed question → refused → AC-31
- [x] `--eval 6` → "has 5 entries, numbered from 1"; an entry with an empty question → "has no question"; no dry run prints any part of the entry's `answer` (first run) → AC-30
- [x] No `pass`, `fail`, `total` or `rate` in any `ask` output (apart from `code pass` on the graph line) → AC-33
- [x] All nine `raw_response` values validate as `Answer`; `ask_output_format()` is a JSON schema with `verdict`, `claims` and `missing` (first run, code unchanged) → AC-15
- [x] `system_prompt()` tells the model to say so in the claim when it uses a HISTORY item, and to name and cite what replaced it (first run, prompt unchanged at `ask-1`) → AC-18b
- [x] Nine records: every claim's saved checks match a recomputation from the record's own items and links. Under the new `link` rule, none of the six recorded `link` claims would change, and no claim in any record fails a check. Costs and bounds recompute exactly. All are `claude-sonnet-5-5`, effort `medium`, prompt `ask-1`, corpus `2e40bcf` → AC-23, AC-25, AC-27, AC-17 note
- [x] Record names: `2026-10-19T21-08-46Z-why-does-the-landing-rule.json`, `...-eval-linked-records-research-q2.json`, scratch `...-eval-nomatch-q1.json`, `...-eval-fakeheld-q4.json` → AC-28
- [x] `build_client()` returns a client with `max_retries` 0 → AC-26
- [x] `src/tracepath/ask/` names no `anthropic`, `build_client` or `extract_once`; `tests/test_spend_fence.py` is unchanged from `main` and passes → AC-21
- [x] `uv run pytest tests/test_ask_*.py tests/test_spend_fence.py` → 125 passed (fence test last, see Notes)

## Notes (not failures)

- **Ctrl-C prints nothing.** The record is saved, but the line naming it is attached to the exception as a note, and that note shows only in a traceback. So nothing tells the person where the failed record went. The spec does not ask for that message. A plain error other than Ctrl-C shows a full traceback that ends with the note. That is how the command ended before this change too.
- `--ceiling abc` exits 2 with Typer's usage error, not 1. `extract --ceiling abc` does the same, and AC-3 says "as for `extract`". No call is possible either way.
- Running `tests/test_spend_fence.py` before the first integration test leaves a fake `NEO4J_PASSWORD` in the environment, which makes two `test_ask_command.py` setups fail. The leak is in a test from `8fbaf90`, already on `main`. Run in the usual order, all pass.
- The ask integration tests empty the shared Neo4j database. Reload with `tracepath load` after running them.
- In the nine real replies, no citation was rejected, no claim was uncited and no claim failed a check. Those marks, `unsupported` and the failed check count are shown here only with a fake reply through the real command.

## Acceptance criteria coverage

- AC-1 met · AC-2 met · AC-3 met (see Notes) · AC-4 met · AC-5 met · AC-5b met · AC-5c met, with its note · AC-6 met
- AC-7 met · AC-8 met · AC-8b met · AC-9 met · AC-10 met · AC-11 met, with its two notes · AC-12 met · AC-12b met
- AC-13 met · AC-14 met, with its note · AC-14b met
- AC-15 met · AC-15b met · AC-16 met · AC-16b met · AC-17 met, with its note · AC-17b met, with its note · AC-18 met · AC-18b met · AC-19 met · AC-20 met, with its note
- AC-21 met · AC-22 met · AC-23 met · AC-24 met, with its note · AC-25 met · AC-26 met
- AC-27 met · AC-27b met · AC-27c met · AC-28 met · AC-29 met
- AC-30 met · AC-31 met · AC-32 met · AC-33 met

Every specced surface exists: the `ask` command with each flag in the API table, `src/tracepath/ask/` (`retrieve.py`, `answer.py`, `record.py`), `ask_metered()` and `ask_bound()`, and `artifacts/asks/`.
