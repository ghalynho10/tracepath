# Verify: held item view · spec 0005 · updated 2026-10-07
_Steps derived from spec 0005's acceptance criteria and its Value sourcing table. `/check verify` runs these; `/test` locks the durable ones. Every command is free: no extraction call, no API credit._

Run from the repository root with Neo4j up (`docker compose up -d`). The steps that load the real graph rewrite `artifacts/graph-build.json`; finish with a plain `uv run tracepath load` so the committed manifest comes back unchanged (`git diff artifacts/graph-build.json` shows nothing).

## Commands

### Default stays clean
- [x] `uv run tracepath load` → summary line, no held line; `artifacts/graph-build.json` has no `held_view` key → AC-5
- [x] In Neo4j Browser after that load: `MATCH (n) WHERE n.held IS NOT NULL RETURN count(n)` and `MATCH ()-[r]->() WHERE r.held IS NOT NULL RETURN count(r)` → both 0 → AC-1
- [x] Save `uv run tracepath trace 0012/AC-7` output; run `uv run tracepath load --with-held`; run `uv run tracepath trace 0012/AC-7` again → byte identical to the saved output, no `HELD:` → AC-3
- [x] Write a synthetic eval file to a scratch path (not an eval question: feature 6 holds the others out), `{"entries":[{"question":"Synthetic, not an eval question","trace":[{"record":"spec 0012 AC-7","file":"docs/specs/0012-model-client-router/index.md","line":26},{"record":"spec 0012 AC-3","file":"docs/specs/0012-model-client-router/index.md","line":22}]}]}`. Run `uv run tracepath trace --eval 1 --eval-file <that path>` after `load`, then again after `load --with-held` → byte identical, no `Held item view` line, no `held only` line, no `through held items` line, no `HELD:` → AC-4
- [x] Compare the accepted graph after `load` and after `load --with-held`: `MATCH (e:Entity) WHERE e.held IS NULL RETURN e.canonical_id, properties(e) ORDER BY e.canonical_id` and `MATCH (a)-[r]->(b) WHERE type(r) <> 'PART_OF' AND type(r) <> 'SPECIFIED_BY' AND r.held IS NULL RETURN type(r), a.canonical_id, b.canonical_id, properties(r) ORDER BY 1, 2, 3` → identical rows → AC-6

### The walk
- [x] `git diff 74e8406 -- src/tracepath/traverse/walk.py` → empty → AC-7
- [x] `uv run pytest tests/test_walk.py tests/test_walk_graph.py` → all pass, files unchanged since `74e8406` (`git diff 74e8406 -- tests/test_walk.py tests/test_walk_graph.py tests/trace_fixture.py tests/fixtures/trace-fixture-expected.txt` is empty) → AC-7b
- [x] `uv run pytest tests/test_held_walk.py -k ac_8` → the held walk over the 9003 fixture visits held `9003/AC-2`, follows a held link to `9003/AC-3`, and reaches accepted `9003/AC-4`, which the clean walk does not → AC-8

### Held steps print as held
- [x] `uv run pytest tests/test_held_walk.py -k "ac_9 or ac_10 or ac_11"` → the full print matches `tests/fixtures/held-fixture-expected.txt` → AC-9, AC-9b, AC-10, AC-11
- [x] On the real graph after `load --with-held`: `uv run tracepath trace 0002/AC-10 --with-held` → the start heading ends `HELD: known_trap_flag`; each held link line ends `HELD:` and its reasons in `name` or `name:detail` form; the line before `Prompt versions:` reads `Held: N steps, M links` → AC-9, AC-10, AC-11
- [x] `uv run pytest tests/test_held_report.py` → reached by the clean walk prints `reached` even with a held shortcut; an item only the held walk reaches prints `held only` with `via` and its held parts from the start; across records lines; the label and meaning lines → AC-12, AC-12b, AC-13, AC-14, AC-14b, AC-15, AC-16

