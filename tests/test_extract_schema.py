import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tracepath.extract.schema import (
    EntityType,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionOutput,
    IdSource,
    KnownTrapFlag,
    LocalEndpoint,
    ReferenceEndpoint,
    RelationshipType,
    extraction_json_schema,
)

RUNS = Path(__file__).parent / "fixtures" / "runs"

AGREEING = ("run1", "run2", "run3")


def load(name: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((RUNS / f"{name}.json").read_text())
    return payload


# AC-12: the schema accepts the four valid fixture runs and rejects the invalid one.


@pytest.mark.parametrize("name", [*AGREEING, "run_split"])
def test_schema_accepts_every_valid_fixture_run(name: str) -> None:
    output = ExtractionOutput.model_validate(load(name))

    assert output.entities
    assert all(e.type is EntityType.ACCEPTANCE_CRITERION for e in output.entities)


def test_schema_rejects_the_run_with_an_invented_flag_name() -> None:
    with pytest.raises(ValidationError) as caught:
        ExtractionOutput.model_validate(load("run_bad"))

    assert "atomicity_boundary_call" in str(caught.value)


def test_fixture_runs_are_fresh_files_not_reachable_from_reference() -> None:
    for name in (*AGREEING, "run_split", "run_bad"):
        path = RUNS / f"{name}.json"
        assert path.is_file()
        assert not path.is_symlink()


# AC-1: three closed sets of values, and one generated schema.


def test_entity_type_rejects_a_value_outside_the_closed_set() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {"id": "derived:1", "id_source": "derived", "type": "Spec", "span": "x"}
        )


def test_relationship_type_rejects_a_value_outside_the_closed_set() -> None:
    with pytest.raises(ValidationError):
        ExtractedRelationship.model_validate(
            {
                "type": "supersedes",
                "source": {"kind": "local", "id": "derived:1"},
                "target": {"kind": "local", "id": "derived:2"},
            }
        )


def test_the_closed_sets_hold_exactly_what_the_spec_names() -> None:
    assert {t.value for t in EntityType} == {
        "Feature",
        "Constraint",
        "AcceptanceCriterion",
        "Consequence",
        "FollowUp",
        "BuildStep",
        "TestScenario",
        "unclassified",
    }
    assert {t.value for t in RelationshipType} == {
        "superseded-by",
        "corrected-by",
        "amended-by",
        "blocked-by",
        "verifies",
        "satisfies",
        "unclassified",
    }
    assert len(KnownTrapFlag) == 7


def test_the_generated_schema_names_the_two_top_level_lists() -> None:
    schema = extraction_json_schema()

    assert set(schema["properties"]) == {"entities", "relationships"}


def test_models_are_frozen() -> None:
    entity = ExtractedEntity.model_validate(load("run1")["entities"][0])

    with pytest.raises(ValidationError):
        entity.span = "changed"


def test_an_unnamed_field_is_rejected_rather_than_ignored() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {
                "id": "derived:1",
                "id_source": "derived",
                "type": "Constraint",
                "span": "x",
                "confidence": 0.9,
            }
        )


# AC-3: the model writes a `derived:N` placeholder or a verbatim `AC-N` token, nothing else.


@pytest.mark.parametrize("entity_id", ["AC-1", "AC-10", "AC-10b"])
def test_a_verbatim_id_may_be_an_ac_token_with_an_optional_letter(entity_id: str) -> None:
    entity = ExtractedEntity.model_validate(
        {"id": entity_id, "id_source": "verbatim", "type": "AcceptanceCriterion", "span": "x"}
    )

    assert entity.id_source is IdSource.VERBATIM


@pytest.mark.parametrize("entity_id", ["COPY-7", "0012#build-plan:2", "0012/AC-8", "AC-10bc"])
def test_no_other_token_shape_counts_as_a_verbatim_id(entity_id: str) -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {"id": entity_id, "id_source": "verbatim", "type": "AcceptanceCriterion", "span": "x"}
        )


def test_a_derived_entity_must_carry_a_placeholder_id() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {"id": "AC-1", "id_source": "derived", "type": "AcceptanceCriterion", "span": "x"}
        )


def test_a_verbatim_entity_must_not_carry_a_placeholder_id() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {"id": "derived:1", "id_source": "verbatim", "type": "AcceptanceCriterion", "span": "x"}
        )


# AC-10: the three kinds of doubt stay separate, and each keeps what it knows.


