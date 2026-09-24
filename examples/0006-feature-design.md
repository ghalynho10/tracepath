# Worked example: 0006 `## Feature design` (excerpt)

Drafted for tracepath's `SYSTEM_PROMPT` (read from `main` at `dbdd5cb`, schema at `src/tracepath/extract/schema.py`). Validates against today's schema — no reference `label`, so it does not wait on build plan task 17.

First example covering `TestScenario` and `verifies`, which is what AC-14's coverage set added this unit kind to reach.

## What this example covers, and what it deliberately leaves

`## Feature design` is the largest and most heterogeneous unit kind in the corpus (mean 15,407 characters; 14,327 here, across **13 bold sub-labels**), and the one real runs disagreed on most. **The input below is a contiguous verbatim excerpt: the last 5,118 characters, from `**Key invariants**` to the end of the section.** Everything inside that excerpt is extracted; nothing inside it is skipped.

The excerpt is deliberate, and the alternative was worse. Showing the whole section with only part of it extracted would teach exactly the failure an example teaches best: that a `## Feature design` run may return the test scenarios and quietly drop the rest. A complete extraction of a contiguous excerpt teaches "extract everything that qualifies" without teaching omission anywhere.

**What is outside the excerpt, and what that does not mean.** Eight sub-labels precede it: `Data model sketch`, `State transitions`, `API surface`, `Value sourcing`, `Copy`, `Smaller composition calls`, `Component inventory`, and `The hero card's <figure> wrapper`. They are not outside because they yield nothing:

- **Two genuinely yield nothing**: `Data model sketch` and `State transitions` both read "Not applicable."
- **Three are reference tables** (`API surface`, `Value sourcing`, `Component inventory`). A table row is a lookup keyed by its first cell, not a claim that stands alone — "Render page | section rhythm tier, per section | spec 0005 `rationale.md`" answers none of the type questions and produces a span no aligner can place. A whole-unit run should return nothing from these.
- **Three do carry real claims** (`Copy`'s four labelled `COPY-N` strings, `Smaller composition calls`' six design decisions, the `<figure>` wrapper's rule about not widening spec 0005's `as` union). **A whole-unit run should extract these.** They are absent here only because the excerpt starts after them, not because they fail any test.

## Reasoning notes

- **`TestScenario` carries the author's own name in `label`** — `Structural`, `Drift guard`, `Happy path`, `Font licence` and so on. These are unnumbered items with author-given names, which is exactly what `label` is for, and what a `{record, label}` reference endpoint (AC-7) would later match against.
- **The `Key invariants` bullets carry no `label`, and that contrast is the point.** Spec 0002's schema names `key invariant 1` as a sample label, but *this* spec's invariants are unnumbered, unnamed bullets. A label is copied when the author wrote one and invented never.
- **`verifies` runs TestScenario → AcceptanceCriterion**, per spec 0002's relationship table, and every target is `{record: "0006", id: "AC-N"}` — the scenarios verify their own spec's criteria, and this unit *is* 0006, so no inference is needed about which record the ids belong to (unlike the feature-21 row, where the record came from a pointer line).
- **"Binding rule 6 is untouched" produces no relationship.** A claim that a rule is *not* affected is not a link: relationships record relations that exist, and "untouched" records one that does not. The claim itself is extracted as a `Constraint`; only the link is withheld. Without this rule, every "X is unaffected" sentence in the corpus would manufacture an edge asserting the opposite of what it says.
- **Scenario 5's `Split 2026-08-29 by spec 0007` is `amended-by`, flagged.** Half the check retires and "The apply half stays and still runs", so the scenario's core claim survives — that is amendment, not supersession. It is the same partial-scope shape as 0012 Build plan step 3, and carries `relationship_type_ambiguous` for the same reason: the stated type is wider than what actually changed.
- The test-scenario intro is extracted as a `Constraint`, because "`automated` means it belongs in the Vitest unit suite and fails in CI; `manual` means it belongs in this spec's `verify.md`" is a standing rule about where tests live, not commentary.

## Input

