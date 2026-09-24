"""`resolve_accepted()` when a unit identified nothing, the case its guard existed for.

A `UnitResult` whose `identified` is empty is what a unit looks like when no run of it
produced usable output. `resolve_accepted()` has always meant to skip such a unit: it
has no entities to name and no links to resolve, so it contributes nothing.

The guard it carried could not do that job. It read:

    known_ids = frozenset(
        entity.canonical_id
        for result in results
        for entity in result.identified[0].entities
        if result.identified              # <- too late, [0] already happened
    )

A comprehension evaluates its clauses left to right, so `result.identified[0]` is
indexed before the trailing `if` ever runs, and the `IndexError` the guard was written
to prevent is raised on the way to the guard. The loop below it indexed `identified[0]`
with no guard at all, so even a corrected comprehension would have failed one line
later.

These tests fail with an `IndexError` against either of those two versions.
"""

from pathlib import Path

from tracepath.extract.compare import (
    ReviewItem,
    ReviewReason,
    ReviewReasonName,
    RoutedUnit,
    RunComparison,
)
from tracepath.extract.ids import IdentifiedEntity, IdentifiedOutput
from tracepath.extract.records import Record, RecordKind, spec_record
from tracepath.extract.schema import EntityType, ExtractedEntity, ExtractedRelationship, IdSource
from tracepath.extract.units import Unit, UnitKind
from tracepath.pipeline import UnitResult, resolve_accepted
from tracepath.resolve.endpoints import Target

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"

EMPTY_COMPARISON = RunComparison(
    agree=True,
    shared_entities=frozenset(),
    differing_entities=frozenset(),
    shared_relationships=frozenset(),
    differing_relationships=frozenset(),
    entity_counts=(),
    relationship_counts=(),
)


def a_unit() -> Unit:
    """One real unit, so nothing here depends on a fabricated path or record id."""
    return Unit(
        kind=UnitKind.SECTION,
        record_id="0012",
        section="Requirements",
        text="- **AC-1**: a plain criterion.\n",
        path="specs/0012-model-client-router/index.md",
        start_offset=0,
        start_line=1,
    )


def a_result(identified: tuple[IdentifiedOutput, ...]) -> UnitResult:
    """A unit result carrying whatever was identified, and nothing accepted."""
    return UnitResult(
        unit=a_unit(),
        section_slug="requirements",
        artifacts=(),
        identified=identified,
        routed=RoutedUnit(
            comparison=EMPTY_COMPARISON,
            accepted_entities=(),
            accepted_relationships=(),
            review=(),
        ),
        input_tokens=0,
        output_tokens=0,
    )


def a_record() -> Record:
    """The Record the unit hangs from, read from the pinned snapshot."""
    path = next(SNAPSHOT.glob("specs/0012-*/index.md"))
    return spec_record(str(path.relative_to(SNAPSHOT)), path.read_text(), COMMIT)


def test_a_unit_that_identified_nothing_is_skipped_rather_than_indexed() -> None:
    """The whole point of the guard: no run produced output, so there is nothing here.

    Before the fix this raised `IndexError: tuple index out of range`, from the
    comprehension that builds `known_ids`.
    """
    corpus = resolve_accepted([a_result(identified=())], [a_record()])

    assert corpus.resolution.links == ()
    assert corpus.held == ()


def test_a_unit_that_identified_nothing_does_not_stop_the_units_that_did() -> None:
    """The real shape of the bug: one bad unit must not take the whole corpus down.

    A corpus run holds many units. If one of them identified nothing, resolution of
    every other unit still has to complete, or a single empty unit loses the run.
    """
    corpus = resolve_accepted(
        [a_result(identified=()), a_result(identified=())],
        [a_record()],
    )

    assert corpus.resolution.links == ()
    assert corpus.held == ()


# AC-7: a `{record, label}` reference held or resolved, added 2026-09-23.
#
# The worked example this pins: 0008's preamble names "spec 0001's binding rule 6", and
# spec 0001's own `## Binding rules` section identifies that item but a run disagreement
# routes it to review. The reference must hold on it (AC-11c), never fall through to
# `:Unresolved`; the target is named, it just has not been ruled on yet.


def binding_rule_unit() -> Unit:
    return Unit(
        kind=UnitKind.SECTION,
        record_id="0001",
        section="Binding rules",
        text="**6.** Authorisation is never decided in the proxy.\n",
        path="specs/0001-stack-and-architecture/index.md",
        start_offset=0,
        start_line=1,
    )


