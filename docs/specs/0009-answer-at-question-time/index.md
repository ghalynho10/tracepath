# 0009. Answer at question time

**Date**: 2026-10-19
**Status**: Accepted

## Summary

This spec adds one command, `tracepath ask "QUESTION"`. Code picks the question's search words, finds the matching graph items and their neighbours, and sends them in one call to Claude Sonnet 5.5 with a rule: answer only from these items, and cite one for every claim. Code then checks every cited id, marks any link the model inferred instead of read, and labels struck or superseded items as history. The command prints the items first, then the answer, then the cost, so a wrong answer shows whether retrieval or reading failed. Every answer is saved to a file, and the command spends only through a new guard that sits beside `run_metered()` in the same file.

## Requirements

**User stories**:
- As the project's author, I want to type a why question in plain English and get an answer whose every claim names the graph item it rests on, so I can check each claim against the source line.
- As the person judging the answer, I want the retrieved items printed before the answer, so when an answer is wrong I can see at once whether the right item was never found or was found and misread.
- As the person who pays for each call, I want a measured bound and a ceiling checked before the call, so a question can never spend more than I allowed.
- As the person who runs the four held out questions once, I want each answer saved and a second run of a settled held out question refused, so the success bar cannot be shaped by trying again.

**Acceptance criteria** (each holds one claim):

*The command*
- **AC-1**: `tracepath ask "QUESTION" --ceiling USD` prints, in this order, the retrieved items (AC-13), the answer (AC-15 to AC-20) and one cost line (AC-25).
- **AC-2**: `ask` takes exactly one of a `QUESTION` argument or `--eval N`; giving both or neither exits 1 before the graph is read.
- **AC-3**: `--ceiling USD` is required and must be a finite number above 0, as for `extract`; otherwise `ask` exits 1 before any call.
  - **Note, 2026-10-19** (after v1): `--ceiling` is no longer required with `--dry-run`, which makes no paid call; the bound line then ends `no ceiling given` and the line saying a real run would stop is left out. A ceiling given to a dry run is still checked, and a real `ask` without one still exits 1 before any read. The criterion text above is unchanged.
- **AC-4**: `ask --dry-run` makes no billed call and writes no record, and prints the search words, the items, the counted input tokens and the call's bound.
- **AC-5**: `ask` reads the graph with held items included, and searches accepted and held items both.
- **AC-5b**: `ask` exits 1 before any call when the graph read holds no held entity or Unresolved node (the test `trace` uses, spec 0005 AC-26), with a message of its own that tells the author to run `tracepath load` without `--no-with-held`.
- **AC-5c**: `ask` prints one line naming how the graph was loaded: the held view, the narrow hold setting and the corpus commit, read from `artifacts/graph-build.json`.
  - **Note, 2026-10-19** (review finding 4): the line also says whether the code pass was on, read from the `code_pass` key of `artifacts/graph-build.json`, for example `Graph: held view yes, narrow hold yes, code pass no, corpus 2e40bcf.` The ask record does not store it. The criterion text above is unchanged.
- **AC-6**: A typed failure (`SettingsInvalid`, `GraphUnavailable`, `SliceError`, an unreadable `graph-build.json`, an unreadable eval file, `HeldOutRefused`, `EstimateUnavailable`, `CountUnreadable`, an API error from the token count, `ArtifactCollisionError`) prints one message on stderr and exits 1, with no traceback.

*Search words and ranking (code only, no model call)*
- **AC-7**: The search words are the question's lowercase tokens, split on whitespace and `/`, with punctuation stripped from each token's ends, less the stoplist below and any token under 3 characters that holds no digit. A token holding a hyphen, underscore or dot is kept whole and its parts of 3 or more characters are also words. The stoplist is: a, an, and, are, as, at, be, been, by, can, could, did, do, does, for, from, had, has, have, how, in, is, it, its, of, on, or, rather, than, that, the, their, there, these, this, those, to, was, were, what, when, where, which, who, why, with, would.
- **AC-8**: A node's searchable text is its text (an entity's `text`, a Record's `title`, an Unresolved node's `mention`) joined with its `canonical_id`. The same tokeniser as AC-7 is run over it, and a word is found when it is in that token set, with no stemming.
- **AC-8b**: Each node is scored as the sum, over the distinct search words found in it, of ln(N / df), where N is the node count read and df is the number of nodes where the word is found. A word found in no node adds nothing. Nodes are ordered by score, highest first, ties by canonical id.
- **AC-9**: The hits are the 16 highest scoring nodes with a score above 0.
- **AC-10**: From the hits, neighbours are added along the seven typed relationship types, in either direction, held links included, up to 2 hops. `PART_OF` is never followed.
  - **Note, 2026-10-20** (experiment 0016): `ask --hops N` sets how many hops are followed, 0, 1 or 2; any other value exits 1 before the graph is read. The default stays 2, so a plain `ask` sends the same items as before and the model message is unchanged (it carries no hop). The value is printed at the end of the `Items sent:` line, for example `Items sent: 12 (12 hits, 0 neighbours, 0 cut; hops 0).`, and stored as `hops` in each ask record; records written before this note have no `hops` field and ran at 2. A history item's replacement (AC-14b) is still added at `--hops 0`, since it is not a hop. The criterion text above is unchanged.
