# tracepath

A terminal tool that answers "why was this built this way?" from a project's decision records. `tracepath ask` finds the graph items that bear on a plain English question by retrieval over the extracted graph, answers it in one model call, and checks every citation in code. Corpus: JobHunt's specs, pinned at commit `2e40bcf`.

## Stack

- **Language / Runtime**: Python 3.12+, managed by uv
- **CLI**: Typer (commands) + Rich (terminal output)
- **Graph store**: Neo4j 5 Community in one Docker container, official `neo4j` driver v6, raw hand written Cypher. The graph is derived and disposable: JSON run artifacts are the source of truth.
- **Extraction**: Claude Sonnet 5.5 (`claude-sonnet-5-5`, spec 0007; since feature 9 every committed unit is on it, at prompt `0003.1`) via the Anthropic SDK, native structured outputs, Pydantic models as the single schema
- **Config**: `.env` loaded with `python-dotenv` (see `.env.example`)
- Full decision: [spec 0001](docs/specs/0001-stack-and-architecture/index.md)

## Build approach

**Tracer Bullet**: one thin, fully real thread through extract, resolve, store, and traverse; each later slice thickens one strand of that same thread.

## Commands

```bash
uv sync                          # install
uv run pre-commit install        # once per clone: enables the commit hook
docker compose up -d             # start Neo4j (Browser: http://localhost:7474)
uv run tracepath status          # run the CLI, from the repo root (see below)
uv run tracepath extract RECORD:SECTION ... --ceiling USD   # paid model calls; --dry-run only counts (free), --resume completes a unit cut short
uv run tracepath load            # rebuild the graph from artifacts/runs/, no API call; by default writes held items, marked held (spec 0005), and applies the narrow hold rule (spec 0008)
uv run tracepath trace START     # walk a chain; trace --eval N scores eval question N
uv run tracepath load --no-with-held --no-narrow-hold   # opt out of either default; graph-build.json records each setting (held_view, narrow_hold), so a plain load after restores both defaults
uv run tracepath trace START --no-with-held   # held items show by default, each printed HELD:; --no-with-held walks accepted items only; --with-held given by name refuses a graph with no held item
uv run tracepath eval            # score every question of eval/linked-records-research.json: pass, fail or inconclusive, no API call (spec 0006); eval/runner.json is its sidecar (evidence flags and the examples digest)
uv run tracepath eval --no-with-held   # score accepted items only; with neither held flag, eval and trace --eval follow how the graph was loaded (graph-build.json's held_view)
uv run tracepath eval --no-narrow-hold   # eval and trace --eval refuse a graph loaded with the other narrow hold setting, so a graph loaded before spec 0008's flip is refused until `tracepath load` runs again
uv run tracepath eval --eval-file F --release-held-out   # run a held out file; refused without the flag, and only once features 13 and 11 have committed
uv run tracepath load --code-pass   # spec 0007: route with the code pass; load, review-queue, eval and trace --eval each take --code-pass, off by default; eval and trace --eval refuse a graph loaded the other way
uv run tracepath review-queue --code-pass   # writes artifacts/review-queue-code-pass.json, never over the default review-queue.json; --no-narrow-hold adds -without-narrow-hold to the name, so four queue files in all
uv run tracepath extract RECORD:SECTION ... --ceiling USD --expect-model M   # refuses (exit 1) before any call when the settings model differs from M
uv run tracepath ask "QUESTION" --ceiling USD   # spec 0009: answers a why question from the graph, every claim citing an item; one paid call, record written to artifacts/asks/; --ceiling is required except with --dry-run; verdict answered, partly, not_supported or no_documented_link (prompt ask-2)
uv run tracepath ask "QUESTION" --dry-run   # finds the items and prices the call only: no call, no record (free), so no --ceiling needed
uv run tracepath ask --eval N --ceiling USD   # asks eval question N; --eval-file F --release-held-out runs a held out file, refusing a question already answered once
uv run tracepath ask "QUESTION" --hops N --ceiling USD   # link hops added around the search hits: 0, 1 or 2, default 2; printed on the Items sent line and stored as hops in the record (spec 0009 AC-10 note, experiment 0016)
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run mypy                      # typecheck, strict
uv run pytest                    # tests, needs Neo4j up for integration; about 15 minutes locally (tests that do not need the whole corpus run on a fixed subset)
uv run pytest -m "not integration"   # unit tests only, no Neo4j needed
uv run tracepath load            # after the suite: the ask integration tests (tests/test_ask_command.py) empty the shared Neo4j graph
```

