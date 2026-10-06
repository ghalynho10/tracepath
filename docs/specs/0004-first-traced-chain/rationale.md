# 0004. First traced chain: rationale

## Context

Feature 5 is the walking skeleton. Every stage already exists as a pure function or a tested module, but nothing joins them: the command line has only `status` and `review-queue`, no command extracts, none loads the graph, none walks it. The first thread through all four stages (extract, resolve, store, traverse) has to be real, because feature 6 will run all five eval questions on top of it and every later slice is measured by that.

Three things make a careless version of this feature worthless. First, one question is one data point, so a walk tuned until that question passes proves nothing about the next one. Second, extraction costs real money and has just been through two defects (PRs #15 and #16) that mock tests could not exercise, so the first paid call is also a test of those paths. Third, the graph mixes prompt versions, so a failing chain cannot be pinned on the walk or on an old prompt section unless each step says where it came from.

Scope row 5 fixes the shape: take a few hand picked records, match them by explicit identifiers only, store them, walk a chain, print the answer with each link citing its record. Done when one eval question whose answer spans three records returns that chain, each link cites its source record, and running it again gives the same chain.

## Requirements weighed

Each requirement in the feature 5 brief (`docs/session-notes.md`), with what this spec did with it.

| Requirement | Verdict | What this spec does |
|---|---|---|
| Every section the chain needs is extracted with the current prompt, with a measured estimate first | Keep | All four of question 3's sections have no run today. `extract --dry-run` measures, `--ceiling` caps, the engineer approves before the paid step (build plan 9). Prompt `0003.1` is current (`PROMPT_VERSION`). |
| Load the chain's records plus others not on the chain, so the walk has to choose | Adjust | The 14 committed units load with the four new ones, so others are present. But checked in design: of 85 resolved links, none touches 0002 or 0007, so no other record is reachable from this chain and the walk chooses only among sibling items inside the four sections. The spec does not buy extra extraction to plant a decoy. It states the fact in the result (AC-40) and says a pass does not show choosing between records. |
| No prompt change to make this question pass | Keep | AC-47 and the locked list in `## Held out discipline`. |
| The walk is general, never a hard coded path | Keep | AC-21 to AC-26, tested on a fixture that is not an eval chain (AC-32, AC-33); the walk never reads `eval/` (AC-31). |
| Record the prompt version of every step | Keep, needs a change | Entities already carry `prompt_version`. Relationships did not, so AC-16 stamps them. Records say "code, no model". AC-30 reports whether the model made steps share one version. |
| Consider a rebuild manifest | Keep, kept small | One derived, deterministic file, `artifacts/graph-build.json` (AC-17a to AC-17c, AC-18). It lists run files and prompt versions per unit and the review log count. It is not stored in the graph. |
| The first extraction command catches `ExampleError` | Keep | AC-3, with no call made. |
| The command calls `ensure_attempt_unwritten()` before every paid call | Keep, widened | AC-4 checks attempt 1 of every run of every unit before the first call, so a collision stops the whole command before any spend. AC-5 covers each retry. |
| Pick the question with held out discipline | Decided by the engineer | Question 3. See below. |

## Decisions the engineer made in this design (2026-10-05)

- **Question and the word "record"**: question 3, "record" kept as a Record node, so the scope Done when is reworded to "two or more" by `/scope` (AC-1, AC-2a, AC-2b). Counts under each reading, verified against the eval file and spec 0002:13:

| Question | Records (nodes) | Source files | Cited passages |
|---|---|---|---|
| 1 | 2 (0008, 0003), 3 with the 0007 corroboration | 2 (3) | 2 (3) |
| 2 | 4 (0011, 0014, 0008, 0001) | 4 | 4 entries, 6 lines |
| 3 | 2 (0002, 0007) | 2 | 4 entries, 5 lines |
| 4 | none | none | none |
| 5 | 4 (0007, feature 21 row, scope document, 0009) | 3 | 5 entries |

  No question spans exactly three Records. Question 3 was kept because it has no overlap with a worked example, which matters more here than the count.
- **Supersession**: show the stored `struck` flag, nothing more (AC-27). Current versus history is feature 8's Done when and inherits its recorded merge risk.
- **Record nodes**: the walk stops at a Record and says so (AC-24). It goes only where an explicit identifier points, and every printed step is one a reader can check by eye.
- **Pass rule**: spans two or more Records, written as separate criteria, with every expected item listed as reached or not reached and a reason for each miss (AC-34 to AC-41, with the cross check's fixes in AC-50 to AC-54).

## Options considered

### Option 1: A general breadth first walk over typed links, locked rules, question 3

Start from one canonical id, follow every typed link both ways to 3 hops, stop at Records and Unresolved nodes, print each step with its citation and prompt version. The walk is a pure function over an immutable slice read from Neo4j. A separate report step compares the printed chain to the eval file.

**Pros**:
- General by construction: nothing in it names a question, a record or a link type.
- Pure, so the fixture test needs no database and the integration test checks only the read.
- Deterministic with a fixed neighbour order, which makes "run it again, same chain" a byte comparison.
- Fits the stack rule: functional core, imperative shell, hand written Cypher, no new dependency.

**Cons**:
- Returns a neighbourhood, not a ranked chain, so noise steps appear. AC-39 counts them.
- Because Records are terminal, it cannot reach an item that no explicit link names (AC-12 and key invariant 1 of spec 0007 in question 3).

### Option 2: One Cypher variable length path query per question

Let Neo4j find paths between a start and an expected end with `MATCH p = (a)-[*..3]-(b)`.

**Pros**:
- Very little code.
- Shortest path is built in.

**Cons**:
- It needs the end item, which means reading the expected chain before the walk. That breaks the held out rule.
- The walk's choices live in a query string and cannot be unit tested without a database.
- Path ordering is not fixed by the query, which puts "same chain on rerun" at risk.

### Option 3: Expand Records into their entities, or follow `PART_OF`

When the walk reaches a Record, add its entities.

**Pros**:
- Reaches every extracted item of a reached record, including spec 0007's AC-12.

**Cons**:
- Two sections of spec 0007 hold dozens of entities, so output is mostly noise and the walk cannot tell which matter.
- Reaching an item because it sits in a reached record is a guess, which a visible chain cannot justify. Rejected by the engineer.

### Option 4: Pick a different question

Use question 5 (fits "three" on any reading but shares the feature 21 row with a worked example) or question 2 (four Records, demonstrated by `examples/0008-preamble.md`), or question 1 (cheapest, shares record 0008).

**Pros**:
- Question 5 or 2 satisfies the Done when without a reword.

**Cons**:
- A pass on 2 or 5 is weaker evidence, because the prompt was shown their links. Question 5's first entry also has no `spec NNNN AC-N` form to start from.
- Question 1 spans two Records too.

## Rationale

The held out problem decides the shape. The walk must be general and judged by rules written before the data, and the only way to make that real is to lock the rules, fix the start item by a rule and not by outcome, keep the walk blind to the expected chain, and test it on a graph that is not an eval chain. Option 1 does all four. Option 2 breaks the third, and Option 3 trades a visible chain for noise.

Question 3 was chosen over 2 and 5 because the prompt has never seen its text, so a pass says something about the mechanism. The cost is the Done when's wording, which the engineer decided to reword and not to bend the question choice around.

The walk's stop at Records is the honest consequence of "match by explicit identifiers only". It predicts a partial chain for question 3 (three of five expected items), which the spec states before the run. A partial chain with named reasons is a better first result than a full one that came from a rule written after the fact, and it hands feature 8 and feature 7 concrete evidence.

The three new commands share one reason for being thin: the pipeline stages are already pure and tested, so the shell only needs to connect them, catch typed failures into exit 1, and keep spending behind a ceiling.

## Evidence

### What the committed graph holds (checked 2026-10-05, no API call, no Neo4j)

Rebuilt from `artifacts/runs/` through `committed_units()`, `records_for_units()` and `resolve_accepted()`:

- 14 units, 12 Records. Prompt versions: one unit at `0002.3` (`0001 Binding rules`), two at `0003.0` (`0013 Feature design`, `feature-9`), eleven at `0003.1`.
- 85 resolved links: `satisfies` 39, `verifies` 34, `unclassified` 8, `amended-by` 2, `blocked-by` 1, `superseded-by` 1. 53 Unresolved nodes. 5 held links.
- No link touches 0002 or 0007, either end. So no other record can be entered from question 3's chain today.
- 33 of 34 `verifies` and 33 of 39 `satisfies` links end at an Unresolved node. Their references are well formed (`record` and `id` both set, for example `0006` and `AC-7`) but the target section was never extracted, so there is no entity to land on. This is why a chain's sections must all be extracted: question 3's struck scenario "verifies AC-10", which can only join `0002/AC-10` if `0002 ## Requirements` is extracted and accepted.
- References written as "feature 28" or "feature 10" stay Unresolved for another reason: the resolver matches canonical ids and ignores a Record's aliases (feature 7).

### Question 3's sections (checked against the unit splitter)

| Section | Holds | Unit start line | `user_prompt` chars |
|---|---|---|---|
| `0002 ## Requirements` | AC-10 (index.md:31) | 11 | 4,970 |
| `0002 ## Feature design` | the struck scenario (index.md:232) | 53 | 23,702 |
| `0007 ## Requirements` | AC-12, AC-13 (index.md:35, 36) | 10 | 8,512 |
| `0007 ## Feature design` | key invariant 1 (index.md:142) | 57 | 29,024 |

Twelve calls at three runs each, and at most twenty four if every run is retried once.

### Indicative cost, not yet the measured estimate

This is arithmetic from measured figures, with input tokens inferred from characters. `extract --dry-run` replaces the inferred input with the count endpoint's figure (AC-6), and the engineer approves that figure, not this one.

- **Input**: the 0003.1 cached prefix is 57,494 tokens (experiment 0008 README). Uncached input per call is inferred at about 2.8 characters per token, from `0012 Requirements` (4,462 chars, 1,657 tokens in `cost-estimate.json`) and `0014 Requirements` (10,725 chars, 3,614 tokens, experiment 0006): about 1,800 (`0002 Requirements`), 8,500 (`0002 Feature design`), 3,050 (`0007 Requirements`) and 10,400 (`0007 Feature design`).
- **Output, central**: priced from the unseen unit figures, as experiment 0008's calibration note says to. Requirements units at 27,384 per call (`0021 ## Requirements`), Feature design units at 26,721 (`0006 ## Feature design`), both from experiment 0008. That note records that example units ran far under estimate and unseen units ran near it, and that estimates built from `0003.x` runs of other units were 10 to 15 times off in the other direction before. `0002 Requirements` is small, so its central figure is probably high.
- **Output, wider**: 39,234, the heaviest measured call (experiment 0005, `0021` run 2).
- **Rates** per million tokens: 2.00 input, 10.00 output, 4.00 one hour cache write, 0.20 cache read.

| Call | Uncached input | Output (central) | Cost per call (central) |
|---|---|---|---|
| `0002 Requirements` | 1,800 | 27,384 | $0.2889 |
| `0007 Requirements` | 3,050 | 27,384 | $0.2914 |
| `0002 Feature design` | 8,500 | 26,721 | $0.2957 |
| `0007 Feature design` | 10,400 | 26,721 | $0.2995 |

Each includes $0.0115 for reading the cached prefix. One pass over the four units is $1.1755, three passes $3.53, plus about $0.22 once for the first cache write instead of a read: **about $3.75 for 12 calls**. The retry is per run, not per unit (`run_with_retry` is called once per run), so the worst case is every one of the 12 runs retried once, which is 24 calls: about $7.27 central, or about **$10.20 at the heaviest output** (39,234 on every call: 6 passes at $1.6627 plus the write). The same 12 calls without a retry at the heaviest output are about $5.21. An earlier draft of this table said 16 calls, which assumed one retry per unit and was wrong. The cache lasts one hour; if the run goes past it, one more write (about $0.23) applies.

The estimate uses standard interactive rates. The extract command calls the interactive streaming API, not the Batch API that spec 0001's storage row assigns to corpus extraction, because no batch path is built (AC-49). The command checks before every call that the running total plus one flat failure figure ($0.4144) stays under the ceiling (AC-9), so an overshoot is at most one call.

Thinking tokens are inside the billed output figures above (they are what `output_tokens` counts), so the estimate counts them. A failed attempt is priced at the flat $0.4144, not its recorded tokens, because two of experiment 0008's failed attempts recorded 2 and 5 output tokens against about 20,000 characters of raw response.

### Why a Record stop is expected to cost items

Spec 0002 AC-5 (the struck range pre check) marks AC-10's struck text. AC-10's unstruck note reads "SUPERSEDED 2026-08-30 by spec [0007] ... now the session mint's guarantee (spec 0007 **AC-13**)" (`0002` index.md:31), which is a reference with `record: 0007`. Spec 0007's AC-12 and key invariant 1 are named by no explicit identifier anywhere in the chain, so the walk has no link to follow to them. The prediction in `## Held out discipline` records this before the run.

## References

**Project sources**:
- `docs/specs/0002-data-model/index.md:13` (what a Record is), AC-7, AC-9, AC-11c, AC-13
- `docs/specs/0001-stack-and-architecture/index.md`, the artifact storage row (single retry, append only artifacts, null usage)
- `docs/specs/0003-extraction-stability-heterogeneous-units/index.md` (prompt `0003.1`, per unit provenance)
- `experiments/0008-type-coverage-rerun/README.md`, calibration note, `cost-estimate.json`, `measure_coverage.py`
- `eval/linked-records-research.json`, question 3 (`superseded_criterion`)
- `docs/session-notes.md`, the feature 5 brief and the mixed prompt version rule
- `docs/reflexes.md` (stop before spend, stop by structure)

**Practices & standards**:
- Hold out a test from tuning, and fix the pass rule before seeing the result.
- Functional core, imperative shell.
