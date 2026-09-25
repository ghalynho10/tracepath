# Ruling sheet, experiment 0005 (AC-16)

Replace each line's marks with one word, and add a few words on why when you disagree. Entity and relationship agreement are tallied separately (`report.py tally`).

- **Entities**: `agree` when the model's cut and type pass HANDOFF's three question test (atomicity, referenceability, right sizing) and the deletion trick, `disagree` otherwise.
- **Relationships**: `agree` when the link is real, and its type, direction and endpoints are what you would have written, `disagree` otherwise.
- **Links the befores wrote and no after wrote**: `real link lost` when the source text states a relation the afters should have kept, `rightly dropped` when it does not (a table row, an unaffected claim, an invented pair, and so on). A note says when the same endpoints survive in the afters under another type.

## Group A: 0021 / requirements (a unit kind with no worked example)

### Entities

10 evenly spaced through after run 1's located order.

- [x] disagree · `0021#requirements:1` · Feature
  - reason: On this item the "so that" clause carried the feature's distinguishing value (the ranking being judgeable), not background; the engineer ruled the span too narrow.
  - span: As a visitor who has not signed up, I want to see real listings scored for real against a
  stated candidate
  - rejected: ['so that I can judge whether the ranking actually works, not just whether it\n  looks plausible.']
  - flags: granularity_boundary_call
- [x] agree · `0021/AC-1` · AcceptanceCriterion
  - span: A visitor reaches `/demo` and sees a list of results with no sign in, no redirect,
  and no account required.
- [x] agree · `0021/AC-3` · AcceptanceCriterion
  - span: The opposite
  is now true on purpose: every listing (company name, title, description, location) is real,
  exactly as Adzuna returned it, including a real employer's name on a `weak_match` or
  `not_a_match` row (AC-19). The two candidate personas are the only fictional element left, and
  they are shown on the page in full (AC-14) as the disclosure that makes this honest.
  - flags: multi_condition_split
- [x] agree · `0021#requirements:5` · AcceptanceCriterion
  - reason: (struck, superseded text: kept whole as the thing replaced, per the struck text rule)
  - span: No control on the page writes to the database. There is no code path by which one
  visitor's visit changes what the next visitor sees.
- [x] agree · `0021#requirements:6` · AcceptanceCriterion
  - reason: (superseded text; kept whole as the thing that was replaced, less fragmentation) 
  - span: Exactly two seeded listings (the same title and company each time) appear under both
  profiles, each with a different band, different matched and not mentioned skills, and
  different written reasoning per profile. Their exact content is named in **Seed content**

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
- [x] disagree · `0021/AC-12` · AcceptanceCriterion
  - reason: (should split: fault renders 200 with a visible failure state / copy distinguishable from AC-15, testable separately)
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
- [x] disagree · `0021/AC-17` · AcceptanceCriterion
  - reason: (should split into its separately testable rules: searches and keep / never selected by score / score against both personas / abort on any unclean call / atomic replace / gate refusal severity / abort on zero kept)
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
### Relationships

5 evenly spaced through the 12 distinct links the three after runs wrote.


- [x] agree · superseded-by · written by 3 of 3 runs
  - reason: (re-checked under the history link rule: new AC-2 contradicts the old, a deliberate change of direction, so superseded)
  - source: `0021#requirements:3` AcceptanceCriterion: The page makes no external paid call on any render: no Adzuna search, no AI scoring
  call. Every value shown was prepared in advance.
  - target: `0021/AC-2` AcceptanceCriterion: The page still
  makes no external paid call on any render. Every paid call (two Adzuna
  searches, then one
  `ai_scoring` call, and, for any listing whose score claims at least one skill, one chained
  `ai_check` call, per listing per persona, exactly the sequence `scoreListings()` already runs for
  a real search) now happens only inside the refresh described in AC-17, gated exactly like every
  other real call in this app, never inside a page render.
  - phrase: SUPERSEDED 2026-09-14
  - source text:
    > - **AC-2**: ~~The page makes no external paid call on any render: no Adzuna search, no AI scoring
    >   call. Every value shown was prepared in advance.~~ · **SUPERSEDED 2026-09-14.** The page still
    >   makes no external paid call on any render. Every paid call (~~one Adzuna search~~ two Adzuna
    >   searches, revised 2026-09-15, then one
    >   `ai_scoring` call, and, for any listing whose score claims at least one skill, one chained
    >   `ai_check` call, per listing per persona, exactly the sequence `scoreListings()` already runs for
    >   a real search) now happens only inside the refresh described in AC-17, gated exactly like every
    >   other real call in this app, never inside a page render.