### What `load --with-held` writes
- [x] `uv run tracepath load --with-held` → a line `Held item view (spec 0005), nothing accepted: …` naming held entities, links and unresolved written, entities and links skipped, and queue rows not written → AC-21b, AC-22b, AC-23b
- [x] `MATCH (e:Entity {held: true}) RETURN count(e), count(e.accepted_by)` → the first equals `held_view.entities` in `graph-build.json`, the second 0 → AC-17, AC-18
- [x] `MATCH (e:Entity {canonical_id: '0002/AC-10'}) RETURN e.held, e.held_reasons` → `true`, `["known_trap_flag"]` → AC-17 (value source: `ReviewItem.reasons`)
- [x] `MATCH (a)-[r {held: true}]->(b) RETURN count(r)` → equals `held_view.links`; `MATCH (:Entity {canonical_id: '0007/AC-13'})-[r:UNCLASSIFIED]->(b) RETURN b.canonical_id, labels(b), r.held_reasons` → `0002`, `["Record"]`, `["endpoint_not_accepted:0007/AC-13"]` → AC-19
- [x] `MATCH (u:Unresolved {held: true})-[r]-() WHERE r.held IS NULL RETURN count(r)` → 0 → AC-20
- [x] `MATCH (u:Unresolved) WHERE u.held IS NULL AND EXISTS { (u)-[h]-() WHERE h.held = true } RETURN count(u)` → more than 0, and each such node's properties are the same as after a plain `load` → AC-20b
- [x] `uv run pytest tests/test_held_view.py` → skipped ids and links, rows not written, the sum check, and `HeldViewIncomplete` on a link with no review item or no relationship → AC-19b, AC-21, AC-22, AC-22c, AC-23, AC-23c
- [x] `artifacts/graph-build.json` after `load --with-held` → `held_view` holds exactly `entities`, `links`, `unresolved`, `skipped_entities`, `skipped_links`, `not_written` → AC-24
- [x] Copy `artifacts/graph-build.json`, run `uv run tracepath load --with-held` again, `cmp` the two → identical → AC-25

### Trace with the flag
- [x] After a plain `uv run tracepath load`: `uv run tracepath trace 0012/AC-7 --with-held; echo $?` → exit 1, stderr names `tracepath load --with-held`, stdout empty → AC-26, AC-26b
- [x] After `uv run tracepath load --with-held`: `uv run tracepath trace --eval 3 --with-held` twice, `diff` the two → identical → AC-27

### The second result
- [x] `git log --oneline -- docs/specs/0005-held-item-view/index.md src/ experiments/0010-held-item-view/` → the spec commit (`74e8406`, with the prediction) comes before the code commit, which comes before the result commit → AC-28, AC-29
- [x] `experiments/0010-held-item-view/README.md` names the design, code and result commits in that order, and says it is a second result beside experiment 0009 → AC-29, AC-29b

## Value sourcing

- [x] A held entity's text, type, flags and ids: `MATCH (e:Entity {canonical_id: '0002#requirements:6'}) RETURN e.text, e.type, e.flags` → the run 1 entity of `0002 ## Requirements` in its committed run file
- [x] A held link's provenance, in a section holding both kinds of link: after `load --with-held`, `MATCH ()-[r]->() WHERE type(r) <> 'PART_OF' AND type(r) <> 'SPECIFIED_BY' AND r.file = 'specs/0002-deployment-and-environments/index.md' AND r.section = 'Feature design' RETURN coalesce(r.held, false) AS held, collect(DISTINCT [r.prompt_version, r.model, r.commit, r.line]) AS provenance, count(r) ORDER BY held` → two rows, accepted and held, with the same provenance (`0003.1`, `claude-sonnet-5`, `2e40bcf`, line 53)
- [x] Whether the graph was loaded with held items: `trace --with-held` succeeds after `load --with-held` and refuses after `load` (the read slice holds a held `:Entity` or `:Unresolved`, or not)
- [x] The clean chain under `--eval --with-held`: an item reached only through a held link never prints `reached`, so the clean chain is `drop_held()` over the same read
- [x] The held parts on a `held only` line: they follow `parent` back to the start in the printed chain; check one by reading the chain above the report

## Acceptance-criteria coverage

- AC-1: default load, Neo4j counts · AC-2: `test_held_walk.py` (`ac_2`) · AC-3: trace before and after `load --with-held` · AC-4: a synthetic question traced on a default and a held graph · AC-5: default load manifest and output · AC-6: accepted graph compared
- AC-7: `git diff` of `walk.py` · AC-7b: spec 0004 walk tests unchanged · AC-8: held fixture walk
- AC-9, AC-9b, AC-10, AC-11: held fixture print, real `trace 0002/AC-10 --with-held`
- AC-12, AC-12b, AC-13, AC-14, AC-14b, AC-15, AC-16: `test_held_report.py`
- AC-17, AC-18, AC-19, AC-20, AC-20b: Neo4j queries after `load --with-held` · AC-19b, AC-21, AC-22, AC-22c, AC-23, AC-23c: `test_held_view.py` · AC-21b, AC-22b, AC-23b: load output · AC-24, AC-25: manifest
- AC-26, AC-26b: refusal on a default graph · AC-27: eval 3 twice
- AC-28, AC-29, AC-29b: git order and the experiment 0010 record
