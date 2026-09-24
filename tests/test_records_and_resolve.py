from pathlib import Path

import pytest

from tracepath.extract.ids import IdentifiedEntity
from tracepath.extract.records import (
    RecordError,
    RecordKind,
    feature_record,
    read_commit,
    records_for,
    scope_document_record,
    spec_record,
    specified_by,
)
from tracepath.extract.schema import EntityType, ExtractedEntity, ExtractedRelationship, IdSource
from tracepath.extract.units import UnitKind, split_units
from tracepath.resolve.endpoints import (
    LinkContext,
    Target,
    build_label_index,
    resolve_endpoints,
    unresolved_id,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SCOPE = SNAPSHOT / "scope" / "scope.md"
COMMIT = "2e40bcf"


def scope_units() -> tuple[object, ...]:
    return split_units("scope/scope.md", SCOPE.read_text())


# Records are parsed from the file tree, never inferred.


def test_the_pinned_commit_is_read_from_the_snapshot_file() -> None:
    assert read_commit((ROOT / "corpus" / "jobhunt" / "SNAPSHOT.md").read_text()) == COMMIT


def test_a_snapshot_file_with_no_commit_raises() -> None:
    with pytest.raises(RecordError):
        read_commit("# Snapshot\n\nNo commit here.\n")


def test_a_spec_record_carries_its_number_title_status_and_aliases() -> None:
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"

    record = spec_record("specs/0012-model-client-router/index.md", path.read_text(), COMMIT)

    assert record.canonical_id == "0012"
    assert record.kind is RecordKind.SPEC
    assert record.title == "Model client router"
    assert record.status == "Accepted"
    assert record.commit == COMMIT
    assert set(record.aliases) == {
        "0012",
        "Model client router",
        "spec 0012",
        "0012-model-client-router",
    }


def test_every_spec_in_the_corpus_yields_a_record_with_a_title() -> None:
    for path in sorted(SNAPSHOT.glob("specs/*/index.md")):
        relative = str(path.relative_to(SNAPSHOT))
        record = spec_record(relative, path.read_text(), COMMIT)
        assert record.canonical_id == path.parent.name.split("-")[0]
        assert record.title
        assert record.status


def test_a_file_with_no_numbered_heading_is_an_error_not_a_guess() -> None:
    with pytest.raises(RecordError):
        spec_record("specs/0001-x/index.md", "No heading at all here.\n", COMMIT)


def test_the_scope_document_is_its_own_record() -> None:
    record = scope_document_record("scope/scope.md", SCOPE.read_text(), COMMIT)

    assert record.canonical_id == "scope"
    assert record.kind is RecordKind.SCOPE_DOCUMENT
    assert record.title == "Scope: JobHunt"


def test_a_feature_row_record_carries_its_status_without_its_tier_tag() -> None:
    unit = next(
        u
        for u in scope_units()
        if u.kind is UnitKind.FEATURE_ROW and u.record_id == "feature-21"  # type: ignore[attr-defined]
    )

    record = feature_record(unit, COMMIT)  # type: ignore[arg-type]

    assert record.canonical_id == "feature-21"
    assert record.kind is RecordKind.SCOPE_FEATURE
    assert record.title == "Terms & privacy notices"
    assert record.status == "done"  # the `· Alpha` tier tag is not a status
    assert "feature 21" in record.aliases


def test_a_feature_row_with_no_status_word_carries_none() -> None:
    unit = next(
        u
        for u in scope_units()
        if u.kind is UnitKind.FEATURE_ROW and u.record_id == "feature-11"  # type: ignore[attr-defined]
    )

    assert feature_record(unit, COMMIT).status is None  # type: ignore[arg-type]


def test_the_scope_document_yields_one_record_per_feature_row_plus_itself() -> None:
    units = split_units("scope/scope.md", SCOPE.read_text())

    records = records_for(units, SCOPE.read_text(), COMMIT)

    assert records[0].kind is RecordKind.SCOPE_DOCUMENT
    assert len(records) == 34  # the document plus its 33 feature rows
    assert all(r.kind is RecordKind.SCOPE_FEATURE for r in records[1:])


def test_only_a_feature_row_can_be_a_feature_record() -> None:
    preamble = scope_units()[0]

    with pytest.raises(RecordError):
        feature_record(preamble, COMMIT)  # type: ignore[arg-type]


# SPECIFIED_BY is read from the row's own pointer line, and a row without one has no link.


def test_fifteen_of_the_thirty_three_rows_cite_a_spec() -> None:
    rows = [u for u in scope_units() if u.kind is UnitKind.FEATURE_ROW]  # type: ignore[attr-defined]

    links = [specified_by(u) for u in rows]  # type: ignore[arg-type]

    assert len(rows) == 33
    assert sum(1 for link in links if link is not None) == 15


def test_a_pointer_line_names_the_spec_and_the_line_it_sits_on() -> None:
    row = next(
        u
        for u in scope_units()
        if u.kind is UnitKind.FEATURE_ROW and u.record_id == "feature-32"  # type: ignore[attr-defined]
    )

    link = specified_by(row)  # type: ignore[arg-type]

    assert link is not None
    assert link.spec_record == "0008"
    assert SCOPE.read_text().splitlines()[link.source_line - 1].startswith("_spec [0008]")


# AC-7 and AC-10: an endpoint that names nothing becomes a node, never a dropped link.


def link_with(target: dict[str, object]) -> ExtractedRelationship:
    return ExtractedRelationship.model_validate(
        {
            "type": "blocked-by",
            "source": {"kind": "local", "id": "0008/AC-1"},
            "target": target,
        }
    )


CONTEXT = LinkContext(source_record="0008", file="specs/0008/index.md", section="Preamble", line=7)


def test_a_reference_naming_a_known_entity_resolves_to_it() -> None:
    relationship = link_with({"kind": "reference", "record": "0001", "id": "AC-8", "mention": "x"})

    resolution = resolve_endpoints(
        [(relationship, CONTEXT)], frozenset({"0001/AC-8"}), frozenset({"0001"}), {}
    )

    assert resolution.links[0].target.canonical_id == "0001/AC-8"
    assert resolution.links[0].target.target is Target.ENTITY
    assert not resolution.unresolved


def test_a_reference_naming_only_a_record_resolves_to_that_record() -> None:
    relationship = link_with({"kind": "reference", "record": "0001", "mention": "spec 0001"})

    resolution = resolve_endpoints([(relationship, CONTEXT)], frozenset(), frozenset({"0001"}), {})

    assert resolution.links[0].target.canonical_id == "0001"
    assert resolution.links[0].target.target is Target.RECORD


def test_a_reference_naming_nothing_becomes_an_unresolved_node_keeping_its_words() -> None:
    relationship = link_with(
        {"kind": "reference", "mention": "spec 0001's binding rule 6"},
    )

    resolution = resolve_endpoints([(relationship, CONTEXT)], frozenset(), frozenset(), {})

    node = resolution.unresolved[0]
    assert node.mention == "spec 0001's binding rule 6"
    assert node.source_record == "0008"
    assert node.line == 7
    assert resolution.links[0].target.canonical_id == node.canonical_id
    assert resolution.links[0].target.target is Target.UNRESOLVED


def test_no_relationship_is_dropped_for_having_an_endpoint_that_cannot_be_named() -> None:
    relationships = [
        (link_with({"kind": "reference", "mention": f"mystery {n}"}), CONTEXT) for n in range(5)
    ]

    resolution = resolve_endpoints(relationships, frozenset(), frozenset(), {})

    assert len(resolution.links) == 5
    assert len(resolution.unresolved) == 5


def test_the_same_words_in_two_records_are_two_separate_unresolved_nodes() -> None:
    other = LinkContext(
        source_record="0014", file="specs/0014/index.md", section="Preamble", line=3
    )
    relationship = link_with({"kind": "reference", "mention": "binding rule 6"})

    resolution = resolve_endpoints(
        [(relationship, CONTEXT), (relationship, other)], frozenset(), frozenset(), {}
    )

    assert len(resolution.unresolved) == 2
    assert unresolved_id("0008", "binding rule 6") == "unresolved:0008:binding-rule-6"
    assert unresolved_id("0014", "binding rule 6") == "unresolved:0014:binding-rule-6"


def test_the_same_mention_twice_in_one_record_is_one_node() -> None:
    relationship = link_with({"kind": "reference", "mention": "binding rule 6"})

    resolution = resolve_endpoints(
        [(relationship, CONTEXT), (relationship, CONTEXT)], frozenset(), frozenset(), {}
    )

    assert len(resolution.links) == 2
    assert len(resolution.unresolved) == 1


# AC-7: a reference endpoint gains `label`, added 2026-09-23.


def test_a_labeled_reference_resolves_to_the_entity_carrying_that_label() -> None:
    relationship = link_with(
        {"kind": "reference", "record": "0001", "label": "binding rule 6", "mention": "x"}
    )

    resolution = resolve_endpoints(
        [(relationship, CONTEXT)],
        frozenset({"0001#binding-rules:6"}),
        frozenset({"0001"}),
        {("0001", "binding rule 6"): "0001#binding-rules:6"},
    )

    assert resolution.links[0].target.canonical_id == "0001#binding-rules:6"
    assert resolution.links[0].target.target is Target.ENTITY
    assert not resolution.unresolved


def test_a_labeled_reference_normalizes_before_matching() -> None:
    relationship = link_with(
        {"kind": "reference", "record": "0001", "label": "  Binding  Rule 6 ", "mention": "x"}
    )

    resolution = resolve_endpoints(
        [(relationship, CONTEXT)],
        frozenset({"0001#binding-rules:6"}),
        frozenset({"0001"}),
        {("0001", "binding rule 6"): "0001#binding-rules:6"},
    )

    assert resolution.links[0].target.target is Target.ENTITY


def test_a_labeled_reference_with_no_match_becomes_unresolved_never_the_record() -> None:
    relationship = link_with(
        {"kind": "reference", "record": "0001", "label": "binding rule 6", "mention": "x"}
    )

    resolution = resolve_endpoints([(relationship, CONTEXT)], frozenset(), frozenset({"0001"}), {})

    node = resolution.unresolved[0]
    assert node.record == "0001"
    assert node.label == "binding rule 6"
    assert resolution.links[0].target.target is Target.UNRESOLVED


def test_an_id_and_a_label_both_set_lets_id_win() -> None:
    relationship = link_with(
        {
            "kind": "reference",
            "record": "0001",
            "id": "AC-8",
            "label": "binding rule 6",
            "mention": "x",
        }
    )

    resolution = resolve_endpoints(
        [(relationship, CONTEXT)],
        frozenset({"0001/AC-8"}),
        frozenset({"0001"}),
        {("0001", "binding rule 6"): "0001#binding-rules:6"},
    )

    assert resolution.links[0].target.canonical_id == "0001/AC-8"


def test_a_label_with_no_record_falls_to_unresolved_like_any_other_unnameable_reference() -> None:
    relationship = link_with({"kind": "reference", "label": "binding rule 6", "mention": "x"})

    resolution = resolve_endpoints([(relationship, CONTEXT)], frozenset(), frozenset(), {})

    assert resolution.links[0].target.target is Target.UNRESOLVED
    assert resolution.unresolved[0].label == "binding rule 6"
    assert resolution.unresolved[0].record is None


def test_a_struck_entity_is_never_a_label_match_target() -> None:
    """`build_label_index()` excludes it; the current, unstruck version is what a
    reference to the label should reach, never a version AC-5 already marked struck."""

    def entity(canonical_id: str, struck: bool) -> IdentifiedEntity:
        return IdentifiedEntity(
            canonical_id=canonical_id,
            entity=ExtractedEntity(
                id="derived:1",
                id_source=IdSource.DERIVED,
                type=EntityType.CONSTRAINT,
                span="x",
                label="binding rule 6",
            ),
            location=None,
            struck=struck,
            followup_status=None,
        )

    index = build_label_index(
        [entity("0001#binding-rules:1", struck=True), entity("0001#binding-rules:2", struck=False)]
    )

    assert index[("0001", "binding rule 6")] == "0001#binding-rules:2"


def test_two_unstruck_entities_sharing_a_label_are_excluded_not_picked() -> None:
    def entity(canonical_id: str) -> IdentifiedEntity:
        return IdentifiedEntity(
            canonical_id=canonical_id,
            entity=ExtractedEntity(
                id="derived:1",
                id_source=IdSource.DERIVED,
                type=EntityType.CONSTRAINT,
                span="x",
                label="key invariant 1",
            ),
            location=None,
            struck=False,
            followup_status=None,
        )

    index = build_label_index([entity("0012#key-invariants:1"), entity("0012#key-invariants:2")])

    assert ("0012", "key invariant 1") not in index
