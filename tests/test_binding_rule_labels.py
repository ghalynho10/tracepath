"""The binding rule label pre-check: `binding rule N` comes from the text, not the model.

Spec 0003 closes the labelled reference defect experiment 0004 found: the reference
side wrote `binding rule 6` stably, and the entity it named never carried a label at
all, because nothing in that rule's own text says "binding rule 6". Code reads the
number off the rule's bold marker instead (AC-1 to AC-5), and AC-12 proves it against
the committed runs with no API call.

Nothing here calls the API or the database, and nothing writes into the committed
artifacts: the rebuild case copies one unit's runs under `tmp_path`.
"""

import shutil
from pathlib import Path
from typing import Any

from tracepath.artifacts import RUNS_DIR
from tracepath.extract.ids import LocatedOutput, assign_ids, label_binding_rules, locate_output
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind
from tracepath.rebuild import committed_units
from tracepath.resolve.endpoints import build_label_index

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
BINDING_RULES = Path("0001") / "binding-rules"

RULES_TEXT = (
    "## Binding rules\n\n"
    "**1. Every request is authorised by the server action itself.** The proxy never decides.\n\n"
    "A second paragraph under rule one, which the model may split out as its own item.\n\n"
    "**2. The secret key is constructed in exactly one module.** Nowhere else builds it.\n\n"
    "**3. Alert rules live in version control beside the code.** They are reviewed.\n"
)

RULE_1 = "Every request is authorised by the server action itself."
RULE_1_BODY = "The proxy never decides."
RULE_1_SECOND_PARAGRAPH = "A second paragraph under rule one, which the model may split out"
RULE_2 = "The secret key is constructed in exactly one module."


def rules_unit(text: str = RULES_TEXT, section: str = "Binding rules") -> Unit:
    return Unit(
        kind=UnitKind.SECTION,
        record_id="0001",
        section=section,
        text=text,
        path="specs/0001-stack-and-architecture/index.md",
        start_offset=0,
        start_line=1,
    )


def entity(n: int, span: str, label: str | None = None) -> dict[str, Any]:
    return {
        "id": f"derived:{n}",
        "id_source": "derived",
        "type": "Constraint",
        "span": span,
        "label": label,
    }


def labelled(unit: Unit, entities: list[dict[str, Any]]) -> tuple[str | None, ...]:
    output = ExtractionOutput.model_validate({"entities": entities, "relationships": []})
    located = label_binding_rules(unit, locate_output(unit, output))
    return tuple(item.entity.label for item in located.entities)


# AC-1: the one entity inside a rule's leading span gets that rule's label.


def test_the_entity_on_a_rule_opening_line_is_labelled_with_the_rule_number() -> None:
    labels = labelled(rules_unit(), [entity(1, RULE_1), entity(2, RULE_2)])

    assert labels == ("binding rule 1", "binding rule 2")


def test_the_pre_check_label_overwrites_whatever_the_model_wrote_on_its_target() -> None:
    labels = labelled(rules_unit(), [entity(1, RULE_1, label="rule one")])

    assert labels == ("binding rule 1",)


def test_the_stored_output_is_never_changed_by_the_pre_check() -> None:
    unit = rules_unit()
    output = ExtractionOutput.model_validate(
        {"entities": [entity(1, RULE_1, label="rule one")], "relationships": []}
    )

    label_binding_rules(unit, locate_output(unit, output))

    assert output.entities[0].label == "rule one"


# AC-2: two entities in one leading span is ambiguous; outside every span is never labelled.


def test_two_entities_inside_one_leading_span_leave_that_rule_unlabelled() -> None:
    labels = labelled(rules_unit(), [entity(1, RULE_1), entity(2, RULE_1_BODY), entity(3, RULE_2)])

    assert labels == (None, None, "binding rule 2")


def test_an_entity_in_a_later_paragraph_of_a_rule_is_outside_its_leading_span() -> None:
    labels = labelled(rules_unit(), [entity(1, RULE_1), entity(2, RULE_1_SECOND_PARAGRAPH)])

    assert labels == ("binding rule 1", None)


# AC-3: no entity inside a rule's leading span sets nothing for that rule.


def test_a_rule_with_no_entity_on_its_leading_span_sets_no_label() -> None:
    labels = labelled(rules_unit(), [entity(1, RULE_2)])

    assert labels == ("binding rule 2",)


