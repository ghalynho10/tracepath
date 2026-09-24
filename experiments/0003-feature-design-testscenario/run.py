"""Run one `## Feature design` section three times, the unit AC-14 could not reach.

AC-14's coverage set named six section kinds and none of them held a test scenario:
in this corpus every scenario sits under a bold `**Critical test scenarios**` label
inside `## Feature design`, so `TestScenario` was never exercised. The amendment of
2026-09-23 added that kind, and this is the run it asks for.

Section: 0006 `## Feature design`, chosen as the harder test. It carries 16 scenario
bullets at 14,311 characters, against 0012's 4 at 6,742, and sits close to the mean
`## Feature design` size of 15,407 that the spec names as the risky heterogeneous case.

Artifacts land in `artifacts/runs/`, the source of truth for a rebuild (spec 0001),
because this is real pipeline output rather than a side measurement.
"""

import json
from pathlib import Path

import anthropic

from tracepath.artifacts import review_entry, write_run
from tracepath.config import load_anthropic_settings
from tracepath.extract.ids import section_slugs
from tracepath.extract.schema import EntityType
from tracepath.extract.units import Unit, UnitKind, split_units
from tracepath.pipeline import UnitFailed, UnitResult, run_unit

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
COMMIT = "2e40bcf"
RECORD = "0006"
SECTION = "Feature design"


def target() -> tuple[Unit, str]:
    """The one unit this run extracts, and the slug its derived ids carry."""
    path = next(SNAPSHOT.glob(f"specs/{RECORD}-*/index.md"))
    relative = str(path.relative_to(SNAPSHOT))
    units = split_units(relative, path.read_text())
    own = [u for u in units if u.kind in (UnitKind.SECTION, UnitKind.PREAMBLE)]
    slugs = section_slugs(tuple(u.section for u in own))
    unit = next(u for u in own if u.section == SECTION)
    return unit, slugs[own.index(unit)]


def describe(result: UnitResult) -> dict[str, object]:
    """The same shape experiment 0001 reported, so the table reads the same way."""
    per_run_types: list[dict[str, int]] = []
    for output in result.identified:
        counts: dict[str, int] = {}
        for entity in output.entities:
            counts[str(entity.entity.type)] = counts.get(str(entity.entity.type), 0) + 1
        per_run_types.append(counts)
    return {
        "record": result.unit.record_id,
        "section": result.unit.section,
        "chars": len(result.unit.text),
        "runs_agree": result.routed.comparison.agree,
        "entities_per_run": [len(o.entities) for o in result.identified],
        "types_per_run": per_run_types,
        "test_scenarios_per_run": [
            sum(1 for e in o.entities if e.entity.type is EntityType.TEST_SCENARIO)
            for o in result.identified
        ],
        "unclassified_per_run": [
            sum(1 for e in o.entities if e.entity.type is EntityType.UNCLASSIFIED)
            for o in result.identified
        ],
        "accepted": len(result.routed.accepted_entities),
        "review": len(result.routed.review),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


def main() -> None:
    """Run the unit three times, write its artifacts, and report the table."""
    settings = load_anthropic_settings()
    unit, slug = target()
    extracted_at = "2026-09-23T00:00:00+00:00"

    print(f"{RECORD} / {SECTION}: {len(unit.text)} chars, effort={settings.effort}")
    client = anthropic.Anthropic(api_key=settings.api_key)
    try:
        result = run_unit(client, settings, unit, slug, COMMIT, extracted_at)
    except UnitFailed as exc:
        # The artifacts ride out of the failure rather than dying with it, so a run
        # that produced nothing still leaves its cost on disk. Writing them here is
        # what makes that carrying worth anything (spec 0001 artifact storage).
        for artifact in exc.artifacts:
            print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
        raise

    for artifact in result.artifacts:
        print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))

    entry = describe(result)
    cost = result.input_tokens / 1e6 * 2 + result.output_tokens / 1e6 * 10
    entry["cost_usd"] = round(cost, 4)

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "per-section.json").write_text(json.dumps(entry, indent=2) + "\n")
    (HERE / "data" / "review-queue.json").write_text(
        json.dumps(
            [
                review_entry(
                    result.unit.record_id,
                    result.unit.section,
                    item,
                    settings.model,
                    extracted_at,
                )
                for item in result.routed.review
            ],
            indent=2,
        )
        + "\n"
    )

    print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()
