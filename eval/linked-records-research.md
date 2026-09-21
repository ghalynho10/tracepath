# Five "why does X work this way" questions that cross more than one record

Research only, drawn from `docs/` of the JobHunt repo on 2026-09-18, at commit `2e40bcf` (the spec 0009 cookie disclosure correction). Every quote below was read from the file named, at the line named, in this session. Paths are repo relative.

---

## 1. Exactly two records

**Question**: Why does the landing rule's profile existence read (`src/lib/landing-rule.ts`) have its own dedicated query instead of reusing `readOwnProfile()`, which already reads the same row?

**Why one spec is not enough**: spec 0008 says "don't reuse it" and names the consequence, but the reason `readOwnProfile()` behaves that way is a deliberate decision recorded two specs earlier. Reading 0008 alone, the missing row reporting to Sentry looks like an accident to be fixed rather than a contract to work around.

**Trace**:

1. **Spec 0008, AC-7** (`docs/specs/0008-app-shell-and-navigation/index.md`, line 54)
   > "The landing rule reads profile row existence through a dedicated existence read. **An absent row is not a failure**: it returns `false` and constructs no `failure()`. It does not reuse `readOwnProfile()` in `src/features/profile/queries.ts:162-166`, whose `record_not_found` path reports to Sentry and marks the `profile.read` span failed. A first time sign in is the expected case and must not move the failure ratio feature 9 will alert on."

2. **Spec 0003, AC-14** (`docs/specs/0003-data-model/index.md`, line 34), which is why `readOwnProfile()` treats a missing row as a visible failure in the first place:
   > "The health page reads the caller's own `profile` through the real server client under a real policy. Each of the two seeded development users with a profile sees only their own row, and a third seeded user, deliberately given no profile row, sees a visible expected failure naming the missing profile rather than an empty page."

   Spec 0007 confirms that this is the same `record_not_found` (`docs/specs/0007-auth-and-per-user-isolation/index.md`, line 307): "They land on `/health` and see the `record_not_found` that spec 0003 **AC-14** exists to prove."

**Answer in one line**: `readOwnProfile()` reports a missing row on purpose (0003 AC-14, the health page must never show an empty page that reads like success), and a first sign in always has a missing row, so a second read that treats absence as a plain `false` was needed to keep the alert ratio honest (0008 AC-7).

**Confidence**: High. Both quotes are read directly, and the 0007 line 307 cross reference confirms the two records are describing the same failure path rather than two coincidentally similar ones. The one thing I did not verify is the code itself (`src/features/profile/queries.ts:162-166`); the question was about the records, so I stayed in `docs/`.

---

## 2. Four records deep

**Question**: Why does `src/proxy.ts` treat a Server Action request differently from every other request, and why does it detect one by the `next-action` header rather than by looking at the route?

**Why it takes four**: the number being protected lives in spec 0011, the bug that forced the change is measured in spec 0014, the fix is specified in spec 0008, and the constraint that dictates *how* the fix may be written (header, never route) is spec 0001's binding rule and its amendment. Each record assumes the previous one.

**Trace**:

1. **Spec 0011, AC-12** (`docs/specs/0011-usage-gating-and-kill-switch/index.md`, line 37), the budget at stake:
   > "The three cap values (25 per account per week, 66 app wide per day, 2000 app wide per month, for `job_search`) live in a database configuration table editable with no deploy, not as a literal in code, matching the kill switch's own no deploy operating model."

2. **Spec 0014, Decision, item 2** (`docs/specs/0014-apply-redirect-and-application-record/index.md`, line 69), the measured bug: a re-render of `/search` spends one of those calls, and the action could not stop it from inside itself:
   > "A cookie mutated during the action's request. This is the one nobody writes on purpose, and revision 3 found only half of it. The half it found: the shared cookie adapter writes cookies, so a session refresh inside the action's own caller check would trigger one, prevented by AC-20's read only adapter. **The half it missed, and the one that actually fired: `src/proxy.ts` runs on the action `POST` too, and refreshes there.** An action cannot defend against that from inside itself, however carefully it builds its own client. Prevented by AC-20a."

   And **AC-20a** on line 51: "`src/proxy.ts` **withholds the refreshed session cookie from the response of a Server Action request**, while still handing the refreshed value to that request's own code through `request.cookies.set()`, so `recordApplication` can verify its caller. The branch keys on the presence of Next's `next-action` request header, never on the route, so binding rule 6's mechanical guard is untouched: the proxy still cannot tell a protected path from a public one. This is the criterion the 25 weekly Adzuna calls actually rest on."

