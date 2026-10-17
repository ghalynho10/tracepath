# 0013 · Held item error analysis: what is behind each hold reason?

**Date started**: 2026-10-15
**Feeds**: feature 11, before its decision rule is written
**Status**: packet drawn 2026-10-15, ruled and scored 2026-10-17; the notes await the engineer's sorting

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

`score_held_sample.py` (no API call) writes `data/held-result.json`. It reads the
committed packet and arm file, and refuses unless the arm file hashes to the committed
`held-arms.sha256`, the commit adding the arm file comes after the packet's last
commit, and every item carries exactly one readable mark.

`tests/test_held_sample.py` covers the grouping, the exclusions, the wording, the
ends, the packet's blindness, the arm file and the refusal to draw twice, on crafted
runs; and the scorer's three refusals, on packets and git repos built in the test.

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
- An end shown `not resolved` does not rule out group e. A group e link's waiting end
  always matches a known entity, but its other end need not: after the exclusions,
  38 of group e's 179 links show one end `not resolved`.
- Rulings used the ruling guide's test throughout.
- H07's note records input from the JobHunt author.

## Result

Scored 2026-10-17 by `score_held_sample.py` (no API call) into `data/held-result.json`,
from the ruled packet (`7b2ebe8`) and the arm file committed after it (`6e0f137`),
whose hash matches the one committed before any ruling (`cb75e5c`).

4 items per group show kinds of failure, not rates. There is no pass or fail. Each
note and "should have been" below is copied verbatim from the packet; the engineer
sorts the notes afterwards.

| Group | Drawn | Agree | Disagree | Unsure |
|---|---|---|---|---|
| a | 4 | 2 | 2 | 0 |
| b | 4 | 3 | 1 | 0 |
| c | 4 | 1 | 3 | 0 |
| d | 4 | 4 | 0 | 0 |
| e | 4 | 4 | 0 | 0 |

#### Group a

- `H01` · entity · Consequence · `claude-sonnet-5` · disagree
  - note: "That defers to the app shell feature" describes the first sentence, not its own claim; "because ..." is rationale. Type Consequence is right.
  - should have been: span: "The entry page at `/` still shows a sign in invitation to a signed in visitor."; rejected: "That defers to the app shell feature, because options that fix it require `/` to read the session, which contradicts spec 0006's accepted security model (...) and its **AC-4**."
- `H06` · entity · FollowUp · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H07` · entity · Consequence · `claude-sonnet-5` · disagree
  - note: guide test used. Sentence 2 explains why sentence 1 holds: removing it loses backing, not a condition. The prompt (client.py:75-78) keeps clauses carrying a checkable fact in the span, so guide and prompt diverge here. Per JobHunt author: sentence 1 follows from Supabase pricing (type question); sentence 3 is a deferred claim with a trigger (separate item). Type Consequence is right.
  - should have been: span: "**Session forced logout was never an option to weigh.**"; rejected: "Both projects report \"Configuring user sessions is only available on the Pro Plan and above\"."
- `H12` · entity · Constraint · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_

#### Group b

- `H02` · entity · Consequence · `claude-sonnet-5` · disagree
  - note: a prediction: not checkable when written, checkable later, and nothing scheduled the later check. Not a FollowUp: it names no owed action. No type covers this. Passes the three question test. Leaving the parenthesis out is right (nothing disappears).
  - should have been: type unclassified
- `H03` · link · superseded-by · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H04` · link · unclassified · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H18` · link · superseded-by · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_

#### Group c

- `H09` · entity · Constraint · `claude-sonnet-5` · disagree
  - note: three conditions that can fail independently (idempotence can fail while the rest holds). Sentence 2 is rationale in its entirety, including "Production carries no fake users and no scaffold row" and the evaluation "which is correct".
  - should have been: split into: (a) "**The `scaffold_check` fixture and its two seeded users** stay in `supabase/seed.sql`", Constraint; (b) "made idempotent", Constraint; (c) "the migration workflow applies that file to the **development project only**, never production", Constraint; rejected: "Production carries no fake users and no scaffold row, which is correct: production has no sign in path at all until feature 7, so the thread is proved on a preview against the development project."
- `H16` · link · unclassified · `claude-sonnet-5` · disagree
  - note: a dependency the text states ("which needs feature 21's privacy policy and terms served from an authorized domain"), so blocked-by, not unclassified.
  - should have been: type blocked-by; to: feature-21 (the scope row), not "feature 21's privacy policy and terms"
- `H17` · entity · FollowUp · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H20` · entity · unclassified · `claude-sonnet-5` · disagree
  - note: part of the paragraph "Why the grant is load bearing rather than tidy up", a reason; also reads as a pointer to build plan tasks 10 and 11 (a claim about the spec's own content).
  - should have been: not an item; rejected span of the grant item at line 101 ("**One explicit `grant select` to `service_role`** ...")

#### Group d

- `H05` · entity · Feature · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H13` · entity · AcceptanceCriterion · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H14` · entity · AcceptanceCriterion · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H15` · entity · AcceptanceCriterion · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_

#### Group e

- `H08` · link · unclassified · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H10` · link · verifies · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H11` · link · unclassified · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_
- `H19` · link · unclassified · `claude-sonnet-5` · agree
  - note: _(blank)_
  - should have been: _(blank)_

## Kinds of failure (sorted by the engineer after scoring)

- A reason or description kept inside the item: H01, H07
- Made an item from a sentence that isn't one: H02 (a prediction), H20 (a reason or a pointer)
- Separate conditions kept as one item: H09
- A stated dependency typed unclassified instead of blocked-by, with the wrong end: H16

## Addendum

H02, reconsidered 2026-10-17 while grouping the failures, after the group table had been shared: re reading the source, the sentence is not an item rather than an unclassified one. The mark stays disagree, so the result table does not change. The committed packet keeps the original ruling.
