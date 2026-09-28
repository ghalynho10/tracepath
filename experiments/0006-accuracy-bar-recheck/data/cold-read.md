# Cold read, experiment 0006 (spec 0003, AC-30)

Read each passage's own text first. Only once you have your own answer for what relation, if any, it states, look below its divider at every link the before and after runs actually wrote from it. Reported alongside the ruling, not pass or fail on its own: the question is whether a real link is missing from all three buckets, accepted, held and dropped alike.

3 passages per unit, drawn at random, seed `20260928001`, reproducible by re-running `prepare_cold_read.py`.

## 0014 / requirements (Requirements)

### Passage 1

```text
- **AC-9**: A search result the caller has already applied to is visibly marked as applied, and its `Mark as applied` control is disabled. Two paths reach that state and both are covered: a server read at render time (`readAppliedJobIds`, scoped to the `source_job_id` values actually rendered), and the action's own returned state after a successful apply in this render. The applied state is reached only on a confirmed database write, never optimistically.
```

---

*(no link, before or after, sources from this passage)*

### Passage 2

```text
- **AC-18**: `/applications` lists rows newest applied first by `applied_at`, and shows for each the full stored snapshot: title, company, location, salary, description snippet, posted date, applied date, and the link out to the posting carrying `COPY-6`. `applied_at` renders as an absolute date and `posted_at` reuses feature 11's relative formatter, because a relative applied date is the one that ages into uselessness on an archive.
```

---

**before**
- **held** · unclassified · written by 2 of 3 runs
  - source: `0014/AC-18` AcceptanceCriterion: `/applications` lists rows newest applied first by `applied_at`, and shows for each the full stored snapshot: title, company, location, salary, description snippet, posted date, applied date, and the link out to the posting carrying `COPY-6`. `applied_at` renders as an absolute date and `posted_at` reuses feature 11's relative formatter,
  - target: reference `0011` (whole record), mention: feature 11's relative formatter
  - phrase: feature 11's relative formatter
**before**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `0014/AC-18` AcceptanceCriterion: `/applications` lists rows newest applied first by `applied_at`, and shows for each the full stored snapshot: title, company, location, salary, description snippet, posted date, applied date, and the link out to the posting carrying `COPY-6`. `applied_at` renders as an absolute date and `posted_at` reuses feature 11's relative formatter.
  - target: reference `feature 11` (whole record), mention: feature 11's relative formatter
  - phrase: reuses feature 11's relative formatter
**after**
- **dropped** · unclassified · written by 2 of 3 runs
  - source: `0014/AC-18` AcceptanceCriterion: **AC-18**: `/applications` lists rows newest applied first by `applied_at`, and shows for each the full stored snapshot: title, company, location, salary, description snippet, posted date, applied date, and the link out to the posting carrying `COPY-6`. `applied_at` renders as an absolute date and `posted_at` reuses feature 11's relative formatter, because a relative applied date is the one that ages into uselessness on an archive.
  - target: reference `feature 11` (whole record), mention: feature 11's relative formatter
  - phrase: feature 11's relative formatter

### Passage 3

```text
- As a job seeker, I want a search to show me which jobs I already applied to, so that I do not waste an application or a click on a job I already sent.
```

---

*(no link, before or after, sources from this passage)*


## 0015 / feature-design (Feature design)

### Passage 1

```text
- No new credential. `OPENAI_API_KEY` is already declared and validated (spec 0012); this feature adds no new environment variable.
```

---

**before**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `0015#feature-design:14` Constraint: No new credential. OPENAI_API_KEY is already declared and validated; this feature adds no new environment variable.
  - target: reference `0012` (whole record), mention: (spec 0012)
  - phrase: already declared and validated (spec 0012)
**after**
- **held** · unclassified · written by 3 of 3 runs
  - source: `0015#feature-design:23` Constraint: No new credential. `OPENAI_API_KEY` is already declared and validated (spec 0012); this feature adds no new environment variable.
  - target: reference `0012` (whole record), mention: spec 0012
  - phrase: (spec 0012)

### Passage 2

```text
**State transitions**: none. Scoring is stateless per render, matching spec 0012's own router.
```

---

**before**
- **dropped** · unclassified · written by 2 of 3 runs
  - source: `0015#feature-design:1` Constraint: Scoring is stateless per render
  - target: reference `0012` (whole record), mention: spec 0012's own router
  - phrase: matching spec 0012's own router
**after**
- **accepted** · unclassified · written by 3 of 3 runs
  - source: `0015#feature-design:2` Constraint: **State transitions**: none. Scoring is stateless per render, matching spec 0012's own router.
  - target: reference `0012` (whole record), mention: spec 0012's own router
  - phrase: matching spec 0012's own router

### Passage 3

