# 0018 · Realistic usage questions

**Date**: 2026-10-22
**Feeds**: how `tracepath ask` handles questions a user would really type; no scope row
**Status**: run once each; not yet marked (the engineer marks afterwards)

## Method

- 22 questions, one run each with `tracepath ask QUESTION --ceiling 0.22`: 10 answer questions (`questions.json`, with a source and `records_needed`), 6 decline type questions (`jobhunt_questions_an1.json`) and 6 decline type questions (`jobhunt-design-questions_cur.json`).
- The questions and the expected lines were committed before the runs (`c1e4143`, `experiments/0018-realistic-usage-questions/questions.json`). Only the question text was passed to `ask`, never the expected line.
- Prompt `ask-2`, model `claude-sonnet-5-5`, corpus `2e40bcf`, hops 2 (the default), the graph as loaded by a plain `tracepath load`.
- `eval/held-out.json` was never opened.
- Nothing is marked right or wrong here and there is no summary of how it did. The engineer marks each answer afterwards.

## Notes on the expected lines

- The expected lines for the daily email digest question (Q19) and the team question (Q22) were written after the engineer read the advisor's summary of what the extracted specs say on them (the questions' original kind labels were decline), and before any run. The other 20 were written before that.
- Q1 was run once on 2026-10-22 at 19:39 UTC, before the questions were committed (`c1e4143`). Its question and expected line were set before that run, and the engineer saw part of the answer in the terminal. That record is its one run; it was not run again.
- Q2 to Q22 were run on 2026-10-22 between 20:24 and 20:26 UTC, in the committed order, after the dry run estimate and the engineer's go.

## Totals

