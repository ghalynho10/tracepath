"""The held out before and after table, the label invention check, and the ruling sheet.

No API call. Everything is rebuilt from committed artifacts: the afters from
`artifacts/runs/`, the befores of all three groups from
`artifacts/superseded/2026-09-24-prompt-0002.3/`, where the after run moved them. Both
are re-located and re-routed by the current code, so before and after are measured by
one method.

Outputs (spec 0003):

* `data/heldout-table.json`: per group, the entity column (count spread, entity rows
  under `runs_disagree`) and the relationship column (rows under `runs_disagree` and,
  separately, under `endpoint_not_accepted`), before and after (AC-14, AC-15), plus
  group B's spread against the threshold of 2 (AC-17), plus the count of links the
  befores wrote and no after wrote.
* The label invention check (build plan task 14): every model set entity `label` in
  the after runs, split into those found verbatim in their own span and those not.
* `data/ruling-sheet.md`, for the engineer's ruling (AC-16), in three sections per
  group, each tallied on its own:
  - **Entities**: 10 evenly spaced through run 1's located order.
  - **Relationships**: 5 evenly spaced through every distinct link the three after
    runs wrote, since an entity sample says nothing about links.
  - **Links the befores wrote and no after wrote** (group A only, where the links
    fell from about 36 per run to about 8): 10 evenly spaced through that set, each
    with its source text, since a sample of the afters cannot show what they dropped.

Two runs:

    uv run python <this file>          # build the table and the sheet
    uv run python <this file> tally    # count the engineer's marks, per group and section

Building the sheet refuses to overwrite one that already carries a ruling, so a rerun
can never erase the engineer's marks.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from tracepath.artifacts import RUNS_DIR, RunArtifact, read_run
from tracepath.extract.compare import (
    ReviewItem,
    ReviewReasonName,
    identities_of,
    relationship_signature,
    route_runs,
)
from tracepath.extract.ids import (
    IdentifiedEntity,
    IdentifiedOutput,
    assign_ids,
    label_binding_rules,
    locate_output,
)
from tracepath.extract.locate import locate_line
from tracepath.extract.schema import ExtractedRelationship, LocalEndpoint, ReferenceEndpoint
from tracepath.extract.units import Unit
from tracepath.rebuild import unit_for

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
SUPERSEDED = ROOT / "artifacts" / "superseded" / "2026-09-24-prompt-0002.3"
SHEET = HERE / "data" / "ruling-sheet.md"

#: The three held out groups: record, section slug, and what each one tests.
GROUPS = {
    "A": ("0021", "requirements", "a unit kind with no worked example"),
    "B": ("0013", "feature-design", "a kind with an example, different content"),
    "C": ("feature-9", "9-profile-entry-done", "a different scope row than the example's"),
}

#: Groups whose dropped links are sampled for the ruling.
LOST_LINK_GROUPS = ("A",)

#: The widest entity spread any stable committed unit showed (AC-17).
SPREAD_THRESHOLD = 2

#: Sample sizes for the three sections of the ruling sheet (AC-16).
ENTITY_SAMPLE, LINK_SAMPLE, LOST_SAMPLE = 10, 5, 10

#: The marks an unruled line carries, per section, and the words that replace them.
UNRULED = {
    "entities": ("agree / disagree", ("agree", "disagree")),
    "relationships": ("agree / disagree", ("agree", "disagree")),
    "lost links": ("real link lost / rightly dropped", ("real link lost", "rightly dropped")),
}


@dataclass(frozen=True)
class Link:
    """One distinct relationship across a set of runs, and where it can be read."""

    signature: tuple[str, str, str]
    relationship: ExtractedRelationship
    entities: dict[str, IdentifiedEntity]
    runs: tuple[int, ...]


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


def comparable(signature: tuple[str, str, str]) -> tuple[str, str, str]:
    """A signature with a reference to a verbatim id read as that id.

    A link to `0021/AC-3` signs as `0021/AC-3` when the run also returned AC-3 as a
    local entity, and as `ref:0021/AC-3` when it did not. Across two prompts that is a
    difference in how the link was written, not in whether it was, so the two compare
    equal here. A reference by label or to a whole record keeps its own form.
    """

    def one(endpoint: str) -> str:
        if endpoint.startswith("ref:") and "|label:" not in endpoint and not endpoint.endswith("/"):
            return endpoint.removeprefix("ref:")
        return endpoint

    kind, source, target = signature
    return (kind, one(source), one(target))


def distinct_links(identified: tuple[IdentifiedOutput, ...]) -> list[Link]:
    """Every distinct link across the runs, with the runs that wrote it, first seen first."""
    found: dict[tuple[str, str, str], Link] = {}
    for number, output in enumerate(identified, start=1):
        identities = identities_of(output)
        entities = {e.canonical_id: e for e in output.entities}
        for relationship in output.relationships:
            key = comparable(relationship_signature(relationship, identities))
            if key in found:
                seen = found[key]
                if number not in seen.runs:
                    found[key] = Link(key, seen.relationship, seen.entities, (*seen.runs, number))
            else:
                found[key] = Link(key, relationship, entities, (number,))
    return list(found.values())


def evenly(items: list[Link] | list[IdentifiedEntity], size: int) -> list[int]:
    """The positions of `size` items evenly spaced through a list, or all of them."""
    if len(items) <= size:
        return list(range(len(items)))
    step = len(items) / size
    return [int(i * step) for i in range(size)]


def entity_sample(output: IdentifiedOutput) -> list[IdentifiedEntity]:
    """Ten entities evenly spaced through one run's located order."""
    ordered = sorted(
        output.entities,
        key=lambda e: (e.location is None, e.location.offset if e.location else 0),
    )
    return [ordered[i] for i in evenly(ordered, ENTITY_SAMPLE)]


