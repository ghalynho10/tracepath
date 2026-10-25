# 0010. Answer gallery

**Date**: 2026-10-23
**Status**: Accepted

## Summary

This spec adds a static web page that shows answers `tracepath ask` has already recorded, for a reader who will never run the tool. A new command, `tracepath gallery build`, reads the records in `artifacts/asks/` and a marks file you commit, and writes one HTML page with no API call. Each citation links to its exact line in JobHunt at the pinned commit `2e40bcf`. A GitHub Actions workflow publishes the page on GitHub Pages from this repository.

## Requirements

**User stories**:
- As a reader who will never run tracepath, I want to see real questions with the answers the tool gave, so I can judge whether it works.
- As that reader, I want every citation to open the exact line it cites in JobHunt, so I can check a claim myself.
- As that reader, I want the engineer's own mark and note next to each answer, so I can tell a good answer from a bad one without trusting the tool's own verdict.
- As the engineer, I want the page to say what it leaves out, so nothing looks hidden.
- As the engineer, I want a wrong citation link to fail the build, so a reader is never sent to the wrong line.

**Acceptance criteria** (each holds one claim):

*What is shown*
- **AC-1**: The page has one entry for each record named in `gallery/marks.json`, and no entry for any other record.
- **AC-2** (amended 2026-10-24): An entry whose `section` is `development` appears in the section "Development questions"; its record's `eval_file` equals the development eval file, `EVAL_FILE` in `src/tracepath/report.py`.
- **AC-3** (amended 2026-10-24): An entry whose `section` is `held out` appears in the section "Held out questions"; its record's `eval_file` is present and is not the development eval file.
- **AC-4**: A record with no `eval_file` appears in the section "Realistic questions".
- **AC-5**: The build fails, exit 1, naming the entry, when `gallery/marks.json` names a record that is not in `artifacts/asks/`.
- **AC-6** (amended 2026-10-24): The build fails, exit 1, naming the entry, when an entry's `section` disagrees with its record: `development` needs an `eval_file` equal to the development eval file, `realistic` needs no `eval_file`, and `held out` needs an `eval_file` that is present and not the development one, so any record with such an `eval_file` must be marked `held out`.
- **AC-7**: The build fails, exit 1, naming the record, when a shown record's `corpus_commit` differs from the pinned commit.
- **AC-8**: The held out section carries the line: asked once at the end of v1, never used to tune the tool.

*Marks*
- **AC-9** (amended 2026-10-24): Each `gallery/marks.json` entry has the fields `record`, `label`, `section` (`development`, `held out` or `realistic`), `mark`, `note`, `source_path` and `source_row`.
- **AC-10**: The build fails, exit 1, naming the entry, when an entry lacks one of those fields.
- **AC-11**: The build fails, exit 1, naming the entry, when `mark` is not one of `right`, `partly right`, `wrong`, `declined`.
- **AC-12**: Each entry shows the mark exactly as in `gallery/marks.json`.
- **AC-13**: Each entry shows the note exactly as in `gallery/marks.json`, and shows no note when the note is null.
- **AC-14**: The mark is labelled as the author's own mark, in first person (My mark).
- **AC-15**: The model's verdict is labelled as the model's own verdict.
- **AC-16**: Each entry shows `source_row` as text and links `source_path` to `https://github.com/ghalynho10/tracepath/blob/main/<source_path>`.

_Note on AC-2, AC-3, AC-6 and AC-9: Amended 2026-10-24 by the engineer: sections come from the record and the marks file, never from an eval file name in source, to keep AC-27 and the report guard intact._

*Each answer*
- **AC-17**: Each entry shows the question text as stored in the record.
- **AC-18**: Each entry shows the model's verdict as stored in the record.
- **AC-19**: Each entry shows the claims in stored order, with each claim's text as stored.
- **AC-20**: Each entry shows the record's `missing` notes when it has any.
- **AC-21**: Each entry shows the date asked.
- **AC-22**: Each entry shows the prompt version.
- **AC-23**: Each entry shows the hop count when the record stores one, and none when it does not.
- **AC-24**: Stored text that contains markup, for example `<figure`, appears on the page as visible text and is not interpreted.
- **AC-25**: Line breaks in stored text are kept, and no markdown in stored text is rendered.