```text
**API surface**:
| Function | Kind | Key inputs | Key outputs | Auth | Key errors |
|---|---|---|---|---|---|
| `scoreListing()` (`src/features/scoring/score.ts`) | server function | `profile: ScoringProfile` (the bounded shape from AC-13), `listing: Listing` | `Result<{ allowed: true; value: FitScore } \| { allowed: false; reason: UsageGateReason }>` | inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached | `session_missing`, `usage_gate_misconfigured`, `database_unavailable` (from the gate), `external_service_failed`, `response_malformed` (from the vendor call), all inherited unchanged from spec 0012 |
| `scoreListings()` (`src/features/scoring/score-listings.ts`) | server function | `profile: ScoringProfile`, `listings: readonly Listing[]` | `readonly ScoreOutcome[]`, one per listing, order preserved, each element is `scoreListing()`'s own `Result` | same as `scoreListing()`, per call | none of its own; each element carries its own `scoreListing()` outcome |
| `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) | client components, one module | `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it; `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened | nothing rendered; the only effect is a `.focus()` call, and only under AC-17's four rules | none of its own; it reads no user data and calls no server function | none; a missing key falls back per AC-17 rather than failing |
```

---

**before**
- **held** · unclassified · written by 2 of 3 runs
  - source: `0015#feature-design:18` Feature: `scoreListing()` (`src/features/scoring/score.ts`) is a server function taking `profile: ScoringProfile` (the bounded shape from AC-13) and `listing: Listing`, returning `Result<{ allowed: true; value: FitScore } | { allowed: false; reason: UsageGateReason }>`, with auth inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached
  - target: reference `0012` (whole record), mention: inherited from `callTier()`
  - phrase: inherited from `callTier()`
**before**
- **held** · unclassified · written by 1 of 3 runs
  - source: `0015#feature-design:20` Feature: `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) are client components in one module; `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it, and `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened; nothing is rendered and the only effect is a `.focus()` call, only under AC-17's four rules
  - target: reference `0015` AC-17, mention: under AC-17's four rules
  - phrase: under AC-17's four rules
**before**
- **dropped** · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:25` Feature: scoreListing() (src/features/scoring/score.ts): a server function taking profile: ScoringProfile and listing: Listing, returning Result<{ allowed: true; value: FitScore } | { allowed: false; reason: UsageGateReason }>, with auth inherited from callTier(), which verifies the caller through checkUsageGate()'s getClaims() before any vendor is reached
  - target: reference `None` AC-13, mention: the bounded shape from AC-13
**before**
- **dropped** · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:27` Feature: FocusRecorder / FocusRestorer (src/features/search/focus-keeper.tsx): client components in one module; FocusRecorder is rendered outside the Suspense boundary so the reveal never unmounts it, and FocusRestorer is rendered inside the resolved content so mounting it is the signal that the reveal happened; nothing is rendered, the only effect is a .focus() call
  - target: reference `None` AC-17, mention: AC-17's four rules


## feature-33 / 33-band-anchor-review-done (Band anchor review)

### Passage 1

```text
- [x] Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018. One pins the corrected `possible_match` expectation so a silent revert to `good_match` fails by name; the other is the general form, asserting that **no `control` tagged pair carries `acceptableBands`**, which is spec 0018's Key invariant that a tolerance is not a way to stop a pair failing, grounded in spec 0016's own reasoning for why `mild-stretch-possible-match` takes "no `acceptableBands` and the plain `control` tag rather than `boundary`". Pinning only `control-one-gap` would have left that escape open on every other control. Each was broken on purpose **after** the commit hooks ran, per the 2026-09-05 reflex, and each failed with its own message, the second naming the offending pair id. AC-1b, AC-4 and AC-4b are deliberately **not** automated: the first would be a test reading comment text, which Prettier can silently invalidate, and the other two are prose corrections in docs. All three are proved by `/check verify` instead, and AC-5 is the paid run
```

---

**before**
- **held** · verifies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` TestScenario: One pins the corrected `possible_match` expectation so a silent revert to `good_match` fails by name
  - target: reference `0018` (whole record), mention: both tracing to spec 0018
**before**
- **held** · unclassified · written by 2 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:12` TestScenario: the other is the general form, asserting that no `control` tagged pair carries `acceptableBands`, which is spec 0018's Key invariant that a tolerance is not a way to stop a pair failing
  - target: reference `0016` (whole record), mention: grounded in spec 0016's own reasoning
  - phrase: grounded in
**before**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:10` BuildStep: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` (whole record), mention: AC-1b, AC-4 and AC-4b are deliberately not automated... proved by /check verify instead
  - phrase: proved by `/check verify` instead
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` (whole record), mention: spec 0018
  - phrase: both tracing to spec 0018
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0016` (whole record), mention: spec 0016's own reasoning
  - phrase: grounded in spec 0016's own reasoning for why `mild-stretch-possible-match` takes "no `acceptableBands` and the plain `control` tag rather than `boundary`"
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` AC-1b, mention: AC-1b
  - phrase: AC-1b, AC-4 and AC-4b are deliberately **not** automated
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` AC-4, mention: AC-4
  - phrase: AC-1b, AC-4 and AC-4b are deliberately **not** automated
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` AC-4b, mention: AC-4b
  - phrase: AC-1b, AC-4 and AC-4b are deliberately **not** automated
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` AC-5, mention: AC-5
  - phrase: AC-5 is the paid run

### Passage 2

```text
- [x] Build it: `/develop band anchor review`
  - [x] Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
  - [x] Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
  - [x] Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3. 1178 unit tests green, `git diff main -- src/features/scoring/rubric.ts` empty. The band coverage guard was broken on purpose (pointing `good-match-adjacent` at `possible_match`) and failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", so the pass is not vacuous
  - [x] Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5. **PASS** 2026-09-09T03:44Z, anchor hash `1b45f524b356` unchanged, exit 0. Distribution `good_match` 2, `possible_match` 3, read from the report's `distribution` field: the pair passes on the strict majority and clears spec 0017's 3 of 5 floor, but by the minimum margin, and the old `good_match` expectation has now lost on all three runs ever taken (4 to 1, 5 to 0, 3 to 2). The five calls were confirmed by measurement rather than by reading the filter output, `ai_scoring global` day 2026-09-09 from absent to 5 and month 1225 to 1230, read through `pg` directly. Note the UTC day had already rolled at 03:44Z, so the 2026-09-08 row stayed at 195 and watching that row would have shown no movement
