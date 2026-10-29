# 0010. Answer gallery: rationale

## Context

`tracepath ask` has recorded 44 answers in `artifacts/asks/`. They are the best evidence that the tool works, but they sit as JSON files in a repository. A reader who will never install tracepath, for example a hiring engineer, has no way to see a question, its answer, whether the engineer judged it right, and the line in JobHunt that each claim rests on.

The records hold what a page needs: the question, the verdict, each claim with the ids it cites, and the full pack the model was sent, where each item stores its file and line. They do not hold the engineer's marks and notes, which sit only in experiment README tables. Several questions have more than one record, written under two prompt versions (`ask-1`, `ask-2`) and two hop settings. Four records are for held out questions, whose result is already spent for any claim about unseen questions.

The page must cost nothing to host and make no API call. Its main risk is a misleading result: a citation link that opens the wrong line, or an answer shown without the judgment that goes with it. The tracepath repository is public, JobHunt is public, and the portfolio repository (`ghalynho10/portfolio`) is private (checked 2026-10-23).

## Options considered

### Option 1: a Python build command, plain HTML, GitHub Pages from this repository

A `tracepath gallery build` command reads the records, a committed marks file and the pinned snapshot, and writes one HTML page. An Actions workflow publishes it.

**Pros**:
- Records and page stay in one place, so nothing is copied and nothing drifts.
- Same language, types, lint and tests as the rest of the project; citation links can be checked against the snapshot.
- Free, and the page works with scripts off.

**Cons**:
- A new command and a new workflow to keep working.
- Plain HTML gives no search, filter or graph.

### Option 2: the same page on Netlify, as a new site linked to this repository

**Pros**:
- Pull request previews are on by default, so a change can be looked at before merge.
- Also keeps a single source of truth.

**Cons**:
- The free plan is credit based (300 credits listed, bandwidth at 20 credits per GB); the checked docs do not say whether that is monthly or what happens at the limit.
- A second platform account to keep an eye on, for a page GitHub already hosts for free.

### Option 3: the portfolio site on Netlify, with the records copied in

**Pros**:
- The page sits beside the engineer's other work.

**Cons**:
- The portfolio repository is private, and the checked docs do not show private repository linking on the free plan.
- Records are copied out of `artifacts/asks/`, which can drift from the source of truth.

### Option 4: a page that loads the raw records in the browser

**Pros**:
- No build step.

**Cons**:
- About 2.8 MB of JSON loads for every visitor, and citation links, the marks join and the checks all move into browser script that is not tested like the rest of the project.
- Blank without scripts.

## Rationale

**Reversibility**: two way door. The page is generated from committed files, so it can be rebuilt for another host by pointing the output folder elsewhere, and the workflow can be deleted without touching a record.

Option 1 fits the forces in Context. The risk that matters is a wrong citation link, and only a build in the project's own language can check each link against `corpus/jobhunt/docs/` and fail before publishing. The records are append only run artifacts, so the marks must live in a separate committed file rather than inside them. A host in the same repository removes the copy step that would let the page drift. Pages is free for public repositories, and this one is public.

The decisions below were made in the design conversation. The first five are the scope row's open questions; the engineer's reasoning is kept where given.

