# 0006. Eval runner: rationale

Read by people, and by `/architect` on an update. Not read during a build.

## Context

Spec 0004 built `trace --eval N`, which walks one question and prints a report. Spec 0005 added a held item view. Neither can run all five questions and say pass or fail, which is what scope feature 6 asks for, and which every later slice (features 7 to 13) is to be measured by.

Three questions block a plain loop:

- Question 4 has no `trace` list. Its right answer is "no documented connection", so there is nothing to reach. A runner that treats "nothing reached" as a pass would also pass when the sections were never extracted.
- Question 5's first entry is a Consequences paragraph (`spec 0007 Consequences`, line 313), not a `spec NNNN AC-N` item, so spec 0004 AC-34 refuses it. Derived ids (`0007#consequences:N`) do not exist until extraction, so a person cannot name the start in advance.
- Questions 2 and 5 draw on records that worked examples in `examples/` also draw on, so a good result may come from the prompt having seen the text. Verified by reading the examples: `examples/0008-preamble.md` carries `0008/AC-10b`, `0008/AC-14`, `0008/AC-7` and spec 0001's binding rule 6 as link endpoints, and `examples/feature-21-scope-row.md` is the verbatim input of the feature 21 row that question 5's third entry cites (`scope.md` line 179).

The scope row also sets a separate need: one or two held out questions, written without sight of `artifacts/`, `experiments/` or the review queue, kept sealed until features 13 and 11 have committed their choices. The scope row's constraint is that the five originals stay as brought in.

The eval stays small by standing rule: a handful of questions and one script, never a harness or a dashboard.

Two facts about the corpus shaped the choices. Of the units the five questions cite, eight need extracting for scoring (listed in index.md). And lines in a spec hold several entities: `0002/AC-10` and the Consequence `0002#requirements:6` both sit at file line 31 in the committed runs, so "the entity at that line" is not unique.

## Options considered

### How question 4 starts and passes

**Option A (chosen): start at 0008/AC-14 from the first `checked` entry, pass on proven absence.** The start comes from the eval file by a general rule. The tempting items (0007 AC-4 and AC-19) sit in the sidecar. Three outcomes, and an absence only counts when the graph holds the item.
- Pros: a pass means the graph held the tempting items and the walk missed them. An unextracted section reads `INCONCLUSIVE`.
- Cons: a new outcome (`INCONCLUSIVE`) and a sidecar entry for the one question.

**Option B: print the chain, no verdict.** Start at 0008/AC-14 and show the walk.
- Pros: smallest.
- Cons: a section never extracted prints the same as a correct "no connection", and the scope row asks for pass or fail.

**Option C: leave question 4 out until features 7 and 8.**
- Pros: smaller runner now.
- Cons: the absence case is the one most worth testing, and it is named in the scope row.

### How question 5 starts

**Option A (chosen): the entity at the first entry's file and line, the lowest canonical id on a tie.** A new rule used only where AC-34 would refuse, fixed before extraction.
- Pros: no walk change, repeatable, not chosen by which start gives the best chain.
- Cons: the tie break is arbitrary, so the start may differ from the one a person would pick.

**Option B: every entity at the line, one walk each, union.**
- Pros: no tie break; hides a bad single pick.
- Cons: several chains per question, hop counts that belong to different starts, and a walk that is no longer one walk from one start.

**Option C: hand pick the start after extraction.**
- Pros: the best start.
- Cons: breaks spec 0004's locked start rule, since the pick is made after seeing the graph.

### What counts as a pass for the questions with a `trace` list

**Option A (chosen): every expected item reached by the clean walk.** The start is marked as the start, left out of the `K of M` count, because the question names it (reaching it shows only that it was extracted and accepted).
- Pros: simple and strict; a held only item is never a pass (spec 0005 condition 4).
- Cons: question 3 prints `FAIL` until its gaps close.

**Option B: an item in another record is reached.**
- Pros: closer to what spec 0004 AC-41 tested.
- Cons: a chain missing most of its items can pass.

