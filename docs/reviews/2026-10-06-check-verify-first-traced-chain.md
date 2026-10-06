# Check verify, first traced chain, 2026-10-06

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/first-traced-chain` at `6464aa7`
**Spec**: [0004](../specs/0004-first-traced-chain/index.md), checked against its [verify.md](../specs/0004-first-traced-chain/verify.md)
**Verdict**: **fail**. AC-41 fails, as [experiment 0009](../../experiments/0009-first-traced-chain/README.md) recorded. It was reported as it stands, not rerun, and nothing was changed to make it pass. Of the other 63 criteria, 55 are verified live and 8 are tested only. The gaps are listed below.

This is a runtime check, not a code review. Statuses:

- **verified live**: the real command was run in this session, and its output is cited.
- **tested only**: covered by a test (a fake client, a fixture or replay) but not observed in a real run here. For a criterion with several claims, it means at least one claim was not observed live.
- **not verified**: neither.

The paid runs used a scratch `--root` outside the repository. No run file landed in `artifacts/`, and `git status` stayed clean apart from this file.

## Evidence

Each entry is a command that was run and an excerpt of its output. The full outputs and proxy logs sit in the session scratch area, never in the repository.

- **E1** `uv run pytest -q` → `549 passed in 372.63s`. `uv run mypy` → `Success: no issues found in 65 source files`. `ruff check` → `All checks passed!`, `ruff format --check` → `254 files already formatted`.
- **E2** `uv run tracepath load`, run twice, exit 0 → `Loaded 18 units: 14 records, 166 entities, 53 unresolved, 89 links written (14 collapsed into an existing relationship), 22 links held across units.` · `Units per prompt version: 0002.3: 1, 0003.0: 2, 0003.1: 15.` `shasum artifacts/graph-build.json` read `ead9b797…` before, after the first load and after the second, `cmp` reported the two loads byte identical, and the two load outputs were identical too.
- **E3** Cypher on the loaded graph. Typed relationships: `AMENDED_BY 2, BLOCKED_BY 1, SATISFIES 25, SUPERSEDED_BY 1, UNCLASSIFIED 8, VERIFIES 38`, each with `missing_provenance: 0`. `PART_OF 166` carries none, as specced. Provenance groups: `0003.1: 60, 0003.0: 14, 0002.3: 1`, all `claude-sonnet-5`, `2e40bcf`. Constraints: `entity_canonical_id_unique`, `record_canonical_id_unique`, `unresolved_canonical_id_unique`. Duplicate `(type, from, to)` relationships: `0`.
- **E4** A script over `graph-build.json`, the split snapshot and the graph:
  - Manifest keys are `corpus_commit, prompt_versions, review_log_entries, units`. Each unit carries `run_files, model, prompt_version, accepted_entities, accepted_links, held_links`, and `review_log_entries: 0`.
  - Accepted entities sum to 166 (the graph holds 166), and accepted links sum to 89 (the load wrote 89).
  - `file_line check: 166 entities with a line, 0 mismatches`. `0014/AC-12` is stored at section line 24 and file line 42, and snapshot line 42 reads `- **AC-12**: \`job_description\` holds…`.
  - `link provenance vs manifest: 75 links, 0 not matching their unit's version`.
- **E5** A collapse check against the rebuilt links:
  - `triples written more than once: 4, extra writes: 14`. Each is held as one relationship carrying its last write.
  - All 14 extra writes come from one unit, `9. Profile entry · done`.
- **E6** The fixture written into Neo4j, then `uv run tracepath trace 9001/AC-1` gave exit 0, and `diff` against `tests/fixtures/trace-fixture-expected.txt` found it identical. Excerpts:
  - `hop 1  9002  Record` … `specs/9002-fixture-neighbour/index.md · commit f1x7ure · code, no model` · `stopped: whole document, not expanded`
  - `link  9001#build-plan:1 -[SATISFIES]-> 9001/AC-1 (incoming to 9001/AC-1)`
  - `mention "feature 99"` · `specs/9001-fixture-walk/index.md · Requirements · line 10 · no commit, no model` · `stopped: unresolved, not expanded`
  - `hop 0  9001/AC-1  AcceptanceCriterion  struck: true`
  - `hop 3  9001/AC-4` … `stopped: depth limit, 1 typed link not followed`
  - `Prompt versions: model made steps do not share one prompt version (0003.0: 2, 0003.1: 11).`
