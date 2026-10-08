# 0006. Eval runner

**Date**: 2026-10-07
**Status**: In Progress

## Summary

This spec adds one command, `tracepath eval`, that runs every question of an eval file and prints pass, fail or inconclusive for each, with the difference shown. It reuses spec 0004's locked walk, matching and reason rules and spec 0005's held item view without changing them. It decides how question 4 (no `trace` list, the right answer is "no documented connection") and question 5 (its first entry is a paragraph, not an AC) start, how the report flags questions whose chains overlap worked examples, and how two held out questions are written, kept sealed and released. The eight sections that questions 1, 2, 4 and 5 still need are priced here from the free token count endpoint, and nothing is extracted until the engineer gives a go.

## Requirements

**User stories**:
- As the project's author and only user, I want one command that scores all five eval questions, so every later slice is measured the same way.
- As the person reading the result, I want each question's difference shown and no total or rate, so a pass is read for what it is and not averaged away.
- As the person who must trust a "no documented connection" answer, I want that question to pass only when the graph really holds the tempting items and the walk really misses them, so a section that was never extracted cannot look like a correct answer.
- As the person who will later check features 13 and 11, I want held out questions written without sight of the artifacts, sealed until those features commit, and released by a deliberate flag, so they are a check and not training data.

**Acceptance criteria** (each holds one claim):

*The command*
- **AC-1**: `tracepath eval` prints one block for every question of the eval file, in the file's order.
- **AC-2**: Each block opens with exactly the lines of spec 0004's report for that question (`report_lines()`), so the text from `Question N:` to the `Across records` line is the text `trace --eval N` prints for it.
- **AC-2b**: After a blank line, each block ends with its result line (AC-5) and then its evidence line (AC-18).
- **AC-3**: Scored with no chain (the start is not in the graph) over the run files as committed at `36a6bc5`, question 3's report lines equal the block recorded in experiment 0009's README (the fenced block from `Question 3:` to the `Across records` line). A pure test, with no Neo4j, over a temporary root made by `git archive 36a6bc5 artifacts`.
- **AC-4**: `trace START` and `trace --eval N` for a question that has a start under spec 0004 AC-34 print what they printed before, except the start marker of AC-10. `trace --eval N` also gains the start rules of AC-12 to AC-14, so questions 4 and 5 no longer exit 1 there.
- **AC-5**: A result line reads `Question N: RESULT · K of M expected items reached besides the start.` where RESULT is `PASS`, `FAIL` or `INCONCLUSIVE`.
- **AC-6**: A question with a `trace` list is `PASS` only when its start is in the clean slice and every expected item, the start's items included, is `reached` by the clean walk (spec 0005 AC-12). `K` equals `M` in a `PASS`.
- **AC-6b**: An item that is `held only` counts as not reached, so a question with one is `FAIL`.
- **AC-6c**: A question with a `trace` list and any item not reached is `FAIL`, and the report's reason for each item is the difference shown.
- **AC-7**: The output holds no total, no count of questions passed, no rate and no percentage.
- **AC-8**: `eval` exits 0 when every question reached a result, `FAIL` and `INCONCLUSIVE` included.
- **AC-8b**: A question that cannot be scored prints `Question N: UNUSABLE, ` and the reason, the later questions still run, and `eval` exits 1 after the last one.
- **AC-8c**: A typed failure of the run (`SettingsInvalid`, `GraphUnavailable`, `SliceError`, `RebuildFailed`, `RecordError`, an unreadable eval file, a malformed `eval/runner.json`) prints a message on stderr and exits 1 before any question, with no traceback. A missing `eval/runner.json` is not a failure: every question reads `not assessed`.
- **AC-8d**: `UNUSABLE` lines go to stdout, in the question's place. A cited file that cannot be read, or a cited line before the first unit of its file, makes that one question `UNUSABLE`.
- **AC-9**: `eval --with-held` over a graph with no held item exits 1 before any question, with the message `trace --with-held` gives (spec 0005 AC-26, AC-26b).
- **AC-9b**: Under `--with-held` every block uses spec 0005's report lines unchanged (AC-12 to AC-16), except that the label line (AC-15) prints once, above the first block, and not in each block.
- **AC-9c**: `eval` prints no chain. Blocks are separated by one blank line. Lines above the first block come in this order: the held out label (AC-29), the unchecked line (AC-21), the held view label.
- **AC-10**: A finding whose step is at hop 0 prints ` · the start` after `hop 0`, in both `reached` and `held only` lines.
- **AC-10b**: `K` and `M` in the result line leave out every expected item whose file and line equal the resolved start node's file and `file_line`, because the question names that item as the start. An absence question leaves out none.
- **AC-10c**: The `Start item:` line names its source: `from the first trace entry "LABEL"` (AC-34), `from the first trace entry "LABEL", the entity at FILE:LINE` (AC-12), or `from the first checked entry "WHERE"` (AC-14); when no entity holds that file and line it reads `Start item: none, no entity at FILE:LINE.` Question 3's line stays byte for byte as it is.

