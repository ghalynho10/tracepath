# 0016 · Link hops: do today's links help the answers?

**Date**: 2026-10-20
**Feeds**: `ask` retrieval (spec 0009 AC-10, note of 2026-10-20); no scope row
**Status**: question, method and decision written and committed before any paid call

## Question

`tracepath ask` sends the model the search hits plus their typed link neighbours, up to
two hops out (spec 0009 AC-10). Do those links help the answers? Put plainly: on the
five tuning questions, does sending only the hits answer as many right as sending the
hits and their neighbours?

## What this measures, and when to run it again

This measures the links as they are today, before features 8 and 7: before whole spec
landings, before the unresolved names are resolved, and before the held links are
settled. It is the baseline. Run it again after either feature lands, with the same
questions, prompt and model, and compare against the numbers here.

## Method

- `ask --hops N` (added for this experiment) sets how many hops of neighbours are added
  around the hits: 0, 1 or 2, default 2. At 2 the model gets exactly what a plain `ask`
  sent before. At 0 it gets the hits only, plus any item that replaces a history hit
  (AC-14b adds those at every hop count, since they are not hops).
- For each question N = 1 to 5 of `eval/linked-records-research.json`, run
  `ask --eval N --hops 2 --ceiling 0.25`, then `ask --eval N --hops 0 --ceiling 0.25`.
  Ten paid calls in all, stopping if the running billed total passes $0.60.
- Prompt `ask-2`, model `claude-sonnet-5-5`, corpus `2e40bcf`, the graph as loaded by a
  plain `tracepath load` (held view on, narrow hold on, code pass off).
- `eval/held-out.json` is never run or opened.
- Each call's record lands in `artifacts/asks/` and carries its `hops` value.
- The engineer marks each answer; this file does not judge them.

## Decision, written before the run

- If hops 0 answers as many questions right as hops 2, the links do not help answering
  on these questions, and dropping hop 2 is worth considering.
- If hops 0 does worse, keep the links.

## Configuration

<!-- filled after the run -->

## Items sent, per question

<!-- filled after the run -->

## Cited items, by hop

<!-- filled after the run -->

## Cost

<!-- filled after the run -->

## Marks

_Left for the engineer. One line per question and hop count: right, partly, or wrong,
with a reason._

| question | hops 2 | hops 0 |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

## Conclusion

_Left until the marks are in._
