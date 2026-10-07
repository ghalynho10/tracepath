# Check verify, held item view, 2026-10-07

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/held-item-view` at `e47d803`
**Spec**: [0005](../specs/0005-held-item-view/index.md), checked against its [verify.md](../specs/0005-held-item-view/verify.md)
**Verdict**: **pass with gaps**. Of the 42 criteria, 39 are verified live and 3 are tested only: AC-19b, AC-21 and AC-23c. None is not verified, and none failed. The gaps are listed below.

This is a runtime check, not a code review. Statuses:

- **verified live**: the real command was run in this session, and its output is cited.
- **tested only**: covered by a test (a fixture or an edited input) but not observed in a real run here. For a criterion with several claims, it means at least one claim was not observed live.
- **not verified**: neither.

Free paths only: the committed artifacts, the local Neo4j and the CLI. No extraction call and no token count call was made, so nothing was spent. Eval question 3 is the only real eval question scored with `--with-held`. The other report checks used a synthetic question over spec 0012 lines.

**The first report of this check said "all 34 acceptance criteria" passed. That number was wrong.** Spec 0005 has 42 criteria: AC-1 to AC-29, plus the 13 lettered ones (AC-7b, AC-9b, AC-12b, AC-14b, AC-19b, AC-20b, AC-21b, AC-22b, AC-22c, AC-23b, AC-23c, AC-26b, AC-29b). The 34 does not map onto them. It was a miscount, and that report also overstated the evidence. When it was written:
- **Tested only:** AC-2's dropped link rule, AC-8 and AC-9b, AC-12's held shortcut, AC-14b's "no" form, and AC-11's "no line" clause.
- **No real case behind the evidence:** AC-22 and AC-22c.

This reconciliation added the missing live checks E13 to E18 and nothing else.

## Evidence

Each entry is a command that was run and an excerpt of its output. The full outputs sit in the session scratch area, never in the repository.

- **E1** Three checks on the code and the tests:
  - `git diff 74e8406 -- src/tracepath/traverse/walk.py | wc -l` → `0`.
  - The same diff over `tests/test_walk.py tests/test_walk_graph.py tests/trace_fixture.py tests/fixtures/trace-fixture-expected.txt` → `0`.
  - `uv run pytest -q tests/test_walk.py tests/test_walk_graph.py tests/test_held_walk.py tests/test_held_walk_graph.py tests/test_held_view.py tests/test_held_report.py` → `111 passed in 33.93s`.
- **E2** The default load:
  - `uv run tracepath load`, exit 0 → `Loaded 18 units: 14 records, 166 entities, 53 unresolved, 89 links written (14 collapsed into an existing relationship), 22 links held across units.` · `Units per prompt version: 0002.3: 1, 0003.0: 2, 0003.1: 15.` · `Build manifest: artifacts/graph-build.json`. There is no held line.
  - `'held_view' in graph-build.json` → `False`.
  - Cypher `MATCH (n) WHERE n.held IS NOT NULL RETURN count(n)` → `0`, and `MATCH ()-[r]->() WHERE r.held IS NOT NULL RETURN count(r)` → `0`.
- **E3** Default traces over a graph that holds held items:
  - `trace 0012/AC-7` after `load` and after `load --with-held`, exit 0 both times → `cmp` identical.
  - Held items are within reach of that start: `trace 0012/AC-7 --with-held` on the held graph differs from it and prints 18 lines with `HELD:` or `Held:`.
  - `trace 0002#feature-design:71` on the held graph prints `Chain from 0002#feature-design:71: 1 step`, with 0 `HELD`, byte identical to the same trace after a plain `load`. With `--with-held` the same start prints `6 steps` and `Held: 4 steps, 5 links`.
- **E4** `trace --eval 1` (no flag) after `load` and after `load --with-held` → `cmp` identical. Both exit 1, because the start is held (`✗ 0008/AC-7 is not in the graph. An entity held for review is not in the graph.`, spec 0004 AC-52). `grep -cE "Held item view|held only|through held items|HELD:"` → `0`.
- **E5** `uv run tracepath load --with-held`, exit 0 → the same accepted line as E2, then `Held item view (spec 0005), nothing accepted: 301 held entities, 205 held links and 83 held unresolved written, each marked held. Skipped as already written: 0 held entities, 3 held links. Not written, no first run item behind them: 165 queue rows.`
- **E6** Cypher dumps of the accepted graph after `load` and after `load --with-held`, compared with `cmp`:
  - entities (`canonical_id, labels, properties`, `held IS NULL`): 166 rows
  - typed links (`type, endpoints, properties`, `held IS NULL`): 75 rows
  - unresolved nodes (`properties`, `held IS NULL`): 53 rows

  All three are identical.
