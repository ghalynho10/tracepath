# Verify: eval runner · spec 0006 · updated 2026-10-07

_Steps derived from spec 0006 acceptance criteria and its Value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

Setup for the steps that need a graph: `docker compose up -d`, then `uv run tracepath load` (the default view). Steps marked "synthetic" use a scratch root made as `tests/test_eval_command.py` makes it: a copy of `artifacts/runs/`, an `eval/questions.json` of questions citing spec 0012, and an `eval/runner.json` with an entry for that file. Run those with `--root <scratch> --snapshot $PWD/corpus/jobhunt/docs`. Never run `--release-held-out` on `eval/held-out.json`: it stays unread until features 13 and 11 have both committed (AC-27, AC-28).

## Commands

### The command (AC-1 to AC-10c)

- [ ] `uv run tracepath eval` → five blocks, `Question 1:` to `Question 5:` in the file's order, no chain printed → AC-1, AC-9c
- [ ] For each N in 1 to 5, the text from `Question N:` to the `Across records` line in `eval` equals the same span of `uv run tracepath trace --eval N` → AC-2
- [ ] In `eval`'s output, each block's `Across records` line is followed by a blank line, its result line, then its evidence line (question 4: the result line, one cause line per item, then the evidence line) → AC-2b, AC-17c
- [ ] Every result line reads `Question N: PASS|FAIL|INCONCLUSIVE · ...`, and a `PASS` or `FAIL` line for a question with a trace list ends `K of M expected items reached besides the start.` → AC-5
- [ ] Synthetic: a question whose every item the walk reaches (spec 0012 AC-7, line 26, and the build step at line 88) prints `PASS · 1 of 1`; one with spec 0012 AC-3 (line 22) added prints `FAIL` and `held_for_review` on that item → AC-6, AC-6c
- [ ] `grep -E '%|\b(total|rate|passed)\b|[0-9]+ of [0-9]+ questions'` over `eval`'s output finds nothing → AC-7
- [ ] `uv run tracepath eval; echo $?` → 0 although no question passes → AC-8
- [ ] Synthetic: a question with no trace list and no sidecar absence entry prints `Question N: UNUSABLE, ...` on stdout in its place, the later questions still print, and the exit code is 1 → AC-8b, AC-8d, AC-15b
- [ ] Synthetic: a question citing `docs/specs/9999-missing/index.md`, and one citing line 0, each print `UNUSABLE` and the rest run → AC-8d
- [ ] `NEO4J_URI=bolt://localhost:1 uv run tracepath eval` → a message on stderr, exit 1, empty stdout, no traceback; the same with a `runner.json` that is not JSON, and with a missing eval file (`--eval-file eval/none.json`) → AC-8c
- [ ] Delete `eval/runner.json` in a scratch root: `eval` runs and every evidence line reads `Evidence: not assessed` → AC-8c, AC-18
- [ ] On the default graph, `uv run tracepath eval --with-held` → exit 1 before any question, with the message `trace --with-held` gives → AC-9
- [ ] `uv run tracepath load --with-held && uv run tracepath eval --with-held` → the held view label once, above the first block; each block opens with the `held_for_review keeps spec 0004's meaning ...` line; a block equals `trace --eval N --with-held`'s report less its label line. Then run a plain `uv run tracepath load` → AC-9b, AC-9c
- [ ] In `eval`'s output, question 2's start line reads `hop 0 · the start · 0011/AC-12`, and under `--with-held` question 1's reads `held only ... hop 0 · the start · 0008/AC-7` → AC-10
- [ ] Question 2 prints `0 of 5` (its start item at 0011 line 37 left out); question 1 prints `0 of 2` on the default graph, where 0008/AC-7 is held and so there is no start node to leave out, and `0 of 1` under `--with-held` → AC-10b
- [ ] The `Start item:` lines name their source: question 2 `from the first trace entry "spec 0011 AC-12"`, question 4 `from the first checked entry "docs/specs/0008-app-shell-and-navigation/index.md line 67 (AC-14)"`, question 5 `Start item: none, no entity at specs/0007-auth-and-per-user-isolation/index.md:313.` (default) and `the entity at ...:313, the lowest id of the 3 entities on that line.` (held); question 3's line is byte for byte experiment 0009's → AC-10c
- [ ] `uv run tracepath trace 0012/AC-7` prints the same chain as before this build; `trace --eval 4` and `trace --eval 5` no longer exit 1 for want of a start rule → AC-4

