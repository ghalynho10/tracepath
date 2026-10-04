"""The worked examples and the prompt they are assembled into (spec 0003, AC-6 to AC-11).

A worked example teaches by demonstration, so a stale one teaches a wrong shape without
anyone noticing. These pin down that every committed example still validates, that only
its Input and Output reach the model, and that the assembled prompt is the same bytes
every time, which is what the prompt cache needs to hit.

Nothing here calls the API.
"""

import json
from types import SimpleNamespace

import pytest

from tracepath.extract.client import (
    CACHE_TTL,
    EXAMPLE_NOTES,
    RULES,
    SYSTEM_PROMPT,
    _attempt_from_usage,
    system_blocks,
)
from tracepath.extract.examples import (
    EXAMPLES_DIR,
    ExampleError,
    WorkedExample,
    few_shot_block,
    parse_example,
    read_examples,
)
from tracepath.extract.precheck import is_struck, mark_struck
from tracepath.extract.schema import ExtractionOutput, IdSource, extraction_json_schema

EXAMPLE = """\
# Worked example: a tiny one

## Reasoning notes

- An authoring note the model must never see.

## Input

```text
Record: 0001
---
- **AC-1**: A claim.
---
```

## Output

```json
{"entities": [], "relationships": []}
```

## Rules this example demonstrates

- A rule.
"""


# AC-11: every committed worked example still validates against the extraction schema.


def test_every_committed_example_output_validates_against_the_extraction_schema() -> None:
    """Validated through `ExtractionOutput`, the model `extraction_json_schema()` is made from.

    The project carries no JSON schema validator, and the model is stricter than its
    generated schema anyway: it also enforces the checks a JSON schema cannot say, such
    as a local endpoint naming an entity that exists.
    """
    examples = read_examples(EXAMPLES_DIR)
    properties = set(extraction_json_schema()["properties"])

    assert len(examples) == 7
    for example in examples:
        payload = json.loads(example.output)
        assert set(payload) <= properties, example.name
        ExtractionOutput.model_validate(payload)


# AC-28: a struck old version and its unstruck replacement may legitimately share one
# verbatim id (`ids.py`, `_verbatim_keepers`); nothing else may.


def test_every_committed_example_holds_at_most_one_unstruck_entity_per_verbatim_id() -> None:
    for example in read_examples(EXAMPLES_DIR):
        payload = json.loads(example.output)
        struck_ranges = mark_struck(example.input)
        unstruck_ids: list[str] = []
        for entity in payload["entities"]:
            if entity["id_source"] != IdSource.VERBATIM:
                continue
            offset = example.input.find(entity["span"])
            struck = offset != -1 and is_struck(struck_ranges, offset)
            if not struck:
                unstruck_ids.append(entity["id"])
        duplicates = {i for i in unstruck_ids if unstruck_ids.count(i) > 1}
        assert not duplicates, f"{example.name}: {duplicates}"


def test_every_committed_example_input_is_a_unit_as_the_model_receives_it() -> None:
    for example in read_examples(EXAMPLES_DIR):
        lines = example.input.splitlines()
        assert lines[0].startswith("Record: "), example.name
        # The opening delimiter may carry a note (`--- (excerpt: ...)`); the closing one
        # is bare, exactly as `user_prompt()` writes it.
        assert any(line.startswith("---") for line in lines[1:-1]), example.name
        assert lines[-1] == "---", example.name


# AC-9: only Input and Output reach the model, in filename order.


def test_an_example_is_read_as_its_input_and_output_and_nothing_else() -> None:
    example = parse_example("tiny", EXAMPLE)

    assert example.input.startswith("Record: 0001")
    assert example.output == '{"entities": [], "relationships": []}'
    block = few_shot_block((example,), {})
    assert "authoring note" not in block
    assert "A rule." not in block


def test_an_example_missing_its_output_is_refused_by_name() -> None:
    with pytest.raises(ExampleError, match="tiny: no `## Output`"):
        parse_example("tiny", EXAMPLE.split("## Output")[0])


def test_an_example_whose_output_is_not_json_is_refused_by_name() -> None:
    with pytest.raises(ExampleError, match="tiny: the Output block is not valid JSON"):
        parse_example("tiny", EXAMPLE.replace('{"entities"', '{entities"'))


def test_a_note_for_an_example_that_does_not_exist_is_refused_not_dropped() -> None:
    example = WorkedExample(name="tiny", input="in", output="{}")

    with pytest.raises(ExampleError, match="nowhere"):
        few_shot_block((example,), {"nowhere": "a note"})


