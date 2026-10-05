"""Run a list of units under one expected prompt version, three calls each (spec 0003).

Used for every paid run of experiment 0005 after the `0021` baseline: the `0002.3`
befores of held out groups B and C, the `0003.0` afters of all three groups (AC-14),
and the `0003.0` type coverage re run (AC-18).

Three guards, each for a mistake that would cost money or evidence:

* The script refuses to run unless `PROMPT_VERSION` is the version asked for, so a
  before can never be measured under the after prompt, or the reverse.
* A unit's committed runs are moved to `artifacts/superseded/<date>-prompt-<their
  version>/` **before** its first call, never deleted and never overwritten by a
  failed attempt (`experiments/README.md`).
* Under a cached prompt, the first unit's later calls must read the cache (AC-19). If
  they read nothing, the run stops there, before the remaining units are paid for at
  the uncached rate.

Run from the repository root:
    uv run python <this file> <expected prompt version> <group> <unit key> [<unit key> ...]
where a unit key is `<record>:<section>`, e.g. `0013:Feature design` or
`feature-9:9. Profile entry · done`.

The `0002.3` befores run the code of commit `972907b` by putting a worktree of it first
on the path (`PYTHONPATH=<worktree>/src`), so the cache fields below are read with a
default: that code has none, and sent no cache marker.
"""

import json
import shutil
import sys
from pathlib import Path

import anthropic

from tracepath.artifacts import RUNS_DIR, ArtifactCollisionError, now_utc, read_run, write_run
from tracepath.config import load_anthropic_settings
from tracepath.extract import client as client_module
from tracepath.extract.client import PROMPT_VERSION
from tracepath.extract.compare import ReviewItem, ReviewReasonName
from tracepath.extract.ids import section_slugs
from tracepath.extract.units import Unit, UnitKind, split_units
from tracepath.pipeline import UnitFailed, UnitResult, run_unit

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
COMMIT = "2e40bcf"
SUPERSEDED_DATE = "2026-09-24"

#: Sonnet 5 rates, dollars per million tokens: input, output, 1 hour cache write, read.
#: Checked against experiment 0004's bill ($1.0185 for its six calls, reproduced exactly).
INPUT_RATE, OUTPUT_RATE, CACHE_WRITE_RATE, CACHE_READ_RATE = 2.0, 10.0, 4.0, 0.2


def target(key: str) -> tuple[Unit, str]:
    """The unit a key names, and the section slug its derived ids carry."""
    record, section = key.split(":", 1)
    if record.startswith("feature-"):
        path = SNAPSHOT / "scope" / "scope.md"
    else:
        path = next(SNAPSHOT.glob(f"specs/{record}-*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    own = [u for u in units if u.record_id == record]
    slugs = section_slugs(tuple(u.section for u in own))
    for unit, slug in zip(own, slugs, strict=True):
        if unit.section == section and unit.kind is not UnitKind.INTRO:
            return unit, slug
    raise SystemExit(f"no unit {key!r} in {path.relative_to(SNAPSHOT)}")


def move_superseded(root: Path, record: str, slug: str) -> list[Path]:
    """Move one unit's committed runs aside, filed under the prompt that made them."""
    source = root / RUNS_DIR / record / slug
    moved: list[Path] = []
    for path in sorted(source.glob("*.json")):
        version = read_run(path).prompt_version
        destination = root / "artifacts" / "superseded" / f"{SUPERSEDED_DATE}-prompt-{version}"
        destination = destination / record / slug
        destination.mkdir(parents=True, exist_ok=True)
        target_path = destination / path.name
        if target_path.exists():
            raise ArtifactCollisionError(f"a superseded artifact already exists at {target_path}")
        moved.append(Path(shutil.move(path, target_path)))
        note = destination / "NOTE.md"
        if not note.exists():
            note.write_text(
                f"Prompt `{version}` runs of `{record}` / `{slug}`, superseded "
                f"{SUPERSEDED_DATE} by a prompt `{PROMPT_VERSION}` run of experiment 0005 "
                "(spec 0003).\n"
            )
    return moved


def cache_tokens(result: object, field: str) -> int:
    """A cache count, or 0 on the `0002.3` code, which never sent a cache marker."""
    value = getattr(result, field, 0)
    return value if isinstance(value, int) else 0


def cost(result: UnitResult) -> float:
    """What one unit's calls cost, each kind of token at its own rate."""
    return round(
        (
            result.input_tokens * INPUT_RATE
            + result.output_tokens * OUTPUT_RATE
            + cache_tokens(result, "cache_creation_input_tokens") * CACHE_WRITE_RATE
            + cache_tokens(result, "cache_read_input_tokens") * CACHE_READ_RATE
        )
        / 1e6,
        4,
    )


def describe(result: UnitResult) -> dict[str, object]:
    """Counts per run, within unit routing, cache use, and cost (AC-15, AC-19)."""
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
        "cache_creation_input_tokens": cache_tokens(result, "cache_creation_input_tokens"),
        "cache_read_input_tokens": cache_tokens(result, "cache_read_input_tokens"),
        "cache_read_per_attempt": [
            cache_tokens(a, "cache_read_input_tokens") for a in result.artifacts
        ],
        "cost_usd": cost(result),
    }


def main(argv: list[str]) -> None:
    """Run each named unit in turn, writing its artifacts and one report per group."""
    if len(argv) < 3:
        raise SystemExit(__doc__)
    expected, group, keys = argv[0], argv[1], argv[2:]
    if expected != PROMPT_VERSION:
        raise SystemExit(f"PROMPT_VERSION is {PROMPT_VERSION}, not {expected}: refusing to run")
    ttl = getattr(client_module, "CACHE_TTL", None)
    cached = ttl is not None
    settings = load_anthropic_settings()
    client = anthropic.Anthropic(api_key=settings.api_key)
    targets = [target(key) for key in keys]
    print(f"prompt {PROMPT_VERSION}, cache {ttl or 'none'}, {len(keys)} units")

    report: list[dict[str, object]] = []
    for position, (unit, slug) in enumerate(targets):
        for path in move_superseded(ROOT, unit.record_id, slug):
            print("  moved", path.relative_to(ROOT))
        try:
            result = run_unit(client, settings, unit, slug, COMMIT, now_utc())
        except UnitFailed as exc:
            # The artifacts ride out of the failure, so what it paid for stays on disk.
            for artifact in exc.artifacts:
                print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
            raise
        for artifact in result.artifacts:
            print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
        entry = describe(result)
        report.append(entry)
        print(json.dumps(entry, indent=2))
        if cached and position == 0 and cache_tokens(result, "cache_read_input_tokens") == 0:
            raise SystemExit(
                "AC-19: the first unit's later calls read nothing from the cache, so the "
                "rest would bill uncached. Stopped before paying for them."
            )

    (HERE / "data").mkdir(exist_ok=True)
    out = HERE / "data" / f"{group}.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    total = sum(float(str(entry["cost_usd"])) for entry in report)
    print(f"{group}: {len(report)} units, ${total:.4f}, report at {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