- **AC-11**: Items are ordered hits by score, then hop 1, then hop 2, each hop in the order of the highest ranked hit that reached it, then by canonical id. At most 90 items are sent, and the output says how many were cut.
  - **Note, 2026-10-19**: a history item's replacement is placed right after it, ahead of the hop order, as `test_ac_14b_the_item_replacing_a_history_item_is_added_right_behind_it` asserts. The code already did this during all nine recorded runs under `artifacts/asks/` (`src/tracepath/ask/retrieve.py` last changed in `baede05`, before the first record), so no result changes. The criterion text above is unchanged.
  - **Note, 2026-10-19** (review nit 3): the cut count now includes a replacement cut together with its history item, even one that no hop reached. A record written before this note can count fewer cut items in that case; the items it sent are unchanged.
- **AC-12**: When no node scores above 0, `ask` prints that no item matches, makes no call, and exits 0. A plain `ask` writes no record then; an `--eval` ask writes one (AC-29).
- **AC-12b**: Every typed link whose two ends are both among the items sent is sent with them, with its type, its phrase and a held mark.

*What is printed about items*
- **AC-13**: Each item line shows its id, its type (the entity type, or `record` or `unresolved`), `accepted` or `held`, `STRUCK` or `HISTORY` when it is one (AC-14), its `file:line`, and `hit` or `hop N`. A Record shows its `path` with no line; an Unresolved node shows its own `file` and `line`.
- **AC-14**: An item is history when it is struck, or is the source of a `superseded-by` or `corrected-by` link anywhere in the graph, held or accepted (both run old to new, per the extraction prompt). An `amended-by` source is not history.
  - **Note, 2026-10-19**: a `corrected-by` link from an item to itself means the item was rewritten in place, and does not make the item history. The live graph holds three: `0009/AC-14`, `0011/AC-9` and `0020/AC-11`. The code already did this during all nine recorded runs (`replacements()` in `src/tracepath/ask/retrieve.py`, last changed in `baede05`, before the first record), so no result changes. The criterion text above is unchanged.
- **AC-14b**: History items are sent to the model under a `HISTORY` label. When a link names the item that replaces one, that replacing item is added to the pack, counted against the limit of AC-11, so the model can cite it.

*The answer and its checks*
- **AC-15**: The model is asked for structured output: a `verdict` (`answered`, `partly` or `not_supported`), a list of claims each with `text`, `cites` (ids) and `basis` (`link`, `text` or `inferred`), and a `missing` list.
  - **Note, 2026-10-19** (after v1, the Follow-up item seen on eval question 4): a fourth verdict, `no_documented_link`, means the items for each thing the question connects were found and no item's text and no sent link states a connection between them. `not_supported` stays for items that are missing. The system prompt says when to use each, and its version moves from `ask-1` to `ask-2`. The nine records under `artifacts/asks/` stay as they ran under `ask-1`, the held out four among them; under `ask-2` only eval question 4 of `eval/linked-records-research.json` is asked again, and the held out file is not. Code checks on claims are unchanged, so this verdict is the model's word, like the other three. The criterion text above is unchanged.
