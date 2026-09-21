# JobHunt corpus snapshot

The `docs/` folder beside this file is an exact copy of JobHunt's `docs/` at one pinned commit. It is read only input. Never edit it.

It is tracked in git, so every clone and CI run has it.

- **Repo**: https://github.com/ghalynho10/JobHunt
- **Commit**: `2e40bcfe1078cc93ab2f951e6c7c708e4825aa1b`
- **Commit date**: 2026-09-18T05:16:15-04:00
- **Commit subject**: docs(spec): correct spec 0009's cookie disclosure and add AC-24's drift guard
- **Files**: 126, all of `docs/` at that commit, images included

## How it was made

```bash
git -C <jobhunt clone> archive 2e40bcf docs | tar -x -C corpus/jobhunt
```

Each file's `git hash-object` matched its blob at `2e40bcf` when copied, so the bytes are unchanged.

## What reads it

The eval set in `eval/linked-records-research.json` was read against this same commit. Every file its expected chains cite is in this snapshot (checked by `tests/test_corpus.py`, which fails if the snapshot is missing).
