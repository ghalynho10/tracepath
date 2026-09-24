# Worked example: `feature-21` scope row

Drafted for tracepath's `SYSTEM_PROMPT` (read from `main` at `dbdd5cb`, schema at `src/tracepath/extract/schema.py`). Validates against today's schema — it carries no reference `label`, so it does not wait on build plan task 17.

First example covering the `FeatureRow` unit kind, and the `Feature` and `Constraint` entity types.

## Reasoning notes

### What each endpoint resolves to today

This is the one unit kind where record identity differs from the document it sits in, so it is worth being explicit rather than assuming:

- **The unit's own record is `feature-21`**, not `scope`. Code creates that Record and attaches every entity here to it (`PART_OF`); the model never writes it.
- **`{record: "0009", id: "AC-N"}` resolves today.** Spec 0009 is a real `spec` Record and the ids are verbatim `AC-N` tokens, so these become `0009/AC-4` and so on. The record number is inferred from this unit's own pointer line, `_spec [0009](…)_` — the AC citations themselves never name a spec.
- **`{record: "feature 7"}`, `{record: "feature 32"}`, `{record: "feature 11"}`, `{record: "feature 13"}`, `{record: "feature 14"}` all resolve to `:Unresolved` today.** A scope feature Record's `canonical_id` is hyphenated (`feature-7`), and the `feature N` form the prose uses lives in that Record's `aliases`, whose stated job is to carry alternative names *until name resolution (feature 7) does the matching*. Feature 7 is not built, so nothing matches an alias yet. The links are still emitted, carrying their verbatim mentions — that gap being visible is what `:Unresolved` is for, and it is not an extraction defect.
- **No `SPECIFIED_BY` link is emitted at all.** Spec 0002's value-sourcing table assigns it to code: "the row's pointer line `_spec [NNNN](...)_`, parsed by code". Same rule as `struck` and `followup_status` — deterministic structure the model must not duplicate. Line 7 of this unit therefore produces no entity and no relationship.

### Extraction calls

- **A scope row mixes types that a spec section usually separates.** One row holds the capability (`Feature`), its acceptance clause (`AcceptanceCriterion`), standing rules (`Constraint`), an accepted tradeoff (`Consequence`), and its build checkboxes (`BuildStep`). Typing each by what it claims, not by where it sits, is what keeps `unclassified` rare here.
- **The `Done when:` sub-label is carried inline in the span, not in `label`.** The clause is unreadable without it, and it stays verbatim-contiguous that way. It is not a `label`: this entity is flagged `multi_condition_split`, so a run could split its three conditions, and three halves each carrying `label: "Done when"` would tie the label index (AC-7 resolves a tie to `:Unresolved`) while disagreeing across runs (AC-11e). See the 0006 example for `label` used as intended, on items the author named individually.
- **Two `Constraint`s are pulled out of paragraphs that are otherwise rationale**, both flagged `embedded_second_claim`: the `usejobhunt.dev` serving requirement inside the slice-move note, and the obligation on later features to add themselves to the notice. Both survive the deletion trick as claims in their own right while everything around them explains *why the row moved* or *why the list is incomplete*.
- **The slice-move note is `unclassified`.** "Moved here from Slice 5 on 2026-08-31, to build after feature 32" is a real, substantial scheduling record that answers none of the named types' questions — it is not a requirement, a consequence, a build step or a test. It carries `entity_type_ambiguous`, as every `unclassified` entity must.
- **"Depends on feature 7, both ways" is `unclassified`, not `blocked-by`.** `blocked-by` is directional (blocked → blocker) and the text says the dependency runs both ways, which the named type cannot express. The verbatim phrase carries what the type cannot.
- **"all 23 acceptance criteria met" produces no links, and this is the deliberate contrast with 0012's Build plan step 9.** There, `satisfies **AC-1** through **AC-8**` names both endpoints of a range and expands to eight links. Here, "all 23" names a *count*, not endpoints — expanding it would invent 23 ids the text never writes. A stated range is enumerable; a stated total is not.

## Input

