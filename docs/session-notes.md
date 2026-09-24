# Session notes

In session residue that no spec, scope row, or `AGENTS.md` owns. Written by `/checkpoint save`, read back by `/checkpoint restore`. Entries leave when they find a real home.

## Ruled out

Each of these is already decided in a spec. Listed here as pointers so a fresh session does not re open them, not as a second copy of the reasoning.

- `effort=low`: at `low`, 2 of 3 runs merged a correction into the span of the claim it replaced and stored it marked struck, filing a current fact as obsolete. Spec 0001, model and run policy row, amendment (b); evidence in experiment 0002.
- An identity anchor below AC-4's alignment threshold: of 26 null line spans, 13 do anchor but all score 0.615 to 0.942, under the 0.96 threshold, and no unit reaches three way agreement. It rescues pairs and acceptance needs triples. Spec 0002, AC-11(d).
- Vector or embedding search for locating spans: near identical criterion wording recurs across this corpus, so a nearest neighbour hit returns a confident wrong line, which is worse than `null`. `src/tracepath/extract/locate.py` module docstring, and spec 0002's Follow-up.

## Standing instructions

- Cost sensitive: this file keeps only the running total now, the stop and flag rule itself is `docs/reflexes.md`'s own entry. About $7.50 spent so far: roughly $6.50 before experiment 0004, plus $1.0185 for the label round trip run.
- Cost figures to hand, all measured: $0.1268 per call at `medium`, about $0.2198 per call on `0006 ## Feature design` (the largest unit extracted so far), about $3.30 to re-run AC-14's 8 unit coverage set, and about $35 for a batched whole corpus run against about $70 unbatched.
