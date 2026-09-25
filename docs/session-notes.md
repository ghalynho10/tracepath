# Session notes

In session residue that no spec, scope row, or `AGENTS.md` owns. Written by `/checkpoint save`, read back by `/checkpoint restore`. Entries leave when they find a real home.

## Open threads

- Ruling for spec 0003 AC-16 is in progress in `experiments/0005-held-out-prompt-examples/data/ruling-sheet.md`, the repo copy only; save before closing. Done and committed at `1b3acc6`: group A entities 1 to 5 (3 agree, 2 disagree) and relationship 1 (agree). Next session: entities 8 and 10 first while fresh, then relationships 2 to 5, then the 10 lost links; then groups B and C, about 5 entities and 5 relationships each. Entities 6, 7 and 9 are skipped by choice; record that in `data/method-notes.md`.
- Rules the engineer set while ruling, kept in `data/method-notes.md`: a struck, superseded criterion is ruled as one entity; a user story's "so that" clause can carry the feature's distinguishing value rather than rationale. Relationships take four checks: stated in the text, right type, right direction (old to new, AC-8), right ends. On every `disagree`, write what it should have been (type, direction or ends), so the rulings can later score another model, not only this one.
- The ruling guide is saved outside the repo at `~/Documents/Work/DEV/extraction_review/extraction-ruling-guide.md`; copy it to `docs/extraction-ruling-guide.md` and commit. Any helper chat may explain rules or find source text, never suggest marks.
- AC-17 fired: group B (`0013 ## Feature design`) after runs spread 3 entities against the bar of 2, about 9% of ~32 entities, with links at 15/15/15. Decide the AC-2 heterogeneity test after the ruling; the advisor leans skip, recording the relative spread, without moving the bar. The 24 call type coverage set ($5.69 central, $6.12 wider) is also held until the ruling. That estimate was made on the 20,851 output token anchor (the `0002.3` baseline) and must be re-estimated from the `0003.0` measurements before approval.
- Before the 24 call run: amend spec 0001's artifact storage row and build four fixes: `write_run` refuses to overwrite, and so does `move_superseded` in `run_units.py`; a run id and an artifact format version; a SHA-256 of the unit text; the raw response text and `stop_reason`. Plus an erratum line in experiment 0003's README: its `extracted_at` is a placeholder, and the real run time is at or before `472b6ed`. No change to experiments 0001 to 0004.
- After feature 12 merges: `/debug` the failed attempt usage undercount in `extract_once` (a schema failure records about 5 output tokens) on its own `fix/` branch.
- A training set distilled from Claude's labels is gated on Anthropic's Commercial Terms D.4 ("train competing AI models"); the routes that hold are an open weight teacher (check the exact version's license, and the platform's terms if hosted), or asking Anthropic. If the student classifies relationships between spans Claude extracted, Claude's outputs are still in the training inputs. Accepted items are auto accepted, not human checked: `artifacts/review-log.json` has 0 entries.
- A zero shot local model test (a small open weight model run through Ollama, classifying relationships with no training, scored against the engineer's rulings) belongs under scope's Deferred "Two stage typing" entry, after feature 5 and measured by the eval, not as a separate plan.

## Ruled out

Each of these is already decided in a spec. Listed here as pointers so a fresh session does not re open them, not as a second copy of the reasoning.

- `effort=low`: at `low`, 2 of 3 runs merged a correction into the span of the claim it replaced and stored it marked struck, filing a current fact as obsolete. Spec 0001, model and run policy row, amendment (b); evidence in experiment 0002.
- An identity anchor below AC-4's alignment threshold: of 26 null line spans, 13 do anchor but all score 0.615 to 0.942, under the 0.96 threshold, and no unit reaches three way agreement. It rescues pairs and acceptance needs triples. Spec 0002, AC-11(d).
- Vector or embedding search for locating spans: near identical criterion wording recurs across this corpus, so a nearest neighbour hit returns a confident wrong line, which is worse than `null`. `src/tracepath/extract/locate.py` module docstring, and spec 0002's Follow-up.

## Standing instructions

- Cost sensitive: this file keeps only the running total now, the stop and flag rule itself is `docs/reflexes.md`'s own entry. About $11.56 spent so far: $7.50 before feature 12, $0.6918 for the fresh `0021` baseline, and $3.37 for the 15 held out calls. One failed attempt's real output is unmeasured (the undercount above).
- Cost figures to hand, all measured: $0.1268 per call at `medium` before the examples, about $0.2198 per call on `0006 ## Feature design`. Under prompt `0003.0` the cached prefix is 49,114 tokens (about $0.20 to write to the 1 hour cache, about $0.0098 per read), and output averaged 32,390 tokens per call on `0021`, 20,307 on `0013 ## Feature design`, and 17,937 on `feature-9`. About $35 for a batched whole corpus run against about $70 unbatched, measured before the examples.