*How a question starts (new rules beside spec 0004 AC-34, used only where AC-34 would refuse)*
- **AC-11**: A first `trace` entry that matches `spec NNNN AC-N` still gives the start `NNNN/AC-N`, by AC-34 as written.
- **AC-12**: A first `trace` entry that does not match gives the start of an entity node whose `file` and `file_line` equal that entry's file (leading `docs/` stripped) and line, taken from the accepted entities only.
- **AC-12b**: When several accepted entity nodes share that file and line, the start is the one with the lowest canonical id, comparing the numbers inside an id as numbers (`:9` before `:10`), and the `Start item:` line says how many candidates sat on the line.
- **AC-12d**: Under `--with-held`, a held entity is a candidate only when no accepted entity holds that file and line, so the default run and the held run start at the same node whenever one accepted entity is there.
- **AC-12c**: When no entity node holds that file and line, the start is not in the graph, and spec 0004 AC-52 applies: every item prints as not reached with its AC-38 reason, and the result is `FAIL`.
- **AC-13**: The start id is resolved once per question and the clean walk starts at that same id (under `--with-held` it may be absent from the clean slice, as spec 0005 says).
- **AC-14**: A question with no `trace` list takes its start from its first `checked` entry whose `where` matches `^docs/specs/(\d{4})-[^/]+/index\.md line (\d+) \((AC-\d+[a-z]?)\)$`, giving `NNNN/AC-X`. The captured line is printed in the `Start item:` line and is not otherwise used.
- **AC-15**: A question that no rule gives a start is `UNUSABLE`, naming the question, and no start is guessed.
- **AC-15b**: A question with no `trace` list and no `absence` entry in the sidecar, a question with an `absence` entry and a `trace` list, and an absence entry in a held out file are each `UNUSABLE`, so no question can pass with no items.

*Absence questions (question 4)*
- **AC-16**: A question the sidecar lists under `absence` is an absence question: its items are those entries, its heading reads `Items that should not be reached:`, and spec 0004's matching, reason and outside link rules run on them unchanged. An item's AC token is the one the AC-34 regex finds in its sidecar `label`.
- **AC-17**: An absence question is `PASS` only when its start is in the clean slice and every item has an accepted entity at its file and line (`routed.accepted_entities`, read as `_reason()` reads them), is not reached by the clean walk, and has the reason `no_link`.
- **AC-17b**: An absence question with any item reached by the clean walk is `FAIL`, and its result line reads `Question N: FAIL · ITEM was reached at hop H, a connection the record does not document.`
- **AC-17c**: Every other absence outcome is `INCONCLUSIVE`, its result line reads `Question N: INCONCLUSIVE · absence not provable.` and one line per item follows with its cause, the first that applies in this order: start not in the clean slice, then the AC-38 reason when it is not `no_link`, then `no accepted entity at the line`, then `held only`. It is never `PASS`.
- **AC-17d**: For an absence item, `link_held` counts as a cause only when the held link's other endpoint is a node the walk visited; any other held link naming the item is ignored for that item. Spec 0004's `_reason()` is not changed for questions with a `trace` list.
- **AC-17e**: Today `INCONCLUSIVE` is the expected result for question 4, because both items are held for review. The result record says so and does not read it as a defect.

