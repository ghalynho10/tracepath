# Worked example: 0012 `## Follow-up`

Drafted for tracepath's `SYSTEM_PROMPT` (branch `experiment/0002-effort-low-fidelity`, schema at `src/tracepath/extract/schema.py`). Not yet validated against `model_json_schema()` — validate in-project before it ships.

## Reasoning notes

- **Bullet 9 deliberately does *not* build a second entity from the correction it describes**, despite explicit correction language ("This item originally named only `OPENAI_API_KEY`"). The difference from bullets 1 and 2 below: there the resolution text is a full, directly quotable replacement span. Here the old version is only *described*, not quoted — no verbatim "old" text exists to build a second entity from. Fabricating one from a paraphrase is the exact failure mode behind the project's struck-claim bug (`## Consequences`, spec 0002): a merged or invented span can label the wrong thing as current. This stays one entity.
- Bullets 1 and 2 use the `resolved-by` escape valve (two `FollowUp` entities linked `unclassified`, phrase = the verbatim "Resolved..." marker, dated). This demonstrates the escape valve being used correctly, not an argument for promoting a `resolved-by` type — spec 0002's own Follow-up list already names that promotion as a decision for later, on real run evidence.
- Every "because/since" clause is checked with the deletion trick and rejected whenever the remaining text still stands as a complete claim on its own, with no exception for a clause that merely *explains why an item is worth tracking* — derived:1 and derived:7 are the matching pair to check this against.
- **Spans and rejected spans keep the source's own backticks and bold markers verbatim, never silently cleaned up.** A span is not just a citation, it's what `locate_line()` aligns back to the source text (spec 0002, AC-4), so stripping formatting the source actually has makes that alignment worse, not more readable.
- Where two spans bundle a comparable "task plus something independently statable" shape (derived:5, derived:6), both are flagged `multi_condition_split`, not just the one that felt harder in the moment. The flag means "splitting was plausible," and it was plausible in both.

## Input

```text
Record: 0012
File: docs/specs/0012-model-client-router/index.md
Section: Follow-up
Unit kind: Section

---
## Follow-up

- [x] This spec is numbered 0012 rather than 0011 because feature 10's own spec already claimed 0011 on the then unmerged `feat/usage-gating-kill-switch` branch. Resolved 2026-09-04: the two branches landed in the expected order (spec 0011 merged and Accepted before this spec merged), so no renumbering is needed.
- [x] Feature 14 confirms or corrects the "one scoring call per search" assumption behind `ai_scoring`'s account per week cap of 25. **Resolved 2026-09-06** by `/architect fit scoring with shown reasoning`: the call shape is one `ai_scoring` call per listing (matching `rationale.md`'s original single-listing token placeholder), not one batched call per search, because a shared reasoning trace across twenty listings would degrade the quality of the shown reasoning that is this feature's whole point, would fail all twenty scores on one schema mismatch instead of just one, and would not map onto feature 16's per-pair eval harness. Feature 11 shipped 2026-09-04 and fixed the real multiplier: `RESULTS_PER_PAGE = 20` (`src/features/search/adzuna.ts:36`), so every listing a search returns is scored, meaning one search now costs 20 `ai_scoring` calls (and, at the existing 1.0 sample rate, 20 `ai_check` calls). `usage_cap`'s six seed rows are corrected accordingly (AC-8), and the dollar ceilings in `rationale.md` are re-derived at the corrected volume. If feature 14's own design later decides not every listing gets scored automatically, that is a `usage_cap` update for feature 14 to make, not a reopening of this item.
- [ ] Feature 17 decides its real sample rate for the check tier. If it drops below 1.0, `ai_check`'s three `usage_cap` rows must be lowered in the same change; a cap left at the scoring tier's level while only a fraction of calls are actually sampled no longer bounds real spend.
- [ ] Feature 16's eval harness should rank the candidate set recorded in `rationale.md` (GLM 5.3 Flash, Gemini 3.8 Flash, GPT-5.6 Luna, Claude Haiku 4.5, Claude Sonnet 5) on accuracy against the ground truth set from feature 15. The vendor this spec ships with, GPT-5.6 Luna, is the provisional default, not a settled choice; price is a tiebreak only between candidates of equivalent accuracy, never the deciding force on its own, and it does not need to be invoked here regardless, since the candidate set's spread is roughly $340 a month at this spec's corrected ceiling (40000 calls/month, not the original 2000), no longer a trivial number to wave off with a tiebreak.
- [ ] If GLM (Zhipu AI) is ever chosen over its benchmark result, that is a deliberate jurisdiction decision for the engineer, since it moves resumes, work history, and locations outside the vendors spec 0009's notice currently names, not a call a benchmark result can make on its own.
- [ ] Feature 14's own scope note about the privacy notice's "not used to train models" claim is unchanged by this feature; this spec's own test calls carry no real user data. Verifying each vendor's training and retention terms before real profile data flows through `ai_scoring` in production remains feature 14's responsibility.
- [ ] **Revised 2026-09-06** (vendor changed, trigger unchanged): revisit pinning `ai_scoring` to a dated snapshot instead of the alias `gpt-5.6-luna` when feature 16's eval harness reports a pair falling outside its expected band that cannot be attributed to a prompt change or a ground truth change; that shape is what a silent alias repoint looks like from inside this system, and it is the concrete trigger to pin, not a vague "if it ever becomes a problem." Pinning has its own honest cost: a dated snapshot eventually retires, and nothing in this repo would warn you before a call to it started failing, which is why the alias plus the harness is the better default rather than a compromise.
- [ ] **New 2026-09-06**: the corrected `usage_cap` ceiling (about $105.60 a month worst case, up from the original spec's $10.60) assumes every listing a search returns gets scored automatically. Feature 14's own design should confirm that is really the intended UX (it is what "every score displays its matched and missing skills" in scope.md's Done-when clause, and the "ranked results" claim, both imply, since ranking needs every result scored) rather than inherit it silently from this spec's arithmetic.
- [ ] **New 2026-09-06, corrected by `/check review` on the same date**: `.env.local` currently holds `ANTHROPIC_API_KEY`, set ahead of this spec's original vendor pick; this revision leaves it with no consumer anywhere in this codebase. Before `/develop model client router` can run against a real vendor and before the pull request for this revision opens, both `OPENAI_API_KEY` and `GOOGLE_GENERATIVE_AI_API_KEY` must be set in `.env.local` and in all three Vercel environments (development, preview, production), per this project's own standing reflex that a new `src/env.ts` variable needs setting in every environment the branch will deploy to. This item originally named only `OPENAI_API_KEY`; both are equally required by AC-10, and a preview build with only one set fails the same way a build with neither set would. `ANTHROPIC_API_KEY` can stay in `.env.local` harmlessly (nothing reads it), but should not be assumed to still matter when reasoning about this feature's configuration.
---
```

