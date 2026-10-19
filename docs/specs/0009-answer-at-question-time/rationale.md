# 0009. Answer at question time: rationale

The decision record for [index.md](index.md). The build does not read this file.

## Context

> ⚠️ Premise note: the engineer's rule 6 says the paid call goes through `run_metered()`. As written, `run_metered()` cannot carry an ask. It takes `Plan` objects made of extraction `Unit`s, it builds and writes a run artifact for every attempt through `build_artifact()`, and it stops a command when a call after the first reads no cache (AC-11 of spec 0004). An ask has no unit, no artifact of that kind, and no cache to read. The rule's purpose is that no paid call escapes the ceiling, the bound and the cost record. That purpose is kept by a sibling function in the same file; the letter of the rule is not. This is recorded here so the change is a visible choice (verified by reading `src/tracepath/extract/metered.py`).

Seven questions have been run against the walk (the five eval questions and two held out) and all fail at a document boundary (experiment 0015, PR #40). The scope changed direction on 2026-10-19: for the rest of v1, the author types a question and gets an answer whose every claim cites a graph item. A hand prototype, with the session playing the model, was marked 4 right and 1 partly right of 5. That is a hint from one hand run, not a measurement of the built feature, and its one partial result was a retrieval miss (0007 AC-12).

The graph the command works on is small. A read in this session found 2,649 entities (613,417 characters of text, a mean of 232 per item, a longest of 2,138, 26 struck) and 1,470 typed links: 810 `SATISFIES`, 305 `UNCLASSIFIED`, 233 `VERIFIES`, 57 `AMENDED_BY`, 30 `BLOCKED_BY`, 26 `SUPERSEDED_BY`, 9 `CORRECTED_BY`. Of the entities, 485 are held (and 269 of the links); the graph also holds 117 Record and Unresolved nodes. One read already exists (`read_graph()`), and the whole result fits in memory.

The paid path is already guarded for extraction: a ceiling, a per call bound from the free token count endpoint, a cost record, and `tests/test_spend_fence.py` listing every file that may reach the model. Rates are recorded for `claude-sonnet-5` and `claude-sonnet-5-5` only, and an unrecorded model is never priced. The success bar is fixed in the scope: at least 4 of 5 eval and 3 of 4 held out, judged by the engineer; questions 1 to 5 may adjust the prompt and the held out questions run once at the end. The held out set sits in a small cluster of records (0004, 0010, 0016 to 0018), so a pass there is a narrow check.

## Options considered

The retrieval, the print order, the citation and history rules, and the use of the guard are fixed by the engineer and are not weighed here. Five things were open. The second look was also fixed at first and was dropped at the cross check (below).

### 1. Who picks the search words

**Option A: code (chosen).** A tokeniser, a fixed list of common words and a rarity score over the graph's own text.
- Pro: free, the same question gives the same items, and the printed item list shows why each was found.
- Pro: a retrieval miss is visible and the cause is a word, which a later fix to the tokeniser or stoplist can address.
- Con: no synonyms. A question that says "dedicated query" cannot find an item that says "its own reader".

**Option B: a first model call.** A cheap call turns the question into terms and synonyms.
- Pro: closes the vocabulary gap.
- Con: adds a billed call to every question and a second thing to judge.
- Con: the terms become the model's, so a miss is harder to trace to a cause.

### 2. Which model answers

**Option A: Sonnet 5.5 (chosen).** The model that built the graph.
- Pro: rates already recorded, so the bound and the cost work with no new price data.
- Pro: the task is reading a few thousand tokens of items and citing them, which suits it.
- Con: a stronger model might read an ambiguous chain better.

**Option B: Opus 5.5.**
- Pro: stronger at careful reading, the failure that would remain after retrieval is fixed.
- Con: its rates must be taken from the vendor's pricing page and added to `cost.py`, and each call costs more.
- Kept as the runner up: try it only if a miss traces to reading and not retrieval.

**Option C: Haiku 5.5.**
- Pro: cheapest.
- Con: same rates gap, and holding every claim to a cited id while saying when items do not support it is the kind of judgement a smaller model gets wrong.

### 3. How the paid call meets the guard

**Option A: a sibling `ask_metered()` in `metered.py` (chosen).**
- Pro: reuses `rates_for()`, `tokens_cost()` and the stop style, and leaves extraction untouched. It needs its own bound function, `ask_bound()`, because `per_call_bound()` prices extraction's output cap and a cache write.
- Pro: `metered.py` is already in `ALLOWED`, so the fence test does not change.
- Con: the file now holds two spend paths, and a future edit to one could miss the other.

**Option B: generalise `run_metered()`.**
- Pro: one function, no sibling to drift.
- Con: it reopens the most pinned code in the project (dozens of criteria in specs 0004 and 0007) for a feature that needs none of its rules.

**Option C: a new module plus an `ALLOWED` entry.**
- Pro: the smallest change to `metered.py`.
- Con: widens the list of files that can spend money, which the fence test exists to keep short.

### 4. The shape of the model's answer

**Option A: structured claims (chosen).** One Pydantic model, native structured output, as extraction does.
- Pro: ids and links are checked by lookup, the printed verdict comes from a field and not from reading prose, and `INFERRED` does not depend on the model remembering to write it.
- Con: a claim must be one sentence with a basis, which suits why answers but forces a short style.

**Option B: prose with id tags.**
- Pro: a simpler schema and a more natural answer.
- Con: "the items don't support this" becomes text matching, and inferred links are marked only if the model volunteers it.

### 5. Whether to save each paid answer

**Option A: one JSON per ask (chosen).**
- Pro: the evidence the engineer judges from, the cost record, and the basis for the held out guard.
- Con: a new tracked folder that grows.

**Option B: print only.**
- Pro: nothing new on disk.
- Con: a held out answer not copied is lost and cannot be bought again without breaking the run once rule.

## Rationale

The two forces that decided most of this are cost and checkability. A question costs cents, but the engineer pays for each call and has already seen an unflagged estimate come out 10 to 15 times low, so the spec states a bound (a hard maximum from a measured token count and a fixed output cap) and leaves the central figure to a measured first call. The success bar is judged by a person against a source line, so every claim must point at an item the code can check, and the output must separate a retrieval failure from a reading failure. That is why retrieval is code (visible and repeatable), the answer is structured (checkable by lookup), and the items print before the answer.

The sibling guard is chosen over changing `run_metered()` because the premise note's mismatch is real: three of its rules (units, run artifacts, the no cache stop) do not apply to an ask, and removing them from the shared function would put the best tested code in the project at risk for no gain. The sibling keeps what the rule is for. The cost of that choice is two spend paths in one file, accepted because the fence test still names one file and the ask path is small.

Two guards were considered and kept because they cheaply prevent a misleading result. The held out run once check (AC-32) is a file name lookup that stops a rerun from quietly invalidating the bar. The `link` check (AC-17) is a lookup that stops a model from labelling an inference as a stated link, the failure the scope names for questions 1 and 2. Three were considered and left out because no failure of that kind has been seen: a code check that an item's text really states a `text` claim, a second model that reviews the answer, and a retry on failure. The spec records the first as a known limit in Consequences.

The second look was dropped by the engineer at the cross check on 2026-10-19. The cross check showed it needed five extra rules (a second call's record name, its dry run price, its failure case, its pack and its exit codes), and that one call over the wide pack (16 hits, 90 items, about what the hand prototype handled) costs about the same as one first call and halves the worst case. What is given up is the extra search on the words the model says are missing. The `missing` list is still printed, so a retrieval miss stays visible, and the second look is a Follow-up to add only if a tuning answer on questions 1 to 5 shows a miss the wide pack did not fix.

The model's cost is not guessed here. The instruction is the reflex of 2026-09-23: derive an estimate from a measured per call cost and the real number of calls. Build plan step 4 produces the first measured figure from one real call before any further paid run.

## Evidence

- Graph size and link counts: a read through `read_graph(driver, database, with_held=True)` on 2026-10-19, run from this session against the local Neo4j.
- Held counts: the same read, 485 held entities and 269 held links, which equal the `held_view` figures in `artifacts/graph-build.json` (485 entities, 269 links, 38 unresolved).
- Link directions: `src/tracepath/extract/client.py` lines 154 to 156 (`superseded-by` and `corrected-by` run old to new, `amended-by` runs amended to amending).
- Rates and the cached prefix: `src/tracepath/extract/cost.py`.
- Spend fence: `tests/test_spend_fence.py`, `ALLOWED` and `PAID_MARKERS`.
