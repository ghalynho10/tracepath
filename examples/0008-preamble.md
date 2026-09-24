# Worked example: 0008 Preamble

Drafted for tracepath's `SYSTEM_PROMPT` (schema at `src/tracepath/extract/schema.py`).

> **Validation caveat.** This example carries a `label` on a reference endpoint, per AC-7's 2026-09-23 amendment. **`ReferenceEndpoint` does not have that field yet** — it is unchanged on `main` at `dbdd5cb` and on `feat/reference-label`, whose own preamble says "No code changes here". Since `_Frozen` sets `extra="forbid"`, this example will fail `ExtractionOutput.model_validate` until build plan task 17 lands (`Add label to ReferenceEndpoint … regenerate extraction_json_schema() … bump prompt_version`). That task also names the gap this example fills: "add at least one `label` worked example to the prompt's few shot set, since it currently has none". Validate this one after task 17, not before.

## Reasoning notes

- **Zero entities.** Every span in this preamble describes a change to something that lives in a different unit (`## Requirements`, or another spec entirely) — nothing here is itself a testable claim this unit can point at locally. This matches spec 0002's own test scenario naming this exact unit as the one that produces links and no local entities.
- Because there are no local entities, **every relationship endpoint here is a `reference`, never `local`** — including references to ACs inside this same spec (`0008`), since "local" means "in this same output," not "in this same document."
- **A correction is only linkable when it has two distinguishable ids.** AC-10b (Revision 6) is a genuinely new id next to AC-10, so `amended-by(AC-10 → AC-10b)` is constructible. But AC-3a (Revision 5) and AC-5a (Revision 4) are each described as flawed and rewritten *under the same id* — no second, distinct identifier exists to build a real "old → new" pair from this unit alone. Constructing a relationship with identical source and target would be a self-loop that misrepresents what `amended-by`/`corrected-by` are for. Both are skipped, deliberately, rather than force a link `AC-8` in spec 0002 promises should point at two different things.
- **Letter-suffixed criteria are treated as `amended-by` their numeric parent**, flagged `relationship_type_ambiguous` throughout, because the text's own stated reason for the convention ("Criteria added as letter suffixes so revision 2's numbering still resolves") is about numbering, not explicitly about amendment semantics — the parent-child reading is the natural one but it's an inference, not a stated fact, for every one of these.
- **The binding rule 6 reference uses the new `label` endpoint, settled by AC-7's 2026-09-23 amendment.** The rule as AC-7 now states it: "`record` plus `label`, with `id` null, becomes the entity in that record whose own `label` matches once both are normalized (case folded, trimmed, internal whitespace collapsed to one space, punctuation untouched)." The endpoint shape here is taken verbatim from that amendment's own corrected critical test scenario: `{record: "0001", id: null, label: "binding rule 6", mention: "Spec 0001's binding rule 6"}`. Four of AC-7's six matching rules bear on reading this example correctly: **"Matching is exact, never fuzzy"** and deliberately not name resolution's job; **"When an endpoint carries both `id` and `label`, `id` wins"**, so only one is set here; **"A struck entity is never a label match target"**; and **"When more than one unstruck entity in that record carries the identical normalized label, the reference cannot tell them apart, so it falls to `:Unresolved` rather than picking one."** Two outcomes are therefore both correct depending on the corpus, and neither is an extraction defect: a match resolves to that entity, while no match keeps `record` and `label` on the `:Unresolved` node rather than only the prose mention (AC-10). A match to an entity that exists but was held routes the link under `endpoint_not_accepted`, never to `:Unresolved` — AC-7 is explicit that this "is a routing concern as much as a resolution one."
- **Link direction and target pairing, stated because the target is inferred.** "Spec 0001's binding rule 6 amendment gains a third item, dated the same day" names what is amended (binding rule 6) but not, in that sentence, what amends it. The target is paired to `0008/AC-10b` because "dated the same day" points at Revision 6, whose stated content is AC-10b's addition. Direction follows AC-8, amended → amending. The pairing is an inference from an adjacent sentence, so the link carries `relationship_type_ambiguous`.
- A `## Key invariants` line "tightened" (Revision 6), the whole-document renumbering (Revision 2), and the AC-8 cap behavior change (Revision 3) still have no second, nameable identifier to link to, and none is fabricated a target. `label` does not rescue these: an unnamed "one `## Key invariants` line" carries no author label to match on, which is the difference between it and `binding rule 6`.
- **Revision 2's renumbering is a blanket statement about the whole document's numbering scheme, not an itemized old-id-to-new-id mapping** ("The acceptance criteria are renumbered, so an AC number cited in that review refers to revision 1."). Building specific old→new pairs from it would mean guessing which pre-renumbering number maps to which current one, which the text doesn't say. No relationship is constructed.
- **The cited review file is not linked either, and for a different reason than the items above.** `docs/reviews/2026-08-31-spec-0008-app-shell-and-navigation.md` isn't one of this schema's three Record kinds (`spec`, `scope_document`, `scope_feature`), so unlike the binding-rule-6 case, this isn't "the target is uncertain which node it resolves to" — there's no relationship claim being made about a review file at all. It's supporting citation for *why* revision 2 happened, the same category as a `rationale.md` pointer, not a link between two named things. Distinct from an unresolvable reference (which still gets emitted, per AC-7, and resolves to `:Unresolved`): here there's nothing to emit in the first place.

