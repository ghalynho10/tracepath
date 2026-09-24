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
from tracepath.extract.schema import ExtractionOutput, extraction_json_schema

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

    assert len(examples) == 6
    for example in examples:
        payload = json.loads(example.output)
        assert set(payload) <= properties, example.name
        ExtractionOutput.model_validate(payload)


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
