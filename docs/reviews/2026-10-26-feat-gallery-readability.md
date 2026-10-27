# Review, feat/gallery-readability, 2026-10-26

**Reviewed by**: Claude Sonnet 5.5 (author on Claude Opus 5.5)
**Scope**: 19 files, branch vs main (merge base 316c637, HEAD 835b998; code ends at 2ff11db)
**Verdict**: Approve with nits
**Tier note**: Feature 19 is Beta tier. This is an extra review you asked for. It does not change the tier, and Beta has no Review it box, so it adds none.

## Summary

The change adds a pure `inline.py` that turns `code` and **bold** in stored text into runs. The list writes each run as escaped HTML, and the graph panel draws the same runs with `textContent`. It also rebuilds each entry with a flat heading order, a verdict and mark block, a graph strip, a total of your marks, and a link to one graph by `#<slug>`. I found no blocker and no major problem. Escaping is sound, the parser follows the spec, and the tests are strong. Two small points are listed below. The browser criteria were already met in `docs/reviews/2026-10-26-check-verify-gallery-readability.md`, and I did not re-check them.

## Minor

### 🟡 A ruling path can climb out of `experiments/` and link into `docs/`, `src/tracepath/gallery/records.py:309` and `src/tracepath/gallery/render.py:656`
**Problem**: The build only checks `source_path.startswith("experiments/")`, then that the resolved path is a file under the build root. A path like `experiments/../docs/scope/scope.md` passes both checks. The page would then link "My full ruling" to `blob/main/experiments/../docs/...`, and `quote()` keeps the `..`.
**Why it matters**: Spec 0012 AC-62 and the Key invariants say the built page holds no link into `docs/`, because `docs/` leaves the public repository after merge. No such path exists in `gallery/marks.json` today, and you write that file yourself, so this is a guard gap and not a live bug. The existing `_is_plain_name` check for `record` already rejects `..`, so the file is inconsistent with itself.
**Suggested fix**: Reject a `source_path` that contains `..` or a backslash in the same place the `experiments/` file check runs, with a clear error naming the entry. One short test next to the existing AC-61 test. Per `docs/reflexes.md` this is cheap and guards a stated invariant, so it passes the filter. If you decide the marks file is trusted, skip it.

### 🟡 `has_pair` and `runs_of` treat any code word run as a "marker pair", `src/tracepath/gallery/inline.py:152` and `src/tracepath/gallery/graph.py:108`
**Problem**: `runs_of` calls `runs(text)` with `code_words` off, so today only explicit markers make code or bold runs and the name is right. But `has_pair` is public and its docstring says "that is, the text held a marker pair". If someone later calls it on `runs(text, code_words=True)`, an item with only a bare file name would get a `runs` key and break AC-98.
**Why it matters**: Low. Nothing does this now, and the spec's tests would catch it. It is a trap for a later change.
**Suggested fix**: Say in the `runs_of` docstring that it must stay on `code_words=False`, or keep as is. Optional.

## Nits

- ⚪ `src/tracepath/gallery/render.py:508` `_formatted` wraps every text in `<span class="stored">`, including the entry's note, so `.stored { white-space: pre-wrap }` applies to it. That is intended (it keeps line breaks), but the note you are rewriting will show any newline you type, so keep each note on one line unless you want a break.
- ⚪ `src/tracepath/gallery/render.py:764` `_key_list` takes already escaped terms and escapes only the description. It works and is tested, but the "term is trusted HTML" rule is not in its docstring (it has none). A one line docstring would make that safe to keep.
- ⚪ `src/tracepath/gallery/render.py:663` `_source` writes `project&#x27;s` as a literal entity inside a string. It renders right. Using the plain apostrophe through `escape()` would match the rest of the file.

## Strengths

- Escaping is done in one place. Every run goes through `html.escape` in `to_html`, `graph.js` uses `createElement` and `textContent` only, and a test pins that `innerHTML` is never set. I read both paths end to end and found no way for stored markup to reach the page as markup. The data block escapes `<` and friends as `\u` sequences.
- `inline.py` is a clean functional core: frozen `Run`, pure functions, one line at a time, double backticks ignored, unpaired markers left as typed. The "rebuild the stored text" property over all 2,602 stored texts is a better test than examples would be.
- The graph link code only uses `history.replaceState`, matches the fragment against the registry of slugs and not against element ids (so `#gw-key` cannot reach `open`), and a static test pins that `pushState` and `location.hash =` never appear.
- An unknown verdict code fails the build with the record named, because `verdict` is now a `Literal` and the validation error is turned into `GalleryError`.
- The marks and verdict words are separate constant tables, so no verdict wording can equal a mark word, and the swipe colours are kept out of the graph styles.
- Both findings of the check verify run are already handled: `verify.md` line 55 now names `tests/test_gallery_code_tint.py`, and commit e648edb spaces the panel's verdict below its question.

## Test coverage

I ran `uv run pytest -m "not integration" tests/test_gallery*.py` (277 passed), `uv run mypy` (clean, 118 files), `uv run ruff check .` (clean) and `uv run ruff format --check .` (clean). New logic is well covered: the inline rule has fixtures for each edge (unpaired, line break, double backticks, `**` in code, bold code, markup inside spans), plus real record properties for the rebuild rule, the pinned code word list, the pinned marks, the verdict codes with an unknown one, the strip's attributes and position, the total line, the source line rules, the `experiments/` file check, and the static checks on `graph.js` and the tint rule. The one untested path is the `..` case in the first Minor above. `graph.js` has no CI test, so I judged it by reading: the new functions are small, build nodes only with `textContent`, and match the Python `to_html` structure (the `g` glue elements and the `w` word elements).