```text
Record: 0006
File: docs/specs/0006-entry-page-and-link-metadata/index.md
Section: Feature design
Unit kind: Section

--- (excerpt: from **Key invariants** to the end of the section)
**Key invariants**:

- Exactly one hairline divider exists on the page. A second one means the background alternation was changed without applying spec 0005's adjacency rule.
- The page renders no `"use client"` file. Any future interactivity here opens its own narrow boundary and states why, rather than making the page a client component the way the prototype was.
- Nothing appears under `working` in the status card that is not `done` in `docs/scope/scope.md`. The page's own About copy makes this a promise, not a preference.
- Nothing on the page that cannot work is a link. That covers the two sign in controls and the apply control alike; the header's anchors and the footer are the only real links, and both go somewhere real.
- The elevated card idiom appears exactly once on this page, on the hero result card.
- The font guard in `opengraph-image.tsx` stays. It looks like a redundant `try`/`catch` around a file read and it is not: it is the only thing standing between a missing font and a silently off brand preview card, because `next/og` falls back to its bundled Geist rather than failing. Removing it does not surface an error, it removes one.

**Security model**: The page is public and reads nothing. No session check, no Supabase client, no Server Action, no user data of any kind. It renders no personal data, so no compliance scope applies. Binding rule 6 is untouched: no route handler under `src/app/api/` is added, and the image generator is a metadata file convention, not a data endpoint.

**Observability**: No Sentry span. The project's span rule covers operations whose failure rate matters; a static prerender has no runtime failure rate to alert on, and spec 0002 already points the uptime monitor at this page, which is the truer signal.

**Configuration required**: None. `NEXT_PUBLIC_SITE_URL` already exists and is already validated in `src/env.ts`. No new environment variable, no credential, no third party account.

**Critical test scenarios**. Each is tagged with where it lives, because spec 0005 keeps a clean split between what its unit suite can prove and what only a real browser can, and this feature keeps that split. `automated` means it belongs in the Vitest unit suite and fails in CI. `manual` means it belongs in this spec's `verify.md`, written later by `/check verify`, and no CI job enforces it.

- `automated` Structural: exactly one `divider="hairline"` is passed across the whole composed page, verifies **AC-3**.
- `automated` Drift guard, with its own vacuousness check: changing any one of the five named tokens in `globals.css` without touching `opengraph-image.tsx` must fail the test, verifies **AC-16**.
- `automated` Regression: nothing the route renders carries `"use client"`, verifies **AC-4**.
- `automated` Rhythm and background: each section receives the tier and background this spec assigns, verifies **AC-2**, **AC-3**.
- `automated` No dead controls: no apply control renders as an anchor, verifies **AC-17**. **Split 2026-08-29 by spec [0007](../0007-auth-and-per-user-isolation/index.md)**: the sign in half of this check retires with **AC-7**, because feature 7 turns those two controls into real submits. The apply half stays and still runs.
- `manual` Happy path: the page renders at 1440 and at 320 pixels with no horizontal overflow and the three rhythm tiers measurably distinct in computed style, verifies **AC-2**, **AC-14**.
- `manual` Keyboard: every control is reachable in order with a visible focus ring, and the header's sign in anchor moves focus to the band, verifies **AC-14**.
- `manual` Link card: the deployed preview URL unfurls with a real 1200 by 630 image, a title and a description, in at least two clients, verifies **AC-10**, **AC-11**.
- `manual` Honesty, both directions: the status card's `working` list contains nothing the scope still marks `planned`, and its `planned` list contains nothing that has no scope row at all. Deliberately a human read: the source is prose in `docs/scope/scope.md`, and a test asserting against it would only encode the same reading twice, verifies **AC-8**.
- `automated` Lint: `pnpm lint` passes with `--max-warnings=0`, which is what actually enforces the no hand composed container rule, verifies **AC-1**.
- `automated` Card idioms: exactly one `tone="elevated"` is rendered on the page, and the comparison and status cards are all `tone="flat"`, verifies **AC-5**.
- `automated` Band: the sign in band renders neither a centring nor a narrowing class, so Tell #7's two removed axes cannot creep back, verifies **AC-6**.
- `automated` Example label: the hero `<figure>` carries its `aria-label` and the `COPY-2` eyebrow is present, verifies **AC-9**.
- `automated` Robots: `layout.tsx` still exports `robots: { index: false, follow: false }`, and no `robots.ts` or `robots.txt` exists anywhere in the repo, verifies **AC-12**.
- `automated` Footer: it renders the lockup and the copyright and nothing between them, verifies **AC-13**.
- `automated` Font licence: the committed `.ttf` has a licence file beside it, so the binary can never land alone, verifies **AC-15**.
---
```

