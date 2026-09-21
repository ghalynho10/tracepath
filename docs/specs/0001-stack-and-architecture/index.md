# 0001. Stack and architecture

**Date**: 2026-09-21
**Status**: Accepted

## Summary

Tracepath will be a Python terminal tool. It stores the entities and relationships it extracts from the JobHunt spec corpus in a real Neo4j graph database (run locally in Docker), not an in memory Python structure. Claude, called through the Anthropic API with its native structured outputs feature layered on top of the already tested hand rolled validation pipeline, turns spec text into that graph. Typer and Rich give it a readable terminal command and output. Every other choice (packaging, secrets, logging, how the tool is invoked) follows plain, boring defaults sized to a one person, one week build. This spec is the foundation every later slice in the scope builds on.

## Decision

**Chosen option**: Option 1: Python, Neo4j, and Claude structured extraction

Build tracepath as a Python CLI backed by a locally run Neo4j graph database, extracting entities and relationships from the corpus with Claude's native structured outputs layered on the already tested validation pipeline in `reference/graphrag-pipeline`, and render traced chains with citations in the terminal using Typer and Rich.

**Implementation skills**: `neo4j-driver-python-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-driver-python-skill/`) · `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `claude-api` (`anthropics/skills`, already installed at `.agents/skills/claude-api/`, reference for the Anthropic API and its structured outputs feature)

## Proposed stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python | The one week timebox was sized for it, an agent writes the code either way, and it shares context with a Python course already in progress. Project pinned to Python 3.12 or later (the `neo4j` driver v6 requires at least 3.10). |
| Package manager | uv | Fastest current install and resolution, one tool instead of pip, venv and pyenv separately. |
| Graph store | Neo4j 5, Community edition, run in a single Docker container | Weighed against Neo4j Desktop and the AuraDB free tier, not assumed. Desktop's main case, a bundled Browser for visually inspecting the graph, is not actually exclusive to it: the standard Neo4j Docker image serves the same Browser on `localhost:7474` by default. Docker is one scriptable command (`docker compose up`), which fits a tool rebuilt across many `/develop` sessions better than a manually operated GUI app. AuraDB removes local infra entirely but adds a network dependency and off machine credentials for a corpus that fits Docker just as easily, a cost with no matching gain for a single user local tool. A uniqueness constraint on `canonical_id` per entity label is enforced by Neo4j itself, for free; `MERGE` is the idempotent upsert once a canonical id exists, not the mechanism that produces one (that resolution step belongs to the later name resolution spec). |
| Graph durability | Derived and disposable; rebuilt from the JSON run artifacts on demand | The run artifacts (below), not the running container, are the source of truth. One idempotent load command reconstructs the graph from them, so the container itself needs no backup strategy. |
| Graph access | The official `neo4j` Python driver, raw Cypher, with every write asserting its own result count | Keeps the Cypher visible and hand written, the project's stated learning goal. Neo4j has no foreign keys: a write whose pattern does not match both endpoints either writes nothing or creates a phantom node, so every write checks `neo4j`'s own write summary (e.g. `relationships_created`) and raises if it does not match what was intended. This is the write itself failing loudly, not a separate correctness auditing system, so it does not reopen the project's no verification layer rule; that rule bars a reconciliation or dashboard layer built on top of the visible chain, not a write failing fast at the moment it happens. |
| Extraction scope | Only each spec's `index.md`; `rationale.md` and `verify.md` are excluded from extraction | Confirmed by real testing, not assumed: none of the five real eval questions cite a `verify.md`. `rationale.md` needs a `Claim` entity type the current schema does not have yet (see Follow-up); extracting it now would force fit a claim into `Feature`, `Spec` or `AcceptanceCriterion`, the same misclassification failure already rejected for this project's extraction approach. |
| Extraction unit | One extraction call per top level `##` section, within that `index.md` scope | Left as a candidate, not a decision, in the handoff notes; decided here. Matches what the tested few shot examples were built against (AC-1's section), and sets the citation granularity below. |
| Extraction | Pydantic models, generated from the existing `entity.py` / `relationship.py` / `flags.py` enums, as the single source of truth; `model_json_schema()` is the schema forced on Claude's native structured outputs; `validate.py` is reduced to what a JSON schema cannot express (that a relationship's endpoints exist among that output's own entities), `compare.py`'s run to run comparison and the flag based review routing stay as tested | Resolves, rather than defers, how structured outputs and the existing hand rolled validator coexist: one schema, generated once, feeds both the model call and what little bespoke validation still matters. `run_bad.json` (an invented flag name) moves from a live path case to a `validate.py` regression fixture, since schema enforcement should prevent that class of error at generation time going forward. |
| Model & run policy | Claude Sonnet 5, temperature left at its default (not forced to zero), 3 runs per section, one retry on a failed or malformed run before routing to the review queue as a flagged failure | A smaller model raises the real, forward looking risk of missing this corpus's judgment heavy calls (the boundary decisions the tested pipeline's own flags exist to catch), not a documented past failure of a specific model. Temperature stays above zero because the tested run comparator's signal depends on real variation between the three runs; structured outputs constrain the JSON's shape without collapsing that variation. No hard cost ceiling: at the real extraction scope (21 `index.md` files, 188 top level sections, in `docs/specs` at `2e40bcf`), that is 188 × 3 = 564 calls total, still a negligible cost at Sonnet tier pricing, so a budget mechanism would be over building for what the project actually needs. |
| Citations | Each entity and relationship carries its source file path, section heading and the pinned corpus commit (`2e40bcf`), reusing the evidence span field the tested pipeline already produces | Citations are the tool's actual output; this names, in the foundation, what one is made of instead of leaving it to a later spec to invent. |
| CLI framework | Typer | Type hint based commands are fast to write for a single developer (plus agent) project. |
| Terminal output | Rich | Renders a traced chain and its citations as a readable tree or table, which is the actual thing this tool exists to show. |
| Pipeline artifact storage | JSON files on disk (one file per run, a review queue, a review log), each recording its model id, prompt/schema version, the corpus commit, the spec and section identifiers, and a timestamp | Matches the convention already tested in `reference/graphrag-pipeline/execution/runs/*.json`: human readable, git diffable, no extra dependency. The added fields let a later prompt change be told apart from a stable one. |
| Config and secrets | A `.env` file loaded with `python-dotenv` | `.gitignore` already excludes `.env` and keeps `.env.example`, so this is already set up. |
| CLI entry point | A packaged command via `pyproject.toml`'s `[project.scripts]` | Gives a real installed `tracepath` command (`uv tool install .`, or `uv run tracepath ...` while developing), the standard shape for a `uv` managed project. |
| Observability | Python's standard library `logging`, terminal only, behind a debug flag; a clear message (not a raw driver traceback) when Neo4j is unreachable at startup, pointing at `docker compose up` | Enough to trace a bad extraction run without building a dashboard or a file based log, which the project's own standing rule rules out. |