```text
Record: feature-21
File: docs/scope/scope.md
Section: 21. Terms & privacy notices · done · Alpha
Unit kind: FeatureRow

---
### 21. Terms & privacy notices · done · Alpha
A plain terms page and a privacy notice saying what is stored, why, and how to have it deleted. Owed the day the first person other than the author signs in, because real resumes and personal details are in the database from Slice 1 onward. Written against the actual data model rather than from a template, so it is accurate.
**Done when:** both pages exist and are linked from the entry page and from sign in, the privacy notice names the real stored fields and the real third parties data reaches, and a user can find out how to request deletion.
_Moved here from Slice 5 on 2026-08-31, to build after feature 32. **The reason is a meter that only runs one way.** This feature is what lifts Google's 100 user cap: the Publish app button is greyed because the privacy policy and terms links are empty, and these pages are what fills them. Until then the app stays in Testing, capped at 100 users, and Google counts that cap over the app's whole lifetime, so it never resets. Every person who signs in before these pages exist spends one of those slots permanently, which is why waiting until launch readiness was the wrong place for it. The pages must be served from `usejobhunt.dev`, because Google will not accept a `vercel.app` address as an authorised domain. Publishing is also the remaining fix for the consent screen naming a Supabase host instead of JobHunt._
_Depends on feature 7, both ways, recorded from spec [0007](../specs/0007-auth-and-per-user-isolation/index.md) on 2026-08-31. Feature 7 is what makes these notices load bearing rather than paperwork: the privacy notice must describe what arrives from the provider into `auth.users`, meaning the email address, the display name and the avatar URL._
_**Building it early means the third party list is incomplete on the day it ships, and that is accepted rather than overlooked.** At this point in the build the real third parties are Supabase, Vercel, Sentry, Google and GitHub. Adzuna arrives at feature 11 and the model providers at features 13 and 14, so each of those features must add itself to the notice as part of its own build. A privacy notice that silently stops matching where data actually goes is worse than one written later, so the revisit is named here rather than left to be noticed._
_spec [0009](../specs/0009-terms-and-privacy-notices/index.md) · code in `src/features/legal/`, `src/app/(marketing)/terms/`, `src/app/(marketing)/privacy/`_
- [x] Design it (spec): `/architect terms & privacy notices` · written 2026-09-01, 23 acceptance criteria. **This box did not exist before today**, although the legend says every feature carries exactly one, which is why nothing flagged that a spec was owed when `/develop` was run against this row. The spec is written from the code rather than a template: the field list comes from the applied migration, the Sentry claim from the running configuration, and the deletion procedure from the actual cascade direction, which corrected the plan we started from. A cross check on a different model confirmed all five factual claims against the repo and found six gaps, all folded in; the load bearing one was that the stored field list had no drift guard while the recipient list did
- [x] Build it: `/develop terms & privacy notices`
  - [x] The two typed registries (recipients, stored fields) and the three guard tests, plus the Sentry regression test · **AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**. Each guard was proved to fail on real drift before being trusted: an unaccounted `src/env.ts` key, an unnamed column, a new unclassified table, a flipped Sentry `userInfo`, and an analytics dependency each fail the suite. One deviation from the spec's invariant 2, recorded in `recipients.ts`: three env keys reach no third party at all, so they are classified in a named `ENV_KEYS_WITH_NO_RECIPIENT` list with a reason each, rather than forced under a company, which would have put a false sentence on the page. The forcing function is unchanged
  - [x] The two routes under `(marketing)`, indexable, with their own metadata, linked from the entry page footer's reserved slot and from a static line under the provider forms on `/sign-in` · **AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**. Both build as static prerenders (`○` in the build output) and a source level test holds the no client JavaScript rule across both routes plus `/sign-in`. Two spec 0006 footer assertions changed shape here rather than being deleted: AC-13 protected the reserved centre slot by forbidding everything in it, which stopped being possible once something belonged there
  - [x] The privacy notice's content: stored fields, recipients, the Sentry claim, retention, the deletion procedure and contact address, the responsible party, lawful basis and rights, the Google disclosure, cookies · **AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**. Both lists are rendered from the registries, and the page test fails if a field the registry names is not printed, so a current registry cannot sit behind a page that says nothing
  - [x] The terms content and effective dates, then the mail delivery check and the Google console work: authorized domain, both URLs, publish out of Testing, submit brand verification · **AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**. The terms content and both effective dates landed with the code; mail delivery and all four console steps were done by the engineer on 2026-09-01, after the merge. **The console half is confirmed from outside Google's console rather than taken on trust**, by starting a real sign in against production with no Google session: the screen reads "to continue to JobHunt" with the JobHunt mark beside it, not the Supabase host, which closes the finding spec 0007 recorded on 2026-08-30 (**AC-22**); and Google itself surfaces "you can review JobHunt's Privacy Policy and Terms of Service" linking `https://usejobhunt.dev/privacy` and `https://usejobhunt.dev/terms`, which is the console's two URL fields read back out (**AC-21**). The requested scope is `email profile` and nothing more, which is also why the notice carries no Limited Use affirmation. Both pages return 200 on the apex domain with no `x-robots-tag` header overriding their index metadata