3. **Spec 0008, AC-10b** (`docs/specs/0008-app-shell-and-navigation/index.md`, line 62), where the fix is specified against the proxy's own spec:
   > "**On a Server Action request the refreshed session cookie is withheld from the response**, while the forwarded request still carries it so that request's own code can verify its caller. Added 2026-09-05 by spec [0014] AC-20a, after a measured bug [...] The branch keys on Next's `next-action` request header, **never on the route**, so AC-9's guard is untouched and the proxy still cannot tell a protected path from a public one. This is the one place the proxy treats two requests differently, and the difference is request kind, not destination."

4. **Spec 0001, binding rule 6 and its amendment, item Three** (`docs/specs/0001-stack-and-architecture/index.md`, lines 133 and 143), which is why "never on the route" is a hard constraint and not a style choice:
   > line 133: "**6. Authorisation is never decided in the proxy.** The proxy (`src/proxy.ts`, the file Next.js called `middleware.ts` before 16) refreshes the Supabase session cookie and does nothing else."

   > line 143: "**Three, added 2026-09-05 by spec [0014] AC-20a [...] "Refreshes the Supabase session cookie" now carries one exception about where the refresh lands.** [...] The reason is not authorisation, it is cost: a cookie mutated during an action makes Next re-render the current route into the action's response, and on `/search` that re-render re-runs the Adzuna search and spends one of the 25 weekly calls spec [0011] rations. **The substance of this rule is untouched, and the same mechanical test decides it.** The branch keys on Next's `next-action` request header, never on the path, so the proxy still reads no session for a decision, still holds no list of routes, and still cannot tell a protected path from a public one. `src/proxy.test.ts` lines 49 to 62 and 64 to 70 both still pass unmodified"

**Answer in one line**: an apply on `/search` was measured spending an Adzuna call because the proxy's cookie refresh on the action `POST` forced a re-render (0014); the proxy now withholds that cookie from action responses (0008 AC-10b); it must recognise an action by request kind and never by path because binding rule 6 forbids the proxy from knowing routes, and two unmodified `proxy.test.ts` assertions are the mechanical guard on that (0001).

**Confidence**: High on the chain and the quotes. I did not open `src/proxy.ts` or `src/proxy.test.ts` to confirm lines 49 to 62 still hold those assertions; three separate records claim it and I am reporting the records, not re-verifying the code. If you want to be certain the chain is still live, that file is the thing to check.

---

## 3. Depends on a superseded acceptance criterion

**Question**: Why is password sign in impossible on production?

