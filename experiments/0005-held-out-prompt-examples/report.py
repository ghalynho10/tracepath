"""The held out before and after table, the label invention check, and the ruling sample.

No API call. Everything is rebuilt from committed artifacts: the afters from
`artifacts/runs/`, the befores of all three groups from
`artifacts/superseded/2026-09-24-prompt-0002.3/`, where the after run moved them. Both
are re-located and re-routed by the current code, so before and after are measured by
one method.

Three outputs (spec 0003):

* `data/heldout-table.json`: per group, the entity column (count spread, entity rows
  under `runs_disagree`) and the relationship column (rows under `runs_disagree` and,
  separately, under `endpoint_not_accepted`), before and after (AC-14, AC-15), plus
  group B's spread against the threshold of 2 (AC-17).
* The label invention check (build plan task 14): every model set entity `label` in
  the after runs, split into those found verbatim in their own span and those not.
* `data/ruling-sample.md`: about 10 items per after run for the engineer to rule on
  against HANDOFF's three question test and the deletion trick (AC-16). The sample is
  fixed and deterministic: 10 entities evenly spaced through run 1's located order.

Run from the repository root: uv run python <this file>
"""

import json
from pathlib import Path

from tracepath.artifacts import RUNS_DIR, RunArtifact, read_run
from tracepath.extract.compare import ReviewItem, ReviewReasonName, route_runs
from tracepath.extract.ids import IdentifiedOutput, assign_ids, label_binding_rules, locate_output
from tracepath.rebuild import unit_for

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
SUPERSEDED = ROOT / "artifacts" / "superseded" / "2026-09-24-prompt-0002.3"

#: The three held out groups: record, section slug, and what each one tests.
GROUPS = {
    "A": ("0021", "requirements", "a unit kind with no worked example"),
    "B": ("0013", "feature-design", "a kind with an example, different content"),
    "C": ("feature-9", "9-profile-entry-done", "a different scope row than the example's"),
}

#: The widest entity spread any stable committed unit showed (AC-17).
SPREAD_THRESHOLD = 2

#: How many items the engineer rules on per after run (AC-16).
SAMPLE_SIZE = 10


def runs_in(directory: Path) -> list[RunArtifact]:
    """The settled runs of one unit, in run order."""
    return sorted((read_run(p) for p in directory.glob("run-*.json")), key=lambda a: a.run)


def identify(runs: list[RunArtifact]) -> tuple[IdentifiedOutput, ...]:
    """Re-locate and re-identify each run with the current code, as a rebuild does."""
    unit = unit_for(runs[0], SNAPSHOT)
    return tuple(
        assign_ids(
            label_binding_rules(unit, locate_output(unit, a.output)),
            unit.record_id,
            a.section_slug,
        )
        for a in runs
        if a.output is not None
    )


def columns(identified: tuple[IdentifiedOutput, ...]) -> dict[str, object]:
    """The entity and relationship columns for one unit's three runs (AC-15)."""
    routed = route_runs(identified)
    entity_rows = [i for i in routed.review if i.canonical_id is not None]
    link_rows = [i for i in routed.review if i.canonical_id is None]

    def with_reason(items: list[ReviewItem], name: ReviewReasonName) -> int:
        return sum(1 for item in items if any(r.name is name for r in item.reasons))

    counts = [len(o.entities) for o in identified]
    return {
        "entities_per_run": counts,
        "entity_spread": max(counts) - min(counts),
        "entity_rows_runs_disagree": with_reason(entity_rows, ReviewReasonName.RUNS_DISAGREE),
        "relationships_per_run": [len(o.relationships) for o in identified],
        "relationship_rows_runs_disagree": with_reason(link_rows, ReviewReasonName.RUNS_DISAGREE),
        "relationship_rows_endpoint_not_accepted": with_reason(
            link_rows, ReviewReasonName.ENDPOINT_NOT_ACCEPTED
        ),
    }


def label_check(identified: tuple[IdentifiedOutput, ...]) -> dict[str, object]:
    """Every model set entity label, found verbatim in its own span or not (task 14)."""
    found: list[str] = []
    invented: list[str] = []
    for output in identified:
        for entity in output.entities:
            label = entity.entity.label
            if label is None:
                continue
            (found if label in entity.entity.span else invented).append(label)
    return {"verbatim_in_span": found, "not_in_span": invented}


def sample(output: IdentifiedOutput) -> list[dict[str, object]]:
    """Ten entities evenly spaced through one run's located order (AC-16)."""
    ordered = sorted(
        output.entities,
        key=lambda e: (e.location is None, e.location.offset if e.location else 0),
    )
    if len(ordered) <= SAMPLE_SIZE:
        picked = ordered
    else:
        step = len(ordered) / SAMPLE_SIZE
        picked = [ordered[int(i * step)] for i in range(SAMPLE_SIZE)]
    return [
        {
            "id": e.canonical_id,
            "type": str(e.entity.type),
            "label": e.entity.label,
            "span": e.entity.span,
            "rejected_spans": list(e.entity.rejected_spans),
            "flags": [str(f) for f in e.entity.known_trap_flags],
        }
        for e in picked
    ]


def main() -> None:
    """Build the table, the label check and the ruling sample, and write all three."""
    table: dict[str, object] = {}
    sheet = [
        "# Ruling sample, experiment 0005 (AC-16)",
        "",
        "For each item: does it pass HANDOFF's three question test (atomicity, "
        "referenceability, right sizing) and the deletion trick? Mark `agree` when the "
        "model's cut and type are what you would have written, `disagree` otherwise, "
        "with a word on why. Sample: 10 entities evenly spaced through run 1's located "
        "order, per group.",
    ]
    for name, (record, slug, what) in GROUPS.items():
        after = identify(runs_in(ROOT / RUNS_DIR / record / slug))
        before_dir = SUPERSEDED / record / slug
        before = identify(runs_in(before_dir)) if before_dir.exists() else ()
        after_columns = columns(after)
        entry: dict[str, object] = {
            "unit": f"{record} / {slug}",
            "tests": what,
            "before": columns(before) if before else None,
            "after": after_columns,
            "label_check_after": label_check(after),
        }
        if name == "B":
            spread = int(str(after_columns["entity_spread"]))
            entry["ac17_threshold"] = SPREAD_THRESHOLD
            entry["ac17_test_ac2"] = spread > SPREAD_THRESHOLD
        table[name] = entry
        sheet += ["", f"## Group {name}: {record} / {slug} ({what})", ""]
        for item in sample(after[0]):
            sheet += [
                f"- [ ] agree / disagree · `{item['id']}` · {item['type']}"
                + (f" · label `{item['label']}`" if item["label"] else ""),
                f"  - span: {item['span']}",
            ]
            if item["rejected_spans"]:
                sheet.append(f"  - rejected: {item['rejected_spans']}")
            if item["flags"]:
                sheet.append(f"  - flags: {', '.join(str(f) for f in item['flags'])}")

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "heldout-table.json").write_text(json.dumps(table, indent=2) + "\n")
    (HERE / "data" / "ruling-sample.md").write_text("\n".join(sheet) + "\n")
    print(json.dumps(table, indent=2))


if __name__ == "__main__":
    main()