- **E7** Cypher on the held graph:
  - `MATCH (e:Entity {held: true}) RETURN count(e), count(e.accepted_by)` → `301, 0`.
  - Held entities with no `PART_OF` to a Record → `0`.
  - `0002/AC-10` → `TRUE, ["known_trap_flag"]`.
  - Held relationships → `205`.
  - `(:Entity {canonical_id: '0007/AC-13'})-[r:UNCLASSIFIED]->(b)` → `"0002", ["Record"], ["endpoint_not_accepted:0007/AC-13"], "0003.1", "claude-sonnet-5", "2e40bcf", "specs/0007-auth-and-per-user-isolation/index.md", "Requirements", 10`.
  - Held `:Unresolved` → `83`, with reasons `0`. Accepted links on a held `:Unresolved` → `0`.
  - Unheld `:Unresolved` reached by a held link → `7`.
  - Accepted entities with `held_reasons` → `0`.
- **E8** Value sources:
  - `0002#requirements:6` in the graph reads `"Consequence", ["rationale_boundary_call"], 31, "Feature 7 deleted the password path outright, page and actio…"`. In `artifacts/runs/0002/requirements/run-1.json` the entity reads `{'type': 'Consequence', 'known_trap_flags': ['rationale_boundary_call']} Feature 7 deleted the password path outright, page and actio…`.
  - `artifacts/runs/0007/requirements/run-1.json` reads `model claude-sonnet-5, prompt_version 0003.1, commit 2e40bcf`, and `## Requirements` sits at snapshot line 10. Both match the held link in E7.
  - In `0002 Feature design`, held links (26) and accepted links (2) carry the same `["0003.1", "claude-sonnet-5", "2e40bcf", 53]`.
- **E9** A second `load --with-held`, exit 0 → `cmp` of the two manifests: identical. The `held_view` keys are `['entities', 'links', 'unresolved', 'skipped_entities', 'skipped_links', 'not_written']`.
- **E10** `trace 0002/AC-10 --with-held`, exit 0:
  - `hop 0  0002/AC-10  AcceptanceCriterion  struck: false  HELD: known_trap_flag`
  - `hop 1  0002#requirements:6  Consequence  struck: false  HELD: runs_disagree, known_trap_flag`
  - `link  0007/AC-13 -[UNCLASSIFIED]-> 0002 (outgoing from 0007/AC-13)  HELD: endpoint_not_accepted:0007/AC-13`
  - `hop 2  0007/AC-13`, reached from `0002#requirements:6`, with no direct link from `0002/AC-10`
  - The last two lines are `Held: 4 steps, 6 links` and then `Prompt versions: all 11 model made steps share prompt 0003.1.`
- **E11** `trace --eval 3 --with-held`, twice, exit 0 both times → `cmp` identical, and identical to `experiments/0010-held-item-view/data/trace-1.txt`. The report opens `Held item view (spec 0005): a second result. Experiment 0009 stays the first.` and `held_for_review keeps spec 0004's meaning: the item is held, whether or not this view wrote it.` It then prints:
  - `held only    spec 0007 AC-13 · …:36 · hop 2 · 0007/AC-13 · via 0002/AC-10, 0002/AC-10 -[SUPERSEDED_BY]-> 0002#requirements:6, 0002#requirements:6, 0002#requirements:6 -[UNCLASSIFIED]-> 0007/AC-13, 0007/AC-13`
  - `Across records: no. No expected item outside 0002 was reached from the start.`
  - `Across records through held items: yes (0007/AC-13, hop 2)`
