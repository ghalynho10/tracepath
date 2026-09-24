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

from tracepath.extract.compare import RoutedUnit, RunComparison
from tracepath.extract.ids import IdentifiedOutput
from tracepath.extract.records import Record, spec_record
from tracepath.extract.units import Unit, UnitKind
from tracepath.pipeline import UnitResult, resolve_accepted

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
