# Review, feat/held-item-view, 2026-10-07

**Reviewed by**: Sonnet 5.5 (author on Opus, confirmed by the engineer; corrected 2026-10-07, the first draft said Sonnet 5.5)
**Scope**: 14 code and test files (7 in src, 7 in tests), branch vs main
**Verdict**: Approve with nits

## Summary

The change adds `load --with-held` and `trace --with-held`. Held items are written with a `held` property, `graph_slice()` drops them unless asked, the walk is untouched, and the report scores a clean walk beside a held walk. I read the full code diff and the spec's build sections. I found no blocker and no major. The design follows the spec closely, the default path stays clean, and every held write goes through the asserted `_write()` calls. The issues below are small.

What I checked and how: I read the diff of all seven src files, `build_held_view()` and `load()` in full, the CLI `trace` flow, and the test tags in the six held test files. I did not run the suite (it passed on this commit, 775 tests). Items marked inferred were not run.

## Minor

### 🟡 Held entity and held link review items are told apart by signature length, `src/tracepath/pipeline.py:436`
**Problem**: `len(i.signature) == 2` means an entity item and `== 3` means a link item. That is an unwritten rule about how signatures are built.
**Why it matters**: If a signature ever gains a part, every held item silently lands in the wrong list. The count check at the end would then raise `HeldViewIncomplete`, so it would fail loudly, but the message would point at the wrong cause.
**Suggested fix**: Use a named helper or property on `ReviewItem` (for example "is an entity item") next to where signatures are made, and call that here.

### 🟡 A resolve mismatch would raise a bare ValueError, `src/tracepath/pipeline.py:517`
**Problem**: `zip(resolved.links, pair_reasons, strict=True)` relies on `resolve_endpoints()` returning exactly one link per pair it was given. If it ever drops or merges one, the error is a plain `ValueError`.
**Why it matters**: The project rule is that real failures are typed exceptions the CLI turns into a message and exit 1. `load_graph` does not catch `ValueError`, so the user would see a traceback. Inferred: I did not confirm whether `resolve_endpoints()` can ever drop a link. The spec says it lines up one to one.
**Suggested fix**: Check the two lengths before the zip and raise `HeldViewIncomplete` with a clear message.

### 🟡 The walk.py pin is a hash of the whole file, `tests/test_held_walk.py:33`
**Problem**: AC-7 is tested by a sha256 of `walk.py`. Any later edit to the walk, even a comment or a legitimate feature 11 change, fails this test with no hint on how to proceed.
**Why it matters**: It proves "unchanged since this feature" only while the feature is in flight. After merge it becomes a permanent lock that the next author must know to update.
**Suggested fix**: Say in the test docstring that the hash is to be re-pinned or the test deleted once the feature merges, or replace it with a check against the merge base in a place CI can reach. The accepted known gap on shallow checkouts applies to the second option.

### 🟡 Held step prints a dangling marker if reasons are empty, `src/tracepath/traverse/render.py:27`
**Problem**: `_held(())` returns `  HELD: ` with nothing after it. A held entity or held link that came back with no `held_reasons` prints that.
**Why it matters**: Routing always gives a held entity at least one reason, and `build_held_view()` raises when no review item stands behind it, so this should not happen from `load --with-held`. A hand edited graph or a later change could still produce it, and the output would look like a bug. Inferred from reading, not run.
**Suggested fix**: Print a fixed word such as `no reason stored` when the tuple is empty, or leave as is and note the invariant in the docstring.

## Nits

- ⚪ `src/tracepath/pipeline.py:388`, `build_held_view()` is about 130 lines doing entity claiming, link claiming, resolution, dedupe and the count checks. Splitting the entity pass and the link pass into private functions would make it easier to read and to test.
- ⚪ `src/tracepath/pipeline.py:380`, `_take()` mutates the list passed to it. It is a local copy at every call site, so it is safe, but the name and docstring could say it mutates.
- ⚪ `src/tracepath/graph/model.py:98`, `held_entity_row()` builds a full row and then `del`s `accepted_by`. It works and is local, but it fails with a KeyError if `entity_row()` ever stops writing that key. Building without the key would be steadier.
- ⚪ `tests/test_held_load.py:413`, the test that pins question 3's stdout to the recorded file ties a unit test to committed artifacts. If a later prompt version moves the artifacts this test fails for a reason that is not a bug. Fine for now, worth a comment saying so.

## Strengths

- `graph_slice()` is the single place that decides whether held items are visible, and `drop_held()` also drops links with a dropped end. `walk.py` is untouched, as AC-7 requires.
- Accepted rows are built in the same order and by the same code as before, and held writes run only after all accepted writes finish. All four held writes go through the asserted `_write()` path, so a missing endpoint stops the load.
- `build_held_view()` accounts for every routed row (written, skipped, not written) and raises `HeldViewIncomplete` before any write if the sums differ (AC-19b, AC-23c). This is the "uncertainty is a value, failure is an exception" rule applied well.
- The held link resolution is its own call over all first run entity ids, so a held entity cannot move where an accepted link lands.
- `trace` decides `reached` from the clean walk and prints the held walk, so a held shortcut cannot relabel an item an accepted path reaches (AC-12). A missing start for the held walk and the clean walk is handled without a traceback.
- Tests are tagged to every AC from AC-1 to AC-29b except AC-28, run real Cypher against real Neo4j, and check default output is byte identical with and without held items (AC-3, AC-4, AC-5).

## Test coverage

Every AC in the spec has at least one tagged test except AC-28, whose git order needs history CI's shallow checkout does not hold (the accepted gap; `/check verify` confirmed it live). Corrected 2026-10-07: the first draft said every AC had one. Pure parts (`build_held_view`, `render_chain`, `score`, `graph_slice`) are tested without mocks on a hand built fixture and on the committed artifacts, and the load and trace paths are tested through the real command against real Neo4j. I found no new logic without a test. The known accepted gaps (AC-19b, AC-21, AC-23c by tests only, AC-28 not a test) were not counted. The one gap I would add is a test for the `zip` length mismatch above, which depends on the fix.
