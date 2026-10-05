"""The model call: one unit in, three validated outputs out (spec 0001's run policy).

The schema handed to the model is generated from the Pydantic models in `schema.py`,
so the call and the validation share one schema and no second one can drift from it.

Sampling parameters are deliberately absent. Spec 0001 asked for temperature left at
its default rather than forced to zero, because the run comparator's signal is the
variation between runs; on this model the sampling parameters are rejected outright,
so leaving them off is both what the spec asked for and the only thing that works.
"""

import functools
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast

import anthropic
import httpx2
from anthropic.types import (
    ContentBlock,
    JSONOutputFormatParam,
    Message,
    OutputConfigParam,
    TextBlockParam,
    Usage,
)
from pydantic import TypeAdapter, ValidationError

from tracepath.config import AnthropicSettings
from tracepath.extract.examples import EXAMPLES_DIR, few_shot_block, read_examples
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit

log = logging.getLogger(__name__)

Effort = Literal["low", "medium", "high", "xhigh", "max"]

#: The version of the instructions below. Stored on every entity, so a later prompt
#: change can be told apart from a stable one when two runs disagree. `0003.0` is the
#: first prompt with worked examples, a new numbering root tied to spec 0003. `0003.1`
#: covers the AC-16 findings: seven rule changes, two changed examples and one new
#: example (spec 0003, AC-21 to AC-29).
PROMPT_VERSION = "0003.1"

#: Room for the extraction and the thinking that precedes it. This model runs adaptive
#: thinking, and at 16000 a real `Consequences` section spent the whole budget reasoning
#: and emitted no JSON at all (`stop_reason: max_tokens`, one `thinking` block, nothing
#: else). The SDK wants streaming for a budget this size, so the call streams.
MAX_TOKENS = 64000

#: One retry on a failed or malformed run before the unit is a flagged failure.
RETRIES = 1