def test_the_examples_appear_in_the_prompt_in_filename_order() -> None:
    names = sorted(path.stem for path in EXAMPLES_DIR.glob("*.md"))

    positions = [SYSTEM_PROMPT.index(f'<example name="{name}">') for name in names]

    assert positions == sorted(positions)


def test_the_excerpt_note_sits_beside_its_own_example_only() -> None:
    (name,) = EXAMPLE_NOTES
    start = SYSTEM_PROMPT.index(f'<example name="{name}">')
    own = SYSTEM_PROMPT[start : SYSTEM_PROMPT.index("</example>", start)]

    assert SYSTEM_PROMPT.count("<note>") == 1
    assert "contiguous verbatim excerpt" in own


def test_no_reasoning_note_or_project_history_reaches_the_model() -> None:
    for leaked in ("Reasoning notes", "Validation caveat", "build plan task", "AC-11e"):
        assert leaked not in SYSTEM_PROMPT


def test_the_assembled_prompt_is_the_same_bytes_every_time() -> None:
    again = RULES + "\n" + few_shot_block(read_examples(EXAMPLES_DIR), EXAMPLE_NOTES) + "\n"

    assert again == SYSTEM_PROMPT


# AC-6 and AC-8: the two general rules the examples alone could not state.


def test_the_prompt_asks_for_an_entity_label_only_when_the_text_names_the_item() -> None:
    assert "Set an item's `label` only when the unit's own text gives that item a name" in RULES
    assert "regardless of any sample text shown anywhere in these instructions" in RULES


def test_the_prompt_says_a_reference_table_row_yields_nothing() -> None:
    assert "A row of a reference or lookup table" in RULES
    assert "Return no item and no link" in RULES


# AC-7: the schema's own sample label is a real one, not an invented `key invariant 1`.


def test_the_entity_label_sample_is_a_label_the_corpus_really_writes() -> None:
    schema = json.dumps(extraction_json_schema())

    assert "key invariant 1" not in schema
    assert "Happy path" in schema
    assert "binding rule 6" in schema


# AC-19: the system prompt carries a one hour cache breakpoint, and usage records it.


