# 0002. Data model for decision records

**Date**: 2026-09-22
**Status**: Proposed

## Summary

This spec settles what tracepath stores: the things it pulls out of JobHunt's decision records, the links between them, and the shape they take in Neo4j. There are three kinds of node. A **Record** is a whole document (a spec's `index.md`, the scope document, or one feature row inside it), created by code from the file tree. An **Entity** is one extracted item (an acceptance criterion, a constraint, a consequence, a follow up item, a build step, a test scenario, a capability, or `unclassified` when it fits none of those), extracted by the model. An **Unresolved** node stands in for a reference the code could not name, so a chain shows the gap instead of guessing. Links between them are typed (superseded by, corrected by, amended by, blocked by, verifies, satisfies) with `UNCLASSIFIED` as a real value that keeps the connecting words from the page. Two different kinds of doubt stay separate and visible: "I do not know what kind of thing this is" (an `unclassified` entity) and "I do not know which thing this points at" (an `Unresolved` node).

## Requirements

**User stories**:

- As the author, I want every item a chain passes through to keep its own citation (file, section, line, commit), so an answer can be checked against the record it came from.
- As the author, I want a reference the tool cannot resolve to appear in the chain as unresolved, so a chain never breaks quietly and never invents a target.
- As the author, I want a real link that fits none of the named types to be stored with the words that made it, so nothing is forced into the nearest type and nothing is dropped.
- As the author, I want the schema to survive the corpus as it really is (letter suffixed ids, struck text, revision notes above the first heading, references to scope features), so the first real extraction does not force a redesign.

**Acceptance criteria** (the contract, each criterion is independently checkable):

