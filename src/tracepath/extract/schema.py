"""The extraction schema: the only schema the model call and validation both use.

One set of frozen Pydantic models holds three closed sets of values (entity type,
relationship type, known trap flag). `extraction_json_schema()` generates the JSON
schema handed to the model, so no second schema exists to drift from this one.
"""

import re
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: A placeholder id the model writes for an item with no verbatim id of its own.
PLACEHOLDER_ID = re.compile(r"derived:\d+")

#: The only token shape that counts as a verbatim id (AC-3): `AC-10`, `AC-10b`.
VERBATIM_ID = re.compile(r"AC-\d+[a-z]?")


class EntityType(StrEnum):
    """The kinds of item an extraction can produce. `UNCLASSIFIED` is a real value."""

    FEATURE = "Feature"
    CONSTRAINT = "Constraint"
    ACCEPTANCE_CRITERION = "AcceptanceCriterion"
    CONSEQUENCE = "Consequence"
    FOLLOW_UP = "FollowUp"
    BUILD_STEP = "BuildStep"
    TEST_SCENARIO = "TestScenario"
    UNCLASSIFIED = "unclassified"


class RelationshipType(StrEnum):
    """The kinds of link between items. `UNCLASSIFIED` keeps the words that made it."""

    SUPERSEDED_BY = "superseded-by"
    CORRECTED_BY = "corrected-by"
    AMENDED_BY = "amended-by"
    BLOCKED_BY = "blocked-by"
    VERIFIES = "verifies"
    SATISFIES = "satisfies"
    UNCLASSIFIED = "unclassified"


class KnownTrapFlag(StrEnum):
    """The seven judgement calls worth flagging for review, carried over unchanged."""

    RATIONALE_BOUNDARY_CALL = "rationale_boundary_call"
    MULTI_CONDITION_SPLIT = "multi_condition_split"
    IMPLICIT_FEATURE_INFERRED = "implicit_feature_inferred"
    EMBEDDED_SECOND_CLAIM = "embedded_second_claim"
    RELATIONSHIP_TYPE_AMBIGUOUS = "relationship_type_ambiguous"
    ENTITY_TYPE_AMBIGUOUS = "entity_type_ambiguous"
    GRANULARITY_BOUNDARY_CALL = "granularity_boundary_call"


class IdSource(StrEnum):
    """Whether an id was written in the source text or has to be derived by code."""

    VERBATIM = "verbatim"
    DERIVED = "derived"


class FollowUpStatus(StrEnum):
    """A follow up item's checkbox state, read by the pre-check and never by the model."""

    OPEN = "open"
    DONE = "done"