- **E7** On the fixture graph:
  - `trace 9002` → `hop 0  9002  Record` … `stopped: whole document, not expanded`.
  - `trace unresolved:9001:feature-99` → `stopped: unresolved, not expanded`.
  - `trace 9999/AC-1` → exit 1, stderr `✗ 9999/AC-1 is not in the graph. An entity held for review is not in the graph.`
- **E8** On the real graph:
  - `trace 0012#build-plan:7` → 7 steps, hops 0 to 3. Entity lines read `specs/0012-model-client-router/index.md · Build plan · file line 88 · commit 2e40bcf · prompt 0003.1`, and link lines read `… · Build plan · line 80 · commit 2e40bcf · prompt 0003.1 · "satisfies **AC-7**"`. It ends `Prompt versions: all 13 model made steps share prompt 0003.1.`
  - `trace 0007/AC-14` → `link  0007#feature-design:54 -[VERIFIES]-> 0007/AC-14 (incoming to 0007/AC-14)`.
- **E9** `trace --eval 3` was run twice, then `load`, then a third time. Each run exited 1, and all three outputs hash to `e2a5fca0…`. The output matches the block in experiment 0009: five items `not reached`, four of them `held_for_review` and line 232 `link_held`, then `Visited steps matching no expected item: 0`, `Accepted links written outside the expected sections that touch 0002 or 0007: 0.`, and `✗ 0002/AC-10 is not in the graph.`
- **E10** `trace --eval N --eval-file <scratch synthetic file>` was run on the real graph with the committed runs. Question A starts at `spec 0012 AC-7`:
  - `reached  spec 0012 AC-7 · …:26 · hop 0 · 0012/AC-7`
  - `reached  spec 0012 AC-1 (also) · …:90 · hop 1 · 0012#build-plan:9`
  - `not reached  spec 0012 AC-3 · …:22 · held_for_review`
  - `…:29 · link_held`
  - `…:50 · section_not_extracted`
  - `spec 0014 … · 0014…/index.md:90 · section_not_extracted`. This is the same line number as the visited `0012#build-plan:9`, but it is not reached.
  - `Visited steps matching no expected item: 4`
  - `Accepted links written outside the expected sections that touch 0012 or 0014: 6.`, followed by six listed links, including `0015#feature-design:2 -[unclassified]-> 0012`.

  Question B: `not reached  spec 0008 preamble · …:3 · record_not_expanded`.
- **E11** Start refusals, each exit 1:
  - `trace --eval 4` → `✗ question 4 has no trace list, so it has no start item`
  - `trace --eval 5` → `✗ question 5: its first trace entry, 'spec 0007 Consequences', does not match \`spec NNNN AC-N\`, so no start item is guessed`
  - `trace --eval 9` → `✗ question 9 is not in the eval set, which holds questions 1 to 5`
- **E12** Typed failures. Every one exited 1 with one stderr line and a `Traceback` count of 0:
  - `load --root <no runs>` → `✗ no run artifacts found under …`
  - `load --root <one run file at 0003.0>` → `✗ 0012 Follow-up: runs mix models ['claude-sonnet-5'] or prompt versions ['0003.0', '0003.1']`
  - `NEO4J_PASSWORD= load` → `✗ NEO4J_PASSWORD is not set.`
  - `NEO4J_URI=bolt://localhost:7699 trace 0012/AC-7` → `✗ Neo4j is not reachable at bolt://localhost:7699.`
  - `ANTHROPIC_API_KEY= extract 0010:Context --ceiling 1` → `✗ ANTHROPIC_API_KEY is not set.`
  - `extract 0010:Context` → `✗ --ceiling USD is required: the most this command may spend.`
  - `extract 0002:Requirements --ceiling 1` → `✗ an artifact already exists at artifacts/runs/0002/requirements/run-1.json`