- [x] Verify it: `/check verify terms & privacy notices` · run 2026-09-01, **PASS**, all 23 acceptance criteria met, 48 of 50 steps ticked in [verify.md](../specs/0009-terms-and-privacy-notices/verify.md). The six drift guards were each broken on purpose and confirmed to fail by name, so none of them is a test that cannot fail. The deletion cascade was proved on the real database rather than read off the migration: one throwaway account with a row in all six tables, delete the `auth.users` row alone, all six go. AC-21 and AC-22 were confirmed from outside Google's console, by starting a real sign in against production. The two unticked steps are recorded there and neither is an acceptance criterion failure; one of them surfaced a **separate, pre existing issue belonging to feature 7**, that the committed `database.types.ts` is missing `before_user_created_hook` and `provider_display_name` in its generated `Functions` block, while the `Tables` block this feature depends on is byte identical to the applied schema
---
```

## Output

```json
{
  "entities": [
    {
      "id": "derived:1",
      "id_source": "derived",
      "type": "Feature",
      "span": "A plain terms page and a privacy notice saying what is stored, why, and how to have it deleted. Owed the day the first person other than the author signs in. Written against the actual data model rather than from a template.",
      "rejected_spans": [
        "because real resumes and personal details are in the database from Slice 1 onward",
        "so it is accurate"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:2",
      "id_source": "derived",
      "type": "AcceptanceCriterion",
      "span": "**Done when:** both pages exist and are linked from the entry page and from sign in, the privacy notice names the real stored fields and the real third parties data reaches, and a user can find out how to request deletion.",
      "rejected_spans": [],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:3",
      "id_source": "derived",
      "type": "unclassified",
      "span": "Moved here from Slice 5 on 2026-08-31, to build after feature 32.",
      "rejected_spans": [
        "**The reason is a meter that only runs one way.** This feature is what lifts Google's 100 user cap: the Publish app button is greyed because the privacy policy and terms links are empty, and these pages are what fills them. Until then the app stays in Testing, capped at 100 users, and Google counts that cap over the app's whole lifetime, so it never resets. Every person who signs in before these pages exist spends one of those slots permanently, which is why waiting until launch readiness was the wrong place for it.",
        "Publishing is also the remaining fix for the consent screen naming a Supabase host instead of JobHunt."
      ],
      "known_trap_flags": ["entity_type_ambiguous"],
      "unclassified_note": "A scheduling record of when and why this row moved between slices. It states no requirement, outcome, build step or test, so none of the named types fits."
    },
    {
      "id": "derived:4",
      "id_source": "derived",
      "type": "Constraint",
      "span": "The pages must be served from `usejobhunt.dev`",
      "rejected_spans": [
        "because Google will not accept a `vercel.app` address as an authorised domain"
      ],
      "known_trap_flags": ["embedded_second_claim"]
    },
    {
      "id": "derived:5",
      "id_source": "derived",
      "type": "Constraint",
      "span": "the privacy notice must describe what arrives from the provider into `auth.users`, meaning the email address, the display name and the avatar URL.",
      "rejected_spans": [
        "Feature 7 is what makes these notices load bearing rather than paperwork"
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:6",
      "id_source": "derived",
      "type": "Consequence",
      "span": "**Building it early means the third party list is incomplete on the day it ships, and that is accepted rather than overlooked.** At this point in the build the real third parties are Supabase, Vercel, Sentry, Google and GitHub.",
      "rejected_spans": [
        "A privacy notice that silently stops matching where data actually goes is worse than one written later, so the revisit is named here rather than left to be noticed."
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:7",
      "id_source": "derived",
      "type": "Constraint",
      "span": "Adzuna arrives at feature 11 and the model providers at features 13 and 14, so each of those features must add itself to the notice as part of its own build.",
      "rejected_spans": [],
      "known_trap_flags": ["embedded_second_claim"]
    },
    {
      "id": "derived:8",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Design it (spec): `/architect terms & privacy notices` · written 2026-09-01, 23 acceptance criteria.",
      "rejected_spans": [
        "**This box did not exist before today**, although the legend says every feature carries exactly one, which is why nothing flagged that a spec was owed when `/develop` was run against this row.",
        "The spec is written from the code rather than a template: the field list comes from the applied migration, the Sentry claim from the running configuration, and the deletion procedure from the actual cascade direction, which corrected the plan we started from. A cross check on a different model confirmed all five factual claims against the repo and found six gaps, all folded in; the load bearing one was that the stored field list had no drift guard while the recipient list did"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:9",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Build it: `/develop terms & privacy notices`",
      "rejected_spans": [],
      "known_trap_flags": []
    },
    {
      "id": "derived:10",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "The two typed registries (recipients, stored fields) and the three guard tests, plus the Sentry regression test · **AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**.",
      "rejected_spans": [
        "Each guard was proved to fail on real drift before being trusted: an unaccounted `src/env.ts` key, an unnamed column, a new unclassified table, a flipped Sentry `userInfo`, and an analytics dependency each fail the suite.",
        "One deviation from the spec's invariant 2, recorded in `recipients.ts`: three env keys reach no third party at all, so they are classified in a named `ENV_KEYS_WITH_NO_RECIPIENT` list with a reason each, rather than forced under a company, which would have put a false sentence on the page. The forcing function is unchanged"
      ],
      "known_trap_flags": ["rationale_boundary_call"]
    },
    {
      "id": "derived:11",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "The two routes under `(marketing)`, indexable, with their own metadata, linked from the entry page footer's reserved slot and from a static line under the provider forms on `/sign-in` · **AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**.",
      "rejected_spans": [
        "Both build as static prerenders (`○` in the build output) and a source level test holds the no client JavaScript rule across both routes plus `/sign-in`.",
        "Two spec 0006 footer assertions changed shape here rather than being deleted: AC-13 protected the reserved centre slot by forbidding everything in it, which stopped being possible once something belonged there"
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:12",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "The privacy notice's content: stored fields, recipients, the Sentry claim, retention, the deletion procedure and contact address, the responsible party, lawful basis and rights, the Google disclosure, cookies · **AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**.",
      "rejected_spans": [
        "Both lists are rendered from the registries, and the page test fails if a field the registry names is not printed, so a current registry cannot sit behind a page that says nothing"
      ],
      "known_trap_flags": []
    },
    {
      "id": "derived:13",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "The terms content and effective dates, then the mail delivery check and the Google console work: authorized domain, both URLs, publish out of Testing, submit brand verification · **AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**.",
      "rejected_spans": [
        "The terms content and both effective dates landed with the code; mail delivery and all four console steps were done by the engineer on 2026-09-01, after the merge.",
        "**The console half is confirmed from outside Google's console rather than taken on trust**, by starting a real sign in against production with no Google session: the screen reads \"to continue to JobHunt\" with the JobHunt mark beside it, not the Supabase host, which closes the finding spec 0007 recorded on 2026-08-30 (**AC-22**); and Google itself surfaces \"you can review JobHunt's Privacy Policy and Terms of Service\" linking `https://usejobhunt.dev/privacy` and `https://usejobhunt.dev/terms`, which is the console's two URL fields read back out (**AC-21**).",
        "The requested scope is `email profile` and nothing more, which is also why the notice carries no Limited Use affirmation. Both pages return 200 on the apex domain with no `x-robots-tag` header overriding their index metadata"
      ],
      "known_trap_flags": ["multi_condition_split"]
    },
    {
      "id": "derived:14",
      "id_source": "derived",
      "type": "BuildStep",
      "span": "Verify it: `/check verify terms & privacy notices` · run 2026-09-01, **PASS**, all 23 acceptance criteria met, 48 of 50 steps ticked in verify.md.",
      "rejected_spans": [
        "The six drift guards were each broken on purpose and confirmed to fail by name, so none of them is a test that cannot fail. The deletion cascade was proved on the real database rather than read off the migration: one throwaway account with a row in all six tables, delete the `auth.users` row alone, all six go. AC-21 and AC-22 were confirmed from outside Google's console, by starting a real sign in against production.",
        "The two unticked steps are recorded there and neither is an acceptance criterion failure; one of them surfaced a **separate, pre existing issue belonging to feature 7**, that the committed `database.types.ts` is missing `before_user_created_hook` and `provider_display_name` in its generated `Functions` block, while the `Tables` block this feature depends on is byte identical to the applied schema"
      ],
      "known_trap_flags": []
    }
  ],
  "relationships": [
    {
      "type": "blocked-by",
      "source": {"kind": "local", "id": "derived:1"},
      "target": {"kind": "reference", "record": "feature 32", "id": null, "mention": "feature 32"},
      "phrase": "to build after feature 32",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:1"},
      "target": {"kind": "reference", "record": "feature 7", "id": null, "mention": "feature 7"},
      "phrase": "Depends on feature 7, both ways",
      "date": "2026-08-31",
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:7"},
      "target": {"kind": "reference", "record": "feature 11", "id": null, "mention": "feature 11"},
      "phrase": "each of those features must add itself to the notice as part of its own build",
      "date": null,
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:7"},
      "target": {"kind": "reference", "record": "feature 13", "id": null, "mention": "features 13 and 14"},
      "phrase": "each of those features must add itself to the notice as part of its own build",
      "date": null,
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "unclassified",
      "source": {"kind": "local", "id": "derived:7"},
      "target": {"kind": "reference", "record": "feature 14", "id": null, "mention": "features 13 and 14"},
      "phrase": "each of those features must add itself to the notice as part of its own build",
      "date": null,
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:10"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-4", "mention": "**AC-4**"},
      "phrase": "**AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:10"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-5", "mention": "**AC-5**"},
      "phrase": "**AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:10"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-6", "mention": "**AC-6**"},
      "phrase": "**AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:10"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-23", "mention": "**AC-23**"},
      "phrase": "**AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:10"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-14", "mention": "the enforcement half of **AC-14**"},
      "phrase": "**AC-4**, **AC-5**, **AC-6**, **AC-23**, and the enforcement half of **AC-14**",
      "date": null,
      "known_trap_flags": ["relationship_type_ambiguous"]
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:11"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-1", "mention": "**AC-1**"},
      "phrase": "**AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:11"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-17", "mention": "**AC-17**"},
      "phrase": "**AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:11"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-18", "mention": "**AC-18**"},
      "phrase": "**AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:11"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-19", "mention": "**AC-19**"},
      "phrase": "**AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:11"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-20", "mention": "**AC-20**"},
      "phrase": "**AC-1**, **AC-17**, **AC-18**, **AC-19**, **AC-20**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-2", "mention": "**AC-2**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-3", "mention": "**AC-3**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-7", "mention": "**AC-7**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-8", "mention": "**AC-8**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-10", "mention": "**AC-10**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-11", "mention": "**AC-11**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-12", "mention": "**AC-12**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-13", "mention": "**AC-13**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:12"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-14", "mention": "**AC-14**"},
      "phrase": "**AC-2**, **AC-3**, **AC-7**, **AC-8**, **AC-10**, **AC-11**, **AC-12**, **AC-13**, **AC-14**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:13"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-15", "mention": "**AC-15**"},
      "phrase": "**AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:13"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-16", "mention": "**AC-16**"},
      "phrase": "**AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:13"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-9", "mention": "**AC-9**"},
      "phrase": "**AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:13"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-21", "mention": "**AC-21**"},
      "phrase": "**AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**",
      "date": null,
      "known_trap_flags": []
    },
    {
      "type": "satisfies",
      "source": {"kind": "local", "id": "derived:13"},
      "target": {"kind": "reference", "record": "0009", "id": "AC-22", "mention": "**AC-22**"},
      "phrase": "**AC-15**, **AC-16**, **AC-9**, **AC-21**, **AC-22**",
      "date": null,
      "known_trap_flags": []
    }
  ]
}
```

## Rules this example demonstrates

- A scope row is its own Record (`feature-21`), and a reference written the way prose names a row (`feature 7`) resolves to `:Unresolved` until name resolution exists. The link is still emitted with its verbatim mention; a visible gap is the designed outcome, not a defect.
- A pointer line that code already parses (`_spec [NNNN](…)_` → `SPECIFIED_BY`) produces no entity and no relationship, the same rule that keeps `struck` and `followup_status` out of the model's output.
- AC citations inside a scope row belong to the spec that row points at, not to the scope document. The record number comes from the unit's own pointer line; nothing else in the row names it.
- **`Done when:` goes in the span, not in `label`.** It is a sub-label heading a block, and this entity is flagged `multi_condition_split` precisely because a run could split its three conditions — three halves all carrying `label: "Done when"` would tie the label index (AC-7 resolves a tie to `:Unresolved`) and disagree across runs (AC-11e). Carrying `**Done when:**` inline keeps the span readable on its own and stays verbatim-contiguous. `label` is reserved for a name the author gave one item, as the test scenarios in the 0006 example use it.
- A stated range is enumerable; a stated total is not. `AC-1 through AC-8` expands to eight links, `all 23 acceptance criteria met` expands to none. **The corpus proves why**: spec 0009 carries 24 acceptance criteria today — AC-24 was added on 2026-09-18 — while this row still reads "all 23". Expanding the total would have invented ids *and* been wrong about the count, in a row that is otherwise accurate. A range names its own endpoints and cannot drift like that; a total is a claim about a set the unit cannot see.
- `blocked-by` is directional, so a dependency the text says runs "both ways" takes `unclassified` with the verbatim phrase rather than being forced into it.
