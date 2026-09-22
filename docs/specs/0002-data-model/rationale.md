# 0002. Data model for decision records, rationale

The decision record behind [index.md](index.md). A build never needs to load this.

## Context

> ⚠️ Premise note: this spec settles the data model while extraction stays inside `index.md`, so tracepath will answer "why is it this way" and not "why not the other way". The census below found that 9 of 20 plausible questions across four specs need `rationale.md`, and every one of those asked about a rejected alternative. The failure mode is not silence. Spec 0014's `index.md` states a reason its own `rationale.md` calls false, so the tool can present a wrong reason as current with nothing in the graph to contradict it. The right framing is to ship the narrower model now and enroll rationale extraction with an `Alternative` type as its own feature, which is what the Follow-up does, rather than to widen the vocabulary here against text the spike has not tested.

Tracepath answers "why was this built this way?" by walking a chain across JobHunt's own decision records, pinned at commit `2e40bcf`. Spec 0001 settled the stack: Python, a local Neo4j in Docker, Claude with native structured outputs, Pydantic models as the single schema, and JSON run artifacts as the source of truth from which the graph is rebuilt. What 0001 left for this spec is the shape of what gets stored: what counts as a thing, what counts as a link, and what happens when either is uncertain.

Three forces shape the answer.

**The corpus is not what the prior work was tested against.** The pipeline in `reference/graphrag-pipeline/` and the prompt in `reference/solutions.xml` were built and tested on spec 0011 alone, mostly on one acceptance criterion. The real snapshot holds 21 `index.md` files, 188 top level sections, 325 acceptance criteria, 33 of them with a letter suffix, 175 `COPY-N` tokens that look like ids but are not requirements, struck supersessions in 7 specs, revision notes above the first heading in 5, and 302 references to scope features that live in a different file entirely.

**Uncertainty has to survive.** The scope requires an "unresolved, do not guess" marker for identity and a "real relationship, unclassified" value for links. The handoff has one `unclassified` value doing both jobs plus a third one (an item whose kind is unknown). A single value cannot say which doubt applies, and a chain that cannot say which doubt applies is a chain that quietly guesses.

**The graph is disposable and the corpus is frozen.** Nothing here needs a migration story: the graph is rebuilt from the JSON artifacts on demand, and the snapshot is read only. That removes a whole class of concern (re-extraction drift, ordinal shift on edit) and puts the weight on getting the vocabulary right the first time, because every later slice reads this shape.

The consequence of not deciding is that feature 5 invents a shape for one hand picked chain, feature 7 invents a second one for name resolution, and feature 8 discovers the first two cannot express supersession.

## Options considered

### Option 1: One extraction schema, three node kinds, deterministic markers in code

Entities carry one type label from a widened closed set, Records are created by code from the file tree, an Unresolved node stands in for any reference code cannot name, and everything a parser can decide (struck text, checkbox state, ids, lines, aliases) is decided by a parser.

**Pros**:

- Each kind of doubt has its own home, so a chain says which one applies.
- Identity stays with code, which is what keeps two runs of the same section comparable and is the handoff's own hardest won lesson.
- New record kinds and entity types are additive, so rationale extraction later costs an enum value, not a restructure.

**Cons**:

- The vocabulary grows from four entity types to eight and from five relationship types to seven, and the tested few shot examples cover none of the new ones.
- Three node kinds mean three write paths and three constraints in the loader.

### Option 2: Keep the handoff vocabulary exactly as tested

Four entity types, five relationship types, one `unclassified` value for every kind of doubt, and the model reporting struck text and ids as it notices them.

**Pros**:

- Everything in it has been run against real text, and the few shot examples match it exactly.
- Smallest prompt, smallest schema, least to get wrong on day one.

**Cons**:

- About 837 template items (consequences, follow ups, build steps, test scenarios) would be `unclassified` and every one would route to review, against 325 acceptance criteria. The escape valve becomes the main path, which is the opposite of an escape valve.
- One `unclassified` value cannot distinguish "unknown kind" from "unknown target", so the scope's own requirement for a separate unresolved marker is unmet.
- Letter suffixed ids (`AC-10b`) fall outside the tested id pattern and would collide across specs.

### Option 3: A single generic node with a type property, no type labels

One `:Item` label for everything, with `type` as a property, and the same for relationships (one `:LINK` type with a `kind` property).

