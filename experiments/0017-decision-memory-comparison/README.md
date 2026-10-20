# 0017 · decision-memory comparison: the same nine questions, two tools

**Date**: 2026-10-20
**Feeds**: nothing yet; an experiment, no scope row
**Status**: run 2026-10-20, one decision-memory query per question; marks owed by the engineer

## Question

decision-memory (github.com/ghalynho10/decision-memory) answers the same kind of "why was
this built this way?" question as `tracepath ask`, with a different design: a RAG pipeline
on OpenAI that fuses BM25 and embedding search over chunks of each spec, drafts an answer,
then checks every sentence against its cited chunks and abstains when a check fails. Put
plainly: on the same pinned corpus and the same nine questions, what does each tool answer?

## Method

- Install decision-memory as it stands, no code changes, and point it at the pinned corpus
  `corpus/jobhunt` (JobHunt docs at `2e40bcf`). Its records and index live outside this
  repository, in `~/dm-jobhunt`.
- Run `doctor` and `adapt` (both offline), then `ingest --dry-run` for the token count, and
  estimate the cost before any paid call. Estimate given: about $0.10 to $0.18; ceiling set
  by the engineer at $0.50 total, stopping if the running total passed it.
- Ingest, then query each of the nine questions once: the five in
  `eval/linked-records-research.json` and the four in `eval/held-out.json`. The held out set
  is already spent for tracepath (v1 ran it on 2026-10-19), so reading it now is allowed.
- Each query ran with `--debug`, which prints the answer exactly as a plain query does,
  then the full trace, including the token counts of every provider call. One run gives
  both the verbatim answer and its cost.
- tracepath's side is not rerun: each question's answer is its existing prompt `ask-1`
  record in `artifacts/asks/`, the records v1 was judged on.
- The engineer marks each answer, side by side with the tool named (no blind marking, per
  `docs/reflexes.md`). This file does not judge them.

**Marking rule**, the needed points rule as experiment 0016 states it: "an answer is right
when it gives the points the question needs."

## Setup

- decision-memory v0.1.0, installed with
  `uv tool install git+https://github.com/ghalynho10/decision-memory` at its commit
  `b9b00e6`. Built in adapter `jsmastery-specs`, adapter version 5.
- Corpus `corpus/jobhunt` (JobHunt `docs/` at `2e40bcf`). Records in
  `~/dm-jobhunt/records`, index in `~/dm-jobhunt/query-index`.
- `OPENAI_API_KEY` loaded from tracepath's `.env` for decision-memory's commands only
  (`set -a; . ./.env; set +a; decision-memory ...`), never printed.
- Models, from decision-memory's `openai_generation.py` and `pipeline.py`: `gpt-4o` for
  facets, the answer draft and the coverage check; `gpt-4o-mini` for sentence
  decomposition and entailment; `text-embedding-3-small` for embeddings.
- tracepath: prompt `ask-1`, `claude-sonnet-5-5`, effort `medium`, asked 2026-10-19.
- Commands:

```bash
decision-memory doctor corpus/jobhunt
decision-memory adapt corpus/jobhunt --output ~/dm-jobhunt/records
decision-memory ingest ~/dm-jobhunt/records --store ~/dm-jobhunt/query-index --dry-run --debug
set -a; . ./.env; set +a; decision-memory ingest ~/dm-jobhunt/records --store ~/dm-jobhunt/query-index
set -a; . ./.env; set +a; decision-memory query "QUESTION" --store ~/dm-jobhunt/query-index --debug
```

- Data, all under `data/`:
  - `doctor.txt`, `adapt.txt`: the offline survey and adapter report (`adapt.txt` is a
    dry run made after the real one, so it reads "unchanged 19" where the real run wrote 19).
  - `ingest-plan.txt`: the chunk plan from the dry run before ingest, chunk ids and token
    counts only.
  - `<set>-q<N>-trace.txt.gz`: each query's full `--debug` output, verbatim (`zless` to read).
  - `answers.json`: per question, decision-memory's verbatim answer, citations, state, cost,
    provider calls and tokens, the records its retrieval accepted, and what it drafted
    before verification; and tracepath's `ask-1` verdict, claims, missing and cost.
