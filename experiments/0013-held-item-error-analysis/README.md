# 0013 · Held item error analysis: what is behind each hold reason?

**Date started**: 2026-10-15
**Feeds**: feature 11, before its decision rule is written
**Status**: packet drawn 2026-10-15, awaiting the engineer's rulings

## Question

The review queue holds items for five reasons, and feature 11 will write a rule for
what to do with them. Before that rule is written: when an item is held for one reason
alone, what is actually wrong with it, if anything? The engineer reads a blind sample
and notes what is wrong; the notes are grouped afterwards.

This is error analysis, not a gate. There is no pass or fail, and no threshold set in
advance.

## Method

`prepare_held_sample.py` (no API call) reads `artifacts/review-queue.json`, checks it
against the queue the committed run files rebuild to (`committed_units()`, then
`review_rows()`) and refuses to draw if they differ. It keeps only rows with one
distinct reason name and sorts them into five groups:

| Group | Rows |
|---|---|
| a | `runs_disagree`, the signature in all three runs with differing counts |
| b | `runs_disagree`, the signature in exactly two of three runs |
| c | `runs_disagree`, the signature in exactly one of three runs |
| d | `known_trap_flag` |
| e | `endpoint_not_accepted`, one end waiting or both |

How many runs hold a signature comes from the unit's per run counts
(`entity_counts` and `relationship_counts` in `src/tracepath/extract/compare.py`),
rebuilt from the run files.

### Exclusions, and why

- **More than one distinct reason name.** A note on such an item could not be put down
  to one reason. The 32 rows naming `endpoint_not_accepted` twice, once per waiting
  end, carry one distinct name and stay in group e.
- **Eval chain passages.** An item is left out when its source line falls inside a
  passage cited by an expected chain step of `eval/linked-records-research.json`:
  an entity by its own line, a link when either local end's line does. A passage runs
  from its cited line through the lines its quote covers, for trace steps and their
  `also` passages; `corroboration` is not a chain step and question 4's `checked`
  list is free text, so neither is read. This keeps the rulings that shape feature
  11's rule off the passages the eval scores, so the eval stays a separate check of
  that rule.
- **Items experiment 0012 drew** (group d only), named by canonical id in its
  `stage-one-arms.json`. The engineer has already ruled them, and their arm file is
  committed, so they could not be ruled blind again.

### Blindness

As in 0012: the seeds come from `secrets` at draw time, one per group plus a shuffle
seed, so the groups cannot be recomputed from committed code. The 20 items are
shuffled together and numbered `H01` to `H20` after the shuffle. The packet shows only
what ruling needs:

- an entity: its span, type and source line;
- a link: its type, its direction (from, then to), and each end's span and source
  line. An end naming something outside its section shows the exact words the text
  used and the entity they match, matched as `_waiting_on()` in
  `src/tracepath/pipeline.py` matches (`{record, id}`, else `{record, label}`
  through the label index), or `not resolved` when they match none.

No group, reason, run count, model, canonical id, or whether the item or an end was
accepted, held or waiting appears in the packet. The wording shown is the earliest
run's that holds the signature.

Each item has a ruling slot (`agree` / `disagree` / `unsure`), a free `note:`, and a
`should have been:` for a disagree (the type, the direction or the ends).

### Files

- `data/held-packet.md`: the packet the engineer rules.
- `data/held-arms.sha256`: the arm file's hash, committed before any ruling.
- `data/held-arms.json`: the arm file, naming every seed, every draw and its pool, the
  exclusion counts, and per item its group, record, section, signature, per run
  counts, model and the run its wording came from. Kept uncommitted until the rulings
  are in; its hash must then match.

The script refuses to run once any of the three exists, so the sample is drawn once.
`tests/test_held_sample.py` covers the grouping, the exclusions, the wording, the
ends, the packet's blindness, the arm file and that refusal, on crafted runs.

## Configuration

No model call. Queue as of `2042871` (its last rebuild), corpus commit `2e40bcf`,
sampler committed in `18c58c7` before the draw. The queue's rows name
`claude-sonnet-5` (947) and `claude-sonnet-5-5` (43).

## Sample

Drawn 2026-10-15, 4 per group, 20 items, no shortfall.

| Group | One reason rows | Inside an eval passage | Drawn in 0012 | Population | Drawn |
|---|---|---|---|---|---|
| a | 20 | 1 | | 19 | 4 |
| b | 62 | 7 | | 55 | 4 |
| c | 174 | 21 | | 153 | 4 |
| d | 279 | 15 | 13 | 251 | 4 |
| e | 186 | 7 | | 179 | 4 |

## Known limits

- 947 of the queue's 990 rows come from `claude-sonnet-5` units, so this informs the
  kinds of failure behind each reason, not their rates on the current model.
- Group a holds only entities and group e only links, so an item's kind partly reveals
  its group.
- Only one run's wording is shown per item, the earliest run's that holds the
  signature; another run may word the same item differently.

## Result

Not yet ruled. The scoring script is written after the rulings are in.