## Output

```json
{
  "entities": [
    {
      "id": "derived:1",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "This spec is numbered 0012 rather than 0011",
      "rejected_spans": [
        "because feature 10's own spec already claimed 0011 on the then unmerged `feat/usage-gating-kill-switch` branch."
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:2",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "the two branches landed in the expected order (spec 0011 merged and Accepted before this spec merged), so no renumbering is needed.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:3",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "Feature 14 confirms or corrects the \"one scoring call per search\" assumption behind `ai_scoring`'s account per week cap of 25.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:4",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "the call shape is one `ai_scoring` call per listing (matching `rationale.md`'s original single-listing token placeholder), not one batched call per search. Feature 11 shipped 2026-09-04 and fixed the real multiplier: `RESULTS_PER_PAGE = 20` (`src/features/search/adzuna.ts:36`), so every listing a search returns is scored, meaning one search now costs 20 `ai_scoring` calls (and, at the existing 1.0 sample rate, 20 `ai_check` calls). `usage_cap`'s six seed rows are corrected accordingly (AC-8), and the dollar ceilings in `rationale.md` are re-derived at the corrected volume.",
      "rejected_spans": [
        "because a shared reasoning trace across twenty listings would degrade the quality of the shown reasoning that is this feature's whole point, would fail all twenty scores on one schema mismatch instead of just one, and would not map onto feature 16's per-pair eval harness",
        "If feature 14's own design later decides not every listing gets scored automatically, that is a `usage_cap` update for feature 14 to make, not a reopening of this item."
      ],
      "known_trap_flags": ["rationale_boundary_call", "multi_condition_split"]
    },
    {
      "id": "derived:5",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "Feature 17 decides its real sample rate for the check tier. If it drops below 1.0, `ai_check`'s three `usage_cap` rows must be lowered in the same change",
      "rejected_spans": [
        "a cap left at the scoring tier's level while only a fraction of calls are actually sampled no longer bounds real spend"
      ],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:6",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "Feature 16's eval harness should rank the candidate set recorded in `rationale.md` (GLM 5.3 Flash, Gemini 3.8 Flash, GPT-5.6 Luna, Claude Haiku 4.5, Claude Sonnet 5) on accuracy against the ground truth set from feature 15. The vendor this spec ships with, GPT-5.6 Luna, is the provisional default, not a settled choice; price is a tiebreak only between candidates of equivalent accuracy, never the deciding force on its own, and it does not need to be invoked here regardless",
      "rejected_spans": [
        "since the candidate set's spread is roughly $340 a month at this spec's corrected ceiling (40000 calls/month, not the original 2000), no longer a trivial number to wave off with a tiebreak"
      ],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:7",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "If GLM (Zhipu AI) is ever chosen over its benchmark result, that is a deliberate jurisdiction decision for the engineer",
      "rejected_spans": [
        "since it moves resumes, work history, and locations outside the vendors spec 0009's notice currently names, not a call a benchmark result can make on its own"
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:8",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "Feature 14's own scope note about the privacy notice's \"not used to train models\" claim is unchanged by this feature; this spec's own test calls carry no real user data. Verifying each vendor's training and retention terms before real profile data flows through `ai_scoring` in production remains feature 14's responsibility.",
      "rejected_spans": [],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:9",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "revisit pinning `ai_scoring` to a dated snapshot instead of the alias `gpt-5.6-luna` when feature 16's eval harness reports a pair falling outside its expected band that cannot be attributed to a prompt change or a ground truth change",
      "rejected_spans": [
        "that shape is what a silent alias repoint looks like from inside this system, and it is the concrete trigger to pin, not a vague \"if it ever becomes a problem.\"",
        "Pinning has its own honest cost: a dated snapshot eventually retires, and nothing in this repo would warn you before a call to it started failing, which is why the alias plus the harness is the better default rather than a compromise."
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:10",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "the corrected `usage_cap` ceiling (about $105.60 a month worst case, up from the original spec's $10.60) assumes every listing a search returns gets scored automatically. Feature 14's own design should confirm that is really the intended UX rather than inherit it silently from this spec's arithmetic",
      "rejected_spans": [
        "(it is what \"every score displays its matched and missing skills\" in scope.md's Done-when clause, and the \"ranked results\" claim, both imply, since ranking needs every result scored)"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:11",
      "id_source": "derived",
      "type": "FollowUp",
      "span": "`.env.local` currently holds `ANTHROPIC_API_KEY`, set ahead of this spec's original vendor pick; this revision leaves it with no consumer anywhere in this codebase. Before `/develop model client router` can run against a real vendor and before the pull request for this revision opens, both `OPENAI_API_KEY` and `GOOGLE_GENERATIVE_AI_API_KEY` must be set in `.env.local` and in all three Vercel environments (development, preview, production). This item originally named only `OPENAI_API_KEY`; both are equally required by AC-10, and a preview build with only one set fails the same way a build with neither set would. `ANTHROPIC_API_KEY` can stay in `.env.local` harmlessly (nothing reads it), but should not be assumed to still matter when reasoning about this feature's configuration.",
      "rejected_spans": [
        "per this project's own standing reflex that a new `src/env.ts` variable needs setting in every environment the branch will deploy to"
      ],
      "known_trap_flags": ["rationale_boundary_call", "embedded_second_claim"]
    }
  ],
  "relationships": [
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:1"},
      "target": {"kind": "local", "id": "derived:2"},
      "phrase": "Resolved 2026-09-04",
      "date": "2026-09-04",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:3"},
      "target": {"kind": "local", "id": "derived:4"},
      "phrase": "**Resolved 2026-09-06**",
      "date": "2026-09-06",
      "known_trap_flags": ["relationship_type_ambiguous"]
    }
  ]
}
```

