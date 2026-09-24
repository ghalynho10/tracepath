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
from typing import Literal, cast

import anthropic
from anthropic.types import OutputConfigParam
from pydantic import ValidationError

from tracepath.config import AnthropicSettings
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit

log = logging.getLogger(__name__)

Effort = Literal["low", "medium", "high", "xhigh", "max"]

#: The version of the instructions below. Stored on every entity, so a later prompt
#: change can be told apart from a stable one when two runs disagree.
PROMPT_VERSION = "0002.3"

#: Room for the extraction and the thinking that precedes it. This model runs adaptive
#: thinking, and at 16000 a real `Consequences` section spent the whole budget reasoning
#: and emitted no JSON at all (`stop_reason: max_tokens`, one `thinking` block, nothing
#: else). The SDK wants streaming for a budget this size, so the call streams.
MAX_TOKENS = 64000

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
the record and, where the text names a specific item inside it, either the item's \
verbatim `AC-N` id, or, for a named but unnumbered item such as "binding rule 6", the \
same `label` you would give that item as an entity. Set at most one of `id` and \
`label`; leave both unset when the text names only the record. Always keep the \
verbatim words that made the reference. A unit may produce links and no items at all.
- Set a known trap flag whenever the call was genuinely a judgement call. A flagged \
item is reviewed, not discarded, so flagging costs nothing and hiding doubt costs a lot.
- Two of those flags are not interchangeable. Set `entity_type_ambiguous` only on an \
item you typed `unclassified`, never on one you gave a named type. When you did pick a \
named type but the choice between named types was close, the flag is \
`granularity_boundary_call`.
- Do not decide whether text is struck through, and do not read checkboxes. Those are \
read from the characters by code.
"""


@dataclass(frozen=True)
class Attempt:
    """One call to the model: what it cost, and what it produced.

    `output` is null when the call raised, and the usage is recorded all the same.
    That is the whole point of the record: spec 0001's artifact storage row exists
    because a failure that hides its own cost made the first 21 call run permanently
    unmeasured. Usage counts **this attempt alone**, never a running total.
    """

    number: int
    input_tokens: int
    output_tokens: int
    output: ExtractionOutput | None = None
    error: str | None = None


class ExtractionFailed(Exception):
    """A call, or a whole run, could not be extracted.

    Carries every attempt it made, each with what that attempt cost, so a run that
    produced no data still reports its spend instead of quietly leaving it out of the
    total, and so the caller can still write an artifact for each one.
    """

    def __init__(self, message: str, attempts: tuple[Attempt, ...] = ()) -> None:
        """Record the failure and every attempt behind it."""
        super().__init__(message)
        self.attempts = attempts


@dataclass(frozen=True)
class RunOutcome:
    """Every attempt one run made, in order, the last being the one that settled it.

    The token properties read the settling attempt alone, and `wasted_*` reads the
    attempts before it, so the cost of a retry stays visible beside the cost of the
    call that replaced it rather than folded into it.
    """

    attempts: tuple[Attempt, ...]

    @property
    def output(self) -> ExtractionOutput:
        """The validated output of the attempt that succeeded.

        Raises:
            ExtractionFailed: this outcome holds no successful attempt.
        """
        settled = self.attempts[-1].output if self.attempts else None
        if settled is None:
            raise ExtractionFailed("this run settled on no output")
        return settled

    @property
    def input_tokens(self) -> int:
        """What the settling attempt read, alone."""
        return self.attempts[-1].input_tokens if self.attempts else 0

    @property
    def output_tokens(self) -> int:
        """What the settling attempt wrote, alone."""
        return self.attempts[-1].output_tokens if self.attempts else 0

    @property
    def wasted_input_tokens(self) -> int:
        """What every attempt before the settling one read."""
        return sum(attempt.input_tokens for attempt in self.attempts[:-1])

    @property
    def wasted_output_tokens(self) -> int:
        """What every attempt before the settling one wrote."""
        return sum(attempt.output_tokens for attempt in self.attempts[:-1])


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
    client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit, number: int = 1
) -> Attempt:
    """Make one extraction call and return it as an attempt carrying its token usage.

    Raises:
        ExtractionFailed: the call failed, or its output did not satisfy the schema.
            The exception carries this attempt, usage included, so the caller can
            still write its artifact.
    """
    # The schema travels as `output_format`, not as a raw `output_config.format.schema`.
    # The models generate a discriminated union, which Pydantic renders as `oneOf`, and
    # the API rejects that keyword outright; the SDK's own path normalises it. `effort`
    # rides alongside in `output_config`, because thinking is billed as output and so
    # effort is the cost dial this pipeline actually turns.
    config: OutputConfigParam = {}
    if settings.effort is not None:
        config["effort"] = cast("Effort", settings.effort)
    try:
        with client.messages.stream(
            model=settings.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_format=ExtractionOutput,
            output_config=config,
        ) as stream:
            try:
                response = stream.get_final_message()
            except ValidationError as exc:
                # The parse raises before the message is returned, so the cost would
                # vanish with it. The snapshot still holds what the call really used.
                snapshot = stream.current_message_snapshot
                message = (
                    f"{unit.record_id} {unit.section}: the output did not satisfy "
                    f"the schema ({exc})"
                )
                raise ExtractionFailed(
                    message,
                    (
                        Attempt(
                            number=number,
                            input_tokens=snapshot.usage.input_tokens if snapshot else 0,
                            output_tokens=snapshot.usage.output_tokens if snapshot else 0,
                            error=message,
                        ),
                    ),
                ) from exc
    except anthropic.APIError as exc:
        # Nothing came back, so the API reported no usage to record. Zero here means
        # "nothing was billed that we were told about", and the error says why.
        message = f"{unit.record_id} {unit.section}: the call failed ({exc})"
        raise ExtractionFailed(
            message, (Attempt(number=number, input_tokens=0, output_tokens=0, error=message),)
        ) from exc

    used_in = response.usage.input_tokens
    used_out = response.usage.output_tokens
    parsed = response.parsed_output
    if parsed is None:
        message = (
            f"{unit.record_id} {unit.section}: the model returned no parsed output "
            f"(stop_reason={response.stop_reason}, "
            f"output_tokens={used_out} of max {MAX_TOKENS})"
        )
        raise ExtractionFailed(
            message,
            (Attempt(number=number, input_tokens=used_in, output_tokens=used_out, error=message),),
        )
    return Attempt(number=number, input_tokens=used_in, output_tokens=used_out, output=parsed)


def extract_unit(client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit) -> UnitRuns:
    """Run one unit the run policy's number of times, retrying a failed run once.

    Raises:
        ExtractionFailed: a run failed again after its retry.
    """
    outputs: list[ExtractionOutput] = []
    for run in range(settings.runs_per_unit):
        outputs.append(run_with_retry(client, settings, unit, run).output)
    return UnitRuns(
        unit=unit,
        outputs=tuple(outputs),
        model=settings.model,
        prompt_version=PROMPT_VERSION,
    )


def run_with_retry(
    client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit, run: int
) -> RunOutcome:
    """Make one run, retrying once on a failed or malformed call (spec 0001's policy).

    Every attempt is kept, the failed ones included, so each can be written as its own
    artifact and the cost of a retry never disappears into the call that replaced it.

    Raises:
        ExtractionFailed: the run failed again after its retry. The exception carries
            every attempt, so the caller can still write their artifacts.
    """
    last: Exception | None = None
    attempts: list[Attempt] = []
    for number in range(1, RETRIES + 2):
        try:
            attempts.append(extract_once(client, settings, unit, number))
            return RunOutcome(attempts=tuple(attempts))
        except ExtractionFailed as exc:
            last = exc
            attempts.extend(exc.attempts)
            log.debug(
                "run %s of %s %s failed on attempt %s",
                run + 1,
                unit.record_id,
                unit.section,
                number,
                exc_info=exc,
            )
    raise ExtractionFailed(
        f"{unit.record_id} {unit.section}: run {run + 1} failed after its retry ({last})",
        tuple(attempts),
    )


def extract_units(
    client: anthropic.Anthropic, settings: AnthropicSettings, units: Sequence[Unit]
) -> tuple[UnitRuns, ...]:
    """Run every unit, in order."""
    return tuple(extract_unit(client, settings, unit) for unit in units)