**Pros**:

- One constraint, one write path, and a new type is pure data with no schema change at all.
- Simple to load and simple to keep consistent.

**Cons**:

- Every traversal filters on a property instead of matching a pattern, which is the anti pattern the modeling skill names first, and it gives up the index backed label match the graph exists to provide.
- A relationship kind held in a property cannot be traversed by type, so history aware traversal (feature 8) would filter every hop by hand.

## Rationale

Option 1 is chosen because of the second and third forces in Context taken together. The scope asks for two different "not confident" values, and the corpus supplies a third case the handoff never met: a reference like `binding rule 6` or `feature 21` whose target is real but unnameable by format. Option 2 collapses all three into one word. Once collapsed, review routing cannot tell a genuinely odd item from an ordinary consequence, which is exactly how the flood arises: 837 template items against 325 criteria, all routed to a person.

The named template types are the part that departs furthest from the tested prompt, which says plainly that consequences and follow up items are not requirements and should be `unclassified`. The departure is justified by evidence rather than taste. The four sections appear in 20 or 21 of the 21 specs, so they recur by the handoff's own promotion bar, and two eval questions walk through them: question 3 crosses a struck test scenario, question 5 crosses a consequence and two follow up items. A type that a real question needs and that every record carries is not speculative. It is also why AC-14 makes a real three run extraction over those sections a gate before the schema is treated as settled.

`VERIFIES` and `SATISFIES` are promoted on measured recurrence rather than on a single question. Leaving them out would have put roughly 434 known shape links into `UNCLASSIFIED`, which buries the few genuinely unclassifiable ones, and promoting them later would mean a prompt and schema change and therefore a re-extraction of every section, with everything it produces flowing through review a second time. The cost now is one enum value each.

Option 3 fails on the one thing the project chose a graph for. Spec 0001 records raw hand written Cypher and multi hop `MATCH` as a stated learning goal, and a model that holds every kind in a property turns every traversal into a filter. It also contradicts the installed modeling skill's first rule about generic labels.

Two smaller calls are worth recording. History links are stored old to new without exception, including `SUPERSEDED_BY` and `AMENDED_BY`, which reads backwards as English but gives feature 8 a single rule ("follow outgoing history links until there are none") instead of a direction table. Only `corrected-by` appears in a tested few shot example, and it already points old to new, so the rename costs no tested evidence. And struck text and checkbox state are parsed in code rather than reported by the model, because whether a record marks something as retired must not depend on the model's attention; the model still supplies the struck text's content and the link to its replacement.

## Corpus spike

All counts were taken from `corpus/jobhunt/docs` at `2e40bcf`, the tracked read only snapshot, during this design session. Commands are recorded so each figure can be re-run.

### Shape counts

