"""A hand built graph with held items, deliberately not an eval chain (spec 0005 AC-8).

Its records are `9003` and `9004`, numbers no corpus spec carries. The rows are in the
exact shape `load --with-held` writes: a held entity has `held` and `held_reasons` and
no `accepted_by`, a held link carries both in its properties, and a held `:Unresolved`
node has `held` and no reasons.

The graph, drawn from the start `9003/AC-1` (accepted):

    9003/AC-1 -AMENDED_BY->    9003/AC-4      held link, AC-4 accepted: its only path
    9003/AC-1 -BLOCKED_BY->    9003/AC-5      accepted
    9003/AC-1 -CORRECTED_BY->  9003/AC-6      held link, a shortcut past an accepted path
    9003/AC-5 -BLOCKED_BY->    9003/AC-6      accepted, so AC-6 is reached clean at hop 2
    9003/AC-1 -SUPERSEDED_BY-> 9003/AC-2      held link, AC-2 itself held
    9003/AC-2 -BLOCKED_BY->    9003/AC-3      held link, AC-3 accepted
    9003/AC-2 -UNCLASSIFIED->  unresolved:9003:feature-77   held link, the gap held
    9004/AC-1 -VERIFIES->      9003/AC-4      accepted, across records behind a held link
    9003/AC-7                                 accepted, no link: never visited
    every entity -PART_OF->    its record     never followed
"""

from typing import Any

FILE = "specs/9003-fixture-held/index.md"
NEIGHBOUR_FILE = "specs/9004-fixture-held-neighbour/index.md"
COMMIT = "f1x7ure"
MODEL = "claude-sonnet-5"
VERSION = "0003.1"
START = "9003/AC-1"

#: Each section's heading line, which every link written in it cites as its `line`.
SECTION_STARTS = {"Requirements": 10, "Feature design": 32}

RECORDS: tuple[dict[str, Any], ...] = (
    {
        "canonical_id": "9003",
        "kind": "spec",
        "title": "Fixture held",
        "path": FILE,
        "commit": COMMIT,
        "aliases": ["9003"],
    },
    {
        "canonical_id": "9004",
        "kind": "spec",
        "title": "Fixture held neighbour",
        "path": NEIGHBOUR_FILE,
        "commit": COMMIT,
        "aliases": ["9004"],
    },
)


def _entity(
    canonical_id: str,
    text: str,
    line: int,
    held: tuple[str, ...] = (),
    file: str = FILE,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "canonical_id": canonical_id,
        "type": "AcceptanceCriterion",
        "text": text,
        "rationale": [],
        "flags": ["multi_condition_split"] if "known_trap_flag" in held else [],
        "id_source": "verbatim",
        "struck": False,
        "file": file,
        "section": "Requirements",
        "line": line,
        "file_line": SECTION_STARTS["Requirements"] + line - 1,
        "commit": COMMIT,
        "model": MODEL,
        "prompt_version": VERSION,
        "extracted_at": "2026-10-07T00:00:00+00:00",
    }
    if held:
        row["held"] = True
        row["held_reasons"] = list(held)
    else:
        row["accepted_by"] = "auto"
    return row


ENTITIES: tuple[dict[str, Any], ...] = (
    _entity(START, "The start criterion holds.", 3),
    _entity("9003/AC-2", "A criterion review holds back.", 4, ("runs_disagree", "known_trap_flag")),
    _entity("9003/AC-3", "A criterion behind a held one.", 5),
    _entity("9003/AC-4", "A criterion reached only by a held link.", 6),
    _entity("9003/AC-5", "A criterion reached clean.", 7),
    _entity("9003/AC-6", "A criterion with a held shortcut.", 8),
    _entity("9003/AC-7", "A criterion no link reaches.", 9),
    _entity("9004/AC-1", "A neighbour criterion.", 3, file=NEIGHBOUR_FILE),
)

UNRESOLVED: tuple[dict[str, Any], ...] = (
    {
        "canonical_id": "unresolved:9003:feature-77",
        "mention": "feature 77",
        "source_record": "9003",
        "file": FILE,
        "section": "Requirements",
        "line": SECTION_STARTS["Requirements"],
        "held": True,
    },
)


def _link(
    link_type: str,
    source: str,
    target: str,
    held: tuple[str, ...] = (),
) -> tuple[str, dict[str, Any]]:
    properties: dict[str, Any] = {
        "source_record": source.split("/", 1)[0],
        "file": FILE,
        "section": "Requirements",
        "line": SECTION_STARTS["Requirements"],
        "prompt_version": VERSION,
        "model": MODEL,
        "commit": COMMIT,
    }
    if held:
        properties["held"] = True
        properties["held_reasons"] = list(held)
    return link_type, {"from_id": source, "to_id": target, "properties": properties}


LINKS: tuple[tuple[str, dict[str, Any]], ...] = (
    _link("AMENDED_BY", START, "9003/AC-4", ("known_trap_flag",)),
    _link("BLOCKED_BY", START, "9003/AC-5"),
    _link("CORRECTED_BY", START, "9003/AC-6", ("runs_disagree",)),
    _link("BLOCKED_BY", "9003/AC-5", "9003/AC-6"),
    _link("SUPERSEDED_BY", START, "9003/AC-2", ("endpoint_not_accepted:9003/AC-2",)),
    _link("BLOCKED_BY", "9003/AC-2", "9003/AC-3", ("runs_disagree",)),
    _link("UNCLASSIFIED", "9003/AC-2", "unresolved:9003:feature-77", ("runs_disagree",)),
    _link("VERIFIES", "9004/AC-1", "9003/AC-4"),
)

PART_OF: tuple[dict[str, str], ...] = tuple(
    {"from_id": entity["canonical_id"], "to_id": entity["canonical_id"].split("/", 1)[0]}
    for entity in ENTITIES
)


def accepted_rows(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    """The node rows a default load would write: every held one left out."""
    return tuple(row for row in rows if not row.get("held"))


def accepted_links(
    links: tuple[tuple[str, dict[str, Any]], ...],
) -> tuple[tuple[str, dict[str, Any]], ...]:
    """The link rows a default load would write: every held one left out."""
    return tuple(link for link in links if not link[1]["properties"].get("held"))
