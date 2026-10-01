# Session notes

In session residue that no spec, scope row, or `AGENTS.md` owns. Written by `/checkpoint save`, read back by `/checkpoint restore`. Entries leave when they find a real home.

## Open threads

- Rules the engineer set while ruling, kept in `data/method-notes.md`: a struck, superseded criterion is ruled as one entity; a user story's "so that" clause can carry the feature's distinguishing value rather than rationale. Relationships take four checks: stated in the text, right type, right direction (old to new, AC-8), right ends. On every `disagree`, write what it should have been (type, direction or ends), so the rulings can later score another model, not only this one.
- Experiment 0006's ruling (spec 0003, AC-30) resumes at `0015`'s entity sample, item 1. 30 of the 45 required entity and relationship items (10 entity plus 5 relationship per unit, across `0014`, `0015`, `feature-33`) are still unmarked. The dropped link sample and the cold read are both prepared (`data/ruling-sheet.md`, `data/cold-read.md`) but deferred, not marked, until the bar is applied to the 45 required items.
- The ruling guide is saved outside the repo at `~/Documents/Work/DEV/extraction_review/extraction-ruling-guide.md`; copy it to `docs/extraction-ruling-guide.md` and commit. Any helper chat may explain rules or find source text, never suggest marks.
- The 24 call type coverage set (spec 0003, build plan step 28) is still unstarted: re estimate its cost from the re check's own measured per call figures once the bar is applied to the 45, and confirm before it runs.
- A training set distilled from Claude's labels is gated on Anthropic's Commercial Terms D.4 ("train competing AI models"); the routes that hold are an open weight teacher (check the exact version's license, and the platform's terms if hosted), or asking Anthropic. If the student classifies relationships between spans Claude extracted, Claude's outputs are still in the training inputs. Accepted items are auto accepted, not human checked: `artifacts/review-log.json` has 0 entries.
- A zero shot local model test (a small open weight model run through Ollama, classifying relationships with no training, scored against the engineer's rulings) belongs under scope's Deferred "Two stage typing" entry, after feature 5 and measured by the eval, not as a separate plan.
- Two `/debug` follow ups, both found running experiment 0006, neither fixed yet: (1) a failed attempt's recorded usage can badly undercount, since `client.extract_once()`'s `ValidationError` path snapshots usage before the API's final usage event lands (observed: 2 output tokens recorded for a ~15,000 character, nearly complete response). (2) `extract_once()`'s `except anthropic.APIError` clause does not catch a connection dropped mid stream (a raw `httpx2`/`httpcore2` error propagates past it uncaught), so a transient network fault crashes a run rather than being recorded as a failed, retriable attempt. Both are narrowed and fixed already in `experiments/0006-accuracy-bar-recheck/run_recheck.py`'s own call path; only `src/tracepath/extract/client.py` still carries them.
- Spec 0001's `rationale.md:10` says the `LLMGraphTransformer` failure "is documented, not assumed" but points nowhere. At the next /architect amendment, add a forward pointer from that line to `experiments/0007-langchain-graph-transformer-baseline/`.
- Spec 0002 AC-13 and its verify/scope lines still say writes assert counters; the code asserts RETURN count(...) against the row count, which AGENTS.md now describes. Reword at the next /architect amendment.

## Ruled out

Each of these is already decided in a spec. Listed here as pointers so a fresh session does not re open them, not as a second copy of the reasoning.

- `effort=low`: at `low`, 2 of 3 runs merged a correction into the span of the claim it replaced and stored it marked struck, filing a current fact as obsolete. Spec 0001, model and run policy row, amendment (b); evidence in experiment 0002.
- An identity anchor below AC-4's alignment threshold: of 26 null line spans, 13 do anchor but all score 0.615 to 0.942, under the 0.96 threshold, and no unit reaches three way agreement. It rescues pairs and acceptance needs triples. Spec 0002, AC-11(d).
- Vector or embedding search for locating spans: near identical criterion wording recurs across this corpus, so a nearest neighbour hit returns a confident wrong line, which is worse than `null`. `src/tracepath/extract/locate.py` module docstring, and spec 0002's Follow-up.

## Standing instructions

- Cost sensitive: this file keeps only the running total now, the stop and flag rule itself is `docs/reflexes.md`'s own entry. About $15.50 to $15.80 spent so far, the range pending a Console check for `0015`'s before run's crashed first call in experiment 0006: the connection dropped before any usage event arrived, so nothing was billed that the pipeline itself was told about, and if the API did bill something, that is the unresolved width of the range.
- Cost figures to hand, all measured: $0.1268 per call at `medium` before the examples, about $0.2198 per call on `0006 ## Feature design`. Under prompt `0003.0` the cached prefix is 49,114 tokens (about $0.20 to write to the 1 hour cache, about $0.0098 per read), and output averaged 32,390 tokens per call on `0021`, 20,307 on `0013 ## Feature design`, and 17,937 on `feature-9`. About $35 for a batched whole corpus run against about $70 unbatched, measured before the examples.
