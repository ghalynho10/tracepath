"""`graph/model.py`'s pure row builders: pipeline values to plain Cypher rows.

Exercised only indirectly, through the full pipeline load, until now: no test named
one of these functions directly, so the AC-10 fields below were never confirmed against
the function that actually builds a write, only against real corpus data that has never
carried them (see docs/specs/0002-data-model/verify.md, "The label extension").
"""

from tracepath.graph.model import unresolved_row
from tracepath.resolve.endpoints import UnresolvedNode


def node(**overrides: object) -> UnresolvedNode:
    base = dict(
        canonical_id="unresolved:0008:binding-rule-6",
        mention="spec 0001's binding rule 6",
        source_record="0008",
        file="specs/0008/index.md",
        section="Preamble",
        line=12,
    )
    base.update(overrides)
    return UnresolvedNode(**base)  # type: ignore[arg-type]


def test_unresolved_row_carries_the_structured_record_and_label_when_named() -> None:
    """AC-10: a held reference's node keeps what it knew, not only `mention`."""
    row = unresolved_row(node(record="0001", label="binding rule 6"))

    assert row["record"] == "0001"
    assert row["label"] == "binding rule 6"
    assert row["mention"] == "spec 0001's binding rule 6"


def test_unresolved_row_drops_record_and_label_when_the_reference_named_neither() -> None:
    """Neo4j stores absence, not null (AC-4's own rule, applied here too): a plain
    unnameable reference, the common case today, must not write `record: null`."""
    row = unresolved_row(node())

    assert "record" not in row
    assert "label" not in row