#: The one assembled rules list (spec 0003, AC-6, AC-8, AC-9). Every rule a worked
#: example demonstrates is stated here once, in general terms, rather than left in the
#: example file where the model never sees it, or copied into both where the two
#: copies could drift apart.
RULES = """\
You extract decision records from a software project's own documentation.

You are given one unit: a section of a spec, the text above its first heading, or one \
feature row of the project's scope document. Return the items it states and the links \
between them, and nothing else.

Rules that matter more than completeness:

Ids and spans
- Never invent an id. If the text gives an item a verbatim `AC-N` label, use exactly \
that token and set `id_source` to `verbatim`. Otherwise use a `derived:N` placeholder, \
numbered from 1 within your own output, and set `id_source` to `derived`. Never write a \
qualified id, a slug or a spec number as an id.
- `span` is the item's own claim, with rationale clauses removed. Put each removed \
clause in `rejected_spans`, verbatim. The reason an item exists is what a "why" \
question is answered with, so it is kept, not discarded.
- A clause goes to `rejected_spans` when it explains why the kept claim exists rather \
than stating a claim of its own, and the deletion test confirms it: delete the clause, \
and the rest still stands as a complete claim. A clause that reads like explanation \
but carries a testable fact of its own stays in the span.
- `span`, `rejected_spans`, `phrase` and `mention` keep the source's backticks, bold \
markers and enclosing punctuation (quotes, parentheses) exactly, and enclosing \
punctuation travels with whichever span holds what it encloses. They are citations \
checked against the source, not paraphrases. Two exceptions: `~~` strike markers never \
go into a span, and a markdown link `[text](url)` inside `phrase` or `mention` is \
reduced to its visible text.
- Where the source writes a bold sub-label inline with its claim \
(`**Observability**: No span.`), the span starts at the sub-label, since the claim is \
unreadable without it. Where a sub-label heads a list, no item in the list repeats it.

Typing items
- Type an item by what it claims, not by where it sits. One unit can hold a \
capability, its acceptance clause, standing rules, an accepted tradeoff and build \
steps side by side.
- If an item fits none of the named types, type it `unclassified` and say why in \
`unclassified_note`. Do not force it into the nearest type.
- A convention stated in prose (what a tag means, where a kind of test lives) is a \
`Constraint`, not commentary.
- A claim that something is unaffected or untouched is an item, and produces no link. \
A link records a relation that exists; asserting the absence of one must not \
manufacture it.
- A stage line that only reports a check (`Verify it`, `Test it`) is not a `BuildStep`. \
It is typed `unclassified`, with `unclassified_note` saying it only reports a check \
rather than delivering one.

Where one item ends
- A numbered list's own numbering is the item boundary. A numbered step stays one item \
however much it bundles, flagged `multi_condition_split` rather than split, so the \
links written on the step stay attached to it.
- A bullet or a sub-label headed block that carries no verbatim id, and that bundles \
several independently statable claims, is split at its own clause boundaries. Every \
part from that split carries `multi_condition_split`, so a reviewer can see they were \
one block. An item that carries a verbatim `AC-N` id is never split, however many \
conditions it bundles; it carries `multi_condition_split` only when it genuinely \
bundles more than one condition.
- A row of a reference or lookup table, keyed by its first cell, is not itself a \
claim: it answers none of the type questions on its own. Return no item and no link \
from it.
- A struck claim and the replacement written beside it are two items, linked per the \
Links rules below, never one span covering both.
- Build a second item for an old version only when the old text is quoted. When the \
old version is only described, nothing is built from the paraphrase, and the \
correction stays inside the current item's span.
- When a follow up records that an earlier concern was resolved ("Resolved ..."), the \
concern and its resolution are two items of the same type, linked `unclassified` with \
the verbatim "Resolved ..." words as `phrase` and the date the text gives. They are \
never merged into one span, and never left unconnected.

Labels
- Set an item's `label` only when the unit's own text gives that item a name standing \
in place of a number: a bold lead in naming that one item, or a quoted or otherwise \
clearly delimited name used as the item's own heading. Copy it verbatim. An unnamed, \
unnumbered item (a plain bullet, an entry in a list of invariants) gets no label, \
regardless of any sample text shown anywhere in these instructions, the field \
descriptions included. Never invent a label to fill the field.
- A bold sub-label that heads a block of several items (`**Done when:**`, \
`**Key invariants**`) is never a `label`: it names a block, not an item. It stays in \
the span wherever the source writes it inline.
- A `label` goes only on an item that is the whole of what the author named. If a \
named item is split, the label goes on neither part.
- A lead-in name, taken up to its own delimiter, that is repeated word for word before \
more than one item in the unit is not a `label` on any of them: it names a kind of \
item, not one item. A name used exactly once stays a label, even where every item in \
the list also carries a separate, shared tag; the shared tag and the item's own \
once-used name are different things, and only the repeated one is barred. Names are \
compared whole, so `Gate` and `Gate failure` are different names, neither one a prefix \
of the other.

Links
- A link starts from the item that is actually connected, never from a sentence that \
only describes the connection (a provenance note such as "That last clause is spec \
0001's third runner constraint...").
- `blocked-by` covers any item waiting on something else to be done first, whether the \
wait is technical or a deliberate hold with a stated condition ("held back until the \
real data version shipped").
- Directions are fixed. `superseded-by` and `corrected-by` run old to new, \
`amended-by` runs amended to amending, `blocked-by` runs blocked to blocker, \
`verifies` runs TestScenario to AcceptanceCriterion, and `satisfies` runs BuildStep to \
AcceptanceCriterion. A dependency the text says runs both ways takes `unclassified` \
with its verbatim phrase, not `blocked-by`.
- `superseded-by` versus `corrected-by` turns on error framing, not on recency. An old \
claim overtaken by events is superseded; one the text says rested on something wrong \
is corrected.
- History link types follow what actually changed, not the author's own stamp word, \
tested in this order: does the old claim stop standing at all? If part of it still \
stands, the change is `amended-by`, flagged `relationship_type_ambiguous`, whether the \
scope narrowed, widened, or gained an addition, whatever the author's own stamp says. \
Only when the old claim is fully retired does the rule above (error framing) decide \
`superseded-by` from `corrected-by`.
- If a link fits none of the named types, type it `unclassified` and put the exact \
connecting words in `phrase`. Do not drop it.
- A link may point at something outside this unit. Use a `reference` endpoint carrying \
the record and, where the text names a specific item inside it, either the item's \
verbatim `AC-N` id or, for a named but unnumbered item such as "binding rule 6", its \
`label`: the author's own words for the item, copied exactly and nothing more \
(`binding rule 6`, not `Spec 0001's binding rule 6`). Set at most one of `id` and \
`label`. Leave both unset when the text names only the record, or a record's own \
stated position rather than an item inside it. The full words that made the reference \
go in `mention`. This works the same inside the unit's own record as across records.
- A `local` endpoint names an item in your own output and nothing else. An item of \
this same document that you did not return is a `reference`. A unit may produce links \
and no items at all.
- Build a link only when its two endpoints are distinguishable. Two mentions of the \
same id do not make an old and new pair; skip it rather than link an item to itself.
- An inferred link, such as a letter suffixed criterion (`AC-10b`) read as amending \
its numeric parent (`AC-10`), is still built, and flagged \
`relationship_type_ambiguous` every time.
- A stated range with both endpoints named (`**AC-1** through **AC-8**`) is enumerated \
into one link per id when the record's numbering has no gaps or letter suffixes, each \
link keeping the whole range as its `phrase`. A stated total ("all 23 criteria") is \
never enumerated.
- A pointer written as part of an item's own statement (`satisfies **AC-3**`) stays in \
the span and also produces a link. A note added later about the item's status \
(`_Superseded ... on <date>_`) goes to `rejected_spans` and also produces a link.
- A `TestScenario` citing more than one criterion produces one `verifies` link per \
criterion, each keeping the full citation as its `phrase`.
- A pointer to something that is not a spec, the scope document or a scope feature row \
(a cited review file, a rationale note) produces no link at all.
- In a scope feature row, the pointer line to its spec (`_spec [NNNN](...)_`) is read \
by code: it produces no item and no link. Criterion ids cited in the row belong to the \
spec that pointer line names. A mention of another row the way prose names it \
(`feature 7`) is still emitted as a reference with its verbatim mention, even when \
nothing will match it yet.
- `phrase` is optional on a named type. When no single verbatim stretch of text names \
the link, leave it null rather than paraphrase.

Flags
- Set a known trap flag whenever the call was genuinely a judgement call. A flagged \
item is reviewed, not discarded, so flagging costs nothing and hiding doubt costs a lot.
- A flag fires per genuinely close call, not per signal word: \
`rationale_boundary_call` when the keep or reject line was not obvious, \
`multi_condition_split` when merging or splitting was plausible either way, \
`embedded_second_claim` when a clause looked rejectable but held its own testable \
fact. An obvious "because" clause with an obvious remainder gets no flag.
- Two of those flags are not interchangeable. Set `entity_type_ambiguous` only on an \
item you typed `unclassified`, never on one you gave a named type. When you did pick a \
named type but the choice between named types was close, the flag is \
`granularity_boundary_call`.
- When a real judgement call matches no flag in the closed set, make the call and set \
no flag. Never invent one.

Read by code, not by you
- Do not decide whether text is struck through, and do not read checkboxes. Those are \
read from the characters by code.

Worked examples follow. Each shows one unit as you receive it, then the output that \
is correct for it. They demonstrate the rules above; none of them is a unit you are \
asked to extract.
"""

