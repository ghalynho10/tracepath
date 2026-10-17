# Held item packet, experiment 0013

Experiment 0013, a blind error analysis. Each item is something the extraction produced
from the pinned JobHunt snapshot; source lines are relative to `corpus/jobhunt/docs/`.
The items are shuffled under opaque ids.

Rule each item by replacing its marks with one word:

- an entity: `agree` when its span is cut right and its type is right;
- a link: `agree` when its type, its direction (from, then to) and both ends are right;
- `disagree` otherwise, and write what it should have been after `should have been:`
  (the type, the direction or the ends);
- `unsure` when you cannot tell.

Write anything you notice after `note:`. For an end that names something outside its
own section, `words` are the exact words the text used and `target` the entity they
match in the corpus, or `not resolved` when they match none. There is no pass or fail:
the notes are read together afterwards.

- [x] disagree · `H01` · entity · Consequence
  - source: specs/0007-auth-and-per-user-isolation/index.md:320
  - span: The entry page at `/` still shows a sign in invitation to a signed in visitor. That defers to the app shell feature, because options that fix it require `/` to read the session, which contradicts spec 0006's accepted security model ("no session check, no Supabase client, no Server Action, no user data of any kind") and its **AC-4**.
  - note: "That defers to the app shell feature" describes the first sentence, not its own claim; "because ..." is rationale. Type Consequence is right.
  - should have been: span: "The entry page at `/` still shows a sign in invitation to a signed in visitor."; rejected: "That defers to the app shell feature, because options that fix it require `/` to read the session, which contradicts spec 0006's accepted security model (...) and its **AC-4**."

- [x] disagree · `H02` · entity · Consequence
  - source: specs/0013-job-search-and-results-list/index.md:64
  - span: Feature 12 imports this exact shape later for its own field mapping.
  - note: a prediction: not checkable when written, checkable later, and nothing scheduled the later check. Not a FollowUp: it names no owed action. No type covers this. Passes the three question test. Leaving the parenthesis out is right (nothing disappears).
  - should have been: type unclassified