def test_the_system_prompt_is_sent_as_one_block_cached_for_an_hour() -> None:
    (block,) = system_blocks()

    assert block["text"] == SYSTEM_PROMPT
    assert block["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert CACHE_TTL == "1h"


def test_an_attempt_keeps_the_cache_counts_the_api_reported() -> None:
    usage = SimpleNamespace(
        input_tokens=8000,
        output_tokens=15000,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=30000,
    )

    attempt = _attempt_from_usage(2, usage)  # type: ignore[arg-type]

    assert attempt.cache_read_input_tokens == 30000
    assert attempt.cache_creation_input_tokens == 0
    assert (attempt.number, attempt.input_tokens, attempt.output_tokens) == (2, 8000, 15000)


def test_an_attempt_with_no_usage_reports_zero_rather_than_failing() -> None:
    attempt = _attempt_from_usage(1, None, error="the call failed")

    assert (attempt.input_tokens, attempt.cache_read_input_tokens) == (0, 0)
    assert attempt.error == "the call failed"


# AC-21 to AC-28: the prompt 0003.1 amendment. Each new rule reaches the model once, in
# the rules, and the three example changes it made still hold.


def example_output(name: str) -> dict[str, list[dict[str, object]]]:
    """One committed worked example's Output, parsed."""
    (example,) = [e for e in read_examples(EXAMPLES_DIR) if e.name == name]
    output: dict[str, list[dict[str, object]]] = json.loads(example.output)
    return output


def flags(item: dict[str, object]) -> list[object]:
    """An entity's or a link's trap flags, empty when it carries none."""
    found = item.get("known_trap_flags")
    return found if isinstance(found, list) else []


@pytest.mark.parametrize(
    ("criterion", "rule"),
    [
        ("AC-21", "does the old claim stop standing at all?"),
        ("AC-22", "repeated word for word before more than one item in the unit"),
        ("AC-23", "never from a sentence that only describes the connection"),
        ("AC-24", "or a deliberate hold with a stated condition"),
        ("AC-27", "A stage line that only reports a check (`Verify it`, `Test it`)"),
        ("AC-28", "An item that carries a verbatim `AC-N` id is never split"),
    ],
)
def test_each_0003_1_rule_reaches_the_model_exactly_once_and_from_the_rules(
    criterion: str, rule: str
) -> None:
    assert rule in RULES, criterion
    assert SYSTEM_PROMPT.count(rule) == 1, criterion


def test_the_struck_claim_rule_defers_the_link_type_to_the_links_rules() -> None:
    """covers: AC-21. The struck claim rule used to name `superseded-by` outright."""
    (bullet,) = [line for line in RULES.split("\n- ") if line.startswith("A struck claim")]

    assert "Links rules" in bullet
    for named in ("superseded-by", "corrected-by", "amended-by"):
        assert named not in bullet


def test_a_partly_standing_claim_is_amended_before_error_framing_is_ever_weighed() -> None:
    """covers: AC-21. The ordered test: does the old claim stand at all, then framing."""
    first = RULES.index("does the old claim stop standing at all?")
    then = RULES.index("Only when the old claim is fully retired")

    assert first < then
    assert "the change is `amended-by`, flagged `relationship_type_ambiguous`" in RULES


def test_the_build_plan_example_types_its_partial_supersession_as_amended_by() -> None:
    """covers: AC-21. Step 3's `ai_check` override narrows the old claim, not retires it."""
    links = example_output("0012-build-plan")["relationships"]
    (partial,) = [link for link in links if "Superseded for `ai_check`" in str(link["phrase"])]

    assert partial["type"] == "amended-by"
    assert "relationship_type_ambiguous" in flags(partial)


def test_the_scope_row_example_splits_done_when_into_its_three_conditions() -> None:
    """covers: AC-26. Split at the author's clause separators, each part flagged."""
    entities = example_output("feature-21-scope-row")["entities"]
    parts = [
        e
        for e in entities
        if e["type"] == "AcceptanceCriterion" and "multi_condition_split" in flags(e)
    ]

    assert len(parts) == 3
    assert str(parts[0]["span"]).startswith("**Done when:** both pages exist and are linked")
    assert "privacy notice names the real stored fields" in str(parts[1]["span"])
    assert "request deletion" in str(parts[2]["span"])


def test_the_scope_row_example_types_its_verify_line_unclassified_with_a_reason() -> None:
    """covers: AC-27."""
    entities = example_output("feature-21-scope-row")["entities"]
    (verify,) = [e for e in entities if str(e["span"]).startswith("Verify it:")]

    assert verify["type"] == "unclassified"
    assert verify["unclassified_note"]


def test_no_example_types_a_check_reporting_stage_line_as_a_build_step() -> None:
    """covers: AC-27, across every example, so a later example cannot teach the old cut."""
    for example in read_examples(EXAMPLES_DIR):
        for entity in json.loads(example.output)["entities"]:
            span = str(entity["span"]).lstrip("-[]x ")
            if span.startswith(("Verify it", "Test it")):
                assert entity["type"] != "BuildStep", example.name


#: Records the seventh example may not be drawn from (spec 0003, AC-25): groups A, B
#: and C, the re check's records, every record an earlier example draws from, and every
#: record an eval chain cites.
EXCLUDED_RECORDS = {
    "0021", "0013", "feature-9",
    "0014", "0015", "0018",
    "0006", "0008", "0012", "feature-21",
    "0001", "0002", "0003", "0007", "0009", "0011",
}  # fmt: skip


def test_the_seventh_example_comes_from_a_record_no_exclusion_covers() -> None:
    """covers: AC-25."""
    (example,) = [e for e in read_examples(EXAMPLES_DIR) if e.name == "0019-requirements"]
    record = example.input.split("\n", 1)[0].removeprefix("Record: ")

    assert record == "0019"
    assert record not in EXCLUDED_RECORDS


def test_the_seventh_example_links_a_pointer_between_its_own_criteria_unclassified() -> None:
    """covers: AC-25. No named type fits, so the link keeps the connecting words."""
    links = example_output("0019-requirements")["relationships"]

    def own_record(end: object) -> bool:
        return isinstance(end, dict) and (end["kind"] == "local" or end.get("record") == "0019")

    pointers = [
        link
        for link in links
        if link["type"] == "unclassified"
        and own_record(link["source"])
        and own_record(link["target"])
    ]

    assert pointers
    assert all(link["phrase"] for link in pointers)


def test_the_seventh_example_keeps_a_bundled_verbatim_criterion_whole_and_flagged() -> None:
    """covers: AC-28. Never split, flagged `multi_condition_split` instead."""
    entities = example_output("0019-requirements")["entities"]
    bundled = [
        e for e in entities if e["id_source"] == "verbatim" and "multi_condition_split" in flags(e)
    ]

    assert bundled
    for entity in bundled:
        assert sum(1 for e in entities if e["id"] == entity["id"]) == 1