### Question 3 reproduced (AC-3)

- [ ] `uv run pytest tests/test_eval_runner.py -k ac_3` → passes: question 3 scored with no chain over `git archive 36a6bc5 artifacts` equals `tests/fixtures/experiment-0009-q3-report.txt` → AC-3

### How a question starts (AC-11 to AC-15b)

- [ ] Question 2 (`spec 0011 AC-12`) starts at `0011/AC-12` → AC-11
- [ ] Synthetic: a first entry `spec 0012 Consequences` at line 99 starts at `0012#consequences:3`, the lower of the two entities there, and says `the lowest id of the 2 entities on that line` → AC-12, AC-12b
- [ ] Synthetic: two entities on one line whose ids differ only as `:9` and `:10` start at `:9` (`tests/test_eval_runner.py -k ac_12b`) → AC-12b
- [ ] Synthetic: line 95 of spec 0012, where no entity sits, prints `Start item: none, no entity at ...:95.` and `FAIL` with every item's reason → AC-12c
- [ ] Question 5 starts nowhere on the default graph and at a held entity under `--with-held`, because no accepted entity holds line 313 → AC-12d
- [ ] Under `--with-held`, question 5 resolves its start once, `0007#consequences:19`; the held walk starts there (its start item `held only`, hop 0), and the clean walk, tried at that same id, finds it absent from the clean slice, so no item reads `reached` → AC-13
- [ ] Question 4, with no trace list, starts at `0008/AC-14` from its first checked entry matching the AC-14 regex → AC-14
- [ ] Synthetic: checked entries none of which match the regex make the question `UNUSABLE`, naming it → AC-15
- [ ] `uv run pytest tests/test_eval_runner.py -k ac_15b` → the three UNUSABLE cases pass → AC-15b

### Absence questions (AC-16 to AC-17e)

- [ ] Question 4's block heads its items `Items that should not be reached:` and lists 0007 AC-4 (line 25) and AC-19 (line 42), from `eval/runner.json` → AC-16
- [ ] `uv run pytest tests/test_eval_runner.py -k "ac_17"` → PASS only when every item is accepted, unlinked and unreached; FAIL naming the reached item and its hop; INCONCLUSIVE with each item's first cause; a held link counts only when its other end was visited → AC-17, AC-17b, AC-17c, AC-17d
- [ ] Synthetic: the absence question over spec 0012 prints `FAIL · spec 0012 AC-1 was reached at hop 2, a connection the record does not document.` → AC-17b
- [ ] Question 4 prints `INCONCLUSIVE · absence not provable.`, and `experiments/0011-eval-runner/README.md` reads it as expected, not as a defect → AC-17e

### Evidence flags (AC-18 to AC-21)

- [ ] Each evidence line reads `Evidence: light|weaker|no overlap with a worked example · <reason>` → AC-18
- [ ] `eval` prints question 1 light, 2 weaker, 3 no overlap, 4 light, 5 weaker → AC-19
- [ ] `uv run pytest tests/test_eval_sidecar.py -k ac_20` → passes; change one byte of a file in `examples/` in a scratch git copy and the digest test fails with a message to re-check the flags → AC-20
- [ ] In a scratch root that is a git work tree holding `examples/` and a sidecar whose `examples_sha256` differs, `eval` prints `Evidence flags unchecked: examples/ has changed since they were written.` once, above the first block, and still prints each level → AC-21

### Held out questions (AC-22 to AC-30)

