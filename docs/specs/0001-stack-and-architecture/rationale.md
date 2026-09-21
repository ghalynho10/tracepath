# Rationale: 0001. Stack and architecture

## Context

Tracepath needs a foundational stack before any code exists. The tool reads JobHunt's own specs, pinned at commit `2e40bcf`: 63 markdown files live under `docs/specs`, but the real extraction scope is narrower, the 21 `index.md` files only (188 top level `##` sections between them), since `rationale.md` and `verify.md` are excluded (see Proposed stack, Extraction scope). The project's own earlier notes had estimated 15 to 20 documents; both figures are corrected here, counted directly against that commit, see Follow-up. The tool extracts entities and typed relationships from that scope with an LLM, stores that graph, and answers a "why was this built this way" question by walking a multi hop chain across it and printing the answer with each link's citation to the terminal. There is one user, the author, and the build is timeboxed to about a week.

Several forces shape the choice more than the small scale suggests:

- **Identity resolution is the project's real risk, not the data volume.** The corpus names the same real thing several ways (by number, nickname, file name). A chain that silently breaks across two names for the same record is the specific failure this project exists to avoid, called out explicitly in the project's own scope notes before any code was written.
- **An extraction pipeline already exists and is already tested against this exact corpus.** `reference/graphrag-pipeline` has a working prompt, closed vocabulary enums for entity and relationship types, a validator, a run comparator for self consistency across repeated runs, and ID assignment logic, tested on real model output including one invalid run (`run_bad.json`, an invented flag name outside the closed vocabulary). A prior attempt with a general purpose extraction library (`LLMGraphTransformer`) failed on this same data: invented relationship types, dropped identifiers, non deterministic output, duplicate entities. That failure is documented, not assumed.
- **The one week timebox favors boring, fast to wire tools** over anything that adds its own learning curve before the actual problem (chain walking, identity resolution) gets attention.
- **This project doubles as an explicit, stated learning and resume goal**: writing real Cypher (`MERGE` for identity resolution, multi hop `MATCH` for traversal), not just building a tool. That is a real, non functional requirement alongside the functional ones, not a soft preference.
- **A standing project rule rules out building a verification layer or a dashboard.** "The visible chain is the check." Any storage or observability choice that requires its own correctness layer on top works against this rule; a choice that gets correctness enforcement for free (a database level constraint, a git diffable file) works with it.

What is not a driver here: concurrent users, write throughput, horizontal scale, or anything past a single local process reading a corpus that fits comfortably in memory. Naming that plainly matters, because it is exactly the kind of force that could otherwise justify tooling this project does not need.

## Options considered

### Option 1: Python, Neo4j, and Claude structured extraction (chosen)

Python throughout, Neo4j 5 Community as the graph store (run in one local Docker container, queried through the official driver with raw Cypher and a result assertion on every write), and Claude called through the Anthropic API, its native structured outputs enforcing the JSON schema in front of the already tested hand rolled validation pipeline.

**Pros**:
- Reuses tested, corpus proven extraction logic instead of rebuilding it.
- A uniqueness constraint on `canonical_id` per entity label is enforced by Neo4j itself, and `MERGE` is a proven, idempotent upsert once that canonical id exists (producing it, the name/nickname/file resolution itself, is a separate step for the later name resolution spec, not something `MERGE` does on its own).
- Every write asserts its own result count, so a write whose pattern does not match both endpoints (Neo4j has no foreign keys) fails loudly instead of silently writing nothing or creating a phantom node.
- Directly serves the stated Cypher learning and resume goal.

**Cons**:
- Running Neo4j, even in one container, is real operational weight (something to start and stop) for a corpus (21 `index.md` files, 188 sections) that still fits comfortably in memory.
- Every write carries an explicit, hand written assertion; a new write path that forgets it silently reopens the exact failure this option is chosen to prevent.

### Option 2: Python, NetworkX (in memory), and Claude structured extraction

The same extraction approach, but the graph lives in a Python `NetworkX` object in the running process, serialized to JSON or pickle between runs, with no database or container to manage.

**Pros**:
- Fewer moving parts: no server or container, one language, one process.
- `NetworkX` ships built in path and traversal algorithms, so multi hop chain walking is a library call rather than hand written Cypher.

**Cons**:
- Both the idempotent upsert `MERGE` gives for free and the uniqueness constraint Neo4j enforces on `canonical_id` would need to be hand written in Python, more code carrying the exact class of risk (the same thing quietly ending up as two different identities) this project is designed to avoid.
- Zero Cypher surface, so it does not serve the project's own stated learning goal at all.
- This was the engineer's explicit, considered call during the stack walk: the Neo4j versus Memgraph comparison in the reference notes already had real evidence behind it (Memgraph's in memory speed advantage does not matter at this scale), and the fact that Kuzu (the strongest embedded, in process alternative) was archived in October 2025 does not reopen that comparison or make the already chosen option wrong. The stated Cypher learning goal alone is sufficient to decide this without leaning on any integrity argument.

### Option 3: TypeScript, Neo4j, and OpenAI structured extraction

Same graph store, different language and model provider: TypeScript for the CLI, OpenAI's structured outputs feature instead of Anthropic's.

**Pros**:
- TypeScript has a large ecosystem and fast tooling for CLI development too.
- OpenAI's structured outputs are mature and widely used.