*Evidence flags*
- **AC-18**: Every question's evidence line reads `Evidence: weaker`, `Evidence: light` or `Evidence: no overlap with a worked example`, then ` · ` and its one line reason from the sidecar, or `Evidence: not assessed` when the sidecar has no entry. `weaker` means an expected item's text is the input of an example, or at least half of the expected items are link targets in an example's output. `light` means at least one expected item is a link target in an example's output. `none` means neither.
- **AC-19**: At the commit that adds `eval/runner.json`, the levels are question 1 light, question 2 weaker, question 3 none, question 4 light, question 5 weaker.
- **AC-20**: A test fails when the digest of `examples/` differs from the digest the sidecar records, and its message says to re-check the flags. The digest covers `git ls-files examples/` only, each file as its path relative to `examples/`, a NUL byte, its length, a NUL byte and its bytes, in sorted path order.
- **AC-21**: When the sidecar has an entry for the eval file and the digests differ at run time, `eval` prints `Evidence flags unchecked: examples/ has changed since they were written.` once, above the first block, and still prints the levels.

*Held out questions*
- **AC-22**: `eval/held-out.json` holds two entries in the eval file's shape, a top level `"held_out": true`, and an expected chain for each read from the corpus at `2e40bcf`.
- **AC-23**: The two entries were written by a fresh session started in a scratch directory that held only `corpus/jobhunt/docs`, the eval file, and the brief below, with reads of the tracepath repository path denied in that session's settings, and the write record holds the directory listing and the session's tool log.
- **AC-24**: A test fails when an entry of `eval/held-out.json` cites a line in a record on the brief's exclusion list.
- **AC-25**: A test fails when an entry cites a record that a file in `examples/` draws from, read from that file's first heading by `^# Worked example: (?:`?(feature-\d+|\d{4}))`, where `feature-N` stands for the scope document. A heading that does not match fails the test.
- **AC-26**: A test fails when a quoted passage of `eval/held-out.json` is not at its cited file and line in the snapshot, at exactly that line, not within one line of it as `tests/test_corpus.py` allows for the eval file. Citations point at `index.md` files and `scope.md` only.
- **AC-27**: No file under `src/` names `held-out.json`, so no command reads the file unless it is pointed at it.
- **AC-28**: `eval --eval-file F` and `trace --eval N --eval-file F`, where `F` has `"held_out": true`, and no `--release-held-out`, exit 1 naming that flag, read no graph, and print no question. The check sits in the shared eval file reader. `--release-held-out` on a file that is not held out exits 1.
- **AC-28b**: `eval/held-out.json` carries `"held_out": true` (a test).
- **AC-29**: With `--release-held-out`, the output opens with `Held out check (spec 0006): a check of the choices features 13 and 11 made, not a measurement.` and reports each question on its own, under AC-7.
- **AC-30**: `eval/held-out.json` is committed before the first commit of feature 13's spec, and no run artifact exists for any unit holding a line it cites.

*The extraction for questions 1, 2, 4 and 5*
- **AC-31**: Before any paid call, `extract --dry-run` is run over the eight units in Feature design, and the engineer gives a go and a ceiling after reading its measured figures and the output assumption with its source.
- **AC-32**: From this spec's commit to the commit holding the eight units' run files, nothing under `examples/` or `src/tracepath/extract/` changes.
- **AC-33**: The result record (`experiments/0011-eval-runner/README.md`) lists, for each of the five questions, its result, its evidence level and the reason for each item not reached.
- **AC-33b**: The result record cites commit `a8da2bc`, which locked the predictions for questions 1, 2, 4 and 5 in `experiments/0011-eval-runner/predictions.md`, and commit `9c53144`, which relocked question 5's prediction to one count, both before the first extraction commit `282b9a4`, and scores each of those four results against its prediction.
- **AC-33c**: The result record names the spec commit, the code commit, the extraction commits (the range `282b9a4` to `8fd0436`, eight commits, one per unit) and the result commit, in that order.
- **AC-34**: From the code commit to the result commit, nothing under `src/` changes. A defect found afterwards is a separate commit, and its rescoring on the same artifacts is a second, labelled result, as spec 0004 AC-47 and AC-53 set.