class _Frozen(BaseModel):
    """Every model here is frozen, and rejects any field the schema does not name."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class LocalEndpoint(_Frozen):
    """A relationship endpoint naming an entity in this same output."""

    kind: Literal["local"] = "local"
    id: str = Field(description="The `id` of an entity in this output's own entity list.")


class ReferenceEndpoint(_Frozen):
    """A relationship endpoint naming something outside this output.

    `record` alone points at a whole document; `record` plus `id` points at one item
    inside it. Both may be null when the text names a target code cannot place, and
    then `mention` is all that survives into an `:Unresolved` node.
    """

    kind: Literal["reference"] = "reference"
    record: str | None = Field(
        default=None, description="The other record as the text names it, e.g. `0001` or `scope`."
    )
    id: str | None = Field(
        default=None, description="The item inside that record, e.g. `AC-8`. Null for the record."
    )
    mention: str = Field(description="The verbatim words that made the reference.")


Endpoint = Annotated[LocalEndpoint | ReferenceEndpoint, Field(discriminator="kind")]


class ExtractedEntity(_Frozen):
    """One item the model pulled out of a unit, before code assigns its canonical id."""

    id: str = Field(
        description="The verbatim `AC-N` token when the text carries one, else `derived:N`."
    )
    id_source: IdSource
    type: EntityType
    span: str = Field(description="The text of the item itself, with rationale clauses removed.")
    rejected_spans: tuple[str, ...] = Field(
        default=(), description="The rationale clauses removed from the span, kept verbatim."
    )
    known_trap_flags: tuple[KnownTrapFlag, ...] = ()
    unclassified_note: str | None = Field(
        default=None,
        description="Why the item fits no named type. Required when type is unclassified.",
    )
    label: str | None = Field(
        default=None,
        description="The author's own label for an unnumbered item, e.g. `key invariant 1`.",
    )

    @model_validator(mode="after")
    def _check_id_matches_its_source(self) -> Self:
        is_placeholder = PLACEHOLDER_ID.fullmatch(self.id) is not None
        if self.id_source is IdSource.DERIVED and not is_placeholder:
            raise ValueError(f"entity {self.id!r}: a derived id must be a `derived:N` placeholder")
        if self.id_source is IdSource.VERBATIM:
            if is_placeholder:
                raise ValueError(f"entity {self.id!r}: a verbatim id must not be a placeholder")
            if VERBATIM_ID.fullmatch(self.id) is None:
                raise ValueError(
                    f"entity {self.id!r}: the only verbatim id shape is `AC-N` or `AC-Nx`"
                )
        return self

    @model_validator(mode="after")
    def _check_unclassified_carries_its_note(self) -> Self:
        if self.type is EntityType.UNCLASSIFIED and not self.unclassified_note:
            raise ValueError(
                f"entity {self.id!r}: an unclassified entity needs an unclassified_note"
            )
        if self.type is not EntityType.UNCLASSIFIED and self.unclassified_note is not None:
            raise ValueError(
                f"entity {self.id!r}: unclassified_note belongs only to an unclassified entity"
            )
        if (
            KnownTrapFlag.ENTITY_TYPE_AMBIGUOUS in self.known_trap_flags
            and self.type is not EntityType.UNCLASSIFIED
        ):
            raise ValueError(
                f"entity {self.id!r}: entity_type_ambiguous is only ever set"
                " on an unclassified entity"
            )
        return self


class ExtractedRelationship(_Frozen):
    """One link the model read out of a unit, with the words that made it."""

    type: RelationshipType
    source: Endpoint
    target: Endpoint
    phrase: str | None = Field(
        default=None,
        description="The verbatim connecting text. Required when type is unclassified.",
    )
    date: str | None = Field(default=None, description="The date the text gives the link, if any.")
    known_trap_flags: tuple[KnownTrapFlag, ...] = ()

    @model_validator(mode="after")
    def _check_unclassified_keeps_its_phrase(self) -> Self:
        if self.type is RelationshipType.UNCLASSIFIED and not self.phrase:
            raise ValueError("an unclassified relationship must keep the phrase that made it")
        return self


class ExtractionOutput(_Frozen):
    """One model run over one unit: the items it found and the links between them."""

    entities: tuple[ExtractedEntity, ...] = ()
    relationships: tuple[ExtractedRelationship, ...] = ()

    @model_validator(mode="after")
    def _check_ids_are_unique(self) -> Self:
        seen = [entity.id for entity in self.entities]
        duplicates = sorted({entity_id for entity_id in seen if seen.count(entity_id) > 1})
        if duplicates:
            raise ValueError(f"two entities share an id: {', '.join(duplicates)}")
        return self

    @model_validator(mode="after")
    def _check_local_endpoints_exist(self) -> Self:
        """A JSON schema cannot say this, so it is the one check left to code."""
        known = {entity.id for entity in self.entities}
        for relationship in self.relationships:
            for endpoint in (relationship.source, relationship.target):
                if isinstance(endpoint, LocalEndpoint) and endpoint.id not in known:
                    raise ValueError(
                        f"relationship endpoint {endpoint.id!r} names no entity in this output"
                    )
        return self


def extraction_json_schema() -> dict[str, Any]:
    """The JSON schema handed to the model call, generated from the models above."""
    return ExtractionOutput.model_json_schema()
