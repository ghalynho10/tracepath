# Verify: Stack & architecture · spec 0001 · updated 2026-09-21
_Steps derived from the scope's Done when line ("the empty project installs and runs one command from the terminal") and the spec's Proposed stack rows. Spec 0001 is a decision spec with no `AC-N` list. `/check verify` runs these; `/test` locks the durable ones._

## Commands
- [x] Fresh clone, `cp .env.example .env`, set `NEO4J_PASSWORD`, then `uv sync` → installs with no errors on Python 3.12 or later → Done when (installs)
- [x] `uv run tracepath --version` → prints `tracepath 0.1.0`, exit 0 → Done when (runs one command); CLI entry point row
- [x] `docker compose up -d`, wait for startup, then `uv run tracepath status` → green check with the Neo4j 5 version and `bolt://localhost:7687`, exit 0 → Done when; Graph store row
- [x] `docker compose down`, then `uv run tracepath status` → red cross, message names the URI and says to run `docker compose up -d`, exit 1, no Python traceback → Observability row
- [x] Neo4j running, `NEO4J_PASSWORD=wrongpassword uv run tracepath status` → credentials message pointing at `.env`, exit 1, no traceback → Config and secrets row
- [x] `.env` without `NEO4J_PASSWORD`, then `docker compose up -d` → compose refuses with "set NEO4J_PASSWORD in .env" → Config and secrets row
- [x] `uv run tracepath --debug status` → one `DEBUG tracepath.graph` line, no Neo4j driver wire protocol lines → Observability row

## Coverage
- Done when, installs: step 1 · runs one command: steps 2 and 3
- Proposed stack rows: Graph store (3), CLI entry point (2), Observability (4, 7), Config and secrets (5, 6)