## Decision

**Chosen option**: Option A, one `eval` command over the existing report, with a small sidecar file for the data that names a question.

`tracepath eval` loops over the questions of one eval file and prints spec 0004's report block for each, then a result line and an evidence line. The rules stay general code. The few facts that name a question (what question 4 must not reach, how weak each question's evidence is) sit in `eval/runner.json`. Held out questions live in a separate file that marks itself `held_out`, and the runner refuses it without an explicit flag.

**Implementation skills**: `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `neo4j-driver-python-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-driver-python-skill/`)

## Rationale

Reasoning, the options, the extraction estimate and the evidence: see [rationale.md](rationale.md).

## Feature design

**Data model sketch**. No node kind, entity type or relationship type is added, and the graph is not changed. Four additions:

- **`eval/runner.json`**, hand written, committed before any run, read only by `report.py`. Keyed by eval file name, then question number:

```json
{
  "linked-records-research.json": {
    "examples_sha256": "<digest of examples/ when the flags were checked>",
    "questions": {
      "1": {"evidence": "light", "reason": "0008 AC-7 is a link target in examples/0008-preamble.md, the other two items are in no example"},
      "2": {"evidence": "weaker", "reason": "0008 AC-10b and spec 0001's binding rule 6 (3 of 6 expected items) are link targets in examples/0008-preamble.md"},
      "3": {"evidence": "none", "reason": "no expected item sits in a record an example draws on (spec 0004 AC-1)"},
      "4": {
        "evidence": "light",
        "reason": "0008 AC-14 is a link target in examples/0008-preamble.md",
        "absence": [
          {"label": "spec 0007 AC-4", "file": "specs/0007-auth-and-per-user-isolation/index.md", "line": 25},
          {"label": "spec 0007 AC-19", "file": "specs/0007-auth-and-per-user-isolation/index.md", "line": 42}
        ]
      },
      "5": {"evidence": "weaker", "reason": "the feature 21 row (scope.md line 179) is the input of examples/feature-21-scope-row.md, whose output points at spec 0009 ACs"}
    }
  }
}
```
  `evidence` is `weaker`, `light` or `none` (defined in AC-18). The file is read relative to `--root`, keyed by the eval file's basename. A missing file or entry means not assessed, and an unknown level or bad JSON exits 1 (AC-8c).
- **`eval/held-out.json`**, the eval file's shape (`entries`, each with `shape`, `question`, `trace`, `answer`) plus a top level `"held_out": true`. Written once, in a fresh session (below). Its entries are numbered by position, in its own file.
- **In memory**, frozen dataclasses: `Question` gains `start_at: tuple[str, int] | None` (the file and line a non AC start resolves from) and `absence: bool`; `Finding` gains `accepted_here: bool`; a new `Verdict` enum (`PASS`, `FAIL`, `INCONCLUSIVE`); a new `Evidence` value (level, reason).
- **The digest** of `examples/`: sha256 as AC-20 defines it.

**State transitions**: none. Each run is a single pass.

**Interface**:

| Command | Key inputs | Key outputs | Auth | Key errors |
|---|---|---|---|---|
| `tracepath eval [--eval-file F] [--with-held] [--release-held-out] [--root] [--snapshot] [--commit]` | the eval file (default `eval/linked-records-research.json`), the loaded graph, the committed run files | one block per question on stdout (AC-2, AC-2b), exit 0, or exit 1 for an unusable question or a typed failure | Neo4j settings | `EvalEntryUnusable`, `SettingsInvalid`, `GraphUnavailable`, `RebuildFailed`, `RecordError`, a held out file without `--release-held-out`, `--with-held` on a graph with no held item |

`trace --eval N` stays, with its output unchanged but for AC-10. The body both commands share (read the graph, resolve the start, walk once or twice, score) becomes one function in `cli.py`.

**The pieces** (pure core, edges at the shell, as AGENTS.md says):

| Piece | Where | Kind | Does |
|---|---|---|---|
| `question_from()` | `report.py` | pure | Gains the non AC start rule (AC-12), the `checked` start rule (AC-14) and the sidecar's absence items (AC-16). AC-34's rule stays as it is. |
| `resolve_start(question, graph)` | `report.py` | pure | Gives the start id: the AC id, or the lowest canonical id at the question's file and line (AC-12, AC-12b). `None` when none. |
| `score()` | `report.py` | pure | Gains `accepted_here` on each finding and the hop 0 marker data. Its reach and reason rules are untouched. |
| `verdict(report)` | `report.py` | pure | Gives `PASS`, `FAIL` or `INCONCLUSIVE` by AC-6 to AC-6c and AC-17 to AC-17c, and the cause of each `INCONCLUSIVE` item. |
| `result_lines(report, verdict, evidence)` | `report.py` | pure | The result line and the evidence line. |
| `read_sidecar()`, `examples_digest()` | `report.py` | edge | Read `eval/runner.json`; hash `examples/`. |
| `eval` command | `cli.py` | shell | Reads the graph once, runs each question, prints, sets the exit code. |

**Value sourcing**:

| Action | Value produced or displayed | Source |
|---|---|---|
| start | id of a first `trace` entry in AC form | spec 0004 AC-34, unchanged |
| start | id for a first entry that is not in AC form | the entity node at that entry's file and line, from the graph as read (AC-12) |
| start | id for a question with no `trace` list | the first `checked[].where` of the form `docs/specs/NNNN-<slug>/index.md line N (AC-X)`: `NNNN` from the path, `AC-X` from the parentheses (AC-14) |
| absence items | the file and line of each item that must not be reached | `eval/runner.json`, `absence` |
| the start marker | which item is the start | the expected items whose file and line equal the resolved start node's file and `file_line` (AC-10b); when the start is not in the graph there is no resolved node, so none is left out and `M` includes the start item |
| `K of M` | reached and total, besides the start | the findings, less the start's items |
| result | `PASS`, `FAIL`, `INCONCLUSIVE` | the findings only, by AC-6 to AC-6c and AC-17 to AC-17c |
| evidence line | level and reason | `eval/runner.json`; "not assessed" when absent |
| stale flags | whether `examples/` changed | the digest of `examples/` against `examples_sha256` |
| held out refusal | whether a file is held out | its top level `held_out` field, read before the graph |
| graph mode | clean or held view | the `--with-held` flag, as `trace` does |
| reproduction of experiment 0009 | question 3's recorded block | `tests/fixtures/experiment-0009-q3-report.txt`, copied verbatim from the README's fenced block |

**The held out brief.** Copied into the scratch directory as `BRIEF.md` for the fresh session. The directory holds only `corpus/jobhunt/docs` at `2e40bcf`, `eval/linked-records-research.json` (the method and the format) and this brief. The brief:

```text
Write two new eval questions in the shape of eval/linked-records-research.json.

