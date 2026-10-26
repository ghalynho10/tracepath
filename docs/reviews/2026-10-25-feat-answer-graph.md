# Review, feat/answer-graph, 2026-10-25

**Reviewed by**: Claude Sonnet 5.5 (author on a different model)
**Scope**: 22 files, branch vs main (merge base f27f433)
**Verdict**: Approve with nits

## Summary

The branch adds an interactive graph to each gallery answer. Python decides every item's state (`graph.py`), `records.py` checks the new data, `render.py` writes the dialog and data blocks, and a 650 line script draws from the flags. You get a clean split: the script reads flags and decides nothing about an item. I found no blocker and no major. The remaining points are small: a few acceptance criteria that hold more than one claim, a couple of wording gaps between spec and code, and some low risk script details.

What I ran: `uv run ruff check .` and `ruff format --check` (clean), `uv run mypy` (clean, 114 files), and `uv run pytest -m "not integration" tests/test_gallery.py tests/test_gallery_graph.py` (155 passed). No paid call, no Neo4j, and I never touched `eval/held-out.json`. I also did not re run the browser checks, since the verify review at `docs/reviews/2026-10-25-check-verify-answer-graph.md` already did. I found nothing in the code that contradicts it.

## Minor

### 🟡 Several acceptance criteria hold more than one claim, `docs/specs/0011-answer-graph/index.md:46`
**Problem**: The project rule is one claim per criterion. These bundle several: AC-22 (no yellow, no pink, and cyan only for the ring), AC-62 (distinct ids, first link order, and leaving out itself), AC-84 and AC-85 (selects, or drags), AC-87 (stored case, shortening with "…", and the full id in the tooltip and panel), AC-48 (type, direction, other id and phrase), AC-94 (order, and null when not cited). AC-14 and AC-16 each give a radius, a fill and an opacity.
**Why it matters**: A test tagged with one number reads as covering all of it. For example `test_neighbours_are_the_distinct_other_ends_in_first_link_order` does cover AC-62's three parts, but AC-87 has no Python test at all and its three parts can only be checked in a browser.
**Suggested fix**: Split the worst ones (AC-22, AC-62, AC-87) into lettered criteria, or accept it and say so in verify.md. This is a spec edit, not a code change.

### 🟡 AC-34 and the dimming code can be read two ways, `src/tracepath/gallery/assets/graph.js:299`
**Problem**: AC-34 says selecting an item dims everything except "that item, its neighbours and the lines between them". `select()` keeps only the lines that touch the selected item at full strength. A line between two neighbours (not touching the selected item) is dimmed. The Drawings table says "on the selected item, its links turn full ink", which matches the code, so the code follows the table and the criterion is the loose one.
**Why it matters**: Someone writing a browser check from AC-34 alone could expect neighbour to neighbour lines to stay bright and call the code wrong.
**Suggested fix**: Reword AC-34 to "the lines that touch that item", or change the code. Pick one; I think the wording is the right thing to change.

### 🟡 A source link in the panel leaves the page in the same tab, `src/tracepath/gallery/assets/graph.js:407`
**Problem**: The JobHunt link in the item view is a plain anchor with no `target`. A click navigates away and throws the open graph, selection and layout away. The list's own links behave the same way, so this matches spec 0010, but the dialog makes losing your place more costly.
**Why it matters**: A reader who clicks "check it myself" (the user story for AC-46) has to press Back and reopen the graph.
**Suggested fix**: Decide whether the panel link should open in a new tab (`target="_blank"` with `rel="noopener"`). If you keep it as is, it is fine; I am flagging it as a choice rather than a fault. The verify review does not mention it.

## Nits

- ⚪ `src/tracepath/gallery/records.py:197`, `_inline_text` refuses `</script` and `<!--` but the licence is pasted inside `/* ... */` (`render.py` `_scripts`). A licence text holding `*/` would end the comment early. The four ISC files do not, so this cannot happen today; a one line check would close it.
- ⚪ `src/tracepath/gallery/assets/graph.js:171`, `place()` calls `arrangeLabels()` on every simulation tick while a dot is dragged, and that loop compares every shown cited label with every other. At the 90 item maximum it is fine; if packs grow it is the first place to look.
- ⚪ `src/tracepath/gallery/graph.py:156`, `lines = dict(zip(ids, entry.items, strict=True))` relies on `checked_items` returning lines in the same order as `record.items`. That holds today (verified in `records.py`), and `strict=True` guards the length, but the order link is silent. A short comment would help.

## Strengths

- The flags really are pure functions of the record, and the tests recompute them independently for all 31 records (cited, held, unresolved, neighbours, near_cited, cited_by, cite_order), including the edge cases in the spec (self links, double links, rejected ids, Q11 and Q16 citing nothing).
- Failures follow the project rule: typed `GalleryError`, turned into a clear message and exit 1 in `cli.py`, naming the record and link, the record and id, both entries, or the script, with tests for each.
- The data block escaping is done on the finished JSON text, which is safe because JSON syntax holds none of the escaped characters, and a hostile string test (`</script>`, `<!--`, `&`, U+2028, U+2029) runs through the whole page.
- The script uses `textContent` everywhere, never puts an id in a selector or element id, and keeps a `Map` for lookups, so ids with `#`, `:` and `/` are handled.
- Vendored files match SOURCES.md: four packages with pinned versions, four licence files of equal size (731 bytes), inlined in dependency order with each licence after its code, and tests that parse the table. I did not read the minified internals, as asked.
- No Co-Authored-By trailer in any of the 15 branch commits; commits are conventional.

## Test coverage

Python side: well covered. 40 tests in `tests/test_gallery_graph.py` cover the data, the guards, the escaping round trip, the vendor table, the self contained page and the cyan and key rules, on top of the existing gallery tests. Both failing and passing sides of AC-68 are tested.

Script side: no JavaScript test runs in CI, which spec 0011 states openly under Consequences. Pan, zoom, the switch, drag, hit reach and focus (AC-3 to AC-11, AC-26 to AC-35, AC-77 to AC-93) rest on the one time browser run in the verify review. A regression in `graph.js` would not fail a push. That is accepted by the spec and I do not raise it as a finding, but it is the main thing a later change could break unseen.
