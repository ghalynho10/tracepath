"""Score stage one from the engineer's rulings, no API call (spec 0007 step 7).

Reads the ruled `data/stage-one-packet.md` and the committed `data/stage-one-arms.json`,
refusing an arm file whose hash differs from `data/stage-one-arms.sha256` (AC-26b).
Applies the flip of AC-26e, scores each arm of each unit from the item rulings (AC-27,
AC-27b), applies stage one's gate (AC-19, AC-19c), checks that nothing accepted
without the pass is lost with it (AC-19b), and counts each unit's held items both ways
(AC-28b). Refuses runs whose model is not `units.json`'s (AC-29b) and records whether
every run was extracted after `units.json` was first committed (AC-22b).

Writes `data/stage-one-result.json` and prints one line per unit.

Run from the repository root: uv run python <this file>
"""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from tracepath.measure import (
    CONTROL,
    RELEASED,
    arm_score,
    flip_bundled,
    held_items,
    parse_rulings,
    read_step_units,
    regressions,
    stage_one_verdict,
    unit_gate,
)
from tracepath.pipeline import resolve_accepted
from tracepath.rebuild import committed_units, records_for_units

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"
UNITS = HERE / "units.json"
PACKET = HERE / "data" / "stage-one-packet.md"
ARMS = HERE / "data" / "stage-one-arms.json"
HASH = HERE / "data" / "stage-one-arms.sha256"
RESULT = HERE / "data" / "stage-one-result.json"

SPLIT = "multi_condition_split"


def units_committed_at() -> datetime:
    """When `units.json` was first committed, read from git."""
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%cI", "--", str(UNITS.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return datetime.fromisoformat(out[-1])


def score() -> None:
    """Score every unit and write the result."""
    arms_bytes = ARMS.read_bytes()
    expected_hash = HASH.read_text().split()[0]
    if hashlib.sha256(arms_bytes).hexdigest() != expected_hash:
        raise SystemExit(f"{ARMS.name} does not match the hash committed before the rulings")
    key = json.loads(arms_bytes)
    rulings = parse_rulings(PACKET.read_text())

    step = read_step_units(UNITS, ROOT)
    without_all = committed_units(ROOT, SNAPSHOT)
    with_all = committed_units(ROOT, SNAPSHOT, code_pass=True)
    without = {(r.unit.record_id, r.unit.section): r for r in without_all}
    with_pass = {(r.unit.record_id, r.unit.section): r for r in with_all}
    by_address = {u.address: (u.record, u.section) for u in step.units}

    chosen_at = units_committed_at()
    late = True
    for unit in step.units:
        artifacts = without[(unit.record, unit.section)].artifacts
        models = {a.model for a in artifacts}
        if models != {step.expected_model}:
            raise SystemExit(f"{unit.address} runs name {sorted(models)} (AC-29b)")
        late = late and all(datetime.fromisoformat(a.extracted_at) > chosen_at for a in artifacts)

    # AC-26e reads the entity each item names: flagged when it carries the split flag.
    flagged: set[str] = set()
    for item in key["items"]:
        accepted = with_pass[by_address[item["unit"]]].routed.accepted_entities
        entity = next(e for e in accepted if e.canonical_id == item["canonical_id"])
        if entity.entity.span != item["span"]:
            raise SystemExit(f"{item['opaque_id']}'s span no longer matches its entity")
        if SPLIT in (str(f) for f in entity.entity.known_trap_flags):
            flagged.add(item["opaque_id"])
    ruled, flipped = flip_bundled(rulings, frozenset(flagged))

    records = records_for_units(without_all, SNAPSHOT, COMMIT)
    corpus_without = resolve_accepted(without_all, records)
    corpus_with = resolve_accepted(with_all, records)
    lost = regressions(without_all, with_all, corpus_without, corpus_with, by_address.values())

    units = []
    for unit in step.units:
        place = (unit.record, unit.section)
        ids = {
            arm: [
                i["opaque_id"]
                for i in key["items"]
                if i["unit"] == unit.address and arm in i["arms"]
            ]
            for arm in (RELEASED, CONTROL)
        }
        released = arm_score(ids[RELEASED], ruled)
        control = arm_score(ids[CONTROL], ruled)
        units.append(
            {
                "unit": unit.address,
                "released": vars(released),
                "control": vars(control),
                "gate": unit_gate(released),
                "flipped": [i for i in flipped if i in ids[RELEASED] + ids[CONTROL]],
                "held_items": {
                    "without_pass": held_items(without[place], corpus_without),
                    "with_pass": held_items(with_pass[place], corpus_with),
                },
            }
        )

    result = {
        "verdict": stage_one_verdict((u["gate"] for u in units), lost),
        "units": units,
        "flipped": len(flipped),
        "regressions": list(lost),
        "unruled": sorted(i["opaque_id"] for i in key["items"] if i["opaque_id"] not in rulings),
        "extracted_after_units_committed": late,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n")

    for u in units:
        r, c = u["released"], u["control"]
        print(
            f"{u['unit']}: {u['gate']} · released {r['agree']}/{r['drawn']} agree "
            f"({r['disagree']} disagree, {r['unsure']} unsure, {r['unruled']} unruled) · "
            f"control {c['agree']}/{c['drawn']} agree · held "
            f"{u['held_items']['without_pass']} without, {u['held_items']['with_pass']} with"
        )
    print(
        f"stage one: {result['verdict']} · flipped {len(flipped)} · "
        f"regressions {len(lost)} · extracted after units.json: {late}"
    )


if __name__ == "__main__":
    score()
