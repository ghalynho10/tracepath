# Check verify, answer gallery, 2026-10-24

**Run by**: `/check verify`, Claude Opus 5.5, on branch `feat/answer-gallery` at `fdd9ccb`
**Spec**: [0010](../specs/0010-answer-gallery/index.md), checked against its [verify.md](../specs/0010-answer-gallery/verify.md)
**Verdict**: **pass before merge, one step blocked until merge**. All 62 criteria were met in a real run in this session. The one step that cannot run yet is the public URL check (verify.md, Commands, last step; build plan task 2), because the Pages workflow only exists on this branch. Nothing failed. Three small findings are listed below; none blocks the merge.

This is a runtime check, not a code review. No code was changed, no paid call was made, `eval/held-out.json` was never opened (the copy below was made without it), and the checkout's working tree was left clean.

How it was run:

- The page: `uv run tracepath gallery build --out /tmp/tracepath-gallery`, served from that folder on `127.0.0.1:8765` (the browser refuses `file:` addresses), and driven with Playwright at 1440 by 900 and 390 by 844.
- The failure cases: on a copy of the repo in the session scratch area (no `.git`, no `.env`, no `reference/`, no `eval/held-out.json`), one fresh copy per case, built with this branch's `tracepath` binary.
- Each entry against its record: a script that reads every record and `gallery/marks.json`, works out each claim's labels and the failed tally from the spec's rules on its own (not by calling the code), and compares them with the built page. It was checked against two altered pages and caught both changes, so it is not passing by default.

## Evidence

- **E1** Build: `uv run tracepath gallery build --out /tmp/tracepath-gallery`, exit 0 → `✓ 31 entries → /tmp/tracepath-gallery/index.html`. The folder holds `index.html` only (775.5K).
- **E2** No key, no database, no network: in the copy (no `.env`), `sandbox-exec -p '(version 1)(allow default)(deny network*)' tracepath gallery build`, exit 0, page byte identical to E1 (`cmp`). The same sandbox makes `curl https://github.com` fail (`Could not resolve host`), so the block was real. Neo4j was left running rather than stopped, since the network block is the stronger check. `env -i PATH HOME uv run tracepath gallery build` in the checkout also exits 0 with an identical page.
- **E3** Never writes inside `artifacts/` or `corpus/`: `git status --short artifacts/ corpus/` after E1 → empty. `--out artifacts/site`, `--out corpus/site` and `--out artifacts` each exit 1 → `✗ --out artifacts/site: the build never writes inside artifacts/` (and the same for the others); neither folder exists afterwards.
- **E4** Self contained: `grep -c '<link\|<script'` → `0`; every `href` is `https://` (2570 into JobHunt, 34 into tracepath); no `@import` and no `url(`. In the browser, 0 `script` or `link` elements; the only console error is the local server's `favicon.ico` 404, which the page never asks for.
- **E5** Failure builds, each on its own copy, all exit 1 with no `index.html` written:

  | Case | Message |
  |---|---|
  | AC-5, entry 2 names `no-such-record.json` | `gallery/marks.json: entry 2 (Eval 2) names no-such-record.json, which is not in artifacts/asks/` |
  | AC-6, Eval 1 `eval_file` = `eval/other.json` | `…research-q1.json: eval_file 'eval/other.json' is not one the gallery shows` |
  | AC-7, Eval 1 `corpus_commit` = `abcdef1` | `…q1.json: corpus_commit 'abcdef1' is not the pinned commit 2e40bcfe…` |
  | AC-10, `source_row` removed from entry 3 | `gallery/marks.json: entry 3 (…q3.json): source_row: Field required` |
  | AC-10, `note` removed from entry 1 | `… entry 1 (…q1.json): note: Field required` |
  | AC-11, `mark` = `mostly right` | `… entry 1 (…q1.json): mark: Input should be 'right', 'partly right', 'wrong' or 'declined'` |
  | AC-37, three spaces before `accepted` | `…q1.json: item 0008/AC-7: stored line '…' has no known shape` |
  | AC-38, cited item at `specs/no-such/index.md:3` | `…q1.json: item 0008/AC-7: specs/no-such/index.md is not in corpus/jobhunt/docs/` |
  | AC-38, an item that is not cited, same file | `…q1.json: item 0008#feature-design:11: specs/no-such/index.md is not in corpus/jobhunt/docs/` |
  | AC-39, line `0` | `… line 0 is outside specs/0008-app-shell-and-navigation/index.md (lines 1 to 264)` |
  | AC-39, line `265` | `… line 265 is outside … (lines 1 to 264)` |
  | AC-40, claim 1 also cites `9999/AC-1` | `…q1.json: a claim cites 9999/AC-1, which is neither among the record's items nor in the claim's rejected_ids` |
  | AC-42, cited item at `no file stored` | `…q1.json: item 0008/AC-7 is cited but has no stored file or path` |

