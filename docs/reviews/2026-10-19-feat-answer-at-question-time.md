# Review, feat/answer-at-question-time, 2026-10-19

**Reviewed by**: Sonnet 5.5 (author on Opus 5.5)
**Scope**: 21 files read (the 4 held out ask records listed by name and size only, never opened), branch vs main
**Verdict**: Approve with nits

## Summary
The branch adds `tracepath ask`: code retrieves items, one guarded model call answers, code checks every citation, and each paid call writes an append only record. I found no way to make a paid call that skips the ceiling, the count, or the record, and no overwrite of an existing record. The held out guard is sound for its stated rule. mypy, ruff and 112 non integration ask and spend fence tests pass. What is left are a few minor gaps where a printed mark or verdict can read stronger than the check behind it.

I ran no paid call. I did not open `eval/held-out.json` or the four held out ask records.

## Spec differences (AC-11 and AC-14)
Both are verified by reading `src/tracepath/ask/retrieve.py`. Neither is harmful under the four criteria.

- **AC-11 (item order).** `build_pack()` at `retrieve.py:257-271` puts a history item's replacement right behind it. This changes print order, and which item falls past 90 when a pack is cut. It cannot spend money, lose data or hide a failure. It is a safety gain: the group is taken whole or not at all (`retrieve.py:269`), so a HISTORY item is never sent without the item that replaces it. Fix the spec text, not the code.
- **AC-14 (self loops).** `replacements()` at `retrieve.py:193` and `_linked()` at `answer.py:140` skip a link from an item to itself. So `0009/AC-14`, `0011/AC-9` and `0020/AC-11` are not marked HISTORY. The cost of the other choice is clear: marking them would tell the model a current item no longer stands. The one open point is that the meaning "rewritten in place" is inferred from the link phrases, and `0009/AC-14` has no phrase. Inferred, low risk. Amend AC-14.

## Minor
### 🟡 A paid call can end with no record on an error type that is not caught, `src/tracepath/extract/metered.py:620-660`
**Problem**: `call()` returns a failed attempt only for `httpx2.TransportError` and `anthropic.APIError` (mid stream and on open). Any other exception raised after the request is paid for (for example a parse `ValueError` from the SDK stream, or Ctrl-C) leaves `ask_metered()` before `write_record()` at line 707. Nothing wraps `attempt = call(pack)` at line 676.
**Why it matters**: Harm (b) and (d). The user is billed, no record exists, and the CLI may show a raw traceback instead of the one line message AGENTS.md requires. For a held out question this also means no settled record, so the once only guard would not stop a second ask. Inferred: I did not find a path in the SDK that raises such an error, so this is a gap in the net, not a seen failure.
**Suggested fix**: In `ask_metered()`, catch `Exception` around `call(pack)`, turn it into a failed `AskAttempt` with error text and no usage (counted at the bound), and still write the record. Cheap, a few lines.

### 🟡 A `link` claim passes when only two of its cited ids are linked, `src/tracepath/ask/answer.py:150-152`
**Problem**: `_linked()` is true when any one link joins any two cited ids. A claim with basis `link` citing A, B and C, where only A and B are linked, gets no INFERRED mark and prints `link`.
**Why it matters**: Harm (c). The mark `link` reads as "every cited item is joined", and the third citation rests on nothing the code checked. Verified by reading the code. The prompt tells the model to cite both ends, but code does not enforce it.
**Suggested fix**: Either require the cited ids to be connected by the sent links (one component), or mark the claim INFERRED when some cited id has no link to another cited id. If the one pair rule is the intended meaning, say so in spec 0009 and in the printed mark.

### 🟡 The verdict is printed as the model gave it, whatever the checks found, `src/tracepath/ask/answer.py:186`
**Problem**: `answer_lines()` prints `Answer (verdict: answered):` even when every claim is CITATION REJECTED, UNCITED or INFERRED, or when there are no claims.
**Why it matters**: Harm (c). A reader skimming the first line sees "answered" above claims that code has just failed. Verified by reading the code. The verify run shows the marks do print, so the failure is visible, only below the verdict.
**Suggested fix**: Print one extra line or mark on the verdict when no claim passed all checks, set by code. Do not change the model's stored verdict.

### 🟡 The `Graph:` line comes from the manifest file, not the graph that was read, and omits the code pass, `src/tracepath/cli.py:1026-1030`, `src/tracepath/artifacts.py:456-474`
**Problem**: `ask` reads `artifacts/graph-build.json` for held view, narrow hold and corpus, but reads items from live Neo4j. It also never reads `code_pass`, which `eval` and `trace` refuse to mix.
**Why it matters**: Harm (c). If Neo4j was last loaded by another checkout, or with `--code-pass`, the printed and recorded `corpus_commit` and settings describe a different graph from the one answered from. Inferred: I did not find a stored marker in Neo4j to compare against.
**Suggested fix**: Add `code_pass` to the summary and the Graph line, so the record at least says which routing was loaded. A cross check against the live graph is only worth adding if this was ever seen in real output.

## Nits
- ⚪ `src/tracepath/ask/answer.py:179-180`, a claim whose every citation is rejected still prints `read from text`. The CITATION REJECTED mark is there, so it is visible, but the extra mark reads as a pass.
- ⚪ `src/tracepath/ask/record.py:58-85`, the held out once only rule is keyed on the eval file stem under `--root`. A copy of the file under another name, or a different `--root`, is not stopped. Fine as a guard against accidents; do not call it tamper proof.
- ⚪ `src/tracepath/ask/retrieve.py:289`, `cut` counts only items in the ranked order, so a replacement pulled in by a history group but then cut is not in the number. Print only.

## Strengths
- The paid path is narrow and well fenced: bound against ceiling before the call (`metered.py:673`), record collision checked before paying (`:675`), no retry, `max_tokens` fixed, and the `ask` package imports no `anthropic` (spend fence test passes).
- A failed call is charged at its bound and a settled one at recorded usage, and the cost line prints both, so a bad number cannot hide. A lost record is reported with exit 1 after the answer prints.
- Every mark on a claim is set by code from the pack sent, never from what the model says about itself; the ids, history and held checks are pure and tested.
- The held out guard checks the exact name pattern (`-q1` never matches `-q10`), treats an unreadable matching record as an error, and runs before any graph read or call.

## Test coverage
112 non integration tests across `test_ask_answer.py`, `test_ask_retrieve.py`, `test_ask_metered.py`, `test_ask_command.py` and `test_spend_fence.py` pass. They cover the ceiling stop, failed call at bound, lost record, collision, the held out guard, and the per claim checks. Two gaps tie to the findings above: no test for an unexpected exception from `call()` (finding 1), and no test where a `link` claim cites three ids with one linked pair (finding 2).