- `report.py` builds `answers.json` and the side by side section below from the traces and
  the ask records, with no API call.

## What the adapter reads, and what it skips

`doctor` only surveys: it read all 108 markdown files under `corpus/jobhunt` (22 non
markdown files ignored, none skipped) and reports their H2 headings. It makes no mapping
claim, so it says nothing about what gets indexed.

`adapt` decides what gets indexed. The `jsmastery-specs` adapter reads only
`docs/specs/NNNN-*/index.md` and its sibling `rationale.md`. Context, Decision, Options
considered, Rationale and Consequences fill typed fields; every other H2 section (Summary,
Requirements, Feature design, Build plan, Follow-up, Copy) falls through to an untyped
`body`, which is still chunked and embedded.

- **Acceptance criteria:** JobHunt keeps them under `## Requirements` in each `index.md`, so
  for the 19 specs that adapted they are indexed, as `body` chunks, not as a field of their
  own.
- **Specs 0020 and 0021 failed to adapt** and are absent from the index entirely:
  - `0020`: its date is `2026-09-11 (revised 2026-09-12, corrected 2026-09-13)`, not a
    plain `YYYY-MM-DD`.
  - `0021`: `decision.chosen` could not be populated.
- **Never read:** `scope/scope.md`, every spec's `verify.md`, `reviews/`, `experiments/`,
  `archive/`, `design/`, `observability/`, `releases/`, `overview.md`, `session-notes.md`,
  `reflexes.md`, `feature-14-v2-architecture.md`.

Which questions that affects, from the files each question's expected chain cites (read
from the two eval files):

| question | expected chain cites a file the adapter skips |
|---|---|
| eval 4 | `docs/reviews/2026-08-31-spec-0008-app-shell-and-navigation.md` |
| eval 5 | `docs/scope/scope.md` |
| held out 1 | `docs/specs/0010-profile-entry/verify.md` |
| held out 2 | `docs/scope/scope.md` |

The other five chains sit wholly in specs that adapted. No question's chain cites 0020 or
0021. Before the run this README's setup report named only eval 4 and 5; reading the held
out file afterwards added held out 1 and 2.

## Cost

**$0.1508 in all**: ingest $0.0049 and nine queries $0.1459, against an estimate of about
$0.10 to $0.18 and a ceiling of $0.50.

- Ingest: 992 chunks, 243,108 embedding input tokens (the dry run's own count) at $0.02 per
  million. `ingest` does not report provider usage, so this figure is computed, not billed.
- Queries: each trace's provider rows (input and output tokens per call, as OpenAI reported
  them) priced at decision-memory's documented rates: `gpt-4o` $2.50 in and $10.00 out,
  `gpt-4o-mini` $0.15 in and $0.60 out, per million tokens (its experiment 0007). The
  question's own embedding reports 0 tokens in the trace and is left out; at about 50
  tokens it is under $0.000002.
- The estimate came from the 27 traces kept in decision-memory's repository, priced the
  same way ($0.0076 to $0.0188 per query), whose chunks average 245 tokens, as JobHunt's do.

| question | decision-memory calls (facets / answer / decompose / entailment / coverage) | tokens in / out | decision-memory USD | tracepath `ask-1` USD |
|---|---|---|---|---|
| eval 1 | 1 / 1 / 5 / 4 / 0 | 9,069 / 1,053 | 0.0146 | 0.0494 |
| eval 2 | 1 / 1 / 5 / 4 / 1 | 18,398 / 1,334 | 0.0208 | 0.0539 |
| eval 3 | 1 / 1 / 4 / 0 / 0 | 5,892 / 609 | 0.0111 | 0.0202 |
| eval 4 | 1 / 1 / 4 / 3 / 1 | 8,070 / 761 | 0.0150 | 0.0539 |
| eval 5 | 1 / 1 / 5 / 4 / 0 | 12,151 / 1,142 | 0.0152 | 0.0336 |
| held out 1 | 1 / 1 / 4 / 8 / 1 | 10,673 / 1,193 | 0.0164 | 0.0561 |
| held out 2 | 1 / 1 / 6 / 8 / 1 | 13,504 / 1,684 | 0.0195 | 0.0326 |
| held out 3 | 1 / 1 / 3 / 7 / 1 | 9,266 / 1,100 | 0.0159 | 0.0383 |
| held out 4 | 1 / 1 / 7 / 4 / 1 | 10,450 / 1,325 | 0.0174 | 0.0438 |
| all | | | 0.1459 | 0.3818 |

