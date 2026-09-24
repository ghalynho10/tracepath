# 0003. Verify

## Commands

```bash
uv run pytest -m "not integration"   # the label pre check, the clearing rule, and example validation tests, no API, no Neo4j
uv run mypy                          # strict, covers the new pre check module
uv run ruff check . && uv run ruff format --check .
```

## The label pre check, proven with no API call

1. Load the committed `0002.3` artifacts for spec 0001's `## Binding rules` section (`artifacts/runs/`).
2. For each of the three runs, find rule 6's leading span, the regex `^\*\*6\.` to the first blank line after it, or to the next `**N.**` marker or the section end if no blank line intervenes first, and confirm exactly one entity's located offset falls inside it, in all three runs. **Do not use marker to next marker alone**: measured against these same three runs, that span gives rule 6 two, six and two candidate entities (17 of 24 rule instances across the section hold exactly one under that definition; rule 6 is not one of them). Marker to first blank line gives 23 of 24 exact one, the only miss being rule 4 in run 3 (no entity located in that span, correctly routes to AC-3's no label case). A run of this check itself is the regression test for the span definition, not only for the mechanism.
3. Run the pre check over the same three runs and confirm it sets `label: "binding rule 6"` on that one entity each time, and on no other entity in rule 6's span.
4. Rebuild the label index and confirm `("0001", "binding rule 6")` resolves to an entity in each of the three runs, the one located on rule 6's opening line in that run; its canonical id differs run to run (`0001#binding-rules:10`, `:12`, `:6`), by design, since derived ids are per run, verifies **AC-1**, **AC-12**.
5. Note the known remaining gap: the link from `0008`'s preamble to this entity still holds under `endpoint_not_accepted`, because `0008/AC-10b` (the entity on the other end of that relationship) was not accepted in experiment 0004's run. This is a separate, already understood acceptance condition (AC-11, spec 0002), not something this spec's label fix changes. Stating it here satisfies the round trip scenario's owed evidence without a new paid run for this part.

## The stray label clearing rule, proven with no API call

1. Build a `## Binding rules` fixture from the committed `0006 ## Feature design` run showing `key invariant 1` through `key invariant 6` (`artifacts/runs/0006/feature-design/run-1.json`), adapted so its entities sit inside a `## Binding rules` unit rather than their real `## Feature design` one, keeping the same invented labels.
2. Run the pre check and confirm every entity's `label` is cleared except the one, if any, whose located offset falls inside a rule's leading span, and except any whose label string is verbatim inside its own span, verifies **AC-4**.

## Example content scope, checked by inspection

- `examples/*.md`: confirm the assembled `SYSTEM_PROMPT` few shot block contains only each file's Input, Output, and the one assembled Rules list, byte for byte, filename sorted order, and none of any file's Reasoning notes or `## What this example covers` prose beyond the lifted excerpt statement.
- `examples/0008-preamble.md`: confirm the Validation caveat block is gone.
- Confirm the assembled Rules list carries the two new general rules (entity labelling, reference tables yield nothing) plus the five lifted and generalised ones (typing by claim not position; a non Record kind citation yields no link; a "Resolved..." follow up links unclassified with phrase and date; no guessed old to new pairs from a blanket renumbering; `embedded_second_claim` on a scope row), stripped of project history references, and exists in exactly one place, not duplicated between `SYSTEM_PROMPT` and any example file.
- Confirm `0006`'s Input carries the excerpt statement ("this input is a contiguous verbatim excerpt; everything inside it is extracted, nothing is skipped") next to it.
- Confirm `schema.py`'s `ExtractedEntity.label` field description (`schema.py:149`) no longer reads `key invariant 1`; confirm `ReferenceEndpoint.label`'s sample (`schema.py:120`, `binding rule 6`) is unchanged.
- Count every model set entity `label` in the held out after runs, split into verbatim (appears inside its own entity's span) and not, and report both counts beside the disagreement and engineer agreement rates (AC-16, no new API cost).

## Spends money (skip unless re measuring)

Do not run any of the below until the go ahead from AC-20 is given, computed with this formula from the assembled few shot block's actual measured token count (token counting endpoint, no cost), not from an estimate:

```text
per call, cached (0003.0 calls):
  prefix_write_cost  = prefix_tokens × $4/MTok       (once per session, first call only)
  prefix_read_cost   = prefix_tokens × $0.20/MTok    (every call after the session's first)
  unit_input_cost    = unit_input_tokens × $2/MTok
  output_cost        = output_tokens × $10/MTok      (includes thinking tokens)
  call_cost          = unit_input_cost + output_cost + (prefix_write_cost if first call else prefix_read_cost)

per call, uncached (the fresh 0021 0002.3 baseline, predates the examples block):
  call_cost          = unit_input_tokens × $2/MTok + output_tokens × $10/MTok

total = sum(call_cost) across every call in the manifest below

stop threshold: if total > $15, stop and re-confirm before running anything
```

**Output token proxy.** Only `artifacts/runs/0001/binding-rules/` and `artifacts/runs/0008/preamble/` (experiment 0004's own six calls) carry real per call token usage; every other committed run, including the original 24 call type coverage set, predates the artifact storage upgrade (spec 0001) and has no usage field at all. So the one real anchor for every call below is experiment 0004: **94,264 output tokens over 6 calls, about 15,711 tokens/call on average**, cross checked against the coverage set's own char count based estimate ($0.1268/call for the 21 ordinary units, $0.2198/call for the three densely enumerated `## Feature design` calls). Experiment 0004's own calibration note says a densely enumerated unit (a numbered list of constraints, a scope row, a `## Feature design` section with 13 bold sub labels) runs output heavier than its character count alone predicts (there, 9.5% over a char based estimate); carry that as a wider margin on the estimate below, not a bigger point figure, for `0013` and `Profile entry`, both densely enumerated.

| Run | Calls | Cached? | Output tokens used in the estimate |
|---|---|---|---|
| `0021 ## Requirements`, fresh `0002.3` baseline | 3 | No | 15,711/call (experiment 0004 average); replace with the real measured figure once this run itself completes |
| `0021 ## Requirements`, after (new prompt) | 3 | Yes | This unit's own fresh baseline output tokens, once measured |
| `0013 ## Feature design`, before and after | 3 + 3 | Before: no · After: yes | 15,711/call, with a wider margin (densely enumerated, 13 bold sub labels) |
| `Profile entry` scope row, before and after | 3 + 3 | Before: no · After: yes | 15,711/call, with a wider margin (densely enumerated, a scope row) |
| Type coverage set, `PROMPT_VERSION 0003.0` | 24 | Yes | 15,711/call, except the three `## Feature design` calls, which carry the wider margin |

18 calls before the type coverage set, 42 total. Confirm this count has not changed (a different unit substituted, a group added or dropped) before running; if it has, recompute. The conditional AC-2 test (AC-17), if triggered, is a separate cost estimate brought fresh at that point, not folded into this total in advance.

For each `0003.0` session: confirm the second call shows `cache_read_input_tokens` greater than zero, verifying the 1 hour breakpoint actually hit (AC-19), before trusting the cached cost estimate for the remaining calls in that session. The fresh `0021` baseline predates the examples block and is never expected to show a cache hit.

## Acceptance criteria coverage

| AC | How verified |
|---|---|
| AC-1 to AC-5 | Unit tests over the pre check and the clearing rule, no API |
| AC-6 to AC-11 | Inspection of the assembled prompt content plus the example validation test |
| AC-12 | Rebuild from committed `0002.3` artifacts, no API, see above |
| AC-13 | `git log`/`git status` on `artifacts/superseded/` after the fresh baseline run; confirm it is not run a second time as "group A before" |
| AC-14, AC-15 | The held out before/after report, entity and relationship columns, per group |
| AC-16 | The engineer's ruling on each after run's fixed ~10 item sample, reported beside the disagreement rate |
| AC-17 | Group B's after run entity spread computed against 2; the experiment README states the resulting decision either way |
| AC-18 | The re run type coverage set, recorded as a new experiment |
| AC-19 | `cache_read_input_tokens` on the second call of each `0003.0` session |
| AC-20 | The measured token count and computed cost (the formula above), confirmed before the first paid call |