**Why the superseded record matters**: spec 0002 AC-10 gives a complete, confident, and now wrong answer. Someone reading only the original criterion (or the config table's original wording) would say "because `DEV_SESSION_ENABLED` is absent on production and two guards fail closed". Neither guard exists any more. The correct answer needs the strike-through and the note that replaces it.

**Trace**:

1. **Spec 0002, AC-10, struck** (`docs/specs/0002-deployment-and-environments/index.md`, line 31), the old answer and the note that retires it:
   > "~~Password sign in is impossible on production, in both places it is guarded: the sign in page does not render and the Server Action refuses to run. The enabling variable is absent there, both guards fail closed, and neither depends any longer on how a build labels `NODE_ENV`.~~ · **SUPERSEDED 2026-08-30 by spec [0007].** Kept rather than deleted, because it was met as written and the reason it stopped applying is worth reading. Feature 7 deleted the password path outright, page and action alike, so password sign in is now impossible in EVERY environment rather than blocked in one, and there are no two guards left to fail closed. [...] What survives from it is the fail closed default itself, which is now the session mint's guarantee (spec 0007 **AC-13**)."

2. **Spec 0007, AC-12 and key invariant 1** (`docs/specs/0007-auth-and-per-user-isolation/index.md`, lines 35 and 142), the replacement mechanism:
   > AC-12: "`src/features/dev-session/` no longer exists, `signInWithDevPassword` no longer exists, `src/lib/supabase/browser.ts` no longer exists, and `/sign-in` renders the real page in every environment rather than a 404 outside development."

   > invariant 1: "**No password path exists anywhere in the product.** Not disabled, not flagged, absent. The only remaining credential path is the test mint, which lives outside `src/` and is guarded by `DEV_SESSION_ENABLED`."

3. **Spec 0007, AC-13** (same file, line 36), where the variable the old answer leaned on now lives:
   > "`DEV_SESSION_ENABLED` survives with exactly one remaining job, guarding the test mint in `test/helpers/admin.ts`. It is no longer set on Vercel Preview, `src/env.ts`'s comment about it says so, and spec 0002's configuration table matches."

4. **Spec 0002, the test scenario, struck** (`docs/specs/0002-deployment-and-environments/index.md`, line 232), which shows the old proof can no longer even be run:
   > "~~a POST to the sign in action on production is refused because `DEV_SESSION_ENABLED` is absent, verifies **AC-10**~~ · **UNRUNNABLE SINCE 2026-08-30**, and see AC-10 above. Spec [0007] deleted the Server Action this scenario posts to, so there is nothing left to refuse. Struck rather than rewritten because the property it tested, that no environment can accept a password, stopped being a guard and became structural: the code path does not exist. Spec 0007's own `verify.md` greps for its absence instead."

**Answer in one line**: not because an environment variable is unset on production (that was true until 2026-08-30 and is the answer spec 0002 AC-10 still gives if you skip the strike-through), but because feature 7 deleted the password page and action from the codebase entirely, so the property holds in every environment and is proved by grepping for absence; `DEV_SESSION_ENABLED` now guards only the test mint.

**Confidence**: High. The supersession is marked in three places in spec 0002 (AC-10 line 31, the config table rows at lines 161 and 194, the scenario at line 232) and I read all three; they agree with each other and with spec 0007. Note the two amendment dates differ (line 31 and 161 say 2026-08-30, line 194 says 2026-08-29); that is a wording inconsistency in the record, not a contradiction in substance.

---

## 4. A sensible "why" with no documented connection

**Question**: Why is the return path cookie's max age 10 minutes? Is it matched to the lifetime of the PKCE code verifier cookie that Supabase writes on the same sign in action, or to the session policy spec 0007 AC-19 records?

**Why it sounds like it should connect**: both cookies are written during the same provider Server Action, both exist only to survive the round trip to Google or GitHub and back to `/auth/callback`, and spec 0007 AC-4 goes out of its way to describe the verifier cookie's host scoping. A matched lifetime would be the natural design, and a reader would expect the number to be derived from it.

**What I checked, and what each place actually says**:

- `docs/specs/0008-app-shell-and-navigation/index.md` line 67 (AC-14): states the value, "with a max age of 10 minutes", and gives no derivation.
- `docs/specs/0008-app-shell-and-navigation/index.md` line 162 (Feature design): "10 minute max age, and `Path` scoped to the callback so it is not carried on ordinary navigation." The `SameSite=Lax` choice on the same line gets a reason; the 10 minutes does not.
- `docs/specs/0008-app-shell-and-navigation/rationale.md`: `grep -n -i "max age\|maxAge\|ten minute\|10 min"` returns no match.
- `docs/specs/0007-auth-and-per-user-isolation/index.md` AC-4 (line 25 to 27): describes the verifier as "a **host only** cookie written on whichever host served the action" and says nothing about its lifetime. The AC-19 session policy table (lines 197 to 213) has rows for access token expiry (`3600`), timebox, inactivity timeout and reuse interval; no row mentions the verifier or any value near 600 seconds.
- `grep -rn -i "pkce" docs/specs/0007-auth-and-per-user-isolation/ docs/specs/0008-app-shell-and-navigation/ | grep -i "minute\|lifetime\|expir\|max"` returns nothing.
- `grep -rn -i "ten minute\|10 minute\|10-minute\|max age of 10\|maxAge: 600\|verifier.*lifetime\|verifier.*expir\|code_verifier" docs/ src/features/auth src/lib/return-path.ts src/proxy.ts` returns exactly four hits: the two spec 0008 lines above, `src/features/auth/actions.test.ts:528` (asserts `maxAge: 600`, no reason), and `src/lib/return-path.ts:58`.
- `src/lib/return-path.ts` lines 58 to 61, the one place a reason is written: "Ten minutes, in seconds. Long enough for a provider consent screen and a password manager, short enough that a stale value cannot sit around." That is a human timescale argument. It does not mention the verifier, the session policy, or Supabase.
- `docs/specs/0009-terms-and-privacy-notices/index.md` line 286 uses `"10 minutes"` as an example `lifetime` string for the cookie registry added today; it records the value for disclosure and derives nothing.
- `docs/reviews/2026-08-31-spec-0008-app-shell-and-navigation.md`: the cross model review of spec 0008 discusses the cookie's `Path` and the length cap (line 241) and does not question the 10 minutes.

**Conclusion**: the number is documented, and one reason for it is documented in code, but nothing in `docs/` or the auth code links it to the PKCE verifier's lifetime or to spec 0007's session policy. As far as the record shows, the two lifetimes are independent choices that happen to coexist on one request. If someone later changes Supabase's verifier expiry, nothing in the repo says the return cookie should move with it, and nothing says it should not.

**Confidence**: High that the connection is undocumented, because the greps above are the exact commands run and their scope covers every spec, review and the three source files involved. I did not check Supabase's own documentation for what the verifier lifetime actually is, so I cannot tell you whether the two numbers happen to be equal in practice; I can only tell you the repo never says.

---

## 5. My own pick: a scheduling decision driven by an external meter, recorded as a cross-row correction

**Question**: Why was feature 21 (terms and privacy notices) built in Foundation, immediately after feature 32, when it was originally scoped into Slice 5 as launch readiness work?

**What makes this different from the other four**: it is not an amendment to a mechanism or a superseded criterion. It is a *scheduling* decision, forced by a counter outside the repo (Google's lifetime OAuth user cap), discovered while building an unrelated feature (7), and recorded by one spec explicitly *not* being allowed to edit the other feature's scope row, so the correction is split across a spec follow-up, a `/scope` edit, the scope's `## Resolved` list, and the new spec's summary. It is also a "blocked on" chain in both directions: feature 21 was blocked on the custom domain, and Google's publish step was blocked on feature 21.

**Trace**:

1. **Spec 0007, Consequences** (`docs/specs/0007-auth-and-per-user-isolation/index.md`, line 313), where the meter is discovered and the scope gap named:
   > "**Leaving Google's Testing mode is gated on feature 21, and the meter only runs one way.** Publish app is greyed because the privacy policy and terms of service links are empty, and feature 21 (Terms and privacy notices) is what produces them. Until then the app is capped at 100 users, and Google counts that cap "over the entire lifetime of the app", so it never goes back down. [...] **Updated 2026-08-31**: when this was written feature 21 sat in Slice 5 and neither scope row recorded the dependency. Both changed on the strength of this paragraph. The dependency is now on feature 21's row, and the feature moved to Foundation, to be built after feature 32, precisely because a meter counted over the app's lifetime is not something to leave until launch readiness."

2. **Spec 0007, Follow-up** (same file, lines 335 and 336), the domain constraint and the ticked item that says who was allowed to make the edit:
   > line 335: "**Publishing and verifying the Google app is the remaining fix for the consent screen**, and it is gated on feature 21 supplying a privacy policy and terms served from `usejobhunt.dev`. That is now possible where it was not before: Google would not accept a `vercel.app` address as an Authorized domain, and it will accept this one."

   > line 336: "[x] **Feature 21 and feature 7 depend on each other and neither scope row says so.** [...] Recording it on feature 21's row is a `/scope` edit, since `/architect` may not edit another feature's contents. · **Done 2026-08-31.** Feature 21's row now carries the dependency in both directions [...] It also went further than this item asked: the feature moved out of Slice 5 into Foundation, to be built after feature 32, because the cap is counted over the app's whole lifetime and every sign in before those pages exist spends a slot permanently."

3. **scope.md, feature 21 row** (`docs/scope/scope.md`, lines 176 to 180), the other side of that edit:
   > line 176: "### 21. Terms & privacy notices · done · Alpha"

   > line 179: "_Moved here from Slice 5 on 2026-08-31, to build after feature 32. **The reason is a meter that only runs one way.** This feature is what lifts Google's 100 user cap [...] Every person who signs in before these pages exist spends one of those slots permanently, which is why waiting until launch readiness was the wrong place for it. The pages must be served from `usejobhunt.dev`, because Google will not accept a `vercel.app` address as an authorised domain. Publishing is also the remaining fix for the consent screen naming a Supabase host instead of JobHunt._"

   > line 180: "_Depends on feature 7, both ways, recorded from spec [0007] on 2026-08-31. Feature 7 is what makes these notices load bearing rather than paperwork: the privacy notice must describe what arrives from the provider into `auth.users`, meaning the email address, the display name and the avatar URL._"

4. **scope.md, `## Resolved`, custom domain** (`docs/scope/scope.md`, lines 516 to 528), the prerequisite that had to land first and the closure feature 21 provided:
   > "**Custom domain**: **done 2026-08-30.** The production origin moved from `https://usejobhunt.vercel.app` to `https://usejobhunt.dev`. [...] **What it did not fix, and what since did**: Google's consent screen read the Supabase host, because that is the OAuth redirect host and the domain move did not touch it. **Closed on 2026-09-01 by feature 21**, which published a privacy policy and terms on `usejobhunt.dev`, letting the app register that Authorized domain, leave Testing and submit brand verification. Confirmed by starting a real sign in against production: the screen now reads "to continue to JobHunt"."

5. **Spec 0009, Summary** (`docs/specs/0009-terms-and-privacy-notices/index.md`, lines 17 to 22), the resulting spec stating its own second purpose:
   > "Two public pages, `/terms` and `/privacy`, written against what this codebase actually stores and actually sends to other companies, rather than from a template. They exist to be true, and they exist to unblock Google: the OAuth app is stuck in Testing because the console's privacy policy and terms fields are empty, and Testing is capped at 100 users counted over the app's whole lifetime."

**Answer in one line**: because Google's Testing mode caps the app at 100 users counted over its whole lifetime and never resets, every sign in before the privacy and terms pages exist permanently spends a slot, so the pages could not wait for launch readiness; they also could not be served from `vercel.app`, which is why the custom domain (resolved 2026-08-30) had to precede them, and the whole chain was recorded across two documents because spec 0007 was not permitted to edit feature 21's row itself.

**Confidence**: High on every quoted step. One thing worth your eye: scope.md line 176 tags the feature "Alpha" while the row's own prose and spec 0009 say it was built in Foundation after feature 32; I did not chase what "Alpha" means in this repo's legend, so if the slice label matters to your research, check the scope legend before relying on it.

---

## Notes on method

- Every quote was read from the file at the stated line in this session; nothing is from memory.
- Working tree was clean at the time of reading (`git status --short` empty), so all quotes are from committed content at `2e40bcf`.
- The initial session snapshot listed spec 0009's `index.md` and `rationale.md` as modified; by the time the files were read they had been committed (`2e40bcf`, 2026-09-18, "docs(spec): correct spec 0009's cookie disclosure and add AC-24's drift guard"). No quote here depends on an uncommitted edit.
- No code was built and nothing in the repo was changed.