tracepath runs from this repository with `uv run`, not as an installed tool: the extraction prompt reads `examples/` relative to the repo root (`EXAMPLES_DIR` in `src/tracepath/extract/examples.py`), and `examples/` is not part of the built package. The prompt is built on first use, so a command that makes no extraction call (`status`, `review-queue`) never reads it.

## Layout

- `docs/`: the scope (`docs/scope/`), specs (`docs/specs/`), and standing rules (`docs/reflexes.md`).
- `corpus/`: the pinned JobHunt snapshot, tracked in git.
- `eval/`: the eval set, tracked in git.
- `reference/`: private inputs from prior work, evidence and candidates, not settled decisions. Gitignored, local only, never edited. Specs may cite it, but code and tests must never read or import from it, so CI works without it.
- `examples/`: worked extraction examples, one per unit kind, tracked in git. Inputs to `system_prompt()` (`src/tracepath/extract/client.py`), each with its input, JSON output, reasoning notes, and a rules list. A worked example's JSON must validate against `extraction_json_schema()`. Only the `text` fence under `## Input` and the `json` fence under `## Output` reach the model, read in filename order by `src/tracepath/extract/examples.py`; a file missing either fence fails the prompt build.
- `artifacts/`: the JSON run artifacts and review queue, tracked in git, the source of truth the graph is rebuilt from. Append only: `write_run()` raises `ArtifactCollisionError` rather than replace an existing file. Runs replaced by a newer prompt move to `artifacts/superseded/<date>-prompt-<version>/` with a `NOTE.md`, never deleted (`experiments/README.md`). `artifacts/graph-build.json` is derived, not a run artifact: every `load` rewrites it (spec 0004 AC-17).

## Specs

Stored in `docs/specs/`. Format: `docs/specs/NNNN-title/index.md` (plus `rationale.md`, `verify.md`). Scope: `docs/scope/scope.md`.

## Corpus and eval

- `corpus/jobhunt/docs/`: JobHunt's `docs/` at `2e40bcf`, a read only snapshot. Never edit or regenerate it. It is tracked in git, so CI checks against it; `corpus/jobhunt/SNAPSHOT.md` records the commit and the command that made it.
- `eval/linked-records-research.json` (plus its `.md` twin): the five eval questions with expected chains, read at the same commit. Bring in as is, never regenerate. `tests/test_corpus.py` checks every cited passage exists in the snapshot; a missing snapshot fails the test.
- `eval` matches an expected item on its cited line, or on the next line when the cited line is blank and the quote starts below it: the same one line tolerance `tests/test_corpus.py` uses (spec 0004 AC-36, note of 2026-10-19).
- `artifacts/runs/` holds the whole corpus, 240 units, all on `claude-sonnet-5-5` with prompt `0003.1` (feature 9). The 12 units `tracepath extract` cannot address are left out (scope, feature 9). The 29 units before it sit in `artifacts/superseded/2026-10-18-claude-sonnet-5/` plus the three it kept; a test pinned to that older corpus reads it through `pre_feature_9_runs()` in `tests/conftest.py`, never through `artifacts/runs/`.

## Rules

- **Functional core, imperative shell.** Pipeline steps (extract, resolve, traverse) are pure functions. Neo4j, the Claude API, files, and the clock live at the edges and are passed in, not reached for.
- **Immutable data.** Frozen dataclasses or frozen Pydantic models, tuples over lists in return values. Never mutate an argument. Module level names are constants only.
- **Uncertainty is a value, failure is an exception.** "Unresolved" and "unclassified" are real values in the model, never guessed away or dropped. Real failures raise typed exceptions (like `GraphUnavailable`); the CLI turns them into a clear message and exit code 1, never a raw traceback.
- **Every Cypher write asserts its own result.** Each batched write returns how many of its input rows it matched or wrote (`RETURN count(...) AS written`), and `_write()` in `src/tracepath/graph/load.py` raises `GraphWriteFailed` when that differs from the number of rows it was given. Neo4j has no foreign keys, so a row whose endpoint is missing writes nothing and says so only in that count. `summary.counters` cannot serve as this check: a `MERGE` that matches an existing node or link reports zero created, exactly as one whose endpoint is missing does.
- **Strict types**: every function fully annotated, `mypy --strict` clean, no bare `Any`.
- **Layout by pipeline stage**: one module or subpackage per stage under `src/tracepath/` (extract, resolve, graph, traverse), with `cli.py` as the shell.
- **Validate settings at startup**: a missing or bad env var fails with a clear message before any work starts.
- **Docstrings** on every public module and function; one short line is enough.
- **Conventional commits**: `feat(extract): ...`, `fix(graph): ...`, `test(cli): ...`.
- **Standing rules from the scope**: no verification layer (the visible chain is the check). The eval stays small, a handful of questions and one script, never a harness or dashboard.
- **Paid calls only through the guards.** Any new paid model call goes through `tracepath extract` or `run_metered()` (`src/tracepath/extract/metered.py`), never `extract_once()` or a client of its own. `tests/test_spend_fence.py` (spec 0004 AC-72) fails on a file outside its allowlist that imports `anthropic` or names `build_client` or `extract_once`, and every test runs with a fake key and an unreachable API (AC-74).