- **E12** `trace 0012/AC-7 --with-held` after a plain `load` → exit 1, stdout 0 bytes, stderr `✗ --with-held: the graph holds no held item, so there is nothing held to show. Run \`tracepath load --with-held\` first, then trace again.`
- **E13** On the held graph, `trace 0001#binding-rules:2 --with-held` (an accepted entity with no typed link), exit 0 → `1 step`, then straight to `Prompt versions: all 1 model made steps share prompt 0002.3.` There is no `Held:` line and no `HELD`.
- **E14** The real `build_held_view()` over the committed artifacts, its held link resolution captured, no code changed → `candidates 208, written 205, skipped 3: same as accepted 1, same as earlier held 2; skipped entities 0`.
- **E15** The spec 0005 held fixture (records `9003`, `9004`) written into Neo4j through the loader's write functions, then:
  - `trace 9003/AC-1 --with-held`, exit 0 → `diff` against `tests/fixtures/held-fixture-expected.txt`: identical. Excerpts: `hop 1  9003/AC-2  AcceptanceCriterion  struck: false  HELD: runs_disagree, known_trap_flag`, `hop 1  9003/AC-4` by `link  9003/AC-1 -[AMENDED_BY]-> 9003/AC-4 …  HELD: known_trap_flag`, `hop 2  9003/AC-3`, `hop 2  unresolved:9003:feature-77  Unresolved  HELD: reached only by held links`, `Held: 2 steps, 5 links`.
  - `trace 9003/AC-1` (no flag) → `3 steps`: `9003/AC-1`, `9003/AC-5`, `9003/AC-6`.
- **E16** On the E15 graph, an unheld `VERIFIES` link was added by hand from accepted `9003/AC-5` to held `9003/AC-2`. Then `trace 9003/AC-1` (no flag) → `cmp` identical to E15's default output, and `9003/AC-2` appears `0` times.
- **E17** On the held corpus, `trace --eval 1 --eval-file <scratch synthetic.json> --with-held` (spec 0012 AC-7 line 26, the build step at line 88, AC-3 line 22), exit 0:
  - `reached      spec 0012 AC-7 · …:26 · hop 0 · 0012/AC-7`
  - `reached      spec 0012 build step registering the span · …:88 · hop 1 · 0012#build-plan:7`
  - `held only    spec 0012 AC-3 · …:22 · hop 2 · 0012/AC-3 · via 0012#build-plan:9 -[SATISFIES]-> 0012/AC-3, 0012/AC-3`
  - `Across records: no.` and `Across records through held items: no.`
- **E18** On the held corpus, a held `AMENDED_BY` link was added by hand from `0012/AC-7` to `0012#build-plan:7`, then E17 was run again, exit 0:
  - The held walk now reaches the build step by the shortcut: `link  0012/AC-7 -[AMENDED_BY]-> 0012#build-plan:7 (outgoing from 0012/AC-7)  HELD: runs_disagree`.
  - The report still prints `reached      spec 0012 build step registering the span · …:88 · hop 1 · 0012#build-plan:7`.
- **E19** Git:
  - `git log` from `74e8406` → `74e8406` spec, `8ef5de4` code (`git log -1 -- src/` → `8ef5de4`), `2bef321` outputs, `4bacf1f` record, `e47d803` docs.
  - `git show 74e8406:docs/specs/0005-held-item-view/index.md` holds `## Held out discipline`, and `git diff 74e8406` on that file changes only `**Status**: Proposed` to `In Progress`.
  - `experiments/0010-held-item-view/README.md` lines 5 to 7 name `74e8406`, `8ef5de4` and `2bef321`, and line 10 reads `This is a second result. Experiment 0009 stays the first`.
- **E20** After every flagged load or hand edit, a plain `uv run tracepath load` exited 0 and `git status --short artifacts/` was empty.

## Status per criterion

