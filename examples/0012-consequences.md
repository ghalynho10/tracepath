# Worked example: 0012 `## Consequences`

Drafted for tracepath's `SYSTEM_PROMPT` (read from `main` at `dbdd5cb`, schema at `src/tracepath/extract/schema.py`). Not yet validated against `model_json_schema()` — validate in-project before it ships.

First example covering `Consequence`, struck text, and the struck-claim-plus-replacement pair. Also carries `corrected-by` and a record-level `unclassified` link.

## Reasoning notes

- **The struck bullet is two entities, never one.** Spec 0002's `## Consequences` records this as a measured failure mode: the model "sometimes returns a single span covering both," the span begins inside the `~~…~~` range, AC-5 correctly marks it `struck`, "and the effect is that the current fact is stored and labelled obsolete." This example exists partly to demonstrate the opposite: the struck claim and its replacement are separate entities linked `superseded-by`, so the current fact is stored as current.
- **`~~` markers are excluded from the span, deliberately, as an exception to the enclosing-punctuation rule.** AC-5's test is that an entity "whose span falls inside a struck range" is marked `struck`; a span that also swallows the delimiters is not unambiguously *inside* that range. The markers are the pre-check's input, not part of the claim's own text — unlike parentheses or quotes, which belong to the sentence. `struck` never appears in the output: code sets it, never the model (AC-5, AC-6).
- **`superseded-by` and `corrected-by` are told apart by error framing, and both appear here.** This is not a fresh judgement: it restates `reference/solutions.xml` line 37, "corrected-by: B fixes A; A explicitly framed as wrong/a bug." The struck bullet's old claim was *true when written and later overtaken* (feature 10 merged) → `superseded-by`. The caps bullet's old claim *rested on an assumption the text says was contradicted* ("Feature 11 shipped since and its real shape … contradicts that") → `corrected-by`. Neither uses the `unclassified` "Resolved …" shape from the 0012 Follow-up example, and the difference is worth stating: there, a checkbox task was closed with no replacement claim; here, one claim about the world is replaced by another.
- **The caps bullet's old values are quoted (`(66, 2000)`), so a second entity is built.** This is the contrast case to 0012 Follow-up bullet 9, where the old version was only *described* and no second entity was fabricated. The rule is unchanged; only the evidence differs.
- **Bullet 9 splits into four entities.** It bundles the alias risk, the nondeterminism from an unset `temperature`, the band rubric that absorbs it, and the reasoning-token ceiling — each independently statable. All four are flagged `multi_condition_split`, since one-entity-per-bullet would have been defensible too.
- **The link to spec 0001 is record-level on purpose, and is *not* the held ambiguity.** "sits in tension with spec 0001's own stated goal that what is deployed always matches what is in git" points at that spec's stated position, not at a labelled item like `binding rule 6`. A `{record: "0001", id: null}` endpoint is the right granularity for it rather than a lossy fallback, which is what bounds the question held open on 0008 and on 0012's Build plan step 4: those name an item *inside* a record and lose it; this one names the record's own position.
- No named type fits "sits in tension with", so it is `unclassified` carrying the verbatim phrase.

## Input

