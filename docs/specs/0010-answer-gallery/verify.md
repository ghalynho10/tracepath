# Verify: answer gallery · spec 0010 · updated 2026-10-24
_Note 2026-10-26: steps here that name the old pill, the old verdict line ("Model's own verdict: answered"), "My mark", "Missing, as the answer says", the Graph button or a source link to `docs/` are superseded by spec 0012's `verify.md`._
_Steps derived from spec 0010 acceptance criteria and its Value sourcing table. `/check verify` runs these; `/test` locks the durable ones._

Build the page once for the UI steps: `uv run tracepath gallery build --out /tmp/gallery`, then open `/tmp/gallery/index.html` in a browser. No step makes a paid call, and none opens `eval/held-out.json`.

## Commands
- [ ] `uv run tracepath gallery build --out DIR` → writes `DIR/index.html`, prints `✓ 31 entries → …`, exits 0 → AC-55
- [ ] Run the build with no `.env` and no Neo4j (`env -i PATH="$PATH" HOME="$HOME" uv run tracepath gallery build --out DIR`) → exits 0 → AC-56, Security model
- [ ] `git status --short artifacts/ corpus/` after a build → nothing changed → AC-57
- [ ] `uv run tracepath gallery build --out artifacts/site` and `--out corpus/site` → exit 1, "never writes inside", no file written → AC-57
- [ ] `grep -c '<link\|<script[^>]*src' DIR/index.html` → 0, and every `href` is `https://…` → AC-58 _(amended 2026-10-27: inline `<script>` elements are allowed)_
- [ ] `grep -o 'preview.png' DIR/index.html | wc -l` → each hit sits in a `<meta>` tag, and no other file name of the site appears → AC-63, AC-64
- [ ] `head -c 2000 DIR/index.html` shows `og:title`, `og:url`, `og:image`, `og:image:width` (1200), `og:image:height` (627), `og:description` and `<meta name="description">` with the ruled content, all before the first `<style>`, and the two descriptions are equal → AC-65 to AC-72
- [ ] `file gallery/preview.png` → PNG, 1200 x 627, and `ls -l` → at most 5 MB → AC-73, AC-74
- [ ] `cmp gallery/preview.png DIR/preview.png` → no difference → AC-75
- [ ] In a copy of the repo, delete `gallery/preview.png` and build → exit 1 naming the file → AC-76
- [ ] The intro's first sentence reads "answers questions about a project's decisions from its specs and decision records" → AC-77
- [ ] After the merge and the Pages run, paste the live URL into LinkedIn's Post Inspector → title, description and image all show (not a criterion; the check the change is for)
- [ ] In a copy of the repo, point a `gallery/marks.json` entry at a record name not in `artifacts/asks/` → exit 1 naming the entry → AC-5
- [ ] In a copy, set a shown record's `eval_file` to `eval/other.json` → exit 1 naming the record → AC-6
- [ ] In a copy, set a shown record's `corpus_commit` to `abcdef1` → exit 1 naming the record; the full commit `2e40bcfe…` builds → AC-7
- [ ] In a copy, delete one field from a marks entry → exit 1 naming the entry and the field → AC-9, AC-10
- [ ] In a copy, set a `mark` to `mostly right` → exit 1 naming the entry → AC-11
- [ ] In a copy, put three spaces between two fields of an item's stored `line` → exit 1 naming the record and item → AC-37
- [ ] In a copy, point a linked item at `specs/no-such/index.md:3` → exit 1 naming the record and item → AC-38
- [ ] In a copy, set a cited item's line to `0`, then to a line past the end of its file → exit 1 each time → AC-39
- [ ] In a copy, add an id to a claim's `cites` that is not in the record's items → exit 1 naming the record and id → AC-40
- [ ] In a copy, change a cited item's location to `no file stored` → exit 1 naming the record and item → AC-42
- [ ] `grep JOBHUNT_COMMIT src/tracepath/gallery/citations.py` matches the commit in `corpus/jobhunt/SNAPSHOT.md` → AC-43
- [ ] `.github/workflows/pages.yml`: triggers on push to `main` and `workflow_dispatch`, builds with `tracepath gallery build --out site` → AC-59
- [ ] The same file uploads `site` with `upload-pages-artifact` and deploys with `deploy-pages` to the `github-pages` environment → AC-60
- [ ] Its `paths` list is exactly `artifacts/asks/**`, `gallery/**`, `src/tracepath/**`, `pyproject.toml`, `uv.lock`, `corpus/jobhunt/**`, `.github/workflows/pages.yml` → AC-61
- [ ] Its `deploy` job has `needs: build` → AC-62
- [ ] After the merge: the Pages workflow run on `main` succeeds, and https://ghalynho10.github.io/tracepath/ shows the page with 31 entries → AC-59, AC-60, build plan task 2