**Cons**:
- The one week timebox was sized around Python from the start, and switching languages does not shorten it since an agent writes the implementation either way.
- The existing tested prompt and few shot examples in `reference/graphrag-pipeline` read as written and validated against Claude; moving providers means re-validating that work rather than reusing it.
- Breaks continuity with the Python course the engineer already has in progress, a real but soft cost.

## Rationale

Option 1 wins on the project's own stated risk, not on general best practice, but the argument has to be stated precisely. Neo4j has no foreign keys and does not, by itself, refuse a relationship to a node that does not exist: an unmatched pattern either writes nothing or, with a bare `MERGE`, creates the missing node, which is silent corruption, not prevention. The two mechanisms that actually hold here are narrower and real: a uniqueness constraint on `canonical_id`, enforced by Neo4j itself with no code written, closes off one entity quietly becoming two rows; and `MERGE`, once a canonical id exists, is a proven, idempotent upsert, not a hand rolled one. What still has to be built is the write time assertion that a relationship's endpoints actually matched, in every write path. That is real code the project owns, not a database guarantee, and Option 2 was not dismissed for lacking it; it was dismissed because in Option 2, the uniqueness constraint and the upsert semantics would also have to be hand built, on top of the same write time check, which is strictly more hand written correctness logic carrying the same risk, not less.

That write time assertion does not reopen the project's "no verification layer" rule. The rule bars a separate reconciliation or dashboard system built on top of the visible chain, checking correctness after the fact; asserting that a single write did what it claimed, inside the same call that made it, is the write failing fast, the same category as checking an INSERT's affected row count. Nothing here audits the graph independently of the chain the tool prints; the assertion is part of producing that chain correctly the first time.

The Cypher learning and resume goal, stated directly by the engineer, is a real requirement here, not a tie breaker dressed up as one: it is explicit, and Option 2 offers nothing that serves it, sufficient on its own to decide against Option 2 even without the integrity argument above. Between Option 1 and Option 3, the deciding force is continuity: an already tested prompt and validation pipeline exist for this exact corpus on Claude, and there is no force in Context that makes TypeScript or OpenAI solve a problem Python and Claude do not already solve, so switching either would only cost re-validation with no offsetting gain.

How Neo4j runs was also weighed, not assumed. Neo4j Desktop's usual case, a bundled Browser for visually inspecting the graph, is not actually exclusive to it: the standard Neo4j Docker image serves the same Browser on `localhost:7474` by default, so that advantage does not distinguish the two. What does distinguish them is operability: Docker is one scriptable command, reproducible across the many `/develop` sessions this project will run; Desktop is a manually operated GUI application, harder to automate or tear down and recreate. AuraDB's free tier removes local infrastructure entirely but trades it for a network dependency and cloud held credentials, a cost with nothing to show for it, since the corpus (21 `index.md` files, 188 sections) runs just as easily in a local container. Docker wins on that comparison, made once here rather than assumed four times.

The operational cost conceded in Option 1's Cons, running a container for a corpus that fits in memory, is accepted deliberately: it buys a real, narrower set of guarantees (the uniqueness constraint, the idempotent upsert, the stated Cypher goal), not the referential integrity claim originally made for it, in exchange for a `docker compose up` and `down` a single developer runs by hand, with no backup burden since the graph is derived and rebuildable from the run artifacts (see Proposed stack, Graph durability).

## References

**Project sources** (verifiable, in this repo):
- `reference/tracepath-for-scope.md`, the original Neo4j versus Memgraph comparison and the "hand rolled extraction, not a library" leaning (basis for keeping the existing extraction pipeline and the graph database framing)
- `reference/HANDOFF.md` and `reference/graphrag-pipeline/` (the tested extraction pipeline: `entity.py`, `relationship.py`, `flags.py`, `validate.py`, `compare.py`, `assign_ids.py`, and the fixture runs including `run_bad.json`)
- `docs/scope/scope.md`, row 1 (Stack & architecture) and the corpus's known naming ambiguity risk noted under Foundations
- `github.com/ghalynho10/JobHunt` at commit `2e40bcf`, `docs/specs/`: 63 markdown files total, 21 `index.md` files (188 top level `##` sections) in this project's actual extraction scope, counted directly against that commit during this spec's write up

**Practices & standards**:
- A uniqueness constraint plus `MERGE` as an idempotent upsert, for entity resolution once a canonical id exists
- Asserting a write's own result at the point of the write, as the correctness mechanism instead of a database level guarantee Neo4j does not actually provide
- Defense in depth for structured output (schema enforcement at generation time, plus explicit validation and review routing downstream)

**Links** (web verified during the Stage (c) landscape check):
- Kuzu archived, October 2025: https://gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/
- Neo4j alternatives landscape, 2026: https://arcadedb.com/blog/neo4j-alternatives-in-2026-a-fair-look-at-the-open-source-options/
- Anthropic native structured outputs: https://platform.claude.com/docs/en/api/structured-outputs
- Instructor, Pydantic based structured extraction: https://python.useinstructor.com/
- Typer, alternatives comparison: https://typer.tiangolo.com/alternatives/
- Rich, terminal formatting: https://rich.readthedocs.io/
- uv adoption as the default Python package manager, 2026: https://dev.to/moksh/why-uv-became-the-go-to-python-package-manager-in-2026-2kag