- [x] disagree · superseded-by · written by 2 of 3 runs
  - reason: (should be amended-by: premise still true, narrowed in scope with an addition; same direction, not retired)
  - source: `0021#requirements:5` AcceptanceCriterion: No control on the page writes to the database. There is no code path by which one
  visitor's visit changes what the next visitor sees.
  - target: `0021/AC-4` AcceptanceCriterion: No
  visitor facing control writes to the database, and a visitor's own visit still cannot change
  what the next visitor sees. What is no longer true is the absolute second sentence: the refresh
  (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the
  visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind
  anything a visitor's browser can reach.
  - phrase: SUPERSEDED 2026-09-14
  - source text:
    > - **AC-4**: ~~No control on the page writes to the database. There is no code path by which one
    >   visitor's visit changes what the next visitor sees.~~ · **SUPERSEDED 2026-09-14.** No
    >   visitor facing control writes to the database, and a visitor's own visit still cannot change
    >   what the next visitor sees. What is no longer true is the absolute second sentence: the refresh
    >   (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the
    >   visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind
    >   anything a visitor's browser can reach.
- [ ] agree / disagree · superseded-by · written by 1 of 3 runs
  - source: `0021#requirements:7` AcceptanceCriterion: Within one profile, listings are ordered best band first, ties broken by Adzuna's own
  returned rank for that search (stored as `sort_order`), the same band ordering rule `/search`
  already uses.
  - target: `0021/AC-7` AcceptanceCriterion: Within one profile, listings are ordered best band first, ties broken by
  the order the kept walk kept each listing, which interleaves the
  two searches' own Adzuna order (stored as `sort_order`), the same band ordering rule `/search`
  already uses.
  - phrase: revised 2026-09-15
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-7**: Within one profile, listings are ordered best band first, ties broken by ~~Adzuna's own
    >   returned rank for that search~~ the order the kept walk kept each listing, which interleaves the
    >   two searches' own Adzuna order (revised 2026-09-15; **Feature design**, "The kept listing
    >   count") (stored as `sort_order`), the same band ordering rule `/search` already uses. *(Tiebreak source changed 2026-09-14: a hand seeded display order is replaced by
    >   Adzuna's own order, since there is no longer a hand authored order to seed.)*
- [ ] agree / disagree · amended-by · written by 1 of 3 runs
  - source: `0021#requirements:10` AcceptanceCriterion: Deliberately not
  built by this spec.
  - target: `0021/AC-13` AcceptanceCriterion: The entry page's hero carries a real, working link to `/demo`, and the "what's real
  today" status card moves "a no sign in demo account" from planned to working. Built
  2026-09-17, once its own stated condition was met: the real data version shipped in pull
  request #135 and the first production refresh ran 2026-09-16, so `/demo` shows real scored
  postings rather than the fabricated set this was waiting out.
  - phrase: Built 2026-09-17
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-13**: The entry page's hero carries a real, working link to `/demo`, and the "what's real
    >   today" status card moves "a no sign in demo account" from planned to working. ~~**Deliberately not
    >   built by this spec.** Recorded in `docs/scope/scope.md` on 2026-09-14: wiring this while the page
    >   still showed fabricated data would have advertised a demo already decided to be insufficient,
    >   and that reasoning holds unchanged for the real data version until it ships.~~ **Built
    >   2026-09-17**, once its own stated condition was met: the real data version shipped in pull
    >   request #135 and the first production refresh ran 2026-09-16, so `/demo` shows real scored
    >   postings rather than the fabricated set this was waiting out.
- [ ] agree / disagree · amended-by · written by 1 of 3 runs
  - source: `0021#requirements:5` AcceptanceCriterion: No control on the page writes to the database. There is no code path by which one visitor's visit changes what the next visitor sees.
  - target: `0021/AC-4` AcceptanceCriterion: No visitor facing control writes to the database, and a visitor's own visit still cannot change what the next visitor sees. What is no longer true is the absolute second sentence: the refresh (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind anything a visitor's browser can reach.
  - phrase: **SUPERSEDED 2026-09-14.**
  - flags: relationship_type_ambiguous
  - source text:
    > - **AC-4**: ~~No control on the page writes to the database. There is no code path by which one
    >   visitor's visit changes what the next visitor sees.~~ · **SUPERSEDED 2026-09-14.** No
    >   visitor facing control writes to the database, and a visitor's own visit still cannot change
    >   what the next visitor sees. What is no longer true is the absolute second sentence: the refresh
    >   (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the
    >   visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind
    >   anything a visitor's browser can reach.

### Links the befores wrote and no after wrote

50 distinct links appear in at least one `0002.3` before run and in none of the `0003.0` afters (by how many before runs wrote each: {'1': 18, '2': 7, '3': 25}). 10 evenly spaced through them, in the order the befores first wrote them.

- [ ] real link lost / rightly dropped · unclassified · written by 3 of 3 runs
  - source: `0021/AC-2` AcceptanceCriterion: ~~The page makes no external paid call on any render: no Adzuna search, no AI scoring call. Every value shown was prepared in advance.~~ · **SUPERSEDED 2026-09-14.** The page still makes no external paid call on any render. Every paid call (~~one Adzuna search~~ two Adzuna searches, revised 2026-09-15, then one `ai_scoring` call, and, for any listing whose score claims at least one skill, one chained `ai_check` call, per listing per persona, exactly the sequence `scoreListings()` already runs for a real search) now happens only inside the refresh described in AC-17, gated exactly like every other real call in this app, never inside a page render.
  - target: `0021/AC-17` AcceptanceCriterion: A refresh, triggered as described in AC-18, runs ~~exactly one real Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings from each search in that search's own returned order, by the walk **Feature design** states (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores every kept listing against both personas exactly as `scoreListings()` already does for a real search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is best effort, the refresh has no reader waiting on it and a previous, fully checked run to fall back to, so an unfinished check is treated the same as an unfinished score rather than silently written as if it had passed. Only once every kept listing has a clean, allowed score under both personas does the refresh atomically replace the entire contents of `demo_result` and the single `demo_refresh` row in one database transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`, `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure. A refresh whose searches leave zero kept listings in total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact shape of each outcome, both recorded 2026-09-15 from what `/develop` built.
  - phrase: now happens only inside the refresh described in AC-17
  - source text:
    > - **AC-2**: ~~The page makes no external paid call on any render: no Adzuna search, no AI scoring
    >   call. Every value shown was prepared in advance.~~ · **SUPERSEDED 2026-09-14.** The page still
    >   makes no external paid call on any render. Every paid call (~~one Adzuna search~~ two Adzuna
    >   searches, revised 2026-09-15, then one
    >   `ai_scoring` call, and, for any listing whose score claims at least one skill, one chained
    >   `ai_check` call, per listing per persona, exactly the sequence `scoreListings()` already runs for
    >   a real search) now happens only inside the refresh described in AC-17, gated exactly like every
    >   other real call in this app, never inside a page render.
- [ ] real link lost / rightly dropped · unclassified · written by 3 of 3 runs
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
- [ ] real link lost / rightly dropped · unclassified · written by 3 of 3 runs
  - source: `0021/AC-7` AcceptanceCriterion: Within one profile, listings are ordered best band first, ties broken by ~~Adzuna's own returned rank for that search~~ the order the kept walk kept each listing, which interleaves the two searches' own Adzuna order (revised 2026-09-15; **Feature design**, "The kept listing count") (stored as `sort_order`), the same band ordering rule `/search` already uses.
  - target: reference `/search` (whole record), mention: the same band ordering rule `/search` already uses
  - phrase: the same band ordering rule `/search` already uses
  - source text:
    > - **AC-7**: Within one profile, listings are ordered best band first, ties broken by ~~Adzuna's own
    >   returned rank for that search~~ the order the kept walk kept each listing, which interleaves the
    >   two searches' own Adzuna order (revised 2026-09-15; **Feature design**, "The kept listing
    >   count") (stored as `sort_order`), the same band ordering rule `/search` already uses. *(Tiebreak source changed 2026-09-14: a hand seeded display order is replaced by
    >   Adzuna's own order, since there is no longer a hand authored order to seed.)*
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0021/AC-9` AcceptanceCriterion: ~~The page shows no Adzuna attribution and no salary prediction attribution, since nothing on it came from either vendor.~~ · **SUPERSEDED 2026-09-14.** The opposite is now required: every card carries the "Jobs by Adzuna" attribution (reusing `AdzunaAttribution` from spec 0013 unchanged), and a card whose salary was predicted rather than stated additionally carries both the `(estimated)` label and the Jobsworth attribution (`JobsworthAttribution`), reusing the same pairing `src/features/search/result-card.tsx` already renders, because the two must never come apart (`salaryText()`'s own doc comment). The listing genuinely came from Adzuna now, so both attributions are load bearing, not decorative.
  - target: reference `salaryText()` (whole record), mention: (`salaryText()`'s own doc comment)
  - phrase: (`salaryText()`'s own doc comment)
  - source text:
    > - **AC-9**: ~~The page shows no Adzuna attribution and no salary prediction attribution, since
    >   nothing on it came from either vendor.~~ · **SUPERSEDED 2026-09-14.** The opposite is now
    >   required: every card carries the "Jobs by Adzuna" attribution (reusing `AdzunaAttribution` from
    >   spec 0013 unchanged), and a card whose salary was predicted rather than stated additionally
    >   carries both the `(estimated)` label and the Jobsworth attribution (`JobsworthAttribution`),
    >   reusing the same pairing `src/features/search/result-card.tsx` already renders, because the two
    >   must never come apart (`salaryText()`'s own doc comment). The listing genuinely came from Adzuna
    >   now, so both attributions are load bearing, not decorative.
- [ ] real link lost / rightly dropped · unclassified · written by 1 of 3 runs
  - source: `0021/AC-13` AcceptanceCriterion: The entry page's hero carries a real, working link to `/demo`, and the "what's real today" status card moves "a no sign in demo account" from planned to working. **Built 2026-09-17**, once its own stated condition was met: the real data version shipped in pull request #135 and the first production refresh ran 2026-09-16, so `/demo` shows real scored postings rather than the fabricated set this was waiting out.
  - target: reference `#135` (whole record), mention: shipped in pull request #135
  - phrase: shipped in pull request #135
  - source text:
    > - **AC-13**: The entry page's hero carries a real, working link to `/demo`, and the "what's real
    >   today" status card moves "a no sign in demo account" from planned to working. ~~**Deliberately not
    >   built by this spec.** Recorded in `docs/scope/scope.md` on 2026-09-14: wiring this while the page
    >   still showed fabricated data would have advertised a demo already decided to be insufficient,
    >   and that reasoning holds unchanged for the real data version until it ships.~~ **Built
    >   2026-09-17**, once its own stated condition was met: the real data version shipped in pull
    >   request #135 and the first production refresh ran 2026-09-16, so `/demo` shows real scored
    >   postings rather than the fabricated set this was waiting out.
- [ ] real link lost / rightly dropped · unclassified · written by 3 of 3 runs
  - source: `0021/AC-17` AcceptanceCriterion: A refresh, triggered as described in AC-18, runs ~~exactly one real Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings from each search in that search's own returned order, by the walk **Feature design** states (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores every kept listing against both personas exactly as `scoreListings()` already does for a real search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is best effort, the refresh has no reader waiting on it and a previous, fully checked run to fall back to, so an unfinished check is treated the same as an unfinished score rather than silently written as if it had passed. Only once every kept listing has a clean, allowed score under both personas does the refresh atomically replace the entire contents of `demo_result` and the single `demo_refresh` row in one database transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`, `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure. A refresh whose searches leave zero kept listings in total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact shape of each outcome, both recorded 2026-09-15 from what `/develop` built.
  - target: `0021/AC-18` AcceptanceCriterion: The refresh is reachable only via a `POST` to a dedicated route handler, authorized by hashing the caller supplied secret (from an `Authorization: Bearer` header) and the configured `env.DEMO_REFRESH_SECRET` with SHA-256 and comparing the two digests; no other path triggers it. To spend real `job_search` and `ai_scoring`/`ai_check` budget through the existing gate (which requires a verified session, **Feature design**), the refresh authenticates as a dedicated, permanent internal identity that holds no `profile` or `application` row and is never reachable by a real visitor. That identity's own weekly account scope budget is therefore always separate from any real signed in user's.
  - phrase: triggered as described in AC-18
  - source text:
    > - **AC-17** (new 2026-09-14): A refresh, triggered as described in AC-18, runs ~~exactly one real
    >   Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's
    >   own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's
    >   own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature
    >   design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings
    >   from each search in that search's own returned order, by the walk **Feature design** states
    >   (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores
    >   every kept listing against both personas exactly as `scoreListings()` already does for a real
    >   search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if
    >   any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained
    >   `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether
    >   refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is
    >   best effort because a real search must still render something, the refresh has no reader waiting
    >   on it and a previous, fully checked run to fall back to, so an unfinished check is treated the
    >   same as an unfinished score rather than silently written as if it had passed. Only once every
    >   kept listing has a clean, allowed score under both personas does the refresh atomically replace
    >   the entire contents of `demo_result` and the single `demo_refresh` row in one database
    >   transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`,
    >   `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure,
    >   since it is the budget working as designed. A refresh whose searches leave zero kept listings in
    >   total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact
    >   shape of each outcome, both recorded 2026-09-15 from what `/develop` built.
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0021/AC-17` AcceptanceCriterion: A refresh, triggered as described in AC-18, runs ~~exactly one real Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings from each search in that search's own returned order, by the walk **Feature design** states (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores every kept listing against both personas exactly as `scoreListings()` already does for a real search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is best effort, the refresh has no reader waiting on it and a previous, fully checked run to fall back to, so an unfinished check is treated the same as an unfinished score rather than silently written as if it had passed. Only once every kept listing has a clean, allowed score under both personas does the refresh atomically replace the entire contents of `demo_result` and the single `demo_refresh` row in one database transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`, `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure. A refresh whose searches leave zero kept listings in total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact shape of each outcome, both recorded 2026-09-15 from what `/develop` built.
  - target: reference `/develop` (whole record), mention: from what `/develop` built
  - phrase: from what `/develop` built
  - source text:
    > - **AC-17** (new 2026-09-14): A refresh, triggered as described in AC-18, runs ~~exactly one real
    >   Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's
    >   own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's
    >   own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature
    >   design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings
    >   from each search in that search's own returned order, by the walk **Feature design** states
    >   (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores
    >   every kept listing against both personas exactly as `scoreListings()` already does for a real
    >   search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if
    >   any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained
    >   `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether
    >   refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is
    >   best effort because a real search must still render something, the refresh has no reader waiting
    >   on it and a previous, fully checked run to fall back to, so an unfinished check is treated the
    >   same as an unfinished score rather than silently written as if it had passed. Only once every
    >   kept listing has a clean, allowed score under both personas does the refresh atomically replace
    >   the entire contents of `demo_result` and the single `demo_refresh` row in one database
    >   transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`,
    >   `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure,
    >   since it is the budget working as designed. A refresh whose searches leave zero kept listings in
    >   total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact
    >   shape of each outcome, both recorded 2026-09-15 from what `/develop` built.
- [ ] real link lost / rightly dropped · superseded-by · written by 1 of 3 runs
  - source: `0021/AC-4` AcceptanceCriterion: ~~No control on the page writes to the database. There is no code path by which one visitor's visit changes what the next visitor sees.~~ · **SUPERSEDED 2026-09-14.** No visitor facing control writes to the database, and a visitor's own visit still cannot change what the next visitor sees. What is no longer true is the absolute second sentence: the refresh (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind anything a visitor's browser can reach.
  - target: `0021/AC-4` AcceptanceCriterion: ~~No control on the page writes to the database. There is no code path by which one visitor's visit changes what the next visitor sees.~~ · **SUPERSEDED 2026-09-14.** No visitor facing control writes to the database, and a visitor's own visit still cannot change what the next visitor sees. What is no longer true is the absolute second sentence: the refresh (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind anything a visitor's browser can reach.
  - phrase: SUPERSEDED 2026-09-14
  - source text:
    > - **AC-4**: ~~No control on the page writes to the database. There is no code path by which one
    >   visitor's visit changes what the next visitor sees.~~ · **SUPERSEDED 2026-09-14.** No
    >   visitor facing control writes to the database, and a visitor's own visit still cannot change
    >   what the next visitor sees. What is no longer true is the absolute second sentence: the refresh
    >   (AC-17) is a code path that deliberately changes what every visitor sees, on a schedule the
    >   visitor never controls. It runs behind a secret only the engineer holds (AC-18), never behind
    >   anything a visitor's browser can reach.
- [ ] real link lost / rightly dropped · superseded-by · written by 1 of 3 runs
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
- [ ] real link lost / rightly dropped · unclassified · written by 2 of 3 runs
  - source: `0021/AC-17` AcceptanceCriterion: A refresh, triggered as described in AC-18, runs ~~exactly one real Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings from each search in that search's own returned order, by the walk **Feature design** states (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores every kept listing against both personas exactly as `scoreListings()` already does for a real search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is best effort, the refresh has no reader waiting on it and a previous, fully checked run to fall back to, so an unfinished check is treated the same as an unfinished score rather than silently written as if it had passed. Only once every kept listing has a clean, allowed score under both personas does the refresh atomically replace the entire contents of `demo_result` and the single `demo_refresh` row in one database transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`, `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure. A refresh whose searches leave zero kept listings in total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact shape of each outcome, both recorded 2026-09-15 from what `/develop` built.
  - target: `0021/AC-2` AcceptanceCriterion: ~~The page makes no external paid call on any render: no Adzuna search, no AI scoring call. Every value shown was prepared in advance.~~ · **SUPERSEDED 2026-09-14.** The page still makes no external paid call on any render. Every paid call (~~one Adzuna search~~ two Adzuna searches, revised 2026-09-15, then one `ai_scoring` call, and, for any listing whose score claims at least one skill, one chained `ai_check` call, per listing per persona, exactly the sequence `scoreListings()` already runs for a real search) now happens only inside the refresh described in AC-17, gated exactly like every other real call in this app, never inside a page render.
  - phrase: exactly as `scoreListings()` already does for a real search (AC-2)
  - source text:
    > - **AC-17** (new 2026-09-14): A refresh, triggered as described in AC-18, runs ~~exactly one real
    >   Adzuna search using the fixed query in **Feature design**, de-duplicates the results by Adzuna's
    >   own listing id (first occurrence wins) and keeps up to a fixed count of what remains in Adzuna's
    >   own returned order~~ exactly two real Adzuna searches using the fixed queries in **Feature
    >   design**, de-duplicates across both by Adzuna's own listing id, and keeps up to four listings
    >   from each search in that search's own returned order, by the walk **Feature design** states
    >   (revised 2026-09-15) (never selected, reordered, or padded by how any score turns out), and scores
    >   every kept listing against both personas exactly as `scoreListings()` already does for a real
    >   search (AC-2), including the chained grounding check. The refresh aborts, writing nothing, if
    >   any one of those `ai_scoring` calls does not come back as an allowed score, or if the chained
    >   `ai_check` call for a listing that claimed a skill does not come back as a clean verdict, whether
    >   refused by the usage gate or genuinely failed either way. Unlike `/search`, where the check is
    >   best effort because a real search must still render something, the refresh has no reader waiting
    >   on it and a previous, fully checked run to fall back to, so an unfinished check is treated the
    >   same as an unfinished score rather than silently written as if it had passed. Only once every
    >   kept listing has a clean, allowed score under both personas does the refresh atomically replace
    >   the entire contents of `demo_result` and the single `demo_refresh` row in one database
    >   transaction. A gate refusal (of ~~either call type~~ any of the three call types, `job_search`,
    >   `ai_scoring` or `ai_check`) is reported at a different Sentry severity than a genuine failure,
    >   since it is the budget working as designed. A refresh whose searches leave zero kept listings in
    >   total also aborts, writing nothing. **Feature design**, "Refresh outcomes", states the exact
    >   shape of each outcome, both recorded 2026-09-15 from what `/develop` built.

## Group B: 0013 / feature-design (a kind with an example, different content)

### Entities

10 evenly spaced through after run 1's located order.

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

### Relationships

5 evenly spaced through the 16 distinct links the three after runs wrote.

- [ ] agree / disagree · unclassified · written by 2 of 3 runs
  - source: `0013#feature-design:3` Constraint: Feature 12 imports this exact shape later for its own field mapping (spec 0003 already names feature 11 as owner of that mapping).
  - target: reference `feature 12` (whole record), mention: Feature 12
  - phrase: Feature 12 imports this exact shape later for its own field mapping
  - flags: relationship_type_ambiguous
  - source text:
    > No new database table. Results are never persisted (by product decision, recorded in `docs/scope/scope.md`'s Slice 1 introduction), so the only new shape is an in memory value object, Zod parsed at the Adzuna response boundary and never written to Postgres. Feature 12 imports this exact shape later for its own field mapping (spec 0003 already names feature 11 as owner of that mapping).
- [ ] agree / disagree · verifies · written by 3 of 3 runs
  - source: `0013#feature-design:22` TestScenario: Happy path: a signed in user with a `job_preference` row searches with a real title, sees real Adzuna listings with working attribution and outbound links, verifies **AC-1**, **AC-6**, **AC-8**.
  - target: reference `0013` AC-8, mention: **AC-8**
  - phrase: verifies **AC-1**, **AC-6**, **AC-8**
  - source text:
    > - Happy path: a signed in user with a `job_preference` row searches with a real title, sees real Adzuna listings with working attribution and outbound links, verifies **AC-1**, **AC-6**, **AC-8**.
- [ ] agree / disagree · verifies · written by 3 of 3 runs
  - source: `0013#feature-design:25` TestScenario: Failure case: a batch where one of several returned listings fails its own item level parse renders the rest normally and drops only the bad one, verifies **AC-1**, **AC-5** (the "every item fails" branch is a separate case, same kind).
  - target: reference `0013` AC-1, mention: **AC-1**
  - phrase: verifies **AC-1**, **AC-5**
  - source text:
    > - Failure case: a batch where one of several returned listings fails its own item level parse renders the rest normally and drops only the bad one, verifies **AC-1**, **AC-5** (the "every item fails" branch is a separate case, same kind).
- [ ] agree / disagree · verifies · written by 3 of 3 runs
  - source: `0013#feature-design:26` TestScenario: Gate: a caller whose account week cap is already spent gets the exact `account_week_cap_reached` sentence and no Adzuna call runs, verifies **AC-3**, **AC-10**.
  - target: reference `0013` AC-10, mention: **AC-10**
  - phrase: verifies **AC-3**, **AC-10**
  - source text:
    > - Gate: a caller whose account week cap is already spent gets the exact `account_week_cap_reached` sentence and no Adzuna call runs, verifies **AC-3**, **AC-10**.
- [ ] agree / disagree · verifies · written by 3 of 3 runs
  - source: `0013#feature-design:29` TestScenario: Empty: a search that legitimately matches nothing renders the empty state, distinguishable from both the failure and refusal states, verifies **AC-4**.
  - target: reference `0013` AC-4, mention: **AC-4**
  - phrase: verifies **AC-4**
  - source text:
    > - Empty: a search that legitimately matches nothing renders the empty state, distinguishable from both the failure and refusal states, verifies **AC-4**.

## Group C: feature-9 / 9-profile-entry-done (a different scope row than the example's)

### Entities

10 evenly spaced through after run 1's located order.

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

### Relationships

5 evenly spaced through the 34 distinct links the three after runs wrote.

- [ ] agree / disagree · unclassified · written by 2 of 3 runs
  - source: `feature-9#9-profile-entry-done:3` AcceptanceCriterion: **Done when:** a signed in user can create and edit their profile, it survives a reload, validation errors are shown rather than swallowed, the saved shape is exactly what scoring will later read, and the profile form's Server Action is driven once from a test with no browser.
  - target: reference `0001` (whole record), mention: spec 0001's third runner constraint
  - phrase: That last clause is spec 0001's third runner constraint, deferred to here by spec 0004
  - flags: relationship_type_ambiguous
  - source text:
    > ### 9. Profile entry · done
    > A form for the flat profile: personal details, skills, one layer of work history, and stated job preferences. Typed by hand, with no resume upload and no extraction, so it makes no external call at all. Scoring cannot function without this, and the completion test does not start without a way to get profile data in.
    > **Done when:** a signed in user can create and edit their profile, it survives a reload, validation errors are shown rather than swallowed, the saved shape is exactly what scoring will later read, and the profile form's Server Action is driven once from a test with no browser. That last clause is spec 0001's third runner constraint, deferred to here by spec 0004 because there was no real write path to drive at feature 8; the technique is recorded in that spec's follow up list. Also, this feature moves its own claim (`profile`) from planned to working in the entry page's "What's real today" card (spec 0006, **AC-8**). It also **closes the deferred half of spec [0007](../specs/0007-auth-and-per-user-isolation/index.md) AC-15**: two real accounts, on the running app, each reading their OWN profile and not the other's. Feature 7 proved only the negative half, that neither account reaches the other's data, because at that point no `profile` row existed for anyone and both signed in users landed on the same named `record_not_found`. AC-15's wording assumes rows are there to be isolated, and this is the feature that first makes that true, so the proof lands here rather than being re run against the fixture pool it was written to go beyond.
    > _spec [0010](../specs/0010-profile-entry/index.md) · code in `src/features/profile/`, `src/app/(app)/profile/`, `src/components/ui/`, proofs in `test/integration/profile-form.test.ts`_
- [ ] agree / disagree · satisfies · written by 3 of 3 runs
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
- [ ] agree / disagree · satisfies · written by 3 of 3 runs
  - source: `feature-9#9-profile-entry-done:10` BuildStep: Thicken: skills (the diff based save) and work history (per entry add, edit, delete with a confirmation step) · AC-5 to AC-8, AC-7a
  - target: reference `0010` AC-5, mention: AC-5 to AC-8, AC-7a
  - phrase: AC-5 to AC-8, AC-7a
  - source text:
    > - [x] Build it: `/develop profile entry`
    >   - [x] Four new base components (`Input`, `Textarea`, `Select`, a `Field`/`Label` wrapper) added to `src/components/ui/`, extending spec 0005's inventory the way spec 0006 added `Logo` · AC-17
    >   - [x] Thin slice: the identity section end to end (create, reload, edit) via `saveIdentity` and the URL driven `/profile` page · AC-1 to AC-4, AC-11 to AC-14
    >   - [x] Thicken: skills (the diff based save) and work history (per entry add, edit, delete with a confirmation step) · AC-5 to AC-8, AC-7a
    >   - [x] Thicken: search preferences, the new spans registered, and the entry page's `profile` claim moved to working · AC-9, AC-10, AC-16
    >   - [x] Proofs: the no browser Server Action test, two account isolation, and the `/ui-preview` keyboard/focus/contrast pass · AC-14, AC-15, AC-17
- [ ] agree / disagree · satisfies · written by 3 of 3 runs
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
- [ ] agree / disagree · unclassified · written by 1 of 3 runs
  - source: `feature-9#9-profile-entry-done:3` Constraint: That last clause is spec 0001's third runner constraint, deferred to here by spec 0004.
  - target: reference `0001` label `third runner constraint`, mention: spec 0001's third runner constraint
  - phrase: spec 0001's third runner constraint
  - flags: relationship_type_ambiguous
  - source text:
    > ### 9. Profile entry · done
    > A form for the flat profile: personal details, skills, one layer of work history, and stated job preferences. Typed by hand, with no resume upload and no extraction, so it makes no external call at all. Scoring cannot function without this, and the completion test does not start without a way to get profile data in.
    > **Done when:** a signed in user can create and edit their profile, it survives a reload, validation errors are shown rather than swallowed, the saved shape is exactly what scoring will later read, and the profile form's Server Action is driven once from a test with no browser. That last clause is spec 0001's third runner constraint, deferred to here by spec 0004 because there was no real write path to drive at feature 8; the technique is recorded in that spec's follow up list. Also, this feature moves its own claim (`profile`) from planned to working in the entry page's "What's real today" card (spec 0006, **AC-8**). It also **closes the deferred half of spec [0007](../specs/0007-auth-and-per-user-isolation/index.md) AC-15**: two real accounts, on the running app, each reading their OWN profile and not the other's. Feature 7 proved only the negative half, that neither account reaches the other's data, because at that point no `profile` row existed for anyone and both signed in users landed on the same named `record_not_found`. AC-15's wording assumes rows are there to be isolated, and this is the feature that first makes that true, so the proof lands here rather than being re run against the fixture pool it was written to go beyond.
    > _spec [0010](../specs/0010-profile-entry/index.md) · code in `src/features/profile/`, `src/app/(app)/profile/`, `src/components/ui/`, proofs in `test/integration/profile-form.test.ts`_