| AC | Status | Evidence |
|---|---|---|
| AC-1 | verified live | E2 (0 held nodes, 0 held relationships) |
| AC-2 | verified live | E3, E4 (held items dropped by the default read), E16 (an unheld link into a held node dropped) |
| AC-3 | verified live | E3 (two starts with held items in reach, byte identical) |
| AC-4 | verified live | E4 |
| AC-5 | verified live | E2 (no `held_view`, no held line) |
| AC-6 | verified live | E6 |
| AC-7 | verified live | E1 (`git diff` empty) |
| AC-7b | verified live | E1 (spec 0004 walk tests unchanged and passing) |
| AC-8 | verified live | E15 (the fixture held walk visits `9003/AC-2`, follows held links, reaches accepted `9003/AC-4`, which the default trace does not) |
| AC-9 | verified live | E10, E15 |
| AC-9b | verified live | E15 |
| AC-10 | verified live | E10, E15 |
| AC-11 | verified live | E10, E15 (the line before `Prompt versions`), E13 (no line when nothing is held) |
| AC-12 | verified live | E11 (two walks), E17 (clean reached prints `reached`), E18 (with a held shortcut) |
| AC-12b | verified live | E11, E17 |
| AC-13 | verified live | E11, E17 |
| AC-14 | verified live | E11 (`Across records: no` while AC-13 is `held only` in 0007) |
| AC-14b | verified live | E11 (yes form), E17 (no form) |
| AC-15 | verified live | E11 |
| AC-16 | verified live | E11 |
| AC-17 | verified live | E5, E7 |
| AC-18 | verified live | E7 (`count(e.accepted_by)` 0) |
| AC-19 | verified live | E7 (held link to Record `0002`), E8 |
| AC-19b | tested only | `tests/test_held_view.py` (both causes) and `tests/test_held_load.py` (the load exits 1 with the graph unchanged). The committed artifacts hold no such link, so the stop cannot be reached through the CLI without hand built artifacts |
| AC-20 | verified live | E7 (83 held `:Unresolved`, no accepted link on them) |
| AC-20b | verified live | E6 (unresolved nodes identical), E7 (7 shared) |
| AC-21 | tested only | `tests/test_held_view.py`. E14: no held entity collides in the committed artifacts, so the skip never happens live |
| AC-21b | verified live | E5 (`0 held entities`) |
| AC-22 | verified live | E14 (1 case), E6 (no accepted link gained `held`) |
| AC-22b | verified live | E5 (`3 held links`) |
| AC-22c | verified live | E14 (2 cases), E5 and E7 (205 written, 205 in the graph) |
| AC-23 | verified live | E5 (165 rows), E10 (the run 2 and 3 link `0002/AC-10 → 0007/AC-13` is absent: AC-13 sits at hop 2) |
| AC-23b | verified live | E5 |
| AC-23c | tested only | The sums held on the real load (E5 succeeded, E14). The stop when they do not is in `tests/test_held_view.py` only |
| AC-24 | verified live | E9 |
| AC-25 | verified live | E9 |
| AC-26 | verified live | E12 |
| AC-26b | verified live | E12 |
| AC-27 | verified live | E11 |
| AC-28 | verified live | E19 |
| AC-29 | verified live | E19 |
| AC-29b | verified live | E19 |

## Gaps (why the verdict is not "pass")

1. **AC-19b is tested only.** No committed unit holds a held link with no review item, or a cross unit held link with no relationship. To observe the stop through the CLI needs a scratch `--root` with a hand edited run artifact.
2. **AC-21 is tested only.** No held entity's id is taken in the committed artifacts (E14, `skipped entities 0`). It needs the same kind of scratch root.
3. **AC-23c is tested only** for its "or the load stops" clause. The sums held on the real load.

## Findings (recorded, not fixed)

1. **verify.md's AC-4 step runs a real eval question.** The step reads `uv run tracepath trace --eval 1` on the held graph, and this check ran it (E4) without `--with-held`. It scored nothing under the held view, and it printed what spec 0004's default report prints. But feature 6 holds out the eval questions other than 3 until features 11 and 13 have locked their choices (scope feature 11's guard). A synthetic question, as in E17, makes the same check without touching them. verify.md should be changed to use one.
2. **verify.md's provenance step names a section with no accepted link.** Spec 0007's `Requirements` holds no accepted link, so "the same values an accepted link written in that unit's section carries" has nothing to compare against there. This check used the unit's run file, then `0002 Feature design`, which has both kinds (E8).
3. **The two hand edits in E16 and E18 wrote to the scratch graph directly**, as the loader never would, to put a case in front of the CLI that the committed data does not hold. Both were cleared by the plain `load` in E20.

## Spend

None. No call reached the Anthropic API.

## Scope

- Feature 14's `Verify it` box is ticked, and all 29 steps in verify.md are ticked. Every step was run and passed, with the substitutions named in findings 1 and 2.
- Spec 0005 stays `In Progress`, because `Test it` is open.
- The three tested only criteria are left for `/test`, or for a scratch root check, to close.