## What happened

**decision-memory abstained on all nine**: each printed `not enough evidence here`, with no
citation, exit 0. Every trace records `state: abstained` at `abstention_stage:
claim_verification`, the last stage.

Retrieval reached the records each expected chain names. Counted at record level only (a
record id among the 8 chunks retrieval accepted), not at the line an expected item cites:

| question | expected chain's spec records | among accepted | not accepted |
|---|---|---|---|
| eval 1 | 0003, 0007, 0008 | all | none |
| eval 2 | 0001, 0008, 0011, 0014 | 0001, 0008, 0014 | 0011 |
| eval 3 | 0002, 0007 | all | none |
| eval 4 | 0007, 0008, 0009 | all | none |
| eval 5 | 0007, 0009 | all | none |
| held out 1 | 0004, 0010 | all | none |
| held out 2 | 0017, 0018 | all | none |
| held out 3 | 0016, 0017, 0018 | all | none |
| held out 4 | 0016, 0017, 0018 | all | none |

Each time, `gpt-4o` split the question into facets and drafted 2 to 4 cited sentences.
Verification then removed some or all of them, and the answer abstains when any facet is
left without a surviving sentence. A sentence is dropped as `decomposition_invalid` when
its split into sub claims fails decision-memory's lexical check (a word in a sub claim
that is not in the sentence, such as `ensure` or `feature`), or as `unsupported_sub_claim`
when `gpt-4o-mini` judges a sub claim unsupported by its chunks.

| question | facets | drafted | removed | facets left uncovered | drop reasons |
|---|---|---|---|---|---|
| eval 1 | 3 | 3 | 3 | 3 | 2 decomposition_invalid, 1 unsupported_sub_claim |
| eval 2 | 3 | 3 | 2 | 1 | 2 decomposition_invalid |
| eval 3 | 1 | 2 | 2 | 1 | 2 decomposition_invalid |
| eval 4 | 3 | 3 | 2 | 2 | 1 decomposition_invalid, 1 unsupported_sub_claim |
| eval 5 | 3 | 3 | 3 | 3 | 2 decomposition_invalid, 1 unsupported_sub_claim |
| held out 1 | 3 | 3 | 1 | 1 | 1 decomposition_invalid |
| held out 2 | 4 | 4 | 3 | 3 | 2 decomposition_invalid, 1 unsupported_sub_claim |
| held out 3 | 2 | 2 | 1 | 1 | 1 decomposition_invalid |
| held out 4 | 4 | 4 | 3 | 3 | 3 decomposition_invalid |

The drafts were never printed by the tool; they are kept in `answers.json`
(`draft_before_verification`) as evidence of where each answer stopped, not as answers.
decision-memory's own README names this failure first among its limitations ("It
over-abstains").

## The answers, side by side

tracepath's answer is each record's claims as stored, with the ids each claim cites and
the record's `missing` list; decision-memory's is its printed output, verbatim.

### Eval question 1

> Why does the landing rule's profile existence read (src/lib/landing-rule.ts) have its own dedicated query instead of reusing readOwnProfile(), which already reads the same row?