def endpoint_text(endpoint: LocalEndpoint | ReferenceEndpoint, link: Link) -> str:
    """One endpoint as a reader needs it: the entity's own span, or the reference."""
    if isinstance(endpoint, LocalEndpoint):
        entity = link.entities.get(endpoint.id)
        if entity is None:
            return f"`{endpoint.id}`"
        return f"`{endpoint.id}` {entity.entity.type}: {entity.entity.span}"
    named = endpoint.id or (f"label `{endpoint.label}`" if endpoint.label else "(whole record)")
    return f"reference `{endpoint.record}` {named}, mention: {endpoint.mention}"


def source_text(unit: Unit, link: Link) -> str:
    """The stretch of the unit the link was read from: its phrase's paragraph or bullet.

    Located by the phrase when there is one, else by the source entity's own line, else
    by the reference's verbatim mention. Null only when none of the three can be placed.
    """
    offset: int | None = None
    relationship = link.relationship
    if relationship.phrase:
        located = locate_line(unit, relationship.phrase)
        offset = located.offset if located else None
    if offset is None and isinstance(relationship.source, LocalEndpoint):
        entity = link.entities.get(relationship.source.id)
        offset = entity.location.offset if entity and entity.location else None
    if offset is None:
        for endpoint in (relationship.source, relationship.target):
            if isinstance(endpoint, ReferenceEndpoint):
                found = unit.text.find(endpoint.mention)
                if found != -1:
                    offset = found
                    break
    if offset is None:
        return "(could not be placed in the unit)"
    text = unit.text
    start = max(text.rfind("\n\n", 0, offset), text.rfind("\n- ", 0, offset + 2)) + 1
    ends = [i for i in (text.find("\n\n", offset), text.find("\n- ", offset + 1)) if i != -1]
    end = min(ends) if ends else len(text)
    return text[start:end].strip()


def link_lines(unit: Unit, link: Link, runs_total: int, mark: str) -> list[str]:
    """One relationship as a ruling line and its detail."""
    relationship = link.relationship
    lines = [
        f"- [ ] {mark} · {relationship.type} · written by {len(link.runs)} of {runs_total} runs",
        f"  - source: {endpoint_text(relationship.source, link)}",
        f"  - target: {endpoint_text(relationship.target, link)}",
    ]
    if relationship.phrase:
        lines.append(f"  - phrase: {relationship.phrase}")
    if relationship.known_trap_flags:
        lines.append(f"  - flags: {', '.join(str(f) for f in relationship.known_trap_flags)}")
    source = source_text(unit, link).replace("\n", "\n    > ")
    lines.append(f"  - source text:\n    > {source}")
    return lines


def entity_lines(entity: IdentifiedEntity) -> list[str]:
    """One entity as a ruling line and its detail."""
    head = f"- [ ] agree / disagree · `{entity.canonical_id}` · {entity.entity.type}"
    if entity.entity.label:
        head += f" · label `{entity.entity.label}`"
    lines = [head, f"  - span: {entity.entity.span}"]
    if entity.entity.rejected_spans:
        lines.append(f"  - rejected: {list(entity.entity.rejected_spans)}")
    if entity.entity.known_trap_flags:
        lines.append(f"  - flags: {', '.join(str(f) for f in entity.entity.known_trap_flags)}")
    return lines


def already_ruled(path: Path) -> bool:
    """True when the sheet on disk carries at least one mark the engineer made."""
    if not path.exists():
        return False
    unruled = {mark for mark, _ in UNRULED.values()}
    return any(
        line.startswith("- [") and not any(mark in line for mark in unruled)
        for line in path.read_text().splitlines()
    )


