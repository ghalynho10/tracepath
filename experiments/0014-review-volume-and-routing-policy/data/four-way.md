# Four way comparison (spec 0008 AC-8 to AC-8f)

Run against `artifacts/runs/` at 8c778e960d74667f9749355619b12f8f5ef372dc; `--code-pass` off in every configuration; eval file `eval/linked-records-research.json`.

| Q | expected step | baseline | --with-held | --narrow-hold | both |
|---|---|---|---|---|---|
| 1 | spec 0008 AC-7 · specs/0008-app-shell-and-navigation/index.md:54 | not reached | reached only as held | reached as accepted (via release) | reached as accepted (via release) |
| 1 | spec 0003 AC-14 · specs/0003-data-model/index.md:34 | not reached | not reached | not reached | not reached |
| 2 | spec 0011 AC-12 · specs/0011-usage-gating-and-kill-switch/index.md:37 | reached as accepted | reached as accepted | reached as accepted | reached as accepted |
| 2 | spec 0014 Decision item 2 and AC-20a · specs/0014-apply-redirect-and-application-record/index.md:69 | not reached | not reached | not reached | not reached |
| 2 | spec 0014 Decision item 2 and AC-20a (also) · specs/0014-apply-redirect-and-application-record/index.md:51 | not reached | not reached | not reached | not reached |
| 2 | spec 0008 AC-10b · specs/0008-app-shell-and-navigation/index.md:62 | not reached | not reached | not reached | not reached |
| 2 | spec 0001 binding rule 6 and amendment item Three · specs/0001-stack-and-architecture/index.md:133 | not reached | not reached | not reached | not reached |
| 2 | spec 0001 binding rule 6 and amendment item Three (also) · specs/0001-stack-and-architecture/index.md:143 | not reached | not reached | not reached | not reached |
| 3 | spec 0002 AC-10 (struck) · specs/0002-deployment-and-environments/index.md:31 | not reached | reached only as held | reached as accepted (via release) | reached as accepted (via release) |
| 3 | spec 0007 AC-12 and key invariant 1 · specs/0007-auth-and-per-user-isolation/index.md:35 | not reached | not reached | not reached | not reached |
| 3 | spec 0007 AC-12 and key invariant 1 (also) · specs/0007-auth-and-per-user-isolation/index.md:142 | not reached | not reached | not reached | not reached |
| 3 | spec 0007 AC-13 · specs/0007-auth-and-per-user-isolation/index.md:36 | not reached | reached only as held | not reached | reached only as held (via release) |
| 3 | spec 0002 test scenario (struck) · specs/0002-deployment-and-environments/index.md:232 | not reached | reached only as held | reached as accepted (via release) | reached as accepted (via release) |
| 4 | spec 0007 AC-4 (absence item) · specs/0007-auth-and-per-user-isolation/index.md:25 | not reached | not reached | not reached | not reached |
| 4 | spec 0007 AC-19 (absence item) · specs/0007-auth-and-per-user-isolation/index.md:42 | not reached | not reached | not reached | not reached |
| 5 | spec 0007 Consequences · specs/0007-auth-and-per-user-isolation/index.md:313 | not reached | reached only as held | not reached | reached only as held |
| 5 | spec 0007 Follow-up · specs/0007-auth-and-per-user-isolation/index.md:335 | not reached | not reached | not reached | not reached |
| 5 | spec 0007 Follow-up (also) · specs/0007-auth-and-per-user-isolation/index.md:336 | not reached | not reached | not reached | not reached |
| 5 | scope.md feature 21 row · scope/scope.md:179 | not reached | not reached | not reached | not reached |
| 5 | scope.md feature 21 row (also) · scope/scope.md:180 | not reached | not reached | not reached | not reached |
| 5 | scope.md Resolved, custom domain · scope/scope.md:516 | not reached | not reached | not reached | not reached |
| 5 | spec 0009 Summary · specs/0009-terms-and-privacy-notices/index.md:17 | not reached | not reached | not reached | not reached |

Visited steps matching no expected item, all five questions summed (AC-8d):

| configuration | total | among held steps | among accepted steps |
|---|---|---|---|
| baseline | 0 | n/a | n/a |
| --with-held | 26 | 26 | 0 |
| --narrow-hold | 20 | n/a | n/a |
| both | 26 | 5 | 21 |

AC-8f, steps worse with both flags than the better single flag: none.
AC-9(a), steps newly reached as accepted under --narrow-hold: Q1 spec 0008 AC-7 · specs/0008-app-shell-and-navigation/index.md:54; Q3 spec 0002 AC-10 (struck) · specs/0002-deployment-and-environments/index.md:31; Q3 spec 0002 test scenario (struck) · specs/0002-deployment-and-environments/index.md:232.
AC-9(b), steps accepted at baseline and not under --narrow-hold: none.
AC-11, steps moving from not reached to reached only as held under --with-held: Q1 spec 0008 AC-7 · specs/0008-app-shell-and-navigation/index.md:54; Q3 spec 0002 AC-10 (struck) · specs/0002-deployment-and-environments/index.md:31; Q3 spec 0007 AC-13 · specs/0007-auth-and-per-user-isolation/index.md:36; Q3 spec 0002 test scenario (struck) · specs/0002-deployment-and-environments/index.md:232; Q5 spec 0007 Consequences · specs/0007-auth-and-per-user-isolation/index.md:313.
