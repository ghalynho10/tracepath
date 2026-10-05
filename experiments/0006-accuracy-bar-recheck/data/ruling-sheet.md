# Ruling sheet, experiment 0006 (spec 0003, AC-30)

Replace each line's marks with one word, and add a few words on why when you disagree, matching experiment 0005's own ruling-sheet.md convention. No item in the entity or relationship sample is left unruled; `unsure` is allowed and counted on its own, neither agree nor disagree.

- **Entities**: `agree` when the model's cut and type pass HANDOFF's three question test (atomicity, referenceability, right sizing) and the deletion trick, `disagree` otherwise.
- **Relationships**: `agree` when the link is real, and its type, direction and endpoints are what you would have written, `disagree` otherwise.
- **Dropped links**: `real link lost` when the source text states a relation the afters should have kept, `rightly dropped` when it does not. Drawn at random, seed `20260928`, reproducible by re-running this script.

Not built here, needed before the bar can be applied (AC-30): the cold read (3 passages per unit) and the blind self agreement check (10 earlier calls), both reported alongside the ruling, not pass or fail on their own.

## 0014 / requirements (Requirements, no prior worked example of this record)

### Entities

10 evenly spaced through after run 1's located order.

- [x] disagree · `0014#requirements:1` · Feature
  - reason: the so-that clause states a product rule (no application process of the app's own), stated nowhere else in the unit; it belongs in the span, not rejected

  - span: As a job seeker, I want to open the real posting on the source site,
  - rejected: ["so that I apply through the employer's own process rather than through a copy of it."]
- [x] agree · `0014#requirements:3` · Feature
  - reason: the so-that clause reads as rationale; the story's action is delivered by AC-9, and nothing it rules out stands on its own

  - span: As a job seeker, I want a search to show me which jobs I already applied to,
  - rejected: ['so that I do not waste an application or a click on a job I already sent.']
- [x] agree · `0014/AC-1` · AcceptanceCriterion
  - reason: bundled AC-N kept whole and flagged, ruled agree by the convention · gap:bundled-ac

  - span: **AC-1**: A result card carries a `Mark as applied` control that is separate from feature 11's `View the posting` link. Opening a posting records nothing at all: no row is written by the click through, and no state changes.
  - flags: multi_condition_split
- [x] agree · `0014/AC-4` · AcceptanceCriterion
  - reason: bundled AC-N kept whole and flagged, ruled agree by the convention (sentence 2 is its own condition: the refusal must come from the unique constraint) · gap:bundled-ac

  - span: **AC-4**: A second apply to the same `(profile_id, source, source_job_id)` writes no second row and produces a visible expected failure carrying `COPY-2`, kind `validation_failed`, severity `expected`. The refusal comes from the unique constraint, so it holds for a caller that never checked first (spec 0003, AC-7).
  - flags: multi_condition_split
- [x] disagree · `0014/AC-6` · AcceptanceCriterion
  - reason: minor: bundle correctly kept whole, but "so it never makes a claim about a figure that does not exist" is the reason for null over false (it cannot fail while the rest passes), so it belongs in rejected

  - span: **AC-6**: `application.salary_is_predicted` exists as a nullable boolean, and a check constraint makes it present exactly when `salary_min` or `salary_max` is present. When Adzuna stated no pay at all, the column is written `null` and never `false`, so it never makes a claim about a figure that does not exist.
  - flags: multi_condition_split
- [x] agree · `0014/AC-9` · AcceptanceCriterion
  - reason: bundled AC-N kept whole and flagged, ruled agree by the convention · gap:bundled-ac

  - span: **AC-9**: A search result the caller has already applied to is visibly marked as applied, and its `Mark as applied` control is disabled. Two paths reach that state and both are covered: a server read at render time (`readAppliedJobIds`, scoped to the `source_job_id` values actually rendered), and the action's own returned state after a successful apply in this render. The applied state is reached only on a confirmed database write, never optimistically.
  - flags: multi_condition_split
- [x] agree · `0014/AC-12` · AcceptanceCriterion

  - span: **AC-12**: `job_description` holds the Adzuna description snippet the search already parsed, and the spec that describes that column as the full posting text is corrected in every place it says so.
- [x] agree · `0014/AC-14` · AcceptanceCriterion
  - reason: bundled AC-N kept whole and flagged, ruled agree by the convention · gap:bundled-ac

  - span: **AC-14**: The four operations this feature adds each open a named span as their first statement, at the moment the operation is first written rather than in a later pass, and are registered in [spans.md](../../observability/spans.md) with `op: "db.query"`: `application.record`, `application.remove`, `application.read_list`, and `search.read_applied`.
  - flags: multi_condition_split
- [x] agree · `0014/AC-17` · AcceptanceCriterion
  - reason: "so the empty state has an exit" is the reason (cannot fail while the link is there), rightly rejected

  - span: **AC-17**: `/applications` with no rows keeps its existing promise sentence and adds a link to `/search` carrying `COPY-5`.
  - rejected: ['so the empty state has an exit rather than being a dead end']
- [x] disagree · `0014/AC-20` · AcceptanceCriterion
  - reason: part 2, the premise ("A cookie write inside a Server Action puts a re-render ... a second Adzuna call"), is the reason for the rule and should be in rejected

  - span: **AC-20**: The apply action builds its Supabase client with a **read only cookie adapter**, so nothing inside it can write a session cookie. A cookie write inside a Server Action puts a re-render of the current route into the action's response, which on `/search` means a second Adzuna call. **This criterion is defence in depth, and it is NOT what makes AC-10 hold for an expired session** (corrected 2026-09-05, revision 4; the original wording said it was). Measured: with the adapter in place and unchanged, an expired session apply still spent a call, because the write came from `src/proxy.ts`, which runs on the action `POST` too. The adapter closes a door this bug never used, and it stays closed because a later session adding a cookie write inside the action would reopen it. What actually makes AC-10 hold for an expired session is **AC-20a**.
  - flags: multi_condition_split, rationale_boundary_call

### Relationships

5 evenly spaced through the 17 distinct links the three after runs wrote.

- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0014/AC-4` AcceptanceCriterion: **AC-4**: A second apply to the same `(profile_id, source, source_job_id)` writes no second row and produces a visible expected failure carrying `COPY-2`, kind `validation_failed`, severity `expected`. The refusal comes from the unique constraint, so it holds for a caller that never checked first (spec 0003, AC-7).
  - target: reference `0003` AC-7, mention: spec 0003, AC-7
  - phrase: The refusal comes from the unique constraint, so it holds for a caller that never checked first (spec 0003, AC-7)
  - source text:
    > - **AC-4**: A second apply to the same `(profile_id, source, source_job_id)` writes no second row and produces a visible expected failure carrying `COPY-2`, kind `validation_failed`, severity `expected`. The refusal comes from the unique constraint, so it holds for a caller that never checked first (spec 0003, AC-7).
- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0014/AC-8` AcceptanceCriterion: **AC-8**: Every application row displayed on `/applications` carries its own `Jobs by Adzuna` attribution through `Card.Footer`'s attribution slot, on the same terms spec 0013 AC-6 sets for a search result, with the link target read from `ADZUNA_ATTRIBUTION_URL`. Attribution renders once per displayed row and never once per screen (spec 0013, invariant 4). A page with no rows shows no attribution block.
  - target: reference `0013` AC-6, mention: spec 0013 AC-6
  - phrase: on the same terms spec 0013 AC-6 sets for a search result
  - source text:
    > - **AC-8**: Every application row displayed on `/applications` carries its own `Jobs by Adzuna` attribution through `Card.Footer`'s attribution slot, on the same terms spec 0013 AC-6 sets for a search result, with the link target read from `ADZUNA_ATTRIBUTION_URL`. Attribution renders once per displayed row and never once per screen (spec 0013, invariant 4). A page with no rows shows no attribution block.
- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0014/AC-11` AcceptanceCriterion: **AC-11**: An application can be removed from `/applications`. The removal is confirmed first at `/applications?remove=<id>`, that URL mutates nothing on its own, and the question carries `COPY-4`, naming the job being removed rather than asking a bare "are you sure". A removal matching zero rows is a reported failure, not a silent success. On success the remove action **does** call `revalidatePath("/applications")`.
  - target: `0014/AC-10` AcceptanceCriterion: **AC-10**: Marking applied does not re-render `/search`. No second Adzuna call is made, no `job_search` gate check is spent, and the weekly counter does not move. This holds for a fresh session **and for a session whose access token has expired**. Measured against a production build (`pnpm build && pnpm start`), never under `pnpm dev`, for the reason spec 0013's AC-10 records.
  - phrase: the deviation in AC-10 is scoped to the apply action alone
  - source text:
    > - **AC-11**: An application can be removed from `/applications`. The removal is confirmed first at `/applications?remove=<id>`, that URL mutates nothing on its own, and the question carries `COPY-4`, naming the job being removed rather than asking a bare "are you sure". A removal matching zero rows is a reported failure, not a silent success. On success the remove action **does** call `revalidatePath("/applications")`, because that page makes no outbound call and the deviation in AC-10 is scoped to the apply action alone.
- [x] agree · unclassified · written by 2 of 3 runs
  - reason: AC-20 still stands in full and its old wording is only described, so no history type fits; a pointer between two standing criteria is unclassified

  - source: `0014/AC-20` AcceptanceCriterion: **AC-20**: The apply action builds its Supabase client with a **read only cookie adapter**, so nothing inside it can write a session cookie. A cookie write inside a Server Action puts a re-render of the current route into the action's response, which on `/search` means a second Adzuna call. **This criterion is defence in depth, and it is NOT what makes AC-10 hold for an expired session** (corrected 2026-09-05, revision 4; the original wording said it was). Measured: with the adapter in place and unchanged, an expired session apply still spent a call, because the write came from `src/proxy.ts`, which runs on the action `POST` too. The adapter closes a door this bug never used, and it stays closed because a later session adding a cookie write inside the action would reopen it. What actually makes AC-10 hold for an expired session is **AC-20a**.
  - target: `0014/AC-20a` AcceptanceCriterion: **AC-20a**: `src/proxy.ts` **withholds the refreshed session cookie from the response of a Server Action request**, while still handing the refreshed value to that request's own code through `request.cookies.set()`, so `recordApplication` can verify its caller. The branch keys on the presence of Next's `next-action` request header, never on the route, so binding rule 6's mechanical guard is untouched: the proxy still cannot tell a protected path from a public one. This is the criterion the 25 weekly Adzuna calls actually rest on. **The trade is deliberate**: the browser keeps its stale cookie until its next ordinary request, which refreshes and persists as usual. That refresh reuses a token the action already rotated, which GoTrue accepts inside `refresh_token_reuse_interval` (10 seconds on this project, read from the running container). **Driven, and the first version of this measurement did not cover the case that matters** (found by the fresh model review on 2026-09-05): three applies about six seconds apart all sit INSIDE the reuse interval, and a pause before an ordinary navigation proves nothing about a second action, because the navigation persists a fresh cookie anyway. The shape that actually tests it is two applies **sixteen seconds apart with no request of any kind between them**. Driven: both applies succeeded, both rows landed, no message on either, and the navigation after returned 200 still signed in with a freshly rotated cookie. The token family was not revoked. Amends spec [0008](../0008-app-shell-and-navigation/index.md) AC-10 and spec [0001](../0001-stack-and-architecture/index.md) binding rule 6, both dated the same day.
  - phrase: What actually makes AC-10 hold for an expired session is **AC-20a**.
  - source text:
    > - **AC-20**: The apply action builds its Supabase client with a **read only cookie adapter**, so nothing inside it can write a session cookie. A cookie write inside a Server Action puts a re-render of the current route into the action's response, which on `/search` means a second Adzuna call. **This criterion is defence in depth, and it is NOT what makes AC-10 hold for an expired session** (corrected 2026-09-05, revision 4; the original wording said it was). Measured: with the adapter in place and unchanged, an expired session apply still spent a call, because the write came from `src/proxy.ts`, which runs on the action `POST` too. The adapter closes a door this bug never used, and it stays closed because a later session adding a cookie write inside the action would reopen it. What actually makes AC-10 hold for an expired session is **AC-20a**.
- [x] agree · unclassified · written by 2 of 3 runs

  - source: `0014/AC-1` AcceptanceCriterion: **AC-1**: A result card carries a `Mark as applied` control that is separate from feature 11's `View the posting` link. Opening a posting records nothing at all: no row is written by the click through, and no state changes.
  - target: reference `feature 11` (whole record), mention: feature 11's `View the posting` link
  - phrase: feature 11's `View the posting` link
  - source text:
    > - **AC-1**: A result card carries a `Mark as applied` control that is separate from feature 11's `View the posting` link. Opening a posting records nothing at all: no row is written by the click through, and no state changes.

### Dropped links (befores wrote, no after wrote)

14 distinct links appear in at least one `0002.3` before run and in none of the `0003.1` afters. 14 drawn at random, seed `20260928`.

- [ ] real link lost / rightly dropped · corrected-by · written by 1 of 3 runs
  - source: `0014/AC-21` AcceptanceCriterion: An apply attempted against a stale build fails visibly, carrying `COPY-7`. The encryption key protecting the bound listing is regenerated on every build, so any results page left open across a deploy has an apply control the framework refuses. The refusal happens before any of this feature's server code runs, so it is caught in the client control around the call, never in `recordApplication`. It costs the reader nothing. An earlier draft recorded a refused dispatch re-rendering `/search` and spending one of the 25 weekly Adzuna calls. That came from a hand built `POST`, the no JavaScript shape, and it does not carry over: driven from a real browser against a genuinely stale build, the dispatch answers `404`, runs none of this feature's code, and moves no `job_search` counter. So `COPY-7` is politeness about a dead button, which is reason enough to keep it, and not compensation for a stolen call.
  - target: reference `0014` label `Consequences`, mention: see ## Consequences
  - source text:
    > - **AC-21**: An apply attempted against a stale build fails visibly, carrying `COPY-7`. The encryption key protecting the bound listing is regenerated on every build, so any results page left open across a deploy has an apply control the framework refuses. **The refusal happens before any of this feature's server code runs, so it is caught in the client control around the call, never in `recordApplication`** (corrected 2026-09-05, see `## Consequences`). **It costs the reader nothing** (settled 2026-09-05, revision 4). An earlier draft recorded a refused dispatch re-rendering `/search` and spending one of the 25 weekly Adzuna calls. That came from a hand built `POST`, the no JavaScript shape, and it does not carry over: driven from a real browser against a genuinely stale build, the dispatch answers `404`, runs none of this feature's code, and moves no `job_search` counter. So `COPY-7` is politeness about a dead button, which is reason enough to keep it, and not compensation for a stolen call.
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0014/AC-12` AcceptanceCriterion: `job_description` holds the Adzuna description snippet the search already parsed, and the spec that describes that column as the full posting text is corrected in every place it says so.
  - target: reference `None` (whole record), mention: the spec that describes that column as the full posting text
  - phrase: is corrected in every place it says so
  - source text:
    > - **AC-12**: `job_description` holds the Adzuna description snippet the search already parsed, and the spec that describes that column as the full posting text is corrected in every place it says so.
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0014/AC-18` AcceptanceCriterion: `/applications` lists rows newest applied first by `applied_at`, and shows for each the full stored snapshot: title, company, location, salary, description snippet, posted date, applied date, and the link out to the posting carrying `COPY-6`. `applied_at` renders as an absolute date and `posted_at` reuses feature 11's relative formatter,
  - target: reference `0011` (whole record), mention: feature 11's relative formatter
  - phrase: feature 11's relative formatter
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-18**: `/applications` lists rows newest applied first by `applied_at`, and shows for each the full stored snapshot: title, company, location, salary, description snippet, posted date, applied date, and the link out to the posting carrying `COPY-6`. `applied_at` renders as an absolute date and `posted_at` reuses feature 11's relative formatter, because a relative applied date is the one that ages into uselessness on an archive.
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0014/AC-1` AcceptanceCriterion: A result card carries a `Mark as applied` control that is separate from feature 11's `View the posting` link. Opening a posting records nothing at all: no row is written by the click through, and no state changes.
  - target: reference `0011` (whole record), mention: feature 11's `View the posting` link
  - phrase: feature 11's `View the posting` link
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-1**: A result card carries a `Mark as applied` control that is separate from feature 11's `View the posting` link. Opening a posting records nothing at all: no row is written by the click through, and no state changes.
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0014/AC-14` AcceptanceCriterion: The four operations this feature adds each open a named span as their first statement, at the moment the operation is first written rather than in a later pass, and are registered in [spans.md](../../observability/spans.md) with `op: "db.query"`: `application.record`, `application.remove`, `application.read_list`, and `search.read_applied`.
  - target: reference `observability/spans.md` (whole record), mention: registered in [spans.md](../../observability/spans.md)
  - phrase: registered in [spans.md](../../observability/spans.md)
  - source text:
    > - **AC-14**: The four operations this feature adds each open a named span as their first statement, at the moment the operation is first written rather than in a later pass, and are registered in [spans.md](../../observability/spans.md) with `op: "db.query"`: `application.record`, `application.remove`, `application.read_list`, and `search.read_applied`.
- [ ] real link lost / rightly dropped · corrected-by · written by 2 of 3 runs
  - source: reference `None` (whole record), mention: the spec that describes that column as the full posting text
  - target: `0014/AC-12` AcceptanceCriterion: `job_description` holds the Adzuna description snippet the search already parsed, and the spec that describes that column as the full posting text is corrected in every place it says so.
  - phrase: the spec that describes that column as the full posting text is corrected in every place it says so
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-12**: `job_description` holds the Adzuna description snippet the search already parsed, and the spec that describes that column as the full posting text is corrected in every place it says so.
- [ ] real link lost / rightly dropped · corrected-by · written by 1 of 3 runs
  - source: `0014/AC-21` AcceptanceCriterion: An apply attempted against a stale build fails visibly, carrying `COPY-7`. The encryption key protecting the bound listing is regenerated on every build, so any results page left open across a deploy has an apply control the framework refuses. The refusal happens before any of this feature's server code runs, so it is caught in the client control around the call, never in `recordApplication` (corrected 2026-09-05, see `## Consequences`). It costs the reader nothing (settled 2026-09-05, revision 4). An earlier draft recorded a refused dispatch re-rendering `/search` and spending one of the 25 weekly Adzuna calls. That came from a hand built `POST`, the no JavaScript shape, and it does not carry over: driven from a real browser against a genuinely stale build, the dispatch answers `404`, runs none of this feature's code, and moves no `job_search` counter.
  - target: reference `0014` (whole record), mention: corrected 2026-09-05, see `## Consequences`
  - phrase: (corrected 2026-09-05, see `## Consequences`)
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-21**: An apply attempted against a stale build fails visibly, carrying `COPY-7`. The encryption key protecting the bound listing is regenerated on every build, so any results page left open across a deploy has an apply control the framework refuses. **The refusal happens before any of this feature's server code runs, so it is caught in the client control around the call, never in `recordApplication`** (corrected 2026-09-05, see `## Consequences`). **It costs the reader nothing** (settled 2026-09-05, revision 4). An earlier draft recorded a refused dispatch re-rendering `/search` and spending one of the 25 weekly Adzuna calls. That came from a hand built `POST`, the no JavaScript shape, and it does not carry over: driven from a real browser against a genuinely stale build, the dispatch answers `404`, runs none of this feature's code, and moves no `job_search` counter. So `COPY-7` is politeness about a dead button, which is reason enough to keep it, and not compensation for a stolen call.
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0014/AC-13` AcceptanceCriterion: `Listing` refuses an empty or whitespace only `sourceJobId`, `title` or `companyName`. Such an item is dropped by feature 11's existing per item parse as an ordinary bad row, so it never reaches the results list and never reaches an insert that the table's check constraints would refuse.
  - target: reference `0011` (whole record), mention: feature 11's existing per item parse
  - phrase: feature 11's existing per item parse
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-13**: `Listing` refuses an empty or whitespace only `sourceJobId`, `title` or `companyName`. Such an item is dropped by feature 11's existing per item parse as an ordinary bad row, so it never reaches the results list and never reaches an insert that the table's check constraints would refuse.
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `0014/AC-4` AcceptanceCriterion: A second apply to the same `(profile_id, source, source_job_id)` writes no second row and produces a visible expected failure carrying `COPY-2`, kind `validation_failed`, severity `expected`. The refusal comes from the unique constraint.
  - target: reference `0003` AC-7, mention: spec 0003, AC-7
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-4**: A second apply to the same `(profile_id, source, source_job_id)` writes no second row and produces a visible expected failure carrying `COPY-2`, kind `validation_failed`, severity `expected`. The refusal comes from the unique constraint, so it holds for a caller that never checked first (spec 0003, AC-7).
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `0014/AC-5` AcceptanceCriterion: An apply by a caller with no `profile` row writes nothing and produces a visible expected failure carrying `COPY-3`, kind `record_not_found`, severity `expected`, which names the profile as the thing needed first and links to `/profile`. The refusal comes from the foreign key (spec 0003, AC-8), and a raw database error never reaches the reader.
  - target: reference `0003` AC-8, mention: spec 0003, AC-8
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-5**: An apply by a caller with no `profile` row writes nothing and produces a visible expected failure carrying `COPY-3`, kind `record_not_found`, severity `expected`, which names the profile as the thing needed first and links to `/profile`. The refusal comes from the foreign key (spec 0003, AC-8), and a raw database error never reaches the reader.
- [ ] real link lost / rightly dropped · amended-by · written by 1 of 3 runs
  - source: `0014/AC-20a` AcceptanceCriterion: `src/proxy.ts` withholds the refreshed session cookie from the response of a Server Action request, while still handing the refreshed value to that request's own code through `request.cookies.set()`. The branch keys on the presence of Next's `next-action` request header, never on the route: the proxy still cannot tell a protected path from a public one. This is the criterion the 25 weekly Adzuna calls actually rest on. The trade is deliberate: the browser keeps its stale cookie until its next ordinary request, which refreshes and persists as usual. That refresh reuses a token the action already rotated, which GoTrue accepts inside `refresh_token_reuse_interval` (10 seconds on this project, read from the running container). Driven, and the first version of this measurement did not cover the case that matters (found by the fresh model review on 2026-09-05): three applies about six seconds apart all sit INSIDE the reuse interval, and a pause before an ordinary navigation proves nothing about a second action. The shape that actually tests it is two applies sixteen seconds apart with no request of any kind between them. Driven: both applies succeeded, both rows landed, no message on either, and the navigation after returned 200 still signed in with a freshly rotated cookie. The token family was not revoked. Amends spec 0008 AC-10 and spec 0001 binding rule 6, both dated the same day.
  - target: reference `0001` label `binding rule 6`, mention: spec 0001 binding rule 6
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-20a**: `src/proxy.ts` **withholds the refreshed session cookie from the response of a Server Action request**, while still handing the refreshed value to that request's own code through `request.cookies.set()`, so `recordApplication` can verify its caller. The branch keys on the presence of Next's `next-action` request header, never on the route, so binding rule 6's mechanical guard is untouched: the proxy still cannot tell a protected path from a public one. This is the criterion the 25 weekly Adzuna calls actually rest on. **The trade is deliberate**: the browser keeps its stale cookie until its next ordinary request, which refreshes and persists as usual. That refresh reuses a token the action already rotated, which GoTrue accepts inside `refresh_token_reuse_interval` (10 seconds on this project, read from the running container). **Driven, and the first version of this measurement did not cover the case that matters** (found by the fresh model review on 2026-09-05): three applies about six seconds apart all sit INSIDE the reuse interval, and a pause before an ordinary navigation proves nothing about a second action, because the navigation persists a fresh cookie anyway. The shape that actually tests it is two applies **sixteen seconds apart with no request of any kind between them**. Driven: both applies succeeded, both rows landed, no message on either, and the navigation after returned 200 still signed in with a freshly rotated cookie. The token family was not revoked. Amends spec [0008](../0008-app-shell-and-navigation/index.md) AC-10 and spec [0001](../0001-stack-and-architecture/index.md) binding rule 6, both dated the same day.
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0014/AC-14` AcceptanceCriterion: The four operations this feature adds each open a named span as their first statement, at the moment the operation is first written rather than in a later pass, and are registered in spans.md with `op: "db.query"`: `application.record`, `application.remove`, `application.read_list`, and `search.read_applied`.
  - target: reference `spans.md` (whole record), mention: registered in spans.md
  - phrase: registered in
  - source text:
    > - **AC-14**: The four operations this feature adds each open a named span as their first statement, at the moment the operation is first written rather than in a later pass, and are registered in [spans.md](../../observability/spans.md) with `op: "db.query"`: `application.record`, `application.remove`, `application.read_list`, and `search.read_applied`.
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0014/AC-21` AcceptanceCriterion: An apply attempted against a stale build fails visibly, carrying `COPY-7`. The encryption key protecting the bound listing is regenerated on every build. **The refusal happens before any of this feature's server code runs** (corrected 2026-09-05, see `## Consequences`). **It costs the reader nothing** (settled 2026-09-05, revision 4). An earlier draft recorded a refused dispatch re-rendering `/search` and spending one of the 25 weekly Adzuna calls. That came from a hand built `POST`, the no JavaScript shape, and it does not carry over: driven from a real browser against a genuinely stale build, the dispatch answers `404`, runs none of this feature's code, and moves no `job_search` counter.
  - target: reference `0014` (whole record), mention: see `## Consequences`
  - phrase: corrected 2026-09-05, see `## Consequences`
  - source text:
    > - **AC-21**: An apply attempted against a stale build fails visibly, carrying `COPY-7`. The encryption key protecting the bound listing is regenerated on every build, so any results page left open across a deploy has an apply control the framework refuses. **The refusal happens before any of this feature's server code runs, so it is caught in the client control around the call, never in `recordApplication`** (corrected 2026-09-05, see `## Consequences`). **It costs the reader nothing** (settled 2026-09-05, revision 4). An earlier draft recorded a refused dispatch re-rendering `/search` and spending one of the 25 weekly Adzuna calls. That came from a hand built `POST`, the no JavaScript shape, and it does not carry over: driven from a real browser against a genuinely stale build, the dispatch answers `404`, runs none of this feature's code, and moves no `job_search` counter. So `COPY-7` is politeness about a dead button, which is reason enough to keep it, and not compensation for a stolen call.
- [ ] real link lost / rightly dropped · amended-by · written by 1 of 3 runs
  - source: `0014/AC-20a` AcceptanceCriterion: `src/proxy.ts` withholds the refreshed session cookie from the response of a Server Action request, while still handing the refreshed value to that request's own code through `request.cookies.set()`. The branch keys on the presence of Next's `next-action` request header, never on the route: the proxy still cannot tell a protected path from a public one. This is the criterion the 25 weekly Adzuna calls actually rest on. The trade is deliberate: the browser keeps its stale cookie until its next ordinary request, which refreshes and persists as usual. That refresh reuses a token the action already rotated, which GoTrue accepts inside `refresh_token_reuse_interval` (10 seconds on this project, read from the running container). Driven, and the first version of this measurement did not cover the case that matters (found by the fresh model review on 2026-09-05): three applies about six seconds apart all sit INSIDE the reuse interval, and a pause before an ordinary navigation proves nothing about a second action. The shape that actually tests it is two applies sixteen seconds apart with no request of any kind between them. Driven: both applies succeeded, both rows landed, no message on either, and the navigation after returned 200 still signed in with a freshly rotated cookie. The token family was not revoked. Amends spec 0008 AC-10 and spec 0001 binding rule 6, both dated the same day.
  - target: reference `0008` AC-10, mention: spec 0008 AC-10
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-20a**: `src/proxy.ts` **withholds the refreshed session cookie from the response of a Server Action request**, while still handing the refreshed value to that request's own code through `request.cookies.set()`, so `recordApplication` can verify its caller. The branch keys on the presence of Next's `next-action` request header, never on the route, so binding rule 6's mechanical guard is untouched: the proxy still cannot tell a protected path from a public one. This is the criterion the 25 weekly Adzuna calls actually rest on. **The trade is deliberate**: the browser keeps its stale cookie until its next ordinary request, which refreshes and persists as usual. That refresh reuses a token the action already rotated, which GoTrue accepts inside `refresh_token_reuse_interval` (10 seconds on this project, read from the running container). **Driven, and the first version of this measurement did not cover the case that matters** (found by the fresh model review on 2026-09-05): three applies about six seconds apart all sit INSIDE the reuse interval, and a pause before an ordinary navigation proves nothing about a second action, because the navigation persists a fresh cookie anyway. The shape that actually tests it is two applies **sixteen seconds apart with no request of any kind between them**. Driven: both applies succeeded, both rows landed, no message on either, and the navigation after returned 200 still signed in with a freshly rotated cookie. The token family was not revoked. Amends spec [0008](../0008-app-shell-and-navigation/index.md) AC-10 and spec [0001](../0001-stack-and-architecture/index.md) binding rule 6, both dated the same day.

## 0015 / feature-design (Feature design, no prior worked example of this record)

### Entities

10 evenly spaced through after run 1's located order.

- [x] disagree · `0015#feature-design:1` · Constraint
  - reason: should split: "no new database table" and "a score is never persisted / computed for one render" are independently statable (no "so" ties them, unlike 0013); no verbatim id, so the splitting rule applies

  - span: **Data model sketch**: No new database table. A score is never persisted (see Consequences); it is an in memory value computed for one render and handed straight to the UI.
  - flags: multi_condition_split
- [x] agree · `0015#feature-design:4` · Constraint

  - span: `notMentionedSkills` never renders under any label implying confirmed absence.
- [x] disagree · `0015#feature-design:8` · Constraint
  - reason: should split: "never runs for an empty profile" and "the gate is checked once, not per listing" fail independently; no verbatim id, so the splitting rule applies

  - span: Scoring never runs at all when the caller has zero skills and zero work experience entries (AC-7); the gate is checked once before the first `ai_scoring` call, not per listing.
  - flags: multi_condition_split
- [x] agree · `0015#feature-design:11` · Constraint
  - reason: one complete rule on its own; the bullet's other two parts only restate cases it already forbids (not sampled, noted only)

  - span: The page never moves a reader's focus except to give back focus it just took away.
  - flags: multi_condition_split
- [x] disagree · `0015#feature-design:15` · Constraint
  - reason: bad cut: split at "and", it loses its subject ("a batch that ranks nothing") and reads as a broader rule than the text states; spans are verbatim, so it should stay joined to "a batch that ranks nothing announces nothing (AC-16)", with "The second is about the DOM being replaced..." in rejected as the reason

  - span: and, having reordered nothing, still restores focus if the reveal orphaned it (AC-17).
  - flags: multi_condition_split
- [x] disagree · `0015#feature-design:18` · Constraint
  - reason: should split: "the session check is inherited via callTier() → checkUsageGate() → getClaims()" (a rule about how it is built) and "scoring never runs for a signed out caller" (the outcome) fail independently; no verbatim id, so the splitting rule applies

  - span: Session: inherited from `callTier()`'s own `checkUsageGate()` → `getClaims()` check. Scoring never runs for a signed out caller.
  - flags: multi_condition_split
- [x] disagree · `0015#feature-design:22` · Constraint
  - reason: wrong type: an accepted limitation of the mitigation (instruction level defense, not a sandbox), not a rule; should be Consequence

  - span: This is instruction level defense, not a sandbox, the same limit the verified reference project accepts.
  - flags: multi_condition_split
- [x] disagree · `0015#feature-design:25` · Constraint
  - reason: not a rule: reports current state (the entry already exists, so this feature needs no registry change); no criterion or invariant requires it. Should be Consequence, as the spec files the same kind of fact under Consequences, Positive (line 176)

  - span: The `DATA_RECIPIENTS` entry for `openai` already exists (spec 0012, AC-9), so no registry change is needed here.
  - flags: multi_condition_split
- [x] disagree · `0015#feature-design:29` · Constraint
  - reason: should split: "none new" and "reuses OPENAI_API_KEY, already declared and validated by spec 0012" are two claims (no verbatim id); "none new" is a report filling the template's configuration field, not a rule (same fact at lines 121 and 176, the latter under Consequences, Positive)

  - span: **Configuration required**: none new. This feature reuses `OPENAI_API_KEY`, already declared and validated by spec 0012.
  - flags: multi_condition_split
- [x] disagree · `0015#feature-design:32` · TestScenario · label `Failure case, vendor error`
  - reason: one test, correctly cut and typed, but no label: "Failure case" is the category (shared with "Failure case, refusal") and "vendor error" names which kind of failure is tested; a category plus its kind is not the test's own name
`
  - span: Failure case, vendor error: a constructed vendor error classified by the router's own `classify()` surfaces as `external_service_failed`, and the affected card alone shows the "could not be scored" state while a sibling card with a successful outcome still renders its band, verifies **AC-10**.

### Relationships

5 evenly spaced through the 31 distinct links the three after runs wrote.

- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0015#feature-design:2` Constraint: **State transitions**: none. Scoring is stateless per render, matching spec 0012's own router.
  - target: reference `0012` (whole record), mention: spec 0012's own router
  - phrase: matching spec 0012's own router
  - source text:
    > **State transitions**: none. Scoring is stateless per render, matching spec 0012's own router.
- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0015#feature-design:7` Constraint: A gate refusal (`{ allowed: false }`) and a vendor failure are never rendered the same way, extending spec 0012's own key invariant (refusal and failure are never the same shape) to the per card versus page level split AC-10 and AC-11 add.
  - target: reference `0015` AC-11, mention: AC-11
  - phrase: the per card versus page level split AC-10 and AC-11 add
  - source text:
    > - A gate refusal (`{ allowed: false }`) and a vendor failure are never rendered the same way, extending spec 0012's own key invariant (refusal and failure are never the same shape) to the per card versus page level split AC-10 and AC-11 add.
- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0015#feature-design:14` Constraint: The re-rank announcement and the focus restoration are two answers to the same event and must stay consistent: a batch that ranks nothing announces nothing (AC-16)
  - target: reference `0015` AC-16, mention: AC-16
  - phrase: (AC-16)
  - source text:
    > - The re-rank announcement and the focus restoration are two answers to the same event and must stay consistent: a batch that ranks nothing announces nothing (AC-16) and, having reordered nothing, still restores focus if the reveal orphaned it (AC-17). The second is about the DOM being replaced, which happens on every reveal, not about whether the order changed.
- [x] agree · unclassified · written by 3 of 3 runs

  - source: `0015#feature-design:25` Constraint: The `DATA_RECIPIENTS` entry for `openai` already exists (spec 0012, AC-9), so no registry change is needed here.
  - target: reference `0012` AC-9, mention: spec 0012, AC-9
  - phrase: (spec 0012, AC-9)
  - source text:
    > - Privacy: this is the first feature that actually sends a real user's own summary, skills, and work history to `ai_scoring` in production. The `DATA_RECIPIENTS` entry for `openai` already exists (spec 0012, AC-9), so no registry change is needed here, but the diligence scope.md already owes this feature, reading OpenAI's terms on training and retention before this ships against real data, is carried forward in Follow-up.
- [x] agree · verifies · written by 3 of 3 runs
  - reason: the text states "verifies AC-8, AC-11" and the link carries it; JobHunt: the scenario covers AC-11's central behaviour only (not the mixed batch or tie-break), a gap in the spec's own claim, not an extraction error

  - source: `0015#feature-design:31` TestScenario: Failure case, refusal: a `usage_cap` row zeroed for `ai_scoring` in a test causes every `scoreListing()` call to return `{ allowed: false, reason }` without reaching the vendor, and the page renders the single page level notice from AC-11, never a per card failure note, verifies **AC-8**, **AC-11**.
  - target: reference `0015` AC-11, mention: **AC-11**
  - phrase: verifies **AC-8**, **AC-11**
  - source text:
    > - Failure case, refusal: a `usage_cap` row zeroed for `ai_scoring` in a test causes every `scoreListing()` call to return `{ allowed: false, reason }` without reaching the vendor, and the page renders the single page level notice from AC-11, never a per card failure note, verifies **AC-8**, **AC-11**.

### Dropped links (befores wrote, no after wrote)

30 distinct links appear in at least one `0002.3` before run and in none of the `0003.1` afters. 15 drawn at random, seed `20260928`.

- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0015#feature-design:18` Feature: `scoreListing()` (`src/features/scoring/score.ts`) is a server function taking `profile: ScoringProfile` (the bounded shape from AC-13) and `listing: Listing`, returning `Result<{ allowed: true; value: FitScore } | { allowed: false; reason: UsageGateReason }>`, with auth inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached
  - target: reference `0012` (whole record), mention: inherited from `callTier()`
  - phrase: inherited from `callTier()`
  - flags: relationship_type_ambiguous
  - source text:
    > **API surface**:
    > | Function | Kind | Key inputs | Key outputs | Auth | Key errors |
    > |---|---|---|---|---|---|
    > | `scoreListing()` (`src/features/scoring/score.ts`) | server function | `profile: ScoringProfile` (the bounded shape from AC-13), `listing: Listing` | `Result<{ allowed: true; value: FitScore } \| { allowed: false; reason: UsageGateReason }>` | inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached | `session_missing`, `usage_gate_misconfigured`, `database_unavailable` (from the gate), `external_service_failed`, `response_malformed` (from the vendor call), all inherited unchanged from spec 0012 |
    > | `scoreListings()` (`src/features/scoring/score-listings.ts`) | server function | `profile: ScoringProfile`, `listings: readonly Listing[]` | `readonly ScoreOutcome[]`, one per listing, order preserved, each element is `scoreListing()`'s own `Result` | same as `scoreListing()`, per call | none of its own; each element carries its own `scoreListing()` outcome |
    > | `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) | client components, one module | `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it; `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened | nothing rendered; the only effect is a `.focus()` call, and only under AC-17's four rules | none of its own; it reads no user data and calls no server function | none; a missing key falls back per AC-17 rather than failing |
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:6` Constraint: Scoring never runs at all when the caller has zero skills and zero work experience entries
  - target: reference `0015` AC-7, mention: AC-7
  - source text:
    > - Scoring never runs at all when the caller has zero skills and zero work experience entries (AC-7); the gate is checked once before the first `ai_scoring` call, not per listing.
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:25` Feature: scoreListing() (src/features/scoring/score.ts): a server function taking profile: ScoringProfile and listing: Listing, returning Result<{ allowed: true; value: FitScore } | { allowed: false; reason: UsageGateReason }>, with auth inherited from callTier(), which verifies the caller through checkUsageGate()'s getClaims() before any vendor is reached
  - target: reference `None` AC-13, mention: the bounded shape from AC-13
  - source text:
    > **API surface**:
    > | Function | Kind | Key inputs | Key outputs | Auth | Key errors |
    > |---|---|---|---|---|---|
    > | `scoreListing()` (`src/features/scoring/score.ts`) | server function | `profile: ScoringProfile` (the bounded shape from AC-13), `listing: Listing` | `Result<{ allowed: true; value: FitScore } \| { allowed: false; reason: UsageGateReason }>` | inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached | `session_missing`, `usage_gate_misconfigured`, `database_unavailable` (from the gate), `external_service_failed`, `response_malformed` (from the vendor call), all inherited unchanged from spec 0012 |
    > | `scoreListings()` (`src/features/scoring/score-listings.ts`) | server function | `profile: ScoringProfile`, `listings: readonly Listing[]` | `readonly ScoreOutcome[]`, one per listing, order preserved, each element is `scoreListing()`'s own `Result` | same as `scoreListing()`, per call | none of its own; each element carries its own `scoreListing()` outcome |
    > | `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) | client components, one module | `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it; `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened | nothing rendered; the only effect is a `.focus()` call, and only under AC-17's four rules | none of its own; it reads no user data and calls no server function | none; a missing key falls back per AC-17 rather than failing |
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:27` Feature: FocusRecorder / FocusRestorer (src/features/search/focus-keeper.tsx): client components in one module; FocusRecorder is rendered outside the Suspense boundary so the reveal never unmounts it, and FocusRestorer is rendered inside the resolved content so mounting it is the signal that the reveal happened; nothing is rendered, the only effect is a .focus() call
  - target: reference `None` AC-17, mention: AC-17's four rules
  - source text:
    > **API surface**:
    > | Function | Kind | Key inputs | Key outputs | Auth | Key errors |
    > |---|---|---|---|---|---|
    > | `scoreListing()` (`src/features/scoring/score.ts`) | server function | `profile: ScoringProfile` (the bounded shape from AC-13), `listing: Listing` | `Result<{ allowed: true; value: FitScore } \| { allowed: false; reason: UsageGateReason }>` | inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached | `session_missing`, `usage_gate_misconfigured`, `database_unavailable` (from the gate), `external_service_failed`, `response_malformed` (from the vendor call), all inherited unchanged from spec 0012 |
    > | `scoreListings()` (`src/features/scoring/score-listings.ts`) | server function | `profile: ScoringProfile`, `listings: readonly Listing[]` | `readonly ScoreOutcome[]`, one per listing, order preserved, each element is `scoreListing()`'s own `Result` | same as `scoreListing()`, per call | none of its own; each element carries its own `scoreListing()` outcome |
    > | `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) | client components, one module | `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it; `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened | nothing rendered; the only effect is a `.focus()` call, and only under AC-17's four rules | none of its own; it reads no user data and calls no server function | none; a missing key falls back per AC-17 rather than failing |
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:5` Constraint: A gate refusal ({ allowed: false }) and a vendor failure are never rendered the same way.
  - target: reference `None` AC-10, mention: AC-10
  - flags: relationship_type_ambiguous
  - source text:
    > - A gate refusal (`{ allowed: false }`) and a vendor failure are never rendered the same way, extending spec 0012's own key invariant (refusal and failure are never the same shape) to the per card versus page level split AC-10 and AC-11 add.
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0015#feature-design:17` Constraint: Retention: ai_scoring sets providerOptions: { openai: { store: false } } (src/lib/ai/tiers.ts), opting out of the Responses API's default 30 day retention of the full request and response.
  - target: reference `0015` (whole record), mention: (Follow-up, first item)
  - phrase: Decided and recorded 2026-09-06
  - flags: relationship_type_ambiguous
  - source text:
    > - Retention: `ai_scoring` sets `providerOptions: { openai: { store: false } }` (`src/lib/ai/tiers.ts`), opting out of the Responses API's default 30 day retention of the full request and response. Nothing is lost by it, because scoring is stateless per render and never references a prior response by id, so the retention the default buys has no caller here. Decided and recorded 2026-09-06 (Follow-up, first item).
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:9` Constraint: The re-rank announcement and the focus restoration are two answers to the same event and must stay consistent: a batch that ranks nothing announces nothing and, having reordered nothing, still restores focus if the reveal orphaned it. The second is about the DOM being replaced, which happens on every reveal, not about whether the order changed.
  - target: reference `None` AC-17, mention: (AC-17)
  - source text:
    > - The re-rank announcement and the focus restoration are two answers to the same event and must stay consistent: a batch that ranks nothing announces nothing (AC-16) and, having reordered nothing, still restores focus if the reveal orphaned it (AC-17). The second is about the DOM being replaced, which happens on every reveal, not about whether the order changed.
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `0015#feature-design:21` TestScenario: Failure case, vendor error: a constructed vendor error classified by the router's own classify() surfaces as external_service_failed, and the affected card alone shows the "could not be scored" state while a sibling card with a successful outcome still renders its band.
  - target: reference `None` AC-10, mention: AC-10
  - source text:
    > - Failure case, vendor error: a constructed vendor error classified by the router's own `classify()` surfaces as `external_service_failed`, and the affected card alone shows the "could not be scored" state while a sibling card with a successful outcome still renders its band, verifies **AC-10**.
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:8` Constraint: The page never moves a reader's focus except to give back focus it just took away. Restoration runs only when the reveal orphaned the active element; it is never a "focus the results" convenience, and it never fires on a render that had no pending state to begin with (the thin profile gate, an unscored list, the empty state).
  - target: reference `None` AC-17, mention: (AC-17)
  - source text:
    > - The page never moves a reader's focus except to give back focus it just took away. Restoration runs only when the reveal orphaned the active element (AC-17); it is never a "focus the results" convenience, and it never fires on a render that had no pending state to begin with (the thin profile gate, an unscored list, the empty state).
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0015#feature-design:11` Consequence: `ai_scoring` sets `providerOptions: { openai: { store: false } }` (`src/lib/ai/tiers.ts`), opting out of the Responses API's default 30 day retention of the full request and response.
  - target: reference `0015` label `Follow-up first item`, mention: (Follow-up, first item)
  - phrase: Decided and recorded 2026-09-06 (Follow-up, first item).
  - flags: relationship_type_ambiguous
  - source text:
    > - Retention: `ai_scoring` sets `providerOptions: { openai: { store: false } }` (`src/lib/ai/tiers.ts`), opting out of the Responses API's default 30 day retention of the full request and response. Nothing is lost by it, because scoring is stateless per render and never references a prior response by id, so the retention the default buys has no caller here. Decided and recorded 2026-09-06 (Follow-up, first item).
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0015#feature-design:20` Feature: `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) are client components in one module; `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it, and `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened; nothing is rendered and the only effect is a `.focus()` call, only under AC-17's four rules
  - target: reference `0015` AC-17, mention: under AC-17's four rules
  - phrase: under AC-17's four rules
  - source text:
    > **API surface**:
    > | Function | Kind | Key inputs | Key outputs | Auth | Key errors |
    > |---|---|---|---|---|---|
    > | `scoreListing()` (`src/features/scoring/score.ts`) | server function | `profile: ScoringProfile` (the bounded shape from AC-13), `listing: Listing` | `Result<{ allowed: true; value: FitScore } \| { allowed: false; reason: UsageGateReason }>` | inherited from `callTier()`, which verifies the caller through `checkUsageGate()`'s `getClaims()` before any vendor is reached | `session_missing`, `usage_gate_misconfigured`, `database_unavailable` (from the gate), `external_service_failed`, `response_malformed` (from the vendor call), all inherited unchanged from spec 0012 |
    > | `scoreListings()` (`src/features/scoring/score-listings.ts`) | server function | `profile: ScoringProfile`, `listings: readonly Listing[]` | `readonly ScoreOutcome[]`, one per listing, order preserved, each element is `scoreListing()`'s own `Result` | same as `scoreListing()`, per call | none of its own; each element carries its own `scoreListing()` outcome |
    > | `FocusRecorder` / `FocusRestorer` (`src/features/search/focus-keeper.tsx`) | client components, one module | `FocusRecorder` takes nothing and is rendered OUTSIDE the Suspense boundary so the reveal never unmounts it; `FocusRestorer` takes nothing and is rendered INSIDE the resolved content so mounting it IS the signal that the reveal happened | nothing rendered; the only effect is a `.focus()` call, and only under AC-17's four rules | none of its own; it reads no user data and calls no server function | none; a missing key falls back per AC-17 rather than failing |