def build() -> None:
    """Build the table and the ruling sheet, and write both."""
    if already_ruled(SHEET):
        raise SystemExit(f"{SHEET.name} already carries a ruling; not overwriting it")
    table: dict[str, object] = {}
    sheet = [
        "# Ruling sheet, experiment 0005 (AC-16)",
        "",
        "Replace each line's marks with one word, and add a few words on why when you "
        "disagree. Entity and relationship agreement are tallied separately "
        "(`report.py tally`).",
        "",
        "- **Entities**: `agree` when the model's cut and type pass HANDOFF's three "
        "question test (atomicity, referenceability, right sizing) and the deletion "
        "trick, `disagree` otherwise.",
        "- **Relationships**: `agree` when the link is real, and its type, direction and "
        "endpoints are what you would have written, `disagree` otherwise.",
        "- **Links the befores wrote and no after wrote**: `real link lost` when the "
        "source text states a relation the afters should have kept, `rightly dropped` "
        "when it does not (a table row, an unaffected claim, an invented pair, and so on). "
        "A note says when the same endpoints survive in the afters under another type.",
    ]
    for name, (record, slug, what) in GROUPS.items():
        after_runs = runs_in(ROOT / RUNS_DIR / record / slug)
        unit = unit_for(after_runs[0], SNAPSHOT)
        after = identify(after_runs)
        before_dir = SUPERSEDED / record / slug
        before = identify(runs_in(before_dir)) if before_dir.exists() else ()
        after_links = distinct_links(after)
        before_links = distinct_links(before)
        after_keys = {link.signature for link in after_links}
        after_pairs = {(link.signature[1], link.signature[2]) for link in after_links}
        lost = [link for link in before_links if link.signature not in after_keys]

        after_columns = columns(after)
        entry: dict[str, object] = {
            "unit": f"{record} / {slug}",
            "tests": what,
            "before": columns(before) if before else None,
            "after": after_columns,
            "distinct_links_before": len(before_links),
            "distinct_links_after": len(after_links),
            "links_before_only": len(lost),
            "links_before_only_by_runs": {
                str(n): sum(1 for link in lost if len(link.runs) == n) for n in (1, 2, 3)
            },
            "links_before_only_pair_kept_under_another_type": sum(
                1 for link in lost if (link.signature[1], link.signature[2]) in after_pairs
            ),
            "label_check_after": label_check(after),
        }
        if name == "B":
            spread = int(str(after_columns["entity_spread"]))
            entry["ac17_threshold"] = SPREAD_THRESHOLD
            entry["ac17_test_ac2"] = spread > SPREAD_THRESHOLD
        table[name] = entry

        sheet += ["", f"## Group {name}: {record} / {slug} ({what})", ""]
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
        if name in LOST_LINK_GROUPS:
            by_runs = entry["links_before_only_by_runs"]
            sheet += [
                "",
                "### Links the befores wrote and no after wrote",
                "",
                f"{len(lost)} distinct links appear in at least one `0002.3` before run and in "
                f"none of the `0003.0` afters (by how many before runs wrote each: {by_runs}). "
                "10 evenly spaced through them, in the order the befores first wrote them.",
                "",
            ]
            for index in evenly(lost, LOST_SAMPLE):
                link = lost[index]
                lines = link_lines(unit, link, len(before), UNRULED["lost links"][0])
                if (link.signature[1], link.signature[2]) in after_pairs:
                    note = "  - note: the afters keep these same endpoints, under another type"
                    lines.insert(1, note)
                sheet += lines

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "heldout-table.json").write_text(json.dumps(table, indent=2) + "\n")
    SHEET.write_text("\n".join(sheet) + "\n")
    print(json.dumps(table, indent=2))


def tally() -> None:
    """Count the engineer's marks per group and section, and write them beside the sheet."""
    counts: dict[str, dict[str, dict[str, int]]] = {}
    group = section = ""
    for line in SHEET.read_text().splitlines():
        heading = re.match(r"^## Group (\w+):", line)
        if heading:
            group = heading.group(1)
            continue
        if line.startswith("### "):
            title = line[4:].lower()
            section = "lost links" if title.startswith("links the befores") else title
            continue
        if not line.startswith("- [") or section not in UNRULED:
            continue
        unruled, words = UNRULED[section]
        body = line.split("]", 1)[1].strip()
        mark = next((w for w in sorted(words, key=len, reverse=True) if body.startswith(w)), None)
        if unruled in body or mark is None:
            mark = "unruled"
        bucket = counts.setdefault(group, {}).setdefault(section, {})
        bucket[mark] = bucket.get(mark, 0) + 1
    (HERE / "data" / "ruling-tally.json").write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["tally"]:
        tally()
    else:
        build()