- **E13** In a scratch copy of the repository, the `json` fence under `## Output` of `examples/0006-feature-design.md` was changed to `text`. Then `extract 0010:Context --ceiling 3` was run through the logging proxy: exit 1, stderr `✗ 0006-feature-design: no \`## Output\` section with a fenced block under it`, 0 tracebacks, and 0 requests at the proxy.
- **E14** `extract --dry-run 0002:Requirements "0002:Feature design" 0007:Requirements "0007:Feature design" --ceiling 11 --root <corpus only>`, through the logging proxy, exit 0:
  - `Rates assumed, standard interactive pricing, not Batch: input $2.00, output $10.00, 1 hour cache write $4.00, cache read $0.20`
  - `0002:Requirements: 59,090 input tokens counted, 57,494 cached prefix, 1,596 uncached per call.`
  - `central: 27,384 output per call, from \`0021 ## Requirements\` (experiment 0008 data/run.json)`
  - `wider: 39,234 output per call, the heaviest measured call (experiment 0005, \`0021\` run 2)`
  - `Central total: 12 calls, $3.7426.` · `Wider total: 24 calls, $10.1903` · `Dry run: no extraction call made.`

  The proxy log shows 7 requests across this and the `0010:Context` dry run, all `/v1/messages/count_tokens`, and none to `/v1/messages`.
- **E15** `extract 0010:Context "0007:Feature design" --ceiling 3`, through the proxy: exit 1, `✗ an artifact already exists at artifacts/runs/0007/feature-design/run-1.json`, 0 requests, and nothing written for `0010`.
- **E16** Paid test 1: `extract 0010:Context --ceiling 0.01 --root <scratch>` → `Wider total: 6 calls, $2.6423, above the ceiling of $0.01.` Then exit 1, `✗ the wider estimate $2.6423 is above the ceiling $0.01, so no call is made.` The proxy saw 2 `count_tokens` calls and 0 message calls, and 0 artifacts were written.
- **E17** Paid test 2a, a drop before any usage event. The proxy answered stream headers and reset the connection before any event, and the API was never contacted for that call. Command: `extract 0010:Context --ceiling 2.65 --root <scratch>`, exit 1.
  - `run 1 attempt 1: failed (… the connection dropped mid stream (peer closed connection without sending complete message body …)), counted at the flat $0.4144 … → artifacts/runs/0010/context/failed-run-1-attempt-1.json`
  - `run 1 attempt 2: settled, 65 in, 121 out, cache write 57,494, read 0, $0.2313; running total $0.6457 → …/run-1.json`
  - `2 calls, 1 settled, 1 failed or dropped.` · `Attempts with null usage:` · `0010:Context run 1 attempt 1: failed-run-1-attempt-1.json`
  - stderr `✗ stopping: call 2 read no cache`
  - The failed artifact holds `input_tokens: None, output_tokens: None`. The proxy log shows `"path": "/v1/messages", "stream": true` for both calls, and no batch path.
- **E18** Paid test 2b, a cut after usage started arriving. The proxy relayed `message_start`, then cut both connections before `message_delta`. Same command, fresh scratch root, exit 0.
  - `run 1 attempt 1: failed (… dropped mid stream …), counted at the flat $0.4144`
  - `run 1 attempt 2: settled, 65 in, 76 out, cache write 0, read 57,494, $0.0124`
  - `run 2 attempt 1: … 67 out … $0.0123` · `run 3 attempt 1: … 91 out … $0.0125`
  - `4 calls, 3 settled, 1 failed or dropped. Spent $0.4516` · `Attempts with null usage:` · `0010:Context run 1 attempt 1: failed-run-1-attempt-1.json`
  - The failed artifact holds `input_tokens: 65, cache_read_input_tokens: 57494, output_tokens: None, stop_reason: None`.
  - Recomputing each settled attempt at the stated rates gives `0.2313, 0.0124, 0.0123, 0.0125`, the same as printed.
- **E19** Artifact file times (`stat %Fm`) against the proxy's request times. Each artifact was written before the next call was sent:
  - 2a: `failed-run-1-attempt-1.json` at …649.197, before call 2 at …649.204.
  - 2b: `failed-run-1-attempt-1.json` …669.049, then call 2 …669.053; `run-1.json` …671.155, then call 3 …671.160; `run-2.json` …673.212, then call 4 …673.217.
- **E20** Rerun of 2a's command on its interrupted unit: exit 1, `✗ an artifact already exists at …/root-a/artifacts/runs/0010/context/run-1.json`, with no call (the base URL pointed at a closed port).
  - `load --root <2a scratch>` → `Loaded 0 units` · `Not loaded: 0010 Context has 1 settled runs of 3, so it is not extracted.` The graph was cleared, then reloaded from the repository.
  - `trace --eval 1 --eval-file <synthetic D> --root <2a scratch>` → `not reached  spec 0010 context · specs/0010-profile-entry/index.md:12 · section_not_extracted`.
