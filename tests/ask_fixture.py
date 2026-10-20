"""Hand built graphs for `ask` (spec 0009), deliberately not an eval chain.

Records `9101` and `9102`, numbers no corpus spec carries. Nodes and links are built
the way `graph_slice()` builds them from a read, so no database is needed.

The default graph:

    9101/AC-1  "The landing rule reads the profile row once."    accepted
    9101/AC-2  "A dedicated query keeps the read narrow."        held
    9101/AC-3  "The old landing check read every row."           struck
    9101/AC-4  "The landing check now reads one row."            accepted
    9102/AC-1  "Sessions expire after one hour."                 accepted
    9102/AC-2  "Expired sessions sign the user out."             accepted
    9101       Record "Landing fixture"
    unresolved:9101:feature-77  mention "feature 77"             held

    9101/AC-1 -AMENDED_BY->    9101/AC-2   held link
    9101/AC-3 -SUPERSEDED_BY-> 9101/AC-4   held link
    9101/AC-2 -BLOCKED_BY->    9102/AC-1
    9102/AC-1 -VERIFIES->      9102/AC-2   (hop 3 from 9101/AC-1)
    9101/AC-1 -UNCLASSIFIED->  unresolved:9101:feature-77
"""

from tracepath.traverse.graph_slice import GraphSlice, Link, Node, NodeKind, graph_slice

FILE = "specs/9101-fixture-ask/index.md"
OTHER = "specs/9102-fixture-ask-neighbour/index.md"


def entity(
    canonical_id: str,
    text: str,
    *,
    file: str = FILE,
    file_line: int = 10,
    held: bool = False,
    struck: bool = False,
    type: str = "AcceptanceCriterion",
) -> Node:
    """One entity node, as a read would build it."""
    return Node(
        canonical_id=canonical_id,
        kind=NodeKind.ENTITY,
        type=type,
        text=text,
        struck=struck,
        file=file,
        file_line=file_line,
        held=held,
        held_reasons=("runs_disagree",) if held else (),
    )


def link(
    type: str, source: str, target: str, *, phrase: str | None = None, held: bool = False
) -> Link:
    """One typed link, as a read would build it."""
    return Link(type=type, source=source, target=target, phrase=phrase, held=held)


NODES = (
    entity("9101/AC-1", "The landing rule reads the profile row once.", file_line=10),
    entity("9101/AC-2", "A dedicated query keeps the read narrow.", file_line=11, held=True),
    entity("9101/AC-3", "The old landing check read every row.", file_line=12, struck=True),
    entity("9101/AC-4", "The landing check now reads one row.", file_line=13),
    entity("9102/AC-1", "Sessions expire after one hour.", file=OTHER, file_line=20),
    entity("9102/AC-2", "Expired sessions sign the user out.", file=OTHER, file_line=21),
    Node(canonical_id="9101", kind=NodeKind.RECORD, title="Landing fixture", path=FILE),
    Node(
        canonical_id="unresolved:9101:feature-77",
        kind=NodeKind.UNRESOLVED,
        mention="feature 77",
        file=FILE,
        line=40,
        held=True,
    ),
)

LINKS = (
    link("AMENDED_BY", "9101/AC-1", "9101/AC-2", phrase="amended by AC-2", held=True),
    link("SUPERSEDED_BY", "9101/AC-3", "9101/AC-4", phrase="replaced", held=True),
    link("BLOCKED_BY", "9101/AC-2", "9102/AC-1"),
    link("VERIFIES", "9102/AC-1", "9102/AC-2"),
    link("UNCLASSIFIED", "9101/AC-1", "unresolved:9101:feature-77", phrase="see feature 77"),
)


def graph(nodes: tuple[Node, ...] = NODES, links: tuple[Link, ...] = LINKS) -> GraphSlice:
    """The slice `ask` would read, held items included."""
    return graph_slice(nodes, links, with_held=True)