- [ ] real link lost / rightly dropped · satisfies · written by 1 of 3 runs
  - source: `0015#feature-design:2` Constraint: No call ever scores more than one listing
  - target: reference `0015` AC-3, mention: AC-3
  - source text:
    > - No call ever scores more than one listing (mirrors spec 0012's settled call shape, AC-3).
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `0015#feature-design:22` TestScenario: Thin profile: a profile with zero skill rows and zero work experience rows performs zero ai_scoring calls for a search that returns listings, and the page renders the unscored list plus the link to /profile; a profile with one skill and no work history, or one work history entry and no skills, scores normally.
  - target: reference `None` AC-7, mention: AC-7
  - source text:
    > - Thin profile: a profile with zero skill rows and zero work experience rows performs zero `ai_scoring` calls for a search that returns listings, and the page renders the unscored list plus the link to `/profile`; a profile with one skill and no work history, or one work history entry and no skills, scores normally, verifies **AC-7**.
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `0015#feature-design:23` TestScenario: Truncation handling: building the prompt for a fixture listing whose descriptionSnippet ends in "…" includes the explicit truncation caveat from AC-4; this is a unit test on the prompt builder itself, needing no live call.
  - target: reference `None` AC-4, mention: AC-4
  - source text:
    > - Truncation handling: building the prompt for a fixture listing whose `descriptionSnippet` ends in "…" includes the explicit truncation caveat from AC-4; this is a unit test on the prompt builder itself, needing no live call, verifies **AC-4**.
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0015#feature-design:4` Constraint: The band is decided by skill and experience alignment only. Stated preferences (`desired_titles`, `desired_locations`, `remote_preference`, `minimum_pay`) and the sponsorship signal are instructed to be context for the written reasoning only, never inputs the model uses to select the band itself. This is instruction level, not structurally enforced: nothing in the schema stops the model from letting a preference mismatch influence the band anyway.
  - target: reference `0015` label `Follow-up`, mention: See Follow-up
  - phrase: See Follow-up for how feature 15's ground truth set is asked to give feature 16's eval harness a real chance to catch it if it happens
  - source text:
    > - The band is decided by skill and experience alignment only. Stated preferences (`desired_titles`, `desired_locations`, `remote_preference`, `minimum_pay`) and the sponsorship signal are instructed to be context for the written reasoning only, never inputs the model uses to select the band itself. This is instruction level, not structurally enforced (the same limit AC-12's prompt injection defense accepts): nothing in the schema stops the model from letting a preference mismatch influence the band anyway. See Follow-up for how feature 15's ground truth set is asked to give feature 16's eval harness a real chance to catch it if it happens.

## feature-33 / 33-band-anchor-review-done (Scope feature row, no prior worked example of this record)

### Entities

10 evenly spaced through after run 1's located order.

- [x] disagree · `feature-33#33-band-anchor-review-done:1` · Feature
  - reason: should split: sentence 1 is the Feature (check the anchors, correct whichever side is wrong); sentence 2 is separate claims (the findings, the corrections, and "rather than changing what real users are scored against"), not an explanation of the first

  - span: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
  - flags: embedded_second_claim
- [x] agree · `feature-33#33-band-anchor-review-done:2` · AcceptanceCriterion

  - span: `control-one-gap` expects `possible_match` and passes a real run,
  - flags: multi_condition_split
- [x] agree · `feature-33#33-band-anchor-review-done:3` · AcceptanceCriterion
  - reason: a checkable done condition (a guard: diff of rubric.ts empty, hash unchanged), so AcceptanceCriterion fits

  - span: `BAND_ANCHORS` and its hash `1b45f524b356` are untouched,
  - flags: multi_condition_split
- [x] agree · `feature-33#33-band-anchor-review-done:4` · AcceptanceCriterion

  - span: the misread run evidence is corrected everywhere it was repeated,
  - flags: multi_condition_split
- [x] disagree · `feature-33#33-band-anchor-review-done:6` · BuildStep
  - reason: span and type fine, but the rejected text holds checkable facts of its own (the refused draft's two anchor rules and three grounds, "5 of 5" as a success count, the 3 to 2 split, seven gaps applied); they should be items, not rejected, as ruled for feature 9's Verify it in experiment 0005

  - span: Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do **not** change.
  - rejected: ['Cross checked twice on Fable against an Opus author. The first draft added two anchor rules and was refused on three independent grounds: it contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed), it used "a substantial share of the role" when `rubric.ts:58` says anchors are written against the visible posting and never against the role, and it falsified spec 0016\'s accepted AC-3 by removing `boundary-seniority-gap`\'s tolerance. The evidence it rested on was also wrong: the report\'s `summary` reads `"5 of 5 succeeded"` as a **success denominator**, not a band count, so `key-domain-mismatch` was a 3 to 2 split rather than stable, which is noise and not a defined gap. The second review of the narrowed spec returned sound with seven gaps, all applied']
  - flags: rationale_boundary_call
- [x] agree · `feature-33#33-band-anchor-review-done:7` · BuildStep

  - span: Build it: `/develop band anchor review`
- [x] agree · `feature-33#33-band-anchor-review-done:8` · BuildStep
  - reason: one task as the author framed it ("Correct the pair and its file's own claim:"), one continuous sentence and one checkbox; the separate AC-1 and AC-1b tags noted

  - span: Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
  - flags: multi_condition_split
- [x] disagree · `feature-33#33-band-anchor-review-done:10` · BuildStep
  - reason: type is right (a Build it sub-step that satisfies AC-2, AC-3), but the rejected text holds checkable facts (1178 tests green, rubric.ts diff empty, the deliberate guard break) that should be items, not rejected


  - span: Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3.
  - rejected: ['1178 unit tests green, `git diff main -- src/features/scoring/rubric.ts` empty. The band coverage guard was broken on purpose (pointing `good-match-adjacent` at `possible_match`) and failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", so the pass is not vacuous']
  - flags: multi_condition_split, rationale_boundary_call
- [x] disagree · `feature-33#33-band-anchor-review-done:11` · BuildStep
  - reason: type is right (it satisfies AC-5, which is the run itself), but its outcome (PASS at 03:44Z, distribution 2 to 3, five calls measured) sits in rejected and is the evidence AC-5 was met; it should be an item. The margin judgement, run history and UTC note can stay rejected

  - span: Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5.
  - rejected: ["**PASS** 2026-09-09T03:44Z, anchor hash `1b45f524b356` unchanged, exit 0. Distribution `good_match` 2, `possible_match` 3, read from the report's `distribution` field: the pair passes on the strict majority and clears spec 0017's 3 of 5 floor, but by the minimum margin, and the old `good_match` expectation has now lost on all three runs ever taken (4 to 1, 5 to 0, 3 to 2). The five calls were confirmed by measurement rather than by reading the filter output, `ai_scoring global` day 2026-09-09 from absent to 5 and month 1225 to 1230, read through `pg` directly. Note the UTC day had already rolled at 03:44Z, so the 2026-09-08 row stayed at 195 and watching that row would have shown no movement"]
  - flags: rationale_boundary_call
- [x] disagree · `feature-33#33-band-anchor-review-done:12` · unclassified
  - reason: type right (a Verify it line), but the rejected paragraph holds checkable facts of its own, three explicitly the proof of AC-2 (rubric.ts absent from the diff), AC-3 (the deliberate guard break) and AC-5 (the 03:44Z run); they should be items, not rejected

  - span: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - rejected: ['The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2\'s central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`\'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it']

### Relationships

5 evenly spaced through the 22 distinct links the three after runs wrote.

- [x] agree · unclassified · written by 3 of 3 runs
  - reason: feature 33 uses feature 16's measurements as its evidence; a reference, not a correction (what it corrects belongs mostly to feature 15), so unclassified fits

  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
  - target: reference `feature 16` (whole record), mention: feature 16's harness
  - phrase: against what feature 16's harness actually measured
  - flags: relationship_type_ambiguous
  - source text:
    > ### 33. Band anchor review · done
    > Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
    > **Done when:** `control-one-gap` expects `possible_match` and passes a real run, `BAND_ANCHORS` and its hash `1b45f524b356` are untouched, the misread run evidence is corrected everywhere it was repeated, and the set still gives every band an exact expectation.
    > _spec [0018](../specs/0018-band-anchor-review/index.md) · code in `src/features/scoring/eval/pairs.ts`_
- [x] agree · satisfies · written by 3 of 3 runs

  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
  - target: reference `0018` AC-4b, mention: AC-4b
  - phrase: satisfies AC-4, AC-4b
  - flags: relationship_type_ambiguous
  - source text:
    > - [x] Build it: `/develop band anchor review`
    >   - [x] Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
    >   - [x] Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
    >   - [x] Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3. 1178 unit tests green, `git diff main -- src/features/scoring/rubric.ts` empty. The band coverage guard was broken on purpose (pointing `good-match-adjacent` at `possible_match`) and failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", so the pass is not vacuous
    >   - [x] Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5. **PASS** 2026-09-09T03:44Z, anchor hash `1b45f524b356` unchanged, exit 0. Distribution `good_match` 2, `possible_match` 3, read from the report's `distribution` field: the pair passes on the strict majority and clears spec 0017's 3 of 5 floor, but by the minimum margin, and the old `good_match` expectation has now lost on all three runs ever taken (4 to 1, 5 to 0, 3 to 2). The five calls were confirmed by measurement rather than by reading the filter output, `ai_scoring global` day 2026-09-09 from absent to 5 and month 1225 to 1230, read through `pg` directly. Note the UTC day had already rolled at 03:44Z, so the 2026-09-08 row stayed at 195 and watching that row would have shown no movement
- [x] disagree · unclassified · written by 1 of 3 runs
  - reason: wrong ends: "it falsified spec 0016's accepted AC-3" is said of the refused first draft, which never took effect, not of the Design it step; AC-3 was a ground for refusing the draft, so no link from Design it with this phrase

  - source: `feature-33#33-band-anchor-review-done:6` BuildStep: Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do **not** change. Cross checked twice on Fable against an Opus author.
  - target: reference `0016` AC-3, mention: spec 0016's accepted AC-3
  - phrase: it falsified spec 0016's accepted AC-3 by removing `boundary-seniority-gap`'s tolerance
  - source text:
    > - [x] Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do **not** change. Cross checked twice on Fable against an Opus author. The first draft added two anchor rules and was refused on three independent grounds: it contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed), it used "a substantial share of the role" when `rubric.ts:58` says anchors are written against the visible posting and never against the role, and it falsified spec 0016's accepted AC-3 by removing `boundary-seniority-gap`'s tolerance. The evidence it rested on was also wrong: the report's `summary` reads `"5 of 5 succeeded"` as a **success denominator**, not a band count, so `key-domain-mismatch` was a 3 to 2 split rather than stable, which is noise and not a defined gap. The second review of the narrowed spec returned sound with seven gaps, all applied
- [x] agree · unclassified · written by 1 of 3 runs
  - reason: a citation: both tests trace to spec 0018

  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` (whole record), mention: spec 0018
  - phrase: both tracing to spec 0018
  - source text:
    > - [x] Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018. One pins the corrected `possible_match` expectation so a silent revert to `good_match` fails by name; the other is the general form, asserting that **no `control` tagged pair carries `acceptableBands`**, which is spec 0018's Key invariant that a tolerance is not a way to stop a pair failing, grounded in spec 0016's own reasoning for why `mild-stretch-possible-match` takes "no `acceptableBands` and the plain `control` tag rather than `boundary`". Pinning only `control-one-gap` would have left that escape open on every other control. Each was broken on purpose **after** the commit hooks ran, per the 2026-09-05 reflex, and each failed with its own message, the second naming the offending pair id. AC-1b, AC-4 and AC-4b are deliberately **not** automated: the first would be a test reading comment text, which Prettier can silently invalidate, and the other two are prose corrections in docs. All three are proved by `/check verify` instead, and AC-5 is the paid run
- [x] disagree · unclassified · written by 1 of 3 runs
  - reason: no link under the current rule: "deliberately not automated" records that AC-4b is not automated and why (a decision with its rationale); a claim of absence makes no link. Kept deliberately: a "why is AC-4b not automated" question cannot reach its answer from AC-4b; see the candidate in session notes

  - source: `feature-33#33-band-anchor-review-done:13` unclassified: Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018.
  - target: reference `0018` AC-4b, mention: AC-4b
  - phrase: AC-1b, AC-4 and AC-4b are deliberately **not** automated
  - source text:
    > - [x] Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018. One pins the corrected `possible_match` expectation so a silent revert to `good_match` fails by name; the other is the general form, asserting that **no `control` tagged pair carries `acceptableBands`**, which is spec 0018's Key invariant that a tolerance is not a way to stop a pair failing, grounded in spec 0016's own reasoning for why `mild-stretch-possible-match` takes "no `acceptableBands` and the plain `control` tag rather than `boundary`". Pinning only `control-one-gap` would have left that escape open on every other control. Each was broken on purpose **after** the commit hooks ran, per the 2026-09-05 reflex, and each failed with its own message, the second naming the offending pair id. AC-1b, AC-4 and AC-4b are deliberately **not** automated: the first would be a test reading comment text, which Prettier can silently invalidate, and the other two are prose corrections in docs. All three are proved by `/check verify` instead, and AC-5 is the paid run

### Dropped links (befores wrote, no after wrote)

16 distinct links appear in at least one `0002.3` before run and in none of the `0003.1` afters. 15 drawn at random, seed `20260928`.

- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` BuildStep: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - target: reference `0018` AC-4b, mention: AC-4b ... proved by /check verify instead
  - source text:
    > - [x] Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed. The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2's central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong.
  - target: reference `feature-16` (whole record), mention: feature 16's harness
  - phrase: against what feature 16's harness actually measured
  - flags: relationship_type_ambiguous
  - source text:
    > ### 33. Band anchor review · done
    > Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
    > **Done when:** `control-one-gap` expects `possible_match` and passes a real run, `BAND_ANCHORS` and its hash `1b45f524b356` are untouched, the misread run evidence is corrected everywhere it was repeated, and the set still gives every band an exact expectation.
    > _spec [0018](../specs/0018-band-anchor-review/index.md) · code in `src/features/scoring/eval/pairs.ts`_
- [ ] real link lost / rightly dropped · corrected-by · written by 2 of 3 runs
  - source: reference `0016` (whole record), mention: spec 0016's stale table row and its Follow up quote that reads as present tense
  - target: `feature-33#33-band-anchor-review-done:5` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense
  - source text:
    > - [x] Build it: `/develop band anchor review`
    >   - [x] Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
    >   - [x] Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
    >   - [x] Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3. 1178 unit tests green, `git diff main -- src/features/scoring/rubric.ts` empty. The band coverage guard was broken on purpose (pointing `good-match-adjacent` at `possible_match`) and failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", so the pass is not vacuous
    >   - [x] Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5. **PASS** 2026-09-09T03:44Z, anchor hash `1b45f524b356` unchanged, exit 0. Distribution `good_match` 2, `possible_match` 3, read from the report's `distribution` field: the pair passes on the strict majority and clears spec 0017's 3 of 5 floor, but by the minimum margin, and the old `good_match` expectation has now lost on all three runs ever taken (4 to 1, 5 to 0, 3 to 2). The five calls were confirmed by measurement rather than by reading the filter output, `ai_scoring global` day 2026-09-09 from absent to 5 and month 1225 to 1230, read through `pg` directly. Note the UTC day had already rolled at 03:44Z, so the 2026-09-08 row stayed at 195 and watching that row would have shown no movement
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - target: reference `0018` AC-3, mention: AC-3 was proved harder than a green suite
  - source text:
    > - [x] Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed. The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2's central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it
- [ ] real link lost / rightly dropped · verifies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` TestScenario: One pins the corrected `possible_match` expectation so a silent revert to `good_match` fails by name
  - target: reference `0018` (whole record), mention: both tracing to spec 0018
  - source text:
    > - [x] Test it: `/test band anchor review` · 2 tests added to `src/features/scoring/eval/ground-truth.test.ts`, taking it to 26, both tracing to spec 0018. One pins the corrected `possible_match` expectation so a silent revert to `good_match` fails by name; the other is the general form, asserting that **no `control` tagged pair carries `acceptableBands`**, which is spec 0018's Key invariant that a tolerance is not a way to stop a pair failing, grounded in spec 0016's own reasoning for why `mild-stretch-possible-match` takes "no `acceptableBands` and the plain `control` tag rather than `boundary`". Pinning only `control-one-gap` would have left that escape open on every other control. Each was broken on purpose **after** the commit hooks ran, per the 2026-09-05 reflex, and each failed with its own message, the second naming the offending pair id. AC-1b, AC-4 and AC-4b are deliberately **not** automated: the first would be a test reading comment text, which Prettier can silently invalidate, and the other two are prose corrections in docs. All three are proved by `/check verify` instead, and AC-5 is the paid run
- [ ] real link lost / rightly dropped · verifies · written by 3 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - target: reference `0018` (whole record), mention: all 7 acceptance criteria met
  - source text:
    > - [x] Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed. The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2's central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` BuildStep: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - target: reference `0018` AC-1b, mention: AC-1b, AC-4 and AC-4b are deliberately not automated ... All three are proved by /check verify instead
  - source text:
    > - [x] Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed. The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2's central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:9` BuildStep: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - target: reference `0018` AC-2, mention: AC-2's central claim proved by the diff
  - source text:
    > - [x] Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed. The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2's central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it
- [ ] real link lost / rightly dropped · verifies · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:11` BuildStep: Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed.
  - target: reference `0018` AC-4, mention: AC-4 ... proved by /check verify instead
  - source text:
    > - [x] Verify it: `/check verify band anchor review` · **PASS** 2026-09-09, all 7 acceptance criteria met, 10 of 10 `verify.md` steps run and passed. The branch touches one file under `src/`, `pairs.ts`, and `rubric.ts` is absent from the diff against `main`, which is AC-2's central claim proved by the diff rather than by reading. AC-3 was proved harder than a green suite: `good-match-adjacent` was pointed at `weak_match` on purpose and the guard failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", naming `good_match`, before being restored. The whole evidence base was re-derived from the two baseline reports rather than trusted: all seven rows of `verify.md`'s distribution table and both run wide band totals match the reports exactly, and all three runs carry anchor hash `1b45f524b356`. The repository was searched again for the misread claim across 416 tracked files and **no surviving assertion of it was found**; every remaining occurrence of "5 of 5" is either a correct success denominator or a passage describing the misread as a misread. Two claims written into the docs were checked against the repo rather than assumed: `pairs.ts` no longer carries the sentence spec 0016 quotes, and no migration holds a `band` or `fit_score` column. AC-5 rests on the confirming run at 03:44Z, which started seven minutes after the commit it scored and against a tree identical to it
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong.
  - target: reference `16` (whole record), mention: feature 16's harness
  - phrase: against what feature 16's harness actually measured
  - source text:
    > ### 33. Band anchor review · done
    > Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
    > **Done when:** `control-one-gap` expects `possible_match` and passes a real run, `BAND_ANCHORS` and its hash `1b45f524b356` are untouched, the misread run evidence is corrected everywhere it was repeated, and the set still gives every band an exact expectation.
    > _spec [0018](../specs/0018-band-anchor-review/index.md) · code in `src/features/scoring/eval/pairs.ts`_
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:1` Feature: Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong.
  - target: reference `0018` (whole record), mention: spec [0018]
  - phrase: spec 0018
  - source text:
    > ### 33. Band anchor review · done
    > Check the band anchors against what feature 16's harness actually measured, and correct whichever side is wrong. The finding is that the anchors hold and one committed expectation does not, so this corrects the pair and records the anchor rule that was drafted and refused, rather than changing what real users are scored against.
    > **Done when:** `control-one-gap` expects `possible_match` and passes a real run, `BAND_ANCHORS` and its hash `1b45f524b356` are untouched, the misread run evidence is corrected everywhere it was repeated, and the set still gives every band an exact expectation.
    > _spec [0018](../specs/0018-band-anchor-review/index.md) · code in `src/features/scoring/eval/pairs.ts`_
- [ ] real link lost / rightly dropped · blocked-by · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:3` BuildStep: Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do not change.
  - target: reference `0016` AC-3, mention: falsified spec 0016's accepted AC-3
  - flags: relationship_type_ambiguous
  - source text:
    > - [x] Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do **not** change. Cross checked twice on Fable against an Opus author. The first draft added two anchor rules and was refused on three independent grounds: it contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed), it used "a substantial share of the role" when `rubric.ts:58` says anchors are written against the visible posting and never against the role, and it falsified spec 0016's accepted AC-3 by removing `boundary-seniority-gap`'s tolerance. The evidence it rested on was also wrong: the report's `summary` reads `"5 of 5 succeeded"` as a **success denominator**, not a band count, so `key-domain-mismatch` was a 3 to 2 split rather than stable, which is noise and not a defined gap. The second review of the narrowed spec returned sound with seven gaps, all applied
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:4` Consequence: The first draft added two anchor rules and was refused on three independent grounds: it contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed), it used "a substantial share of the role" when `rubric.ts:58` says anchors are written against the visible posting and never against the role, and it falsified spec 0016's accepted AC-3 by removing `boundary-seniority-gap`'s tolerance.
  - target: reference `src/features/scoring/rubric.ts` (whole record), mention: rubric.ts:58 says anchors are written against the visible posting and never against the role
  - phrase: it used "a substantial share of the role" when rubric.ts:58 says
  - flags: relationship_type_ambiguous
  - source text:
    > - [x] Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do **not** change. Cross checked twice on Fable against an Opus author. The first draft added two anchor rules and was refused on three independent grounds: it contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed), it used "a substantial share of the role" when `rubric.ts:58` says anchors are written against the visible posting and never against the role, and it falsified spec 0016's accepted AC-3 by removing `boundary-seniority-gap`'s tolerance. The evidence it rested on was also wrong: the report's `summary` reads `"5 of 5 succeeded"` as a **success denominator**, not a band count, so `key-domain-mismatch` was a 3 to 2 split rather than stable, which is noise and not a defined gap. The second review of the narrowed spec returned sound with seven gaps, all applied