- **E6** The matching passes, each exit 0, `✓ 31 entries`: the full commit `2e40bcfe1078cc93ab2f951e6c7c708e4825aa1b` in `corpus_commit` (page byte identical to E1); line `264`, the last line, links `#L264`; `9999/AC-1` cited and also in `rejected_ids` shows `CITATION REJECTED: 9999/AC-1` with no link, and the verdict line adds `; 1 of 4 claims failed a check`.
- **E7** Labels the real page has no case of, in a copy: Eval 1 claim 1 made uncited, claim 2 citing only a rejected id, and an item that is not cited set to `no file stored`. Exit 0. Verdict line `…answered; 2 of 4 claims failed a check`; claim 1 `UNCITED read from text`; claim 2 `Cites: 9999/X` (no link) and `CITATION REJECTED: 9999/X unsupported`; the item row `0008#feature-design:11 · Constraint · held · no file stored` with no link.
- **E8** Value sourcing, each on a copy, diffed against the E1 page:
  - Q3's question changed → only that text changes.
  - Q4's note changed → only that note changes.
  - `Q7` renamed `Q7b` → only that heading changes.
  - A dummy `zz-dummy.json` in `artifacts/asks/` → `holds 44 records` becomes `holds 45 records`, nothing else.
  - Q4's `eval_file` set to the linked records research file → Q4 moves to the end of Development questions.
