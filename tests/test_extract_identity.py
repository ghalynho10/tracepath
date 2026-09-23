import json
import re
from pathlib import Path
from typing import Any

import pytest

from tracepath.extract.compare import (
    COLLAPSED,
    LINE_PREFIX,
    ComparisonError,
    ReviewReason,
    ReviewReasonName,
    compare_runs,
    entity_identity,
    entity_signature,
    route_runs,
)
from tracepath.extract.ids import (
    IdAssignmentError,
    assign_ids,
    locate_output,
    section_slugs,
    slugify,
)
from tracepath.extract.locate import ALIGNMENT_THRESHOLD, align, locate_line, locate_verbatim
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind, split_units

SNAPSHOT = Path(__file__).resolve().parents[1] / "corpus" / "jobhunt" / "docs"
RUNS = Path(__file__).parent / "fixtures" / "runs"


def load(name: str) -> ExtractionOutput:
    payload: dict[str, Any] = json.loads((RUNS / f"{name}.json").read_text())
    return ExtractionOutput.model_validate(payload)


def unit_named(spec: str, section: str) -> Unit:
    path = next(SNAPSHOT.glob(f"specs/{spec}-*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    return next(u for u in units if u.section == section)


def unit_of(text: str) -> Unit:
    return Unit(
        kind=UnitKind.SECTION,
        record_id="0012",
        section="Requirements",
        text=text,
        path="specs/0012-model-client-router/index.md",
        start_offset=0,
        start_line=1,
    )


def identified(name: str, unit: Unit, record: str = "0011", slug: str = "requirements") -> Any:
    return assign_ids(locate_output(unit, load(name)), record, slug)


# AC-4: a line is located or it is null, never guessed.


def test_a_verbatim_id_is_located_at_its_own_definition_line() -> None:
    unit = unit_named("0012", "Requirements")

    located = locate_verbatim(unit, "AC-8")

    assert located is not None
    assert unit.text.splitlines()[located.line - 1].startswith("- **AC-8**:")


def test_a_verbatim_id_the_unit_does_not_define_is_not_located() -> None:
    assert locate_verbatim(unit_named("0012", "Requirements"), "AC-999") is None


def test_an_exact_span_is_located_at_its_own_offset() -> None:
    unit = unit_of("line one\nline two holds the span here\nline three\n")

    located = locate_line(unit, "the span here")

    assert located is not None
    assert located.line == 2
    assert located.method == "exact"
    assert located.score == 1.0


def test_a_span_with_a_rationale_clause_removed_still_locates() -> None:
    source = (
        "- **AC-1**: A call is decided by one atomic database function, because two "
        "separate reads cannot be made atomic, and it returns a decision.\n"
    )
    span = "A call is decided by one atomic database function and it returns a decision."

    located = locate_line(unit_of(source), span)

    assert located is not None
    assert located.method == "aligned"
    assert located.score >= ALIGNMENT_THRESHOLD


def test_a_span_belonging_to_another_document_is_not_located_at_all() -> None:
    unit = unit_of("- **AC-1**: The proxy withholds the refreshed cookie from an action.\n")

    assert locate_line(unit, "Every seeded listing carries an obviously fake company name.") is None


def test_an_unlocatable_span_returns_none_rather_than_a_nearby_line() -> None:
    unit = unit_of("- **AC-1**: something entirely unrelated to the span below.\n")

    assert locate_line(unit, "x" * 200) is None


# AC-4: the threshold is a measured separation, not a picked number.


def criteria_bullets() -> list[tuple[Unit, str, int]]:
    """Every real acceptance criterion in the corpus, with the line it is defined on."""
    bullets: list[tuple[Unit, str, int]] = []
    for path in sorted(SNAPSHOT.glob("specs/*/index.md")):
        for unit in split_units(str(path.relative_to(SNAPSHOT)), path.read_text()):
            if unit.kind is not UnitKind.SECTION:
                continue
            for match in re.finditer(
                r"^- \*\*AC-\d+[a-z]?\*\*: (.+?)(?=\n- |\n\n|\Z)", unit.text, re.S | re.M
            ):
                body = match.group(1).strip()
                if len(body) > 80:
                    bullets.append((unit, body, unit.text.count("\n", 0, match.start(1)) + 1))
    return bullets


def as_extraction_would(text: str) -> str:
    """Mutate a criterion the way extraction mutates it.

    A rationale clause is dropped, hard wrapping is collapsed, inline markup is
    stripped. This is why a span is so often not a verbatim substring of its source.
    """
    collapsed = re.sub(r"\s*\n\s*", " ", text)
    plain = re.sub(r"\*\*|`|~~", "", collapsed)
    sentences = re.split(r"(?<=\.) ", plain)
    trimmed = " ".join(sentences[:-1]) if len(sentences) > 2 else plain
    return re.sub(r", (because|since|which|so that)[^,.]*", "", trimmed, count=1)


def test_a_mutated_criterion_still_lands_on_the_line_it_came_from() -> None:
    """The fast guard: locating a realistic span returns its own definition line."""
    sample = criteria_bullets()[::10]
    assert len(sample) > 20

    landed = [locate_line(unit, as_extraction_would(body)) for unit, body, _ in sample]
    correct = sum(
        1
        for located, (_, _, true_line) in zip(landed, sample, strict=True)
        if located is not None and located.line == true_line
    )

    assert correct / len(sample) >= 0.95, f"only {correct} of {len(sample)} landed on their line"


@pytest.mark.slow
def test_the_threshold_separates_a_genuine_span_from_a_wrong_unit() -> None:
    """Re-derive, over the whole corpus, the measurement the threshold rests on.

    A corpus change that closed the separation this number depends on should fail
    here rather than pass quietly. The adversarial pool is the other `Requirements`
    sections, which carry the near identical criterion wording the spec warns about.
    """
    bullets = criteria_bullets()
    assert len(bullets) > 250, "the corpus should hold hundreds of real criteria"
    units = list({id(unit): unit for unit, _, _ in bullets}.values())

    own_scores: list[float] = []
    correct_line = 0
    for unit, body, true_line in bullets:
        located = locate_line(unit, as_extraction_would(body))
        own_scores.append(located.score if located else 0.0)
        if located is not None and located.line == true_line:
            correct_line += 1

    wrong_scores: list[float] = []
    for unit, body, _ in bullets[::4]:
        span = as_extraction_would(body)
        for other in units:
            if other is unit:
                continue
            scored = align(other.text, span)
            if scored:
                wrong_scores.append(scored[1])

    located_share = sum(1 for s in own_scores if s >= ALIGNMENT_THRESHOLD) / len(own_scores)
    assert located_share >= 0.98, f"only {located_share:.1%} of genuine spans clear the threshold"
    assert correct_line / len(bullets) >= 0.98, "the located line drifted from the true line"
    assert wrong_scores, "the study needs wrong unit scores to separate against"
    assert max(wrong_scores) < ALIGNMENT_THRESHOLD, (
        f"a wrong unit scored {max(wrong_scores):.3f}, at or above the threshold"
    )


# AC-3: code owns identity.


def test_a_verbatim_id_is_qualified_by_its_record() -> None:
    unit = unit_named("0011", "Requirements")

    output = identified("run1", unit)

    assert [e.canonical_id for e in output.entities] == ["0011/AC-1"]


def test_every_other_entity_gets_a_derived_id_naming_its_section() -> None:
    unit = unit_of("- **AC-1**: first.\n\n- a second item with no id of its own at all here.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "first.",
                },
                {
                    "id": "derived:1",
                    "id_source": "derived",
                    "type": "Constraint",
                    "span": "a second item with no id of its own at all here.",
                },
            ],
            "relationships": [],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0012", "requirements")

    assert [e.canonical_id for e in output.entities] == ["0012/AC-1", "0012#requirements:1"]


def test_derived_ids_are_numbered_by_where_the_span_sits_not_by_output_order() -> None:
    unit = unit_of("alpha comes first in the source text here.\nbeta comes second in the text.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "derived:1",
                    "id_source": "derived",
                    "type": "Constraint",
                    "span": "beta comes second in the text.",
                },
                {
                    "id": "derived:2",
                    "id_source": "derived",
                    "type": "Constraint",
                    "span": "alpha comes first in the source text here.",
                },
            ],
            "relationships": [],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0012", "requirements")

    by_span = {e.entity.span: e.canonical_id for e in output.entities}
    assert by_span["alpha comes first in the source text here."] == "0012#requirements:1"
    assert by_span["beta comes second in the text."] == "0012#requirements:2"


