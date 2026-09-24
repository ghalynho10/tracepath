# Session notes

In session residue that no spec, scope row, or `AGENTS.md` owns. Written by `/checkpoint save`, read back by `/checkpoint restore`. Entries leave when they find a real home.

## Open threads

- Branch state, verified 2026-09-23: `main` is deliberately parked at `ee2e264` so feature 4's closing steps keep `/test`'s last commit fallback. `experiment/0002-effort-low-fidelity` carries the spec amendments and the build; `docs/merge-after-closing-steps` and `experiment/low-effort-calibration` are also unmerged. All three merge after `/check verify` and `/test`, not before.
- The merge timing rule is already a reflex, and it lives on the `docs/merge-after-closing-steps` branch, which is itself deliberately unmerged. So `docs/reflexes.md` on any other branch shows one rule and looks as though the merge rule were missing. It is not. Check that branch before concluding a reflex is absent.
- Agreed ordering: finish feature 4, then feature 12 (prompt examples), then re-run AC-14 if the prompt changed, then feature 11 (queue policy, needs feature 6 for eval evidence), then feature 5 onward, with the whole corpus run (feature 9) last. The scope carries this too, on feature 12's At a glance row and the "feature 12 comes first" pointer under feature 11.

## Ruled out

Each of these is already decided in a spec. Listed here as pointers so a fresh session does not re open them, not as a second copy of the reasoning.

- `effort=low`: at `low`, 2 of 3 runs merged a correction into the span of the claim it replaced and stored it marked struck, filing a current fact as obsolete. Spec 0001, model and run policy row, amendment (b); evidence in experiment 0002.
- An identity anchor below AC-4's alignment threshold: of 26 null line spans, 13 do anchor but all score 0.615 to 0.942, under the 0.96 threshold, and no unit reaches three way agreement. It rescues pairs and acceptance needs triples. Spec 0002, AC-11(d).
- Vector or embedding search for locating spans: near identical criterion wording recurs across this corpus, so a nearest neighbour hit returns a confident wrong line, which is worse than `null`. `src/tracepath/extract/locate.py` module docstring, and spec 0002's Follow-up.

## Standing instructions

- Cost sensitive. Stop and flag before anything that spends API credit, with a measured estimate, and wait for a go ahead rather than proceeding on a plausible sounding number. About $6.50 spent so far. Now a reflex on the `docs/merge-after-closing-steps` branch; kept here only for the running total.
- Cost figures to hand, all measured: $0.1268 per call at `medium`, about $0.2198 per call on `0006 ## Feature design` (the largest unit extracted so far), about $3.30 to re-run AC-14's 8 unit coverage set, and about $35 for a batched whole corpus run against about $70 unbatched.