- **AC-1**: One set of frozen Pydantic models is the whole schema. It holds three closed enums: entity type (`Feature`, `Constraint`, `AcceptanceCriterion`, `Consequence`, `FollowUp`, `BuildStep`, `TestScenario`, `unclassified`), relationship type (`superseded-by`, `corrected-by`, `amended-by`, `blocked-by`, `verifies`, `satisfies`, `unclassified`), and the seven known trap flags. `model_json_schema()` is the only schema handed to the model call and the only one validation uses, so no second schema exists to drift.
- **AC-2**: An extraction unit is one of: a top level `##` section of a spec's `index.md`; the text above the first `##` in that file (the `Preamble` unit); one `### N.` feature row of `docs/scope/scope.md`; the text above the first `### N.` row inside a `##` section of that file (the `Intro` unit, which 5 of its sections carry: Slice 1, Slice 2, v1 extras, v1.5 and v2; Foundation has none); or one other `##` section of `docs/scope/scope.md`. Every byte of those files belongs to exactly one unit, so nothing is skipped without a record of it.
- **AC-3**: Only a token matching `AC-<digits><optional single lowercase letter>` is a verbatim id. Code qualifies it as `<record>/<id>` (`0008/AC-10b`). Every other entity gets a derived id `<record>#<section-slug>:<n>`; a section slug that repeats inside one record gets a numeric suffix. `n` follows each span's located start offset in the unit's source text, so `locate_line()` runs before `assign_ids()`. A span that cannot be located keeps the model's own output order, behind the located ones. **That fallback is not a stability guarantee**: an unlocatable span can take a different `n` in a different run, which is safe only because `compare_runs()` (AC-11) collapses every derived id to `<derived>` before comparing. The model writes only `derived:N` placeholders and never a slug, a qualified id, or a spec number.
- **AC-4**: Every entity carries its citation: file path, section heading, corpus commit, and `line`. `line` is located by code: the definition line for a verbatim id, otherwise the best deterministic text alignment above a stated threshold. Below that threshold `line` is `null`. It is never guessed and never approximated silently.
- **AC-5**: A deterministic pre-check, run before the model call, reports the character ranges of every `~~struck~~` span in a unit. An entity whose span falls inside a struck range is stored with `struck` true. Where one verbatim id carries both struck and unstruck text, the unstruck text keeps the verbatim id and the struck version takes a derived id. Whether something is struck never depends on the model noticing it.
- **AC-6**: A follow up item's checkbox (`- [x]` or `- [ ]`) is read by the same pre-check into `followup_status` (`done` or `open`), not by the model.
- **AC-7**: A relationship endpoint is either a local placeholder id (an entity in the same output) or a structured reference `{record, id, mention}`, where `mention` is the verbatim connecting text. Code resolves references after the whole corpus is loaded: `record` plus `id` becomes `<record>/<id>`, `record` alone becomes that Record, and anything that resolves to nothing becomes an `:Unresolved` node carrying `mention`. No relationship is dropped for having an endpoint that cannot be named.
- **AC-8**: Every history link is stored old to new: `(old)-[:SUPERSEDED_BY|:CORRECTED_BY|:AMENDED_BY]->(new)`. Finding the current version is always "follow outgoing history links until there are none".
- **AC-9**: The graph has one uniqueness constraint per node kind: `:Entity(canonical_id)`, `:Record(canonical_id)`, `:Unresolved(canonical_id)`. Every entity carries `:Entity` plus exactly one type label. Every entity is `PART_OF` exactly one Record. A `scope_feature` Record links `SPECIFIED_BY` to zero or more spec Records, read from its pointer line.
- **AC-10**: Both "not confident" values exist and are distinct in the stored graph. An entity whose kind fits none of the named types is typed `unclassified` and carries `unclassified_note`. A reference whose target cannot be named becomes an `:Unresolved` node holding the verbatim mention and its source record. A link whose type fits none of the named types is stored as `UNCLASSIFIED` with its verbatim `phrase`. None of the three is dropped, and none stands in for either of the others.
- **AC-11**: `compare_runs()` decides agreement on a stated signature and nothing else: per entity, the tuple (canonical id with every derived id collapsed to `<derived>`, type, sorted flags); per relationship, the tuple (type, from, to, same collapsing). Span text, rationale spans, citations and provenance are ignored, as the tested comparator ignores them; `struck` and `followup_status` are excluded because code sets them identically for all three runs. An item routes to review when the three runs disagree on that signature, when any known trap flag is present, or when the entity's type is `unclassified`. An `UNCLASSIFIED` relationship alone does not route to review; it enters the graph carrying its phrase, visible in the chain. Only accepted items are written to the graph.
- **AC-12**: The schema accepts the three agreeing fixture runs and the split run, and rejects the invalid one (the invented flag name). The fixtures live as fresh files under `tests/`; nothing in `src/` or `tests/` reads or imports from `reference/`.
- **AC-13**: Every Cypher write asserts its own result counters and raises on a mismatch, and every constraint is created with `IF NOT EXISTS` so a rebuild is idempotent.
- **AC-14**: Before the schema is treated as settled, a real extraction run under spec 0001's run policy (Claude Sonnet 5, three runs) covers at least: one `Consequences` section, one `Follow-up` section, one `Build plan` section, one section holding struck text, one `Preamble`, and one scope feature row. The new entity types come back stably across the three runs, or the disagreement is recorded and the vocabulary revisited before feature 5 builds on it.

## Decision

**Chosen option**: Option 1: One extraction schema, three node kinds, deterministic markers in code

Store each extracted item as an `:Entity` node carrying one type label and its own citation, group items under code created `:Record` nodes for the documents they came from, and keep every reference the code cannot name as an `:Unresolved` node so unresolved identity is a value in the graph rather than a dropped link.

**Implementation skills**: `pydantic` (`pydantic/skills`, `.agents/skills/pydantic/`) · `neo4j-modeling-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-modeling-skill/`) · `neo4j-cypher-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-cypher-skill/`) · `neo4j-driver-python-skill` (`neo4j-contrib/neo4j-skills`, `.agents/skills/neo4j-driver-python-skill/`) · `claude-api` (`anthropics/skills`, bundled with Claude Code)

## Rationale

Reasoning, the options weighed, the corpus spike and its six hand runs: see [rationale.md](rationale.md).

## Feature design

**Data model sketch**

`:Record`, one per document, created by code, never by the model.