## UI / manual
- [ ] Count the entries → 31, one per `gallery/marks.json` entry, headed by its `label` → AC-1
- [ ] Eval 1 to 5 sit under "Development questions" → AC-2
- [ ] Held out 1 to 4 sit under "Held out questions" → AC-3
- [ ] Q1 to Q22 sit under "Realistic questions" → AC-4
- [ ] The held out section reads "Asked once at the end of v1, never used to tune the tool." → AC-8
- [ ] Held out 3 shows "My mark: partly right" and its note word for word from the v1 finish line → AC-12, AC-13
- [ ] Eval 1 and Q1 show no note → AC-13
- [ ] The mark is a filled pill reading "My mark", apart from the outlined "Model's own verdict" pill → AC-14, AC-15
- [ ] Q4's source line links to `experiments/0018-realistic-usage-questions/README.md` on GitHub and names row `Q4` → AC-16
- [ ] Eval 1's question, verdict and claims match its record, claims in stored order → AC-17, AC-18, AC-19
- [ ] Q4 lists the answer's missing notes; Eval 1 shows none → AC-20
- [ ] Eval 1 shows "Asked 2026-10-20 · prompt ask-2 · 2 hops"; Held out 3 shows "Asked 2026-10-19 · prompt ask-1" with no hops → AC-21, AC-22, AC-23
- [ ] Stored backticks and `**` show as typed, with no bold or code formatting; line breaks are kept → AC-24, AC-25
- [ ] A held cited id shows `held` after it (17 on the real page) → AC-26
- [ ] Claim labels match the record's stored fields (`HISTORY`, `INFERRED`, `link`, `read from text` on the real page) → AC-27 to AC-32
- [ ] No real entry has a failed check, so no verdict line shows "N of M claims failed a check" (the fixture tests cover the case) → AC-33
- [ ] Click Eval 1, claim 1, `0008/AC-7` → GitHub opens JobHunt at `2e40bcfe…`, `specs/0008-app-shell-and-navigation/index.md` as plain text, line 54 highlighted → AC-34
- [ ] Open Eval 3's Items sent: the `0007` record row links to its file with "whole file" and no line anchor → AC-35
- [ ] Every "Items sent" fold is closed when the page loads → AC-44
- [ ] Inside an opened fold, each cited item shows its full stored text → AC-45
- [ ] Each item that is not cited is one row: id · type · held or accepted · location link → AC-46, AC-48
- [ ] A row with `STRUCK` or `HISTORY` shows it (Eval 1: `0021#feature-design:12 … STRUCK`) → AC-47
- [ ] The intro says `artifacts/asks/` holds 44 records and links to the folder on GitHub → AC-49, AC-50
- [ ] The intro says it shows 31: eval questions 1 to 5, held out questions 1 to 4, and experiment 0018's 22 → AC-51
- [ ] The development section says the earlier ask-1 runs "I also marked them right", linking the v1 finish line → AC-52
- [ ] The realistic section links to experiment 0018's README → AC-53
- [ ] The intro names JobHunt at commit `2e40bcf`, each a link → AC-54
- [ ] Resize to 390px wide → no sideways scroll; the key stacks each term above its meaning → task 8

## Value sourcing
- [ ] Question, verdict, claims and missing notes come from the record named in marks: change Q3's question text in a copy and rebuild → the page shows the new text → Value sourcing row 1
- [ ] Date, prompt and hops come from `asked_at`, `prompt_version`, `hops`: Held out records (no `hops` key) show no hops → row 2
- [ ] Mark, note, source link and row come from `gallery/marks.json`: change one note in a copy and rebuild → only that entry changes → row 3
- [ ] Section comes from `eval_file`: set a realistic record's `eval_file` to `eval/linked-records-research.json` in a copy → it moves to Development → row 4
- [ ] Heading comes from `label`: rename `Q7` to `Q7b` in a copy → the heading changes → row 5
- [ ] `held`, `HISTORY`, `INFERRED`, `CITATION REJECTED`, `UNCITED` come from the claim's stored fields, never looked up again → row 6
- [ ] `unsupported`, `link` or `read from text`, and the failed tally use the same rules as `ask` (`claim_marks()` and `CheckedClaim` in `src/tracepath/ask/answer.py`) → row 7
- [ ] Item type, marker, file and line are parsed from the stored `line`: Eval 1's `0008/AC-7` shows line 54, as stored → row 8
- [ ] Links use the JobHunt URL and the full pinned commit constants → row 9
- [ ] Each link is checked against `corpus/jobhunt/docs/<file>`, lines counted from 1: a line one past the end fails the build, the last line passes → row 10
- [ ] Each record's `corpus_commit` is checked against the pinned commit → row 11
- [ ] Items sent shows cited items' text and other items' id, type, held flag and marker from the record's `items` → row 12
- [ ] The 44 is counted at build time: add a dummy `*.json` to `artifacts/asks/` in a copy → the intro says 45 → row 13
- [ ] The held out line and the ask-1 line are constants (`HELD_OUT_LINE`, `ASK_1_LINE` in `render.py`) → rows 14, 15
- [ ] Held out marks and notes match the v1 finish line in `docs/scope/scope.md`: 3 right, Held out 3 partly right with its note → row 16
- [ ] The mark key repeats the engineer's four lines word for word (`MARK_KEY`), and the label key matches `LABEL_KEY` → row 17

## Acceptance-criteria coverage
- AC-1 to AC-4, AC-8, AC-12 to AC-27, AC-34, AC-35, AC-44 to AC-54: UI steps
- AC-5 to AC-7, AC-9 to AC-11, AC-37 to AC-40, AC-42, AC-43: command steps (failure builds in a copy)
- AC-28 to AC-33, AC-36, AC-41: UI steps on the real page where present, and fixture tests in `tests/test_gallery.py` and `tests/test_gallery_citations.py` where no shown record has the case
- AC-55 to AC-58: command steps
- AC-59 to AC-62: workflow file steps, and the public URL check after the merge
