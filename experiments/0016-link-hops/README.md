# 0016 · Link hops: do today's links help the answers?

**Date**: 2026-10-20
**Feeds**: `ask` retrieval (spec 0009 AC-10, note of 2026-10-20); no scope row
**Status**: run 2026-10-20; question, method and decision committed before any paid call (`0cc044d`); marks owed by the engineer

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

- Code: `--hops` added in `3792ab0`; this file's question, method and decision in
  `0cc044d`, both before the first call.
- Graph: rebuilt by a plain `tracepath load` after the test suite, from the 240 units of
  `artifacts/runs/` (all `claude-sonnet-5-5`, prompt `0003.1`). Held view on, narrow
  hold on, code pass off, corpus `2e40bcf`.
- Ask: model `claude-sonnet-5-5`, effort `medium`, prompt `ask-2`, `--ceiling 0.25` per
  call. All ten calls settled.
- Records, committed in `8b8b837`, all under `artifacts/asks/`:

| question | hops 2 | hops 0 |
|---|---|---|
| 1 | `2026-10-20T17-36-09Z-eval-linked-records-research-q1.json` | `2026-10-20T17-36-15Z-eval-linked-records-research-q1.json` |
| 2 | `2026-10-20T17-36-22Z-eval-linked-records-research-q2.json` | `2026-10-20T17-36-30Z-eval-linked-records-research-q2.json` |
| 3 | `2026-10-20T17-36-38Z-eval-linked-records-research-q3.json` | `2026-10-20T17-36-43Z-eval-linked-records-research-q3.json` |
| 4 | `2026-10-20T17-36-48Z-eval-linked-records-research-q4.json` | `2026-10-20T17-36-54Z-eval-linked-records-research-q4.json` |
| 5 | `2026-10-20T17-37-02Z-eval-linked-records-research-q5.json` | `2026-10-20T17-37-08Z-eval-linked-records-research-q5.json` |

## Items sent, per question

Counted from each record's `items` by their `hop`. Every question has 16 hits, so the
hits are the same at both hop counts.

| question | hops 2: hits / hop 1 / hop 2 / sent / cut | hops 0: hits / other / sent | verdict, hops 2 | verdict, hops 0 |
|---|---|---|---|---|
| 1 | 16 / 21 / 47 / 84 / 0 | 16 / 0 / 16 | answered | answered |
| 2 | 16 / 37 / 37 / 90 / 19 | 16 / 0 / 16 | answered | answered |
| 3 | 16 / 7 / 14 / 37 / 0 | 16 / 4 / 20 | answered | answered |
| 4 | 16 / 37 / 37 / 90 / 38 | 16 / 0 / 16 | no_documented_link | no_documented_link |
| 5 | 16 / 20 / 23 / 59 / 0 | 16 / 0 / 16 | answered | answered |

The verdict is the model's own word (spec 0009), not a mark.

At hops 0, question 3's four other items are not link neighbours. They came in as
replacements (AC-14b): a history hit brings in what replaces it, and those can carry a
replacement of their own, so they sit at hop 1 and hop 2 in the record. They are
`0007` (record), `0006/AC-7` (itself history), `0007/AC-16` and
`0007#consequences:21` (held). The `Items sent:` line counts them as neighbours, as it
always has.

## Cited items, by hop

The distinct ids each answer cites, grouped by the hop the item was sent at. No
citation was rejected and no claim was marked inferred in any of the ten.

| question | hops 2: hit / hop 1 / hop 2 | hops 0: hit |
|---|---|---|
| 1 | 5 / 0 / 0 | 4 |
| 2 | 6 / 1 / 0 | 7 |
| 3 | 4 / 1 / 0 | 4 |
| 4 | 7 / 0 / 0 | 6 |
| 5 | 5 / 0 / 0 | 4 |

Across the five hops 2 answers, 2 of 29 cited items were neighbours, both at hop 1:
`0014/AC-20` (question 2) and `0002#build-plan:7` (question 3). No hop 2 item was cited.

Ids cited at one hop count and not the other:

- Question 1: `0008#build-plan:6` at hops 2 only.
- Question 2: `0014/AC-20` (hop 1) at hops 2 only; `0014#feature-design:28` at hops 0 only.
- Question 3: `0002#build-plan:7` (hop 1) at hops 2 only.
- Question 4: `0009/AC-24` at hops 2 only.
- Question 5: `feature-21#21-terms-privacy-notices-done-alpha:1` at hops 2 only.

A citation count says what the answer leaned on. It does not say the answer is right;
that is the marks below.

## Cost

**$0.2904 over ten calls**, against an estimate of **$0.30** given before the run. The
estimate came from each call's free token count (`ask --dry-run`) plus the 402 to 791
output tokens measured on the ten earlier ask records, at the rates in
`src/tracepath/extract/cost.py` ($2.00 in, $10.00 out, per million tokens). Every
record's `cost_usd` equals its `recorded_usd`.

| question | hops 2: in / out / USD | hops 0: in / out / USD |
|---|---|---|
| 1 | 22,814 / 480 / 0.0504 | 5,024 / 461 / 0.0147 |
| 2 | 24,084 / 660 / 0.0548 | 6,751 / 776 / 0.0213 |
| 3 | 7,178 / 435 / 0.0187 | 3,882 / 326 / 0.0110 |
| 4 | 24,448 / 602 / 0.0549 | 6,823 / 655 / 0.0202 |
| 5 | 12,999 / 630 / 0.0323 | 3,344 / 546 / 0.0121 |
| all | 0.2111 | 0.0793 |

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