| Property | Type | Required | Notes |
|---|---|---|---|
| `canonical_id` | str | yes | `0012` for a spec, `scope` for the scope document, `feature-21` for a feature row. Unique across all Records. |
| `kind` | str | yes | One of `spec`, `scope_document`, `scope_feature`. New kinds (a `rationale` document) are added here without touching existing nodes. |
| `title` | str | yes | The document's own heading text. |
| `status` | str \| null | no | Parsed from `**Status**:` for a spec, from the row heading for a feature row (`done`, `needs a decision`). |
| `path` | str | yes | Repository relative path inside the snapshot. |
| `commit` | str | yes | The pinned corpus commit, `2e40bcf`. |
| `aliases` | list[str] | yes | Every name the corpus uses for this record: the number, the title, the directory slug, and for a feature row the `feature N` form. This is what carries "the same thing named several ways" until name resolution (feature 7) does the matching. |

`:Entity`, one per extracted item, always carrying `:Entity` plus one type label.

| Property | Type | Required | Notes |
|---|---|---|---|
| `canonical_id` | str | yes | `0008/AC-10b` (verbatim) or `0012#build-plan:2` (derived). Unique across all entities. |
| `type` | enum | yes | `Feature`, `Constraint`, `AcceptanceCriterion`, `Consequence`, `FollowUp`, `BuildStep`, `TestScenario`, `unclassified`. Also the node's second label. |
| `text` | str | yes | The span the model kept. |
| `rationale` | list[str] | yes | The spans the deletion trick removed, kept because they are the "because" text a why answer shows. Empty list when there are none. |
| `flags` | list[str] | yes | Known trap flags from the closed set of seven, carried over unchanged from the tested pipeline: `rationale_boundary_call` (was a clause rationale to drop or load bearing to keep), `multi_condition_split` (was a multi condition sentence one item or several), `implicit_feature_inferred` (a capability inferred from implication, not an announcing sentence), `embedded_second_claim` (a clause that looked like rationale but hid its own testable claim), `relationship_type_ambiguous` (which link type applied was not obvious), `entity_type_ambiguous` (the item fits no named type and went to `unclassified`; only ever set on an `unclassified` entity), `granularity_boundary_call` (choosing between named types was a close call). Empty list when there are none. |
| `unclassified_note` | str \| null | no | Required when `type` is `unclassified`, null otherwise. |
| `id_source` | str | yes | `verbatim` or `derived`. |
| `label` | str \| null | no | The author's own label for an unnumbered item (`binding rule 6`, `key invariant 1`), verbatim. Name resolution reads this. |
| `struck` | bool | yes | Set from the pre-check's character ranges (AC-5), never by the model. |
| `followup_status` | str \| null | no | `open` or `done` for a `FollowUp`, null otherwise. Parsed from the checkbox. |
| `file`, `section`, `line`, `commit` | str, str, int \| null, str | yes except `line` | The citation. `line` is null when it cannot be located (AC-4). |
| `model`, `prompt_version`, `extracted_at`, `accepted_by` | str, str, str, str | yes | Provenance. `accepted_by` is `auto` or `review`. |

`:Unresolved`, one per reference the code could not name.

| Property | Type | Required | Notes |
|---|---|---|---|
| `canonical_id` | str | yes | `unresolved:<source record>:<slug of mention>`. Scoped to the source record on purpose: the same words can mean different things in different documents. |
| `mention` | str | yes | The verbatim reference text (`binding rule 6`). |
| `source_record` | str | yes | The record whose text made the reference. |
| `file`, `section`, `line` | str, str, int \| null | yes except `line` | Where the reference was written. |

**Relationships**

| Type | From → To | Cardinality | Properties |
|---|---|---|---|
| `PART_OF` | Entity → Record, and scope_feature Record → scope_document Record | N:1 | none |
| `SPECIFIED_BY` | Record (`scope_feature`) → Record (`spec`) | 1:N, and absent when the row cites no spec | `source_line` |
| `SUPERSEDED_BY` | old → new | N:M | `phrase`, `date`, `flags`, citation |
| `CORRECTED_BY` | old → new | N:M | same |
| `AMENDED_BY` | amended → amending | N:M | same |
| `BLOCKED_BY` | blocked → blocker | N:M | same |
| `VERIFIES` | TestScenario → AcceptanceCriterion | N:M | same |
| `SATISFIES` | BuildStep → AcceptanceCriterion | N:M | same |
| `UNCLASSIFIED` | as the text reads | N:M | same, and `phrase` is required |

Every relationship endpoint may be an Entity, a Record, or an Unresolved node. History links always point old to new (AC-8).

