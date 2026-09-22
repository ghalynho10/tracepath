# Experiments

An experiment answers one question with real evidence: a prompt variant, a model
comparison, a measurement, a "does this work at all" probe. It is written on
purpose, read by people, and never read by the tool.

- `artifacts/` is the pipeline's own output and the source of truth for a graph
  rebuild. If the tool would notice a file's absence, it belongs there, not here.
- Artifacts are evidence. Never delete a run's artifacts to make a set clean. Move
  them instead, to `artifacts/superseded/<date>-<config>/` or into the experiment's
  own `data/`, with a one line note saying which configuration produced them and why
  they were superseded. Commit `artifacts/` before any run that clears it, so nothing
  that has been cited exists only in a chat.
- An experiment is frozen once run. It records what was true on that day, under
  that configuration, with the corpus commit and the code commit named.
- Each experiment is `NNNN-slug/` with a `README.md` (question, method, config,
  result, conclusion, date) and an optional `data/` for its measurements,
  tables and any non-production output. Scripts it needed live beside them.
- When an experiment settles a decision, its conclusion is summarised into that
  spec's `rationale.md`, and the spec links here for the long form. The spec
  stays self-contained; the evidence is not copied twice.