**Option C: no verdict.**
- Pros: smallest.
- Cons: not what scope feature 6 asks for.

### Where the per question data lives

**Option A (chosen): a sidecar `eval/runner.json`.** Hand written, committed before any run.
- Pros: the rules in code stay general and name no question; the eval file stays as brought in.
- Cons: one more file, and its flags can be wrong.

**Option B: constants in `report.py`.** Cons: puts question numbers in code spec 0004 says names none.

**Option C: compute everything from the eval file.** Cons: parsing the free text of `checked` is fragile, and it cannot hold the evidence flags.

### Isolation for the fresh writing session

**Option A (chosen): a scratch directory copy.** Only `corpus/jobhunt/docs`, the eval file and the brief exist there.
- Pros: isolation by what is on disk, not by an instruction.
- Cons: a few minutes of setup.

**Option B: a subagent in this repo told not to look.** Cons: `artifacts/` and `experiments/` are readable, so isolation rests on an instruction.

**Option C: the engineer writes them.** Cons: not the fresh session the scope row sets, and the writer knows the repo.

### How the writer learns what is off limits

**Option A (chosen): a record level list plus a mechanical check.** Only record ids go to the writer. A test rejects a cited line in an excluded record, and another rejects a record that a worked example draws from.
- Pros: a small leak (which records are extracted, no section, no content), simple, and a check that survives feature 13 adding examples.
- Cons: coarse, so seven of twenty one spec records are left eligible.

**Option B: a section level list.** Cons: hands the writer a map of what is extracted.

**Option C: no list, check after.** Cons: the rejection itself tells the writer what is extracted, and it may take several rewrites.

### The guard on the held out file

**Option A (chosen): an explicit `--release-held-out` flag, with the file marking itself `held_out`.** No source file names it.
- Pros: a deliberate act before the sealed questions run, and no filename in code.
- Cons: stops a slip, not a person who passes the flag.

**Option B: the separate file only.** Cons: nothing prompts a pause before pointing at it.

**Option C: read feature status from the scope.** Cons: the runner would parse a planning document, and the parse is hard to keep correct.

### The evidence flags

**Option A (chosen): sidecar levels plus a staleness test on a digest of the contents of every file in `examples/`.** A changed byte in an example, not only a changed file name, forces a re-check.
- Pros: cheap, visible in the terminal, and feature 13 cannot edit an example without being told.
- Cons: hand written, and the digest says only that something changed.

**Option B: compute from `examples/`.** Cons: parsing code in a runner meant to stay small.

**Option C: a note in the result record only.** Cons: easy to read past in the terminal.

## Rationale

The runner is a thin shell over code that already exists, because spec 0004 and spec 0005 locked the rules and the user's constraint is to reuse them unchanged. Everything new is either a rule for where AC-34 would refuse (question 5, question 4's start), a verdict built from findings the report already makes, or data that names a question. That keeps the walk, the matching rule and the reason codes untouched, so experiments 0009 and 0010 stay valid as recorded, and the reproduction of question 3 at `36a6bc5` (AC-3) is a direct test that nothing drifted.

Strict pass (every item reached) was chosen over a cross record test because the runner's job is to measure later slices, and a looser rule hides the gaps those slices exist to close. The start item is left out of the `K of M` count for a reason the engineer gave: the question hands it over, so reaching it proves extraction and acceptance, not that the walk found anything.

Question 4's three outcomes come from one force: spec 0004 AC-38 gives `no_link` when nothing explains a miss, and that is also what an item with no entity at its line would give if the unit was extracted but the model skipped it. Without the `accepted_here` check a missing entity would pass as a correct absence. `INCONCLUSIVE` is the honest word for every other case, and it is never `PASS`.

Question 5's tie break by lowest canonical id copies spec 0004's own habit (AC-26 orders by lexical id) and is the least inventive rule that is fixed before extraction. The union option was dropped because it makes hop counts mean different things.

The sidecar keeps the rules general while still naming the few facts that belong to one question. The held out design follows the scope row's constraints exactly, and each of its three guards (a scratch directory, a record level exclusion, a release flag) removes one way the questions could stop being a check: seeing the artifacts, drawing on extracted text, running early.