#: A note shown beside one example's input, where the input alone would teach the
#: wrong thing (spec 0003, AC-9). Without it, an excerpt of a section can teach a run
#: to extract only part of a whole section.
EXAMPLE_NOTES = {
    "0006-feature-design": (
        "This input is a contiguous verbatim excerpt of a longer `## Feature design` "
        "section, from `**Key invariants**` to the end of the section. Everything inside "
        "the excerpt is extracted, and nothing inside it is skipped. A run over a whole "
        "section extracts every part of it that qualifies, not only the part shown here."
    ),
}


@functools.cache
def system_prompt() -> str:
    """The whole system prompt: the rules, then the worked examples, in filename order.

    Built on first use, not at import, so a command that makes no extraction call never
    reads `examples/`. Cached, so it is byte identical on every call in a process, which
    is what lets the cache prefix hit (AC-19).

    Raises:
        ExampleError: an example is missing, unreadable or malformed.
    """
    return RULES + "\n" + few_shot_block(read_examples(EXAMPLES_DIR), EXAMPLE_NOTES) + "\n"


#: How long the cached system prompt lives. One call's output can outlast the 5 minute
#: default, and a cache lifetime runs from the start of the request that last read it
#: (spec 0003, AC-19).
CACHE_TTL: Literal["5m", "1h"] = "1h"