*Claim labels* (each derived from stored fields only; nothing is looked up again)
- **AC-26**: A cited id that is in the claim's `held_ids` shows `held` after it.
- **AC-27**: A claim whose `history` is true shows `HISTORY`.
- **AC-28**: A claim whose `inferred` is true shows `INFERRED`.
- **AC-29**: A claim whose `rejected_ids` is not empty shows `CITATION REJECTED:` and those ids.
- **AC-30**: A claim whose `uncited` is true shows `UNCITED`.
- **AC-31**: A claim that cites at least one id, where every cited id is in `rejected_ids`, shows `unsupported`.
- **AC-32**: A claim that is neither inferred nor unsupported shows `link` when its `basis` is `link`, and `read from text` otherwise.
- **AC-33**: When one or more claims failed a check, the verdict line adds "N of M claims failed a check"; a claim failed when its `rejected_ids` is not empty, or it is uncited, or its `basis` is `link` and it is inferred.

*Citations*
- **AC-34**: Each linked item links to `https://github.com/ghalynho10/JobHunt/blob/<full pinned commit>/docs/<file>?plain=1#L<line>`, where `<file>` and `<line>` come from the item's stored location.
- **AC-35**: A linked item that has a file but no line links to the file with no line anchor, and the link text says "whole file".
- **AC-36**: An item whose stored location is "no file stored" or "no path stored" gets no link.
- **AC-37**: The build fails, exit 1, naming the record and item, when an item's stored `line` does not match `<id>  <type>  <held or accepted>  [STRUCK or HISTORY  ]<location>  <hit or hop N>`, with fields separated by exactly two spaces.
- **AC-38**: The build fails, exit 1, naming the record and item, when a linked item's file does not exist under `corpus/jobhunt/docs/`.
- **AC-39**: The build fails, exit 1, naming the record and item, when a linked item's line is below 1 or past the last line of its file.
- **AC-40**: The build fails, exit 1, naming the record and id, when a claim cites an id that is neither among the record's items nor in that claim's `rejected_ids`.
- **AC-41**: A cited id in `rejected_ids` is shown with no link.
- **AC-42**: The build fails, exit 1, naming the record and item, when a cited item has no stored file or path.
- **AC-43**: The pinned commit in the code equals the full commit recorded in `corpus/jobhunt/SNAPSHOT.md`.

*Evidence*
- **AC-44**: Each entry has an "Items sent" section that is closed until the reader opens it.
- **AC-45**: In that section, each item the answer cites is shown with its full stored text.
- **AC-46**: In that section, each item the answer does not cite is one row that shows its id, its type and whether it is held or accepted.
- **AC-47**: That row shows `STRUCK` or `HISTORY` when the stored line has that marker.
- **AC-48**: That row carries a link built by AC-34, AC-35 and AC-36.

*Page statements*
- **AC-49**: The page states how many records `artifacts/asks/` holds, counted by the build.
- **AC-50**: The page links to the `artifacts/asks/` directory on GitHub.
- **AC-51**: The page states which questions it shows: eval questions 1 to 5, held out questions 1 to 4, and experiment 0018's 22.
- **AC-52**: The development section states, in first person, that the earlier `ask-1` runs of eval questions 1 to 5, from 2026-10-19, "I also marked right".
- **AC-53**: The realistic section links to experiment 0018's README as the place that records how those questions were set and run.
- **AC-54**: The page names JobHunt at the pinned commit as the source every citation points into, with a link to the repository.

*The build*
- **AC-55**: `uv run tracepath gallery build --out DIR` writes `DIR/index.html` and exits 0.
- **AC-56**: The build makes no network call and no API call; a test that blocks sockets still passes.
- **AC-57**: The build never writes inside `artifacts/` or `corpus/`.
- **AC-58**: `index.html` is self contained: its styles are inline and it refers to no other file of the site.