- Prompt version: `ask-2` (every record).
- Calls: 22, one per question.
- Total recorded cost: $1.022538 (sum of each record's `cost_usd`; not yet matched to the Console).
- Dry run bound for Q2 to Q22 was $4.2547; the per call ceiling was $0.22.

## Marks

| Q | Mark | Note |
|---|---|---|
| Q1 | wrong | none |
| Q2 | wrong | Feature 3 ("Deployment & environments", scope row 3) and spec 0002 are the same thing. The tool cited spec 0011's item naming "the emergency kill switch built in feature 3", but that name stayed unresolved: it was not linked to feature 3 or to spec 0002. So it said the decision was missing. |
| Q3 | right | none |
| Q4 | partly right | The rationale for the decision is not included. The items cited were correct and related to the question; they lacked the direct explanation for the choice. |
| Q5 | right | none |
| Q6 | right | The second claim arguably answers the question. It may not give all the answers, but it is a valid answer. |
| Q7 | right | Right. Partly would also be a fair judgment, but explaining the difference between a failure and a refusal (a usage limit being a refusal) can be considered an answer. The cited items were not from spec 0011, and the alert ratio wording is in the source but not in the answer. |
| Q8 | right | none |
| Q9 | right | none |
| Q10 | right | none |
| Q11 | declined | The tool has no set verdict for a false premise. Its verdicts are answered, partly, not_supported and no_documented_link, so not_supported is the closest it can give. |
| Q12 | declined | I don't see the model inventing anything. |
| Q13 | declined | It did not stretch any of the related items (apply, search) into an answer about a Chrome extension. |
| Q14 | declined | none |
| Q15 | declined | none |
| Q16 | declined | none |
| Q17 | declined | none |
| Q18 | declined | none |
| Q19 | right | Marked against the question, not the committed line. "Not built" is the answer to the question; adding "a deferred idea" to the expected line was my mistake. It shows a needed improvement: when a related item exists (here, the deferred "Scheduled push digest" idea), the answer should give that context. Claim 3 says the scope document does not mention a digest, but scope.md:497 does; the tool checked only the preamble item it cited. |
| Q20 | declined | none |
| Q21 | declined | none |
| Q22 | right | The answers are correct except for claim 3, which misreads "the author family" (the Opus model family that wrote the code) as the human author's family. |

Answer questions (12): 9 right, 1 partly right, 2 wrong. Decline questions (10): 10 declined, 0 invented. Marked by the engineer on 2026-10-23.

## What it showed

Drafted from checks made on 2026-10-23. Neither finding changes a mark, and no fix below has been tested.

1. **Word matching misses items that are in the graph (Q1, Q2, Q19).** In each case the item holding the answer was in the graph but not among the 16 hits `build_pack` keeps: `0001#summary:3` ranked 40th (it matched only "values"), `0002#summary:3` ranked 351st (only "row"), and `scope#deferred:5` ranked 35th (only "digest"). The questions used everyday words ("error", "throwing", "emergency stop toggle", "daily email digest") where the specs say "failures", "thrown", "kill switch" and "Scheduled push digest", and pairs of common question words outscored the one rare match. Checked by rerunning `build_pack` on the live graph for each question, with no model call.
2. **The reasons live in `rationale.md`, which is not extracted (Q1, Q4, Q7, partly Q6).** Spec 0001's extraction scope covers each spec's `index.md` only. The reasoning behind Q1 (`specs/0001-stack-and-architecture/rationale.md:92`) and Q7 (`specs/0011-usage-gating-and-kill-switch/rationale.md:40-48`), and part of it for Q4 (`specs/0005-design-system-and-ui-foundation/rationale.md:60`) and Q6 (`specs/0010-profile-entry/rationale.md:11`), is only in `rationale.md`, so no graph item could carry it. Scope feature 10 (rationale extraction) is the planned change.

## Results

### Q1

- **Question**: why does error handling pass back explicit values instead of throwing exceptions?
- **Expected**: A correct answer must explain that returning failures as values allows TypeScript's type system to enforce handling at compile time so errors cannot be silently swallowed. It must also mention that each failure immediately reports itself to Sentry upon creation.
- **Verdict**: not_supported
- **Answer text**:
  - No item states why error handling returns explicit values rather than throwing. The items only touch the error model in passing and give no rationale for the choice. (cites: 0014#consequences:10; basis: text)
  - Spec 0014 says its failures normally go through `failure()` and an error model, and its one exception is the stale build refusal. That refusal is caught with a plain try/catch in `ApplyControl` and reported by an explicit `Sentry.captureException`. This shows a failure-value convention exists but does not say why it was chosen. (cites: 0014#consequences:10; basis: text)
  - Spec 0002 describes a module that uses `attempt()` for a genuine transport throw, an explicit check of the returned `error` field mapped to a named failure, and Zod for a row that parses wrong. This shows failures returned as named kinds, but gives no reason for preferring that to exceptions. (cites: 0002#build-plan:11; basis: text)
  - Spec 0013 specifies `withUsageGate` returning a `Result` so a caller cannot reach its outbound call without the gate's `allowed: true` branch. This gives a reason for a Result type in that one helper, not for the project's error handling overall. (cites: 0013#build-plan:4; basis: text)
- **Missing, as the answer says**:
  - A decision or rationale record explaining why the project returns explicit failure values instead of throwing exceptions
  - The project's error model spec or the definition of `failure()` and `Result`
- **Cited items**: 0014#consequences:10, 0002#build-plan:11, 0013#build-plan:4
- **Cost**: $0.056654
- **Record**: `artifacts/asks/2026-10-22T19-39-13Z-why-does-error-handling-pass.json`
- **Mark**: wrong

### Q2

- **Question**: which spec decided to put the emergency stop toggle as a single row in the database instead of an environment variable?
- **Expected**: A correct answer must identify spec 0002 as making this decision. It must also explain that storing the toggle in Postgres allows the operator to shut down external spend immediately from a dashboard without triggering or waiting for a redeployment.
- **Verdict**: not_supported
- **Answer text**:
  - Spec 0011 mentions an emergency kill switch that the operator can throw, but only says it was built in feature 3. It states nothing about how the switch is stored, and the records have no item for that feature. (cites: 0011#summary:3, unresolved:0011:the-emergency-kill-switch-built-in-feature-3; basis: text)
- **Missing, as the answer says**:
  - The spec and items for feature 3 where the emergency kill switch was built
  - Any decision about storing the kill switch as a single database row rather than as an environment variable
- **Cited items**: 0011#summary:3, unresolved:0011:the-emergency-kill-switch-built-in-feature-3
- **Cost**: $0.047404
- **Record**: `artifacts/asks/2026-10-22T20-24-02Z-which-spec-decided-to-put.json`
- **Mark**: wrong
- **Note**: Feature 3 ("Deployment & environments", scope row 3) and spec 0002 are the same thing. The tool cited spec 0011's item naming "the emergency kill switch built in feature 3", but that name stayed unresolved: it was not linked to feature 3 or to spec 0002. So it said the decision was missing.

### Q3

- **Question**: what did we decide about setting up automated end-to-end browser tests in the test suite?
- **Expected**: A correct answer must state that Playwright was chosen as the end-to-end runner but intentionally left uninstalled in the foundation. It must explain that setup was postponed until a feature genuinely requires real browser testing so CI does not have to maintain an empty test suite.
- **Verdict**: answered
- **Answer text**:
  - Playwright is the recorded choice for end to end browser tests, and the choice is binding whether or not it is installed. Spec 0004 did not install it; the first feature that genuinely needs a browser stands the tool up alongside its first real test. (cites: 0004#decision:3; basis: text)
  - The follow-up restates the plan: Playwright is installed, configured and given its first real end to end test together, by the first feature that needs a browser (feature 9 onward). Waiting on it are the missing profile path in the verify list, which stays a manual browser check until then, and any claim that only a real browser can prove. (cites: 0004#follow-up:4; basis: text)
  - Vitest runs both unit and integration suites. `pnpm test` runs unit tests without the stack, and `pnpm test:integration` fails with a clear message when the local stack is down. (cites: 0004#decision:3, 0004/AC-12; basis: text)
  - A related decision is parked: fetching the full posting with `defuddle` is to be revisited only alongside a deliberate decision to add a headless browser to the stack. (cites: 0015#follow-up:8; basis: text)
  - The items do not show Playwright actually being installed. Spec 0009's cookie guard (AC-24) is an integration test that drives real sign in steps, and it does not mention Playwright. (cites: 0009/AC-24; basis: text)
- **Missing, as the answer says**:
  - No item records whether Playwright has actually been installed or configured, or which feature first did it.
- **Cited items**: 0004#decision:3, 0004#follow-up:4, 0004/AC-12, 0015#follow-up:8, 0009/AC-24
- **Cost**: $0.054986
- **Record**: `artifacts/asks/2026-10-22T20-24-07Z-what-did-we-decide-about.json`
- **Mark**: right

### Q4

- **Question**: why does the design system reserve monospace font only for certain pieces of text?
- **Expected**: A correct answer must note that monospace typography is strictly reserved for literal data and generated reasoning explanations such as salaries, dates, and fit reasoning. It must also note that decorative labels, badges, and headers must use tracked uppercase sans-serif instead.
- **Verdict**: partly
- **Answer text**:
  - The design system's `Text` base component encodes the mono usage rule: mono is reserved for written reasoning and literal data (skill gap notes, the summary line, salaries, dates, scores), while decorative labels (eyebrows, section micro labels, filter chips, step numerals, status badges) render in tracked sans serif caps. (cites: 0005/AC-6; basis: text)
  - A build step built the `Text` and `Heading` components and retired the old `.eyebrow`/`.mono-label` CSS classes; it is listed as satisfying AC-6, as is the completed feature 5 build step. (cites: 0005#build-plan:6, 0005/AC-6, feature-5#5-design-system-ui-foundation-done:8; basis: link)
  - JetBrains Mono is loaded alongside Space Grotesk and mapped as `--font-mono` next to `--font-sans`, so a mono face exists to be reserved. (cites: 0005/AC-2; basis: text)
- **Missing, as the answer says**:
  - An explicit statement of the rationale for reserving mono, beyond the rule itself (which text gets mono and which gets tracked sans caps).
- **Cited items**: 0005/AC-6, 0005#build-plan:6, feature-5#5-design-system-ui-foundation-done:8, 0005/AC-2
- **Cost**: $0.052592
- **Record**: `artifacts/asks/2026-10-22T20-24-13Z-why-does-the-design-system.json`
- **Mark**: partly right
- **Note**: The rationale for the decision is not included. The items cited were correct and related to the question; they lacked the direct explanation for the choice.

### Q5

- **Question**: why did we publish the privacy and terms pages before most of the product was even built?
- **Expected**: A correct answer must explain that publishing live terms and privacy notices was required to unblock Google OAuth verification. It must mention that Google's developer console caps testing mode at 100 lifetime users until real policy pages are provided.
- **Verdict**: answered
- **Answer text**:
  - The pages were built early because Google's Publish app was blocked until a privacy policy and terms of service URL existed. Those links were empty, and feature 21 (Terms and privacy notices) is what produces them. (cites: 0007#consequences:11; basis: text)
  - While the app stays in Testing mode it is capped at 100 users. Google counts that cap over the app's entire lifetime, so it never goes back down. That is why delaying the pages carried a cost. (cites: 0007#consequences:11; basis: text)
  - The spec describes the pages as existing to be true and to unblock Google. (cites: 0009#summary:1; basis: text)
  - The pages must be served from usejobhunt.dev, because Google would not accept a vercel.app address as an Authorized domain but will accept this one. (cites: 0007#follow-up:10, feature-21#21-terms-privacy-notices-done-alpha:6; basis: text)
  - Publishing and verifying the Google app is also the remaining fix for the consent screen. The screen currently shows the Supabase host instead of naming JobHunt, and brand verification is meant to correct that. (cites: 0007#follow-up:10, 0009/AC-22, 0007#consequences:10; basis: text)
  - The dependency was recorded and feature 21 was moved out of Slice 5 into Foundation, to be built after feature 32. Both changes were made on the strength of the consequence paragraph. (cites: 0007#consequences:11; basis: text)
- **Cited items**: 0007#consequences:11, 0009#summary:1, 0007#follow-up:10, feature-21#21-terms-privacy-notices-done-alpha:6, 0009/AC-22, 0007#consequences:10
- **Cost**: $0.031266
- **Record**: `artifacts/asks/2026-10-22T20-24-19Z-why-did-we-publish-the.json`
- **Mark**: right

### Q6

- **Question**: why does updating candidate skills do a diff instead of just wiping them all and re-inserting?
- **Expected**: A correct answer must explain that saving skills compares incoming names case-insensitively against existing rows to delete only removed items and insert only new ones. It must note that this avoids unnecessary database churn, preserves stored capitalization, and respects unique constraints.
- **Verdict**: partly
- **Answer text**:
  - The requirement is explicit: saving compares the submitted list to the caller's current profile_skill rows case-insensitively, deletes only removed names and inserts only new ones, and never does a blanket delete followed by a blanket insert. (cites: 0010/AC-5; basis: text)
  - The diff is also what makes a capitalisation-only change a no-op: submitting `react` for stored `React` leaves the stored casing alone, because comparison follows the unique index that is the authority on skill identity. (cites: 0010/AC-5; basis: text)
  - The expected behavior is shown by a test scenario: with stored skills a, b, c and a submission of a, c, d, only b is deleted and d inserted, while a and c are untouched. (cites: 0010#feature-design:29, 0010/AC-5; basis: link)
  - The diff has a cost: a read before the write, a specific statement order, and zero-row checks, all of which a naive implementation would skip. The records accept this cost. (cites: 0010#consequences:7; basis: text)
  - The write order is insert-then-delete, and a failure test covers the case where the delete half fails after the insert half succeeded: the caller's prior skills are all still present. This suggests the ordering protects existing data from partial writes, though the records do not state this as the reason for choosing a diff. (cites: 0010#build-plan:4, 0010#feature-design:30; basis: inferred)
- **Missing, as the answer says**:
  - An explicit rationale statement for why a wipe-and-reinsert was rejected, beyond the requirement that it never be used
- **Cited items**: 0010/AC-5, 0010#feature-design:29, 0010#consequences:7, 0010#build-plan:4, 0010#feature-design:30
- **Cost**: $0.055348
- **Record**: `artifacts/asks/2026-10-22T20-24-25Z-why-does-updating-candidate-skills.json`
- **Mark**: right
- **Note**: The second claim arguably answers the question. It may not give all the answers, but it is a valid answer.

### Q7

- **Question**: why does hitting a usage limit return an ordinary successful response rather than an error?
- **Expected**: A correct answer must explain that a rate limit refusal is a successful business decision whose answer is simply no. It must also state that treating a refusal as a failure would incorrectly mark observability spans as failed when the system worked as intended.
- **Verdict**: partly
- **Answer text**:
  - A usage gate refusal is a distinct kind of result from a failure. Spec 0012's invariant keeps a refusal and a failure as two structurally distinct results. (cites: 0019/AC-7; basis: text)
  - Scoring refusals (`{ allowed: false }`) are handled differently from failures: a refusal gives a single page level notice naming the limit, and a vendor failure gives a per card "could not be scored" state. The two are kept visibly distinct. (cites: 0015/AC-11, 0015/AC-10; basis: link)
  - A misconfigured tier is a `Failure` and not a refusal, and every `Failure` is reported to Sentry on construction. This shows that errors are the path reported as failures, while a refusal is a normal outcome. (cites: 0019#consequences:9; basis: text)
- **Missing, as the answer says**:
  - Any item stating why a limit hit returns an ordinary successful HTTP response rather than an error status. The items describe refusals as a result value but give no rationale for that choice.
- **Cited items**: 0019/AC-7, 0015/AC-11, 0015/AC-10, 0019#consequences:9
- **Cost**: $0.049512
- **Record**: `artifacts/asks/2026-10-22T20-24-31Z-why-does-hitting-a-usage.json`
- **Mark**: right
- **Note**: Right. Partly would also be a fair judgment, but explaining the difference between a failure and a refusal (a usage limit being a refusal) can be considered an answer. The cited items were not from spec 0011, and the alert ratio wording is in the source but not in the answer.

### Q8

- **Question**: what replaced sending users to the diagnostic screen after they log in?
- **Expected**: A correct answer must state that logging in initially routed directly to the health check page under spec 0007. It must explain that spec 0008 replaced this with a landing rule directing users with no profile to the profile setup page and users with an existing profile to search.
- **Verdict**: answered
- **Answer text**:
  - The old rule sent a person to `/health` after signing in. That destination was superseded on 2026-08-31 by spec 0008 AC-6, so 0007/AC-1 is HISTORY and no longer stands as written. (cites: 0007/AC-1, 0008/AC-6; basis: link)
  - The replacement is a landing rule. A user with no profile row lands on `/profile`, a user with a profile row lands on `/search`, and the callback no longer redirects to the literal `/health`. (cites: 0008/AC-6; basis: text)
  - `/health` remains as an internal diagnostic. It is deliberately unlinked and is not in the navigation. (cites: 0008/AC-22; basis: text)
- **Cited items**: 0007/AC-1, 0008/AC-6, 0008/AC-22
- **Cost**: $0.048990
- **Record**: `artifacts/asks/2026-10-22T20-24-38Z-what-replaced-sending-users-to.json`
- **Mark**: right

### Q9

- **Question**: is it still true that the job listings search screen doesn't ship any client javascript?
- **Expected**: A correct answer must state that the search page no longer runs completely without client-side JavaScript. It must explain that spec 0014 added a client component for the apply button to prevent form submissions from causing a full page re-render that would re-run and waste a paid job search call.
- **Verdict**: answered
- **Answer text**:
  - No, it is no longer true. Spec 0014 adds `ApplyControl`, one Client Component per result card, so `/search` ships client JavaScript for the first time. The record says the property is gone rather than reduced. (cites: 0014#consequences:6, 0013#decision:5; basis: text)
  - Spec 0013's original claim of no client JavaScript for search was narrowed when feature 12 shipped. The link from 0013#decision:1 to 0013#decision:5 marks that amendment, and 0013#decision:5 is HELD, meaning not yet reviewed. (cites: 0013#decision:1, 0013#decision:5; basis: link)
  - Only half of the original claim survives. The search itself is still a Server Component reading the URL, with no Server Action and no client-side fetch producing results. The form is still a plain GET, and a shared `/search?q=...` link is still a working search. (cites: 0013#decision:4, 0014#consequences:6; basis: text)
  - The follow-up to amend spec 0013's Decision is recorded as done on 2026-09-05. The Decision now has a block quote splitting the claim in two. (cites: 0014#follow-up:6, 0014#follow-up:7; basis: text)
- **Cited items**: 0014#consequences:6, 0013#decision:5, 0013#decision:1, 0013#decision:4, 0014#follow-up:6, 0014#follow-up:7
- **Cost**: $0.056056
- **Record**: `artifacts/asks/2026-10-22T20-24-44Z-is-it-still-true-that.json`
- **Mark**: right

### Q10

- **Question**: what did we decide about the timeout limit for the secondary model verification call?
- **Expected**: A correct answer must state that the secondary verification tier originally shared a thirty-second timeout with the primary scoring tier in spec 0012. It must explain that spec 0019 reduced this timeout to twenty seconds based on real observed latencies measured from live model calls.
- **Verdict**: answered
- **Answer text**:
  - The decision (AC-6) is that `ai_check`'s `timeoutMs` in `tiers.ts` is shortened from the 30000ms it shares with `ai_scoring` to a value derived from measurement, not a guess. (cites: 0019/AC-6; basis: text)
  - The derivation rule: make at least 5 live calls under `TEST_LIVE_MODEL_CALLS_ENABLED`, multiply the slowest observed latency by 3, round up to the nearest 5 seconds, and clamp between a 15 second floor and a 30 second ceiling. The measured figure and resulting value are recorded in Follow-up. (cites: 0019/AC-6; basis: text)
  - The build plan step carries this out: run the live `checkFitScore()` calls, apply the rule, set `ai_check`'s `timeoutMs` in `tiers.ts` to the result, and record the latencies in Follow-up. It is blocked by the step that writes `check.ts`, and it satisfies AC-6. (cites: 0019#build-plan:3, 0019#build-plan:2, 0019/AC-6; basis: link)
- **Missing, as the answer says**:
  - The actual measured latencies and the final derived timeout value, which the spec says are recorded in Follow-up but are not among the items given.
- **Cited items**: 0019/AC-6, 0019#build-plan:3, 0019#build-plan:2
- **Cost**: $0.054060
- **Record**: `artifacts/asks/2026-10-22T20-24-50Z-what-did-we-decide-about.json`
- **Mark**: right

### Q11

- **Question**: Hey, why did we end up going with Neo4j for mapping company connections instead of just using Postgres foreign keys?
- **Kind label**: false_premise
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - (no claims)
- **Missing, as the answer says**:
  - Any item mentioning Neo4j or a graph database
  - Any item about mapping company connections or relationships between companies
  - Any decision record comparing a graph database with Postgres foreign keys
- **Cited items**: none
- **Cost**: $0.045598
- **Record**: `artifacts/asks/2026-10-22T20-24-55Z-hey-why-did-we-end.json`
- **Mark**: declined
- **Note**: The tool has no set verdict for a false premise. Its verdicts are answered, partly, not_supported and no_documented_link, so not_supported is the closest it can give.

### Q12

- **Question**: Why did we decide to use an event sourcing pattern for updating application status instead of normal CRUD updates?
- **Kind label**: false_premise
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - The records do not state any decision to use event sourcing for application status. The only status-related items say the opposite of a decided design: `application` deliberately carries no status column in v1, so there is no state machine to define. (cites: 0003#feature-design:2, 0014#feature-design:4; basis: text)
  - Feature 23 is recorded as the point where a status column and its check are added, as an alter against a table that already holds real rows. That is a plain column change, not an event log. (cites: 0003#follow-up:6, 0003#consequences:6; basis: text)
- **Missing, as the answer says**:
  - Any decision record choosing event sourcing for application status
  - Any comparison of event sourcing with CRUD updates
  - The feature 23 (applications dashboard) spec, which the records name but do not contain
- **Cited items**: 0003#feature-design:2, 0014#feature-design:4, 0003#follow-up:6, 0003#consequences:6
- **Cost**: $0.034378
- **Record**: `artifacts/asks/2026-10-22T20-24-59Z-why-did-we-decide-to.json`
- **Mark**: declined
- **Note**: I don't see the model inventing anything.

### Q13

- **Question**: Did we ever decide on building auto-import for job listings via a Chrome extension, or is that still shelved?
- **Kind label**: missing_feature
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - None of the items mention a Chrome extension or auto-import of job listings. The listing-related items describe Adzuna search and a manually triggered demo refresh. (cites: feature-31#31-seeded-demo-account-done:2; basis: text)
  - The apply feature is minimal: you click through to the real posting and record that you applied. Nothing is auto filled or submitted on the user's behalf. (cites: feature-12#12-apply-redirect-application-record-done:1, 0014#summary:2; basis: text)
- **Missing, as the answer says**:
  - Any decision, deferral or shelving record about a Chrome extension or auto-import of job listings
- **Cited items**: feature-31#31-seeded-demo-account-done:2, feature-12#12-apply-redirect-application-record-done:1, 0014#summary:2
- **Cost**: $0.043340
- **Record**: `artifacts/asks/2026-10-22T20-25-04Z-did-we-ever-decide-on.json`
- **Mark**: declined
- **Note**: It did not stretch any of the related items (apply, search) into an answer about a Chrome extension.

### Q14

- **Question**: Did we add a salary comparison tool for the offer stage, or are people just tracking compensation in plain notes?
- **Kind label**: missing_feature
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - The items show no salary comparison tool and no plain notes mechanism for tracking compensation at the offer stage. They only cover how salary appears on listings and on stored application rows. (cites: 0014/AC-6, 0014/AC-7; basis: text)
  - The application record stores a nullable salary_is_predicted flag next to salary_min and salary_max, and a predicted salary renders with an (estimated) label. This is a display and storage feature for a listing's salary, not a comparison tool. (cites: 0014/AC-6, 0014/AC-7; basis: text)
- **Missing, as the answer says**:
  - Any item about an offer stage, offers, or compensation comparison
  - Any item describing notes used to track compensation
- **Cited items**: 0014/AC-6, 0014/AC-7
- **Cost**: $0.052312
- **Record**: `artifacts/asks/2026-10-22T20-25-08Z-did-we-add-a-salary.json`
- **Mark**: declined

### Q15

- **Question**: What's our monthly AWS bill running at right now since we started getting more active job seekers?
- **Kind label**: outside
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - The only item that speaks to cost says both hosted environments are free and that nothing in the deployment spec introduces a monthly bill; it gives no AWS figure and says nothing about job seeker activity. (cites: 0002#consequences:5; basis: text)
- **Missing, as the answer says**:
  - Any current monthly AWS bill figure
  - Any item on AWS as a provider or its costs
  - Any item on active job seeker counts or usage growth
- **Cited items**: 0002#consequences:5
- **Cost**: $0.040900
- **Record**: `artifacts/asks/2026-10-22T20-25-13Z-what-s-our-monthly-aws.json`
- **Mark**: declined

### Q16

- **Question**: How are we handling competition with Huntr now that they rolled out their AI resume analyzer?
- **Kind label**: outside
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - (no claims)
- **Missing, as the answer says**:
  - Any item mentioning Huntr, competitors, or competitive strategy
  - Any item about Huntr's AI resume analyzer or a response to it
  - Any competitive analysis or positioning decision in the decision records
- **Cited items**: none
- **Cost**: $0.052584
- **Record**: `artifacts/asks/2026-10-22T20-25-17Z-how-are-we-handling-competition.json`
- **Mark**: declined

### Q17

- **Question**: why did we put the job listings in Mongo instead of postgres? feels like a weird split if the rest of the user data is relational
- **Kind label**: false_premise
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - The items do not say listings are stored in Mongo. They describe a data path through `@supabase/ssr` with authorisation enforced by Postgres row level security and no ORM, so the question's premise isn't supported here. (cites: 0001#decision:2; basis: text)
  - Search results are fetched live from Adzuna on each search and are never persisted, which means the search listings are not kept in any database. (cites: feature-11#11-job-search-results-list:1, 0013#requirements:1; basis: text)
  - Listing fields are stored on `application` rows, but the items do not say where those rows live or give any reason for a Mongo versus Postgres choice. (cites: scope#deferred:17; basis: text)
- **Missing, as the answer says**:
  - Any item mentioning Mongo or a decision to store job listings outside Postgres
  - The rationale for a split between listing storage and relational user data
- **Cited items**: 0001#decision:2, feature-11#11-job-search-results-list:1, 0013#requirements:1, scope#deferred:17
- **Cost**: $0.025128
- **Record**: `artifacts/asks/2026-10-22T20-25-28Z-why-did-we-put-the.json`
- **Mark**: declined

### Q18

- **Question**: is the ranking pipeline hitting elasticsearch for the match score, or is that just used for keyword search?
- **Kind label**: false_premise
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - The items describe ranking as a model-based fit score that sorts listings by band. The model gives a band, matched skills and not-mentioned skills from the listing's visible title and description, and the result list is re-sorted once by band after all outcomes resolve. (cites: 0015/AC-5, 0015/AC-9; basis: text)
  - Scoring runs through `scoreListings()`, which dispatches a concurrent `scoreListing()` call per listing, and a cross-vendor `checkFitScore()` follows each successful score. The items name model vendors (`@ai-sdk/openai`, `@ai-sdk/google`) and usage tiers (`ai_scoring`, `ai_check`), and none mentions Elasticsearch. (cites: 0019#build-plan:4, feature-13#13-model-client-router-done:11; basis: text)
  - The listing data comes from Adzuna search, with a 500 character description excerpt. No item says Elasticsearch supplies a match score or powers keyword search. (cites: feature-11#11-job-search-results-list:1, scope#deferred:13; basis: text)
- **Missing, as the answer says**:
  - Any item that mentions Elasticsearch, either as a source of match scores or as the keyword search backend
- **Cited items**: 0015/AC-5, 0015/AC-9, 0019#build-plan:4, feature-13#13-model-client-router-done:11, feature-11#11-job-search-results-list:1, scope#deferred:13
- **Cost**: $0.050934
- **Record**: `artifacts/asks/2026-10-22T20-25-33Z-is-the-ranking-pipeline-hitting.json`
- **Mark**: declined

### Q19

- **Question**: did we ever add a daily email digest when new ranked jobs show up, or is that still a tab-you-have-to-open thing?
- **Kind label**: missing_feature
- **Expected**: should answer: it must say the daily email digest was not built and that it is a deferred idea.
- **Verdict**: not_supported
- **Answer text**:
  - The only item that mentions email digests is spec 0006 AC-8, which removed `email digests` from the entry page's `planned` list because it was not actually planned. The card is meant to show only what is really planned or working. (cites: 0006/AC-8; basis: text)
  - Ranked results with reasoning are shown on the search page, and refused scoring calls produce an on-page notice. No item describes any email or notification delivery of new ranked jobs. (cites: 0015/AC-11, 0015/AC-15; basis: text)
  - The scope document describes the app as one where you enter a profile, search listings, see them ranked, click through to apply and record the application. It does not mention a digest. (cites: scope#preamble:1; basis: text)
- **Missing, as the answer says**:
  - Any item stating that a daily email digest was built, planned, or declined
  - Any scope row or spec for email or notification delivery of ranked jobs
- **Cited items**: 0006/AC-8, 0015/AC-11, 0015/AC-15, scope#preamble:1
- **Cost**: $0.047938
- **Record**: `artifacts/asks/2026-10-22T20-25-38Z-did-we-ever-add-a.json`
- **Mark**: right
- **Note**: Marked against the question, not the committed line. "Not built" is the answer to the question; adding "a deferred idea" to the expected line was my mistake. It shows a needed improvement: when a related item exists (here, the deferred "Scheduled push digest" idea), the answer should give that context. Claim 3 says the scope document does not mention a digest, but scope.md:497 does; the tool checked only the preamble item it cited.

### Q20

- **Question**: is there an interview calendar in the app so you can log phone screens against the jobs you marked as applied?
- **Kind label**: missing_feature
- **Expected**: should decline
- **Verdict**: not_supported
- **Answer text**:
  - The items describe recording that you applied to a job, with no interview or phone screen logging. The apply feature is minimal, and its guided capture questions are deferred to v2. (cites: feature-12#12-apply-redirect-application-record-done:1; basis: text)
  - Marking a job applied writes one application row holding the listing snapshot, and the applications screen lists those rows newest first with the snapshot fields. None of these fields concern interviews or phone screens. (cites: 0014/AC-2, 0014/AC-18; basis: text)
  - Search results mark jobs already applied to and disable the Mark as applied control. This is the only applied-state feature described, and it has no calendar. (cites: 0014/AC-9; basis: text)
- **Missing, as the answer says**:
  - Any item describing an interview calendar or logging phone screens against applications
- **Cited items**: feature-12#12-apply-redirect-application-record-done:1, 0014/AC-2, 0014/AC-18, 0014/AC-9
- **Cost**: $0.030464
- **Record**: `artifacts/asks/2026-10-22T20-25-44Z-is-there-an-interview-calendar.json`
- **Mark**: declined

### Q21

- **Question**: what's the typical monthly openai plus vercel bill when it's just me and a couple of friends using it?
- **Kind label**: outside
- **Expected**: should decline
- **Verdict**: partly
- **Answer text**:
  - The records say both hosted environments are free and that nothing in the deployment spec introduces a monthly bill. (cites: 0002#consequences:5; basis: text)
  - The project describes itself as free, with no billing, built for the author's own job search plus a few friends and recruiters. (cites: scope#preamble:1; basis: text)
  - The records show OpenAI is used: an OPENAI_API_KEY must be set in .env.local and all three Vercel environments, alongside a Google key. No item states what OpenAI usage costs. (cites: 0012#follow-up:11; basis: text)
  - Model usage is capped by seeded usage_cap rows for ai_scoring and ai_check (500 per account per week, 1320 per day globally, 40000 per month globally). These are call-count ceilings, not dollar figures. (cites: 0012/AC-8; basis: text)
- **Missing, as the answer says**:
  - Typical or actual monthly OpenAI spend
  - Per-call pricing for the OpenAI or Google models
  - Vercel plan or billing figures for this project
  - Typical usage volume for the author plus a couple of friends
- **Cited items**: 0002#consequences:5, scope#preamble:1, 0012#follow-up:11, 0012/AC-8
- **Cost**: $0.046140
- **Record**: `artifacts/asks/2026-10-22T20-25-48Z-what-s-the-typical-monthly.json`
- **Mark**: declined

### Q22

- **Question**: was anyone else on the team besides the original author, or is this still a one-person repo?
- **Kind label**: outside
- **Expected**: should answer along the lines of one author; if it does not, decline.
- **Verdict**: partly
- **Answer text**:
  - The records do not state a team size or contributor list. The closest evidence is that the terms and privacy notice is described as owed on the day the first person other than the author signs in, which implies that at the time of writing the author was the only user, though it says nothing about collaborators. (cites: feature-21#21-terms-privacy-notices-done-alpha:1; basis: text)
  - Spec 0006 says its fixes land before anyone outside the author sees the page, which again speaks about outside viewers rather than team members. (cites: 0006#consequences:2; basis: text)
  - A review record says a reviewer was spawned on a model that named itself as the author's family, so reviews appear to be done by AI models. That suggests, but does not prove, that review was not done by other people. (cites: feature-28#28-spend-visibility-gating-polish-done:15; basis: inferred)
- **Missing, as the answer says**:
  - Any statement of how many people have contributed to the repository
  - Any list of team members or collaborators
- **Cited items**: feature-21#21-terms-privacy-notices-done-alpha:1, 0006#consequences:2, feature-28#28-spend-visibility-gating-polish-done:15
- **Cost**: $0.045954
- **Record**: `artifacts/asks/2026-10-22T20-25-54Z-was-anyone-else-on-the.json`
- **Mark**: right
- **Note**: The answers are correct except for claim 3, which misreads "the author family" (the Opus model family that wrote the code) as the human author's family.

