# Verify: data model · spec 0002 · updated 2026-09-24

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
- [x] Token usage → every artifact **the pipeline writes** carries `input_tokens` and `output_tokens` as integers, counting one attempt rather than a running total, so a run's cost is recoverable after the process exits. The 24 artifacts written before the field read back as null, meaning unmeasured, which spec 0001's artifact storage row now states explicitly → spec **0001** artifact storage (`tests/test_run_unit_usage.py`, `tests/test_artifacts.py`) · the blocker on this step is cleared: spec 0001 was amended 2026-09-23 to require the field of the pipeline rather than of files that predate it. Ready for `/check verify` to run and tick
- [x] `hold an unlocatable entity` → a derived entity whose `line` is null carries the reason `span_not_located` and never accepts on its signature's count. On the committed artifacts accepted entities stay at 71, queue rows stay at 403, and no accepted entity has a null `line`; 10 rows are newly labelled, 6 from `_entity_reasons()` and 4 from the leftovers branch → **AC-11d**, **AC-4** (`test_a_derived_entity_with_no_line_is_held_even_when_the_counts_agree`, mutation checked: removing the rule fails it)

## Artifact storage, built 2026-09-23

Each of these guards a way the cost or the held items could go missing again.

- [x] Usage counts one attempt, never a running total: a retried run writes the retry's own numbers, and the failed attempt's sit beside them rather than added into them → spec **0001** artifact storage (`test_a_retried_run_writes_both_attempts_with_their_own_numbers`)
- [x] A call that raises still produces an artifact, carrying its usage, its error and a null `output` → spec **0001** artifact storage (`test_a_call_that_raises_still_produces_an_artifact_carrying_its_usage`)
- [x] A failed attempt lands at `failed-run-N-attempt-M.json`, which the `run-*.json` glob does not match, so a rebuild never reads a failure as a fourth run and the three-runs-per-unit count stays true. Only the settled run takes `run-N.json` → spec **0001** artifact storage (`test_a_failed_attempt_is_not_read_back_as_a_fourth_run`)
- [x] A unit that fails after its retry hands its artifacts back through `UnitFailed` instead of losing them with the exception. This is the case that made the first 21 call run's cost unrecoverable → spec **0001** artifact storage (`test_a_unit_that_fails_after_its_retry_still_hands_back_its_artifacts`)
- [x] `uv run tracepath review-queue` rebuilds `artifacts/review-queue.json` from the committed artifacts alone, no API call and no graph, and the committed file matches what it produces → **AC-11c** (`test_the_committed_queue_matches_what_the_committed_artifacts_produce`)
- [x] The queue holds **both** kinds of held item: the ones routing holds inside a unit and the ones `resolve_accepted()` holds across units. Holding only the first would make AC-11c's promise true for 97 links and false for the one that crosses a unit boundary → **AC-7**, **AC-11c** (`test_a_cross_unit_held_link_is_not_lost_between_routing_and_resolution`)
- [x] The queue is byte stable from one rebuild to the next, so a file tracked in git does not reorder itself on every run → **AC-11** (`test_the_queue_is_stable_from_one_rebuild_to_the_next`)
- [x] `artifacts/review-log.json` is created once and never overwritten by a pipeline run. A run rules on nothing, so writing `[]` over a reviewer's work would erase it → **AC-11c** (`test_the_review_log_is_never_overwritten_by_a_later_run`)

## The label extension, AC-7 / AC-10 / AC-11(e), built 2026-09-23

Spec 0002 build plan tasks 16 and 17: a reference endpoint gains `label`, resolving to
a named but unnumbered item. Six matching rules, each with its own regression test; all
six ran clean tonight (2026-09-24) as part of the full suite.

- [x] Exact match: a `{record, label}` reference resolves to the unstruck entity in that
  record whose own `label` normalizes to the same string → **AC-7** (`test_a_labeled_reference_resolves_to_the_entity_carrying_that_label`, `test_a_labeled_reference_normalizes_before_matching`)
- [x] Held under `endpoint_not_accepted`, never `:Unresolved`: a labeled reference to an
  entity that exists but was held for review holds the whole link instead of guessing →
  **AC-7**, **AC-11c** (`test_a_labeled_reference_to_a_held_entity_holds_the_link_not_unresolved`)
- [x] `:Unresolved` on no match or a tie: no entity anywhere carries the label, or two
  unstruck entities share it, so the index excludes it and the reference falls through →
  **AC-7**, **AC-10** (`test_a_labeled_reference_with_no_match_becomes_unresolved_never_the_record`, `test_a_labeled_reference_with_no_matching_entity_at_all_becomes_unresolved`, `test_two_unstruck_entities_sharing_a_label_are_excluded_not_picked`)
- [x] `id` wins over `label`: both set, `id` resolves and `label` is never consulted →
  **AC-7** (`test_an_id_and_a_label_both_set_lets_id_win`)