**State transitions**

An entity has no lifecycle of its own; the graph is rebuilt from the JSON run artifacts (spec 0001). The one ordered thing is the pipeline: `unit → pre-check → three model runs → validate → compare → assign ids → accepted or review → load`. Only accepted items reach the graph.

**API surface**

This feature ships no terminal command. Its surface is the Pydantic models plus pure functions, with the Neo4j writes at the edge, matching the functional core rule in `AGENTS.md`.

| Surface | Kind | Key inputs | Key outputs | Auth | Key errors |
|---|---|---|---|---|---|
| `ExtractionOutput` (Pydantic) | schema | the model's JSON | frozen models, closed enums | n/a | `ValidationError` on a value outside a closed enum or a malformed endpoint |
| `split_units(path, text)` | pure | a file's path and text | ordered units (`Preamble`, `##` sections, scope rows) | n/a | raises when a unit cannot be attributed to a record |
| `mark_struck(text)` / `read_checkbox(text)` | pure | a unit's text | struck character ranges, `open`/`done` | n/a | none, a unit with no marker returns empty |
| `locate_line(unit, span)` | pure | a unit and a span | a start offset and line number, or `None` | n/a | none, below threshold returns `None` |
| `compare_runs(outputs)` | pure | the three validated outputs for one unit | agree or disagree, plus the differing signatures | n/a | raises when fewer than two outputs are given |
| `assign_ids(output, record, section)` | pure | one validated output, with spans already located | the same output with canonical ids | n/a | raises on a `derived:N` placeholder that no entity carries |
| `resolve_endpoints(outputs)` | pure | every accepted output | resolved links plus Unresolved nodes | n/a | none, an unresolvable reference is a value |
| `load(driver, records, entities, links)` | effect | the resolved graph | write counters | local Neo4j | `GraphUnavailable`, and a raise when a counter does not match |

**Value sourcing**

| Action | Value produced or displayed | Source |
|---|---|---|
| build a Record | `canonical_id`, `kind`, `path` | the file path inside the snapshot, and the `### N.` heading for a feature row; never the model |
| build a Record | `status` | the `**Status**:` line of a spec, or the row heading's own status word |
| build a Record | `aliases` | the record number, the title text, the directory slug, and `feature N` for a row; all parsed, never inferred |
| link a feature row to its spec | `SPECIFIED_BY` | the row's pointer line `_spec [NNNN](...)_`, parsed by code. 15 of 33 rows carry one at `2e40bcf`, so a row with none simply has no link |
| extract a unit | `type`, `text`, `rationale`, `flags`, `unclassified_note`, `label` | the model call, constrained by the generated JSON schema |
| extract a unit | `struck`, `followup_status` | the deterministic pre-check, never the model |
| assign an id | `canonical_id` | code: the verbatim `AC-N[a-z]` token qualified by the record, else `<record>#<section-slug>:<n>` |
| cite an item | `file`, `section`, `commit` | the unit the call was made from, and the pinned commit from `SNAPSHOT.md` |
| cite an item | `line` | code: the definition line of a verbatim id, else deterministic text alignment above the threshold, else `null` |
| resolve a link | endpoint `canonical_id` | code, from `{record, id}` after the whole corpus loads; otherwise an `:Unresolved` node built from `mention` |
| store a link | `phrase` | the model's verbatim connecting text, required for `UNCLASSIFIED` |
| assign an id | the derived ordinal `n` | the span's located start offset in the unit, and the model's output order only for spans that could not be located |
| decide agreement | agree or disagree across the three runs | `compare_runs()`'s signature (AC-11), never span text or citations |
| accept an item | `accepted_by` | `auto` when no review trigger fired, `review` when a person ruled on it |
| record provenance | `model`, `prompt_version`, `extracted_at` | the run artifact's own header (spec 0001's artifact fields) |

**Key invariants**

1. `canonical_id` is unique across every entity, enforced by Neo4j, not by the loader.
2. Every entity belongs to exactly one Record, and that Record exists before the entity is written.
3. The model never writes a final id and never writes a qualified one. Code owns identity.
4. `struck` and `followup_status` come from deterministic parsing only.
5. A reference that cannot be named becomes a node, never a dropped link and never a guessed target.
6. A relationship whose type fits none of the named types keeps the words that made it.
7. History links point old to new, without exception.
8. Uncertainty has three separate homes: `unclassified` type (kind unknown), `:Unresolved` node (identity unknown), `UNCLASSIFIED` link (link kind unknown). None is a substitute for another.
9. Nothing under `src/` or `tests/` reads `reference/`.