**tracepath** (`2026-10-19T21-08-46Z-why-does-the-landing-rule.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0494). Verdict: `answered`.

1. The landing rule uses a dedicated existence read because readOwnProfile()'s record_not_found path reports to Sentry and marks the profile.read span failed. An absent profile row is a normal case for the landing rule, so its read returns false and builds no failure(). [`0008/AC-7`]
2. The dedicated read is a new named export beside readOwnProfile() in src/features/profile/queries.ts, because it queries that feature's table. The landing rule in src/lib/landing-rule.ts imports it from there. [`0008/AC-5b`, `0008#build-plan:6`]
3. The exemption is narrow. A genuine query error is still a failure: the read goes through attempt(), and an error is never collapsed into false. On an errored read the landing rule sends the visitor to /search. [`0008/AC-7a`]
4. The existence read and the AC-7a error handling are built together with the landing rule. [`0008#build-plan:6`, `0008/AC-7`, `0008/AC-7a`]

**decision-memory** (`data/eval-q1-trace.txt.gz`, $0.0146). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Eval question 2

> Why does src/proxy.ts treat a Server Action request differently from every other request, and why does it detect one by the next-action header rather than by the route?

**tracepath** (`2026-10-19T21-57-44Z-eval-linked-records-research-q2.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0539). Verdict: `answered`.

1. The proxy withholds the refreshed session cookie from a Server Action response because the proxy also runs on the action POST and refreshes there. That write cost one of the 25 weekly Adzuna calls, and the action cannot defend against it from inside itself. [`0014#decision:7`, `0014/AC-20a`]
2. The proxy still hands the refreshed value to the request's own code via request.cookies.set(), so recordApplication can verify its caller. [`0014/AC-20a`, `0008/AC-10b`]
3. The action's read-only cookie adapter (AC-20) was measured not to be what makes an expired-session apply hold; AC-20a is. AC-20a amends AC-20. [`0014/AC-20`, `0014/AC-20a`]
4. The branch keys on the next-action request header rather than the route so that binding rule 6's guard is untouched. The proxy still cannot tell a protected path from a public one, and the difference is request kind, not destination. [`0014/AC-20a`, `0008/AC-10b`, `0001#binding-rules:32`]
5. The cost is that the browser keeps a stale cookie until its next ordinary request. GoTrue's refresh_token_reuse_interval (10 seconds) covers the reuse, and it was driven as two applies sixteen seconds apart with no request between them, which succeeded without revoking the token family. [`0014/AC-20a`, `0008/AC-10b`]

Missing, as the answer states it:

- Why detecting by the next-action header was chosen over other ways of recognising an action request; the items only give the route-blindness rationale.

**decision-memory** (`data/eval-q2-trace.txt.gz`, $0.0208). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Eval question 3

> Why is password sign in impossible on production?

**tracepath** (`2026-10-19T21-57-56Z-eval-linked-records-research-q3.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0202). Verdict: `partly`.

1. The original reason, per spec 0002 AC-10 (HISTORY: struck through and replaced by 0007), was that the enabling variable is absent on production, so both guards (the sign in page and the Server Action) fail closed. That no longer depended on how a build labels NODE_ENV. [`0002/AC-10`] (history)
2. The build step that satisfies AC-10 replaced the NODE_ENV guard with the validated DEV_SESSION_ENABLED check, failing closed, in both the action and the page guard. [`0002#build-plan:7`, `0002/AC-10`] (history)
3. The design constraint was that dev password sign in is enabled by an explicit variable defaulting to false, set only on Vercel Preview and locally, and production never carries it. [`0002#feature-design:27`]
4. Spec 0007 builds real sign in via Google and GitHub OAuth with no password anywhere, and deletes the development only password sign in from feature 1, so password sign in is gone altogether rather than merely blocked on production. [`0007#summary:1`, `0007#summary:4`, `feature-7#7-auth-per-user-isolation-done-ga:6`]
5. DEV_SESSION_ENABLED now has one job, guarding the test mint, and is no longer set on Vercel Preview. [`0007/AC-13`]

Missing, as the answer states it:

- The items do not state how the 0007 record explicitly replaces AC-10 beyond its being marked superseded; the superseding text is not given.
- Scope item for feature 27 mentions email and password sign up as a possible later alternative, but no decision on it is recorded.

**decision-memory** (`data/eval-q3-trace.txt.gz`, $0.0111). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Eval question 4

> Why is the return path cookie's max age 10 minutes? Is it matched to the lifetime of the PKCE code verifier cookie Supabase writes on the same sign in action, or to the session policy spec 0007 AC-19 records?

**tracepath** (`2026-10-19T21-58-07Z-eval-linked-records-research-q4.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0539). Verdict: `not_supported`.

1. The items state that the return cookie has a 10 minute max age, along with httpOnly, SameSite=Lax and a Path scoped to /auth/callback. They give no reason for choosing 10 minutes. [`0008/AC-14`, `0008#feature-design:13`]
2. Spec 0009 describes the same cookie as short lived at 600 seconds, which is 10 minutes. It does not say why that length was chosen. [`0009#follow-up:9`]
3. Spec 0007 AC-19 only says the session policy (token lifetime, refresh, forced logout, auth rate limits, manual linking) is recorded for all three environments. It gives no value and does not mention the return cookie, so nothing ties the 10 minutes to it. [`0007/AC-19`]
4. The PKCE verifier cookies are described as short lived cookies that @supabase/ssr writes during the OAuth handshake. No item gives their lifetime or relates it to the return cookie's max age. [`0009/AC-14`, `0009/AC-24`]

Missing, as the answer states it:

- The rationale for the 10 minute max age of the return path cookie
- The max age of the Supabase PKCE code verifier cookie
- Any session policy value in 0007 AC-19 that the 10 minutes could be matched to
- Any statement that the return cookie's lifetime was chosen to match either the verifier cookie or the session policy

**decision-memory** (`data/eval-q4-trace.txt.gz`, $0.0150). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Eval question 5

> Why was feature 21 (terms and privacy notices) built in Foundation immediately after feature 32, when it was originally scoped into Slice 5 as launch readiness work?

**tracepath** (`2026-10-19T21-58-18Z-eval-linked-records-research-q5.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0336). Verdict: `answered`.

1. Feature 21 moved because leaving Google's Testing mode was gated on it: Publish app was greyed out since the privacy policy and terms links were empty, and feature 21 is what produces them. [`0007#consequences:11`]
2. The urgency was that the app stayed capped at 100 users until it was published. Google counts that cap over the app's whole lifetime, so it never goes back down. [`0007#consequences:11`]
3. When that paragraph was written, feature 21 sat in Slice 5 and neither scope row recorded the dependency. Both rows were changed on the strength of it, and the feature moved to Foundation, to be built after feature 32. [`0007#consequences:11`, `feature-21#21-terms-privacy-notices-done-alpha:5`]
4. A follow-up says the move went further than the follow-up itself asked: the dependency was recorded on feature 21's row, and the feature moved out of Slice 5 into Foundation. [`0007#follow-up:12`]
5. Feature 21 and feature 7 depend on each other. Feature 21 unblocks Publish app, which lifts the lifetime 100 user cap, and feature 7 is what makes the notices load bearing rather than paperwork. [`0007#follow-up:11`]
6. The pages had to be served from `usejobhunt.dev`, because Google would not accept a `vercel.app` address as an Authorized domain. [`0007#follow-up:10`]
7. Feature 21 was owed the day the first person other than the author signs in, which fits pulling it forward. [`feature-21#21-terms-privacy-notices-done-alpha:1`]
8. The outcome: on 2026-09-01 feature 21 published the policy and terms on `usejobhunt.dev`, which let the app register that Authorized domain, leave Testing and submit brand verification. [`scope#resolved:4`]

Missing, as the answer states it:

- Why feature 32 specifically is the point after which feature 21 was placed; the items do not describe feature 32 or why the order is after it.

**decision-memory** (`data/eval-q5-trace.txt.gz`, $0.0152). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Held out question 1

> Why does test/integration/profile-form.test.ts read the $ACTION_ field index out of the rendered /profile page and scope its read to one form, when spec 0010's build plan says to confirm the fields $ACTION_REF_1 / $ACTION_1:0 / $ACTION_1:1 are present?

**tracepath** (`2026-10-19T22-17-23Z-eval-held-out-q1.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0561). Verdict: `answered`.

1. The build plan's wording (`$ACTION_REF_1` / `$ACTION_1:0` / `$ACTION_1:1`) was a spike, written before the field shape was proven; it assumed the shape from spec 0004's Follow up recipe and asked for it to be confirmed in the rendered HTML. [`0010#build-plan:3`]
2. Spec 0004's Follow up later corrected this: `<n>` is a per form index, not part of the field name. The correction was dated 2026 09 02, when feature 9 proved it against React 19.2.8 and Next.js 16.3.1, so the test reads the index out of the rendered page rather than assuming 1. [`0004#follow-up:8`]
3. The read is scoped to the one form under test because otherwise the sign out action's own hidden field is harvested and posted alongside the identity form's fields. [`0004#follow-up:8`]
4. The test is the one the Follow up points to as meeting spec 0001's third runner constraint, and it implements AC-14: fetch the page with the edit form open, read the hidden action fields, post them back, and expect a redirect carrying the session cookie. [`0004#follow-up:7`, `0010/AC-14`, `0010#build-plan:9`]

Missing, as the answer states it:

- The test file's own contents are not among the items; the explanation rests on the spec 0004 Follow up's description of it.
- Spec 0001's third runner constraint is unresolved in the records, so its exact wording is not available.

**decision-memory** (`data/held-out-q1-trace.txt.gz`, $0.0164). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Held out question 2

> Why does spec 0018 say to read a pair's `distribution` and never its `summary` when asking how the five reruns split, given that spec 0017 requires every verdict to carry a count like '5 of 5 succeeded'?

**tracepath** (`2026-10-19T22-17-37Z-eval-held-out-q2.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0326). Verdict: `answered`.

1. Spec 0018 says the `5 of 5` in a `summary` like "possible_match, 5 of 5 succeeded" is the success denominator, meaning all five reruns returned a band. It is not the count landing on that band, so it cannot show how the reruns split. [`0018#review-findings:1`]
2. Spec 0018 therefore tells readers to use `distribution`, never `summary`, when the question is how the reruns split. [`0018#review-findings:2`]
3. This does not contradict spec 0017's AC-6, which requires every verdict to name its denominator, such as "good_match, 3 of 3 succeeded", never just a band. That denominator is the count of successful reruns, not a per-band count. [`0017/AC-6`]
4. Spec 0017 reports a distribution-shaped verdict as a per-band split with the denominator, e.g. "3 strong_match / 2 possible_match, 5 of 5 succeeded". A stability-probe pair is always reported as its observed distribution, never a lone band. So the per-band split lives in the distribution, and the denominator only says how many reruns were scored. [`0017/AC-6`, `0017/AC-4`]

Missing, as the answer states it:

- The items do not show spec 0018's own wording explaining why `distribution` is preferred beyond the denominator-versus-band-count distinction, nor the structure of the `distribution` field itself.

**decision-memory** (`data/held-out-q2-trace.txt.gz`, $0.0195). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Held out question 3

> control-one-gap passed its confirming run by only 3 to 2 (possible_match over good_match). Why can't it be given acceptableBands [good_match, possible_match] so it stops sitting one rerun away from having no majority?

**tracepath** (`2026-10-19T22-17-49Z-eval-held-out-q3.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0383). Verdict: `partly`.

1. Widening `control-one-gap` with `acceptableBands` is refused outright by the Key invariants of spec 0018, and `ground-truth.test.ts` now asserts that no `control` tagged pair carries `acceptableBands`. [`0018#follow-up:4`]
2. Retagging the pair `boundary` is not a way out either, because it would concede the anchors do not settle the pair, which contradicts spec 0018's finding that they do. So the retag and the tolerance are not independent choices. [`0018#follow-up:4`]
3. The pair's expectation is `possible_match` with no `acceptableBands`, argued from the existing `possible_match` anchor text. [`0018/AC-1`, `0018#review-findings:3`]
4. The earlier expectation of `good_match` is HISTORY: it was corrected to `possible_match` by feature-16#16-eval-harness-runner:17, so a range containing `good_match` would reintroduce the expectation that was dropped. [`feature-16#16-eval-harness-runner:16`, `feature-16#16-eval-harness-runner:17`] (history)
5. Under the harness rules, a 3 to 2 result still counts as a strict majority and passes. With no `acceptableBands`, a rerun with no majority would be `inconclusive` (`no-majority`). [`0017#requirements:7`]
6. The follow-up records the question of whether the pair keeps its `control` tag as recorded but not answered. [`0018#follow-up:4`]

Missing, as the answer states it:

- Text of the Key invariants section of spec 0018, which the follow-up cites as the reason `acceptableBands` is refused for control pairs
- Any decision on whether `control-one-gap` keeps its `control` tag

**decision-memory** (`data/held-out-q3-trace.txt.gz`, $0.0159). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

### Held out question 4

> Why does band-anchors.test.ts pin BAND_ANCHORS twice, once as five inline strings and once as bandAnchorsHash(BAND_ANCHORS), when either assertion alone fails on an anchor edit?

**tracepath** (`2026-10-19T22-18-05Z-eval-held-out-q4.json`, prompt `ask-1`, `claude-sonnet-5-5`, $0.0438). Verdict: `answered`.

1. The two assertions guard different things. The inline `toEqual` pins the anchor wording, and the hash assertion pins `bandAnchorsHash(BAND_ANCHORS)`, which is the value written into every eval report. A change to the hash function alone is therefore caught too, even if the anchor text is untouched. [`0016#follow-up:6`]
2. The inline strings are used instead of a snapshot file because a routine `vitest -u` could silently rewrite a snapshot. The hash is checked against today's computed value. [`0017/AC-10`]
3. The hash is defined once and shared between the report and the drift test, so the report's hash and the test's hash are computed the same way by construction. Pinning it in the test therefore protects the value that reports carry for comparison. [`0017/AC-9`]
4. The wording pin exists because the anchors' own comment says the wording is expected to change, and every expected band and rationale in the ground truth set derives from today's wording. Spec 0016 asked the harness spec to detect that drift, and AC-10 is the item that does so. [`0016#follow-up:5`, `0016#follow-up:6`]
5. The build step for the drift test satisfies AC-10 with both a literal `toEqual` pin and a `bandAnchorsHash()` equality check, each failing by name and pointing at spec 0016's dataset. [`0017#build-plan:6`, `0017/AC-10`]

Missing, as the answer states it:

- No item states explicitly why the hash check is kept beyond catching a hash function change, for example whether the two were meant to cross check each other on an anchor edit.

**decision-memory** (`data/held-out-q4-trace.txt.gz`, $0.0174). State: `abstained` at `claim_verification`.

```text
not enough evidence here
```

Citations: none.

## Marks

Judged by the engineer with the needed points rule: an answer is right when it gives the
points the question needs.

| question | tracepath (`ask-1`) | decision-memory |
|---|---|---|
| eval 1 | | |
| eval 2 | | |
| eval 3 | | |
| eval 4 | | |
| eval 5 | | |
| held out 1 | | |
| held out 2 | | |
| held out 3 | | |
| held out 4 | | |

## Limits of this comparison

- **Different model providers.** decision-memory runs on OpenAI (`gpt-4o`, `gpt-4o-mini`,
  `text-embedding-3-small`); tracepath on Claude (`claude-sonnet-5-5`). A difference here
  is the two tools and their models together, not the design alone.
- **One run per question is a snapshot.** decision-memory's output varies between runs (its
  README says so, and its experiment 0014 measured it over 12 runs), and so does whether a
  drafted sentence survives decomposition. tracepath's answers are also one run each.
- **Different inputs.** tracepath answers from its extracted graph of 240 units, which
  includes `scope.md` and spec 0020 and 0021 sections; decision-memory sees 19 specs'
  `index.md` and `rationale.md` only (see above). Four of the nine expected chains cite a
  file decision-memory never reads.
- **Not the same day.** tracepath's answers are from 2026-10-19; decision-memory's from
  2026-10-20. The corpus is the same pinned commit for both.
- **Retrieval is compared at record level only**, from the files each expected chain names;
  whether the accepted chunks hold the expected lines was not checked.
