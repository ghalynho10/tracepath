# Worked example: 0012 `## Build plan`

Drafted for tracepath's `SYSTEM_PROMPT` (read from `main` at `dbdd5cb`, schema at `src/tracepath/extract/schema.py`).

First example covering `satisfies`, and also the first to carry `blocked-by` and `superseded-by`.

> **Validation caveat.** Step 4's link carries a `label` on a reference endpoint, per AC-7's 2026-09-23 amendment. **`ReferenceEndpoint` does not have that field yet** — unchanged on `main` at `dbdd5cb` and on `feat/reference-label`, whose preamble says "No code changes here" — and `_Frozen` sets `extra="forbid"`, so that one relationship fails `model_validate` until build plan task 17 lands. The other 22 relationships and all 9 entities are unaffected. Re-validate the whole file after task 17.

## Reasoning notes

- **Nine numbered steps, nine `BuildStep` entities, all derived ids.** The author's numbering is the unit's own structure, so a step stays one entity even when it bundles many instructions (steps 3 and 5 are enormous). Splitting them would break the one-to-one correspondence between a numbered step and the `satisfies` links written on it. Both are flagged `multi_condition_split` instead.
- **A `satisfies **AC-N**` pointer stays inside the span; the relationship is derived from it, not extracted out of it.** It isn't rationale, so `rejected_spans` would mislabel it, and dropping it would leave the span non-contiguous against the source. The relationship carrying the same information is not redundancy — one is the citation, the other is the edge.
- **A later status annotation is different, and is rejected.** Step 3's trailing `_Superseded for `ai_check` by spec 0019 AC-6 on 2026-09-09: …_` fails the deletion trick as part of the step's own work — the step stands complete without it — and it describes history, the same category as "corrected … an earlier version read" in the 0012 Follow-up example. It goes to `rejected_spans` *and* produces the `superseded-by` link. The distinction from the pointer above: `satisfies` is part of what the author wrote the step to say; `Superseded` is an annotation added later about the step's status.
- **Step 9's range is enumerated into eight links.** `satisfies **AC-1** through **AC-8**` names both endpoints, and this record's criteria run AC-1…AC-10 with no letter suffixes, so the range expands with nothing invented. Enumeration also fails safe: the model sees only this unit and cannot confirm each id exists, but a wrong id resolves to `:Unresolved` (AC-7) — visible — whereas not enumerating would silently lose eight real edges. No flag is set, because none of the seven covers "endpoint inferred from a stated range" (see the finding below).
- **Step 2's `Blocked until feature 10's `usage_cap` table exists on `main`` is a `blocked-by`**, direction blocked → blocker per spec 0002's relationship table. The endpoint is written as the text names it (`feature 10`), per the schema's own instruction for `record`. **Its expected outcome today is an `:Unresolved` node, not the feature 10 row** — a scope feature Record's `canonical_id` is `feature-10`, hyphenated, and the `feature N` form lives in that Record's `aliases`, whose stated job is to carry alternative names *until name resolution (feature 7) does the matching*. Feature 7 is not built, so nothing matches an alias yet. That is the correct behaviour, not a defect in the extraction: the link is preserved with its verbatim mention and the gap is visible, which is exactly what `:Unresolved` is for.
- **Step 3's supersession is partial** ("Superseded **for `ai_check`**"), which spec 0002's own Follow-up already records as a known corpus shape with no partial semantics in the schema. The type follows the text's own word, so the phrase is what carries the partiality; it is flagged anyway so a reviewer sees that the link is narrower than its type implies.
- **Step 6's correction produces no second entity and no link.** "this step originally named only `tiers.ts` and only `@ai-sdk/`" describes the old version without quoting it, and `/check review` round 2 is not one of the three Record kinds — the same two rules as 0012 Follow-up bullet 9 and 0008's cited review file, applied together.

### Step 4's link, settled by AC-7's `label` amendment

Step 4 ends `satisfies the Value sourcing row for a provider failure's message` — a `satisfies` whose target is a named row inside **this same record** that carries no verbatim id. AC-7's 2026-09-23 amendment cites this exact sentence as the second instance that made the rule general rather than a fix for one corpus sentence, and gives the endpoint shape directly: `{record: "0012", label: "the Value sourcing row for a provider failure's message"}`. The rule it resolves under: "`record` plus `label`, with `id` null, becomes the entity in that record whose own `label` matches once both are normalized (case folded, trimmed, internal whitespace collapsed to one space, punctuation untouched)", matched **"exact, never fuzzy"**.