```text
Record: 0012
File: docs/specs/0012-model-client-router/index.md
Section: Consequences
Unit kind: Section

---
## Consequences

**Positive**:
- Every future AI caller (feature 14, feature 17, and anything after) gets budget enforcement, a visible failure model, and a config only vendor swap for free, by construction, rather than by remembering to add each one.
- Reusing `checkUsageGate()` unchanged means this feature adds no new database function and no new `plpgsql` to review; it is entirely new rows in an existing table plus application code.

**Negative / tradeoffs**:
- ~~This feature's migration and its integration tests cannot run until feature 10 (`usage_cap`, `checkUsageGate`) merges into `main`; it currently exists only on `feat/usage-gating-kill-switch`.~~ **Resolved 2026-09-04**: feature 10 merged to `main` at `5b01b4c` (pull request 86), spec 0011 is Accepted, and `usage_cap`, `check_usage_gate`, and `src/lib/usage-gating/` all exist on `main`. This feature's build, migration included, is unblocked.
- `src/lib/ai/client.ts` imports `checkUsageGate` and `UsageGateReason` from `src/lib/usage-gating/`, not a feature folder: feature 10's pull request 86 (commit `d309e65`) already moved the module there, on the same reasoning this spec would otherwise have had to raise, that code shared by more than one feature belongs in `src/lib` (`kill-switch.ts` already set that precedent, and `checkUsageGate()` is now shared by features 11, 13, and 14). No open layering question remains for this feature to inherit.
- **Revised 2026-09-06**: the global day and month caps were originally `job_search`'s own numbers (66, 2000) borrowed unchanged, on the assumption that one `ai_scoring` call answers one search. Feature 11 shipped since and its real shape (`RESULTS_PER_PAGE = 20`, `src/features/search/adzuna.ts:36`) contradicts that: scoring runs one call per listing, not one per search, so the real multiplier is 20. The caps are now `job_search`'s numbers times 20 (`1320`, `40000`), still not derived from any external vendor ceiling the way `job_search`'s own numbers were derived from Adzuna's terms. A reader must not assume these reflect a vendor limit; the number that actually bears on the named risk is the dollar ceiling in `rationale.md`, which this correction also raised by roughly 10x (see below).
- `checkUsageGate()` marks budget consumed as soon as it decides `allowed: true`, before the vendor is ever called, the same shape `job_search` already accepts. A vendor outage during a busy week can burn an account's entire weekly `ai_scoring` budget on calls that returned nothing, exactly as an Adzuna outage could already burn `job_search`'s.
- `tiers.ts` fixes `maxRetries: 0` specifically because the dollar ceilings in `rationale.md` assume one vendor call per gated call. Restoring the AI SDK's own default of 2 retries would let a single gated call make up to three vendor calls while `usage_cap` still reads the same 40000 a month, moving the real worst case from about $73.60 and $32 a month to about $220.80 and $96. Do not raise `maxRetries` above 0 without re-deriving those figures.
- With the check tier sampled at 1.0 (every scoring call also gets a check call), every profile and job listing sent to OpenAI for scoring is also sent to Google for the check, not one vendor per call but two, every time, twenty times per search rather than once (see the call volume correction above).
- **New 2026-09-06**: `gpt-5.6-luna` is an alias, not a pinned snapshot, the same shape of risk `claude-haiku-4-5` carried in this spec's original vendor pick. OpenAI can repoint it to a newer Luna build without a commit here, which sits in tension with spec 0001's own stated goal that what is deployed always matches what is in git; see Follow-up for the concrete trigger to revisit it (unchanged in kind from the original Haiku follow-up, just moved to the new vendor). Separately, `gpt-5.6-luna` is a reasoning model: at the fixed `reasoningEffort: "medium"` this spec sets, the OpenAI API rejects an explicit `temperature: 0` with an HTTP 400, so `ai_scoring`'s `temperature` is left unset rather than fixed, meaning this tier's output is not deterministic the way `ai_check`'s is. **This was a decision, not an accepted side effect**: the alternative, `reasoning.effort: "none"` with `temperature: 0`, was rejected because it would forfeit the Intelligence Index comparison (39 vs Claude Haiku 4.5's 30) this spec's `ai_scoring` pick actually rests on, that figure was measured at `"medium"`, not `"none"`. Instead, feature 14's band rubric is the instrument that absorbs the nondeterminism: bands are coarse categories, not exact scores, so ordinary sampling variance should only ever flip a boundary-adjacent pair between two neighboring bands, never move a clear-fit pair off its band; see `rationale.md`'s "The determinism decision" for the full reasoning and for how this narrows Follow-up 119's alias-pin trigger (a single boundary flip is not that trigger; a multi-band miss or a reproducing flip is). Reasoning tokens are also billed as output tokens and are not visible in the returned object, which is why `maxOutputTokens` for `ai_scoring` is now 2048 rather than a plain non-reasoning estimate, and why the dollar figures above use a larger, less certain output token placeholder for this tier than for `ai_check`.
- The two vendors and models named here are provisional defaults for feature 16's eval harness to rank against, not a settled choice on accuracy; see `rationale.md`.

**Neutral**:
- The token counts behind the dollar estimates in `rationale.md` (roughly 2000 input and ~1200 output tokens for a scoring call, once GPT-5.6 Luna's own hidden reasoning tokens are accounted for; 1000 input and 200 output for a check call) are rough placeholders until feature 14 and feature 17's real prompts exist, and the scoring output figure is less certain than the rest, since it depends on how much a real fit-scoring prompt actually makes the model reason at `"medium"` effort.
---
```

## Output