Method (from that file). Each question is a real "why does X work this way" question
whose answer spans two or more records of the corpus. Read every quote from the file
at the line you cite, in this session, and write the expected chain from what you read.
Each entry has: shape, question, why_multiple_records, trace (each step: record, file,
line, quote), answer, confidence and confidence_note. Cite repo relative paths as the
eval file does (docs/specs/...). Do not copy a shape or a topic from the five existing
questions.

Records you must not draw on at all: 0001, 0002, 0003, 0006, 0007, 0008, 0009, 0011,
0012, 0013, 0014, 0015, 0019, 0021, and the scope document (docs/scope/scope.md).
Records left to you: 0004, 0005, 0010, 0016, 0017, 0018, 0020.
You may not read any other directory than corpus/jobhunt/docs and the eval file.

If you cannot find a real question whose answer spans two or more of the records left
to you, say so and stop. Do not stretch one.

Output: eval/held-out.json with "held_out": true at the top level and two entries,
and a short note listing the files you opened.
```

**Key invariants**:
1. Spec 0004's walk rules (AC-20 to AC-30), matching rule (AC-35, AC-36) and reason rules (AC-38) are unchanged. Only two things are added beside them: a start rule where AC-34 would refuse, and a result built from the findings.
2. `walk.py` and the Cypher read are not edited, and the walk never reads `eval/` (spec 0004 AC-31). `report.py` stays the only code that reads `eval/`, and `eval/runner.json` is read there.
3. No result is a total. No line anywhere counts questions passed (AC-7).
4. `INCONCLUSIVE` is never `PASS`. An absence only counts when the graph holds the item (AC-17).
5. A held item never makes a question pass (AC-6b, spec 0005 condition 4).
6. No command reads a held out file unless it is pointed at it and released (AC-27, AC-28).
7. `load` is not changed, so `SPECIFIED_BY` and a feature row's `PART_OF` are still not written, and the walk still leaves `SPECIFIED_BY` out. Question 5's result says what that costs it, as a finding.
8. No paid call is made outside `tracepath extract`: the runner has no model client (`tests/test_spend_fence.py` is unchanged).

**Security model**: none. A local tool over public repository text. No new setting or secret, and no API call from the runner.

**Configuration required**: none new. `eval` reads the same Neo4j settings as `trace`. Neo4j must be up.

**The eight units** (the free token count endpoint, `extract --dry-run`, 2026-10-07, 57,494 token cached prefix, standard interactive rates). Questions 1, 2 and 5 score items in these sections, and question 4 needs `0008:Requirements` for its start. None is extracted. `0008:Feature design` and `0009:Feature design` are left out: no scored rule reads them, and question 4 is `INCONCLUSIVE` today whatever they hold (AC-17e).

| Unit | Needed by | Counted input | Uncached per call | Measured central, 3 calls | Per call bound |
|---|---|---|---|---|---|
| `0008:Requirements` | 1, 2, 4 | 64,281 | 6,787 | $1.25 | $0.8835 |
| `0003:Requirements` | 1 | 59,061 | 1,567 | $0.27 | $0.8731 |
| `0007:Consequences` | 5 | 59,897 | 2,403 | $0.16 | $0.8748 |
| `0011:Requirements` | 2 | 61,590 | 4,096 | $0.64 | $0.8782 |
| `0014:Decision` | 2 | 58,928 | 1,434 | $0.23 | $0.8728 |
| `0007:Follow-up` | 5 | 59,099 | 1,605 | $0.12 | $0.8732 |
| `scope:Resolved` | 5 | 58,026 | 532 | $0.11 | $0.8710 |
| `0009:Summary` | 5 | 57,762 | 268 | $0.05 | $0.8705 |

The central column is a measured ratio, not the tool's figure (the tool prices only the units whose kind it has a measured output for, and says "not priced" for five of the nine it was shown). How it is built, and the wider total, are in rationale.md. Central total about $2.8, the tool's wider total about $30.1 for the eight, every call at the heaviest measured output with a retry on every run.

**Critical test scenarios**:
- Happy path: question 3's block over the artifacts of `36a6bc5` equals the recorded text, verifies **AC-2**, **AC-3**.
- Happy path: a fixture graph where one question reaches every item prints `PASS`, one reaches some prints `FAIL` with each reason, verifies **AC-5**, **AC-6**, **AC-6c**.
- Edge: a fixture where the only path to an item runs through a held link prints `FAIL` under `--with-held` and the item as `held only`, verifies **AC-6b**.
- Edge: the start item is `reached` at hop 0, prints ` · the start`, and is left out of `K` and `M`, verifies **AC-10**, **AC-10b**.
- Edge: a first entry with no AC form starts at the lowest id among two entities on its line, and at nothing when none is there, verifies **AC-12**, **AC-12b**, **AC-12c**.
- Edge: a question with no `trace` list starts from its first matching `checked` entry, verifies **AC-14**; one with neither is `UNUSABLE` and the run goes on, verifies **AC-15**, **AC-8b**.
- Happy path: an absence question whose two items have accepted entities and no path is `PASS`; with an item reached it is `FAIL` naming the hop; with an item whose section is not extracted it is `INCONCLUSIVE`, verifies **AC-17**, **AC-17b**, **AC-17c**.
- Failure case: a held out file without the flag exits 1, names the flag and prints no question; with the flag it opens with the label, verifies **AC-28**, **AC-29**.
- Failure case: a changed byte in an example makes the digest test fail and the runner print the unchecked line, verifies **AC-20**, **AC-21**.
- Edge: no output line holds a total or a percent, verifies **AC-7**.
- Failure case: `--with-held` on a default graph exits 1 before any question, verifies **AC-9**.

## Build plan

Tracer Bullet: the thinnest real thread first (the runner over a fixture, then over question 3 on the real graph, which needs no new extraction), then the data that names questions, then the gate and the one paid step, then the first full run.

1. `eval` command and the shared body: loop the questions, `report_lines()` per block, the blank line, `Question N: RESULT · K of M` and `verdict()` for questions with a `trace` list, exit codes, no totals, `--with-held` through spec 0005, the hop 0 marker, tested over the hand built fixture graph, with the three existing test strings that read `hop 0` updated, satisfies **AC-1**, **AC-2**, **AC-2b**, **AC-4**, **AC-5**, **AC-6**, **AC-6b**, **AC-6c**, **AC-7**, **AC-8**, **AC-8b**, **AC-8c**, **AC-9**, **AC-9b**, **AC-9c**, **AC-10**, **AC-10b**, **AC-8d**.
2. Question 3 at `36a6bc5`, no API call and no Neo4j: copy the recorded block into `tests/fixtures/experiment-0009-q3-report.txt`, make a temporary root from `git archive 36a6bc5 artifacts`, rebuild the units, score with no chain, and diff the report lines, satisfies **AC-3**.
3. The two new start rules, `resolve_start()` and the `checked` rule, tested on a synthetic eval file and the fixture graph, satisfies **AC-10c**, **AC-11** to **AC-15b**, **AC-12d**.
4. Absence questions: the sidecar's `absence` items, `accepted_here`, the three outcomes and their causes, satisfies **AC-16** to **AC-17e**.
5. `eval/runner.json` with the levels of AC-19 and the digest of `examples/`, the evidence lines, the unchecked line, the digest test, satisfies **AC-18** to **AC-21**.
6. Held out guard: the `held_out` refusal, `--release-held-out`, the label line, the three file tests and the test that no file under `src/` names `held-out`, run against a synthetic held out file, satisfies **AC-24** to **AC-29**, **AC-28b**.
7. Gate, no code: full suite, mypy strict and ruff pass, then commit `src/` and `tests/` as the code commit. Run `extract --dry-run` over the eight units and give the engineer the measured figures, the output assumption and its source. **Nothing paid runs before the engineer's go and a ceiling**, and nothing under `examples/` or `src/tracepath/extract/` changes before the extraction, satisfies **AC-31**, **AC-32**.
8. The paid step, after the go: `extract` on the eight units, one pass, each unit's run files committed as they come back, then `load`. Satisfies **AC-32**.
9. The first full run, no API call: `eval` and `eval --with-held` over the five questions, recorded in `experiments/0011-eval-runner/README.md` with each result, evidence level and reason, and the four commits in order, satisfies **AC-33**, **AC-33b**, **AC-33c**, **AC-34**.
10. The held out questions: open a fresh session in a scratch directory made as the brief says, run the brief, copy `eval/held-out.json` back, write the record of the directory's listing, commit before feature 13's spec, satisfies **AC-22**, **AC-23**, **AC-30**. Independent of steps 7 to 9; do it any time before feature 13 starts.

## Consequences

**Positive**:
- Every later slice is measured by one command, with the difference shown and no number to average.
- Question 4 can only pass on a real absence: an unextracted or held item reads `INCONCLUSIVE`, not a pass.
- The walk, the report rules and the held view are untouched, so experiment 0009 and experiment 0010 stay valid as recorded.
- The held out questions cannot be run by accident, and a drifted example set forces the evidence flags to be re-checked.

**Negative / tradeoffs**:
- Question 3 prints `FAIL` until its gaps close. That is strict on purpose (AC-6), and it is the honest reading of experiment 0009 and 0010.
- Question 5 will probably print `FAIL`: its chain passes through a feature row and through references like "feature 21" that the resolver leaves unresolved, and `load` still does not write `SPECIFIED_BY` or a feature row's `PART_OF`. That is a finding for features 7 and 8, not a defect of the runner.
- The lexically lowest id for question 5's start is a tie break, not a judgment. If three entities share line 313, the start may not be the one a person would pick, and the result says which it was.
- `eval/runner.json` is hand written, so a flag can be wrong. The digest only says the examples changed, not that a flag is still right.
- The hop 0 marker changes three existing test strings and the wording of one line of spec 0004's report. The rule for reaching an item does not change.
- Predictions for questions 1, 2, 4 and 5 were locked before the extraction, in `experiments/0011-eval-runner/predictions.md` (commits `a8da2bc` and `9c53144`), so each first result is scored against its prediction (AC-33b).
- The held out guard stops a slip, not a person who passes the flag.
- Question 4 will read `INCONCLUSIVE` after this extraction, because both tempting items are held for `known_trap_flag` and a held link names AC-4. It can pass only after feature 11 releases them (AC-17e).
- Extraction costs about $2.8 central and up to about $30.1 by the tool's wider rule; the central figure rests on a ratio measured on 54 earlier runs and may be low for prose heavy sections like `0007:Consequences`.

**Neutral**:
- The runner has no model client, so `tests/test_spend_fence.py` is unchanged.
- The eight units are extracted at the current prompt (`0003.1`). Feature 13 may change the prompt, and then these units are extracted again by that decision, not by this one.
- `unit_for()` still takes the first of two same named units, and none of the eight is one of them.

## Follow-up

- [ ] **`/scope`**: feature 13's row should say that no worked example or prompt change may draw on a section cited by `eval/held-out.json` (this spec's AC-25 guards the examples), and that feature 13 re-checks `eval/runner.json`'s flags when it edits `examples/` (AC-20). This spec does not edit another feature's row.
- [ ] **`/scope`**: features 13 and 11 each name `--release-held-out` as the step that runs the held out questions once both have committed, and the extraction of their sections as the one paid step, with a measured estimate and a go.
- [x] **Predictions for questions 1, 2, 4 and 5**: locked before the extraction, in `experiments/0011-eval-runner/predictions.md` (commits `a8da2bc` and `9c53144`). The text is not copied here.
- [ ] **Feature 7 and feature 8**: question 5's result is evidence for alias resolution ("feature 21") and for `SPECIFIED_BY` and feature `PART_OF` links. Neither is built here.
- [ ] **Duplicate section names**: spec 0004's follow up stays open (`unit_for()` and the two `Build plan` units of spec 0007). None of the eight units is affected.
- [ ] **`verify.md`** owes steps for every AC, added by `/develop` with the build.
- [ ] **`/sync`** adds `tracepath eval` and `eval/runner.json` to `AGENTS.md` after the build.
