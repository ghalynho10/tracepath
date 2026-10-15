# Stage one packet, experiment 0012

Stage one of spec 0007 (AC-19, AC-25 to AC-26d). Each unit below holds up to 8 entity
marks drawn at random and mixed blind, under opaque ids in shuffled order. The arm of
each item is in `stage-one-arms.json`, whose hash is committed in
`stage-one-arms.sha256`; the arm file itself is committed only after the rulings.

Replace each item's marks with one word: `agree` when the cut and type pass HANDOFF's
three question test (atomicity, referenceability, right sizing) and the deletion trick,
`disagree` otherwise, `unsure` when you cannot tell. Add a few words on why after
`reason:` when you disagree or are unsure. Tag `gap:bundled-ac` in the reason when you
rule a bundled criterion agree by the convention (AC-26e). Every item is ruled: in the
gate, `unsure`, `disagree` and an unruled item all count against (AC-18c, AC-19).

## 0009:Requirements

- [x] agree · `P01` · AcceptanceCriterion

  - source: specs/0009-terms-and-privacy-notices/index.md:41
  - span: **AC-1**: `/terms` and `/privacy` exist as routes in the `(marketing)` group. Each composes `EntryHeader` with `navigation="none"` and `EntryFooter`, and each ships zero client JavaScript.
  - reason: gap:bundled-ac (sentence 1, the routes exist, can hold while sentence 2, header, footer and zero client JS, fails)
 

- [x] agree · `P02` · AcceptanceCriterion

  - source: specs/0009-terms-and-privacy-notices/index.md:81
  - span: **AC-13**: The privacy notice discloses how data received from Google is accessed, used, stored and shared, and states plainly that data is not sold, not used for advertising, not shared with data brokers, and not used to train models. It carries no Limited Use affirmation.
  - reason: gap:bundled-ac (the disclosure of access, use, storage and sharing, each of the four "not" statements, and the absent Limited Use affirmation can each fail on its own) 

- [x] agree · `P03` · AcceptanceCriterion

  - source: specs/0009-terms-and-privacy-notices/index.md:43
  - span: **AC-2**: The privacy notice names every category of personal data stored, and its list matches the applied schema. From the identity provider: the email address, display name and avatar URL in `auth.users`. From this app's own tables: full name, location and written summary (`profile`); skill names (`profile_skill`); company, job title, location, description and start and end month (`work_experience`); desired titles, desired locations, remote preference, minimum pay and its currency (`job_preference`); the source and its job id, job title, company, location, link, description, salary range and currency, posted and applied timestamps (`application`); and the question key with the person's own typed answer (`application_answer`). It also names the `created_at` and `updated_at` timestamps every one of these tables carries,
   - reason: gap:bundled-ac (each named category and the timestamps can be missing on their own); the "since …" clause is left out as a reason, correctly


