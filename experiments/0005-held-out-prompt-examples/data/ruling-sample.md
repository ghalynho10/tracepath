# Ruling sample, experiment 0005 (AC-16)

For each item: does it pass HANDOFF's three question test (atomicity, referenceability, right sizing) and the deletion trick? Mark `agree` when the model's cut and type are what you would have written, `disagree` otherwise, with a word on why. Sample: 10 entities evenly spaced through run 1's located order, per group.

## Group A: 0021 / requirements (a unit kind with no worked example)

- [ ] agree / disagree · `0021#requirements:1` · Feature
  - span: As a visitor who has not signed up, I want to see real listings scored for real against a
  stated candidate
  - rejected: ['so that I can judge whether the ranking actually works, not just whether it\n  looks plausible.']
  - flags: granularity_boundary_call
- [ ] agree / disagree · `0021/AC-1` · AcceptanceCriterion
  - span: A visitor reaches `/demo` and sees a list of results with no sign in, no redirect,
  and no account required.
- [ ] agree / disagree · `0021/AC-3` · AcceptanceCriterion
  - span: The opposite
  is now true on purpose: every listing (company name, title, description, location) is real,
  exactly as Adzuna returned it, including a real employer's name on a `weak_match` or
  `not_a_match` row (AC-19). The two candidate personas are the only fictional element left, and
  they are shown on the page in full (AC-14) as the disclosure that makes this honest.
  - flags: multi_condition_split
- [ ] agree / disagree · `0021#requirements:5` · AcceptanceCriterion
  - span: No control on the page writes to the database. There is no code path by which one
  visitor's visit changes what the next visitor sees.
- [ ] agree / disagree · `0021#requirements:6` · AcceptanceCriterion
  - span: Exactly two seeded listings (the same title and company each time) appear under both
  profiles, each with a different band, different matched and not mentioned skills, and
  different written reasoning per profile. Their exact content is named in **Seed content**
  below.
- [ ] agree / disagree · `0021/AC-8` · AcceptanceCriterion
  - span: Each card shows title, company, location when present, a stated or predicted salary
  on some listings, a description snippet, the band, matched skills, not mentioned skills, the
  written reasoning, and (AC-16) a compact line naming the other persona's band for the same
  listing. A matched skill the grounding check flagged as ungrounded is removed from the displayed
  matched list and the same two sentences the real card shows appear here too (**Feature design**,
  "Ungrounded skills"). It carries no real "view posting" link and no working apply control, only a
  plain text line where the real apply control would sit, never a disabled button.
  - flags: multi_condition_split
- [ ] agree / disagree · `0021/AC-10` · AcceptanceCriterion
  - span: That claim is now false and reversed: a visible line
  states plainly that the listings are real, live Adzuna results, refreshed periodically, and that
  the two candidate profiles judged against them are fictional (AC-14 names what else that line
  shows). Every other place on the page or in its code that asserted the old claim (page metadata,
  heading, intro copy, the demo card's own doc comment, the not mentioned skills caption's
  justification) is corrected in the same pass (**Build plan**, "the wording pass").
  - flags: multi_condition_split
- [ ] agree / disagree · `0021/AC-12` · AcceptanceCriterion
  - span: If the seeded data cannot be read because of a genuine fault (the database is
  unreachable, or a row fails to parse), the page answers a normal 200 and shows a visible failure
  state rather than an empty, broken looking, or server error page. This is a different case from
  AC-15, and the two must render distinguishable copy.
  - flags: multi_condition_split
- [ ] agree / disagree · `0021/AC-14` · AcceptanceCriterion
  - span: The page shows both search queries the current
  results answer (both titles, and the shared location when one is set) and
  when the data was last refreshed,
  both read from the single `demo_refresh` row (**Feature design**). It also shows both persona
  profiles' full content (summary, skills, experience, preferences) somewhere on the page, which is
  the disclosure AC-3 now depends on.
  - rejected: ['revised 2026-09-15']
  - flags: multi_condition_split, embedded_second_claim