- **Reader goal** (recommended pick taken): the page shows that the tool works and is honest about failures, with right, partly right and wrong answers side by side.
- **Which records** (the engineer's own wording): one per question. Experiment 0018's single run for its 22 questions. For eval questions 1 to 5, experiment 0016's 2 hop run under `ask-2`, the current prompt and the default. A line says earlier `ask-1` runs were also marked right. The demo GIF runs are not shown. The page says how many records exist in all and links to the directory.
- **Held out records** (the engineer's decision, changed after the cross check; the first answer was to hide them): shown, in their own section labelled "held out", with one line: asked once at the end of v1, never used to tune the tool. Their marks come from the v1 finish line in `docs/scope/scope.md` (3 right, 1 partly right), copied word for word with that source. The recommendation had been to hide them, because those questions are spent for any claim about unseen questions and the page presents rather than evaluates. The engineer chose to show them, so the shown set is 31 records. The cost is in Consequences.
- **Marks and notes** (recommended pick taken): shown. The engineer's marks are the page's evidence; the verdict is the model's own word and is shown apart.
- **Disclosures** (engineer's pick, against the recommendation): a link to experiment 0018's README only. The recommendation was a note on each affected answer plus a method section, so the caveat sits where the reader sees the answer. The cost of the engineer's choice is recorded in Consequences.
- **UI** (the engineer's own wording): a plain list with the evidence folded under each answer, as the first slice. The graph per answer is the next slice and is kept in scope feature 17. Visual design is not decided here.
- **Host**: GitHub Pages from this repository (recommended pick taken).
- **Data build**: a tracepath command (recommended pick taken). The engineer asked that the build session may copy the marks but the engineer checks them before commit, which keeps the marks the engineer's own ruling.
- **Publishing**: an Actions workflow, because a Pages branch source can only be a branch root or the `/docs` folder, and `docs/` here is the specs folder.
- **Evidence fold**: cited items in full, other items as one line rows.
- **Claim labels**: kept, with the terminal's names and a key.
- **Cited item with no line**: link to the file, labelled "whole file". Two cited items are affected today.
- **Marks file**: `gallery/marks.json`, one entry per shown record, each naming its source README, copied word for word.
- **Citation check**: the cited file must exist and the line must be inside it, else the build fails. A text match against the item was offered and not chosen, because items are quoted spans that may cross lines.
- **Page technology**: plain HTML written by the build, folds with `<details>`, no JavaScript.

### Two readings the spec makes, to confirm

- The engineer's marks answer said the build fails on "a shown record with no entry". Because `gallery/marks.json` is the one list of what is shown, a shown record always has an entry. The spec instead fails the build on an entry that is incomplete (AC-10, AC-11) or points nowhere (AC-5, AC-6), and the build plan names the 31 records of the starting content, so a record cannot be dropped without notice. (The counts were criteria in the first draft and were moved to the build plan by the engineer.)
- The confirmed marks entry had four fields. The spec now has six: `label` is added because experiment 0018's question numbers (Q1 to Q22) cannot be read back from the records, and `source` is split into `source_path` and `source_row` so the path can be linked.

### Filter applied to every guard

Guards kept: the citation file and line check for every linked item (a wrong link misleads), the item line grammar check (97 real items have a sixth field and a loose parser would fail or mislink them), the record `corpus_commit` check (a record cut on another snapshot would pass the line check yet link wrongly), the `eval_file` allowlist, the pinned commit test, the incomplete entry failure. Guards not added: a text match of each item, a network link check, a hash of the output, a rule that forbids new records. None of those protects against a failure seen in the real records.

Trimmed by the engineer after the cross check, because none protects against a failure seen in real output: an order rule for entries, an anchor rule for labels, a test that the build runs with no credentials, a test that the output has no script element, and a criterion for the label key (kept as a build step). The deploy on failure rule moved to Consequences.

### Cross check, 2026-10-23 (another model, read only)

It read all 44 records and the ask code and found 17 gaps. The ones that changed the design: the item line has an optional sixth field (verified in `retrieve.py:322-331`; 97 items), so the first grammar in this spec was wrong; `rejected_ids` means cited ids not in the pack (verified in `answer.py:180`), so a check that every cited id is in the pack contradicted the rejected label; the terminal prints more labels than the first draft listed; the records lack some keys; every linked file is markdown, which GitHub renders; stored text holds raw markup; and the workflow and its path filter were under specified. The engineer applied the factual fixes and the recommended picks for escaping, source links, workflow details, the wider path filter and inline styles.

### Correction of 2026-10-27: the page size

The note on the link preview (2026-10-27) held that "LinkedIn documents no page size limit" and left the page whole. The next run of Post Inspector showed otherwise: it refused the page for size, with a threshold of 3,145,728 bytes. The page was 4,817,451 bytes, of which 3,834,664 were the 31 graph blocks of spec 0011; the rest was 982,787, found again by rebuilding at 747365c on 2026-10-27. The Follow up said to revisit "only if Post Inspector still fails", and it did. The engineer ruled that each entry's graph data moves out into its own file (spec 0011 AC-104 to AC-127a, with the options and the rulings in its `rationale.md`), and that the size limit gets one test (AC-78). The earlier ruling was a reading of LinkedIn's help page, which lists the tags and the image and says nothing of page size; absence of a documented limit was taken as no limit, which the measured failure disproves.

## Evidence

### Records checked, 2026-10-23

- 44 records in `artifacts/asks/`: 35 on `ask-2`, 9 on `ask-1`. Every cited id is in its own record's pack (263 cites, 0 missing).
- Claim flags stored across all records: held 24, history 14, inferred 2, rejected 0, uncited 0.
- 3,016 stored items; 62 have a file but no line (whole records). 2 of those are cited.
- Older `ask-1` records lack some keys (`called`, `hops`, `eval_file`) that `ask-2` records have. The cross check found 3,016 stored items: 2,919 with five fields and 97 with six; every location maps to a file under `corpus/jobhunt/docs/` and no line is past the end of its file; all 44 records say `corpus_commit` `2e40bcf`.
- Held out marks: 3 right and 1 partly right (question 3, cause retrieval), recorded in `docs/scope/scope.md`, v1 finish line, 2026-10-19.
- Marks: experiment 0018's README holds Q1 to Q22 marks and notes; experiment 0016's README holds hops 2 and hops 0 marks (all right); scope's v1 finish line holds the `ask-1` marks for eval 1 to 5 (all right) and the held out result.

### Host facts, checked against official docs on 2026-10-23

GitHub Pages:
- Free for public repositories on a free account: verified (plans page). The plans page does not say hosting is free of charge in so many words.
- Publishing source: a branch (root or `/docs`) or a GitHub Actions workflow: verified.
- Limits: 1 GB published site, soft 100 GB per month bandwidth, 10 minute deployment timeout, soft 10 builds per hour (not for custom workflows): verified.
- A free personal account cannot use Pages on a private repository; a Pages site is public even when its repository is private: verified.
- Prohibited use: free hosting of businesses, e-commerce or commercial SaaS. A personal showcase is not addressed: verified.
- Default project site URL form: not found on the pages fetched. `https://<owner>.github.io/<repo>/` is inferred.
- Skipping a docs only push: not found for branch publishing; a path filter on an Actions trigger is the route. Whether the filter works as described was not confirmed from the pages fetched.

Netlify:
- Free plan is credit based (300 credits listed, bandwidth 20 credits per GB, unlimited deploy previews): verified on the pricing page. Not found: whether 300 is monthly, build minute and site count allowances, what happens at exhaustion.
- Subdirectory deploy with a base directory and a publish directory: verified. An empty build command is not explicitly confirmed.
- Pull request previews are on by default; branch deploys are off by default: verified.
- A second site linked to one repository: not found. A private GitHub repository on the free plan: not found (private organization repositories appear only under Pro).
- Terms point to a Self-Serve Subscription Agreement that could not be fetched. No fair use clause found.

Facts that differ from common belief: Pages on a private repository is not possible on a free account, and Pro does not change that; Netlify Free now uses credits, not bandwidth and build minute allowances.

## References

**Project sources** (verifiable, in this repo):
- `AGENTS.md`: Tracer Bullet default, functional core with an imperative shell, typed exceptions with exit code 1, no mutation of arguments, the rule that code and tests never read `reference/`.
- `docs/specs/0009-answer-at-question-time/index.md`: the shape of the ask record and the claim labels.
- `docs/scope/scope.md`, feature 17: the intent, the five open questions, the v1 finish line.
- `README.md` line 92: the held out result.
- `experiments/0016-link-hops/README.md`, `experiments/0018-realistic-usage-questions/README.md`: the marks and the disclosures.
- `corpus/jobhunt/SNAPSHOT.md`: the pinned commit and the repository.

**Practices & standards**:
- Static site generation from versioned data.
- Fail the build, not the reader, on a broken link.

**Links** (web verified in the host check, 2026-10-23):
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Configuring a publishing source: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- Creating a GitHub Pages site (private repository rule): https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- Custom workflows for Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub plans: https://docs.github.com/en/get-started/learning-about-github/githubs-plans
- GitHub Actions workflow syntax (`needs`, `paths`, `concurrency`): https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- Netlify pricing: https://www.netlify.com/pricing/
- Netlify build configuration: https://docs.netlify.com/build/configure-builds/overview/
- Netlify deploy previews: https://docs.netlify.com/deploy/deploy-types/deploy-previews/
- Netlify branch deploys: https://docs.netlify.com/deploy/deploy-types/branch-deploys/