- **AC-15b**: The printed answer is the claims, numbered, plus the verdict and the `missing` line. No other model text is printed as part of the answer.
- **AC-16**: A cited id that was not among the items sent prints the claim marked `CITATION REJECTED: ID`.
- **AC-16b**: A claim with no cited id prints marked `UNCITED`.
- **AC-17**: A claim whose basis is `link` is checked by code: a typed link, in either direction, must join two of its cited ids among the links sent. With none, the claim prints marked `INFERRED`.
  - **Note, 2026-10-19** (review finding 2): a `link` claim passes only when every cited id is joined by a sent link to another cited id. One cited id left unjoined, or one that was not sent, marks the claim `INFERRED`. Before this note, one linked pair among the cited ids was enough. The criterion text above is unchanged.
- **AC-17b**: A claim whose basis is `inferred` prints marked `INFERRED`. A verified `link` claim prints `link`, and a `text` claim prints `read from text`.
  - **Note, 2026-10-19** (review nit 1): a claim whose every citation is rejected prints `unsupported` in place of `link` or `read from text`. The criterion text above is unchanged.
- **AC-18**: A claim that cites a history item prints marked `HISTORY`, set by code from AC-14 and not from anything the model says.
- **AC-18b**: The system prompt tells the model to say in the claim itself when it uses a history item, and what replaced it if a link names it.
- **AC-19**: Each cited id prints with `held` beside it when that item is held.
- **AC-20**: The verdict prints above the claims, and a non empty `missing` list prints below them as `Missing:`. When several marks apply to one claim they print in this order: `HISTORY`, `INFERRED`, `CITATION REJECTED`, `UNCITED`.
  - **Note, 2026-10-19** (review finding 3): when any claim failed a code check, the verdict line says how many, for example `Answer (verdict: answered; 1 of 2 claims failed a check):`. A claim fails a check when it cites an id that was not sent (AC-16), cites nothing (AC-16b), or is a `link` claim whose link was not found (AC-17). A claim the model itself marks `inferred` does not count as failed. The model's verdict is printed and stored as it came. The criterion text above is unchanged.