def test_an_unclassified_entity_must_say_why() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {"id": "derived:1", "id_source": "derived", "type": "unclassified", "span": "x"}
        )


def test_a_named_type_must_not_carry_an_unclassified_note() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {
                "id": "derived:1",
                "id_source": "derived",
                "type": "Constraint",
                "span": "x",
                "unclassified_note": "unsure",
            }
        )


def test_entity_type_ambiguous_is_only_ever_set_on_an_unclassified_entity() -> None:
    with pytest.raises(ValidationError):
        ExtractedEntity.model_validate(
            {
                "id": "derived:1",
                "id_source": "derived",
                "type": "Constraint",
                "span": "x",
                "known_trap_flags": ["entity_type_ambiguous"],
            }
        )


def test_an_unclassified_relationship_must_keep_the_phrase_that_made_it() -> None:
    with pytest.raises(ValidationError):
        ExtractionOutput.model_validate(
            {
                "entities": [
                    {"id": "derived:1", "id_source": "derived", "type": "Constraint", "span": "a"},
                    {"id": "derived:2", "id_source": "derived", "type": "Constraint", "span": "b"},
                ],
                "relationships": [
                    {
                        "type": "unclassified",
                        "source": {"kind": "local", "id": "derived:1"},
                        "target": {"kind": "local", "id": "derived:2"},
                    }
                ],
            }
        )


# AC-7: an endpoint is a local placeholder or a structured reference, and both validate.


def test_a_relationship_may_point_at_another_record() -> None:
    output = ExtractionOutput.model_validate(
        {
            "entities": [
                {"id": "AC-1", "id_source": "verbatim", "type": "AcceptanceCriterion", "span": "a"}
            ],
            "relationships": [
                {
                    "type": "blocked-by",
                    "source": {"kind": "local", "id": "AC-1"},
                    "target": {
                        "kind": "reference",
                        "record": "0001",
                        "id": "AC-8",
                        "mention": "spec 0001's AC-8",
                    },
                }
            ],
        }
    )

    link = output.relationships[0]
    assert isinstance(link.source, LocalEndpoint)
    assert isinstance(link.target, ReferenceEndpoint)
    assert link.target.mention == "spec 0001's AC-8"


def test_a_unit_may_produce_relationships_and_no_entities_at_all() -> None:
    output = ExtractionOutput.model_validate(
        {
            "entities": [],
            "relationships": [
                {
                    "type": "amended-by",
                    "source": {"kind": "reference", "record": "0008", "mention": "this spec"},
                    "target": {"kind": "reference", "record": "0014", "mention": "spec 0014"},
                }
            ],
        }
    )

    assert not output.entities
    assert len(output.relationships) == 1


def test_a_local_endpoint_naming_no_entity_in_the_output_is_rejected() -> None:
    with pytest.raises(ValidationError) as caught:
        ExtractionOutput.model_validate(
            {
                "entities": [
                    {
                        "id": "AC-1",
                        "id_source": "verbatim",
                        "type": "AcceptanceCriterion",
                        "span": "a",
                    }
                ],
                "relationships": [
                    {
                        "type": "satisfies",
                        "source": {"kind": "local", "id": "derived:9"},
                        "target": {"kind": "local", "id": "AC-1"},
                    }
                ],
            }
        )

    assert "derived:9" in str(caught.value)


def test_two_entities_may_not_share_a_placeholder_id() -> None:
    with pytest.raises(ValidationError):
        ExtractionOutput.model_validate(
            {
                "entities": [
                    {
                        "id": "derived:1",
                        "id_source": "derived",
                        "type": "Constraint",
                        "span": "a",
                    },
                    {
                        "id": "derived:1",
                        "id_source": "derived",
                        "type": "Constraint",
                        "span": "b",
                    },
                ],
                "relationships": [],
            }
        )


def test_one_verbatim_id_may_carry_both_a_struck_and_an_unstruck_version() -> None:
    """AC-5 needs this shape, so the schema must not reject it.

    Which of the two keeps the verbatim id is code's call, not the model's, and it is
    made in `assign_ids()` once the pre-check has said which one is struck.
    """
    output = ExtractionOutput.model_validate(
        {
            "entities": [
                {
                    "id": "AC-2",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "the old version, struck in the source",
                },
                {
                    "id": "AC-2",
                    "id_source": "verbatim",
                    "type": "AcceptanceCriterion",
                    "span": "the replacement that stands",
                },
            ],
            "relationships": [],
        }
    )

    assert len(output.entities) == 2
