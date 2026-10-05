"""Build the re check's ruling sheet, no API call (spec 0003, AC-30).

Rebuilds the after and before runs from committed artifacts with today's code (as a
rebuild always does), then writes one ruling sheet section per unit: 10 entities
evenly spaced through after run 1's located order, 5 relationships evenly spaced
through the after runs' distinct links, and 15 dropped links (written by a before run,
by no after run) drawn at random, the seed recorded so the draw is reproducible.

Every sample is left for the engineer to rule; this never marks a line itself. AC-30
allows no unruled items in the entity and relationship samples once ruled, and rules
the dropped link sample too; the cold read and blind self agreement checks it also
asks for are not built here, they need a human step this script cannot prepare.

Run from the repository root: uv run python <this file>
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "0005-held-out-prompt-examples"))
from report import (
    UNRULED,
    Link,
    distinct_links,
    entity_lines,
    entity_sample,
    evenly,
    link_lines,
    runs_in,
)

from tracepath.extract.ids import assign_ids, label_binding_rules, locate_output
from tracepath.rebuild import unit_for

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
SHEET = HERE / "data" / "ruling-sheet.md"

#: The three re check units, and the before dir they settled into after the run
#: (relocated by hand from `run_units.py`'s own, differently dated, default).
UNITS = [
    ("0014", "requirements", "Requirements, no prior worked example of this record"),
    ("0015", "feature-design", "Feature design, no prior worked example of this record"),
    (
        "feature-33",
        "33-band-anchor-review-done",
        "Scope feature row, no prior worked example of this record",
    ),
]
BEFORE_DIR = ROOT / "artifacts" / "superseded" / "2026-09-28-prompt-0002.3"

ENTITY_SAMPLE, LINK_SAMPLE, DROPPED_SAMPLE = 10, 5, 15
DROPPED_SEED = 20260928


def identify(runs: list) -> tuple:  # type: ignore[type-arg]
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


def build() -> None:
    """Build the ruling sheet's three sections per unit, and write it."""
    if SHEET.exists() and any(
        line.startswith("- [") and not any(mark in line for mark, _ in UNRULED.values())
        for line in SHEET.read_text().splitlines()
    ):
        raise SystemExit(f"{SHEET.name} already carries a ruling; not overwriting it")

    rng = random.Random(DROPPED_SEED)
    sheet = [
        "# Ruling sheet, experiment 0006 (spec 0003, AC-30)",
        "",
        "Replace each line's marks with one word, and add a few words on why when you "
        "disagree, matching experiment 0005's own ruling-sheet.md convention. No item "
        "in the entity or relationship sample is left unruled; `unsure` is allowed and "
        "counted on its own, neither agree nor disagree.",
        "",
        "- **Entities**: `agree` when the model's cut and type pass HANDOFF's three "
        "question test (atomicity, referenceability, right sizing) and the deletion "
        "trick, `disagree` otherwise.",
        "- **Relationships**: `agree` when the link is real, and its type, direction "
        "and endpoints are what you would have written, `disagree` otherwise.",
        "- **Dropped links**: `real link lost` when the source text states a relation "
        "the afters should have kept, `rightly dropped` when it does not. Drawn at "
        f"random, seed `{DROPPED_SEED}`, reproducible by re-running this script.",
        "",
        "Not built here, needed before the bar can be applied (AC-30): the cold read "
        "(3 passages per unit) and the blind self agreement check (10 earlier calls), "
        "both reported alongside the ruling, not pass or fail on their own.",
    ]

    for record, slug, what in UNITS:
        after = identify(runs_in(ROOT / "artifacts" / "runs" / record / slug))
        before_dir = BEFORE_DIR / record / slug
        before = identify(runs_in(before_dir)) if before_dir.exists() else ()
        unit = unit_for(runs_in(ROOT / "artifacts" / "runs" / record / slug)[0], SNAPSHOT)

        after_links = distinct_links(after)
        before_links = distinct_links(before)
        after_keys = {link.signature for link in after_links}
        lost: list[Link] = [link for link in before_links if link.signature not in after_keys]

        sheet += ["", f"## {record} / {slug} ({what})", ""]
        sheet += ["### Entities", "", "10 evenly spaced through after run 1's located order.", ""]
        for entity in entity_sample(after[0]):
            sheet += entity_lines(entity)

        sheet += [
            "",
            "### Relationships",
            "",
            f"5 evenly spaced through the {len(after_links)} distinct links the three after "
            "runs wrote.",
            "",
        ]
        for index in evenly(after_links, LINK_SAMPLE):
            sheet += link_lines(unit, after_links[index], len(after), "agree / disagree")

        sheet += [
            "",
            "### Dropped links (befores wrote, no after wrote)",
            "",
            f"{len(lost)} distinct links appear in at least one `0002.3` before run and in "
            f"none of the `0003.1` afters. {min(DROPPED_SAMPLE, len(lost))} drawn at random, "
            f"seed `{DROPPED_SEED}`.",
            "",
        ]
        sample_size = min(DROPPED_SAMPLE, len(lost))
        for link in rng.sample(lost, sample_size) if lost else []:
            sheet += link_lines(unit, link, len(before), UNRULED["lost links"][0])

    (HERE / "data").mkdir(exist_ok=True)
    SHEET.write_text("\n".join(sheet) + "\n")
    print(f"wrote {SHEET.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
