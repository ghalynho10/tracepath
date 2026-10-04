"""Judge experiment 0008's four type sections against spec 0003's AC-36 to AC-38.

No API call: reads `data/run.json`, which `run_coverage.py` writes per unit, and writes
`data/judgement.json`.

* AC-36: in each section, the count of the section's own type differs by at most 1
  across the three runs.
* AC-37: in each section, every run produces the same set of entity types.
* AC-38: no run of a section returns zero items of the section's own type.

Run from the repository root: uv run python <this file>
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: The four sections and the type each is about (spec 0003, AC-36 to AC-38).
SECTIONS = {
    ("0012", "Consequences"): "Consequence",
    ("0012", "Follow-up"): "FollowUp",
    ("0012", "Build plan"): "BuildStep",
    ("0006", "Feature design"): "TestScenario",
}


def judge(entry: dict[str, object], own: str) -> dict[str, object]:
    """One section's verdict on each criterion, with the figures it rests on."""
    runs = entry["types_per_run"]
    assert isinstance(runs, list)
    counts = [int(run.get(own, 0)) for run in runs]
    type_sets = [sorted(run) for run in runs]
    ac36 = max(counts) - min(counts) <= 1
    ac37 = all(s == type_sets[0] for s in type_sets)
    ac38 = min(counts) > 0
    return {
        "section": f"{entry['record']} {entry['section']}",
        "own_type": own,
        "own_type_per_run": counts,
        "types_per_run": runs,
        "AC-36": ac36,
        "AC-37": ac37,
        "AC-38": ac38,
        "passes": ac36 and ac37 and ac38,
    }


def main() -> None:
    """Judge every type section present in the run report and write the verdicts."""
    report = json.loads((HERE / "data" / "run.json").read_text())
    by_key = {(str(e["record"]), str(e["section"])): e for e in report}
    verdicts = [judge(by_key[key], own) for key, own in SECTIONS.items() if key in by_key]
    missing = [f"{r} {s}" for r, s in SECTIONS if (r, s) not in by_key]
    result = {"verdicts": verdicts, "sections_not_run": missing}
    (HERE / "data" / "judgement.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