*Publishing*
- **AC-59**: A workflow builds the page on a push to `main`.
- **AC-60**: That workflow deploys the built page to GitHub Pages.
- **AC-61**: That workflow runs only when `artifacts/asks/`, `gallery/`, `src/tracepath/`, `pyproject.toml`, `uv.lock`, `corpus/jobhunt/` or the workflow file changes.
- **AC-62**: The workflow's deploy job lists its build job under `needs`, so a failed build deploys nothing; a test reads the workflow file and checks that line.

## Decision

**Chosen option**: Option 1: a Python build command that writes plain HTML, published to GitHub Pages by an Actions workflow.

`tracepath gallery build` joins the stored ask records, a committed marks file and the pinned JobHunt snapshot into one static page with no JavaScript, and a workflow publishes it from this public repository.

**Follows**: static site generation from versioned data (build once, serve files) · functional core with an imperative shell, as the project's own rule.

**Implementation skills**: `typer-and-rich` (`jamie-bitflight/claude_skills`, `.agents/skills/typer-and-rich/`) · `pydantic` (`pydantic/skills`, `.agents/skills/pydantic/`) · `uv` (`astral-sh/claude-code-plugins`, `.agents/skills/uv/`)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Mode and platform**: FEATURE. A static web page built by the Python CLI. No server, no database, no JavaScript.

**Data model sketch**: nothing is stored beyond one new committed file and the records that already exist.

`gallery/marks.json` is a JSON list; each entry:

| Field | Type | Rule |
|---|---|---|
| `record` | string, required | File name in `artifacts/asks/`; unique across entries; the key |
| `label` | string, required | Short name used for the heading, for example `Eval 3`, `Held out 2` or `Q7`; unique across entries |
| `mark` | string, required | One of `right`, `partly right`, `wrong`, `declined` |
| `note` | string or null, required | Copied word for word from the source; null when the source gives none |
| `source_path` | string, required | Repository path of the file the mark was copied from, for example `experiments/0018-realistic-usage-questions/README.md` |
| `source_row` | string, required | Where in that file, for example `Q7` or `v1 finish line` |

The build reads each named record into a frozen Pydantic model: `question`, `eval_file`, `eval_question`, `prompt_version`, `hops`, `asked_at`, `corpus_commit`, `verdict`, `missing`, `claims` and `items`. The keys `eval_file`, `eval_question` and `hops` default to null when a record lacks them (they are absent from some `ask-1` records and from one `ask-2` record). It does not read the records' `links`.

**Item location grammar.** An item's stored `line` text, after leading spaces are stripped, is `<id>  <type>  <held or accepted>  [STRUCK or HISTORY  ]<location>  <hit or hop N>`, fields joined by exactly two spaces (so `hop 1` keeps one inside it). `<location>` is `<file>:<line>`, `<file>`, `no file stored` or `no path stored`. Of 3,016 stored items, 2,919 have five fields and 97 have six. The builder splits on exactly two spaces and fails on any other shape (AC-37).

**State transitions**: none.