- **E9** Every entry against its record (the script above), on the E1 page → `problems: 0` over 31 entries: heading, question, verdict, mark, note (or none when null), source link and row, `Asked <date> · prompt <version>[ · N hops]`, claim count, order and text, each cite shown and linked to the line its stored `line` gives, rejected ids unlinked, the failed tally, the missing notes, the Items sent count, each cited item's full stored text, each other item's `id · type · held or accepted[ · STRUCK or HISTORY]` row and its link. `held` marks after cited ids: 17. Labels seen on the real page: `HISTORY`, `INFERRED`, `link`, `read from text`. Markers seen in Items sent: `STRUCK`, `HISTORY`, and `whole file`.
- **E10** The page in the browser, 1440 wide:
  - 31 entries (33 `h3`, two of them the key's): Development questions Eval 1 to 5, Held out questions Held out 1 to 4, Realistic questions Q1 to Q22.
  - Intro: "Every citation points into JobHunt at commit 2e40bcf…", both links (repo, and `tree/2e40bcfe…`); "artifacts/asks/ holds 44 records. This page shows 31 of them: eval questions 1 to 5, held out questions 1 to 4, and experiment 0018's 22.", linked to `tracepath/tree/main/artifacts/asks`.
  - Development section: "…Earlier runs of eval questions 1 to 5 on prompt ask-1, from 2026-10-19: I also marked them right (v1 finish line)." `docs/scope/scope.md` line 55 reads "Eval questions 1 to 5: 5 of 5 right."
  - Held out section: "Asked once at the end of v1, never used to tune the tool."
  - Realistic section links `experiments/0018-realistic-usage-questions/README.md`.
  - Held out 3: "Asked 2026-10-19 · prompt ask-1" (no hops), "My mark: partly right", note word for word as `docs/scope/scope.md` line 56. Eval 1 and Q1 show no note.
  - Eval 1: "Asked 2026-10-20 · prompt ask-2 · 2 hops"; mark pill filled (`rgba(7,160,195,0.18)`, 1px solid border), verdict pill outlined (transparent, 1px border at 0.3 alpha). Screenshot `desktop-eval1-top.png`.
  - Q4 lists its missing note under "Missing, as the answer says"; Eval 1 shows none.
  - Held out 1 shows `` `<n>` `` as typed (escaped `&lt;n&gt;` in the source); 86 stored spans show `**` as typed; 0 `strong`, `b`, `em` or `code` inside any entry; Eval 4's cited `0007/AC-4` text keeps its 5 lines (`white-space: pre-wrap`).
  - All 31 Items sent folds closed on load (`details[open]` = 0). Opened: Eval 1 shows "Cited" then "Not cited", and the row `0021#feature-design:12 · Constraint · accepted · STRUCK · specs/0021-seeded-demo-account/index.md:314`; Eval 3 shows `0007 · record · accepted · specs/0007-auth-and-per-user-isolation/index.md, whole file`, linked with no `?plain=1` and no anchor.
  - Screenshots `desktop-top.png`, `desktop-heldout3.png`.
- **E11** 390 wide, every fold opened: `scrollWidth` 390 = viewport, no element past either edge; the key stacks each term above its meaning (term bottom 531, meaning top 535, both left 16). Screenshots `mobile-top.png`, `mobile-eval3-items.png`.
- **E12** Clicking Eval 1, claim 1, `0008/AC-7` opens `https://github.com/ghalynho10/JobHunt/blob/2e40bcfe…/docs/specs/0008-app-shell-and-navigation/index.md?plain=1#L54`, in the Code (plain text) view, line 54 highlighted, reading "**AC-7**: The landing rule reads profile row existence…". Screenshot `github-L54.png`. This settles the spec's open question on the `?plain=1` form.
- **E13** Pinned commit: `JOBHUNT_COMMIT = "2e40bcfe1078cc93ab2f951e6c7c708e4825aa1b"` in `src/tracepath/gallery/citations.py`, the same as `corpus/jobhunt/SNAPSHOT.md` line 8.
- **E14** `.github/workflows/pages.yml`: on `push` to `main` with exactly the seven paths of AC-61, plus `workflow_dispatch`; build job runs `uv run tracepath gallery build --out site`, then `configure-pages@v6` and `upload-pages-artifact@v5` with `path: site`; `deploy` has `needs: build`, `environment: github-pages`, `deploy-pages@v5`. All five action tags exist (`gh api repos/<action>/git/ref/tags/<tag>` → `refs/tags/v7`, `v7`, `v6`, `v5`, `v5`). `gh api repos/ghalynho10/tracepath/pages` → `"build_type":"workflow"`, so the Pages source is already set.
- **E15** `uv run pytest tests/test_gallery.py tests/test_gallery_citations.py tests/test_pages_workflow.py -q` → `101 passed in 6.67s`, including the socket blocking test for AC-56.

## Per criterion

| Criteria | Status | Evidence |
|---|---|---|
| AC-1 to AC-4, AC-8 | met | E9, E10 |
| AC-5 to AC-7 | met | E5, E6 |
| AC-9 to AC-11 | met | E5 |
| AC-12 to AC-16 | met | E9, E10 |
| AC-17 to AC-23 | met | E9, E10 |
| AC-24, AC-25 | met | E10 |
| AC-26 to AC-28, AC-32 | met on the real page | E9 |
| AC-29, AC-30, AC-31, AC-33 | met in a copy (no real entry has the case) | E6, E7 |
| AC-34, AC-35 | met | E9, E10, E12 |
| AC-36 | met in a copy | E7 |
| AC-37 to AC-40, AC-42 | met | E5 |
| AC-41 | met in a copy | E6, E7 |
| AC-43 | met | E13 |
| AC-44 to AC-48 | met | E9, E10 |
| AC-49 to AC-54 | met | E8, E10 |
| AC-55 to AC-58 | met | E1 to E4 |
| AC-59 to AC-62 | met in the workflow file | E14, E15 |
| Public URL shows 31 entries (build plan task 2) | **blocked until merge** | `curl https://ghalynho10.github.io/tracepath/` → 404, and `gh run list --workflow pages.yml` → "not found on the default branch" |

## Findings

None of these blocks the merge. Each is a recommendation you may take or skip.

1. **Claim labels and the details line are shown in capitals, so the page no longer matches its own key.** The DOM text is right (`read from text`, `link`, `prompt ask-2`), but CSS `text-transform: uppercase` on `p.labels` and `p.details` shows them as `READ FROM TEXT`, `HISTORY LINK` and `PROMPT ASK-2`. The key teaches flags in capitals (`HISTORY`, `INFERRED`) and the basis in lower case (`link`, `read from text`), and on a claim that distinction is gone: Held out 3, claim 4 reads `HISTORY LINK` as one phrase (`desktop-heldout3.png`). The stored prompt version also shows in a case it was never stored in. Seen on the real page, and a reader could misread it; the fix is one CSS rule. Route: `/develop` (or `/debug`) on `render.py`'s styles.
2. **Spec 0010's Configuration section names older action versions than the workflow uses.** The spec says `configure-pages@v5`, `upload-pages-artifact@v4`, `deploy-pages@v4`; the workflow uses `@v6`, `@v5`, `@v5` and `checkout@v7`, all of which exist (E14). The spec said the builder would recheck them, so the code is likely right and the spec text is stale. Route: `/sync` flags it, or a one line spec edit.
3. **The "v1 finish line" links open `docs/scope/scope.md` at the top.** The held out source links and the development section's link carry no anchor, so a reader has to find the section (the note sits at line 56 of a long file). Optional; `#v1-finish-line` would land them on it. It does not mislead, so skipping it is reasonable.

Also seen, no action suggested: error messages name an entry by its label for AC-5 (`entry 2 (Eval 2)`) but by its record file for AC-10 and AC-11 (`entry 1 (…q1.json)`). Both name the entry, as the spec asks.

## Not done in this run

- `verify.md` and the scope were not ticked. You asked for findings in `docs/reviews/` only, so the ticks are left for you to decide.
- The public URL step waits for the merge (see the table above).