- [ ] `python3 -c "import json; d=json.load(open('eval/held-out.json')); print(d['held_out'], len(d['entries']))"` → `True 2`, without printing any entry → AC-22, AC-28b
- [ ] `experiments/0011-eval-runner/held-out-record/` holds the directory listing, the session's `settings.json` with the deny rules, its `NOTE.md` and the two session transcripts → AC-23
- [ ] `uv run pytest tests/test_held_out.py --tb=no -q` → every test passes, none skipped → AC-24, AC-25, AC-26, AC-27, AC-28b
- [ ] `grep -rl "held-out.json" src/` → nothing → AC-27
- [ ] `uv run tracepath eval --eval-file eval/held-out.json` and `uv run tracepath trace --eval 1 --eval-file eval/held-out.json` → exit 1, naming `--release-held-out`, no question printed; `uv run tracepath eval --release-held-out` → exit 1, the file is not held out → AC-28
- [ ] Synthetic held out file, released: the output opens with `Held out check (spec 0006): a check of the choices features 13 and 11 made, not a measurement.` → AC-29
- [ ] `git log --oneline -- eval/held-out.json` is older than the first commit of feature 13's spec, and no unit holding a line the file cites has a file under `artifacts/runs/` (counts only, never the text) → AC-30

### The extraction and the result record (AC-31 to AC-34)

- [ ] The dry run over the eight units ran before `282b9a4`, and the go and ceiling ($9) came after it → AC-31
- [ ] `git diff --stat 5c8bda4 8fd0436 -- examples src/tracepath/extract` → empty → AC-32
- [ ] `experiments/0011-eval-runner/README.md` lists each question's result, evidence level and the reason for each item not reached → AC-33
- [ ] The README cites `a8da2bc` and `9c53144`, both before `282b9a4`, and scores questions 1, 2, 4 and 5 against their predictions → AC-33b
- [ ] The README names the spec commits, the code commit `e24801d`, the range `282b9a4` to `8fd0436`, and the result commit, in that order → AC-33c
- [ ] `git diff --stat e24801d 4629330 -- src` → empty → AC-34

## Value sourcing

- [ ] Start, AC form: question 2's start is `0011/AC-12`, from its first trace entry by spec 0004 AC-34; edit a scratch copy's first entry to `spec 0011 AC-13` and the start follows it
- [ ] Start, not AC form: synthetic line 99 starts at the entity the graph holds there; on a graph loaded without spec 0012's Consequences runs it reads `Start item: none`, so the id comes from the graph and not the text
- [ ] Start, no trace list: question 4's start comes from the first checked `where` in AC form; in a scratch copy, move that entry after one not in AC form and the start is unchanged; remove it and the question is `UNUSABLE`
- [ ] Absence items: question 4's items come from `eval/runner.json`; change one line number in a scratch sidecar and the block lists the new line
- [ ] Start marker: only an item on the resolved start node's file and line carries ` · the start`, and a held start not in the default graph gets none there
- [ ] K of M: the count leaves out the start node's items; for a start not in the graph it leaves out none (question 1, default view, `0 of 2`)
- [ ] Result: built from the findings only; the same findings under a different evidence level give the same result line
- [ ] Evidence line: from `eval/runner.json`; with the file removed every line reads `not assessed`
- [ ] Stale flags: the unchecked line follows the digest of `examples/` against `examples_sha256`, and is absent outside a git work tree
- [ ] Held out refusal: read from the file's top level `held_out` before any graph read (an unreachable `NEO4J_URI` still gives the refusal message, not a graph error)
- [ ] Graph mode: the `--with-held` flag alone switches the view, as `trace` does
- [ ] Reproduction of experiment 0009: `tests/fixtures/experiment-0009-q3-report.txt` equals the README's fenced block, lines 70 to 82 of `experiments/0009-first-traced-chain/README.md`

## Acceptance criteria coverage

- AC-1 to AC-10c: The command steps · AC-3: Question 3 reproduced · AC-11 to AC-15b: How a question starts · AC-16 to AC-17e: Absence questions · AC-18 to AC-21: Evidence flags · AC-22 to AC-30: Held out questions · AC-31 to AC-34: The extraction and the result record
