"""Draw stage one's blind sample and write its packet, no API call (spec 0007 step 7).

Per chosen unit, 5 entity marks drawn at random from the entities the code pass
releases (AC-25b) and 3 from the control arm's accepted entities (AC-25), each draw
with its own seed (AC-25c). A draw asking for more than exist takes all there are and
the shortfall is stated (AC-25d). The marks are mixed per unit, shuffled and numbered
under opaque ids (AC-26), and the packet shows each item's id, span, type and source
line only (AC-26d).

Three files are written under `data/`:

- `stage-one-packet.md`, the packet the engineer rules;
- `stage-one-arms.json`, the arm file: every seed, every draw and each item's arm.
  It stays uncommitted until the rulings are in (AC-26c);
- `stage-one-arms.sha256`, the arm file's hash, committed before the rulings (AC-26b).

The seeds are drawn fresh by `secrets`, not written here, so the arms cannot be
recomputed from committed code before the arm file itself is committed; the arm file
records them, and its hash shows they were fixed before any ruling. The script refuses
to run once any of the three files exists, so a sample is never drawn twice.

Prints the packet's path, the number of items per unit and any shortfall, nothing
that names an item's arm.

Run from the repository root: uv run python <this file>
"""

import hashlib
import json
import secrets
from pathlib import Path

from tracepath.measure import (
    CONTROL,
    RELEASED,
    Draw,
    arm_key,
    build_packet,
    control_marks,
    draw,
    packet_markdown,
    read_step_units,
    released_marks,
)
from tracepath.rebuild import committed_units

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
UNITS = HERE / "units.json"
PACKET = HERE / "data" / "stage-one-packet.md"
ARMS = HERE / "data" / "stage-one-arms.json"
HASH = HERE / "data" / "stage-one-arms.sha256"

RELEASED_PER_UNIT = 5
CONTROL_PER_UNIT = 3

INTRO = """\
Stage one of spec 0007 (AC-19, AC-25 to AC-26d). Each unit below holds up to 8 entity
marks drawn at random and mixed blind, under opaque ids in shuffled order. The arm of
each item is in `stage-one-arms.json`, whose hash is committed in
`stage-one-arms.sha256`; the arm file itself is committed only after the rulings.

Replace each item's marks with one word: `agree` when the cut and type pass HANDOFF's
three question test (atomicity, referenceability, right sizing) and the deletion trick,
`disagree` otherwise, `unsure` when you cannot tell. Add a few words on why after
`reason:` when you disagree or are unsure. Tag `gap:bundled-ac` in the reason when you
rule a bundled criterion agree by the convention (AC-26e). Every item is ruled: in the
gate, `unsure`, `disagree` and an unruled item all count against (AC-18c, AC-19)."""


def _seed() -> int:
    """A fresh seed, recorded in the arm file, not in code."""
    return secrets.randbits(48)


def build() -> None:
    """Draw every unit's sample, write the packet, the arm file and its hash."""
    existing = [p.name for p in (PACKET, ARMS, HASH) if p.exists()]
    if existing:
        raise SystemExit(f"{', '.join(existing)} already exist; a sample is drawn once")

    step = read_step_units(UNITS, ROOT)
    without = {(r.unit.record_id, r.unit.section): r for r in committed_units(ROOT, SNAPSHOT)}
    with_pass = {
        (r.unit.record_id, r.unit.section): r
        for r in committed_units(ROOT, SNAPSHOT, code_pass=True)
    }

    draws: list[Draw] = []
    for unit in step.units:
        key = (unit.record, unit.section)
        if key not in without:
            raise SystemExit(f"{unit.address} is not fully extracted")
        models = {a.model for a in without[key].artifacts}
        if models != {step.expected_model}:
            # Scoring refuses such runs (AC-29b), so drawing from them would be wasted.
            raise SystemExit(
                f"{unit.address} runs name {sorted(models)}, not {step.expected_model}"
            )
        draws.append(
            draw(
                unit.address,
                RELEASED,
                released_marks(with_pass[key], unit.address),
                RELEASED_PER_UNIT,
                _seed(),
            )
        )
        draws.append(
            draw(
                unit.address,
                CONTROL,
                control_marks(without[key], unit.address),
                CONTROL_PER_UNIT,
                _seed(),
            )
        )

    shuffle_seed = _seed()
    addresses = [u.address for u in step.units]
    items = build_packet(draws, addresses, shuffle_seed)

    PACKET.parent.mkdir(exist_ok=True)
    PACKET.write_text(packet_markdown(items, "Stage one packet, experiment 0012", INTRO))
    arms = (json.dumps(arm_key(items, draws, shuffle_seed), indent=2) + "\n").encode()
    ARMS.write_bytes(arms)
    HASH.write_text(f"{hashlib.sha256(arms).hexdigest()}  {ARMS.name}\n")

    print(f"packet: {PACKET.relative_to(ROOT)}")
    for address in addresses:
        count = sum(1 for i in items if i.mark.unit == address)
        print(f"{address}: {count} items")
    for d in draws:
        if d.shortfall:
            print(f"shortfall: {d.unit} {d.arm} draw asked {d.asked}, drew {len(d.marks)}")


if __name__ == "__main__":
    build()