```json
{
  "entities": [
    {
      "id": "derived:1",
      "id_source": "derived",
      "type": "Consequence",
      "span": "Every future AI caller (feature 14, feature 17, and anything after) gets budget enforcement, a visible failure model, and a config only vendor swap for free, by construction, rather than by remembering to add each one.",
      "rejected_spans": [],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:2",
      "id_source": "derived",
      "type": "Consequence",
      "span": "Reusing `checkUsageGate()` unchanged means this feature adds no new database function and no new `plpgsql` to review; it is entirely new rows in an existing table plus application code.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:3",
      "id_source": "derived",
      "type": "Consequence",
      "span": "This feature's migration and its integration tests cannot run until feature 10 (`usage_cap`, `checkUsageGate`) merges into `main`; it currently exists only on `feat/usage-gating-kill-switch`.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:4",
      "id_source": "derived",
      "type": "Consequence",
      "span": "feature 10 merged to `main` at `5b01b4c` (pull request 86), spec 0011 is Accepted, and `usage_cap`, `check_usage_gate`, and `src/lib/usage-gating/` all exist on `main`. This feature's build, migration included, is unblocked.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:5",
      "id_source": "derived",
      "type": "Consequence",
      "span": "`src/lib/ai/client.ts` imports `checkUsageGate` and `UsageGateReason` from `src/lib/usage-gating/`, not a feature folder: feature 10's pull request 86 (commit `d309e65`) already moved the module there. No open layering question remains for this feature to inherit.",
      "rejected_spans": [
        "on the same reasoning this spec would otherwise have had to raise, that code shared by more than one feature belongs in `src/lib` (`kill-switch.ts` already set that precedent, and `checkUsageGate()` is now shared by features 11, 13, and 14)"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:6",
      "id_source": "derived",
      "type": "Consequence",
      "span": "the global day and month caps were originally `job_search`'s own numbers (66, 2000) borrowed unchanged, on the assumption that one `ai_scoring` call answers one search.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:7",
      "id_source": "derived",
      "type": "Consequence",
      "span": "The caps are now `job_search`'s numbers times 20 (`1320`, `40000`), still not derived from any external vendor ceiling the way `job_search`'s own numbers were derived from Adzuna's terms. A reader must not assume these reflect a vendor limit; the number that actually bears on the named risk is the dollar ceiling in `rationale.md`, which this correction also raised by roughly 10x (see below).",
      "rejected_spans": [
        "Feature 11 shipped since and its real shape (`RESULTS_PER_PAGE = 20`, `src/features/search/adzuna.ts:36`) contradicts that: scoring runs one call per listing, not one per search, so the real multiplier is 20."
      ],
      "known_trap_flags": ["embedded_second_claim", "multi_condition_split"]
    },
    {
      "id": "derived:8",
      "id_source": "derived",
      "type": "Consequence",
      "span": "`checkUsageGate()` marks budget consumed as soon as it decides `allowed: true`, before the vendor is ever called. A vendor outage during a busy week can burn an account's entire weekly `ai_scoring` budget on calls that returned nothing.",
      "rejected_spans": [
        "the same shape `job_search` already accepts",
        "exactly as an Adzuna outage could already burn `job_search`'s"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:9",
      "id_source": "derived",
      "type": "Consequence",
      "span": "`tiers.ts` fixes `maxRetries: 0`. Restoring the AI SDK's own default of 2 retries would let a single gated call make up to three vendor calls while `usage_cap` still reads the same 40000 a month, moving the real worst case from about $73.60 and $32 a month to about $220.80 and $96. Do not raise `maxRetries` above 0 without re-deriving those figures.",
      "rejected_spans": [
        "specifically because the dollar ceilings in `rationale.md` assume one vendor call per gated call"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:10",
      "id_source": "derived",
      "type": "Consequence",
      "span": "With the check tier sampled at 1.0, every profile and job listing sent to OpenAI for scoring is also sent to Google for the check, not one vendor per call but two, every time, twenty times per search rather than once (see the call volume correction above).",
      "rejected_spans": [
        "(every scoring call also gets a check call)"
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:11",
      "id_source": "derived",
      "type": "Consequence",
      "span": "`gpt-5.6-luna` is an alias, not a pinned snapshot, the same shape of risk `claude-haiku-4-5` carried in this spec's original vendor pick. OpenAI can repoint it to a newer Luna build without a commit here, which sits in tension with spec 0001's own stated goal that what is deployed always matches what is in git; see Follow-up for the concrete trigger to revisit it.",
      "rejected_spans": [
        "(unchanged in kind from the original Haiku follow-up, just moved to the new vendor)"
      ],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:12",
      "id_source": "derived",
      "type": "Consequence",
      "span": "`gpt-5.6-luna` is a reasoning model: at the fixed `reasoningEffort: \"medium\"` this spec sets, the OpenAI API rejects an explicit `temperature: 0` with an HTTP 400, so `ai_scoring`'s `temperature` is left unset rather than fixed, meaning this tier's output is not deterministic the way `ai_check`'s is. **This was a decision, not an accepted side effect**.",
      "rejected_spans": [
        "the alternative, `reasoning.effort: \"none\"` with `temperature: 0`, was rejected because it would forfeit the Intelligence Index comparison (39 vs Claude Haiku 4.5's 30) this spec's `ai_scoring` pick actually rests on, that figure was measured at `\"medium\"`, not `\"none\"`"
      ],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:13",
      "id_source": "derived",
      "type": "Consequence",
      "span": "feature 14's band rubric is the instrument that absorbs the nondeterminism: bands are coarse categories, not exact scores, so ordinary sampling variance should only ever flip a boundary-adjacent pair between two neighboring bands, never move a clear-fit pair off its band.",
      "rejected_spans": [
        "see `rationale.md`'s \"The determinism decision\" for the full reasoning and for how this narrows Follow-up 119's alias-pin trigger (a single boundary flip is not that trigger; a multi-band miss or a reproducing flip is)"
      ],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:14",
      "id_source": "derived",
      "type": "Consequence",
      "span": "Reasoning tokens are also billed as output tokens and are not visible in the returned object, which is why `maxOutputTokens` for `ai_scoring` is now 2048 rather than a plain non-reasoning estimate, and why the dollar figures above use a larger, less certain output token placeholder for this tier than for `ai_check`.",
      "rejected_spans": [],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:15",
      "id_source": "derived",
      "type": "Consequence",
      "span": "The two vendors and models named here are provisional defaults for feature 16's eval harness to rank against, not a settled choice on accuracy; see `rationale.md`.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:16",
      "id_source": "derived",
      "type": "Consequence",
      "span": "The token counts behind the dollar estimates in `rationale.md` (roughly 2000 input and ~1200 output tokens for a scoring call, once GPT-5.6 Luna's own hidden reasoning tokens are accounted for; 1000 input and 200 output for a check call) are rough placeholders until feature 14 and feature 17's real prompts exist, and the scoring output figure is less certain than the rest.",
      "rejected_spans": [
        "since it depends on how much a real fit-scoring prompt actually makes the model reason at `\"medium\"` effort"
      ],
      "known_trap_flags": []
    }
  ],
  "relationships": [
    {
      "type": "superseded-by",
      "source": {"kind": "local", "id": "derived:3"},
      "target": {"kind": "local", "id": "derived:4"},
      "phrase": "**Resolved 2026-09-04**",
      "date": "2026-09-04",
      "known_trap_flags": []
    },
    {
      "type": "corrected-by",
      "source": {"kind": "local", "id": "derived:6"},
      "target": {"kind": "local", "id": "derived:7"},
      "phrase": "**Revised 2026-09-06**",
      "date": "2026-09-06",
      "known_trap_flags": []
    },
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:11"},
      "target": {"kind": "reference", "record": "0001", "id": null, "mention": "spec 0001's own stated goal that what is deployed always matches what is in git"},
      "phrase": "which sits in tension with spec 0001's own stated goal that what is deployed always matches what is in git",
      "date": null,
      "known_trap_flags": ["relationship_type_ambiguous"]
    }
  ]
}
```

## Rules this example demonstrates

- A struck claim and the replacement written beside it are two entities linked `superseded-by`, never one span covering both. The `~~` delimiters stay out of the span so AC-5's containment test is unambiguous; `struck` itself is never in the output, because code sets it.
- `superseded-by` versus `corrected-by` turns on error framing, not on recency: overtaken by events is superseded, rested on something the text says was contradicted is corrected.
- A second entity for an old version is built when the old text is quoted (`(66, 2000)`) and not built when it is only described. Same rule as 0012 Follow-up bullet 9; only the evidence differs.
- A reference endpoint with `id: null` is correct when the text names a record's own position, and is the lossy fallback only when the text names an item *inside* a record. The first is a genuine record-level link; the second is the question held open on 0008.
- A bullet that bundles several independently statable claims may be split, and every entity from that split carries `multi_condition_split`, so a reviewer can see the whole group was one author's bullet.
