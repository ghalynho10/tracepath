"""A hand built graph for testing the walk, deliberately not an eval chain (AC-32).

Its records are `9001` and `9002`, numbers no corpus spec carries. The rows are in the
exact shape the loader writes, so the unit test builds its slice from them without a
database and the integration test writes them through the real write functions.

The graph, drawn from the start `9001/AC-1`:

    9001#build-plan:1 -SATISFIES->      9001/AC-1  (incoming)
    9001#feature-design:1 -VERIFIES->   9001/AC-1  (incoming, a second link to one node)
    9001#feature-design:1 -UNCLASSIFIED-> 9001/AC-1 (incoming, reached first by type order)
    9001/AC-1 -AMENDED_BY->     9002                (a Record stop)
    9001/AC-1 -SUPERSEDED_BY->  9001/AC-2
    9001/AC-1 -UNCLASSIFIED->   unresolved:9001:feature-99 (an Unresolved stop)
    9001/AC-2 -BLOCKED_BY->     9001/AC-3           (hop 2)
    9001/AC-3 -CORRECTED_BY->   9001#feature-design:1 (closes a cycle)
    9001/AC-3 -BLOCKED_BY->     9001/AC-4           (hop 3, the depth limit)
    9001/AC-4 -BLOCKED_BY->     9001/AC-5           (past the limit, never visited)
    every entity -PART_OF->     9001                (never followed)

`9001/AC-1` is struck. `9001#feature-design:1` and both of its links carry an older
prompt version, so the closing line has two versions to count.
"""

from typing import Any

FILE = "specs/9001-fixture-walk/index.md"
COMMIT = "f1x7ure"
MODEL = "claude-sonnet-5"
CURRENT = "0003.1"
OLDER = "0003.0"
START = "9001/AC-1"

#: Each section's heading line, which every link written in it cites as its `line`.
SECTION_STARTS = {"Requirements": 10, "Feature design": 32, "Build plan": 59}

RECORDS: tuple[dict[str, Any], ...] = (
    {
        "canonical_id": "9001",
        "kind": "spec",
        "title": "Fixture walk",
        "path": FILE,
        "commit": COMMIT,
        "aliases": ["9001"],
    },
    {
        "canonical_id": "9002",
        "kind": "spec",
        "title": "Fixture neighbour",
        "path": "specs/9002-fixture-neighbour/index.md",
        "commit": COMMIT,
        "aliases": ["9002"],
    },
)


def _entity(
    canonical_id: str,
    entity_type: str,
    text: str,
    section: str,
    line: int,
    struck: bool = False,
    prompt_version: str = CURRENT,
) -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "type": entity_type,
        "text": text,
        "rationale": [],
        "flags": [],
        "id_source": "verbatim" if "/" in canonical_id else "derived",
        "struck": struck,
        "file": FILE,
        "section": section,
        "line": line,
        "file_line": SECTION_STARTS[section] + line - 1,
        "commit": COMMIT,
        "model": MODEL,
        "prompt_version": prompt_version,
        "extracted_at": "2026-10-05T00:00:00+00:00",
        "accepted_by": "auto",
    }


ENTITIES: tuple[dict[str, Any], ...] = (
    _entity(START, "AcceptanceCriterion", "The start criterion holds.", "Requirements", 3, True),
    _entity(
        "9001/AC-2", "AcceptanceCriterion", "The replacement criterion holds.", "Requirements", 4
    ),
    _entity("9001/AC-3", "AcceptanceCriterion", "A criterion two hops out.", "Requirements", 5),
    _entity(
        "9001/AC-4", "AcceptanceCriterion", "A criterion at the depth limit.", "Requirements", 6
    ),
    _entity(
        "9001/AC-5", "AcceptanceCriterion", "A criterion past the depth limit.", "Requirements", 7
    ),
    _entity(
        "9001#feature-design:1",
        "TestScenario",
        "a request to the old path is refused, verifies AC-1",
        "Feature design",
        9,
        prompt_version=OLDER,
    ),
    _entity("9001#build-plan:1", "BuildStep", "Build the start criterion.", "Build plan", 2),
)

UNRESOLVED: tuple[dict[str, Any], ...] = (
    {
        "canonical_id": "unresolved:9001:feature-99",
        "mention": "feature 99",
        "source_record": "9001",
        "file": FILE,
        "section": "Requirements",
        "line": SECTION_STARTS["Requirements"],
    },
)


def _link(
    link_type: str,
    source: str,
    target: str,
    section: str,
    phrase: str | None = None,
    prompt_version: str = CURRENT,
) -> tuple[str, dict[str, Any]]:
    properties: dict[str, Any] = {
        "source_record": "9001",
        "file": FILE,
        "section": section,
        "line": SECTION_STARTS[section],
        "prompt_version": prompt_version,
        "model": MODEL,
        "commit": COMMIT,
    }
    if phrase is not None:
        properties["phrase"] = phrase
    return link_type, {"from_id": source, "to_id": target, "properties": properties}


LINKS: tuple[tuple[str, dict[str, Any]], ...] = (
    _link("VERIFIES", "9001#feature-design:1", START, "Feature design", "verifies AC-1", OLDER),
    _link("UNCLASSIFIED", "9001#feature-design:1", START, "Feature design", "see AC-1", OLDER),
    _link("SUPERSEDED_BY", START, "9001/AC-2", "Requirements"),
    _link(
        "UNCLASSIFIED",
        START,
        "unresolved:9001:feature-99",
        "Requirements",
        "as feature 99 describes",
    ),
    _link("AMENDED_BY", START, "9002", "Requirements"),
    _link("SATISFIES", "9001#build-plan:1", START, "Build plan", "satisfies AC-1"),
    _link("BLOCKED_BY", "9001/AC-2", "9001/AC-3", "Requirements"),
    _link("CORRECTED_BY", "9001/AC-3", "9001#feature-design:1", "Requirements"),
    _link("BLOCKED_BY", "9001/AC-3", "9001/AC-4", "Requirements"),
    _link("BLOCKED_BY", "9001/AC-4", "9001/AC-5", "Requirements"),
)

PART_OF: tuple[dict[str, str], ...] = tuple(
    {"from_id": entity["canonical_id"], "to_id": "9001"} for entity in ENTITIES
)
