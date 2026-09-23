# Verify: data model · spec 0002 · updated 2026-09-23

_Steps derived from spec 0002 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

Every step here runs without an API call. The run artifacts under `artifacts/runs/` are
the source of truth for a rebuild (spec 0001), so the whole pipeline below re-runs from
committed data. Only the last section spends money, and it is marked.

## Commands

- [x] `uv run pytest -m "not integration"` → all pass, no API key needed → **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-5**, **AC-6**, **AC-11**, **AC-12**
- [x] `docker compose up -d` then `uv run pytest` → all pass, integration included → **AC-9**, **AC-13**
- [x] `uv run pytest tests/test_reload_artifacts.py` → the full load completes from the committed artifacts and no counter mismatch is raised. This is the regression test for `UNCLASSIFIED links: asked to write 7 but the database wrote 2` → **AC-7**, **AC-11**, **AC-13**
- [x] `uv run mypy` → clean, strict → **AC-1**
- [x] `uv run ruff check . && uv run ruff format --check .` → clean

## The amended rules, each with the regression it guards

These are the ones most likely to be "simplified" back into bugs, so each names what
breaks if it is undone.

- [x] Flags are not in the agreement signature: three runs agreeing on located line and type read as agreeing however the flags move, and a flagged item still routes to review on its own trigger. Undoing this makes agreement measure flagging volume, and marks *unflagged* neighbours as disagreements → **AC-11a** (`test_flag_churn_alone_no_longer_breaks_agreement`)
- [x] A derived entity is identified by its located line, not by `<derived>`: `entity_signature()` on a located derived entity returns `("line:N", type)`. Undoing this collapses every derived entity of one type onto one signature, so three runs could extract fifteen different spans and read as full agreement → **AC-11a** (`test_a_derived_entity_is_identified_by_its_located_line`)
- [x] `<derived>` survives only for an unlocatable span → **AC-11a**, **AC-4** (`test_a_derived_entity_whose_span_cannot_be_located_collapses`)
- [x] Runs are compared by count, and a count that differs holds **every** copy, not just the surplus. Accepting the first `min(counts)` asserts a correspondence the runs never established → **AC-11b** (`test_a_count_that_differs_holds_every_copy_not_just_the_surplus`)
- [x] A link whose endpoint entity was not accepted is held, never written and never turned into an `:Unresolved` node. An `:Unresolved` node here would draw a gap in the chain that does not exist, breaking **AC-10** and key invariant 8 → **AC-7**, **AC-11c** (`test_a_link_pointing_at_a_held_entity_is_held_too`)
- [x] Holding is decided before resolution: no link reaching `resolve_endpoints()` has a held endpoint, and its `known_entities` is the accepted set → **AC-7**, **AC-11c** (`test_no_accepted_link_points_at_an_entity_that_was_not_accepted`)

## Value sourcing, one step per amended row

- [x] `decide agreement` → the signature is `(line or verbatim id, type)`, flags absent, compared as counts. Check a real unit: `0012 Consequences` gives entity counts 15 / 16 / 15 and therefore disagrees on count, not on flag churn → **AC-11**
- [x] `hold a link` → a held link's queue row carries `reasons[].name == "endpoint_not_accepted"` and a `detail` naming the entity it waits on. A reviewer can read which entity to rule on first → **AC-11c**
- [x] Review queue entry shape → an entity row carries a non null `canonical_id` and its `line`; a relationship row carries `canonical_id: null` and is identified by its `signature`. Rows are ordered by lowest located offset → **AC-11**
- [x] `extract a unit` → `effort` in every run artifact reads `medium`, never null and never `high`. Unset used to fall through to the model's own default, `high`, which is how the first runs measured the wrong configuration → spec **0001** run policy
- [ ] Token usage → every run artifact carries `input_tokens` and `output_tokens` as integers, per attempt, so a run's cost is recoverable after the process exits → spec **0001** artifact storage

## Spends money (skip unless re-measuring)

- [ ] `uv run python experiments/0003-feature-design-testscenario/run.py` → about $0.66, three calls at `medium`. Expect `TestScenario` 16 / 16 / 16 against the 16 `**Critical test scenarios**` bullets in `0006 ## Feature design`, and no collapse to `unclassified` → **AC-14**

## Acceptance-criteria coverage

- **AC-1** schema is one frozen Pydantic set · unit tests + mypy
- **AC-2** unit splitting covers both file kinds byte for byte · `tests/test_extract_units.py`
- **AC-3** code owns identity, derived ids collapse for comparison · `tests/test_extract_identity.py`
- **AC-4** a line is located or null, never guessed · threshold re-derived over the corpus
- **AC-5** struck ranges come from the pre-check · `tests/test_extract_precheck.py`
- **AC-6** checkbox state comes from the pre-check · `tests/test_extract_precheck.py`
- **AC-7** no link dropped for an unnameable endpoint; a held endpoint is a different case · reload test
- **AC-9** one uniqueness constraint per node kind · integration tests
- **AC-10** the three uncertainties stay distinct, and holding is not a fourth · reload test
- **AC-11** agreement rests on the stated signature; only accepted items are written · comparator tests + reload test
- **AC-12** the schema accepts the four valid fixtures and rejects the invalid one · `tests/test_extract_schema.py`
- **AC-13** every write asserts its counters · integration tests + reload test
- **AC-14** seven section kinds, all four new types exercised where they live · experiments 0001 and 0003
- **AC-8** history links point old to new · covered by the graph model tests; not re-exercised by this build