**Command surface**:
| Command | Key inputs | Key outputs | Key errors |
|---|---|---|---|
| `tracepath gallery build` | `--out DIR` (required), `--root PATH` (default: the repository root) | `DIR/index.html`, a one line count of entries written | exit 1 with a typed message on AC-5, AC-6, AC-7, AC-10, AC-11, AC-37 to AC-40, AC-42 |

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| Render an entry | question, verdict, claims, missing notes | the record named by `gallery/marks.json` (`question`, `verdict`, `claims`, `missing`) |
| Render an entry | date asked, prompt version, hops | the record's `asked_at`, `prompt_version`, `hops` (hops omitted when null) |
| Render an entry | mark, note, source link and row | `gallery/marks.json` (`mark`, `note`, `source_path`, `source_row`) |
| Render an entry | section | the marks entry's `section`, checked against the record's `eval_file`: the development eval file means development, null means realistic, any other means held out (amended 2026-10-24, AC-6) |
| Render an entry | heading | `label` in `gallery/marks.json` |
| Render a claim | `held`, `HISTORY`, `INFERRED`, `CITATION REJECTED`, `UNCITED` | the claim's stored `held_ids`, `history`, `inferred`, `rejected_ids`, `uncited` |
| Render a claim | `unsupported`, `link` or `read from text`, the failed tally | derived from the claim's stored `cites`, `rejected_ids`, `uncited`, `inferred` and `basis`, by the rules in AC-31 to AC-33 (the same rules as `src/tracepath/ask/answer.py`) |
| Render a citation | item type, STRUCK or HISTORY marker, file, line | parsed from the cited item's stored `line` by the grammar above |
| Render a citation | link | constants for the JobHunt repository URL and the full pinned commit, plus the file and line above |
| Check a link | file and line count | `corpus/jobhunt/docs/<file>`; lines counted with `splitlines`, first line is 1 |
| Check a record | commit it was cut on | the record's `corpus_commit` against the pinned commit |
| Render the evidence list | cited item text; other items' id, type, held flag, marker | the record's stored `items` |
| Page statement | number of records in all | count of `*.json` in `artifacts/asks/` at build time |
| Page statement | held out line | a constant (AC-8) |
| Page statement | `ask-1` runs of eval 1 to 5 were marked right | a constant, from `docs/scope/scope.md` line 238 (the v1 finish line) |
| Held out marks | mark and note for held out 1 to 4 | `docs/scope/scope.md`, the v1 finish line: 3 right, 1 partly right (question 3); notes copied word for word |
| Key text for labels and marks | one line each | a constant written in the build; the marks' wording is the engineer's (see Follow-up) |

**Key invariants**:
- A link is built only from a file and line that exist in the pinned snapshot (AC-38, AC-39), for every item that gets a link, not only cited ones.
- The page shows stored fields as stored, escaped. It looks nothing up again and rewrites no claim, note or question.
- `gallery/marks.json` is the only list of what is shown; the code holds no second list.
- The page carries no timestamp of the build.
- Records in `artifacts/asks/` and files in `corpus/` are read, never written (AC-57).