## Input

```text
Record: 0008
File: docs/specs/0008-app-shell-and-navigation/index.md
Section: Preamble
Unit kind: Preamble

---
# 0008. App shell and navigation

**Date**: 2026-08-31
**Status**: Accepted

**Revision 6, 2026-09-05.** **AC-10b added**, by spec [0014](../0014-apply-redirect-and-application-record/index.md) AC-20a, after a measured bug in feature 12. This spec made the proxy's session refresh survive into the forwarded request (AC-10) and never considered what that refresh does to a Server Action's response. It puts a re-render of the current route into it, and on `/search` that re-render re-runs the Adzuna search and spends one of 25 weekly calls. Spec 0014 had defended the action from the inside and could not have defended it from here. The proxy now withholds the refreshed cookie from an action response, keyed on the `next-action` header rather than on the route, so **AC-9 and AC-10a are unaffected and both `src/proxy.test.ts` assertions still pass unmodified**. One `## Key invariants` line is tightened to match. Spec 0001's binding rule 6 amendment gains a third item, dated the same day.

**Revision 5, 2026-08-31.** **AC-3a's signed in half was not buildable**, which is the same defect revision 4 found and fixed on the marketing half and left standing on this one. It said the `(app)` layout composes the signed in header once. AC-5 says each route passes its own `aria-current="page"` in and that no component computes it. A layout never learns the pathname (`layout.md` lines 238 to 242), so a header composed there can never be told which page it is on, and the two criteria cannot both hold. Found during the build and decided by the engineer on 2026-08-31: **each route under `(app)` composes the header itself**, the same shape the marketing side already uses. AC-3a is rewritten below, and the `## Decision` line, build plan step 11 and one `## Consequences` line are corrected to match. **AC-5 is unchanged**, because per page composition is what it always asked for. The options weighed, including the parallel route slot that would have kept the layout composing it, are recorded in [rationale.md](rationale.md).

**Revision 2, 2026-08-31.** The return path mechanism changed after the cross model review in [docs/reviews/2026-08-31-spec-0008-app-shell-and-navigation.md](../../reviews/2026-08-31-spec-0008-app-shell-and-navigation.md). Revision 1 had the proxy write the return cookie. It now echoes the requested path as a request header and writes nothing, and the provider Server Action writes the cookie. The acceptance criteria are renumbered, so an AC number cited in that review refers to revision 1.

**Revision 4, 2026-08-31.** The architect cross check ran a decision completeness pass (values an acceptance criterion needs whose source is unnamed) and found eight gaps, all closed here. The load bearing one: **revision 3's AC-5a was not buildable**, because it asked a layout to vary its navigation by page and a layout never learns the pathname, so the marketing header is now composed by each page instead. Also added: AC-5b naming `src/lib/return-path.ts` and `src/lib/landing-rule.ts` with the header and cookie strings fixed, AC-15a having `completeSignIn()` return its claims, AC-17a enumerating an errored session read at both routes that read one, AC-24a keeping `redirect()` outside every span, the three span names, `aria-current` on the nav, and `COPY-7`.

