# tracepath

A terminal tool that answers "why was this built this way?" from a project's own decision records, by walking a chain across records.

## Setup

Needs Python 3.12 or later, [uv](https://docs.astral.sh/uv/), and Docker.

```sh
cp .env.example .env        # then set NEO4J_PASSWORD (8 characters or more)
docker compose up -d        # Neo4j 5; Browser at http://localhost:7474
uv sync
uv run tracepath status     # checks that Neo4j is reachable
```

The graph holds no state of its own. It is rebuilt from the JSON run artifacts, so the container has no volume and can be thrown away.

Add `--debug` before any command for debug logging, e.g. `uv run tracepath --debug status`.
