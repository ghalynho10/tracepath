# tracepath

A terminal tool that answers "why was this built this way?" by walking a chain across a project's decision records. Corpus: JobHunt's specs, pinned at commit `2e40bcf`.

## Stack

- **Language / Runtime**: Python 3.12+, managed by uv
- **CLI**: Typer (commands) + Rich (terminal output)
- **Graph store**: Neo4j 5 Community in one Docker container, official `neo4j` driver v6, raw hand written Cypher. The graph is derived and disposable: JSON run artifacts are the source of truth.
- **Extraction**: Claude Sonnet 5 via the Anthropic SDK, native structured outputs, Pydantic models as the single schema
- **Config**: `.env` loaded with `python-dotenv` (see `.env.example`)
- Full decision: [spec 0001](docs/specs/0001-stack-and-architecture/index.md)

## Build approach

**Tracer Bullet**: one thin, fully real thread through extract, resolve, store, and traverse; each later slice thickens one strand of that same thread.

## Commands

```bash
uv sync                          # install
docker compose up -d             # start Neo4j (Browser: http://localhost:7474)
uv run tracepath status          # run the CLI
uv run ruff check . && uv run ruff format --check .   # lint + format   (after /develop tooling)
uv run mypy                      # typecheck, strict                    (after /develop tooling)
uv run pytest                    # tests, needs Neo4j up for integration (after /develop tooling)
```

## Specs

Stored in `docs/specs/`. Format: `docs/specs/NNNN-title/index.md` (plus `rationale.md`, `verify.md`). Scope: `docs/scope/scope.md`.

## Rules

- **Functional core, imperative shell.** Pipeline steps (extract, resolve, traverse) are pure functions. Neo4j, the Claude API, files, and the clock live at the edges and are passed in, not reached for.
- **Immutable data.** Frozen dataclasses or frozen Pydantic models, tuples over lists in return values. Never mutate an argument. Module level names are constants only.
- **Uncertainty is a value, failure is an exception.** "Unresolved" and "unclassified" are real values in the model, never guessed away or dropped. Real failures raise typed exceptions (like `GraphUnavailable`); the CLI turns them into a clear message and exit code 1, never a raw traceback.
- **Every Cypher write asserts its own result** (`summary.counters`) and raises on mismatch. Neo4j has no foreign keys, so a missed check silently corrupts the graph.
- **Strict types**: every function fully annotated, `mypy --strict` clean, no bare `Any`.
- **Layout by pipeline stage**: one module or subpackage per stage under `src/tracepath/` (extract, resolve, graph, traverse), with `cli.py` as the shell.
- **Validate settings at startup**: a missing or bad env var fails with a clear message before any work starts.
- **Docstrings** on every public module and function; one short line is enough.
- **Conventional commits**: `feat(extract): ...`, `fix(graph): ...`, `test(cli): ...`.
- **Standing rules from the scope**: no verification layer (the visible chain is the check). The eval stays small, a handful of questions and one script, never a harness or dashboard.

## Tooling

Chosen here, installed by `/develop tooling`.

- **Lint + format**: Ruff. **Typecheck**: mypy `--strict`. **Before commit**: pre-commit hook runs all three.
- **Tests**: pytest, `tests/test_*.py`. Pure functions need no mocks. Integration tests run real Cypher against real Neo4j (docker compose locally, a service container in CI); never mock the driver.
- **CI**: GitHub Actions on push runs lint, format check, typecheck, and tests.

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

## Circuit breaker

If the same problem persists after one corrective prompt, stop and run /recover before trying again. It diagnoses an isolated bug (routes to /debug), a session gone wrong through repeated patching (hard reset), or a foundation resting on a wrong assumption (rethink). It pauses for confirmation before a hard reset or a rethink; a hard reset note goes to `docs/session-notes.md`.

## Context files

<!-- Nested AGENTS.md files are listed here as they are created -->

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