**Security model**: the page is public. It holds only the stored records (questions and answers over JobHunt's public specs), the engineer's own marks, and links to public repositories. All stored text is escaped (AC-24). No secret is read. The build needs no key and no database; settings load only inside commands that use them, so `gallery build` loads none. No compliance scope applies.

**Configuration required**:
- Constants in code, no environment variable: the JobHunt repository URL, the full pinned commit, this repository's URL, the docs path prefix `docs/`.
- One GitHub setting, set once by the engineer: Pages source set to "GitHub Actions" in the repository settings.
- The workflow (`.github/workflows/pages.yml`) needs: `permissions` of `contents: read`, `pages: write` and `id-token: write`; `environment: github-pages`; `actions/configure-pages@v6`, `actions/upload-pages-artifact@v5` and `actions/deploy-pages@v5` (the versions the workflow uses; each tag checked to exist on 2026-10-24); the deploy job separate from the build job and listing it under `needs` (checked against GitHub's workflow syntax docs: a job that needs a failed or skipped job is skipped); `concurrency: pages` (not shown on the docs page checked; the builder takes it from GitHub's starter workflow); `workflow_dispatch` so the first deploy can be started by hand; a runner pinned to `ubuntu-24.04` as in `ci.yml`; `astral-sh/setup-uv@v7` with `uv sync --locked`. No Neo4j service. The builder re-checks the action versions when slice 1 is built.

**Critical test scenarios** (each maps to an acceptance criterion in ## Requirements):
- Happy path: build a page from a fixture of two records and a marks file; the page shows both with marks, claims, labels, evidence and links, verifies **AC-1, AC-12, AC-19, AC-34, AC-45**.
- Happy path on the real data: build from `artifacts/asks/` and the committed `gallery/marks.json` succeeds and writes one entry per marks entry, verifies **AC-1, AC-55**.
- Failure: a marks entry naming a missing record, a missing field, a bad mark, a `section` its record disagrees with or a different `corpus_commit` each exit 1 with the entry named, verifies **AC-5, AC-6, AC-7, AC-10, AC-11**.
- Failure: a line past the end of its file, a missing file, an unexpected item line shape, or a claim citing an unknown id each exit 1, verifies **AC-37, AC-38, AC-39, AC-40**.
- Edge: an item with a file and no line links to the file and says "whole file", checked with a fixture because no record cites such an item among the 31, verifies **AC-35**.
- Edge: a six field item line with `STRUCK` parses and its row shows the marker, verifies **AC-37, AC-47**.
- Edge: an older `ask-1` record without `hops` or `eval_file` renders with no hop count, verifies **AC-23**.
- Edge: stored text containing `<figure` shows as text, verifies **AC-24**.
- Guard: the pinned commit in code equals `SNAPSHOT.md`, verifies **AC-43**.
- Isolation: the build passes with sockets blocked and writes nothing under `artifacts/` or `corpus/`, verifies **AC-56, AC-57**.
- Workflow: the workflow file's trigger lists the paths of AC-61, and its deploy job lists the build job under `needs`, verifies **AC-59, AC-60, AC-61, AC-62**.

## Build plan

Approach: Tracer Bullet (the project default). The first slice is one real record, built and published end to end, so the whole route (command, page, workflow, Pages setting, public URL) is proven before the page is thickened.

1. [x] Slice 1, the thin thread. Add `src/tracepath/gallery/` with a loader for one record and one marks entry and a renderer that writes a self contained `index.html` with the question, verdict and claims; wire `tracepath gallery build --out DIR` in `cli.py`, satisfies **AC-1, AC-17, AC-18, AC-19, AC-55, AC-56, AC-57, AC-58**
2. [x] Slice 1, publish it. Add the Pages workflow (build job, then deploy job) with the path filter; check its action names against GitHub's docs; the engineer sets the Pages source once; confirm the one entry page opens at its public URL, satisfies **AC-59, AC-60, AC-61, AC-62** · done 2026-10-24: the Pages run on `befdcaa` succeeded and the page is live at https://ghalynho10.github.io/tracepath/ with 31 entries
3. [x] Slice 2, the marks file. Add the marks model and loader with its failure cases; render the mark, note, source, the three sections and the held out line, satisfies **AC-2, AC-3, AC-4, AC-5, AC-6, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-15, AC-16**
4. [x] Slice 2, the real marks. Fill `gallery/marks.json` with its starting content, 31 entries, each copied word for word from its source (the 0016 and 0018 READMEs for the development and realistic records, the v1 finish line for the held out ones); the engineer checks it before commit, satisfies **AC-1**
   - 5 development records: eval questions 1 to 5, the `ask-2` runs at 2 hops of 2026-10-20 (experiment 0016's hops 2 column).
   - 4 held out records: `eval-held-out-q1` to `q4`, the `ask-1` runs of 2026-10-19; marks and notes from the v1 finish line in `docs/scope/scope.md`.
   - 22 realistic records: experiment 0018's Q1 to Q22, which are `2026-10-22T19-39-13Z` (Q1) and the 21 records from `2026-10-22T20-24-02Z` to `2026-10-22T20-25-54Z` in committed order.
5. [x] Slice 3, citations. Parse each item's location by the grammar, build the links, check every linked item against `corpus/jobhunt/docs/`, check `corpus_commit`, handle the no line, rejected and no file cases, add the `SNAPSHOT.md` test, satisfies **AC-7, AC-34, AC-35, AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42, AC-43**
6. [x] Slice 4, labels, evidence and escaping. Render the claim labels and the verdict tally by the rules in AC-26 to AC-33, the key for labels and marks, the closed "Items sent" section with cited items in full and other items as rows, the record details, and escape all stored text, satisfies **AC-20, AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29, AC-30, AC-31, AC-32, AC-33, AC-44, AC-45, AC-46, AC-47, AC-48**
7. [x] Slice 5, page statements. Add the record count and directory link, the shown set, the `ask-1` line, the 0018 link and the source line, satisfies **AC-49, AC-50, AC-51, AC-52, AC-53, AC-54**
8. [x] Visual design pass, settled before this task starts (see Follow-up), then applied so the engineer's mark reads clearly apart from the model's verdict, satisfies **AC-14**

## Consequences

**Positive**:
- A reader who never installs anything can read real answers, see the engineer's marks, and open each cited line in JobHunt.
- The records and the page live in one repository, so the page cannot drift from `artifacts/asks/`.
- The build is offline and free, and a wrong link fails the build rather than reaching a reader.

**Negative / tradeoffs**:
- Experiment 0018's disclosures reach the reader by one link only (the engineer's choice). The notes that Q19 and Q22's expected lines were written after the advisor's summary, and that Q1 ran before the questions were committed, are not on the page next to those answers. This leaves scope feature 17's "Done when" clause, "anything the page leaves out or qualifies is stated on the page", only partly met, and the scope row should be reconciled with it.
- The page now shows the four held out records. Those questions are public from the day it is published, so they cannot be used again as unseen questions, which they already could not for any new claim.
- The marks exist only as README tables and the v1 finish line today, so `gallery/marks.json` is a second copy that can drift if a source changes. AC-16 links each entry back to its source to make that visible.
- The page shows 31 of 44 records; the other 13 are named only as a count.
- Parsing an item's location out of its stored display text depends on that text's format. The build fails on a shape it does not know rather than guessing.
- GitHub renders `.md` files, so a plain `#L<line>` link may not open the line. The `?plain=1` form is the fix. It was first inferred from how GitHub behaves, then confirmed on a real link by `/check verify` (step E12 in `docs/reviews/2026-10-24-check-verify-answer-gallery.md`): the link opened GitHub's plain text Code view with the cited line highlighted.
- Pages deploys on a push to `main` even if the `check` job fails on that push. Pull requests must pass `check` first, so this is accepted.
- When the build job of the workflow fails, nothing is deployed and the previously published page stays up (AC-62).
- The page has no search, filter or graph. It is a list.

**Neutral**:
- A new package `src/tracepath/gallery/`, a new top level folder `gallery/` for the marks file, and a new workflow file.
- GitHub Pages serves a project site from `https://<owner>.github.io/<repo>/` (inferred, not on the docs pages checked). All links on the page are absolute or in page anchors, and the styles are inline, so the path does not matter.
- The page stays far under GitHub Pages' published limits (1 GB site, soft 100 GB per month).
- The label key lives in the build as a step, not as a criterion.

## Follow-up

- [x] Wording of the key for each mark (`right`, `partly right`, `wrong`, `declined`) is the engineer's to give, especially `declined`, which no README defines in one line. Needed before slice 4.
- [x] Visual design (fonts, colours, layout, how the folds look) is left open here. Settle it before task 8, with `/imprint` or by hand.
- [ ] Next slice, recorded in scope feature 17: a list plus one interactive graph per answer, drawn from each record's stored pack, with cited items highlighted and held items and unresolved names marked. It would cover part of the deferred "Visual UI". Needs its own spec.
- [x] Reconcile scope feature 17's "Done when" clause with the link only disclosure choice (see Consequences).
- [x] Confirm the wording of AC-52 against `docs/scope/scope.md` line 238 when slice 5 is built. Experiment 0016's README marks only the `ask-2` runs.
- [x] Check the `?plain=1` link form on one real link during slice 3, and the Pages action versions during slice 1.
- [ ] Decide whether Netlify or the portfolio site is worth a second look later; the unchecked Netlify facts are in `rationale.md`.
- [ ] Dark mode that follows the visitor's system setting, CSS only, with each mark pill readable in both modes; later, after launch.