@dataclass(frozen=True)
class Attempt:
    """One call to the model: what it cost, and what it produced.

    `output` is null when the call raised, and the usage is recorded all the same.
    That is the whole point of the record: spec 0001's artifact storage row exists
    because a failure that hides its own cost made the first 21 call run permanently
    unmeasured. Usage counts **this attempt alone**, never a running total.
    `input_tokens` is the uncached input only; the cached system prompt is counted
    apart, as written to the cache or read from it, because each bills at its own rate.
    Either token count is null when the connection dropped before the API reported it:
    unmeasured, not zero.

    `run_id` is a fresh identifier minted for this one call, distinct from `number`
    (the retry accounting within a run) and from `attempt` (`pipeline.py`'s own count):
    two attempts can share a `number`/`attempt` position across different runs, but
    never a `run_id` (spec 0001's storage row, amended 2026-09-28). `raw_response` and
    `stop_reason` carry the API's own text and stop reason alongside the already
    parsed `output`, so a malformed or truncated response is diagnosable from the
    artifact itself; both are null when the call raised before any response came back.
    """

    number: int
    input_tokens: int | None
    output_tokens: int | None
    run_id: str
    output: ExtractionOutput | None = None
    error: str | None = None
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    raw_response: str | None = None
    stop_reason: str | None = None


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
    def input_tokens(self) -> int | None:
        """What the settling attempt read, alone."""
        return self.attempts[-1].input_tokens if self.attempts else 0

    @property
    def output_tokens(self) -> int | None:
        """What the settling attempt wrote, alone."""
        return self.attempts[-1].output_tokens if self.attempts else 0

    @property
    def wasted_input_tokens(self) -> int:
        """What every attempt before the settling one read, where it was measured."""
        return sum(attempt.input_tokens or 0 for attempt in self.attempts[:-1])

    @property
    def wasted_output_tokens(self) -> int:
        """What every attempt before the settling one wrote, where it was measured."""
        return sum(attempt.output_tokens or 0 for attempt in self.attempts[:-1])


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


def system_blocks() -> list[TextBlockParam]:
    """The system prompt as one block, cached for `CACHE_TTL` (spec 0003, AC-19).

    Raises:
        ExampleError: the worked examples cannot be read into the prompt.
    """
    return [
        {
            "type": "text",
            "text": system_prompt(),
            "cache_control": {"type": "ephemeral", "ttl": CACHE_TTL},
        }
    ]


def _raw_text(content: Sequence[ContentBlock]) -> str | None:
    """The response's own text, exactly as the API wrote it.

    For diagnosing a malformed or truncated call from the artifact alone (spec 0001,
    amended 2026-09-28). `None` when no text block came back at all.
    """
    blocks = [block.text for block in content if block.type == "text"]
    return "\n".join(blocks) if blocks else None


def _attempt_from_usage(
    number: int,
    usage: Usage | None,
    output: ExtractionOutput | None = None,
    error: str | None = None,
    raw_response: str | None = None,
    stop_reason: str | None = None,
) -> Attempt:
    """One attempt, with every part of the usage the API reported for it."""
    run_id = uuid.uuid4().hex
    if usage is None:
        return Attempt(
            number=number,
            input_tokens=0,
            output_tokens=0,
            run_id=run_id,
            output=output,
            error=error,
            raw_response=raw_response,
            stop_reason=stop_reason,
        )
    return Attempt(
        number=number,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        run_id=run_id,
        output=output,
        error=error,
        cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
        cache_read_input_tokens=usage.cache_read_input_tokens or 0,
        raw_response=raw_response,
        stop_reason=stop_reason,
    )


def _dropped_attempt(number: int, message: str, snapshot: Message | None) -> Attempt:
    """A call whose connection dropped, with only the usage that had arrived.

    `message_start` reports the input and cache counts, so they are real once it has
    arrived. The output count is final only once `message_delta` has, which also sets
    the stop reason; before that it is `message_start`'s placeholder, so it stays null.
    With no snapshot at all, nothing was reported and both counts are null.
    """
    if snapshot is None:
        return Attempt(
            number=number,
            input_tokens=None,
            output_tokens=None,
            run_id=uuid.uuid4().hex,
            error=message,
        )
    usage = snapshot.usage
    return Attempt(
        number=number,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens if snapshot.stop_reason is not None else None,
        run_id=uuid.uuid4().hex,
        error=message,
        cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
        cache_read_input_tokens=usage.cache_read_input_tokens or 0,
        raw_response=_raw_text(snapshot.content),
        stop_reason=snapshot.stop_reason,
    )