- [ ] agree / disagree · `0021/AC-17` · AcceptanceCriterion
  - span: A refresh, triggered as described in AC-18, runs
  exactly two real Adzuna searches using the fixed queries in **Feature
  design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings
  from each search in that search's own returned order, by the walk **Feature design** states
  (never selected, reordered, or padded by how any score turns out), and scores
  every kept listing against both personas exactly as `scoreListings()` already does for a real
  search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if
  any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained
  `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether
  refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is
  best effort because a real search must still render something, the refresh has no reader waiting
  on it and a previous, fully checked run to fall back to, so an unfinished check is treated the
  same as an unfinished score rather than silently written as if it had passed. Only once every
  kept listing has a clean, allowed score under both personas does the refresh atomically replace
  the entire contents of `demo_result` and the single `demo_refresh` row in one database
  transaction. A gate refusal (of any of the three call
  types, `job_search`, `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure,
  since it is the budget working as designed. A refresh whose searches leave zero kept listings in
  total also aborts, writing nothing.
  - rejected: ['**Feature design**, "Refresh outcomes", states the exact\n  shape of each outcome, both recorded 2026-09-15 from what `/develop` built.']
  - flags: multi_condition_split, rationale_boundary_call

## Group B: 0013 / feature-design (a kind with an example, different content)

- [ ] agree / disagree · `0013#feature-design:1` · Constraint
  - span: No new database table.
- [ ] agree / disagree · `0013#feature-design:4` · Constraint
  - span: Adzuna's response is parsed as an envelope first (does the whole body match the expected shape at all) and then per item: a single listing that fails its own parse is dropped and counted, not treated as a reason to fail the whole page.
- [ ] agree / disagree · `0013#feature-design:7` · Constraint
  - span: **Copy**: one slot per user facing string, text left for the engineer to write before `/develop`, the same convention specs 0007 and 0011 use.
- [ ] agree / disagree · `0013#feature-design:10` · Constraint
  - span: Exactly one Adzuna call, and exactly one usage gate check, per user submitted search, never zero and never more than one, so spec 0011's own accounting assumption ("the cap counts outbound API calls") holds exactly.
  - flags: multi_condition_split
- [ ] agree / disagree · `0013#feature-design:13` · Constraint
  - span: Attribution renders once per displayed listing, never once per screen. A screen with zero listings shows no attribution block.
  - rejected: ['since there is nothing to attribute']
  - flags: rationale_boundary_call
- [ ] agree / disagree · `0013#feature-design:16` · Constraint
  - span: An optional field with no value (`location`, `descriptionSnippet`, either salary figure, `postedAt`) is simply omitted from the card, never rendered as a placeholder or a dash that could be mistaken for real data.
- [ ] agree / disagree · `0013#feature-design:19` · Constraint
  - span: `ADZUNA_APP_KEY`: server only, required (`z.string().min(1)`, no default), Adzuna's application key credential.
- [ ] agree / disagree · `0013#feature-design:22` · TestScenario · label `Happy path`
  - span: Happy path: a signed in user with a `job_preference` row searches with a real title, sees real Adzuna listings with working attribution and outbound links, verifies **AC-1**, **AC-6**, **AC-8**.
- [ ] agree / disagree · `0013#feature-design:25` · TestScenario · label `Failure case`
  - span: Failure case: a batch where one of several returned listings fails its own item level parse renders the rest normally and drops only the bad one, verifies **AC-1**, **AC-5** (the "every item fails" branch is a separate case, same kind).
- [ ] agree / disagree · `0013#feature-design:28` · TestScenario · label `Validation`
  - span: Validation: a submission with both fields blank is refused before any call and spends no budget, verifies **AC-2**.

## Group C: feature-9 / 9-profile-entry-done (a different scope row than the example's)