**Security model**

No new surface. One local user, a local Neo4j in Docker, a read only corpus snapshot, and the Anthropic key already governed by spec 0001. The corpus is public project documentation, so no personal data enters the graph.

**Configuration required**

None beyond spec 0001's `.env` (`NEO4J_*`, the Anthropic key).

**Critical test scenarios**

- Happy path: one `## Requirements` section of a real spec runs pre-check, model call, validation, id assignment and load, and the stored entity carries its citation and reaches its record, verifies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-9**.
- Struck text: 0021's `AC-2`, which holds a struck old version and a struck fragment inside its replacement, yields an unstruck entity keeping `0021/AC-2` and a struck entity with a derived id, linked `SUPERSEDED_BY`, verifies **AC-5**, **AC-8**.
- Template sections: a `Consequences`, a `Follow-up` and a `Build plan` section return `Consequence`, `FollowUp` and `BuildStep` entities, with checkbox state parsed in code, verifies **AC-6**, **AC-14**.
- Cross record link: 0012's build step 2 (`satisfies AC-8`, `blocked until feature 10`) resolves `SATISFIES` to `0012/AC-8` and `BLOCKED_BY` to a record or an Unresolved node, verifies **AC-7**.
- Unresolvable reference: 0008's preamble, which names `spec 0001's binding rule 6` and produces no local entities, yields links whose endpoint is an `:Unresolved` node holding the verbatim mention, verifies **AC-7**, **AC-10**.
- Failure case: the fixture run with the invented flag name is rejected by the schema, and a write whose counters do not match raises rather than returning, verifies **AC-12**, **AC-13**.
- Review routing: an `unclassified` entity routes to review and stays out of the graph until ruled on, while an `UNCLASSIFIED` link with its phrase is written straight through, verifies **AC-10**, **AC-11**.

## Build plan

Tracer Bullet: one section goes all the way through first, then the thread widens to the section kinds and the markers the corpus actually contains. The graph is derived and rebuildable (spec 0001), so the constraints land with the first load rather than as a separate migration.

1. Write the Pydantic models and the three closed enums, fresh under `src/tracepath/extract/`, and generate the JSON schema from them, satisfies **AC-1**.
2. Copy the five fixture runs into `tests/fixtures/` as fresh files and assert the generated schema accepts the four valid ones and rejects the invented flag name, satisfies **AC-12**.
3. Write `split_units()` for a spec `index.md` (preamble plus `##` sections) with the byte coverage check, satisfies **AC-2**.
4. Write the deterministic pre-check: struck character ranges and checkbox state, satisfies **AC-5**, **AC-6**.
5. Write `locate_line()` with its stated threshold, then `assign_ids()` on top of it (verbatim `AC-N[a-z]` qualification, derived ids numbered by located start offset, repeated slug suffixes), satisfies **AC-3**, **AC-4**.
5a. Write `compare_runs()` fresh under `src/`, with the signature rule in AC-11, and test it against the four valid fixtures plus the split run, which must read as a disagreement, satisfies **AC-11**, **AC-12**.
6. Write the graph schema and loader: constraints with `IF NOT EXISTS`, `MERGE` upserts, and a counter assertion on every write, satisfies **AC-9**, **AC-13**.
7. Run the thin thread end to end on one `## Requirements` section under spec 0001's run policy and load it, satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-9**.
8. Write `resolve_endpoints()` with the `:Unresolved` fallback, and the review routing rules, satisfies **AC-7**, **AC-10**, **AC-11**.
9. Widen `split_units()` to `docs/scope/scope.md` (feature rows and other sections), with alias building and `SPECIFIED_BY` from the pointer line, satisfies **AC-2**, **AC-9**.
10. Run the widened thread over the spike's six section kinds and record whether the new types come back stably across three runs, satisfies **AC-14**.

## Consequences

**Positive**:

- Uncertainty is visible in three separate, queryable forms rather than collapsed into one word, which is what the scope asked for and what keeps a chain honest.
- Identity stays in code. The model never writes an id, so two runs of the same section produce the same ids and the run comparator keeps working.
- The named template types keep `unclassified` rare. Under HANDOFF's rules about 837 items (roughly 280 consequences, 185 follow ups, 206 build steps, 166 test scenarios) would have been unclassified and all routed to review, against 325 acceptance criteria.
- New record kinds (rationale documents) and new entity types (an Alternative) are additive: a new `kind` value or enum value, with no restructuring of existing nodes.
- Citations carry a line, so a chain link lands where the eval's own traces land.

**Negative / tradeoffs**:

- Extraction stays limited to `index.md`, the preamble and the scope document. "Why not X" questions are therefore unanswerable, and that is not a small corner: in a census of 20 self picked questions across four specs, 9 needed `rationale.md`, and every one of them asked about a rejected alternative. Correction narratives that live only in `rationale.md` are invisible too.
- Worse than silence: an `index.md` can state a reason its own `rationale.md` calls false. Spec 0014's index line 68 lists `redirect` among the triggers that re-render `/search`; its rationale line 102 says that is exactly the wrong reason, because `redirect()` streams the destination instead. With `rationale.md` out of scope, tracepath can present that reason as current with nothing contradicting it.
- Four new entity types reverse a rule the tested prompt states plainly (`solutions.xml` line 32: "Consequences and Follow-up items are not requirements: use unclassified"). The tested few shot examples do not cover them, so AC-14's run is a real gate, not a formality.
- A `Feature` entity (a capability claim written inside a record) is never linked to the `scope_feature` Record covering the same capability, unless the text names the row. Matching them is deferred to name resolution (feature 7); until then the two live side by side unconnected.
- Neo4j Community enforces only uniqueness. Required properties, property types and composite keys are all Enterprise features, so every other guarantee rests on the loader's own assertions.
- `line` is best effort by design. A span is not a verbatim substring of the source (the model drops rationale clauses mid sentence), so some citations will carry `null`.

**Neutral**:

- The vocabulary is now larger than HANDOFF's: eight entity types against four, seven relationship types against five. The prompt and its few shot examples must be rewritten from the enums rather than reused as they are.
- Three node kinds mean three uniqueness constraints and three write paths in the loader.
- `rationale` spans are stored on the node as a list, so nodes are wider than the tested pipeline's output.

## Follow-up

- [x] **Enrolled 2026-09-22 as scope feature 10** (Slice 6, Rationale extraction and alternatives): rationale.md extraction with an `Alternative` entity type, designed against real `## Options considered` sections. Two limits to record on that row: outcomes are not only chosen or rejected (spec 0012's rationale says "Anthropic is parked, not rejected"), and `Alternative` answers "why OpenAI over Anthropic" but not "what was the decision before, and why did it change" (0012's vendor pick was re-decided in place on 2026-09-06 and the old version is kept nowhere else). That second shape stays open alongside a `Claim` type.
- [ ] `granularity_boundary_call`'s definition still names Feature, Spec and AcceptanceCriterion. Widen it to any named type when the prompt is rewritten; `entity_type_ambiguous` stays tied to an `unclassified` entity.
- [ ] Candidate relationship types seen in the spike's escape valve, for promotion only on real run evidence: `resolved-by` (a follow up closed by a later spec's criterion, 0003 Follow-up line 274), and a "reuses or seeds" shape (0019 Consequences, "spec 0012 already seeded `ai_check`").
- [ ] Partial supersession exists in the corpus ("Superseded for `ai_check` by spec 0019 AC-6", 0012 build step 3). The schema stores the verbatim phrase and no partial semantics; history aware traversal (feature 8) decides what to do with it.
- [ ] `line` needs its alignment threshold fixed by measurement during the build (exact match first, then deterministic alignment such as `difflib.SequenceMatcher` or `rapidfuzz` partial ratio). No embedding or vector search: near identical criterion wording recurs across specs, so a nearest neighbour hit would return a confident wrong line, which is worse than `null`.
- [ ] Spec 0001 is amended by this spec at lines 24, 27, 28, 29, 31 and its follow up items 68 and 70. If a later spec widens extraction again, amend it there too rather than letting the two drift.