def output_format() -> JSONOutputFormatParam:
    """The output schema exactly as the SDK builds it from `output_format=ExtractionOutput`.

    Sent through `output_config` instead, so the request is unchanged but the stream no
    longer validates the output itself. The SDK validates at the text block's end,
    before the final usage event, so a schema failure there lost the attempt's real
    output count and stop reason. `extract_once()` validates once the stream is done.
    """
    schema = anthropic.transform_schema(TypeAdapter(ExtractionOutput).json_schema())
    return {"type": "json_schema", "schema": schema}


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
        ExtractionFailed: the call failed, its connection dropped mid stream, or its
            output did not satisfy the schema. The exception carries this attempt,
            usage included, so the caller can still write its artifact.
    """
    # The schema is the one the SDK builds from `output_format` (`output_format()`): the
    # models generate a discriminated union, which Pydantic renders as `oneOf`, and the
    # API rejects that keyword unless the SDK's transform normalises it. `effort` rides
    # alongside in `output_config`, because thinking is billed as output and so effort is
    # the cost dial this pipeline actually turns.
    config: OutputConfigParam = {"format": output_format()}
    if settings.effort is not None:
        config["effort"] = cast("Effort", settings.effort)
    try:
        with client.messages.stream(
            model=settings.model,
            max_tokens=MAX_TOKENS,
            system=system_blocks(),
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_config=config,
        ) as stream:
            try:
                response = stream.get_final_message()
            except httpx2.TransportError as exc:
                # The SDK wraps a transport error as `APIConnectionError` only while it
                # sends the request; one that breaks the response body arrives raw.
                # Recorded as a failed attempt, so the run's one retry covers it.
                try:
                    snapshot: Message | None = stream.current_message_snapshot
                except AssertionError:  # the SDK holds none before `message_start`
                    snapshot = None
                message = (
                    f"{unit.record_id} {unit.section}: the connection dropped mid stream ({exc})"
                )
                raise ExtractionFailed(
                    message, (_dropped_attempt(number, message, snapshot),)
                ) from exc
    except anthropic.APIError as exc:
        # Nothing came back, so the API reported no usage to record. Zero here means
        # "nothing was billed that we were told about", and the error says why.
        message = f"{unit.record_id} {unit.section}: the call failed ({exc})"
        raise ExtractionFailed(
            message,
            (
                Attempt(
                    number=number,
                    input_tokens=0,
                    output_tokens=0,
                    run_id=uuid.uuid4().hex,
                    error=message,
                ),
            ),
        ) from exc

    # Validated only now, with the whole response in hand, so a failure still records
    # the usage and stop reason of the full call.
    text = next((block.text for block in response.content if block.type == "text"), None)
    try:
        parsed = None if text is None else ExtractionOutput.model_validate_json(text)
    except ValidationError as exc:
        message = f"{unit.record_id} {unit.section}: the output did not satisfy the schema ({exc})"
        raise ExtractionFailed(
            message,
            (
                _attempt_from_usage(
                    number,
                    response.usage,
                    error=message,
                    raw_response=_raw_text(response.content),
                    stop_reason=response.stop_reason,
                ),
            ),
        ) from exc
    if parsed is None:
        message = (
            f"{unit.record_id} {unit.section}: the model returned no parsed output "
            f"(stop_reason={response.stop_reason}, "
            f"output_tokens={response.usage.output_tokens} of max {MAX_TOKENS})"
        )
        raise ExtractionFailed(
            message,
            (
                _attempt_from_usage(
                    number,
                    response.usage,
                    error=message,
                    raw_response=_raw_text(response.content),
                    stop_reason=response.stop_reason,
                ),
            ),
        )
    return _attempt_from_usage(
        number,
        response.usage,
        output=parsed,
        raw_response=_raw_text(response.content),
        stop_reason=response.stop_reason,
    )


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
