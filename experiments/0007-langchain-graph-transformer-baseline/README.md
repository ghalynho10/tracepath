# 0007 · LangChain `LLMGraphTransformer` baseline

**Date run**: 2026-09-15 (recorded here 2026-10-01)
**Corpus**: JobHunt's live working tree, most likely at commit `e331b25`, not the pinned `2e40bcf` (see Provenance)
**Code commit**: none. The run predates tracepath's first commit (`b4b37c0`, 2026-09-18) and used none of its code
**Spec**: [0001, rationale, Context](../../docs/specs/0001-stack-and-architecture/rationale.md), which cites this failure in one sentence

## What this is

Spec 0001's rationale rejects a general purpose extraction library on the grounds that
"a prior attempt with `LLMGraphTransformer` failed on this same data". That sentence had
no script, log or output behind it in the repo. This experiment is that evidence: the
script and what it printed.

The question was whether an off the shelf extractor, run with its defaults, would carry
what tracepath needs from JobHunt's docs: acceptance criterion ids as nodes, one identity
per feature across files, links between files, and supersession and correction as
relationships.

## Method

`script.py` runs LangChain's `LLMGraphTransformer` with default settings, no
`allowed_nodes` and no `allowed_relationships`, over four whole JobHunt files:

- `docs/specs/0006-entry-page-and-link-metadata/index.md`
- `docs/specs/0007-auth-and-per-user-isolation/index.md`
- `docs/scope/scope.md`
- `docs/reflexes.md`

It prints each file's nodes and relationships. Nothing is stored: the transformer works in
memory and no Neo4j was involved. The two flagged questions were (1) do AC-7, AC-16,
feature 6 and feature 7 appear as node ids, and (2) does anything like `SUPERSEDES` or
`CORRECTED_BY` appear.

These four were chosen because they hold one supersession story. Spec 0006 AC-7 is struck
and marked "SUPERSEDED 2026-08-29 by spec 0007 AC-16", and spec 0007 AC-16 deletes 0006's
`COPY-1` ("Sign in isn't live yet"). `scope.md` names the features and `reflexes.md`
mentions feature 7 again.

## Provenance

- **Where it ran**: a one off GitHub Copilot chat in VS Code, in the JobHunt workspace, on
  2026-09-15. A throwaway venv at `/tmp/lc-graph-venv` and the script at
  `/tmp/graph_extract_test.py`.
- **Packages**: `langchain-neo4j 0.10.0`, `langchain-openai 1.6.2`, `langchain-core 1.6.3`,
  as the chat's `pip list` reported them.
- **Provider**: OpenAI, using the key in JobHunt's `.env.local`.
- **Corpus state**: the script read JobHunt's live working tree, not a pinned snapshot. The
  last JobHunt commit before the run day ended is `e331b25` (2026-09-15 23:23 -0400), from
  `git -C jobhunt log -1 --before="2026-09-16 00:00"`. That is the most likely state of the
  docs, but uncommitted changes in the working tree at the time cannot be ruled out. It is
  three days before tracepath's pinned `2e40bcf` (2026-09-18). Between those two commits,
  specs 0006 and 0007 and `reflexes.md` are unchanged, and `scope.md` differs (107 lines
  added, 89 removed, per `git diff --stat e331b25 2e40bcf`).
- **Capture**: the temp files were lost, so everything in `data/` is copied verbatim from
  the chat transcript, not from the run's own files.
- **Script**: `script.py` is reconstructed from the original prompt plus the transcript's
  stated one-line change (the model on the LLM line), not the file that ran.

## Runs

| Run | Model | Result |
|---|---|---|
| 1 | `gpt-4o-mini` | Crashed on file 1 of 4 with `openai.LengthFinishReasonError`: 16,384 completion tokens (the model's output cap), 44,854 prompt tokens. No output. `data/run1-error.txt` |
| 2 | `gpt-4.1` | Succeeded. Only the LLM line changed, no prompt edits, still no allowed types. Output not kept |
| 3 | `gpt-4.1` | Succeeded. An accidental re run: the capture command executed the script again. Full output in `data/output-run3.txt` |

Both models ran at `temperature=0`. Runs 2 and 3 produced different graphs; the
transcript's summary of the diff is `data/run2-vs-run3.md`.

## Findings

All from run 3 (`data/output-run3.txt`) unless marked.

1. **AC-7 and AC-16 are absent as nodes.** No node anywhere in the four files carries
   either id. `reflexes.md` produced only a generic `Ac-N Tag (Identifier)`.
2. **Feature 7 has three incompatible identities.** Specs 0006 and 0007 each emit
   `Feature 7 (Feature)`, which would merge. `scope.md` emits the same feature as
   `Auth & Per User Isolation (Concept)` and `reflexes.md` as a generic `Feature (Concept)`.
   Different ids and types, nothing linking them.
3. **No supersession or correction types.** Nothing like `SUPERSEDES` or `CORRECTED_BY`
   appears, and the "SUPERSEDED 2026-08-29 by spec 0007 AC-16" text produced nothing.
   Instead there are 86 distinct ad hoc relationship types (`USES`, `CONTAINS`, `MENTIONS`,
   `DEFINED_IN`, `MAPS_TO`, `USES_PLACEHOLDER`, ...). The transcript estimated about 60;
   86 is the count from the committed output.
4. **Zero cross file links.** Each file's graph is an island. Spec 0006's graph has a
   `Docs/Scope/Scope.Md (File)` node, but nothing ties it to `scope.md`'s own graph.
5. **The struck string comes back as a live fact.** Spec 0006's graph emits
   `Copy-1 --[HAS_VALUE]--> Sign In Isn'T Live Yet. Coming Soon With Google And Github.`,
   the `COPY-1` that spec 0007 AC-16 deletes. Spec 0007's graph emits its own `Copy-1 (Text)`,
   a live `/sign-in` error slot (`Access_Denied --[MAPS_TO]--> Copy-1`). On load the two
   would merge into one node, a deleted string fused with a live one, with no trace of
   AC-16.

## Caveats

- **Defaults only.** No `allowed_nodes`, `allowed_relationships`, custom prompt or schema.
  A constrained configuration could do better on findings 3 and 5. This measures the
  library as it comes, not its ceiling.
- **Whole files, not sections.** Each file went in as one document, which is what blew
  run 1's output cap. Tracepath extracts per section.
- **OpenAI, not Claude.** The models differ from tracepath's (Claude Sonnet 5), so this does
  not separate the library's behaviour from the model's.
- **Non determinism rests on two runs.** Runs 2 and 3 differ, which shows drift exists at
  `temperature=0`. It does not measure how much.
- **Transcript capture.** The temp files are gone. Run 3's output and the run 2 vs 3
  summary are as the chat printed them, and run 2's own output was never kept.

## Conclusion

With defaults, `LLMGraphTransformer` on these four files drops the acceptance criterion
ids, fragments one feature into identities that cannot be reconciled, links nothing across
files, has no supersession vocabulary, and re-asserts a struck clause as current. Those are
the failures spec 0001's rationale names, and they are why tracepath uses a closed
vocabulary schema with per section extraction and its own identity resolution.
