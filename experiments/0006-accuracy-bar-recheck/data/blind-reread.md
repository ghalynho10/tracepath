# Blind self agreement, experiment 0006 (spec 0003, AC-30)

10 items drawn at random from experiment 0005's already ruled `ruling-sheet.md` (42 ruled items across groups A, B, C), seed `20260928002`. Rule each cold, as if seeing it for the first time; only once every item here is re-marked, open `blind-reread-answers.md` in this same directory and compare.

## Item 1
_Group C: feature-9 / 9-profile-entry-done (a different scope row than the example's) · Relationships_

- [x] agree · satisfies · written by 3 of 3 runs

  - source: `feature-9#9-profile-entry-done:9` BuildStep: Thin slice: the identity section end to end (create, reload, edit) via `saveIdentity` and the URL driven `/profile` page · AC-1 to AC-4, AC-11 to AC-14
  - target: reference `0010` AC-2, mention: AC-1 to AC-4, AC-11 to AC-14
  - phrase: AC-1 to AC-4, AC-11 to AC-14
  - source text:
    > - [x] Build it: `/develop profile entry`
    >   - [x] Four new base components (`Input`, `Textarea`, `Select`, a `Field`/`Label` wrapper) added to `src/components/ui/`, extending spec 0005's inventory the way spec 0006 added `Logo` · AC-17
    >   - [x] Thin slice: the identity section end to end (create, reload, edit) via `saveIdentity` and the URL driven `/profile` page · AC-1 to AC-4, AC-11 to AC-14
    >   - [x] Thicken: skills (the diff based save) and work history (per entry add, edit, delete with a confirmation step) · AC-5 to AC-8, AC-7a
    >   - [x] Thicken: search preferences, the new spans registered, and the entry page's `profile` claim moved to working · AC-9, AC-10, AC-16
    >   - [x] Proofs: the no browser Server Action test, two account isolation, and the `/ui-preview` keyboard/focus/contrast pass · AC-14, AC-15, AC-17

## Item 2
_Group C: feature-9 / 9-profile-entry-done (a different scope row than the example's) · Entities_

- [x] agree · `feature-9#9-profile-entry-done:9` · BuildStep

  - span: Thin slice: the identity section end to end (create, reload, edit) via `saveIdentity` and the URL driven `/profile` page · AC-1 to AC-4, AC-11 to AC-14

## Item 3
_Group A: 0021 / requirements (a unit kind with no worked example) · Links the befores wrote and no after wrote_

- [x] real link lost · superseded-by · written by 1 of 3 runs

    - on review: missed that source and target are the same entity (AC-9 to itself); I stand by the original, rightly dropped

  - source: `0021/AC-9` AcceptanceCriterion: ~~The page shows no Adzuna attribution and no salary prediction attribution~~ · **SUPERSEDED 2026-09-14.** The opposite is now required: every card carries the "Jobs by Adzuna" attribution (reusing `AdzunaAttribution` from spec 0013 unchanged), and a card whose salary was predicted rather than stated additionally carries both the `(estimated)` label and the Jobsworth attribution (`JobsworthAttribution`), reusing the same pairing `src/features/search/result-card.tsx` already renders. The listing genuinely came from Adzuna now, so both attributions are load bearing, not decorative.
  - target: `0021/AC-9` AcceptanceCriterion: ~~The page shows no Adzuna attribution and no salary prediction attribution~~ · **SUPERSEDED 2026-09-14.** The opposite is now required: every card carries the "Jobs by Adzuna" attribution (reusing `AdzunaAttribution` from spec 0013 unchanged), and a card whose salary was predicted rather than stated additionally carries both the `(estimated)` label and the Jobsworth attribution (`JobsworthAttribution`), reusing the same pairing `src/features/search/result-card.tsx` already renders. The listing genuinely came from Adzuna now, so both attributions are load bearing, not decorative.
  - phrase: SUPERSEDED 2026-09-14
  - source text:
    > - **AC-9**: ~~The page shows no Adzuna attribution and no salary prediction attribution, since
    >   nothing on it came from either vendor.~~ · **SUPERSEDED 2026-09-14.** The opposite is now
    >   required: every card carries the "Jobs by Adzuna" attribution (reusing `AdzunaAttribution` from
    >   spec 0013 unchanged), and a card whose salary was predicted rather than stated additionally
    >   carries both the `(estimated)` label and the Jobsworth attribution (`JobsworthAttribution`),
    >   reusing the same pairing `src/features/search/result-card.tsx` already renders, because the two
    >   must never come apart (`salaryText()`'s own doc comment). The listing genuinely came from Adzuna
    >   now, so both attributions are load bearing, not decorative.

## Item 4
_Group C: feature-9 / 9-profile-entry-done (a different scope row than the example's) · Relationships_

- [x] disagree · unclassified · written by 2 of 3 runs
  - reason: too broad: the link should point at the named constraint inside spec 0001 ("third runner constraint"), not the whole record


  - source: `feature-9#9-profile-entry-done:3` AcceptanceCriterion: **Done when:** a signed in user can create and edit their profile, it survives a reload, validation errors are shown rather than swallowed, the saved shape is exactly what scoring will later read, and the profile form's Server Action is driven once from a test with no browser.
  - target: reference `0001` (whole record), mention: spec 0001's third runner constraint
  - phrase: That last clause is spec 0001's third runner constraint, deferred to here by spec 0004
  - flags: relationship_type_ambiguous
  - source text:
    > ### 9. Profile entry · done
    > A form for the flat profile: personal details, skills, one layer of work history, and stated job preferences. Typed by hand, with no resume upload and no extraction, so it makes no external call at all. Scoring cannot function without this, and the completion test does not start without a way to get profile data in.
    > **Done when:** a signed in user can create and edit their profile, it survives a reload, validation errors are shown rather than swallowed, the saved shape is exactly what scoring will later read, and the profile form's Server Action is driven once from a test with no browser. That last clause is spec 0001's third runner constraint, deferred to here by spec 0004 because there was no real write path to drive at feature 8; the technique is recorded in that spec's follow up list. Also, this feature moves its own claim (`profile`) from planned to working in the entry page's "What's real today" card (spec 0006, **AC-8**). It also **closes the deferred half of spec [0007](../specs/0007-auth-and-per-user-isolation/index.md) AC-15**: two real accounts, on the running app, each reading their OWN profile and not the other's. Feature 7 proved only the negative half, that neither account reaches the other's data, because at that point no `profile` row existed for anyone and both signed in users landed on the same named `record_not_found`. AC-15's wording assumes rows are there to be isolated, and this is the feature that first makes that true, so the proof lands here rather than being re run against the fixture pool it was written to go beyond.
    > _spec [0010](../specs/0010-profile-entry/index.md) · code in `src/features/profile/`, `src/app/(app)/profile/`, `src/components/ui/`, proofs in `test/integration/profile-form.test.ts`_

## Item 5
_Group B: 0013 / feature-design (a kind with an example, different content) · Entities_

- [x] agree · `0013#feature-design:25` · TestScenario · label `Failure case`
`

  - span: Failure case: a batch where one of several returned listings fails its own item level parse renders the rest normally and drops only the bad one, verifies **AC-1**, **AC-5** (the "every item fails" branch is a separate case, same kind).

   - on review: I stand by the original disagree: "Failure case" is shared by three bullets, so it is not this item's own name

## Item 6
_Group A: 0021 / requirements (a unit kind with no worked example) · Links the befores wrote and no after wrote_

- [x] rightly dropped · unclassified · written by 3 of 3 runs
  - reason: rationale.md is not a record kind yet (feature 10); the pointer survives verbatim in AC-5's rejected_spans, so a later version can recover it by code


  - source: `0021/AC-5` AcceptanceCriterion: The page offers exactly two example candidate profiles, `backend-engineer` ("Backend engineer", the default) and `frontend-engineer` ("Frontend engineer"), switchable through a `?persona=` link. Any value that is not exactly one of those two slugs (absent, unrecognized, empty, or a repeated query param) shows the default profile rather than erroring.
  - target: reference `rationale.md` (whole record), mention: see `rationale.md`
  - phrase: see `rationale.md`
  - source text:
    > - **AC-5**: The page offers exactly two example candidate profiles, `backend-engineer`
    >   ("Backend engineer", the default) and `frontend-engineer` ("Frontend engineer"), switchable
    >   through a `?persona=` link. Any value that is not exactly one of those two slugs (absent,
    >   unrecognized, empty, or a repeated query param) shows the default profile rather than erroring.
    >   *(Slug changed 2026-09-14: `product-designer` is replaced by `frontend-engineer`, since the
    >   personas are now scored for real and a contrasting-stack pair of engineers gives a cleaner
    >   signal than an engineer against a designer; see `rationale.md`.)*

## Item 7
_Group C: feature-9 / 9-profile-entry-done (a different scope row than the example's) · Relationships_

- [x] agree · satisfies · written by 3 of 3 runs


  - source: `feature-9#9-profile-entry-done:11` BuildStep: Thicken: search preferences, the new spans registered, and the entry page's `profile` claim moved to working · AC-9, AC-10, AC-16
  - target: reference `0010` AC-16, mention: AC-9, AC-10, AC-16
  - phrase: AC-9, AC-10, AC-16
  - source text:
    > - [x] Build it: `/develop profile entry`
    >   - [x] Four new base components (`Input`, `Textarea`, `Select`, a `Field`/`Label` wrapper) added to `src/components/ui/`, extending spec 0005's inventory the way spec 0006 added `Logo` · AC-17
    >   - [x] Thin slice: the identity section end to end (create, reload, edit) via `saveIdentity` and the URL driven `/profile` page · AC-1 to AC-4, AC-11 to AC-14
    >   - [x] Thicken: skills (the diff based save) and work history (per entry add, edit, delete with a confirmation step) · AC-5 to AC-8, AC-7a
    >   - [x] Thicken: search preferences, the new spans registered, and the entry page's `profile` claim moved to working · AC-9, AC-10, AC-16
    >   - [x] Proofs: the no browser Server Action test, two account isolation, and the `/ui-preview` keyboard/focus/contrast pass · AC-14, AC-15, AC-17

## Item 8
_Group A: 0021 / requirements (a unit kind with no worked example) · Entities_

- [x] agree · `0021/AC-3` · AcceptanceCriterion
  - reason: bundled AC-N kept whole and flagged, ruled agree by the convention · gap:bundled-ac

  - span: The opposite
  is now true on purpose: every listing (company name, title, description, location) is real,
  exactly as Adzuna returned it, including a real employer's name on a `weak_match` or
  `not_a_match` row (AC-19). The two candidate personas are the only fictional element left, and
  they are shown on the page in full (AC-14) as the disclosure that makes this honest.
  - flags: multi_condition_split

## Item 9
_Group B: 0013 / feature-design (a kind with an example, different content) · Relationships_

- [x] agree · verifies · written by 3 of 3 runs
  - reason: extraction matches the text; JobHunt: page.test.ts:291 checks only AC-4's first clause, not "distinct from both" (a code gap, not an extraction error)


  - source: `0013#feature-design:29` TestScenario: Empty: a search that legitimately matches nothing renders the empty state, distinguishable from both the failure and refusal states, verifies **AC-4**.
  - target: reference `0013` AC-4, mention: **AC-4**
  - phrase: verifies **AC-4**
  - source text:
    > - Empty: a search that legitimately matches nothing renders the empty state, distinguishable from both the failure and refusal states, verifies **AC-4**.

## Item 10
_Group B: 0013 / feature-design (a kind with an example, different content) · Relationships_

- [x] disagree · unclassified · written by 2 of 3 runs
    - on review: I stand by today's disagree; the original agree is superseded. gap:reuses-type drops from 3 to 2

  - reason: no link: the sentence only says something is reused in another feature, not a relation between records


  - source: `0013#feature-design:3` Constraint: Feature 12 imports this exact shape later for its own field mapping (spec 0003 already names feature 11 as owner of that mapping).
  - target: reference `feature 12` (whole record), mention: Feature 12
  - phrase: Feature 12 imports this exact shape later for its own field mapping
  - flags: relationship_type_ambiguous
  - source text:
    > No new database table. Results are never persisted (by product decision, recorded in `docs/scope/scope.md`'s Slice 1 introduction), so the only new shape is an in memory value object, Zod parsed at the Adzuna response boundary and never written to Postgres. Feature 12 imports this exact shape later for its own field mapping (spec 0003 already names feature 11 as owner of that mapping).