No prediction is locked for questions 1, 2, 4 and 5. Spec 0004 and 0005 locked one for question 3 because they were testing a mechanism on a question chosen for it. The runner is measuring, so the first results are findings. The Follow-up in index.md keeps the option open before the paid step.

## Extraction estimate (measured 2026-10-07, free endpoint only)

Source of every figure: `uv run tracepath extract <the eight units plus 0008:Feature design and 0009:Feature design> --ceiling 30 --dry-run` (ten were counted; two are left out after the cross check), which calls only the free token count endpoint. It prices at standard interactive rates (input $2.00, output $10.00, 1 hour cache write $4.00, cache read $0.20 per million), not Batch (spec 0004 AC-49). The cached prefix is 57,494 tokens as billed (experiment 0008).

The tool's central line says "not priced" for five of the ten counted units, because it holds a measured output figure only for the Requirements and Feature design unit kinds. Its wider figure uses 39,234 output tokens for every call, the heaviest measured, which overstates small sections. So the central column in index.md is built by hand from a measurement, as follows.

**Output assumption and its source.** Across the 54 settled runs in `artifacts/runs/` (18 units, 3 runs each, field `output_tokens` against `input_tokens`, the uncached input), output scaled with the section's uncached input, not with a fixed amount:

| Unit kind in the measured runs | Runs | Output per uncached input token, median | Highest |
|---|---|---|---|
| Requirements | 15 | 4.71 | 6.77 |
| Feature design | 15 | 4.96 | 6.00 |
| Consequences and Follow-up (spec 0012) | 6 | 1.51 | 1.76 |
| Preamble (spec 0008) | 3 | 1.20 | 1.21 |
| All 54 runs | 54 | 4.22 | 13.39 |

Each unit's central output per call is its uncached tokens times the median ratio of the nearest measured kind: Requirements for the three Requirements units, Consequences and Follow-up for `0007:Consequences` and `0007:Follow-up`, Preamble for `0009:Summary`, and the all runs median for `0014:Decision` and `scope:Resolved`, which match no measured kind. The first call of the command writes the cache ($0.2300), the later calls read it, as spec 0004 prices a central run.

| Unit | Uncached | Ratio used | Output per call | 3 calls |
|---|---|---|---|---|
| `0008:Requirements` | 6,787 | 4.71 | 31,998 | $1.254 |
| `0003:Requirements` | 1,567 | 4.71 | 7,388 | $0.266 |
| `0007:Consequences` | 2,403 | 1.51 | 3,639 | $0.158 |
| `0011:Requirements` | 4,096 | 4.71 | 19,311 | $0.638 |
| `0014:Decision` | 1,434 | 4.22 | 6,055 | $0.225 |
| `0007:Follow-up` | 1,605 | 1.51 | 2,431 | $0.117 |
| `scope:Resolved` | 532 | 4.22 | 2,246 | $0.105 |
| `0009:Summary` | 268 | 1.20 | 321 | $0.046 |
| **Eight units** | | | | **about $2.80** |

The first row includes the one cache write ($0.23) for the whole command.

**What this can be wrong about.** The ratios come from earlier units, and the highest measured ratio is 13.39 (a small feature row), so a prose heavy small section such as `0007:Consequences` could cost several times its figure. The reflex that an unflagged $0.40 estimate was 10 to 15 times low applies here, so the engineer is shown three figures and not one:
- **Central, about $2.8**, from the measured ratios above.
- **Tool's wider total, $30.10 for the eight** (the tool's $37.66 for ten, less $3.81 and $3.76 for the two left out): 6 calls per unit, every call writing the cache, each at 39,234 output tokens.
- **Per call bound, $0.87 to $0.89**: the most one call can cost (64,000 output tokens plus uncached input plus one cache write), which is what the ceiling guard checks before every call (spec 0004 AC-55). A ceiling must cover the expected spend plus one bound.

No call is made until the engineer gives a go and a ceiling (AC-31).
