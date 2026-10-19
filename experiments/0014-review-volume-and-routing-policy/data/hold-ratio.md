# Accept to review ratio (spec 0008 AC-7)

Routing rebuilt from `artifacts/runs/` at 8c778e960d74667f9749355619b12f8f5ef372dc, without the narrow hold rule, no code pass, 29 units.

Note (2026-10-18): this line said "default routing"; the default has had the narrow hold rule on since cb28c68 (526 rows), and these tables measure routing without it (990 rows).

Per unit kind:

| unit kind | accepted entities | held entity rows | held link rows | held rows | accepted : held |
|---|---|---|---|---|---|
| Binding rules | 6 | 15 | 23 | 38 | 1 : 6.33 |
| Build plan | 5 | 4 | 16 | 20 | 1 : 4.00 |
| Consequences | 10 | 42 | 28 | 70 | 1 : 7.00 |
| Decision | 2 | 16 | 6 | 22 | 1 : 11.00 |
| Feature design | 88 | 229 | 123 | 352 | 1 : 4.00 |
| Follow-up | 7 | 20 | 25 | 45 | 1 : 6.43 |
| Preamble | 0 | 0 | 11 | 11 | no accepted entities |
| Requirements | 105 | 163 | 150 | 313 | 1 : 2.98 |
| Resolved | 0 | 9 | 11 | 20 | no accepted entities |
| Summary | 2 | 4 | 3 | 7 | 1 : 3.50 |
| scope row | 12 | 33 | 59 | 92 | 1 : 7.67 |
| **total** | 237 | 535 | 455 | 990 | 1 : 4.18 |

Per unit:

| unit (kind) | accepted entities | held entity rows | held link rows | held rows | accepted : held |
|---|---|---|---|---|---|
| 0001 Binding rules (Binding rules) | 6 | 15 | 23 | 38 | 1 : 6.33 |
| 0002 Feature design (Feature design) | 21 | 77 | 43 | 120 | 1 : 5.71 |
| 0002 Requirements (Requirements) | 10 | 14 | 4 | 18 | 1 : 1.80 |
| 0003 Requirements (Requirements) | 7 | 13 | 5 | 18 | 1 : 2.57 |
| 0006 Feature design (Feature design) | 25 | 42 | 15 | 57 | 1 : 2.28 |
| 0007 Consequences (Consequences) | 3 | 33 | 26 | 59 | 1 : 19.67 |
| 0007 Feature design (Feature design) | 15 | 59 | 32 | 91 | 1 : 6.07 |
| 0007 Follow-up (Follow-up) | 3 | 13 | 23 | 36 | 1 : 12.00 |
| 0007 Requirements (Requirements) | 8 | 19 | 10 | 29 | 1 : 3.62 |
| 0008 Preamble (Preamble) | 0 | 0 | 11 | 11 | no accepted entities |
| 0008 Requirements (Requirements) | 7 | 31 | 39 | 70 | 1 : 10.00 |
| 0009 Requirements (Requirements) | 19 | 10 | 6 | 16 | 1 : 0.84 |
| 0009 Summary (Summary) | 2 | 4 | 3 | 7 | 1 : 3.50 |
| 0011 Requirements (Requirements) | 7 | 12 | 14 | 26 | 1 : 3.71 |
| 0012 Build plan (Build plan) | 5 | 4 | 16 | 20 | 1 : 4.00 |
| 0012 Consequences (Consequences) | 7 | 9 | 2 | 11 | 1 : 1.57 |
| 0012 Follow-up (Follow-up) | 4 | 7 | 2 | 9 | 1 : 2.25 |
| 0012 Requirements (Requirements) | 10 | 4 | 2 | 6 | 1 : 0.60 |
| 0013 Feature design (Feature design) | 18 | 20 | 10 | 30 | 1 : 1.67 |
| 0013 Requirements (Requirements) | 11 | 5 | 4 | 9 | 1 : 0.82 |
| 0014 Decision (Decision) | 2 | 16 | 6 | 22 | 1 : 11.00 |
| 0014 Requirements (Requirements) | 10 | 17 | 15 | 32 | 1 : 3.20 |
| 0015 Feature design (Feature design) | 9 | 31 | 23 | 54 | 1 : 6.00 |
| 0015 Requirements (Requirements) | 10 | 11 | 7 | 18 | 1 : 1.80 |
| 0021 Requirements (Requirements) | 6 | 27 | 44 | 71 | 1 : 11.83 |
| feature-21 21. Terms & privacy notices · done · Alpha (scope row) | 5 | 11 | 21 | 32 | 1 : 6.40 |
| feature-33 33. Band anchor review · done (scope row) | 1 | 12 | 22 | 34 | 1 : 34.00 |
| feature-9 9. Profile entry · done (scope row) | 6 | 10 | 16 | 26 | 1 : 4.33 |
| scope Resolved (Resolved) | 0 | 9 | 11 | 20 | no accepted entities |
| **total** | 237 | 535 | 455 | 990 | 1 : 4.18 |