## Rules this example demonstrates

- `rejected_spans` holds any clause that (a) explains *why* the kept claim exists rather than stating a claim itself, and (b) is confirmed by the deletion trick: delete it, and the rest of the span still stands as a complete claim on its own. A clause is kept regardless of "because"/"since" wording when deleting it removes real content (`derived:11`'s second sentence bundles a testable failure mode, so it stays despite reading like elaboration).
- `known_trap_flags` fires per genuinely close call, not per clause with a signal word: `rationale_boundary_call` when the reject/keep line was non-obvious, `multi_condition_split` when a merge-vs-split call was plausible either way, `embedded_second_claim` when a clause looked rejectable but held its own testable fact. An obvious "because" clause with an obvious remainder (`derived:1`, `derived:7`) gets no flag.
- A resolution and its original concern are both typed the same as each other (here, both `FollowUp`) and linked, never merged into one span and never left as two unconnected entities — the same shape as AC-5's struck-claim-plus-replacement treatment, just for a checkbox item instead of a criterion.
- Nothing is fabricated from a paraphrase. A second entity for a described-but-unquoted "old version" is never built; where the old text isn't directly quotable, the correction stays inside one entity's own span.
- Spans and rejected spans preserve the source's own backticks, bold markers, and enclosing punctuation (quotes, parentheses) exactly — enclosing punctuation travels with whichever span, kept or rejected, contains what it encloses. Formatting is not cosmetic here — it's part of what a downstream aligner matches against.