- [ ] real link lost / rightly dropped · blocked-by · written by 1 of 3 runs
  - source: `feature-33#33-band-anchor-review-done:3` BuildStep: Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do not change.
  - target: reference `None` label `weak-match-shallow-overlap`, mention: contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed)
  - flags: relationship_type_ambiguous
  - source text:
    > - [x] Design it (spec): `/architect band anchor review` · written 2026-09-08, 7 acceptance criteria, and the decision is that the anchors do **not** change. Cross checked twice on Fable against an Opus author. The first draft added two anchor rules and was refused on three independent grounds: it contradicted a fourth pair (`weak-match-shallow-overlap`, whose own rationale rejects the test it proposed), it used "a substantial share of the role" when `rubric.ts:58` says anchors are written against the visible posting and never against the role, and it falsified spec 0016's accepted AC-3 by removing `boundary-seniority-gap`'s tolerance. The evidence it rested on was also wrong: the report's `summary` reads `"5 of 5 succeeded"` as a **success denominator**, not a band count, so `key-domain-mismatch` was a 3 to 2 split rather than stable, which is noise and not a defined gap. The second review of the narrowed spec returned sound with seven gaps, all applied
- [ ] real link lost / rightly dropped · corrected-by · written by 2 of 3 runs
  - source: reference `scope.md` (whole record), mention: the misread evidence at `scope.md:326`
  - target: `feature-33#33-band-anchor-review-done:5` BuildStep: Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense
  - source text:
    > - [x] Build it: `/develop band anchor review`
    >   - [x] Correct the pair and its file's own claim: `control-one-gap` to `possible_match` argued from the existing `possible_match` anchor text, and `pairs.ts`'s "before any model was asked" header amended to name its one exception, satisfies AC-1, AC-1b
    >   - [x] Correct the record: the misread evidence at `scope.md:326`, plus spec 0016's stale table row and its Follow up quote that reads as present tense, satisfies AC-4, AC-4b
    >   - [x] Prove it for free: the drift guard passes untouched, the data quality gate is clean, and every band still has an exact expectation now that `good-match-adjacent` is the only pair expecting `good_match`, satisfies AC-2, AC-3. 1178 unit tests green, `git diff main -- src/features/scoring/rubric.ts` empty. The band coverage guard was broken on purpose (pointing `good-match-adjacent` at `possible_match`) and failed by name on both assertions, `band-not-covered` and "covers every band with at least one exact expectation", so the pass is not vacuous
    >   - [x] Confirm it paid: `pnpm eval -t control-one-gap`, five vendor calls rather than eighty, satisfies AC-5. **PASS** 2026-09-09T03:44Z, anchor hash `1b45f524b356` unchanged, exit 0. Distribution `good_match` 2, `possible_match` 3, read from the report's `distribution` field: the pair passes on the strict majority and clears spec 0017's 3 of 5 floor, but by the minimum margin, and the old `good_match` expectation has now lost on all three runs ever taken (4 to 1, 5 to 0, 3 to 2). The five calls were confirmed by measurement rather than by reading the filter output, `ai_scoring global` day 2026-09-09 from absent to 5 and month 1225 to 1230, read through `pg` directly. Note the UTC day had already rolled at 03:44Z, so the 2026-09-08 row stayed at 195 and watching that row would have shown no movement
