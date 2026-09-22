"""The model call: one unit in, three validated outputs out (spec 0001's run policy).

The schema handed to the model is generated from the Pydantic models in `schema.py`,
so the call and the validation share one schema and no second one can drift from it.

Sampling parameters are deliberately absent. Spec 0001 asked for temperature left at
its default rather than forced to zero, because the run comparator's signal is the
variation between runs; on this model the sampling parameters are rejected outright,
so leaving them off is both what the spec asked for and the only thing that works.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import anthropic
from pydantic import ValidationError

from tracepath.config import AnthropicSettings
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit

log = logging.getLogger(__name__)

#: The version of the instructions below. Stored on every entity, so a later prompt
#: change can be told apart from a stable one when two runs disagree.
PROMPT_VERSION = "0002.1"

#: Room for the largest unit in the corpus and its extraction, with margin.
MAX_TOKENS = 16000

#: One retry on a failed or malformed run before the unit is a flagged failure.
RETRIES = 1

SYSTEM_PROMPT = """\
You extract decision records from a software project's own documentation.

You are given one unit: a section of a spec, the text above its first heading, or one \
feature row of the project's scope document. Return the items it states and the links \
between them, and nothing else.

Rules that matter more than completeness:

- Never invent an id. If the text gives an item a verbatim `AC-N` label, use exactly \
that token and set `id_source` to `verbatim`. Otherwise use a `derived:N` placeholder, \
numbered from 1 within your own output, and set `id_source` to `derived`. Never write a \
qualified id, a slug or a spec number as an id.
- `span` is the item's own claim, with rationale clauses removed. Put each removed \
clause in `rejected_spans`, verbatim. The reason an item exists is what a "why" \
question is answered with, so it is kept, not discarded.
- If an item fits none of the named types, type it `unclassified` and say why in \
`unclassified_note`. Do not force it into the nearest type.
- If a link fits none of the named types, type it `unclassified` and put the exact \
connecting words in `phrase`. Do not drop it.
- A link may point at something outside this unit. Use a `reference` endpoint carrying \
the record and, where the text names one, the item inside it, plus the verbatim words \
that made the reference. A unit may produce links and no items at all.
- Set a known trap flag whenever the call was genuinely a judgement call. A flagged \
item is reviewed, not discarded, so flagging costs nothing and hiding doubt costs a lot.
- Do not decide whether text is struck through, and do not read checkboxes. Those are \
read from the characters by code.
"""


class ExtractionFailed(Exception):
    """A unit could not be extracted after its retry."""


@dataclass(frozen=True)
class UnitRuns:
    """Every run of one unit, in order."""

    unit: Unit
    outputs: tuple[ExtractionOutput, ...]
    model: str
    prompt_version: str


def build_client(settings: AnthropicSettings) -> anthropic.Anthropic:
    """Open an Anthropic client from validated settings."""
    return anthropic.Anthropic(api_key=settings.api_key)


def user_prompt(unit: Unit) -> str:
    """The message one extraction call is made from."""
    return (
        f"Record: {unit.record_id}\n"
        f"File: {unit.path}\n"
        f"Section: {unit.section}\n"
        f"Unit kind: {unit.kind}\n\n"
        f"---\n{unit.text}\n---"
    )


def extract_once(
    client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit
) -> ExtractionOutput:
    """Make one extraction call and return its validated output.

    Raises:
        ExtractionFailed: the call failed, or its output did not satisfy the schema.
    """
    try:
        response = client.messages.parse(
            model=settings.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_format=ExtractionOutput,
        )
    except anthropic.APIError as exc:
        raise ExtractionFailed(f"{unit.record_id} {unit.section}: the call failed ({exc})") from exc
    parsed = response.parsed_output
    if parsed is None:
        raise ExtractionFailed(f"{unit.record_id} {unit.section}: the model returned no output")
    return parsed


def extract_unit(client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit) -> UnitRuns:
    """Run one unit the run policy's number of times, retrying a failed run once.

    Raises:
        ExtractionFailed: a run failed again after its retry.
    """
    outputs: list[ExtractionOutput] = []
    for run in range(settings.runs_per_unit):
        outputs.append(_run_with_retry(client, settings, unit, run))
    return UnitRuns(
        unit=unit,
        outputs=tuple(outputs),
        model=settings.model,
        prompt_version=PROMPT_VERSION,
    )


def _run_with_retry(
    client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit, run: int
) -> ExtractionOutput:
    last: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            return extract_once(client, settings, unit)
        except (ExtractionFailed, ValidationError) as exc:
            last = exc
            log.debug(
                "run %s of %s %s failed on attempt %s",
                run + 1,
                unit.record_id,
                unit.section,
                attempt + 1,
                exc_info=exc,
            )
    raise ExtractionFailed(
        f"{unit.record_id} {unit.section}: run {run + 1} failed after its retry ({last})"
    )


def extract_units(
    client: anthropic.Anthropic, settings: AnthropicSettings, units: Sequence[Unit]
) -> tuple[UnitRuns, ...]:
    """Run every unit, in order."""
    return tuple(extract_unit(client, settings, unit) for unit in units)
