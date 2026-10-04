# Review, feat/extraction-stability-on-heterogeneous-units, 2026-10-04

**Reviewed by**: Sonnet 5.5 as the reviewer; the author model was Opus (confirmed by the engineer before the review ran)
**Scope**: 8 source files and 9 test files, plus the experiment scripts for evidence safety only, branch vs main (merge base 666666f)
**Verdict**: Changes requested

## Summary
The branch adds the worked examples block and a cached system prompt, the binding rule label pre check, per unit provenance, richer run artifacts (run id, format version, unit hash, raw response, stop reason, cache counts) and a refusal to overwrite an existing artifact. The source code is tidy and well tested: with the paid calls made impossible, 377 tests passed, 1 xfailed (the documented dropped stream defect), mypy strict, ruff check and ruff format are clean. The headline issues are one import time side effect in client.py and one experiment script (`prepare_blind_reread.py`) that can silently overwrite the engineer's hand marked rulings.

I checked what I read: the full diff of src, client.py lines 225 to 560, artifacts.py write_run and run_path, the examples directory, pyproject.toml packaging, and the experiment scripts' write and move calls. Packaging behavior in item 1 is inferred from pyproject.toml, not run.

## Major
### 🟠 The system prompt reads files at import time, `src/tracepath/extract/client.py:236`
**Problem**: `SYSTEM_PROMPT = RULES + ... few_shot_block(read_examples(EXAMPLES_DIR), ...)` runs at module import and reads seven files from `examples/`, found by `Path(__file__).parents[3] / "examples"`. `cli.py` imports `pipeline`, which imports `client`, so every command, including `tracepath status`, does this on start.
**Why it matters**: AGENTS.md says files live at the edges and module level names are constants only. In practice, a malformed or missing example raises `ExampleError` during import, which reaches the user as a raw traceback, against the rule that failures become a clear message and exit code 1. The build backend is `uv_build` over `src/`, and `examples/` sits at the repo root outside the package, so any non editable install (a built wheel, or `uv tool install`) points at a folder that does not exist and breaks every command. This is inferred from pyproject.toml, not run.
**Suggested fix**: Build the prompt in a function called from the shell (or a cached accessor called by `extract_once`), pass the directory in, and turn `ExampleError` into a typed startup failure that the CLI reports cleanly. Decide whether the examples ship inside the package or the tool is documented as repo only.

### 🟠 Re running `prepare_blind_reread.py` overwrites the engineer's rulings, `experiments/0006-accuracy-bar-recheck/prepare_blind_reread.py:149`
**Problem**: `build()` ends with `BLIND.write_text(...)` and `ANSWERS.write_text(...)` (lines 149 and 150) on `data/blind-reread.md` and `data/blind-reread-answers.md`. The script only checks that its source exists and has enough items, never whether the target already holds marks. The committed `blind-reread.md` carries the engineer's rulings (10 lines of the form `- [x] agree ...`).
**Why it matters**: A casual rerun silently replaces human rulings, which are evidence for the accuracy bar recheck. This is the "rerun that silently replaces evidence" the evidence rule forbids.
**Suggested fix**: Refuse to write when the target already carries a mark, using the same guard `report.py` and `prepare_ruling.py` already have.

Checked and fine: `experiments/0005-held-out-prompt-examples/report.py` (`build()` stops through `already_ruled(SHEET)` before the write at line 383) and `experiments/0006-accuracy-bar-recheck/prepare_ruling.py` (inline guard at lines 74 to 79 before the write at line 144) both refuse to overwrite a marked sheet. My first draft wrongly called them unguarded.

## Minor
### 🟡 Collision is only found after the paid calls are made, `src/tracepath/artifacts.py:222`
**Problem**: `write_run` raises `ArtifactCollisionError` only when called, after `run_unit` has already spent the unit's API calls. The error then loses the fresh `raw_response` that was never written.
**Why it matters**: Safe for evidence, but a rerun into an already populated unit costs real money and keeps nothing. Experiment scripts avoid it by moving first, but the library does not enforce it.
**Suggested fix**: Offer a cheap pre check (does a run file already exist for this unit) that the shell calls before the first call.

### 🟡 Check then write is not atomic, `src/tracepath/artifacts.py:222`
**Problem**: `path.exists()` followed by `write_text` can race and still overwrite.
**Why it matters**: Low risk with one writer, but the guard is meant to be absolute.
**Suggested fix**: Open with exclusive create mode and map `FileExistsError` to `ArtifactCollisionError`.

### 🟡 `baseline_0021.py` move has no collision guard, `experiments/0005-held-out-prompt-examples/baseline_0021.py:61`
**Problem**: `shutil.move(path, destination / path.name)` replaces a same named file already in `artifacts/superseded/2026-09-24-prompt-0002.2/`, unlike `run_units.py` and `run_coverage.py`, which check first.
**Why it matters**: A rerun after the folder exists would overwrite superseded evidence.
**Suggested fix**: Add the same `exists()` check and raise `ArtifactCollisionError`.

### 🟡 No test covers a failed attempt path collision
**Problem**: The collision test covers a settled run only.
**Why it matters**: A `failed-run-*` path is a second place `write_run` must refuse to overwrite.
**Suggested fix**: Add a collision case for `failed-run-*` paths.

**Corrected 2026-10-04**: this item first also said nothing tests `load` stamping each entity from its own unit, because nothing calls `load` yet. That was wrong. `tests/test_reload_artifacts.py:126-145` calls `load` over the committed units, which span more than one prompt version, and asserts every loaded entity carries its own unit's model, prompt version and extraction time.

### 🟡 `prepare_cold_read.py` overwrites its sheet without a guard, `experiments/0006-accuracy-bar-recheck/prepare_cold_read.py:196`
**Problem**: `SHEET.write_text(...)` on `data/cold-read.md` has no check.
**Why it matters**: Low. The cold read was left unruled by decision (spec 0003 AC-30 amended) and passages are drawn with a recorded seed, so a rerun rewrites the same content.
**Suggested fix**: Add the same guard for consistency.

## Nits
- ⚪ `src/tracepath/extract/client.py:362`, `_attempt_from_usage` calls `uuid.uuid4()` inside a helper, so it is not deterministic; passing the id in would keep it pure.
- ⚪ `src/tracepath/artifacts.py:186`, the new fields are listed in the payload in a different order than the dataclass; harmless, but a stable order eases diffs.

## Strengths
- The pre check labels binding rules from the text, never the model, is computed fresh on rebuild, and has tests against the real committed runs (including a negative control with the check skipped).
- The old artifact read path treats missing new fields as null, and tests prove it, so evidence from before the amendment still loads.
- `unit_provenance` raises on mixed models or prompt versions instead of guessing, and the experiment move scripts for 0005 and 0008 refuse to overwrite superseded files.
- The two known defects were left to /debug, with a strict xfail documenting one.

## Test coverage
Strong. New logic in artifacts (collision, round trip, legacy read), ids (`label_binding_rules`), precheck (`read_binding_rules`, including fenced blocks), examples parsing and block assembly, cache block shape, usage mapping and provenance each has direct tests with no mocks of the driver, including the per unit provenance `load` writes (`tests/test_reload_artifacts.py:126-145`, against real Neo4j). The one gap is the failed attempt collision Minor item. The known xfail covers the dropped stream case; I found nothing more to add to either known defect.