def test_an_entity_that_could_not_be_located_is_never_labelled() -> None:
    labels = labelled(rules_unit(), [entity(1, "words that appear nowhere in this unit at all")])

    assert labels == (None,)


# AC-4: a stray model label in a binding rules unit is cleared unless it is verbatim.
# The labels below are the real ones the model invented in the committed `0006`
# `## Feature design` runs (`artifacts/runs/0006/feature-design/run-1.json`), adapted
# onto a binding rules fixture, since `0006` is not itself a binding rules unit.


def test_invented_labels_from_the_committed_0006_runs_are_cleared() -> None:
    labels = labelled(
        rules_unit(),
        [
            entity(1, RULE_1_SECOND_PARAGRAPH, label="key invariant 1"),
            entity(2, RULE_1, label="key invariant 2"),
            entity(3, RULE_2, label="COPY-1"),
            entity(4, "Alert rules live in version control beside the code.", label="Tell #4"),
        ],
    )

    # The first sits outside every leading span, so it is cleared outright; the other
    # three are each their rule's one target, so the rule's own label replaces them.
    assert labels == (None, "binding rule 1", "binding rule 2", "binding rule 3")


def test_a_label_that_sits_verbatim_in_its_own_span_survives() -> None:
    text = (
        "## Binding rules\n\n**1. A rule.** Body.\n\n"
        "COPY-1, the sign in line, is kept as written.\n"
    )

    labels = labelled(
        rules_unit(text),
        [entity(1, "COPY-1, the sign in line, is kept as written.", label="COPY-1")],
    )

    assert labels == ("COPY-1",)


# AC-5: only a `## Binding rules` section with bold numbered items is read.


def test_a_section_with_another_name_is_left_exactly_as_the_model_wrote_it() -> None:
    unit = rules_unit(section="Requirements")

    labels = labelled(unit, [entity(1, RULE_1, label="key invariant 1")])

    assert labels == ("key invariant 1",)


def test_a_binding_rules_section_with_no_numbered_items_is_left_unchanged() -> None:
    text = "## Binding rules\n\n- Every request is authorised by the server action itself.\n"
    unit = rules_unit(text)
    output = ExtractionOutput.model_validate(
        {"entities": [entity(1, RULE_1, label="key invariant 1")], "relationships": []}
    )
    located = locate_output(unit, output)

    assert label_binding_rules(unit, located) is located


def test_a_labelled_located_output_keeps_its_relationships() -> None:
    unit = rules_unit()
    located = locate_output(
        unit, ExtractionOutput.model_validate({"entities": [entity(1, RULE_1)]})
    )

    result = label_binding_rules(unit, located)

    assert isinstance(result, LocatedOutput)
    assert result.relationships == located.relationships


# AC-12: rebuilt from the committed `0002.3` runs, no API call, `binding rule 6` resolves.


def test_binding_rule_6_resolves_to_one_entity_on_its_opening_line_in_every_committed_run(
    tmp_path: Path,
) -> None:
    destination = tmp_path / RUNS_DIR / BINDING_RULES
    destination.parent.mkdir(parents=True)
    shutil.copytree(ROOT / RUNS_DIR / BINDING_RULES, destination)

    (result,) = committed_units(tmp_path, SNAPSHOT)
    opening_line = result.unit.text[: result.unit.text.index("**6.")].count("\n") + 1

    assert len(result.identified) == 3
    for run in result.identified:
        matched = build_label_index(run.entities).get(("0001", "binding rule 6"))
        assert matched is not None
        (target,) = [e for e in run.entities if e.canonical_id == matched]
        assert target.location is not None
        assert target.location.line == opening_line
        assert target.entity.span.startswith("Authorisation is never decided in the proxy.")


def test_the_same_rebuild_with_the_pre_check_skipped_resolves_nothing(tmp_path: Path) -> None:
    """The committed runs carry no entity label at all, so the pre-check is the whole fix."""
    destination = tmp_path / RUNS_DIR / BINDING_RULES
    destination.parent.mkdir(parents=True)
    shutil.copytree(ROOT / RUNS_DIR / BINDING_RULES, destination)
    (result,) = committed_units(tmp_path, SNAPSHOT)

    for artifact in result.artifacts:
        assert artifact.output is not None
        bare = assign_ids(locate_output(result.unit, artifact.output), "0001", "binding-rules")
        assert build_label_index(bare.entities).get(("0001", "binding rule 6")) is None