## Rationale

Reasoning and the options weighed: see [rationale.md](rationale.md).

## Consequences

**Positive**:
- Reuses the extraction pipeline already validated against this exact corpus, instead of re-deriving that work in a new form.
- A uniqueness constraint on `canonical_id` is enforced by Neo4j itself, and every write asserts its own result, so a bad write fails immediately instead of silently succeeding into a corrupt graph.
- The Cypher the project writes by hand (`MERGE` as the idempotent upsert, multi hop `MATCH` for traversal) directly serves the project's own stated learning goal.
- The graph is fully rebuildable from the JSON run artifacts, so nothing needs a backup strategy of its own.
- Pipeline artifacts (runs, review queue, review log) stay as plain JSON files, readable and diffable in git, matching the project's "the visible chain is the check" rule.
- Native structured outputs and `validate.py` share one generated schema instead of two hand maintained ones, closing the drift risk before it opens.

**Negative / tradeoffs**:
- Running Neo4j, even in one Docker container, is real operational weight beyond a pure Python only tool: something to start and stop, for a corpus (21 `index.md` files, 188 top level sections at `docs/specs`, pinned commit `2e40bcf`) that still fits comfortably in memory. This was a deliberate, informed choice (see rationale.md), weighed against Desktop and AuraDB too, not an oversight or an unexamined default.
- Every Cypher write now carries an explicit result assertion the code must write and maintain, rather than relying on a database level guarantee; a missed assertion on a new write path would silently reopen the exact failure this spec designed against.

**Neutral**:
- Adds Docker (or a local Neo4j install) as a new environment dependency, beyond Python itself.
- Two representations of the same data exist: the JSON run artifacts (the source of truth) and the Neo4j graph (a queryable projection rebuilt from them). They are not kept in sync by hand; rebuilding the graph is the one command that reconciles them.
- Real API volume: 188 sections times 3 runs is 564 extraction calls across the whole corpus, still cheap in absolute terms at this tier, but a real number, not "a few".

## Follow-up

- [ ] The Neo4j Cypher writing skill (`neo4j-cypher-skill`, same `neo4j-contrib/neo4j-skills` source as the driver skill just installed) was found but not installed; it covers `MERGE`, multi hop `MATCH` and query optimisation directly, worth adding once real Cypher writing starts.
- [ ] The `neo4j-mcp-skill` MCP server (live Neo4j access for the agent) was found but not connected; connecting it is a manual step in MCP settings, worth doing once the database is actually running.
- [ ] The Docker Compose file for Neo4j (Community image, ports, no persistent volume required since the graph is derived and rebuildable, default credentials sourced from `.env`) is scaffold work for `/develop`, not decided in this spec.
- [ ] Confirm the current name and status of Anthropic's native structured outputs feature at build time; it was under a beta header when this spec was researched, and that can change before `/develop` runs.
- [ ] Once the Pydantic models exist, verify their generated JSON schema still validates the existing fixtures in `reference/graphrag-pipeline/execution/runs/*.json` before the first real extraction run.
- [x] `reference/tracepath-for-scope.md` stated the corpus as 15 to 20 documents; corrected to the real count, 21 `index.md` files (188 top level sections) at the pinned commit `2e40bcf`, out of 63 total markdown files under `docs/specs`. `docs/scope/scope.md` itself never stated a count, so needed no fix.
- [ ] A `Claim` entity type, using the existing `CORRECTED_BY` relationship, is needed for the data model spec. This is a confirmed finding from testing, not speculative: investigating the Adzuna rate limit case showed an `index.md` asserting a claim as current that its `rationale.md` had already recorded as corrected. Not designed here; the data model spec (`/architect data model`) owns the type's actual shape.