def test_an_unlocatable_span_is_numbered_behind_every_located_one() -> None:
    unit = unit_of("alpha comes first in the source text here and runs on.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "derived:1",
                    "id_source": "derived",
                    "type": "Constraint",
                    "span": "nothing in the unit resembles this span in the slightest way at all",
                },
                {
                    "id": "derived:2",
                    "id_source": "derived",
                    "type": "Constraint",
                    "span": "alpha comes first in the source text here and runs on.",
                },
            ],
            "relationships": [],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0012", "requirements")

    assert output.entities[0].canonical_id == "0012#requirements:2"
    assert output.entities[0].location is None
    assert output.entities[1].canonical_id == "0012#requirements:1"


def test_a_section_slug_repeating_inside_one_record_is_suffixed() -> None:
    slugs = section_slugs(("Follow-up", "Build plan", "Follow up", "Follow-up"))

    assert slugs == ("follow-up", "build-plan", "follow-up-2", "follow-up-3")
    assert len(set(slugs)) == len(slugs), "a slug must name exactly one section"
    assert slugify("Options considered") == "options-considered"


def test_every_real_record_gets_one_distinct_slug_per_section() -> None:
    for path in sorted(SNAPSHOT.glob("specs/*/index.md")):
        units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
        slugs = section_slugs(tuple(u.section for u in units))
        assert len(set(slugs)) == len(slugs), path.parent.name


