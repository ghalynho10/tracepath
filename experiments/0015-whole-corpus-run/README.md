# 0015 · Whole corpus run: what feature 9 cost, and what the eval says after it

**Date**: 2026-10-19
**Feeds**: feature 9 (whole corpus) and the v1 finish line in `docs/scope/scope.md`
**Status**: run 2026-10-19; v1 finishes under the fallback recorded 2026-10-19, before this run

## Question

Feature 9 extracts the whole corpus again, on one model and one prompt version. Three
things are recorded here: what the run cost against its estimate, how the held rows of
the re extracted units changed, and how the five eval questions read after it, under
both readings of the v1 finish line.

## Configuration

- Corpus: JobHunt at `2e40bcf`.
- Extraction: `claude-sonnet-5-5`, prompt `0003.1`, effort `medium`, three runs per unit.
- Run artifacts: `artifacts/runs/` at `2c3456c`, 240 units. The 12 units the scope leaves
  out (feature 9, decided 2026-10-18) are not among them.
- The 26 units first extracted on `claude-sonnet-5` sit in
  `artifacts/superseded/2026-10-18-claude-sonnet-5/` with a `NOTE.md`. The three units
  already on `claude-sonnet-5-5` (`0009`, `0013` and `0015` `## Requirements`) were kept.
- Eval: `tracepath eval` with both defaults on (narrow hold rule, held view), over
  `eval/linked-records-research.json`. `eval/held-out.json` is never opened.

## Cost

**$30.33 over 719 calls**, against an estimate of **$31.80 central** given before the go
ahead. Counted from the run files themselves: every attempt file on `claude-sonnet-5-5`
extracted on 2026-10-19, in `artifacts/runs/` and in the two `*-before-fix` folders of
the superseded set, priced at the rates in `src/tracepath/extract/cost.py`. The count
takes in settled runs and failed attempts alike, since each was a paid call.

## Held rows on the re extracted units

`data/before.json` is each unit's review queue rows under the 29 unit corpus, before the
move (526 rows in all under the narrow hold default). `data/after.json` was taken partway
through the first group, when 18 of the 26 re extracted units had settled. The other 8
(`0014 ## Decision`, `0014 ## Requirements`, `0015 ## Feature design`,
`0021 ## Requirements`, the `feature-21`, `feature-33` and `feature-9` scope rows, and the
scope's `## Resolved`) have no after figure in this folder. Cross unit holds depend on
which units are present, so the two files do not describe the same surroundings.

On those 18 units:

| held rows | before | after |
|---|---|---|
| narrow hold rule on (the default) | 387 | 191 |
| narrow hold rule off | 656 | 414 |
| of the default's rows, held for `runs_disagree` | 344 | 186 |

Per unit, narrow hold rule on:

| unit | prompt before | before | after |
|---|---|---|---|
| `0001 ## Binding rules` | 0002.3 | 37 | 19 |
| `0002 ## Feature design` | 0003.1 | 98 | 45 |
| `0002 ## Requirements` | 0003.1 | 5 | 1 |
| `0003 ## Requirements` | 0003.1 | 2 | 0 |
| `0006 ## Feature design` | 0003.1 | 45 | 25 |
| `0007 ## Consequences` | 0003.1 | 55 | 27 |
| `0007 ## Feature design` | 0003.1 | 69 | 40 |
| `0007 ## Follow-up` | 0003.1 | 26 | 7 |
| `0007 ## Requirements` | 0003.1 | 10 | 2 |
| `0008 ## Preamble` | 0003.1 | 0 | 0 |
| `0008 ## Requirements` | 0003.1 | 10 | 5 |
| `0009 ## Summary` | 0003.1 | 3 | 5 |
| `0011 ## Requirements` | 0003.1 | 5 | 8 |
| `0012 ## Build plan` | 0003.1 | 0 | 0 |
| `0012 ## Consequences` | 0003.1 | 0 | 0 |
| `0012 ## Follow-up` | 0003.1 | 0 | 0 |
| `0012 ## Requirements` | 0003.1 | 1 | 3 |
| `0013 ## Feature design` | 0003.0 | 21 | 4 |

Every unit before was on `claude-sonnet-5`; every unit after is on `claude-sonnet-5-5`
with `0003.1`. So a change here mixes the model change and, for two units, the prompt
change. It does not separate them.

## Eval result

**1 of 5 under both readings, the one a proven absence.** Question 4 prints `PASS`: its
two items stay not reached. Questions 1, 2, 3 and 5 print `FAIL`. Under the second reading
(a step reached only as held also counts), question 3 reaches 3 of its 4 items, so it
still fails. That is fewer than 3 of 5, so the fallback recorded on 2026-10-19 applies: v1
is finished, and the eval is reported as it is.

Each failing question, with what `eval` printed and the cause the fallback names. The
causes come from the 2026-10-19 diagnosis made before this run; they are not diagnosed
again here.

| Q | strict | second reading | items not reached, with the printed reason | cause named by the fallback |
|---|---|---|---|---|
| 1 | FAIL, 0 of 1 | FAIL, 0 of 1 | `0003 AC-14`: `link_held` | a link the text does not state |
| 2 | FAIL, 0 of 5 | FAIL, 0 of 5 | `0014` Decision item 2: `no_link`; its second line, `0008 AC-10b`, and both lines of `0001` binding rule 6: `link_held` | a link the text does not state |
| 3 | FAIL, 1 of 4 | FAIL, 3 of 4 | `0007 AC-12` and `0007 AC-13`: held only, through `0002/AC-10 -[UNCLASSIFIED]-> 0007/AC-13`; the second line of `0007 AC-12` (line 142): `record_not_expanded` | a link ending on a whole spec rather than an item |
| 5 | FAIL, 0 of 6 | FAIL, 0 of 6 | `0007` Follow-up, both lines of the feature 21 row, `0009` Summary: `no_link`; the second line of `0007` Follow-up: `held_for_review`; `scope.md` Resolved, custom domain: see below | name resolution, feature 7 |

`data/eval-final.txt` is the run as made, on the code at `2c3456c`. Two items of question
5 cite a blank line, with their quoted text starting on the line below (`scope.md:516` and
`0009` line 17). The eval matching now accepts that one line, the same tolerance
`tests/test_corpus.py` already gives a citation. `data/eval-after-matching-fix.txt` is the
same eval after that fix, over the same graph. It differs in one line: the custom domain
item's reason reads `held_for_review` instead of `no_link`. No verdict and no count changes.

## Conclusion

The whole corpus is on one model and one prompt version, at $30.33 against a $31.80
estimate. On the 18 re extracted units measured, held rows under the default fell from
387 to 191. The eval reads 1 of 5 under both readings, the one a proven absence, so v1
finishes under the fallback, and the four failing causes above become the after v1 work.