| Finding | Figure | How it was counted |
|---|---|---|
| Acceptance criterion definitions | 325 | `grep -hcE "^- \*\*AC-[0-9]+[a-z]?\*\*" */index.md` summed |
| With a letter suffix (`AC-10b`) | 33 | `grep -ohE "\*\*AC-[0-9]+[a-z]\*\*" */index.md \| wc -l` |
| `COPY-N` tokens (id shaped, not requirements) | 175 | `grep -ohE "\b[A-Z][A-Za-z]*-[0-9]+[a-z]?\b" */index.md` grouped by prefix |
| Specs with `Status: Superseded` | 0 of 21 | `grep -H "^\*\*Status\*\*" */index.md` |
| Specs with struck text | 7 (0021 alone has 44 struck lines) | `grep -c "~~" */index.md` |
| Specs with revision notes above the first `##` | 5 (0008 has five) | `awk` over the lines before the first `## ` |
| `verifies AC-N` | 158 lines, 20 specs, 220 criterion references | `grep -hciE "verifies \*{0,2}AC-"`, references counted with `grep -oE "AC-[0-9]+[a-z]?"` |
| `satisfies AC-N` | 183 lines, 20 specs, 434 criterion references | same shape of command |
| Template items that would be `unclassified` | about 837 (280 consequences, 185 follow ups, 206 build steps, 166 test scenarios) | `awk` per section, counting top level bullets and numbered items |
| Template sections present | Consequences 21/21, Follow-up 21/21, Build plan 20/21, test scenarios 20/21 | `grep -l` per heading |
| "Critical test scenarios" as a `##`/`###` heading | 1 spec (0002); in 19 it is a bold label inside another section | `grep -l "^### Critical test scenarios"` against `grep -l "^\*\*Critical test scenarios\*\*"` |
| Scope `##` sections with intro prose before their first `### N.` row | 5 of 6 (Slice 1, Slice 2, v1 extras, v1.5, v2; Foundation's first row follows its heading directly) | read directly at lines 50 to 53 and 191 to 195, plus an `awk` pass per section |
| Scope rows with a `spec [NNNN]` pointer line | 15 of 33; 11 rows mention no spec at all; 0 pointer lines cite two specs | `grep -cE "^_spec \["` and an `awk` pass per row |
| Cross spec criterion references (`spec [0014] AC-20a` form) | 52 | `grep -ohE "spec \[?[0-9]{4}\]?(\([^)]*\))? \*?\*?AC-[0-9]+[a-z]?"` |
| `feature N` mentions inside specs | 302 | `grep -ohE "\bfeature [0-9]+\b" */index.md \| wc -l` |

The engineer's own count of `satisfies` (about 197 lines, about 457 references) differs slightly from the 183 and 434 above. The difference is the regular expression: the figures here require `AC-` immediately after the word, with the bold markers optional, and ignore case.

### The rationale.md census

Twenty questions across four specs (0012, 0003, 0014, 0019; 0011 excluded because the handoff's examples were built on it). I read 0012 and 0003 in full, and 0014 and 0019 with their `rationale.md` in full and their `index.md` by targeted reads and greps. **Caveat: I wrote the questions myself, so this is indicative, not a sample.**

| Spec | Question | Answer lives in |
|---|---|---|
| 0012 | Why no plain text call surface? | rationale, Options lines 24 to 32 |
| 0012 | Why OpenAI rather than Anthropic for `ai_scoring`? | rationale lines 62 to 68; index line 5 says it changed, not why |
| 0012 | Why is the weekly cap 500, not 25? | index, AC-8 |
| 0012 | Why `maxRetries: 0`? | index, invariant line 65 and Consequences line 103 |
| 0012 | Why is `ai_scoring`'s temperature unset? | index, Consequences line 105 (names the rejected alternative too) |
| 0003 | Why is the profile primary key the auth user id? | index line 58 |
| 0003 | Why check constraints rather than enum types? | rationale line 80; index line 112 gives half the reason |
| 0003 | Why is `job_preference` a separate table? | rationale line 82 only |
| 0003 | Why not JSON documents in one wide table? | rationale, Option 2; index states only the principle |
| 0003 | Why the redundant `profile_id`? | index line 143, which names the runner up |
| 0014 | Why a separate "Mark as applied" control? | rationale, Option 3 and line 96 |
| 0014 | Why no `redirect` after the write? | rationale line 102, **and index line 68 gives a reason rationale calls false** |
| 0014 | Why an inline closure rather than hidden fields? | index lines 62 and 191 |
| 0014 | Why does the proxy withhold the refreshed cookie? | index, AC-20a line 51 |
| 0014 | Why is `salary_is_predicted` nullable? | index, AC-6 and line 97 |
| 0019 | Why check only matched skills, not the prose? | rationale line 46; index line 116 names the gap, not the reason |
| 0019 | Why one reveal rather than a progressive second wave? | rationale line 48 only |
| 0019 | Why no page level notice for a misconfigured tier? | index lines 119 and 130 |
| 0019 | Why caveat the prose instead of suppressing it? | index, AC-13 |
| 0019 | Why nothing special when every skill is flagged? | index, AC-13's last sentence |

Eleven in `index.md`, nine needing `rationale.md`, none needing neither. Every question answered by `index.md` asked about a value or rule stated in a criterion. Every question needing `rationale.md` asked about an alternative the spec rejected. That is what points the follow up at an `Alternative` type rather than at a `Claim` type.

Two supporting counts, taken the same way: all 21 `rationale.md` files carry an `## Options considered` section (94 top level sections across the 21 files), while only 7 `index.md` files have such a heading, and in 6 of those it is a one line pointer back to `rationale.md`. Structured rejected options exist in `rationale.md` for 20 of 21 specs.

### Why no Claim type

Spec 0001's follow up line 70 recorded a confirmed finding: an `index.md` asserting a claim as current that its `rationale.md` had already recorded as corrected, found while investigating the Adzuna rate limit case. **That does not reproduce at `2e40bcf`.** Spec 0011's `index.md` line 209 carries the final, corrected attribution ("their terms of service page ... checked 2026-09-04"), and `reference/correction-chains.md` says the same: the misattribution survives only in `rationale.md`. The motivating case for a `Claim` type is therefore a case where `index.md` is right and `rationale.md` holds the history. With `rationale.md` out of extraction scope, nothing wrong enters the graph from it. The correction shapes that do live in `index.md` (struck criteria, "an earlier version read ...") are covered by reading (a): the old text is its own entity linked to its replacement, which is exactly what the tested `AC-9` example already produces.

### Six hand runs

These are hand runs by the architect model (Opus 5) applying the revised vocabulary to real sections, the same way every run in `reference/` was made (pasted by hand, one run each). **They are not three independent Sonnet runs under spec 0001's policy, so `/develop` must repeat them**; that is AC-14.

**Run A. `0019/Consequences`, first three positive bullets.** Three `Consequence` entities, derived ids. Bullet 2 ("No `usage_cap` migration is needed: spec 0012 already seeded `ai_check` ...") produced one `UNCLASSIFIED` link to Record `0012` carrying the verbatim phrase. Bullet 1 ("nothing reads as verified that was not") is close to a testable constraint and carried `granularity_boundary_call`.
_Finding_: the flag's own definition names only Feature, Spec and AcceptanceCriterion, so it must widen to any named type. `entity_type_ambiguous` stays tied to an `unclassified` entity.

**Run B. `0003/Follow-up`, four items.** Four `FollowUp` entities, two `done` and two `open` from the checkbox. Item 1 produced an `UNCLASSIFIED` link to `0014/AC-5` ("Spec 0014 AC-5 supplies the criterion"). Items 3 and 4 produced `BLOCKED_BY` links to `feature 20` and `feature 23` with `relationship_type_ambiguous`, since "adds it later" is a weaker claim than "cannot proceed until".
_Findings_: the checkbox is deterministic and belongs in the pre-check; "supplies the criterion" is real evidence for a future `resolved-by` type; a follow up item routinely points at a scope feature, not a spec.

**Run C. `0012/Build plan`, step 2 and the tail of step 3.** Two `BuildStep` entities. Step 2 produced `SATISFIES` to `AC-8` (same record, different section) and `BLOCKED_BY` to `feature 10`. Step 3's trailing italic produced `SUPERSEDED_BY` to `0019/AC-6` with the phrase "Superseded for `ai_check` ... on 2026-09-09".
_Findings_: endpoints commonly point outside the current output, including to another section of the same record, so resolution has to happen after the whole corpus is loaded; partial supersession ("for `ai_check`") exists and is carried as a phrase, with no partial semantics in the schema.

**Run D. `0021/AC-2`, struck.** The unstruck replacement text kept `0021/AC-2`; the struck old version became a derived entity with `struck` true and `SUPERSEDED_BY` to it. A second struck fragment, `~~one Adzuna search~~`, sits **inside** the replacement text and was revised again a day later.
_Finding_: struck state is not a per item boolean. The pre-check has to emit character ranges, and an entity is struck when its span falls inside one. Whether the tiny retained fragment deserves its own entity is a genuine boundary call; it carried `rationale_boundary_call` and would route to review, which is the designed outcome.

**Run E. `0008/Preamble`, revision 6.** **No entities at all, and two relationships.** `AMENDED_BY` from Record `0008` to `0014/AC-20a`, and `AMENDED_BY` from an `:Unresolved` node for "spec 0001's binding rule 6" to this record.
_Finding_: this breaks spec 0001 line 29's rule that validation checks a relationship's endpoints exist among that output's own entities. Validation now checks that local placeholder endpoints exist in the output and that structured references are well formed; resolution against the whole corpus happens at load time, with `:Unresolved` as the honest fallback.

**Run F. `scope.md`, feature row 21.** Record `feature-21` (kind `scope_feature`, status `done`, aliases `feature 21`, `Terms & privacy notices`, `21`), `SPECIFIED_BY` to Record `0009` from the pointer line, one `AcceptanceCriterion` from the "Done when" clause, one `unclassified` entity for the "Moved here from Slice 5" paragraph (a scheduling decision with its reason, which fits no named type and routes to review), and two `BLOCKED_BY` links for "Depends on feature 7, both ways".
_Finding_: eval question 5's chain runs through exactly those nodes, and the unclassified entity it needs is a correct use of the escape valve rather than a failure of the vocabulary.

### What this spec amends in spec 0001

| 0001 line | Was | Now |
|---|---|---|
| 24 | uniqueness on `canonical_id` per entity label | one uniqueness constraint on a shared `:Entity` label, so an id cannot exist twice under two type labels |
| 27 | extraction covers each spec's `index.md` only, `rationale.md` excluded because it needs a `Claim` type | extraction also covers the preamble and `docs/scope/scope.md`; `rationale.md` stays out for a different, recorded reason (the census and the Adzuna case above), not for the `Claim` reason |
| 28 | one extraction call per top level `##` section | plus the preamble unit, plus scope feature rows and scope sections |
| 29 | `validate.py` reduced to checking a relationship's endpoints exist among that output's own entities | endpoints may be local or structured external references; validation checks local endpoints and reference shape, and resolution happens at load time |
| 31 | citations carry file path, section heading and commit | plus `line`, located deterministically or left null |
| 68 (follow up) | verify the generated schema still validates the fixtures in `reference/graphrag-pipeline/runs/` | same check, against fresh copies under `tests/`, since nothing in `src/` or `tests/` may read `reference/` |
| 70 (follow up) | a `Claim` type using `CORRECTED_BY` is owed to the data model spec | not adopted; the motivating case does not reproduce at `2e40bcf`, and the real gap is rejected alternatives, now enrolled as its own feature with an `Alternative` type |

## References

**Project sources** (verifiable, in this repo):

- `docs/specs/0001-stack-and-architecture/index.md`, lines 24, 27, 28, 29, 31, and follow up items 68 and 70, all amended by this spec.
- `docs/scope/scope.md`, feature 4 ("the schema holds real extractions from several snapshot files, and both not confident values exist"), feature 7 (name resolution), feature 8 (history aware traversal), feature 9 (all five eval questions pass), and the two standing rules.
- `eval/linked-records-research.json` and its markdown twin: the five questions, their traces citing file and line, read at `2e40bcf`.
- `corpus/jobhunt/docs` at `2e40bcf`: the counts and the six hand runs above, with the specific lines named in each finding.
- `reference/HANDOFF.md`: the draft vocabulary, the seven flags, the three question test, the deletion trick, and the code assigned id rules. Weighed, partly adopted, partly changed here.
- `reference/solutions.xml`: the tested prompt and its four few shot examples (line 32's rule on Consequences and Follow-up is reversed here, on the evidence above).
- `reference/graphrag-pipeline/`: `entity.py`, `relationship.py`, `flags.py`, `validate.py`, `compare.py`, `assign_ids.py` and the five fixture runs. Adopted in shape, rewritten fresh into `src/` and `tests/`; the verbatim id pattern is widened to accept a letter suffix.
- `reference/correction-chains.md` and `reference/tracepath-for-scope.md`: the three real correction chains, the "named several ways" risk, and the "real relationship, unclassified" escape valve.
- Installed skills: `.agents/skills/neo4j-modeling-skill/` (generic labels, constraints, and the Enterprise only constraint list at SKILL.md lines 214 to 222), `.agents/skills/neo4j-cypher-skill/`, `.agents/skills/neo4j-driver-python-skill/`, `.agents/skills/pydantic/`.
- Neo4j's own Cypher manual for version 5, checked during this design: uniqueness constraints are available in Community, while property existence, property type and key constraints are Enterprise only.

**Practices & standards**:

- Uncertainty is a value, failure is an exception (`AGENTS.md`): unresolved and unclassified are stored values, never guesses and never drops.
- Functional core, imperative shell: splitting, marking, id assignment, line location and endpoint resolution are pure functions; Neo4j and the model call sit at the edges.
- Code owns identity, models do not: a model written id varies between runs, which breaks both the run comparator and the graph's uniqueness.
- Do not promote a type until real runs show it recurring or a real question needs it (the handoff's own bar, applied to `VERIFIES`, `SATISFIES` and the four template types, and applied against `Claim`).
- Prefer a label match a graph can index over a property filter (the modeling skill's rule on generic labels).