def test_a_relationship_endpoint_is_rewritten_to_the_canonical_id() -> None:
    unit = unit_of("- **AC-1**: the criterion.\n\nthe build step that satisfies it appears here.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "the criterion.",
                },
                {
                    "id": "derived:1",
                    "id_source": "derived",
                    "type": "BuildStep",
                    "span": "the build step that satisfies it appears here.",
                },
            ],
            "relationships": [
                {
                    "type": "satisfies",
                    "source": {"kind": "local", "id": "derived:1"},
                    "target": {"kind": "local", "id": "AC-1"},
                }
            ],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0012", "requirements")

    link = output.relationships[0]
    assert link.source.id == "0012#requirements:1"
    assert link.target.id == "0012/AC-1"


def test_a_reference_endpoint_is_left_for_the_resolver() -> None:
    unit = unit_of("- **AC-1**: the criterion, blocked until spec 0001 lands.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "the criterion, blocked until spec 0001 lands.",
                }
            ],
            "relationships": [
                {
                    "type": "blocked-by",
                    "source": {"kind": "local", "id": "AC-1"},
                    "target": {"kind": "reference", "record": "0001", "mention": "spec 0001"},
                }
            ],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0012", "requirements")

    assert output.relationships[0].target.mention == "spec 0001"  # type: ignore[union-attr]


# AC-5: the struck version of a verbatim id gives up the id, it is not dropped.


def test_where_one_id_carries_struck_and_unstruck_text_only_the_unstruck_keeps_it() -> None:
    unit = unit_of(
        "- **AC-2**: ~~The page makes no external paid call on any render at all.~~ "
        "· The page still makes no external paid call on any render whatsoever.\n"
    )
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-2",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "The page makes no external paid call on any render at all.",
                },
                {
                    "id": "AC-2",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "The page still makes no external paid call on any render whatsoever.",
                },
            ],
            "relationships": [],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0021", "requirements")

    by_span = {e.entity.span: e for e in output.entities}
    old = by_span["The page makes no external paid call on any render at all."]
    new = by_span["The page still makes no external paid call on any render whatsoever."]
    assert old.struck is True
    assert new.struck is False
    assert new.canonical_id == "0021/AC-2"
    assert old.canonical_id == "0021#requirements:1"