## Tooling

Chosen here, installed by `/develop tooling`.

- **Lint + format**: Ruff. **Typecheck**: mypy `--strict`. **Before commit**: pre-commit hook runs all three.
- **Tests**: pytest, `tests/test_*.py`. Pure functions need no mocks. Integration tests run real Cypher against real Neo4j (docker compose locally, a service container in CI); never mock the driver.
- **CI**: GitHub Actions on push runs lint, format check, typecheck, and tests.
- **Config lives in**: `pyproject.toml` (Ruff, mypy, pytest markers), `.pre-commit-config.yaml` (runs the locked versions via `uv run`), `.github/workflows/ci.yml`.

## Git

- integration: on
- branch prefix: feat/
- commit: per-milestone

## Agent skills

- [neo4j-driver-python-skill](.agents/skills/neo4j-driver-python-skill/): `neo4j-contrib/neo4j-skills`, driver lifecycle, `execute_query`, transactions, result counters
- [neo4j-cypher-skill](.agents/skills/neo4j-cypher-skill/): `neo4j-contrib/neo4j-skills`, writing `MERGE` / multi hop `MATCH`. It targets Cypher 25; this project runs Neo4j 5.26, so use Cypher 5 syntax only
- [neo4j-modeling-skill](.agents/skills/neo4j-modeling-skill/): `neo4j-contrib/neo4j-skills`, labels vs relationships vs properties, constraints (data model spec)
- [typer-and-rich](.agents/skills/typer-and-rich/): `jamie-bitflight/claude_skills`, CLI wiring, stdout vs stderr, Rich output without a TTY
- [pydantic](.agents/skills/pydantic/): `pydantic/skills`, v2 models, constraints, JSON schema (the extraction schema)
- [uv](.agents/skills/uv/): `astral-sh/claude-code-plugins`, dependencies, lockfile, `uv run` / `uv tool install`
- claude-api: `anthropics/skills`, bundled with Claude Code (not in the project skills dir), Anthropic SDK and structured outputs

MCP servers: Neo4j MCP `neo4j/mcp` (recommended, connect once real Cypher work starts)
Declined: skills for Ruff, mypy, pytest, pre-commit

## Circuit breaker

If the same problem persists after one corrective prompt, stop and run /recover before trying again. It diagnoses an isolated bug (routes to /debug), a session gone wrong through repeated patching (hard reset), or a foundation resting on a wrong assumption (rethink). It pauses for confirmation before a hard reset or a rethink; a hard reset note goes to `docs/session-notes.md`.

## Standing rules

Read [docs/reflexes.md](docs/reflexes.md) before making changes: standing rules for how work is
done here, one line each, written by /reflex. A rule that has become a plain convention belongs in
this file instead; /reflex flags it and the engineer moves it.

- **Verify before you recommend.** When recommending anything about something that already exists, read it first and name what you read: a file, migration, config, or current behaviour in the repo, and the vendor's own docs for limits, terms, API shape, or version outside it. Mark each substantive claim verified (naming the file or source) or inferred, and when you cannot verify something that matters, say what you would need rather than filling the gap.
- **Confirm the specific action.** When beginning a multi step skill, confirm the engineer agreed to that specific action rather than to a summary or a suggestion in passing.
- **One claim per acceptance criterion.** When writing or reviewing an acceptance criterion, split it until it holds one independently falsifiable claim, and give a claim that relates two states its own criterion, because a test tagged with a criterion's number reads as covering all of it while proving only the clause easiest to observe, and a claim about how two states relate belongs to neither when tests are grouped one block per state. (added 2026 09 30, carried over from a sibling project where four acceptance criteria across three specs shipped with only their easiest clause tested)

## Context files

<!-- Nested AGENTS.md files are listed here as they are created -->

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