def held_binding_rule_result() -> UnitResult:
    """Spec 0001's binding rule 6: identified, but a run disagreement holds it."""
    entity = IdentifiedEntity(
        canonical_id="0001#binding-rules:1",
        entity=ExtractedEntity(
            id="derived:1",
            id_source=IdSource.DERIVED,
            type=EntityType.CONSTRAINT,
            span="Authorisation is never decided in the proxy.",
            label="binding rule 6",
        ),
        location=None,
        struck=False,
        followup_status=None,
    )
    return UnitResult(
        unit=binding_rule_unit(),
        section_slug="binding-rules",
        artifacts=(),
        identified=(IdentifiedOutput(entities=(entity,), relationships=()),),
        routed=RoutedUnit(
            comparison=EMPTY_COMPARISON,
            accepted_entities=(),
            accepted_relationships=(),
            review=(
                ReviewItem(
                    signature=("<derived>", "Constraint"),
                    reasons=(ReviewReason(ReviewReasonName.RUNS_DISAGREE),),
                    canonical_id="0001#binding-rules:1",
                ),
            ),
        ),
        input_tokens=0,
        output_tokens=0,
    )


def preamble_unit() -> Unit:
    return Unit(
        kind=UnitKind.PREAMBLE,
        record_id="0008",
        section="Preamble",
        text="Spec 0001's binding rule 6 amendment gains a third item, dated the same day.\n",
        path="specs/0008-app-shell-and-navigation/index.md",
        start_offset=0,
        start_line=1,
    )


def preamble_result(*, matching_label: str = "binding rule 6") -> UnitResult:
    """0008's preamble: no local entities, one accepted reference to a labeled item."""
    relationship = ExtractedRelationship.model_validate(
        {
            "type": "amended-by",
            "source": {
                "kind": "reference",
                "record": "0001",
                "label": matching_label,
                "mention": "Spec 0001's binding rule 6",
            },
            "target": {"kind": "reference", "record": "0008", "mention": "0008"},
        }
    )
    return UnitResult(
        unit=preamble_unit(),
        section_slug="preamble",
        artifacts=(),
        identified=(IdentifiedOutput(entities=(), relationships=(relationship,)),),
        routed=RoutedUnit(
            comparison=EMPTY_COMPARISON,
            accepted_entities=(),
            accepted_relationships=(relationship,),
            review=(),
        ),
        input_tokens=0,
        output_tokens=0,
    )


def two_records() -> list[Record]:
    return [
        Record(
            canonical_id="0001",
            kind=RecordKind.SPEC,
            title="Stack and architecture",
            status="Accepted",
            path="specs/0001-stack-and-architecture/index.md",
            commit=COMMIT,
            aliases=(),
        ),
        Record(
            canonical_id="0008",
            kind=RecordKind.SPEC,
            title="App shell and navigation",
            status="Accepted",
            path="specs/0008-app-shell-and-navigation/index.md",
            commit=COMMIT,
            aliases=(),
        ),
    ]


def test_a_labeled_reference_to_a_held_entity_holds_the_link_not_unresolved() -> None:
    corpus = resolve_accepted([held_binding_rule_result(), preamble_result()], two_records())

    assert corpus.resolution.links == ()
    assert corpus.resolution.unresolved == ()
    assert len(corpus.held) == 1
    assert corpus.held[0].item.reasons == (
        ReviewReason(ReviewReasonName.ENDPOINT_NOT_ACCEPTED, detail="0001#binding-rules:1"),
    )


def test_a_labeled_reference_to_an_accepted_entity_resolves_to_it() -> None:
    accepted = held_binding_rule_result()
    accepted = UnitResult(
        unit=accepted.unit,
        section_slug=accepted.section_slug,
        artifacts=accepted.artifacts,
        identified=accepted.identified,
        routed=RoutedUnit(
            comparison=EMPTY_COMPARISON,
            accepted_entities=accepted.identified[0].entities,
            accepted_relationships=(),
            review=(),
        ),
        input_tokens=0,
        output_tokens=0,
    )

    corpus = resolve_accepted([accepted, preamble_result()], two_records())

    assert corpus.held == ()
    assert corpus.resolution.unresolved == ()
    assert len(corpus.resolution.links) == 1
    assert corpus.resolution.links[0].source.canonical_id == "0001#binding-rules:1"
    assert corpus.resolution.links[0].source.target is Target.ENTITY


def test_a_labeled_reference_with_no_matching_entity_at_all_becomes_unresolved() -> None:
    """No unit identifying "binding rule 6" ever ran, so the reference cannot be held
    on anything: it is genuinely unnameable, and AC-7's fallback applies."""
    corpus = resolve_accepted([preamble_result()], two_records())

    assert corpus.held == ()
    assert len(corpus.resolution.unresolved) == 1
    node = corpus.resolution.unresolved[0]
    assert node.record == "0001"
    assert node.label == "binding rule 6"
    assert node.mention == "Spec 0001's binding rule 6"