def test_an_endpoint_naming_no_entity_raises_rather_than_writing_a_dangling_link() -> None:
    unit = unit_of("- **AC-1**: the criterion.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "the criterion.",
                }
            ],
            "relationships": [],
        }
    )
    located = locate_output(unit, raw)
    broken = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "the criterion.",
                }
            ],
            "relationships": [
                {
                    "type": "satisfies",
                    "source": {"kind": "local", "id": "AC-1"},
                    "target": {"kind": "local", "id": "AC-1"},
                }
            ],
        }
    )
    tampered = type(located)(
        entities=located.entities,
        relationships=(
            broken.relationships[0].model_copy(
                update={"source": broken.relationships[0].source.model_copy(update={"id": "AC-99"})}
            ),
        ),
    )

    with pytest.raises(IdAssignmentError):
        assign_ids(tampered, "0012", "requirements")


# AC-11: agreement rests on the signature and nothing else.


def test_the_three_agreeing_fixture_runs_agree_despite_differing_span_text() -> None:
    unit = unit_named("0011", "Requirements")
    outputs = [identified(name, unit) for name in ("run1", "run2", "run3")]

    comparison = compare_runs(outputs)

    assert comparison.agree
    assert not comparison.differing_entities


def test_the_split_run_reads_as_a_disagreement() -> None:
    unit = unit_named("0011", "Requirements")
    outputs = [identified(name, unit) for name in ("run1", "run2", "run_split")]

    comparison = compare_runs(outputs)

    assert not comparison.agree
    assert comparison.differing_entities


def test_a_derived_entity_is_identified_by_its_located_line() -> None:
    """AC-11a: a verbatim id stands as it is, a derived one becomes its located line.

    The line is what keeps agreement honest once flags leave the signature. Without
    it every derived entity of one type would share the tuple (`<derived>`, type), so
    three runs could extract entirely different spans and still read as agreeing.
    """
    unit = unit_named("0011", "Requirements")
    split = identified("run_split", unit)

    signatures = {entity_signature(e)[0] for e in split.entities}

    assert "0011/AC-1" in signatures
    assert any(s.startswith(LINE_PREFIX) for s in signatures)
    assert COLLAPSED not in signatures


def test_a_derived_entity_whose_span_cannot_be_located_collapses() -> None:
    """AC-11a's fallback: `<derived>` survives only for an unlocatable span."""
    unit = unit_of("- **AC-1**: a plain criterion with nothing ambiguous about it.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "derived:1",
                    "id_source": "derived",
                    "type": "Constraint",
                    "span": "Every seeded listing carries an obviously fake company name.",
                }
            ],
            "relationships": [],
        }
    )

    output = assign_ids(locate_output(unit, raw), "0012", "requirements")
    entity = output.entities[0]

    assert entity.location is None, "this span should not locate in this unit"
    assert entity_identity(entity) == COLLAPSED
    assert entity_signature(entity) == (COLLAPSED, "Constraint")


def test_comparing_fewer_than_two_runs_raises() -> None:
    unit = unit_named("0011", "Requirements")

    with pytest.raises(ComparisonError):
        compare_runs([identified("run1", unit)])


# AC-11: only accepted items reach the graph.


def test_an_item_carrying_a_known_trap_flag_is_held_for_review() -> None:
    unit = unit_named("0011", "Requirements")
    outputs = [identified(name, unit) for name in ("run1", "run2", "run3")]

    routed = route_runs(outputs)

    assert not routed.accepted_entities
    assert ReviewReason(ReviewReasonName.KNOWN_TRAP_FLAG) in routed.review[0].reasons


def test_an_unflagged_agreed_entity_is_accepted() -> None:
    unit = unit_of("- **AC-1**: a plain criterion with nothing ambiguous about it at all.\n")
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "a plain criterion with nothing ambiguous about it at all.",
                }
            ],
            "relationships": [],
        }
    )
    outputs = [assign_ids(locate_output(unit, raw), "0012", "requirements") for _ in range(3)]

    routed = route_runs(outputs)

    assert [e.canonical_id for e in routed.accepted_entities] == ["0012/AC-1"]
    assert not routed.review


