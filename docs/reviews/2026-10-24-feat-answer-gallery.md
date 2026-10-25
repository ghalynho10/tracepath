# Review, feat/answer-gallery, 2026-10-24

**Reviewed by**: Sonnet 5.5 (author on Opus 5.5)
**Scope**: 15 files, branch vs main
**Verdict**: Approve with nits

## Summary
This change adds `tracepath gallery build`, a pure renderer, a record and marks loader, a citation parser, the marks file with 31 entries, and the Pages workflow. The code follows the spec and the project rules. Failures are typed, exit 1, and no traceback reaches you. I found no blockers and no majors. The notes below are small.

I ran the allowed checks. `pytest -m "not integration"` on the three gallery test files gave 112 passed. `mypy` and `ruff check` and `ruff format --check` are clean. I did not run integration tests, paid calls or anything that touches the held out file.

## Minor
### 🟡 A snapshot file that cannot be read raises a raw error, `src/tracepath/gallery/records.py:224`
**Problem**: `_line_count` calls `read_text` with no handler. A snapshot file that is not valid UTF-8, or cannot be opened, raises `UnicodeDecodeError` or `OSError`, not `GalleryError`.
**Why it matters**: The project rule says failures are typed and the CLI never shows a raw traceback. Today the pinned snapshot is fine, so this only bites on a damaged checkout.
**Suggested fix**: Catch `OSError` and `UnicodeDecodeError` there and raise `GalleryError` naming the file.

### 🟡 A marks `record` value is joined into a path without a check, `src/tracepath/gallery/records.py:203`
**Problem**: `root / ASKS_DIR / entry.record` accepts a value like `../x.json`. The file would be read from outside `artifacts/asks/`.
**Why it matters**: The marks file is committed and written by you, so the risk is low. It does break the invariant that only records in `artifacts/asks/` are shown (AC-1).
**Suggested fix**: Refuse a `record` that has a path separator or is not a bare file name. This is a few lines, so it fits the cheap guard rule.

## Nits
- ⚪ `src/tracepath/gallery/render.py:243`, `asked_at.astimezone(UTC)` on a naive datetime would use the local zone. Stored values carry a zone today, so no change needed unless a record lacks one.
- ⚪ `src/tracepath/gallery/render.py:167`, label text at 10px and the `--ink-46` colour are small and pale for the evidence a reader checks. Consider 11px.
- ⚪ `docs/specs/0010-answer-gallery/index.md:233`, Follow-up items for the mark wording and the visual design are still unchecked, though both are done in this branch. Tick them.
- ⚪ `docs/specs/0010-answer-gallery/index.md:196`, task 2 is still open (the Pages setting and the public URL). This is correct for now, but it must be closed before the feature counts as shipped.

## Strengths
- The functional core and shell split is clean: `citations.py` and `render.py` are pure, and all file reading sits in `records.py` and the CLI.
- Every stored text goes through `escape`, and links are built only after the file and line are checked against the pinned snapshot.
- `claim_marks` was pulled out of `ask/answer.py`, so the page and the terminal share one rule for labels instead of two copies.
- The build refuses an `--out` inside `artifacts/` or `corpus/`, and the tests prove it.
- The workflow has a separate deploy job with `needs: build`, and a test reads that line.
- Commits follow the convention and carry no Co-Authored-By trailer.

## Test coverage
Coverage is good. The 58 tests in `tests/test_gallery.py`, plus `tests/test_gallery_citations.py` and `tests/test_pages_workflow.py`, cover each failure path (AC-5 to AC-7, AC-10, AC-11, AC-37 to AC-42), the no line and six field cases, escaping, the sockets blocked build, the read only folders, the SNAPSHOT commit match and the workflow lines. The only untested paths are the two in the Minor section, which are unreachable with today's committed data.
