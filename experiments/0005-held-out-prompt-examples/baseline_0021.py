"""The fresh `0002.3` baseline for `0021 ## Requirements`, three calls (spec 0003, AC-13).

This is held out group A's before measurement, taken once, under the current prompt,
before the few shot block changes it. The unit's committed runs are `0002.2`, so they
cannot stand as the before half of a `0003.0` comparison: they are moved aside to
`artifacts/superseded/`, never deleted (`experiments/README.md`), and moved **before**
the first call, because a failed run still writes whatever it paid for into the same
directory and must never overwrite them.

Artifacts land in `artifacts/runs/`, the source of truth for a rebuild (spec 0001).

Run from the repository root: uv run python <this file>
"""

import json
import shutil
from pathlib import Path

import anthropic

from tracepath.artifacts import RUNS_DIR, now_utc, write_run
from tracepath.config import load_anthropic_settings
from tracepath.extract.client import PROMPT_VERSION
from tracepath.extract.compare import ReviewItem, ReviewReasonName
from tracepath.extract.ids import section_slugs
from tracepath.extract.units import Unit, UnitKind, split_units
from tracepath.pipeline import UnitFailed, UnitResult, run_unit

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
COMMIT = "2e40bcf"
RECORD = "0021"
SECTION = "Requirements"

#: The prompt this baseline must run under. The script refuses any other, so it cannot
#: quietly measure the new prompt and call it the before.
BASELINE_PROMPT = "0002.3"

#: Where the replaced runs go, named for the day and the configuration that made them.
SUPERSEDED = Path("artifacts") / "superseded" / "2026-09-24-prompt-0002.2"


def target() -> tuple[Unit, str]:
    """The one unit this run extracts, and the slug its derived ids carry."""
    path = next(SNAPSHOT.glob(f"specs/{RECORD}-*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    own = [u for u in units if u.kind in (UnitKind.SECTION, UnitKind.PREAMBLE)]
    slugs = section_slugs(tuple(u.section for u in own))
    unit = next(u for u in own if u.section == SECTION)
    return unit, slugs[own.index(unit)]


def move_superseded(root: Path, slug: str) -> list[Path]:
    """Move the unit's committed runs aside, with a note saying why. Returns what moved."""
    source = root / RUNS_DIR / RECORD / slug
    destination = root / SUPERSEDED / RECORD / slug
    moved: list[Path] = []
    for path in sorted(source.glob("*.json")):
        destination.mkdir(parents=True, exist_ok=True)
        moved.append(Path(shutil.move(path, destination / path.name)))
    if moved:
        (destination / "NOTE.md").write_text(
            f"Prompt `0002.2` runs of `{RECORD} ## {SECTION}`, superseded 2026-09-24 by a "
            "fresh `0002.3` baseline (spec 0003, AC-13), so the before and after "
            "comparison is not a mixed prompt version one.\n"
        )
    return moved


def describe(result: UnitResult) -> dict[str, object]:
    """Counts per run, within unit routing, and what the calls cost."""
    entity_rows = [item for item in result.routed.review if item.canonical_id is not None]
    link_rows = [item for item in result.routed.review if item.canonical_id is None]

    def with_reason(items: list[ReviewItem], name: ReviewReasonName) -> int:
        return sum(1 for item in items if any(reason.name is name for reason in item.reasons))

    counts = [len(o.entities) for o in result.identified]
    return {
        "record": result.unit.record_id,
        "section": result.unit.section,
        "prompt_version": PROMPT_VERSION,
        "chars": len(result.unit.text),
        "entities_per_run": counts,
        "entity_spread": max(counts) - min(counts),
        "relationships_per_run": [len(o.relationships) for o in result.identified],
        "entity_rows_runs_disagree": with_reason(entity_rows, ReviewReasonName.RUNS_DISAGREE),
        "relationship_rows_runs_disagree": with_reason(link_rows, ReviewReasonName.RUNS_DISAGREE),
        "relationship_rows_endpoint_not_accepted_in_unit": with_reason(
            link_rows, ReviewReasonName.ENDPOINT_NOT_ACCEPTED
        ),
        "accepted_entities": len(result.routed.accepted_entities),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": round(result.input_tokens / 1e6 * 2 + result.output_tokens / 1e6 * 10, 4),
    }


def main() -> None:
    """Move the old runs aside, run the unit three times, write artifacts and a report."""
    if PROMPT_VERSION != BASELINE_PROMPT:
        raise SystemExit(
            f"PROMPT_VERSION is {PROMPT_VERSION}, not {BASELINE_PROMPT}: this baseline "
            "measures the prompt before the few shot block, so it cannot run now"
        )
    settings = load_anthropic_settings()
    unit, slug = target()
    print(f"{RECORD} / {SECTION}: {len(unit.text)} chars, effort={settings.effort}")

    for path in move_superseded(ROOT, slug):
        print("  moved", path.relative_to(ROOT))

    client = anthropic.Anthropic(api_key=settings.api_key)
    try:
        result = run_unit(client, settings, unit, slug, COMMIT, now_utc())
    except UnitFailed as exc:
        # The artifacts ride out of the failure, so a run that produced nothing still
        # leaves its cost on disk (spec 0001 artifact storage).
        for artifact in exc.artifacts:
            print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
        raise

    for artifact in result.artifacts:
        print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))

    entry = describe(result)
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "baseline-0021.json").write_text(json.dumps(entry, indent=2) + "\n")
    print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()