def test_an_unclassified_entity_is_held_back_but_an_unclassified_link_goes_straight_through() -> (
    None
):
    unit = unit_of(
        "- a thing that fits no named type at all in this whole section.\n"
        "- **AC-1**: a plain criterion with nothing ambiguous about it whatsoever.\n"
    )
    raw = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "derived:1",
                    "id_source": "derived",
                    "type": "unclassified",
                    "span": "a thing that fits no named type at all in this whole section.",
                    "unclassified_note": "it is neither a constraint nor a consequence",
                },
                {
                    "id": "AC-1",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "a plain criterion with nothing ambiguous about it whatsoever.",
                },
            ],
            "relationships": [
                {
                    "type": "unclassified",
                    "source": {"kind": "local", "id": "AC-1"},
                    "target": {"kind": "reference", "record": "0019", "mention": "spec 0019"},
                    "phrase": "already seeded by",
                }
            ],
        }
    )
    outputs = [assign_ids(locate_output(unit, raw), "0012", "requirements") for _ in range(3)]

    routed = route_runs(outputs)

    assert [e.canonical_id for e in routed.accepted_entities] == ["0012/AC-1"]
    assert len(routed.accepted_relationships) == 1
    assert routed.accepted_relationships[0].phrase == "already seeded by"
    assert routed.review[0].reasons == (ReviewReason(ReviewReasonName.UNCLASSIFIED_TYPE),)


def test_a_signature_only_some_runs_produced_is_held_for_review() -> None:
    unit = unit_named("0011", "Requirements")
    outputs = [identified(name, unit) for name in ("run1", "run2", "run_split")]

    routed = route_runs(outputs)

    assert any(
        ReviewReason(ReviewReasonName.RUNS_DISAGREE) in item.reasons for item in routed.review
    )
    assert not routed.accepted_entities


# AC-11a/b: the amended comparator, added 2026-09-23.


def _output(entities: list[dict[str, Any]], flags: tuple[str, ...] = ()) -> ExtractionOutput:
    return ExtractionOutput.model_validate(
        {
            "entities": [{**e, "known_trap_flags": list(flags)} for e in entities],
            "relationships": [],
        }
    )


ALPHA = {
    "id": "derived:1",
    "id_source": "derived",
    "type": "Constraint",
    "span": "alpha claim about caching",
}
BETA = {
    "id": "derived:2",
    "id_source": "derived",
    "type": "Constraint",
    "span": "beta claim about retries",
}
ONE_LINE = "- **AC-9**: alpha claim about caching, and beta claim about retries.\n"


def test_flag_churn_alone_no_longer_breaks_agreement() -> None:
    """AC-11a: runs agreeing on identity and type agree, however the flags move.

    The flagged item still routes to review on its own trigger, which is the point:
    the flag was being counted twice, and the second count marked *neighbours* as
    disagreements.
    """
    unit = unit_of(ONE_LINE)
    outputs = [
        assign_ids(locate_output(unit, _output([ALPHA], flags=flags)), "0012", "requirements")
        for flags in (("rationale_boundary_call",), (), ("multi_condition_split",))
    ]

    comparison = compare_runs(outputs)
    routed = route_runs(outputs)

    assert comparison.agree, "identical identity and type should agree whatever the flags do"
    assert not comparison.differing_entities
    assert not routed.accepted_entities, "the flag still holds it back on its own trigger"
    assert routed.review[0].reasons == (ReviewReason(ReviewReasonName.KNOWN_TRAP_FLAG),)
    assert routed.review[0].canonical_id == "0012#requirements:1"
    assert routed.review[0].line == 1


def test_a_count_that_differs_holds_every_copy_not_just_the_surplus() -> None:
    """AC-11b: two entities share a signature in one run and one in the others.

    Accepting the first `min(counts)` would assert a correspondence the runs never
    established, so every copy of that signature is held.
    """
    unit = unit_of(ONE_LINE)
    outputs = [
        assign_ids(locate_output(unit, _output(entities)), "0012", "requirements")
        for entities in ([ALPHA, BETA], [ALPHA], [ALPHA])
    ]

    comparison = compare_runs(outputs)
    routed = route_runs(outputs)

    assert {e.entity.span for e in outputs[0].entities} == {ALPHA["span"], BETA["span"]}
    assert [entity_signature(e) for e in outputs[0].entities] == [
        ("line:1", "Constraint"),
        ("line:1", "Constraint"),
    ], "both spans sit on the same line, so they share one signature"
    assert not comparison.agree
    assert comparison.entity_counts == ((("line:1", "Constraint"), (2, 1, 1)),)
    assert not routed.accepted_entities, "every copy is held, not just the surplus"
    assert len(routed.review) == 2