- [ ] agree / disagree · `feature-9#9-profile-entry-done:1` · Feature
  - span: A form for the flat profile: personal details, skills, one layer of work history, and stated job preferences. Typed by hand, with no resume upload and no extraction, so it makes no external call at all.
  - flags: embedded_second_claim
- [ ] agree / disagree · `feature-9#9-profile-entry-done:2` · Consequence
  - span: Scoring cannot function without this, and the completion test does not start without a way to get profile data in.
  - flags: multi_condition_split
- [ ] agree / disagree · `feature-9#9-profile-entry-done:3` · AcceptanceCriterion
  - span: **Done when:** a signed in user can create and edit their profile, it survives a reload, validation errors are shown rather than swallowed, the saved shape is exactly what scoring will later read, and the profile form's Server Action is driven once from a test with no browser.
  - rejected: ["That last clause is spec 0001's third runner constraint, deferred to here by spec 0004 because there was no real write path to drive at feature 8; the technique is recorded in that spec's follow up list."]
  - flags: multi_condition_split, rationale_boundary_call
- [ ] agree / disagree · `feature-9#9-profile-entry-done:5` · TestScenario
  - span: **closes the deferred half of spec [0007](../specs/0007-auth-and-per-user-isolation/index.md) AC-15**: two real accounts, on the running app, each reading their OWN profile and not the other's.
  - rejected: ["Feature 7 proved only the negative half, that neither account reaches the other's data, because at that point no `profile` row existed for anyone and both signed in users landed on the same named `record_not_found`. AC-15's wording assumes rows are there to be isolated, and this is the feature that first makes that true, so the proof lands here rather than being re run against the fixture pool it was written to go beyond."]
  - flags: rationale_boundary_call, embedded_second_claim
- [ ] agree / disagree · `feature-9#9-profile-entry-done:6` · BuildStep
  - span: Design it (spec): `/architect profile entry`
- [ ] agree / disagree · `feature-9#9-profile-entry-done:8` · BuildStep
  - span: Four new base components (`Input`, `Textarea`, `Select`, a `Field`/`Label` wrapper) added to `src/components/ui/` · AC-17
  - rejected: ["extending spec 0005's inventory the way spec 0006 added `Logo`"]
  - flags: rationale_boundary_call
- [ ] agree / disagree · `feature-9#9-profile-entry-done:9` · BuildStep
  - span: Thin slice: the identity section end to end (create, reload, edit) via `saveIdentity` and the URL driven `/profile` page · AC-1 to AC-4, AC-11 to AC-14
- [ ] agree / disagree · `feature-9#9-profile-entry-done:10` · BuildStep
  - span: Thicken: skills (the diff based save) and work history (per entry add, edit, delete with a confirmation step) · AC-5 to AC-8, AC-7a
- [ ] agree / disagree · `feature-9#9-profile-entry-done:12` · BuildStep
  - span: Proofs: the no browser Server Action test, two account isolation, and the `/ui-preview` keyboard/focus/contrast pass · AC-14, AC-15, AC-17
- [ ] agree / disagree · `feature-9#9-profile-entry-done:13` · BuildStep
  - span: Verify it: `/check verify profile entry` · run 2026-09-02, **PASS**, all 18 acceptance criteria met, 51 of 53 steps ticked in [verify.md](../specs/0010-profile-entry/verify.md).
  - rejected: ['A first run on the same day found **AC-13 half unbuilt**: a malformed `entry` id rendered the plain list and said nothing, while a well formed one that matched no row correctly said the entry was gone. `/debug` traced it to `parsePageState` collapsing an unusable id into the plain view, fixed in `8a59fdf`, and this run re-proved all four URL cases. The two unticked steps are recorded at the end of `verify.md` and neither is an acceptance criterion failure. The read failure state was proved by stopping the database container: `/profile` renders the failure treatment and never the first run form']
  - flags: rationale_boundary_call