- [x] agree · `H03` · link · superseded-by
  - from source: specs/0021-seeded-demo-account/index.md:92
  - from span: The page shows no Adzuna attribution and no salary prediction attribution
  - to source: specs/0021-seeded-demo-account/index.md:92
  - to span: **AC-9**: The opposite is now required: every card carries the "Jobs by Adzuna" attribution (reusing `AdzunaAttribution` from spec 0013 unchanged), and a card whose salary was predicted rather than stated additionally carries both the `(estimated)` label and the Jobsworth attribution (`JobsworthAttribution`), reusing the same pairing `src/features/search/result-card.tsx` already renders, because the two must never come apart (`salaryText()`'s own doc comment). The listing genuinely came from Adzuna now, so both attributions are load bearing, not decorative.
  - note: 
  - should have been: 

- [x] agree · `H04` · link · unclassified
  - from source: specs/0008-app-shell-and-navigation/index.md:60
  - from span: The two existing assertions in `src/proxy.test.ts` pass **unmodified**: that the proxy treats a protected route exactly as it treats a public one (lines 49 to 62), and that it sets no cookies (lines 64 to 70).
  - to words: binding rule 6
  - to target: not resolved
  - note: 
  - should have been: 

- [x] agree · `H05` · entity · Feature
  - source: specs/0003-data-model/index.md:14
  - span: As a signed in user, I want my profile, skills, work history and preferences stored
  - note: 
  - should have been: 

- [x] agree · `H06` · entity · FollowUp
  - source: specs/0007-auth-and-per-user-isolation/index.md:332
  - span: `docs/observability/spans.md` will hold three unalerted auth spans. Decide at feature 10, which brings the first alert rule, whether `auth.callback`'s failure rate deserves one.
  - note: 
  - should have been: 

- [x] disagree · `H07` · entity · Consequence
  - source: specs/0007-auth-and-per-user-isolation/index.md:314
  - span: Session forced logout was never an option to weigh. Both projects report "Configuring user sessions is only available on the Pro Plan and above".
  - note: guide test used. Sentence 2 explains why sentence 1 holds: removing it loses backing, not a condition. The prompt (client.py:75-78) keeps clauses carrying a checkable fact in the span, so guide and prompt diverge here. Per JobHunt author: sentence 1 follows from Supabase pricing (type question); sentence 3 is a deferred claim with a trigger (separate item). Type Consequence is right.
  - should have been: span: "**Session forced logout was never an option to weigh.**"; rejected: "Both projects report \"Configuring user sessions is only available on the Pro Plan and above\"."

- [x] agree · `H08` · link · unclassified
  - from source: specs/0021-seeded-demo-account/index.md:108
  - from span: If the seeded data cannot be read because of a genuine fault (the database is unreachable, or a row fails to parse), the page answers a normal 200 and shows a visible failure state rather than an empty, broken looking, or server error page. This is a different case from AC-15, and the two must render distinguishable copy.
  - to source: specs/0021-seeded-demo-account/index.md:127
  - to span: If no refresh has ever run since the current schema was deployed (`demo_refresh.refreshed_at is null`), the page shows a visible "results are not available yet" state, worded distinctly from AC-12's failure state (the first is expected and temporary, the second is a fault), never a blank or partially rendered page. This is a normal, successful read of an empty state, not a `Failure`.
  - note: 
  - should have been: 

- [x] disagree · `H09` · entity · Constraint
  - source: specs/0002-deployment-and-environments/index.md:122
  - span: **The `scaffold_check` fixture and its two seeded users** stay in `supabase/seed.sql`, made idempotent, and the migration workflow applies that file to the **development project only**, never production.
  - note: three conditions that can fail independently (idempotence can fail while the rest holds). Sentence 2 is rationale in its entirety, including "Production carries no fake users and no scaffold row" and the evaluation "which is correct".
  - should have been: split into: (a) "**The `scaffold_check` fixture and its two seeded users** stay in `supabase/seed.sql`", Constraint; (b) "made idempotent", Constraint; (c) "the migration workflow applies that file to the **development project only**, never production", Constraint; rejected: "Production carries no fake users and no scaffold row, which is correct: production has no sign in path at all until feature 7, so the thread is proved on a preview against the development project."

- [x] agree · `H10` · link · verifies
  - from source: specs/0002-deployment-and-environments/index.md:231
  - from span: Auth/permission: an anonymous request to a preview URL is stopped by Vercel Authentication, verifies **AC-3**.
  - to words: **AC-3**
  - to target: specs/0002-deployment-and-environments/index.md:24
  - to target span: **AC-3**: A preview URL is not reachable without a Vercel login. The production URL is public.
  - note: 
  - should have been: 

- [x] agree · `H11` · link · unclassified
  - from source: specs/0015-fit-scoring-with-shown-reasoning/index.md:114
  - from span: and, having reordered nothing, still restores focus if the reveal orphaned it (AC-17).
  - to words: AC-17
  - to target: specs/0015-fit-scoring-with-shown-reasoning/index.md:39
  - to target span: **AC-17**: Focus survives the re-sort by being **restored, not preserved**. The restoration obeys four rules, each written as what the reader experiences rather than what the code sets: It acts **only when focus was actually orphaned**, that is, the active element is the body (or nothing) at the moment the ranked list arrives. A reader whose focus is still on a live element, the search box, the header, a card control outside the boundary, is never moved. It restores **the same control**, found by a key that is unique per control and stable across the reorder, never by position in the list. The key is `<source>:<sourceJobId>:<control>`, where the first two segments are the `Listing` fields `result-list.tsx` already composes into its React key, and `<control>` is one of exactly two literals: `posting-link` for the "View the posting" link, `apply` for the apply control. A third focusable control added to a card later adds a third literal here first. It **remembers at most one key, and forgets it the moment it is used or declined**. `FocusRestorer` consumes and clears the recorded key on every mount, whether it restored anything or not. The recorder listens for `focusin` **on the document, filtered by `event.target.closest('[data-focus-key]')`**, rather than on a results container. A `focusin` on anything without a key (the search box, the header) is a no operation and leaves the last remembered key alone; it does not need to clear it, because focus resting on a live element already stops the first rule from firing. When that key is absent from the ranked list, it focuses the results list container, which carries `tabindex="-1"` and an accessible name (`COPY-8`), rather than leaving the reader on the body. The restored control is **brought into view**, so focus is moved without `preventScroll`. A card that moved from the bottom of the list to the top takes the reader with it.
  - note: 
  - should have been: 

- [x] agree · `H12` · entity · Constraint
  - source: specs/0002-deployment-and-environments/index.md:124
  - span: The seed is applied with `psql "$SUPABASE_DB_URL_DEV" -f supabase/seed.sql`, a direct connection using a stored connection string.
  - note: 
  - should have been: 

- [x] agree · `H13` · entity · AcceptanceCriterion
  - source: specs/0014-apply-redirect-and-application-record/index.md:37
  - span: **AC-7**: An application row whose stored salary was predicted renders `(estimated)` beside the figure and carries the Jobsworth attribution, matching spec 0013's AC-7 exactly: a 20 by 20 pixel icon plus the words `Adzuna Jobsworth`, both linked to `ADZUNA_JOBSWORTH_URL`, with the mouseover text `Salary estimate powered by Adzuna Jobsworth`. A stored non predicted salary renders neither.
  - note: 
  - should have been: 

- [x] agree · `H14` · entity · AcceptanceCriterion
  - source: specs/0008-app-shell-and-navigation/index.md:60
  - span: **AC-9**: The two existing assertions in `src/proxy.test.ts` pass **unmodified**: that the proxy treats a protected route exactly as it treats a public one (lines 49 to 62), and that it sets no cookies (lines 64 to 70).
  - note: 
  - should have been: 

- [x] agree · `H15` · entity · AcceptanceCriterion
  - source: specs/0003-data-model/index.md:22
  - span: **AC-2**: Every one of the six has row level security enabled and forced, and carries an explicit `grant` to `authenticated` and to no other role. `anon` and `service_role` hold nothing, so a request carrying no session is refused at the privilege check with a hard permission denial, not an empty result set that reads like success.
  - note: 
  - should have been: 

- [x] disagree · `H16` · link · unclassified
  - from source: specs/0007-auth-and-per-user-isolation/index.md:334
  - from span: Both remedies need a domain this project owns: a Supabase custom domain, which is a paid add on, so the host itself reads as the product; or publishing and verifying the Google app, which needs feature 21's privacy policy and terms served from an authorized domain, and **Google will not accept a `vercel.app` address**. The scope's deferred entry is rewritten on those terms.
  - to words: feature 21's privacy policy and terms
  - to target: not resolved
  - note: a dependency the text states ("which needs feature 21's privacy policy and terms served from an authorized domain"), so blocked-by, not unclassified.
  - should have been: type blocked-by; to: feature-21 (the scope row), not "feature 21's privacy policy and terms"

- [x] agree · `H17` · entity · FollowUp
  - source: specs/0007-auth-and-per-user-isolation/index.md:328
  - span: Feature 21's privacy notice must describe what arrives from the provider into `auth.users`: email address, display name, avatar URL.
  - note: 
  - should have been: 

- [x] agree · `H18` · link · superseded-by
  - from source: specs/0021-seeded-demo-account/index.md:67
  - from span: Exactly two seeded listings (the same title and company each time) appear under both profiles, each with a different band, different matched and not mentioned skills, and different written reasoning per profile. Their exact content is named in **Seed content** below.
  - to source: specs/0021-seeded-demo-account/index.md:67
  - to span: **AC-6**: Every kept listing (AC-17) appears under both profiles now, not just two of them, because both personas are scored against the same kept set, drawn from both searches. Each listing's band, matched skills, not mentioned skills, ungrounded skills, and reasoning are computed independently per persona by the real scorer and the real grounding check, and are expected to differ, but nothing in the build may select or discard a listing based on whether they actually do, and a refresh that returns fewer than the target count (**Feature design**, "The kept listing count") is still published as is, never padded or retried to reach it, as long as it kept at least one listing; a refresh that kept zero aborts (**Feature design**, "Refresh outcomes").
  - note: 
  - should have been: 

- [x] agree · `H19` · link · unclassified
  - from source: specs/0011-usage-gating-and-kill-switch/index.md:39
  - from span: **AC-14**: A database failure while reading the cap configuration or writing the counters fails closed: the call is refused, matching the project's named risk rule and the kill switch's own existing fail closed default. `checkUsageGate()` inspects the `.rpc()` response's own `error` field before reading `configured`, `allowed`, or `reason`: a non null `error` maps to `database_unavailable`, and `data: null` with no `error` is itself also treated as `database_unavailable` rather than as an absent decision.
  - to source: specs/0011-usage-gating-and-kill-switch/index.md:31
  - to span: **AC-6**: An unrecognised `call_type`, or a `call_type` missing any one of its three required `usage_cap` rows (account/week, global/day, global/month; partial configuration is treated the same as none), is reported through `failure()` with a new `FailureKind` member, `usage_gate_misconfigured`, severity `unexpected`. The atomic function never raises to signal this: it returns `configured: boolean` as an ordinary output column. `configured: false` is what `checkUsageGate()` maps to this failure; the `allowed`/`reason` columns carry no meaning when `configured` is false.
  - note: 
  - should have been: 

- [x] disagree · `H20` · entity · unclassified
  - source: specs/0002-deployment-and-environments/index.md:104
  - span: Task 10 writes the grant and task 11 proves the read by hand before anything trusts it.
  - note: part of the paragraph "Why the grant is load bearing rather than tidy up", a reason; also reads as a pointer to build plan tasks 10 and 11 (a claim about the spec's own content).
  - should have been: not an item; rejected span of the grant item at line 101 ("**One explicit `grant select` to `service_role`** ...")