Worth noting what this example does *not* prove: whether the `## Feature design` extraction of that same row emits an entity whose own `label` is the identical string. AC-7's amendment is explicit that nothing measured yet shows the model reproducing a matching `label` on both sides, and build plan task 17 owes that run. Until it happens, a mismatch falls to `:Unresolved` carrying `record` and `label` (AC-10) — "a missed match, never a wrong one".

### Finding: a flag gap

Two candidates, on evidence from this unit, recorded the way `resolved-by` was recorded — not promotions argued for here:

1. **An endpoint inferred from a stated range.** Step 9's `satisfies **AC-1** through **AC-8**` expands to eight endpoints, none of them written individually in the text.
2. **A supersession whose stated type is wider than its actual scope.** Step 3's `Superseded for `ai_check`` uses the word plainly, but only one of the two tiers is superseded. Spec 0002's Follow-up already records partial supersession as a known corpus shape, so this candidate has a home there.

Per the closed-set rule, nothing was invented: step 9 carries no flag, step 3 borrows `relationship_type_ambiguous`.

## Input

```text
Record: 0012
File: docs/specs/0012-model-client-router/index.md
Section: Build plan
Unit kind: Section

---
## Build plan

1. Add `@ai-sdk/openai`, `@ai-sdk/google`, and `ai` to `package.json`, none pinned, matching this spec's original style; `4.0.60` is the `@ai-sdk/openai` version this revision checked at design time (see `rationale.md`), not a version this project's `pnpm install` has actually resolved, since this project has no `ai` or `@ai-sdk/*` dependency yet, adding them is this very step. Confirm after running `pnpm install` that the resolved `@ai-sdk/openai` version still shares its `@ai-sdk/provider`/`@ai-sdk/provider-utils` versions with whatever `@ai-sdk/google` and `ai` resolve to; a mismatch there is what an actual incompatibility would look like, and neither `npm view` nor this spec can rule that out ahead of a real install. Add `OPENAI_API_KEY` and `GOOGLE_GENERATIVE_AI_API_KEY` to `src/env.ts`'s server schema (required, non empty), to its `runtimeEnv` block (the drift guard in `recipients.test.ts` only reads that block), and to `.env.example` and `.env.test.example`, satisfies **AC-10**.
2. Write the migration seeding the six `usage_cap` rows for `ai_scoring` and `ai_check` at the corrected values (`500` / `1320` / `40000`, see Rationale). Blocked until feature 10's `usage_cap` table exists on `main` (see Consequences), satisfies **AC-8**.
3. Write `src/lib/ai/tiers.ts`: the `Tier` union, and the checked in map from tier to `{ model, temperature?, maxOutputTokens, maxRetries: 0, timeoutMs: 30_000, providerOptions? }`. `temperature` is `number | undefined` in the type, not a plain `number`: `ai_check` (Gemini) sets it to `0`, but `ai_scoring` (GPT-5.6 Luna, a reasoning model) leaves it `undefined`, because the OpenAI API rejects `temperature: 0` outright (HTTP 400) whenever `reasoning.effort` is anything other than `"none"`, and `"none"` effort is not chosen here (see Rationale). `ai_scoring`'s entry instead sets `providerOptions: { openai: { reasoningEffort: "medium" } }`, passed through unchanged to `generateObject`; `ai_check` has no `providerOptions`. `maxOutputTokens` is `2048` for `ai_scoring` (up from a plain non-reasoning estimate, to leave headroom for GPT-5.6 Luna's own hidden reasoning tokens, which are billed as output and count against this ceiling) and `512` for `ai_check`, unchanged. Construct each vendor's provider instance (`createOpenAI`, `createGoogle`) by passing the validated `env.OPENAI_API_KEY` / `env.GOOGLE_GENERATIVE_AI_API_KEY` explicitly; calling the returned `OpenAIProvider` instance directly with a model id (`createOpenAI({ apiKey })("gpt-5.6-luna")`) already resolves to the Responses API model, the shape OpenAI's own reasoning model guidance recommends, so no separate `.responses()` call is needed. The map stores `timeoutMs`, a plain number, never a constructed `AbortSignal`: `AbortSignal.timeout()` starts counting the moment it is called, so one built at module load time would already read as expired for every call made after the first thirty seconds of the process's life. `callTier()` builds a fresh `AbortSignal.timeout(tier.timeoutMs)` on every call, satisfies **AC-1**, **AC-3**, **AC-10**. _Superseded for `ai_check` by spec [0019](../0019-cross-vendor-self-check/index.md) AC-6 on 2026-09-09: that tier's `timeoutMs` is now 20000, derived from five live latency measurements rather than shared with `ai_scoring` by default. `ai_scoring` still reads 30000._
4. Write `src/lib/ai/failures.ts`, a fixed, non secret message per new failure kind used here, mirroring the shape of `USAGE_GATE_FAILURES`, satisfies the Value sourcing row for a provider failure's message.
5. Write `src/lib/ai/client.ts`: `callTier()`, opening the named span `ai.call_tier` (`op: "function"`, `tier` as a span attribute, one name for both tiers) as the first statement, then passing the vendor call to `withUsageGate(tier, fn, cookieAdapter)` (spec 0011's inversion-of-control helper, already `job_search`'s own caller shape in `src/features/search/adzuna.ts`), rather than calling `checkUsageGate()` and branching on its decision by hand: `withUsageGate()` invokes its `fn` thunk only once the gate has already decided `allowed: true`, so the vendor being unreachable on a refusal is a structural guarantee of the call shape, not a fact depending on the branching being written correctly at every call site. The thunk calls `generateObject` with a freshly built `AbortSignal.timeout(tier.timeoutMs)` inside a single `try`/`catch` (not `attempt()`, which carries one fixed kind) with the tier's fixed vendor, model and parameters and the caller's schema, spreading `tier.providerOptions` into the call only when the tier defines one and passing `temperature` through as-is (`undefined` for `ai_scoring` is dropped by serialization, never coerced to `0`); on a caught error, `classify()` (a pure function, mirroring `src/features/auth/callback.ts`) reads it, the active span gets `span.setAttribute("stage", "vendor")`, and exactly one `failure()` call follows, `response_malformed` for `NoObjectGeneratedError.isInstance(error)`, `external_service_failed` otherwise, satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**.
6. Write a test asserting no file under `src/` other than `src/lib/ai/tiers.ts` and `src/lib/ai/client.ts` imports an `@ai-sdk/` package or the plain `ai` package, satisfies **AC-3**. Corrected 2026-09-06 by `/check review` round 2: this step originally named only `tiers.ts` and only `@ai-sdk/`, understating the guard on both axes after a later fix widened it to also allow `client.ts` (the router itself, the one file that legitimately calls `generateObject`) and to also ban the plain `ai` package (a caller could otherwise import `generateObject` from `ai` directly and call it on `TIERS.ai_scoring.model`, an already exported live model instance, bypassing both the router and the usage gate).
7. Register the `ai.call_tier` span in `docs/observability/spans.md`, satisfies **AC-7**.
8. Add two new `DATA_RECIPIENTS` entries, `openai` and `google-ai`, leaving the existing `google` entry untouched; remove `"OpenAI"` from `notYetRecipients` in `src/app/(marketing)/privacy/page.test.ts` (leave `"Anthropic"` in place) and correct its comment; update the id array assertion in `recipients.test.ts` (line 110) to include both new ids, satisfies **AC-9**.
9. Write the critical test scenarios above: the `classify()` unit tests (no vendor call needed), a zeroed cap refusing without reaching a vendor, and, gated behind `TEST_LIVE_MODEL_CALLS_ENABLED`, both tiers reaching two real, different vendors, satisfies **AC-1** through **AC-8**.
---
```

## Output

```json
{
  "entities": [
    {
      "id": "derived:1",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Add `@ai-sdk/openai`, `@ai-sdk/google`, and `ai` to `package.json`, none pinned. Confirm after running `pnpm install` that the resolved `@ai-sdk/openai` version still shares its `@ai-sdk/provider`/`@ai-sdk/provider-utils` versions with whatever `@ai-sdk/google` and `ai` resolve to. Add `OPENAI_API_KEY` and `GOOGLE_GENERATIVE_AI_API_KEY` to `src/env.ts`'s server schema (required, non empty), to its `runtimeEnv` block, and to `.env.example` and `.env.test.example`, satisfies **AC-10**.",
      "rejected_spans": [
        "matching this spec's original style",
        "`4.0.60` is the `@ai-sdk/openai` version this revision checked at design time (see `rationale.md`), not a version this project's `pnpm install` has actually resolved, since this project has no `ai` or `@ai-sdk/*` dependency yet, adding them is this very step.",
        "a mismatch there is what an actual incompatibility would look like, and neither `npm view` nor this spec can rule that out ahead of a real install",
        "(the drift guard in `recipients.test.ts` only reads that block)"
      ],
      "known_trap_flags": ["rationale_boundary_call", "multi_condition_split"]
    },
    {
      "id": "derived:2",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Write the migration seeding the six `usage_cap` rows for `ai_scoring` and `ai_check` at the corrected values (`500` / `1320` / `40000`, see Rationale). Blocked until feature 10's `usage_cap` table exists on `main` (see Consequences), satisfies **AC-8**.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:3",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Write `src/lib/ai/tiers.ts`: the `Tier` union, and the checked in map from tier to `{ model, temperature?, maxOutputTokens, maxRetries: 0, timeoutMs: 30_000, providerOptions? }`. `temperature` is `number | undefined` in the type, not a plain `number`: `ai_check` (Gemini) sets it to `0`, but `ai_scoring` (GPT-5.6 Luna, a reasoning model) leaves it `undefined`. `ai_scoring`'s entry instead sets `providerOptions: { openai: { reasoningEffort: \"medium\" } }`, passed through unchanged to `generateObject`; `ai_check` has no `providerOptions`. `maxOutputTokens` is `2048` for `ai_scoring` and `512` for `ai_check`, unchanged. Construct each vendor's provider instance (`createOpenAI`, `createGoogle`) by passing the validated `env.OPENAI_API_KEY` / `env.GOOGLE_GENERATIVE_AI_API_KEY` explicitly; no separate `.responses()` call is needed. The map stores `timeoutMs`, a plain number, never a constructed `AbortSignal`. `callTier()` builds a fresh `AbortSignal.timeout(tier.timeoutMs)` on every call, satisfies **AC-1**, **AC-3**, **AC-10**.",
      "rejected_spans": [
        "because the OpenAI API rejects `temperature: 0` outright (HTTP 400) whenever `reasoning.effort` is anything other than `\"none\"`, and `\"none\"` effort is not chosen here (see Rationale)",
        "(up from a plain non-reasoning estimate, to leave headroom for GPT-5.6 Luna's own hidden reasoning tokens, which are billed as output and count against this ceiling)",
        "calling the returned `OpenAIProvider` instance directly with a model id (`createOpenAI({ apiKey })(\"gpt-5.6-luna\")`) already resolves to the Responses API model, the shape OpenAI's own reasoning model guidance recommends, so",
        "`AbortSignal.timeout()` starts counting the moment it is called, so one built at module load time would already read as expired for every call made after the first thirty seconds of the process's life",
        "_Superseded for `ai_check` by spec 0019 AC-6 on 2026-09-09: that tier's `timeoutMs` is now 20000, derived from five live latency measurements rather than shared with `ai_scoring` by default. `ai_scoring` still reads 30000._"
      ],
      "known_trap_flags": ["rationale_boundary_call", "multi_condition_split"]
    },
    {
      "id": "derived:4",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Write `src/lib/ai/failures.ts`, a fixed, non secret message per new failure kind used here, mirroring the shape of `USAGE_GATE_FAILURES`, satisfies the Value sourcing row for a provider failure's message.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:5",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Write `src/lib/ai/client.ts`: `callTier()`, opening the named span `ai.call_tier` (`op: \"function\"`, `tier` as a span attribute, one name for both tiers) as the first statement, then passing the vendor call to `withUsageGate(tier, fn, cookieAdapter)`. The thunk calls `generateObject` with a freshly built `AbortSignal.timeout(tier.timeoutMs)` inside a single `try`/`catch` with the tier's fixed vendor, model and parameters and the caller's schema, spreading `tier.providerOptions` into the call only when the tier defines one and passing `temperature` through as-is; on a caught error, `classify()` reads it, the active span gets `span.setAttribute(\"stage\", \"vendor\")`, and exactly one `failure()` call follows, `response_malformed` for `NoObjectGeneratedError.isInstance(error)`, `external_service_failed` otherwise, satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**.",
      "rejected_spans": [
        "(spec 0011's inversion-of-control helper, already `job_search`'s own caller shape in `src/features/search/adzuna.ts`), rather than calling `checkUsageGate()` and branching on its decision by hand: `withUsageGate()` invokes its `fn` thunk only once the gate has already decided `allowed: true`, so the vendor being unreachable on a refusal is a structural guarantee of the call shape, not a fact depending on the branching being written correctly at every call site",
        "(not `attempt()`, which carries one fixed kind)",
        "(`undefined` for `ai_scoring` is dropped by serialization, never coerced to `0`)",
        "(a pure function, mirroring `src/features/auth/callback.ts`)"
      ],
      "known_trap_flags": ["rationale_boundary_call", "multi_condition_split"]
    },
    {
      "id": "derived:6",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Write a test asserting no file under `src/` other than `src/lib/ai/tiers.ts` and `src/lib/ai/client.ts` imports an `@ai-sdk/` package or the plain `ai` package, satisfies **AC-3**.",
      "rejected_spans": [
        "Corrected 2026-09-06 by `/check review` round 2: this step originally named only `tiers.ts` and only `@ai-sdk/`, understating the guard on both axes after a later fix widened it to also allow `client.ts` (the router itself, the one file that legitimately calls `generateObject`) and to also ban the plain `ai` package (a caller could otherwise import `generateObject` from `ai` directly and call it on `TIERS.ai_scoring.model`, an already exported live model instance, bypassing both the router and the usage gate)."
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:7",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Register the `ai.call_tier` span in `docs/observability/spans.md`, satisfies **AC-7**.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:8",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Add two new `DATA_RECIPIENTS` entries, `openai` and `google-ai`, leaving the existing `google` entry untouched; remove `\"OpenAI\"` from `notYetRecipients` in `src/app/(marketing)/privacy/page.test.ts` (leave `\"Anthropic\"` in place) and correct its comment; update the id array assertion in `recipients.test.ts` (line 110) to include both new ids, satisfies **AC-9**.",
      "rejected_spans": [],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:9",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Write the critical test scenarios above: the `classify()` unit tests (no vendor call needed), a zeroed cap refusing without reaching a vendor, and, gated behind `TEST_LIVE_MODEL_CALLS_ENABLED`, both tiers reaching two real, different vendors, satisfies **AC-1** through **AC-8**.",
      "rejected_spans": [],
      "known_trap_flags": []
    }
  ],
  "relationships": [
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:1"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-10", "mention": "**AC-10**"},
      "phrase": "satisfies **AC-10**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:2"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-8", "mention": "**AC-8**"},
      "phrase": "satisfies **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "blocked-by",
      "source": {"kind": "local", "id": "derived:2"},
      "target": {"kind": "reference", "record": "feature 10", "id": null, "mention": "feature 10's `usage_cap` table"},
      "phrase": "Blocked until feature 10's `usage_cap` table exists on `main`",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:3"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-1", "mention": "**AC-1**"},
      "phrase": "satisfies **AC-1**, **AC-3**, **AC-10**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:3"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-3", "mention": "**AC-3**"},
      "phrase": "satisfies **AC-1**, **AC-3**, **AC-10**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:3"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-10", "mention": "**AC-10**"},
      "phrase": "satisfies **AC-1**, **AC-3**, **AC-10**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "superseded-by",
      "source": {"kind": "local", "id": "derived:3"},
      "target": {"kind": "reference", "record": "0019", "id": "AC-6", "mention": "spec 0019 AC-6"},
      "phrase": "Superseded for `ai_check` by spec 0019 AC-6 on 2026-09-09: that tier's `timeoutMs` is now 20000",
      "date": "2026-09-09",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:4"},
      "target": {"kind": "reference", "record": "0012", "id": null, "label": "the Value sourcing row for a provider failure's message", "mention": "the Value sourcing row for a provider failure's message"},
      "phrase": "satisfies the Value sourcing row for a provider failure's message",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:5"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-2", "mention": "**AC-2**"},
      "phrase": "satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:5"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-4", "mention": "**AC-4**"},
      "phrase": "satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:5"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-5", "mention": "**AC-5**"},
      "phrase": "satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:5"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-6", "mention": "**AC-6**"},
      "phrase": "satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:5"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-7", "mention": "**AC-7**"},
      "phrase": "satisfies **AC-2**, **AC-4**, **AC-5**, **AC-6**, **AC-7**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:6"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-3", "mention": "**AC-3**"},
      "phrase": "satisfies **AC-3**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:7"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-7", "mention": "**AC-7**"},
      "phrase": "satisfies **AC-7**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:8"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-9", "mention": "**AC-9**"},
      "phrase": "satisfies **AC-9**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-1", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-2", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-3", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-4", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-5", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-6", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-7", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:9"},
      "target": {"kind": "reference", "record": "0012", "id": "AC-8", "mention": "**AC-1** through **AC-8**"},
      "phrase": "satisfies **AC-1** through **AC-8**",
      "date": null,
      "known_trap_flags": []
    }
  ]
}
```

## Rules this example demonstrates

- A numbered list's own numbering is the entity boundary. A step stays one `BuildStep` however much it bundles, flagged `multi_condition_split` rather than split, so the `satisfies` links written on a step keep their one-to-one correspondence to it.
- A `satisfies`/`blocked-by` pointer written as part of the step stays in the span **and** produces a link. A later status annotation about the step (`_Superseded … on 2026-09-09_`) is rejected from the span and produces a link. The test is the deletion trick plus who wrote it when: the step's own statement of its work, or a note added later about its status.
- A stated range (`**AC-1** through **AC-8**`) is enumerated into one link per id when both endpoints are named and the record's numbering has no gaps or suffixes, because a wrong id fails safe to `:Unresolved` while a skipped range silently loses every edge. Each enumerated link keeps the whole range as its `phrase`, so the expansion is auditable back to the one sentence that authorised it.
- Direction follows spec 0002's relationship table without exception: `satisfies` is BuildStep → AcceptanceCriterion, `blocked-by` is blocked → blocker, `superseded-by` is old → new.
- A relationship whose target is named but unnumbered (a "Value sourcing row") uses a `{record, label}` reference endpoint, per AC-7, rather than collapsing to the bare Record or dropping to `:Unresolved`. The `label` is the author's own words for the item, copied exactly; matching is exact, never fuzzy, and a miss falls to `:Unresolved` keeping both `record` and `label`.
- A `{record, label}` endpoint works the same way inside the unit's own record as across records. Step 4 points at a row in `0012` while 0008's preamble points at an item in `0001`; nothing about the shape changes.
- When a real judgement call matches no flag in the closed set, nothing is invented: the call is made, the reasoning is written down here, and the gap is recorded as a candidate on evidence.