**Revision 3, 2026-08-31.** A second cold read of revision 2 (same review file, second round) confirmed the three severe findings resolved and raised nine more. Applied here: AC-7a (a genuine query error is still a failure, since AC-7's ban on `failure()` had over corrected against binding rule 5), AC-10 and AC-10a (the request headers must be re-derived before each `NextResponse.next()`, not hoisted, or the refreshed session cookie is lost instead of the pathname), AC-5a (the marketing navigation varies by page, so `/sign-in` ships no dead anchors), AC-14a (the deep link survives both error retry paths), and the AC-8 cap now omits rather than truncates. Criteria added as letter suffixes so revision 2's numbering still resolves.
---
```

## Output

```json
{
  "entities": [],
  "relationships": [
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-10", "mention": "AC-10"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-10b", "mention": "AC-10b"},
      "phrase": null,
      "date": "2026-09-05",
      "known_trap_flags": []
    },
    {
      "type": "unclassified",
      "source": {"kind": "reference", "record": "0008", "id": "AC-10b", "mention": "AC-10b"},
      "target": {"kind": "reference", "record": "0014", "id": "AC-20a", "mention": "spec 0014 AC-20a"},
      "phrase": "**AC-10b added**, by spec 0014 AC-20a, after a measured bug in feature 12.",
      "date": "2026-09-05",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0001", "id": null, "label": "binding rule 6", "mention": "Spec 0001's binding rule 6"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-10b", "mention": "AC-10b"},
      "phrase": "Spec 0001's binding rule 6 amendment gains a third item, dated the same day.",
      "date": "2026-09-05",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-7", "mention": "AC-7"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-7a", "mention": "AC-7a"},
      "phrase": "AC-7a (a genuine query error is still a failure, since AC-7's ban on `failure()` had over corrected against binding rule 5)",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-10", "mention": "AC-10"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-10a", "mention": "AC-10a"},
      "phrase": "AC-10 and AC-10a (the request headers must be re-derived before each `NextResponse.next()`, not hoisted, or the refreshed session cookie is lost instead of the pathname)",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-5", "mention": "AC-5"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-5a", "mention": "AC-5a"},
      "phrase": "AC-5a (the marketing navigation varies by page, so `/sign-in` ships no dead anchors)",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-14", "mention": "AC-14"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-14a", "mention": "AC-14a"},
      "phrase": "AC-14a (the deep link survives both error retry paths)",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-5", "mention": "AC-5"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-5b", "mention": "AC-5b"},
      "phrase": "AC-5b naming `src/lib/return-path.ts` and `src/lib/landing-rule.ts` with the header and cookie strings fixed",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-15", "mention": "AC-15"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-15a", "mention": "AC-15a"},
      "phrase": "AC-15a having `completeSignIn()` return its claims",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-17", "mention": "AC-17"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-17a", "mention": "AC-17a"},
      "phrase": "AC-17a enumerating an errored session read at both routes that read one",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "amended-by",
      "source": {"kind": "reference", "record": "0008", "id": "AC-24", "mention": "AC-24"},
      "target": {"kind": "reference", "record": "0008", "id": "AC-24a", "mention": "AC-24a"},
      "phrase": "AC-24a keeping `redirect()` outside every span",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    }
  ]
}
```

## Rules this example demonstrates

- A unit can legitimately produce zero entities and several relationships — that's not an empty/failed extraction, it's the correct read of a unit that only narrates changes to things defined elsewhere.
- Every endpoint here is `reference`, never `local`, including references to the unit's own spec number — `local` is scoped to the output, not the document.
- A relationship is only constructed when both endpoints are genuinely distinguishable. Two mentions of the identical id, with no other identifying detail, do not make a valid old/new pair — skip it rather than build a self-loop.
- A reference to a named but unnumbered item carries `{record, label, mention}` with `id` null. The `label` is the author's own name for the item, copied exactly and nothing more (`binding rule 6`, not `Spec 0001's binding rule 6`); the full phrase stays in `mention`. An item with no author-given name at all ("one `## Key invariants` line") still gets no link, because there is no label to match on.
- An inferred parent-child link (a letter suffix implying amendment of its numeric parent) is still constructed, but flagged every time, consistently — inference is not fabrication, but it isn't free either.
- `phrase` and `mention` preserve the source's backticks and bold exactly, same rule as `span`/`rejected_spans` in the 0012 example, for the same reason: they're citations meant to be checked against the source, not paraphrases.
- **Exception, stated explicitly rather than left to guess: a markdown link `[label](url)` inside `phrase`/`mention` is reduced to its visible label.** Unlike backticks or bold, the link's target is already carried structurally in the `record` field — repeating the raw `[0014](../0014-.../index.md)` syntax inside a text field would duplicate that URL in an unstructured form with no alignment benefit, since a `ReferenceEndpoint` carries no `line` of its own for `locate_line()` to align against (only an entity's `span` does). `phrase`/`mention` are for a human or the loader to verify the citation, not for byte-level source alignment the way `span` is.
- `phrase` is optional on a named relationship type (only `unclassified` requires it). Where no single verbatim substring cleanly names both endpoints together (the AC-10/AC-10b `amended-by` link — AC-10b's addition and its cause are stated in one place, its relation to AC-10 in another), `phrase` is left null rather than assembled from an approximate paraphrase.