- **E21** Git:
  - `git merge-base --is-ancestor` orders `7bd6c48` (spec) before `f12892d` (`src/`), and `f12892d` before `fda25e1` (first run artifact).
  - `git diff --stat f12892d HEAD -- src examples` is empty.
  - The four units' run files have one commit, `fda25e1`, and no diff since.
  - Spec 0004 changed after `7bd6c48` only in its `**Status**` line (`5dbc968`).
  - `artifacts/review-log.json` is `[]`, last touched in `f6ad4e9`.
  - `ls examples` lists no file drawn from 0002 or 0007.
  - `468f05f` rewords the scope row, and `docs/scope/scope.md:76` reads `two or more Records`.
- **E22** Summing the 12 question 3 artifacts gives `input 69927 output 321796 cache write 57494 cache read 632434`, 759,855 tokens in, `$3.7143`. This matches experiment 0009's Cost table.
- **E24** The engineer read the Console's Usage page for 2026-10-06 UTC (model Sonnet 5, all workspaces and API keys), against this check's paid runs:
  - Tokens in: 287,795. The artifacts give 287,795, a gap of 0.
  - Tokens out: 421. The artifacts give 355, a gap of 66. The 66 are the 2b cut call's output, which its artifact records as null by design.
  - Credits fell from $16.10 to $15.82 over the same period, $0.28.
- **E23** `grep -i eval src/tracepath/traverse/*.py src/tracepath/graph/read.py` finds only three docstrings that state nothing there names the eval set. `grep -rl "eval/\|EVAL_FILE\|linked-records-research" src/` lists `report.py` and `cli.py`; `cli.py` only imports `EVAL_FILE` and `read_question` from `report.py`.

## Status per criterion