## Output

```json
{
  "entities": [
    {
      "id": "derived:1",
      "id_source": "derived",
      "type": "Constraint",
      "span": "Exactly one hairline divider exists on the page.",
      "rejected_spans": [
        "A second one means the background alternation was changed without applying spec 0005's adjacency rule."
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:2",
      "id_source": "derived",
      "type": "Constraint",
      "span": "The page renders no `\"use client\"` file. Any future interactivity here opens its own narrow boundary and states why",
      "rejected_spans": [
        "rather than making the page a client component the way the prototype was"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:3",
      "id_source": "derived",
      "type": "Constraint",
      "span": "Nothing appears under `working` in the status card that is not `done` in `docs/scope/scope.md`.",
      "rejected_spans": [
        "The page's own About copy makes this a promise, not a preference."
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:4",
      "id_source": "derived",
      "type": "Constraint",
      "span": "Nothing on the page that cannot work is a link. That covers the two sign in controls and the apply control alike; the header's anchors and the footer are the only real links, and both go somewhere real.",
      "rejected_spans": [],
      "known_trap_flags": ["embedded_second_claim"]
    },
    {
      "id": "derived:5",
      "id_source": "derived",
      "type": "Constraint",
      "span": "The elevated card idiom appears exactly once on this page, on the hero result card.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:6",
      "id_source": "derived",
      "type": "Constraint",
      "span": "The font guard in `opengraph-image.tsx` stays.",
      "rejected_spans": [
        "It looks like a redundant `try`/`catch` around a file read and it is not: it is the only thing standing between a missing font and a silently off brand preview card, because `next/og` falls back to its bundled Geist rather than failing. Removing it does not surface an error, it removes one."
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:7",
      "id_source": "derived",
      "type": "Constraint",
      "span": "**Security model**: The page is public and reads nothing. No session check, no Supabase client, no Server Action, no user data of any kind. It renders no personal data, so no compliance scope applies.",
      "rejected_spans": [],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:8",
      "id_source": "derived",
      "type": "Constraint",
      "span": "Binding rule 6 is untouched: no route handler under `src/app/api/` is added, and the image generator is a metadata file convention, not a data endpoint.",
      "rejected_spans": [],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:9",
      "id_source": "derived",
      "type": "Constraint",
      "span": "**Observability**: No Sentry span.",
      "rejected_spans": [
        "The project's span rule covers operations whose failure rate matters; a static prerender has no runtime failure rate to alert on, and spec 0002 already points the uptime monitor at this page, which is the truer signal."
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:10",
      "id_source": "derived",
      "type": "Constraint",
      "span": "**Configuration required**: None. `NEXT_PUBLIC_SITE_URL` already exists and is already validated in `src/env.ts`. No new environment variable, no credential, no third party account.",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:11",
      "id_source": "derived",
      "type": "Constraint",
      "span": "**Critical test scenarios**. Each is tagged with where it lives. `automated` means it belongs in the Vitest unit suite and fails in CI. `manual` means it belongs in this spec's `verify.md`, written later by `/check verify`, and no CI job enforces it.",
      "rejected_spans": [
        "because spec 0005 keeps a clean split between what its unit suite can prove and what only a real browser can, and this feature keeps that split"
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:12",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Structural: exactly one `divider=\"hairline\"` is passed across the whole composed page, verifies **AC-3**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Structural"
    },
    {
      "id": "derived:13",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Drift guard, with its own vacuousness check: changing any one of the five named tokens in `globals.css` without touching `opengraph-image.tsx` must fail the test, verifies **AC-16**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Drift guard"
    },
    {
      "id": "derived:14",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Regression: nothing the route renders carries `\"use client\"`, verifies **AC-4**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Regression"
    },
    {
      "id": "derived:15",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Rhythm and background: each section receives the tier and background this spec assigns, verifies **AC-2**, **AC-3**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Rhythm and background"
    },
    {
      "id": "derived:16",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` No dead controls: no apply control renders as an anchor, verifies **AC-17**.",
      "rejected_spans": [
        "**Split 2026-08-29 by spec 0007**: the sign in half of this check retires with **AC-7**, because feature 7 turns those two controls into real submits. The apply half stays and still runs."
      ],
      "known_trap_flags": [],
      "label": "No dead controls"
    },
    {
      "id": "derived:17",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`manual` Happy path: the page renders at 1440 and at 320 pixels with no horizontal overflow and the three rhythm tiers measurably distinct in computed style, verifies **AC-2**, **AC-14**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Happy path"
    },
    {
      "id": "derived:18",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`manual` Keyboard: every control is reachable in order with a visible focus ring, and the header's sign in anchor moves focus to the band, verifies **AC-14**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Keyboard"
    },
    {
      "id": "derived:19",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`manual` Link card: the deployed preview URL unfurls with a real 1200 by 630 image, a title and a description, in at least two clients, verifies **AC-10**, **AC-11**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Link card"
    },
    {
      "id": "derived:20",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`manual` Honesty, both directions: the status card's `working` list contains nothing the scope still marks `planned`, and its `planned` list contains nothing that has no scope row at all, verifies **AC-8**.",
      "rejected_spans": [
        "Deliberately a human read: the source is prose in `docs/scope/scope.md`, and a test asserting against it would only encode the same reading twice"
      ],
      "known_trap_flags": ["rationale_boundary_call"],
      "label": "Honesty, both directions"
    },
    {
      "id": "derived:21",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Lint: `pnpm lint` passes with `--max-warnings=0`, verifies **AC-1**.",
      "rejected_spans": [
        "which is what actually enforces the no hand composed container rule"
      ],
      "known_trap_flags": [],
      "label": "Lint"
    },
    {
      "id": "derived:22",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Card idioms: exactly one `tone=\"elevated\"` is rendered on the page, and the comparison and status cards are all `tone=\"flat\"`, verifies **AC-5**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Card idioms"
    },
    {
      "id": "derived:23",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Band: the sign in band renders neither a centring nor a narrowing class, verifies **AC-6**.",
      "rejected_spans": [
        "so Tell #7's two removed axes cannot creep back"
      ],
      "known_trap_flags": [],
      "label": "Band"
    },
    {
      "id": "derived:24",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Example label: the hero `<figure>` carries its `aria-label` and the `COPY-2` eyebrow is present, verifies **AC-9**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Example label"
    },
    {
      "id": "derived:25",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Robots: `layout.tsx` still exports `robots: { index: false, follow: false }`, and no `robots.ts` or `robots.txt` exists anywhere in the repo, verifies **AC-12**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Robots"
    },
    {
      "id": "derived:26",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Footer: it renders the lockup and the copyright and nothing between them, verifies **AC-13**.",
      "rejected_spans": [],
      "known_trap_flags": [],
      "label": "Footer"
    },
    {
      "id": "derived:27",
      "id_source": "derived",
      "type": "TestScenario",
      "span": "`automated` Font licence: the committed `.ttf` has a licence file beside it, verifies **AC-15**.",
      "rejected_spans": [
        "so the binary can never land alone"
      ],
      "known_trap_flags": [],
      "label": "Font licence"
    }
  ],
  "relationships": [
    {"type": "verifies", "source": {"kind": "local", "id": "derived:12"}, "target": {"kind": "reference", "record": "0006", "id": "AC-3", "mention": "**AC-3**"}, "phrase": "verifies **AC-3**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:13"}, "target": {"kind": "reference", "record": "0006", "id": "AC-16", "mention": "**AC-16**"}, "phrase": "verifies **AC-16**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:14"}, "target": {"kind": "reference", "record": "0006", "id": "AC-4", "mention": "**AC-4**"}, "phrase": "verifies **AC-4**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:15"}, "target": {"kind": "reference", "record": "0006", "id": "AC-2", "mention": "**AC-2**"}, "phrase": "verifies **AC-2**, **AC-3**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:15"}, "target": {"kind": "reference", "record": "0006", "id": "AC-3", "mention": "**AC-3**"}, "phrase": "verifies **AC-2**, **AC-3**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:16"}, "target": {"kind": "reference", "record": "0006", "id": "AC-17", "mention": "**AC-17**"}, "phrase": "verifies **AC-17**", "date": null, "known_trap_flags": []},
    {"type": "amended-by", "source": {"kind": "local", "id": "derived:16"}, "target": {"kind": "reference", "record": "0007", "id": null, "mention": "spec 0007"}, "phrase": "**Split 2026-08-29 by spec 0007**: the sign in half of this check retires with **AC-7**", "date": "2026-08-29", "known_trap_flags": ["relationship_type_ambiguous"]},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:17"}, "target": {"kind": "reference", "record": "0006", "id": "AC-2", "mention": "**AC-2**"}, "phrase": "verifies **AC-2**, **AC-14**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:17"}, "target": {"kind": "reference", "record": "0006", "id": "AC-14", "mention": "**AC-14**"}, "phrase": "verifies **AC-2**, **AC-14**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:18"}, "target": {"kind": "reference", "record": "0006", "id": "AC-14", "mention": "**AC-14**"}, "phrase": "verifies **AC-14**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:19"}, "target": {"kind": "reference", "record": "0006", "id": "AC-10", "mention": "**AC-10**"}, "phrase": "verifies **AC-10**, **AC-11**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:19"}, "target": {"kind": "reference", "record": "0006", "id": "AC-11", "mention": "**AC-11**"}, "phrase": "verifies **AC-10**, **AC-11**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:20"}, "target": {"kind": "reference", "record": "0006", "id": "AC-8", "mention": "**AC-8**"}, "phrase": "verifies **AC-8**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:21"}, "target": {"kind": "reference", "record": "0006", "id": "AC-1", "mention": "**AC-1**"}, "phrase": "verifies **AC-1**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:22"}, "target": {"kind": "reference", "record": "0006", "id": "AC-5", "mention": "**AC-5**"}, "phrase": "verifies **AC-5**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:23"}, "target": {"kind": "reference", "record": "0006", "id": "AC-6", "mention": "**AC-6**"}, "phrase": "verifies **AC-6**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:24"}, "target": {"kind": "reference", "record": "0006", "id": "AC-9", "mention": "**AC-9**"}, "phrase": "verifies **AC-9**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:25"}, "target": {"kind": "reference", "record": "0006", "id": "AC-12", "mention": "**AC-12**"}, "phrase": "verifies **AC-12**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:26"}, "target": {"kind": "reference", "record": "0006", "id": "AC-13", "mention": "**AC-13**"}, "phrase": "verifies **AC-13**", "date": null, "known_trap_flags": []},
    {"type": "verifies", "source": {"kind": "local", "id": "derived:27"}, "target": {"kind": "reference", "record": "0006", "id": "AC-15", "mention": "**AC-15**"}, "phrase": "verifies **AC-15**", "date": null, "known_trap_flags": []}
  ]
}
```

## Rules this example demonstrates

- `TestScenario` → `verifies` → `AcceptanceCriterion` is the whole reason this unit kind is in AC-14's coverage set; a scenario that cites more than one criterion emits one link per criterion, each keeping the full citation as its `phrase`.
- A `label` is copied when the author gave the item a name (`Happy path`, `Font licence`) and left null when they did not (every `Key invariants` bullet). Labels are never invented to fill the field.
- A claim that something is *unaffected* ("Binding rule 6 is untouched") produces an entity and no relationship. A link records a relation that exists; asserting the absence of one must not manufacture its opposite.
- A tagging convention stated in prose (`automated` versus `manual`, and where each lives) is a `Constraint`, not commentary.
- A change that retires part of an item while the rest keeps running is `amended-by`, not `superseded-by`, flagged because the stated type is wider than the actual scope — the same shape as a partial supersession.
- An example may cover an excerpt, but it must extract that excerpt completely, and say what lies outside it and whether a whole-unit run should return anything from there. A partial extraction of a whole unit teaches skipping.
- **A bold sub-label never becomes an entity's `label`.** `label` names an *item* a reference can point at; a sub-label names a *block*, and any block can be split. Using one as a label makes the label depend on how a given run split that block, which ties the label index (AC-7 resolves a tie to `:Unresolved`) and manufactures run-to-run disagreement now that labels join the comparison signature (AC-11e). The same choice would break both.
- **Where the source writes a sub-label inline with its claim (`**Observability**: No Sentry span.`), the span starts at the sub-label**, because it is contiguous verbatim source text and the claim is unreadable without it — "No Sentry span." alone cites a sentence that says nothing. **Where a sub-label heads a list, no bullet repeats it**, because each bullet already stands alone and the sub-label is not contiguous with any of them. The source's own typography decides this, not a count of entities.
- A `label` is set only on an entity that is the whole of the item the author named. If an item carrying a label is split, the label travels to neither half.