*Spending*
- **AC-21**: The model call `ask` makes goes through `ask_metered()` in `src/tracepath/extract/metered.py`, which holds the client call and the token count too. `ALLOWED` in `tests/test_spend_fence.py` gains no entry, and the test passes as it stands.
- **AC-22**: Before the call, its bound must not pass the ceiling; otherwise `ask` stops with `stopping here before the call: ceiling` and exits 1.
- **AC-23**: The call's bound is its counted input tokens at the model's input rate plus `ASK_MAX_TOKENS` at its output rate, priced by a new `ask_bound()` that uses `rates_for()` and `tokens_cost()` and not `per_call_bound()` (which prices extraction's cap and a cache write). The count comes from the free token count endpoint. A model with no recorded rates exits 1 before the call (`EstimateUnavailable`).
- **AC-24**: A call fails when it raises a transport or API error, stops on `max_tokens` or a refusal, or returns a reply that does not validate as `Answer`. A failed call counts at its bound, is saved (AC-27), makes no retry, and ends the command with exit 1.
  - **Note, 2026-10-19** (review finding 1): any exception the call raises, `KeyboardInterrupt` included, is saved as a failed call at its bound before it propagates, so a paid request is never left without a record. The record's `error` names the exception and its usage is unmeasured. The exception then ends the command as before (Ctrl-C exits 130). Like any failed call, this record does not use up a held out question (AC-32). The criterion text above is unchanged.
  - **Note, 2026-10-19** (after v1): when the call is interrupted, `ask` prints the note `ask_metered()` adds, naming the path of the saved record (or saying it is lost) on stderr, because Click would otherwise print only `Aborted!`. The criterion text above is unchanged.
- **AC-25**: The cost line gives the number of calls, input and output tokens, dollars by the recorded usage, dollars by the guard's rule (a failed call at its bound), and the ceiling.
- **AC-26**: `ask` opens its client with `build_client()`, so the SDK's own retries stay off and one call is one billed request (spec 0004 AC-70).

*The record*
- **AC-27**: The paid call is written to one file under `artifacts/asks/` as it settles, holding the question, the search words, the items and links sent, the raw reply, the checked claims, the usage, both costs, the model, the effort, the prompt version and the corpus commit.
- **AC-27b**: The write refuses to replace an existing file (`ArtifactCollisionError`).
- **AC-27c**: When the call's record cannot be written, `ask` still prints the answer and the call's usage, says the record is lost, and exits 1.
- **AC-28**: A record's file name is `<UTC time>-<slug>.json` for a typed question and `<UTC time>-eval-<stem>-q<N>.json` for an `--eval` ask, where `<stem>` is the eval file's name without its extension.
- **AC-29**: Every `--eval` ask writes a record that carries the eval file and the number N, including one that made no call because no item matched (AC-12).

*Running the eval questions*
- **AC-30**: `ask --eval N` takes the `question` text of entry N (counting from 1) of `--eval-file` (default `eval/linked-records-research.json`) from `read_eval_set()`, rejects an N out of range or an empty question, and prints nothing from the entry's expected chain or answer.
- **AC-31**: A held out eval file is refused without `--release-held-out`, and the flag is refused on a file that is not held out, by `read_eval_set()` unchanged.
- **AC-32**: `ask --eval N --release-held-out` exits 1 before any call when `artifacts/asks/` holds a record, matched by the exact pattern of AC-28, for that file stem and N that contains a settled call. A record of a failed call or of no call does not count, so that question can be run again.
- **AC-33**: `ask` prints no pass, fail, total or rate. The engineer judges each answer against the expected one.

## Decision

**Chosen option**: a new `ask` command with retrieval and checking in code, one structured call to Claude Sonnet 5.5 over one pack of up to 90 items, and a new spend function `ask_metered()` beside `run_metered()`.

The points the engineer fixed after the 2026-10-19 hand prototype are built as given: the retrieval of AC-7 to AC-12b, the print order of AC-1, the citation rule of AC-16 to AC-17b, the history rule of AC-14 and AC-18, and the guarded spend of AC-21 to AC-26. **One change to those points, made by the engineer at the cross check on 2026-10-19:** the second look (a wider search and a second call when the first answer says the items do not support a claim) is dropped from this spec. The single pack is already the wide one: 16 hits and 90 items, about the size the hand prototype handled. The second look is a Follow-up, to be added only if a tuning answer on questions 1 to 5 shows a retrieval miss the wider pack did not fix. The `missing` list stays and is printed, so such a miss is visible in the output.

Decided here after being open:

- **Search words**: chosen by code (AC-7), not by a first model call. Runner up: a cheap first call that adds synonyms.
- **Model**: `claude-sonnet-5-5`, the model that built the graph, whose rates `cost.py` already holds. Runner up: Opus 5.5, which needs its rates added first.
- **Guard**: `ask_metered()` is a sibling of `run_metered()` in `metered.py`. `run_metered()` itself cannot carry an ask (see the Premise note in `rationale.md`). Runner up: generalise `run_metered()`.
- **Answer shape**: structured claims (AC-15), so code checks ids and links with lookups. Runner up: prose with id tags.

Decided without a question, with the runner up:

- **`ASK_MAX_TOKENS` is 16,000** and effort follows `settings.effort` (default `medium`). Thinking counts inside the cap, so a small cap risks a cut off reply. Runner up: 8,000, which halves the bound but can truncate the JSON.
- **No prompt cache.** The system prompt is far under what `extract` caches (57,494 tokens), so `ask` skips the cache and does not use `run_metered()`'s rule that stops a call that read no cache.
- **No automatic retry.** A failed call ends the command (AC-24); the engineer runs it again. Runner up: one retry as in `extract`, rejected because each retry is a billed call on a question that costs cents to rerun by hand.
- **The model sees held items**, labelled `HELD` in the prompt and printed as `held` (AC-13, AC-19). Runner up: accepted items only, rejected because the engineer fixed both in.
- **A held out question with a settled answer runs once**, enforced by a cheap check on the saved records (AC-32). A failed call does not use the question up. Runner up: no check and rely on discipline.
- **Ids are searchable** (AC-8), so a question that names "spec 0007 AC-19" finds that item. Runner up: text only, rejected because the eval questions name items this way.

**Implementation skills**: `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `pydantic` (`pydantic/skills`, `.agents/skills/pydantic/`) · `claude-api` (`anthropics/skills`, bundled with Claude Code)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model sketch**:
Nothing is added to Neo4j and no migration runs. `ask` reads the graph once with `read_graph(..., with_held=True)` and works on the immutable `GraphSlice`. Three new values, all frozen:

- `Answer` (Pydantic): `verdict: Literal["answered", "partly", "not_supported"]`, `claims: tuple[Claim, ...]`, `missing: tuple[str, ...]`. `Claim`: `text: str`, `cites: tuple[str, ...]`, `basis: Literal["link", "text", "inferred"]`.
- `CheckedClaim`: a `Claim` plus `rejected_ids`, `uncited`, `inferred`, `history` and `held_ids`, all set by code.
- `AskRecord`: the JSON of AC-27 and AC-29, written under `artifacts/asks/`. Nothing reads it back except AC-32's file name and settled call check.

The `ask` package imports no `anthropic`, not even under `TYPE_CHECKING`, because the fence test matches that text. So `metered.py` holds the client, the token count and the call, and imports `Answer` and the prompt from `ask/`. `ask/` must not import `metered.py`, to avoid a cycle.

**State transitions**:
One question moves through: words, pack, bound check, one call, claim checks, print, record. No loop and no second call.

**API surface**:
| Command | Key inputs | Key outputs | Key errors |
|---|---|---|---|
| `tracepath ask QUESTION` | `QUESTION`, `--ceiling USD` (req), `--dry-run`, `--root` | items, answer, cost line, a record file | exit 1: no ceiling, graph without held items, unreadable manifest, unpriced model, ceiling too low, failed call |
| `tracepath ask --eval N` | `N`, `--eval-file`, `--release-held-out`, `--ceiling USD` (req), `--dry-run` | the same | exit 1 as above, plus held out refusals (AC-31, AC-32) |

Output shape (ids illustrative):

```
Question: <text>
Graph: held view yes, narrow hold yes, corpus 2e40bcf.
Search words: landing, rule, profile, readownprofile ...
Items sent: 74 (16 hits, 58 neighbours, 0 cut).
  0008/AC-7   requirement  accepted  docs/specs/0008-.../index.md:54   hit
  0003/AC-14  requirement  held      docs/specs/0003-.../index.md:88   hop 1
  0002/AC-10  requirement  accepted  STRUCK  docs/specs/0002-.../index.md:31   hop 2
Answer (verdict: answered):
  1. <claim text> [0008/AC-7] link
  2. <claim text> [0003/AC-14 held] read from text
  3. <claim text> [0002/AC-10] HISTORY read from text
  4. <claim text> [0007/AC-3] [0009/AC-1] INFERRED
Missing: <what the items did not hold>
Cost: 1 call, 6,412 in, 1,903 out, $0.0318 by recorded usage, $0.0318 by the guard's rule, ceiling $0.50.
Record: artifacts/asks/2026-10-20T09-12-31Z-why-does-the-landing-rule.json
```

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| Search | the search words | the question text, `tokenise()` in `ask/retrieve.py`, the stoplist of AC-7 as a constant in the same file |
| Search | a word's df and N | counted over every node `read_graph()` returned |
| Search | a node's searchable text | `Node.text`, `Node.title` or `Node.mention`, and `Node.canonical_id` |
| Print items | accepted or held | `Node.held` |
| Print items | STRUCK | `Node.struck` |
| Print items | HISTORY and what replaces it | a `superseded-by` or `corrected-by` link in the slice, source is old, target is new, held or accepted |
| Print items | `file:line` | `Node.file` and `Node.file_line` (Record: `Node.path`; Unresolved: `Node.file` and `Node.line`) |
| Check claims | which links exist | the `GraphSlice.links` sent with the call |
| Bound | counted input tokens | the free `messages.count_tokens` endpoint over the real request |
| Bound and cost | rates | `RATES[settings.model]` in `extract/cost.py`, through `rates_for()` and `tokens_cost()` |
| Bound | the output cap | `ASK_MAX_TOKENS` constant (16,000), decided above |
| Call | model and effort | `AnthropicSettings` (`ANTHROPIC_MODEL`, default `claude-sonnet-5-5`; `ANTHROPIC_EFFORT`, default `medium`) |
| Cost line | the ceiling | the `--ceiling` flag |
| Graph line and record | corpus commit, held view, narrow hold | `artifacts/graph-build.json` |
| Record | the timestamp | the clock, read once in `cli.py` and passed in |
| `--eval` | the question text | `entries[N-1]["question"]` of the entry list `read_eval_set()` returns, with its own range and empty check |
| Held out guard | whether a settled record exists | the files under `artifacts/asks/` whose names match AC-28's pattern for the stem and N, and whose content holds a settled call |

**Key invariants**:
1. The model sees only ids that are in the pack, and every id it cites is checked against that pack (AC-16). A claim never prints as supported when its id was not sent.
2. A paid call is never made without its bound inside the ceiling (AC-22), and a call with no recorded rates is never priced (AC-23).
3. Retrieval, history labelling, claim checking and printing are pure functions of the slice, the question and the reply. Only the client, the clock, the files and Neo4j sit at the edge.
4. The `ask` package imports no `anthropic` and names no `build_client` or `extract_once`; the one call lives in `metered.py`.
5. Nothing in `ask` reads `eval/held-out.json` except through `read_eval_set()` with `--release-held-out`.

**Security model**:
One local user. The question and the item text go to the Anthropic API under the key in `.env`, as extraction does; the corpus is JobHunt's public decision records. No other user, role or tenant. No regulated data. Held items are unreviewed extraction, so they are labelled `HELD` to the model and in the output.

**Configuration required**:
No new environment variable. `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` and `ANTHROPIC_EFFORT` already exist. `ASK_MAX_TOKENS`, the pack limits (16 hits, 90 items) and the prompt version (`ask-1`) are constants in code.

**Critical test scenarios** (all with a fake call and a hand built `GraphSlice`; none reaches the API):
- Happy path: a question whose words match two linked items prints both, a reply citing both with basis `link` prints `link`, the cost line and the record, verifies AC-1, AC-8b, AC-10, AC-17b, AC-27.
- Failure case: a reply citing an id that was not sent prints `CITATION REJECTED`, and a `link` claim with no link between its ids prints `INFERRED`, verifies AC-16, AC-17.
- Failure case: a ceiling below the call's bound stops before the call with exit 1, verifies AC-22. A call that raises, stops on `max_tokens`, or returns a reply that fails validation is saved at its bound and ends with exit 1, verifies AC-24.
- Failure case: a record that cannot be written still prints the answer and exits 1, verifies AC-27c. A second write to the same path raises, verifies AC-27b.
- Edge: a question with no matching word makes no call, verifies AC-12. A question naming "0007 AC-19" finds the item through its id, verifies AC-8. A tokeniser case with a path and `readOwnProfile()` keeps the tokens whole and stripped, verifies AC-7.
- Edge: a struck item and the source of a held `superseded-by` link print as history and mark the claim `HISTORY`; the replacing item is in the pack and its citation passes, verifies AC-14, AC-14b, AC-18. The system prompt text tells the model to say it, verifies AC-18b.
- Guard: `--eval N --release-held-out` with a settled record for the same stem and N exits 1 before any call; with only a failed or no call record it does not, and `-q1` never matches `-q10`, verifies AC-32. `--eval` with no match writes a record, verifies AC-29. `test_spend_fence.py` passes unchanged, verifies AC-21.

## Build plan

Build approach is Tracer Bullet (AGENTS.md): a thin real thread first, then thicken. The thread is question, retrieval, one call, checked answer, record. No step before step 4 makes a billed call.

1. **Retrieval and `ask --dry-run`**, no model: `ask/retrieve.py` (tokeniser, scoring, neighbours, history), the `ask` command with the `QUESTION` argument, the graph and manifest checks, the item printout. Run it dry on eval question 1 to read the items. Satisfies AC-2, AC-4, AC-5, AC-5b, AC-5c, AC-6, AC-7, AC-8, AC-8b, AC-9, AC-10, AC-11, AC-12, AC-12b, AC-13, AC-14, AC-14b.
2. **The answer type, prompt and claim checks**, pure: `ask/answer.py` (the `Answer` model, the system prompt, the pack rendering, the checks) and the answer printing. Tested with hand written replies. Satisfies AC-15, AC-15b, AC-16, AC-16b, AC-17, AC-17b, AC-18, AC-18b, AC-19, AC-20.
3. **The guarded call and the record**: `ask_metered()`, `ask_bound()` and the real call and token count in `metered.py`, the cost line, `ask/record.py`. Tested with a fake call. Satisfies AC-1, AC-3, AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-27b, AC-27c, AC-28.
4. **Gate, the first paid step**: `ask --dry-run` over the five eval questions prints each counted input and bound. Stop and give the engineer these figures and a worst case. After the go and a ceiling, run eval question 1 alone and record its output tokens in `experiments/` as the first measured per call cost. Every later estimate comes from that measurement and the real number of calls (reflex of 2026-09-23).
5. **Eval wiring**: `--eval`, the eval records, the held out refusals, the one run guard. Satisfies AC-29, AC-30, AC-31, AC-32, AC-33.
6. **Eval questions 1 to 5**, one per command, each under its own ceiling, the engineer judging each against its expected answer. The prompt may be adjusted here and only here; each change is committed with a new prompt version before the next question runs. Stop when the engineer freezes the prompt.
7. **Held out questions**, after the freeze commit: one per command, once each, never used to adjust anything. The engineer judges. Report the result against the bar (at least 4 of 5 and 3 of 4), with each miss's cause, retrieval or reading, read from its record.

## Consequences

**Positive**:
- The tool answers a plain English why question across record boundaries, where the walk fails today.
- Each answer carries its evidence: the items sent, the checked claims, the cost and a saved record, so a wrong answer is diagnosed from files, not memory.
- One call per question keeps the worst case small and removes a whole class of two call rules.
- Spending is bounded per call, and a held out question with a settled answer cannot be repeated by accident.

**Negative / tradeoffs**:
- Retrieval is word overlap. A relevant item that shares no word with the question and sits more than 2 hops from a hit is not found, which is the class of the 0007 AC-12 miss. With no second look, only the wider pack guards against it.
- A `text` claim that cites two items is trusted as the model's reading of the text. Code can verify a `link` but cannot verify that an item's text states a connection. The two are printed differently so the engineer can check them.
- Answers are not repeatable run to run. The same question can print different claims, so one judged answer is one sample.
- A proven absence is not proven: eval question 4 will print `not_supported` or `partly`, meaning no stated connection in the items found, not that none exists.
- Held items, which are unreviewed extraction, appear in answers. They are marked, but a claim resting on one is only as good as that item.
- A held out answer whose record could not be written (AC-27c) leaves nothing for AC-32 to see, so it could be run again. The result report must say so if it happens.
- `artifacts/asks/` is a new tracked folder that grows with every paid question.
- `metered.py` gains a second spend path next to the extraction one, so the file now guards two kinds of call.

**Neutral**:
- `trace`, `eval` and `load` are unchanged, and eval question 4's walk PASS stays as recorded.
- Features 7 and 8 stay after v1 as retrieval improvements; this feature is their baseline.

## Follow-up

- [ ] **The second look**, dropped by the engineer on 2026-10-19: add it only if a tuning answer on questions 1 to 5 shows a retrieval miss that the 90 item pack did not fix. It would need its own spec amendment covering the second call's pack (the first pack plus new items), its record, its dry run price and its failure rules.
- [ ] The refusal text of `read_eval_set()` still says a held out file runs "once features 13 and 11 have both committed". For `ask` the real gate is the prompt freeze commit (build plan step 7). Reword it, or leave it and note the difference in the held out result.
- [ ] Add `ask` to the Commands list in AGENTS.md once built (`/sync`).
- [ ] Measured per call cost is unknown until build plan step 4. The bound below is a ceiling, not an estimate: about $0.18 per call at `ASK_MAX_TOKENS` of 16,000 (inferred: about 90 items at 4 characters per token over the graph's measured 232 character mean item text, so roughly 8,000 input tokens; the dry run measures the real count). Nine questions at one call each come to about $1.6 at the bound, and each rerun of a question 1 to 5 after a prompt change adds about $0.18.
- [ ] If the bar is missed, record each miss's cause from its saved record (retrieval or reading) in the scope, as the v1 finish line asks.
- [ ] After v1, decide whether `ask --eval` should run all questions in one command; this spec runs one per command so a stop is by structure.
- [x] After v1, add a distinct verdict for an absence answer. _Built 2026-10-19 as `no_documented_link`, prompt `ask-2`; see the note on AC-15._ Seen on eval question 4 (2026-10-19, record `artifacts/asks/2026-10-19T21-58-07Z-eval-linked-records-research-q4.json`): its correct answer is "no documented link", but the only verdict that fits is `not_supported`, which reads as "could not answer". A separate verdict would let an answer say the items were found and hold no stated connection. Recorded by the engineer after the prompt `ask-1` freeze; not built in v1.
- [ ] After v1: held out question 3 is evidence for the second look (the first Follow-up item). Retrieval did not reach 0018 line 63 (`0018#review-findings:10`), the invariant's text, with nothing cut and the item beyond two hops (record `artifacts/asks/2026-10-19T22-17-49Z-eval-held-out-q3.json`). Once a fix targets it, held out question 3 no longer counts as unseen. Recorded by the engineer on 2026-10-19.