- [x] disagree · `P04` · Feature

  - source: specs/0009-terms-and-privacy-notices/index.md:36
  - span: As the operator, I want Google's consent screen to name JobHunt and the 100 user cap lifted,
   - reason: kept whole but holds two claims that can fail independently (Google's consent screen names JobHunt; the 100 user cap is lifted); should be two Feature items. The "so that" clause is left out as a reason, correctly
 

- [x] agree · `P05` · AcceptanceCriterion

  - source: specs/0009-terms-and-privacy-notices/index.md:140
  - span: **AC-21**: In the Google Cloud console, `usejobhunt.dev` is added as an authorized domain, the privacy policy and terms fields hold the two live URLs, and the app is moved out of Testing.
   - reason: gap:bundled-ac (authorized domain added, the two URL fields filled, and the app moved out of Testing can each fail on its own)
 

- [x] agree · `P06` · AcceptanceCriterion

  - source: specs/0009-terms-and-privacy-notices/index.md:135
  - span: **AC-19**: `/sign-in` renders a static line under the two provider forms saying that continuing means agreeing to the Terms and the Privacy Notice, with both linked, and the page still ships zero client JavaScript.
  - reason: gap:bundled-ac (the static line rendered, both links present, and zero client JS can each fail on its own)
 

- [x] agree · `P07` · Feature

  - source: specs/0009-terms-and-privacy-notices/index.md:32
  - span: As a person who has signed in, I want a way to have everything about me removed,
  - reason: the "so that" clause is motivation, its substance covered by AC-7, AC-8 and AC-10, so it is correctly left out as rationale; one claim
 

- [x] agree · `P08` · AcceptanceCriterion

  - source: specs/0009-terms-and-privacy-notices/index.md:138
  - span: **AC-20**: Both pages carry their own title and description metadata, have exactly one `h1` with headings in order, and every link is keyboard reachable with a visible focus ring (WCAG 2.2 AA).
  - reason: gap:bundled-ac (title and description metadata, one h1 with ordered headings, and keyboard reachable links with focus ring can each fail on its own)
 

## 0013:Requirements

- [x] agree · `P09` · AcceptanceCriterion

  - source: specs/0013-job-search-and-results-list/index.md:29
  - span: **AC-7**: A result whose salary is predicted (Adzuna's `salary_is_predicted: true`) shows "(estimated)" beside the figure and carries the separate Jobsworth attribution: a 20 by 20 pixel icon plus the words "Adzuna Jobsworth", both linked to `http://www.adzuna.co.uk/jobs/salary-predictor.html`, with the mouseover text "Salary estimate powered by Adzuna Jobsworth". A stated, non predicted salary shows neither the label nor the Jobsworth attribution.
  - reason: gap:bundled-ac (the "(estimated)" label, the icon and words, the link, the mouseover text, and the absence on a stated salary can each fail on its own)
 

- [x] agree · `P10` · AcceptanceCriterion

  - source: specs/0013-job-search-and-results-list/index.md:30
  - span: **AC-8**: Each result shows its title, company, location, a relative posted date (e.g. "posted 3 days ago", computed at render from the raw timestamp), a salary range when present, and its description snippet, plus a real, working link that opens the source posting (`job_url`) in a new tab.
  - reason: gap:bundled-ac (each displayed field, the relative date, and the working new-tab link can each fail on its own)
 

- [x] agree · `P11` · AcceptanceCriterion

  - source: specs/0013-job-search-and-results-list/index.md:24
  - span: **AC-2**: A search submitted with both title and location blank is refused before any external call runs, with a visible validation message, and spends no usage gate budget.
  - reason: gap:bundled-ac (refused before any external call, a visible validation message, and no usage budget spent can each fail on its own)
 

- [x] agree · `P12` · Feature

  - source: specs/0013-job-search-and-results-list/index.md:16
  - span: As a signed in user, I want to search real job listings by title and location,
  - reason: the "so I can … rather than a mock" clause is the reason, correctly left out as rationale; one claim
 

- [x] agree · `P13` · AcceptanceCriterion

  - source: specs/0013-job-search-and-results-list/index.md:27
  - span: **AC-5**: An Adzuna call that fails outright (network error, timeout, a non success response) is reported through `failure()` with `external_service_failed`; a response that does not match the expected shape is reported with `response_malformed`. Either renders a visible failure state distinct from AC-4's empty state.
  - reason: gap:bundled-ac (outright failure reported as external_service_failed, a malformed response as response_malformed, and a failure state distinct from AC-4's can each fail on its own) 

- [x] agree · `P14` · AcceptanceCriterion

  - source: specs/0013-job-search-and-results-list/index.md:25
  - span: **AC-3**: Every search that passes AC-2's check is checked through `checkUsageGate("job_search")` before the Adzuna call runs. A refusal, for any of the five reasons feature 10 defines, renders the exact sentence from `src/lib/usage-gating/copy.ts`'s `SENTENCES` map for that reason, and the Adzuna call never runs.
  - reason: gap:bundled-ac (the gate check before the call, the exact refusal sentence, and no Adzuna call on refusal can each fail on its own)

## 0015:Requirements

- [x] agree · `P15` · AcceptanceCriterion

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:37
  - span: **AC-15**: The entry page's "What's real today" card (spec 0006, AC-8) moves `ranked results with reasoning` from its `planned` list to its `working` list.
   - reason: one condition (the card's entry moves from planned to working)
 

- [x] agree · `P16` · AcceptanceCriterion

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:38
  - span: **AC-16**: Every pending card carries `aria-busy="true"` until its outcome resolves. A single polite live region announces, exactly once and **only when at least one listing was actually scored**, that results are now ranked (`COPY-7`); a batch in which every call was refused or failed ranks nothing, leaves the list in Adzuna's own order, and therefore announces nothing. And the reader's keyboard focus survives the re-sort: a reader who was focused on a control inside a result card before the ranking arrived is left focused on **that same control**, in its new position, never on the document body. Matching this project's WCAG 2.2 AA bar (`AGENTS.md`).
  - reason: gap:bundled-ac (aria-busy on pending cards, the single conditional announcement, and focus surviving the re-sort can each fail on its own); the italic correction note is history, correctly left out
 

- [x] disagree · `P17` · Feature

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:20
  - span: As the operator, I want a scoring failure to be visible and never mistaken for a working score, and a usage cap refusal to read differently from an actual failure.
  - reason: kept whole but holds two claims that can fail independently (a scoring failure visible and never mistaken for a score; a usage cap refusal reads differently from a failure); should be two Feature items 

- [x] agree · `P18` · AcceptanceCriterion

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:31
  - span: **AC-9**: The result list renders immediately, in Adzuna's original order, with a pending indicator on every card while scoring runs in the background. It re-sorts exactly once, once every listing's outcome (a score, a gate refusal, or a failure) has resolved: scored cards first, ordered by band (`strong_match` first, `not_a_match` last, ties within a band keeping Adzuna's original relative order,), then every refused or failed card after them in its own original relative order. No further re-sort happens after that. Outcomes are matched back to their card by `sourceJobId` (never by array position),
  - reason: gap:bundled-ac (immediate render with pending indicators, a single ordered re-sort, no further re-sort, and matching by sourceJobId can each fail on its own); both "since" clauses are reasons, correctly left out (a mid-sentence cut is allowed) 

- [x] agree · `P19` · AcceptanceCriterion

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:26
  - span: **AC-4**: The prompt built for every listing states plainly that Adzuna truncates `descriptionSnippet` at 500 characters and marks a truncated description with a trailing "…"; the model is instructed never to assert that a skill is required by a specific posting unless the visible text actually says so, and never to treat an unconfirmed skill as absent from the posting either.
  - reason: gap:bundled-ac (the truncation statement, the never-assert-required instruction, and the never-treat-as-absent instruction can each fail on its own)

- [x] disagree · `P20` · Feature

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:18
  - span: As a job seeker, I want to see which of my skills matched and which were not mentioned in the posting, not just a number,
  - reason: kept whole but holds two claims that can fail independently (see which skills matched; see which were not mentioned, a separate selection per AC-5); should be two Feature items. The "so that" clause is a reason, correctly left out

- [x] agree · `P21` · AcceptanceCriterion

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:34
  - span: **AC-12**: The prompt's system instructions state that the listing's title and description are untrusted external text, that the model must not follow any instruction contained within them, and must not fetch, describe, or act on any URL or address that appears in them.
  - reason: gap:bundled-ac (untrusted text stated, never follow embedded instructions, and never fetch or act on embedded URLs can each fail on its own)

- [x] agree · `P22` · AcceptanceCriterion

  - source: specs/0015-fit-scoring-with-shown-reasoning/index.md:27
  - span: **AC-5**: The score schema exposes `matchedSkills` (the caller's own skills whose name, or a clear synonym, appears in the listing's visible title or description) and `notMentionedSkills` (skills from the caller's own list that a role like this one would typically value, that do not appear anywhere in the listing's visible text). Both arrays are filtered after parsing to names that case insensitively match one of the caller's own `profile_skill` names; any other name the model returns is dropped before it reaches the UI, never displayed and never a reason to fail the whole call. Neither the schema field name nor any displayed label ever reads "missing skills"; the UI's label for `notMentionedSkills` states plainly that this is not a confirmed absence (`COPY-2`).
  - reason: gap:bundled-ac (both arrays exposed, the post-parse name filter, and never labelled "missing skills" can each fail on its own)