| AC | Status | Evidence |
|---|---|---|
| AC-1 | verified live | E21 (no example from 0002 or 0007), E9 (question 3) |
| AC-2a | verified live | experiment 0009 README, Question section: "Question 3 spans two Records, spec 0002 and spec 0007 (AC-2a)" |
| AC-2b | verified live | E21 (`468f05f`, `scope.md:76`) |
| AC-3 | verified live | E13 |
| AC-4 | verified live | E12, E15 |
| AC-5 | tested only | `tests/test_extract_command.py`. A collision at a retry's path needs a planted file, which was not done in a paid run |
| AC-6a | verified live | E14 (proxy: count endpoint only) |
| AC-6b | verified live | E14 |
| AC-6c | verified live | E14 |
| AC-7 | verified live | E12 |
| AC-8 | verified live | E16 |
| AC-9 | tested only | `tests/test_extract_command.py`. It cannot fire live on a small run (finding 4) |
| AC-10a | verified live | E17, E18 (`counted at the flat $0.4144`) |
| AC-10b | verified live | E18 (recomputed costs match) |
| AC-11 | verified live | E17 (stop), E18 (no stop when calls read the cache). See finding 1 |
| AC-12a | verified live | E19 |
| AC-12b | verified live | E17, E18 |
| AC-13 | tested only | `tests/test_extract_command.py`. No paid run failed after its retry |
| AC-14 | verified live | E17, E18 |
| AC-48 | verified live | E20 |
| AC-49 | verified live | E17, E18 (proxy: `/v1/messages`, `stream: true`, no batch path) |
| AC-15 | verified live | E2, E3. The clear is shown by E20, where a load of 0 units emptied the graph |
| AC-16 | tested only | Live: every typed link carries provenance matching its unit (E3, E4), and repeated triples collapse into one relationship carrying the last write (E5). Not live: links from different units collapsing, because all 14 collapses in the data are within one unit (E5). Tested in `tests/test_load_provenance.py` |
| AC-17a | verified live | E4 |
| AC-17b | verified live | E4 |
| AC-17c | verified live | E4, E2 |
| AC-18 | verified live | E2 |
| AC-19 | verified live | E2 |
| AC-50 | verified live | E4 |
| AC-51 | verified live | E2 (`14 collapsed`), E5 |
| AC-20 | verified live | E7, E9 |
| AC-21 | tested only | Followed live: `AMENDED_BY`, `SATISFIES` (both ways), `SUPERSEDED_BY`, `UNCLASSIFIED` (both ways), `BLOCKED_BY` (E6) and `VERIFIES` (E8). `CORRECTED_BY` is absent from the real graph, and in the fixture it only closes the cycle, so following it never shows in the output. Covered by `tests/test_walk.py` |
| AC-22 | verified live | E6. Every fixture entity is `PART_OF` Record 9001, and 9001 never appears |
| AC-23 | verified live | E6 |
| AC-24 | verified live | E6, E7 (a Record and an Unresolved node, both as the start) |
| AC-25 | verified live | E6: 8 steps, 8 distinct nodes, the cycle ends |
| AC-26 | verified live | E6: hop 1 runs `AMENDED_BY`, `SATISFIES`, `SUPERSEDED_BY`, then `UNCLASSIFIED` outgoing before incoming. E9 repeats identically |
| AC-27 | verified live | E6 (`struck: true` on the start, nothing else changes) |
| AC-28a | verified live | E6, E8 |
| AC-28b | verified live | E6, E7 |
| AC-28c | verified live | E6, E7 |
| AC-29 | verified live | E6, E8 |
| AC-30 | verified live | E6 (mixed), E8 (shared) |
| AC-31 | verified live | E23 |
| AC-32 | verified live | E6 (the command's output equals the hand written expectation), E1 |
| AC-33 | verified live | E6 |
| AC-34 | verified live | E9 (`0002/AC-10` from `"spec 0002 AC-10 (struck)"`), E11 |
| AC-35 | tested only | Live: question 3's items are lines 31, 35, 142, 36 and 232, and `also` items carry the label `(also)` (E9, E10). Not observable: that an `also` line carries no AC token. Tested in `tests/test_report.py` |
| AC-36 | verified live | E10 (same file and line are reached; the same line in another file is not) |
| AC-37 | verified live | E9, E10 |
| AC-38 | tested only | Live: `held_for_review`, `link_held`, `section_not_extracted`, `record_not_expanded` (E9, E10, E20). Not live: `unresolved_endpoint`, `no_link`. Each code is tested in `tests/test_report.py` |
| AC-39 | verified live | E9 (0), E10 (4) |
| AC-40 | verified live | E9 (0), E10 (6 listed, 1 listed) |
| AC-41 | **failed** | As recorded in `experiments/0009-first-traced-chain/README.md`, Result: "AC-41 does not hold. No item in spec 0007 was reached, because no walk started." Confirmed unchanged by E9. Not rerun, nothing changed |
| AC-52 | verified live | E9 |
| AC-42 | verified live | E9 |
| AC-43 | verified live | E9 |
| AC-44 | tested only | Live for `ExampleError`, `ArtifactCollisionError`, `GraphUnavailable`, `SettingsInvalid`, `RebuildFailed`, `ProvenanceMismatch`, a missing start and an unusable eval entry (E7, E11, E12, E13). Not live: `UnitFailed` (the AC-13 stop) and `GraphWriteFailed`, tested in `tests/test_extract_command.py` and `tests/test_graph_load.py` |
| AC-45 | verified live | E21 |
| AC-46a | verified live | experiment 0009 README header: "Spec: 0004, committed at `7bd6c48`" |
| AC-46b | verified live | E21 |
| AC-47 | verified live | E21 |
| AC-53 | verified live | E21 (no `src/` change after `f12892d`). The record says "No defect in the walk or the report code was found. This is the only result" |
| AC-54 | verified live | The record's comparison exists and states its gap (0). The artifact half matches the record (E22). The Console comparison was repeated live on this check's own paid runs (E24): input matched to the token, and the output gap was stated and explained, not hidden. The 2026-10-05 Console figures themselves rest on the record's own reading by the engineer |

## Gaps (why the verdict is not "pass")

1. **AC-41 failed**, as recorded in experiment 0009. Feature 5 stays in progress.
2. **Tested only**: AC-5, AC-9, AC-13, AC-16, AC-21, AC-35, AC-38, AC-44, each for the reason given in its row.
3. **Fault (b) did not cut partway through the output.** The proxy's rule was to cut after 5 text deltas, or at `message_delta`, whichever came first. `0010 Context` produced only 3 text deltas, so the cut landed after the whole output and before `message_delta`. The failed artifact's `raw_response` holds the complete `{"entities":[],"relationships":[]}`. The code path is the same one a cut in the middle takes (a snapshot exists, `stop_reason` is null, output is null), but a cut in the middle of the text was not observed. Closing this needs a rerun with the cut at the first text delta, on a section that writes more than a few tokens.

## Findings (recorded, not fixed)

1. **AC-11 stops the command when a first call drops on a cold cache (confirmed by E17).** When the command's first call drops before `message_start`, nothing writes the cache. The retry then has to write it, so it reads 0, and the check in `run_metered()` (`calls > 1`, usage reported, `cache_read_input_tokens == 0`, `src/tracepath/extract/metered.py`) stops the command with `stopping: call 2 read no cache`.
   - The unit is left with 1 settled run of 3, and AC-48 means it can never be resumed. The $0.23 cache write is spent, and the unit yields nothing loadable.
   - This follows AC-11's wording, but not its stated reason ("they should read the prefix the first call wrote"): here the first call wrote nothing.
   - verify.md's build reading, "neither says anything about the cache, so the run's one retry still covers it", holds for the retry being made, but not for the run continuing after it.
   - A cold cache is the normal state at the start of any extraction session (the cache lasts 1 hour), so this is the realistic case for a first call that drops.
2. **`--dry-run` refuses units that are already extracted.** `preflight()` runs before the dry run branch in `extract` (`src/tracepath/cli.py`), so verify.md's dry run command for the four question 3 units now exits 1 with `an artifact already exists at artifacts/runs/0002/requirements/run-1.json`. A dry run spends nothing and writes nothing, so the collision check is not needed for it. Workaround used here: `--root` pointing at a copy that holds only the corpus (E14).
3. **A garbled count response ends in a raw traceback.** While building the proxy, a gzip body passed through without its header made `count_tokens` fail to parse, and `extract` printed a full Rich traceback ending `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8b`. The `except` around the count calls in `extract` catches only `EstimateUnavailable` and `anthropic.APIError`. The trigger was a fault in the test proxy, not in the API, and AC-44's list does not name this case. But it breaks AGENTS.md's rule that real failures exit 1 with a clear message, "never a raw traceback".
4. **AC-8 forces a ceiling so high that AC-9 cannot fire on a small run.** AC-8 refuses to start unless the ceiling is at least the wider estimate, which prices every call at 39,234 output tokens with a retry on every run. For `0010 Context`, 47 characters, that is $2.6423 (E16). AC-9 then stops only when the running total plus $0.4144 would pass the ceiling, which is after about $2.23 has been spent. So `--ceiling` cannot express a budget below the wider estimate, and on a single unit the guard per call never bites below about $2.2. For this check, the bound on spend was the measured worst case, not the tool's ceiling.
5. **A cut call's output is billed but never reaches its artifact.** In 2b, the cut call's artifact records `output_tokens: null` by design (`_dropped_attempt()` keeps the output count null until `message_delta`). The Console shows 66 output tokens for it, about $0.0007. Summed artifact usage therefore undercounts any cut that comes after `message_start`, and only the Console gives the true figure. This is why AC-54's comparison exists. The flat $0.4144 in the running total covers it.
6. Smaller observations:
   - A dropped call that never reached the API still counts $0.4144 in the running total (E17: running total $0.6457, real spend $0.2313). This errs safe.
   - `load` over a root with no complete unit prints `Units per prompt version: .` (E20). This is cosmetic.

## Spend

Paid tests on 2026-10-06, between 18:50:47 and 18:51:15 UTC, section `0010:Context`, approved worst case about $1.30 in total.

| Test | Measured worst case | Actual, from the artifacts | Running total printed |
|---|---|---|---|
| 1, `--ceiling 0.01` | $0 | $0 (2 free count calls, no message call) | none, stopped before any call |
| 2a, drop before usage | $0.4633 | $0.2313 (the retry: 65 in, 121 out, 57,494 cache write; the dropped call never reached the API) | $0.6457 |
| 2b, cut after usage started | $0.5449 | $0.0495: $0.0372 for the three settled calls, plus $0.0123 for the cut call (65 in and 57,494 cache read as recorded, and 66 output tokens from the Console, E24) | $0.4516 |
| **Total** | **$1.0082** | **$0.2808**, matching the $0.28 fall in Console credits (E24) | |

Console check (E24): 287,795 tokens in against 287,795 in the artifacts, and 421 out against 355 in the artifacts. The 66 token gap is the cut call's output. The zero input gap confirms that 2a's dropped call never reached the API.

## Scope

Nothing ticked. The verdict is fail, so feature 5's `Verify it` box, the spec's status and the boxes in verify.md are left as they were.
