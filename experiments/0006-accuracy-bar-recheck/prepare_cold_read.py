"""Build the re check's cold read sheet, no API call (spec 0003, AC-30).

A cold read asks the opposite question a sample rules on: not "is this extracted item
right", but "read this passage fresh, what relation would you have written from it,
and does that appear anywhere the runs actually wrote (accepted, held, or dropped)".
Reading the runs' own output first would bias that, so every passage's text comes
first, every link the before and after runs wrote from it sits below a divider, read
only once the passage has been read cold.

A passage is one paragraph or list item of the unit's own text (split the same way
`report.py`'s `source_text()` locates a link's source: at a blank line or the start of
a bulleted line), so "does this passage's link appear below" is a like for like check
against the same span a link would be placed in. 3 per unit, drawn at random, the seed
recorded so the draw is reproducible.

Classification below the divider:
* **accepted**: in the after (or before) run's own `accepted_relationships`.
* **held**: in review, flagged `endpoint_not_accepted` (an unaccepted endpoint, not a
  missing link).
* **dropped**: in review for any other reason (runs disagreed, a trap flag, an
  unclassified type, an unlocated span).
A link whose signature matches none of the three (rare; `route_runs()` only routes the
first run's own items plus what other runs uniquely add) is shown unclassified rather
than silently placed in the wrong bucket.

Run from the repository root: uv run python <this file>
"""

import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "0005-held-out-prompt-examples"))
from report import (
    Link,
    comparable,
    distinct_links,
    endpoint_text,
    runs_in,
    source_text,
)

from tracepath.extract.compare import (
    ReviewReasonName,
    identities_of,
    relationship_signature,
    route_runs,
)
from tracepath.extract.ids import assign_ids, label_binding_rules, locate_output
from tracepath.extract.units import Unit
from tracepath.rebuild import unit_for

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
SHEET = HERE / "data" / "cold-read.md"
BEFORE_DIR = ROOT / "artifacts" / "superseded" / "2026-09-28-prompt-0002.3"

PASSAGE_SAMPLE = 3
PASSAGE_SEED = 20260928001
MIN_PASSAGE_CHARS = 40

#: One paragraph or bulleted item: the same boundary `report.py`'s `source_text()`
#: uses to locate a link's own source (a blank line, or the start of a `- ` line).
BOUNDARY = re.compile(r"\n\n|\n(?=- )")

UNITS = [
    ("0014", "requirements", "Requirements"),
    ("0015", "feature-design", "Feature design"),
    ("feature-33", "33-band-anchor-review-done", "Band anchor review"),
]


@dataclass(frozen=True)
class Passage:
    """One paragraph or bulleted item, and where it sits in the unit's own text."""

    start: int
    end: int
    text: str


def passages(text: str) -> list[Passage]:
    """Every substantive paragraph or bulleted item, in source order."""
    bounds = [(m.start(), m.end()) for m in BOUNDARY.finditer(text)]
    starts = [0] + [end for _start, end in bounds]
    ends = [start for start, _end in bounds] + [len(text)]
    found = []
    for start, end in zip(starts, ends, strict=True):
        segment = text[start:end].strip()
        if len(segment) >= MIN_PASSAGE_CHARS:
            found.append(Passage(start, end, segment))
    return found


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


def classify(identified: tuple) -> dict[tuple[str, str, str], str]:  # type: ignore[type-arg]
    """Every distinct relationship's signature, mapped to accepted / held / dropped."""
    if not identified:
        return {}
    routed = route_runs(identified)
    identities = identities_of(identified[0])
    labels: dict[tuple[str, str, str], str] = {}
    for relationship in routed.accepted_relationships:
        labels[comparable(relationship_signature(relationship, identities))] = "accepted"
    for item in routed.review:
        if len(item.signature) != 3:
            continue  # an entity row (2-tuple signature), not a link (3-tuple)
        key = comparable(item.signature)  # type: ignore[arg-type]
        held = any(r.name is ReviewReasonName.ENDPOINT_NOT_ACCEPTED for r in item.reasons)
        labels[key] = "held" if held else "dropped"
    return labels


def link_block(unit: Unit, link: Link, label: str, run_count: int) -> list[str]:
    """One link's classification, endpoints, and phrase."""
    relationship = link.relationship
    lines = [
        f"- **{label}** · {relationship.type} · written by {len(link.runs)} of {run_count} runs",
        f"  - source: {endpoint_text(relationship.source, link)}",
        f"  - target: {endpoint_text(relationship.target, link)}",
    ]
    if relationship.phrase:
        lines.append(f"  - phrase: {relationship.phrase}")
    return lines


def build() -> None:
    """Build the cold read sheet's three passages per unit, and write it."""
    rng = random.Random(PASSAGE_SEED)
    sheet = [
        "# Cold read, experiment 0006 (spec 0003, AC-30)",
        "",
        "Read each passage's own text first. Only once you have your own answer for "
        "what relation, if any, it states, look below its divider at every link the "
        "before and after runs actually wrote from it. Reported alongside the ruling, "
        "not pass or fail on its own: the question is whether a real link is missing "
        "from all three buckets, accepted, held and dropped alike.",
        "",
        f"3 passages per unit, drawn at random, seed `{PASSAGE_SEED}`, reproducible by "
        "re-running `prepare_cold_read.py`.",
    ]

    for record, slug, label in UNITS:
        after_runs_dir = ROOT / "artifacts" / "runs" / record / slug
        before_runs_dir = BEFORE_DIR / record / slug
        after_runs = runs_in(after_runs_dir)
        after = identify(after_runs)
        before = identify(runs_in(before_runs_dir)) if before_runs_dir.exists() else ()
        unit = unit_for(after_runs[0], SNAPSHOT)

        after_labels = classify(after)
        before_labels = classify(before)
        after_links = distinct_links(after)
        before_links = distinct_links(before)

        ps = passages(unit.text)
        chosen = rng.sample(ps, min(PASSAGE_SAMPLE, len(ps)))
        sheet += ["", f"## {record} / {slug} ({label})", ""]

        for n, passage in enumerate(chosen, start=1):
            sheet += [f"### Passage {n}", "", "```text", passage.text, "```", "", "---", ""]
            matches: list[str] = []
            for kind, links, labels, run_count in (
                ("before", before_links, before_labels, len(before)),
                ("after", after_links, after_labels, len(after)),
            ):
                for link in links:
                    block_text = source_text(unit, link)
                    if block_text != passage.text:
                        continue
                    key = link.signature
                    tag = labels.get(key, "unclassified (routing artifact, see method note)")
                    matches += [f"**{kind}**", *link_block(unit, link, tag, run_count)]
            if matches:
                sheet += [*matches, ""]
            else:
                sheet += ["*(no link, before or after, sources from this passage)*", ""]

    (HERE / "data").mkdir(exist_ok=True)
    SHEET.write_text("\n".join(sheet) + "\n")
    print(f"wrote {SHEET.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