```

---

**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:5` BuildStep: Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception
  - target: reference `0018` AC-1, mention: AC-1
**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:5` BuildStep: Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception
  - target: reference `0018` AC-1b, mention: AC-1b
**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:6` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense
  - target: reference `0018` AC-4, mention: AC-4
**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:6` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense
  - target: reference `0018` AC-4b, mention: AC-4b
**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:7` BuildStep: Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`
  - target: reference `0018` AC-2, mention: AC-2
**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:7` BuildStep: Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`
  - target: reference `0018` AC-3, mention: AC-3
**before**
- **accepted** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:8` BuildStep: Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty
  - target: reference `0018` AC-5, mention: AC-5
**before**
- **dropped** · corrected-by · written by 2 of 3 runs
  - source: reference `scope.md` (whole record), mention: the misread evidence at `scope.md:326`
  - target: `feature-33#33-band-anchor-review-done:5` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense
**before**
- **dropped** · corrected-by · written by 2 of 3 runs
  - source: reference `0016` (whole record), mention: spec 0016's stale table row and its Follow up quote that reads as present tense
  - target: `feature-33#33-band-anchor-review-done:5` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:8` BuildStep: Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
  - target: reference `0018` AC-1, mention: AC-1
  - phrase: satisfies AC-1, AC-1b
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:8` BuildStep: Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
  - target: reference `0018` AC-1b, mention: AC-1b
  - phrase: satisfies AC-1, AC-1b
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
  - target: reference `0018` AC-4, mention: AC-4
  - phrase: satisfies AC-4, AC-4b
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
  - target: reference `0018` AC-4b, mention: AC-4b
  - phrase: satisfies AC-4, AC-4b
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:10` BuildStep: Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3.
  - target: reference `0018` AC-2, mention: AC-2
  - phrase: satisfies AC-2, AC-3
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:10` BuildStep: Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3.
  - target: reference `0018` AC-3, mention: AC-3
  - phrase: satisfies AC-2, AC-3
**after**
- **held** · satisfies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` BuildStep: Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5.
  - target: reference `0018` AC-5, mention: AC-5
  - phrase: satisfies AC-5
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` BuildStep: Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5.
  - target: reference `0017` (whole record), mention: spec 0017's 3 of 5 floor
  - phrase: clears spec 0017's 3 of 5 floor
**after**
- **dropped** · amended-by · written by 1 of 3 runs
  - source: reference `0018` AC-1, mention: AC-1
  - target: reference `0018` AC-1b, mention: AC-1b
**after**
- **dropped** · amended-by · written by 1 of 3 runs
  - source: reference `0018` AC-4, mention: AC-4
  - target: reference `0018` AC-4b, mention: AC-4b
**after**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
  - target: reference `0016` (whole record), mention: spec 0016's stale table row and its Follow up quote
  - phrase: plus spec 0016's stale table row and its Follow up quote that reads as present tense

### Passage 3

```text
### 33. Band anchor review · done
Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
**Done when:** `control-one-gap` expects `possible_match` and passes a real run, `BAND_ANCHORS` and its hash `1b45f524b356` are untouched, the misread run evidence is corrected everywhere it was repeated, and the set still gives every band an exact expectation.
_spec [0018](../specs/0018-band-anchor-review/index.md) · code in `src/features/scoring/eval/pairs.ts`_
```

---

**before**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong.
  - target: reference `0018` (whole record), mention: spec [0018]
  - phrase: spec 0018
**before**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong.
  - target: reference `16` (whole record), mention: feature 16's harness
  - phrase: against what feature 16's harness actually measured
**before**
- **dropped** · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong.
  - target: reference `feature-16` (whole record), mention: feature 16's harness
  - phrase: against what feature 16's harness actually measured
**after**
- **held** · unclassified · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
  - target: reference `feature 16` (whole record), mention: feature 16's harness
  - phrase: against what feature 16's harness actually measured