- [x] `label` with no `record`: falls to `:Unresolved` like any other unnameable
  reference, not a special case → **AC-7** (`test_a_label_with_no_record_falls_to_unresolved_like_any_other_unnameable_reference`)
- [x] Struck exclusion: `build_label_index()` never offers a struck entity as a match
  target, only the current, unstruck version → **AC-7**, **AC-5** (`test_a_struck_entity_is_never_a_label_match_target`)

AC-10, the `:Unresolved` node carries what it knew, not only prose:

- [x] A held reference's `:Unresolved` node carries structured `record` and `label`,
  not only `mention`, both when named and when the record alone is missing → **AC-10**
  (`test_a_labeled_reference_with_no_match_becomes_unresolved_never_the_record`, `test_a_label_with_no_record_falls_to_unresolved_like_any_other_unnameable_reference`, `test_a_labeled_reference_with_no_matching_entity_at_all_becomes_unresolved`)

AC-11(e), the label joins both comparison signatures:

- [x] An entity's own `label`, normalized, joins its identity signature; two runs
  agreeing on everything else but differing only on `label` disagree → **AC-11e**
  (`test_a_labeled_entity_carries_its_label_in_the_signature`, `test_two_runs_agreeing_on_identity_but_differing_only_on_label_disagree`, `test_a_label_is_normalized_before_it_joins_the_signature`)
- [x] A `COLLAPSED` identity (unlocatable derived entity) stays exactly `COLLAPSED`
  whatever its `label`, so the label can never defeat AC-11(d)'s collapse rule →
  **AC-11e**, **AC-11d** (`test_an_unlocated_derived_entitys_label_does_not_defeat_the_collapsed_check`)
- [x] A reference endpoint's `label`, normalized, joins the relationship signature too →
  **AC-11e** (`test_a_reference_endpoints_label_joins_the_relationship_signature`)

- [ ] **Owed**: a successful label match against real model output. All six matching
  rules above are proven by unit tests on synthetic data, and the held/hold-not-guess
  path is separately proven live (below); none has been observed end to end against a
  real extraction, because no entity anywhere in the real corpus has ever written a
  `label` at all. [Experiment 0004](../../../experiments/0004-label-round-trip/README.md)
  found this with a real run against `0001 ## Binding rules` and `0008`'s `Preamble`
  ($1.0185, six calls): the reference side wrote `label: "binding rule 6"` stably three
  times, the entity side never wrote a `label` once. `/check verify` on 2026-09-24
  confirmed this still holds live: querying the graph after a full reload of every
  committed artifact found 0 `Entity` or `:Unresolved` nodes carrying `label`, and the
  committed review queue (464 rows) holds the `0008` reference under
  `endpoint_not_accepted`, the held path, never the match path. This is scoped to
  feature 12, not a defect here: the fix (an explicit entity-label instruction in
  `SYSTEM_PROMPT`, plus the worked examples already drafted under `examples/`) is
  feature 12's, and the exact-match rule cannot be marked verified against real data
  until it lands.

## Spends money (skip unless re-measuring)

- [ ] `uv run python experiments/0003-feature-design-testscenario/run.py` → about $0.66, three calls at `medium`. Expect `TestScenario` 16 / 16 / 16 against the 16 `**Critical test scenarios**` bullets in `0006 ## Feature design`, and no collapse to `unclassified` → **AC-14**

## Acceptance-criteria coverage

- **AC-1** schema is one frozen Pydantic set · unit tests + mypy
- **AC-2** unit splitting covers both file kinds byte for byte · `tests/test_extract_units.py`
- **AC-3** code owns identity, derived ids collapse for comparison · `tests/test_extract_identity.py`
- **AC-4** a line is located or null, never guessed · threshold re-derived over the corpus
- **AC-5** struck ranges come from the pre-check · `tests/test_extract_precheck.py`
- **AC-6** checkbox state comes from the pre-check · `tests/test_extract_precheck.py`
- **AC-7** no link dropped for an unnameable endpoint; a held endpoint is a different case · reload test; the `label` extension (six matching rules) · see "The label extension" above, exact-match still owed against real data
- **AC-9** one uniqueness constraint per node kind · integration tests
- **AC-10** the three uncertainties stay distinct, and holding is not a fourth · reload test; `:Unresolved`'s structured `record`/`label` · see "The label extension" above
- **AC-11** agreement rests on the stated signature; only accepted items are written · comparator tests + reload test; **(e)** `label` joins both signatures · see "The label extension" above
- **AC-12** the schema accepts the four valid fixtures and rejects the invalid one · `tests/test_extract_schema.py`
- **AC-13** every write asserts its counters · integration tests + reload test
- **AC-14** seven section kinds, all four new types exercised where they live · experiments 0001 and 0003
- **AC-8** history links point old to new · covered by the graph model tests; not re-exercised by this build
