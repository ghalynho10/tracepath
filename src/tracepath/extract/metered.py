"""The paid extraction run behind `tracepath extract` (spec 0004 AC-4 to AC-14, AC-55 to AC-70).

Every attempt is checked before it is made and written the moment it settles:

* Before the first paid call, no artifact may sit where any run's first attempt would
  land (`preflight()`, AC-4), or, for a resume, where any owed run's next attempt would
  land (`resume_preflight()`, AC-61). Before every attempt, the same for that attempt
  (AC-5, AC-61b).
* Before every call, the running total plus the unit's per call bound must stay within
  the ceiling (AC-9, AC-55), so spend never passes it.
* Each attempt's artifact is written as it settles, before the next call (AC-12a).
* After the command's first call, a call that reported usage and read nothing from the
  cache stops the run, unless no earlier call of the command reported usage (AC-11).
* Only a model failure counts toward a run's single retry (AC-67, AC-68). Two model
  failures block the run and stop the command (AC-13). One command makes at most two
  attempts per run; a run still owed after them stops the command (AC-69), and
  `--resume` picks it up later (AC-56).

Each stop is a value the run returns, said plainly, never an error raised to halt it.

`ask_metered()` guards the one call `tracepath ask` makes (spec 0009 AC-21 to AC-27):
its bound is checked against the ceiling before it, and its record written as it
settles. The `ask` package never imports `anthropic`, so the client, the token count
and the call for an ask live here too.
"""

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

import anthropic
import httpx2
from anthropic.types import JSONOutputFormatParam, Message, OutputConfigParam
from pydantic import TypeAdapter, ValidationError

from tracepath.artifacts import (
    RUNS_DIR,
    ArtifactCollisionError,
    attempt_paths,
    build_artifact,
    ensure_attempt_unwritten,
    read_run,
    run_path,
    write_run,
)
from tracepath.ask import answer as asking
from tracepath.ask.answer import ASK_MAX_TOKENS, Answer, CheckedClaim, check_claims, pack_message
from tracepath.ask.record import (
    AskRecord,
    EvalSource,
    Usage,
    ensure_record_unwritten,
    write_record,
)
from tracepath.ask.retrieve import Pack
from tracepath.config import AnthropicSettings
from tracepath.extract import client as extraction
from tracepath.extract.address import Target
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    RETRIES,
    Attempt,
    Effort,
    ExtractionFailed,
    FailureKind,
    output_format,
    system_blocks,
    user_prompt,
)
from tracepath.extract.cost import attempt_cost, recorded_cost, tokens_cost
from tracepath.extract.units import Unit

#: One extraction call for one unit and attempt number, failure returned as an attempt.
Call = Callable[[Unit, int], Attempt]

#: The most attempts one command makes for one run, of any kind (AC-69): a call and
#: spec 0001's single retry.
ATTEMPTS_PER_COMMAND = RETRIES + 1

#: Model failures that block a run for good (AC-13): the call and its one retry.
BLOCKING_MODEL_FAILURES = RETRIES + 1

_SETTLED = re.compile(r"run-(\d+)\.json")
_FAILED = re.compile(r"failed-run-(\d+)-attempt-(\d+)\.json")


@dataclass(frozen=True)
class Written:
    """One attempt as it was paid for and written."""

    address: str
    run: int
    attempt: int
    path: Path
    cost_usd: float
    recorded_usd: float
    settled: bool
    null_usage: bool
    error: str | None
    failure_kind: FailureKind | None


@dataclass(frozen=True)
class RunOutcome:
    """Everything one command spent and wrote, and the stop it ended on, if any."""

    written: tuple[Written, ...]
    total_usd: float
    stop: str | None

    @property
    def recorded_usd(self) -> float:
        """What the attempts' recorded usage costs, beside the guard's total (AC-14b)."""
        return sum(w.recorded_usd for w in self.written)


@dataclass(frozen=True)
class RunPlan:
    """One run this command owes.

    `first_attempt` is where its attempt numbers start, and `model_failures` the ones it
    already holds from an earlier command.
    """

    run: int
    first_attempt: int = 1
    model_failures: int = 0


@dataclass(frozen=True)
class Plan:
    """What one command will do for one unit, and the per call bound it is held to."""

    target: Target
    runs: tuple[RunPlan, ...]
    bound: float


class CountUnreadable(Exception):
    """The token count endpoint answered with a body that could not be read."""


class ResumeRefused(Exception):
    """A unit `--resume` cannot plan or must not touch (AC-58b, AC-59, AC-60)."""


def fresh_runs(runs: int) -> tuple[RunPlan, ...]:
    """Every run of a unit not yet started, each from attempt 1."""
    return tuple(RunPlan(run=n) for n in range(1, runs + 1))


def calls_through(client: anthropic.Anthropic, settings: AnthropicSettings) -> Call:
    """The real call: `extract_once()` on the interactive streaming API (AC-49).

    A failed or dropped call comes back as its attempt, usage and failure kind
    included, so it can be written and counted like any other.
    """

    def call(unit: Unit, number: int) -> Attempt:
        try:
            return extraction.extract_once(client, settings, unit, number)
        except ExtractionFailed as exc:
            if exc.attempts:
                return exc.attempts[-1]
            # No attempt was recorded, so the response never completed (AC-67).
            return Attempt(
                number=number,
                input_tokens=None,
                output_tokens=None,
                run_id=uuid.uuid4().hex,
                error=str(exc),
                failure_kind=FailureKind.TRANSPORT,
            )

    return call


def count_input(client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit) -> int:
    """A unit's whole input as the free token count endpoint counts it.

    The same system blocks, message and output schema `extract_once()` sends, so the
    count matches what a call would bill as input, cached and uncached together.

    Raises:
        CountUnreadable: the endpoint answered with a body the SDK could not parse,
            which it raises as a `ValueError` (a decode or validation error), not as an
            `anthropic.APIError`.
    """
    try:
        return client.messages.count_tokens(
            model=settings.model,
            system=system_blocks(),
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_config={"format": output_format()},
        ).input_tokens
    except ValueError as exc:
        raise CountUnreadable(
            f"its answer for {unit.record_id} {unit.section} could not be read ({exc!r})"
        ) from exc


def first_collision(root: Path, target: Target, runs: int) -> Path | None:
    """The first artifact sitting where one of a unit's runs would make attempt 1."""
    for run in range(1, runs + 1):
        for path in attempt_paths(root, target.unit.record_id, target.section_slug, run, 1):
            if path.exists():
                return path
    return None


def preflight(root: Path, targets: Sequence[Target], runs: int) -> None:
    """Check every run's first attempt of every unit before anything is paid (AC-4).

    Raises:
        ArtifactCollisionError: one artifact already sits where an attempt would land.
    """
    for target in targets:
        path = first_collision(root, target, runs)
        if path is not None:
            raise ArtifactCollisionError(f"an artifact already exists at {path}")


def resume_runs(root: Path, target: Target, runs: int) -> tuple[RunPlan, ...]:
    """The owed runs of a unit cut short, read from its artifacts (AC-56 to AC-60).

    A run is settled when `run-N.json` exists, whatever failed files sit beside it;
    blocked when it holds two model failures; otherwise owed, its next attempt numbered
    one above its highest. A run with no artifact at all is owed from attempt 1.

    Raises:
        ResumeRefused: the unit has no artifact (AC-60), breaks the naming pattern
            (AC-58b), holds a blocked run, or owes nothing (AC-59).
    """
    address = target.address
    directory = root / RUNS_DIR / target.unit.record_id / target.section_slug
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not files:
        raise ResumeRefused(f"{address} has no artifact: a plain `extract` starts it")

    settled: set[int] = set()
    failed: dict[int, list[tuple[int, Path]]] = {}
    for path in files:
        if (match := _SETTLED.fullmatch(path.name)) is not None:
            run = int(match.group(1))
            if not 1 <= run <= runs:
                raise ResumeRefused(f"{address} cannot be planned: {path} is outside {runs} runs")
            settled.add(run)
        elif (match := _FAILED.fullmatch(path.name)) is not None:
            run, attempt = int(match.group(1)), int(match.group(2))
            if not 1 <= run <= runs:
                raise ResumeRefused(f"{address} cannot be planned: {path} is outside {runs} runs")
            failed.setdefault(run, []).append((attempt, path))
        else:
            raise ResumeRefused(f"{address} cannot be planned: {path} is not a run artifact")

    owed: list[RunPlan] = []
    for run in range(1, runs + 1):
        attempts = sorted(failed.get(run, []))
        for expected, (attempt, path) in enumerate(attempts, start=1):
            if attempt != expected:
                raise ResumeRefused(
                    f"{address} cannot be planned: {path} has no attempt {expected} before it"
                )
        if run in settled:
            continue
        model_failures = sum(
            1 for _, path in attempts if read_run(path).failure_kind is FailureKind.MODEL
        )
        if model_failures >= BLOCKING_MODEL_FAILURES:
            raise ResumeRefused(
                f"{address} is blocked: run {run} holds {model_failures} model failures "
                "and is not run again"
            )
        owed.append(
            RunPlan(run=run, first_attempt=len(attempts) + 1, model_failures=model_failures)
        )
    if not owed:
        raise ResumeRefused(f"{address} owes nothing: all {runs} runs are settled")
    return tuple(owed)


def provenance_mismatch(
    root: Path, target: Target, settings: AnthropicSettings, commit: str
) -> str | None:
    """How a unit's settled runs differ from what a resume would write, if they do (AC-60b).

    Runs compared across a prompt, model, corpus or effort change say nothing about
    stability, so a resume that mixed them would be refused at load anyway, after spend.
    """
    directory = root / RUNS_DIR / target.unit.record_id / target.section_slug
    current = {
        "prompt_version": PROMPT_VERSION,
        "model": settings.model,
        "commit": commit,
        "effort": settings.effort or "default",
    }
    for path in sorted(directory.glob("run-*.json")):
        artifact = read_run(path)
        found = {
            "prompt_version": artifact.prompt_version,
            "model": artifact.model,
            "commit": artifact.commit,
            "effort": artifact.effort,
        }
        differ = [
            f"{key} {found[key]} (now {current[key]})"
            for key in current
            if found[key] != current[key]
        ]
        if differ:
            return f"{target.address}: {path.name} was written with " + ", ".join(differ)
    return None


def resume_preflight(root: Path, plans: Sequence[Plan]) -> None:
    """Check every owed run's next attempt before anything is paid (AC-61).

    Raises:
        ArtifactCollisionError: one artifact already sits where an attempt would land.
    """
    for plan in plans:
        for run in plan.runs:
            target = plan.target
            ensure_attempt_unwritten(
                root, target.unit.record_id, target.section_slug, run.run, run.first_attempt
            )


def _null_usage(attempt: Attempt) -> bool:
    return attempt.input_tokens is None or attempt.output_tokens is None


def _reported_usage(attempt: Attempt) -> bool:
    """Whether the API reported any usage for the call at all.

    A call refused before it reached the model reports zeros, and one dropped before
    `message_start` reports nulls. Neither says anything about the cache.
    """
    if attempt.input_tokens is None:
        return False
    return (
        attempt.input_tokens + attempt.cache_creation_input_tokens + attempt.cache_read_input_tokens
        > 0
    )


def _is_model_failure(attempt: Attempt) -> bool:
    """A failed attempt with no recorded kind counts as a model failure, the safe side."""
    return attempt.failure_kind is not FailureKind.TRANSPORT


def run_metered(
    plans: Sequence[Plan],
    call: Call,
    settings: AnthropicSettings,
    root: Path,
    commit: str,
    extracted_at: str,
    ceiling: float,
    say: Callable[[str], None],
) -> RunOutcome:
    """Make every planned attempt in order, until done or a stop is reached."""
    written: list[Written] = []
    total = 0.0
    calls = 0
    reported_before = False

    def outcome(stop: str | None) -> RunOutcome:
        return RunOutcome(written=tuple(written), total_usd=total, stop=stop)

    for plan in plans:
        target, unit = plan.target, plan.target.unit
        for owed in plan.runs:
            model_failures = owed.model_failures
            settled = False
            last = owed.first_attempt + ATTEMPTS_PER_COMMAND
            for number in range(owed.first_attempt, last):
                where = f"{target.address} run {owed.run} attempt {number}"
                # AC-5, AC-61b: before an attempt is paid for, not after, when its
                # artifact could no longer be written.
                try:
                    ensure_attempt_unwritten(
                        root, unit.record_id, target.section_slug, owed.run, number
                    )
                except ArtifactCollisionError as exc:
                    return outcome(f"stopping here before {where}: {exc}")
                if total + plan.bound > ceiling:
                    return outcome(f"stopping here before {where}: ceiling")
                attempt = call(unit, number)
                artifact = build_artifact(
                    unit=unit,
                    section_slug=target.section_slug,
                    run=owed.run,
                    attempt=attempt.number,
                    output=attempt.output,
                    model=settings.model,
                    prompt_version=PROMPT_VERSION,
                    commit=commit,
                    extracted_at=extracted_at,
                    max_output_tokens=MAX_TOKENS,
                    effort=settings.effort or "default",
                    input_tokens=attempt.input_tokens,
                    output_tokens=attempt.output_tokens,
                    run_id=attempt.run_id,
                    raw_response=attempt.raw_response,
                    stop_reason=attempt.stop_reason,
                    error=attempt.error,
                    cache_creation_input_tokens=attempt.cache_creation_input_tokens,
                    cache_read_input_tokens=attempt.cache_read_input_tokens,
                    failure_kind=attempt.failure_kind,
                )
                path = run_path(root, artifact)
                try:
                    write_run(root, artifact)
                except (OSError, ArtifactCollisionError) as exc:
                    lost: Exception | None = exc
                else:
                    lost = None
                # Priced at the model its artifact names (spec 0007 AC-5d).
                cost = attempt_cost(attempt, plan.bound, artifact.model)
                total += cost
                calls += 1
                settled = attempt.output is not None
                written.append(
                    Written(
                        address=target.address,
                        run=owed.run,
                        attempt=number,
                        path=path,
                        cost_usd=cost,
                        recorded_usd=recorded_cost(attempt, artifact.model),
                        settled=settled,
                        null_usage=_null_usage(attempt),
                        error=attempt.error,
                        failure_kind=None if settled else artifact.failure_kind,
                    )
                )
                say(_attempt_line(where, attempt, cost, total, path, root))
                if lost is not None:
                    # Paid for, so counted above; its record exists only in this message.
                    return outcome(
                        f"stopping: {where} was paid for, but its artifact could not be "
                        f"written to {path} ({lost}). Its usage: "
                        f"{attempt.input_tokens} in, {attempt.output_tokens} out, cache write "
                        f"{attempt.cache_creation_input_tokens}, read "
                        f"{attempt.cache_read_input_tokens}"
                    )
                reported = _reported_usage(attempt)
                # AC-11: a call reading no cache is a fault only once an earlier call of
                # this command could have written it.
                if reported_before and reported and attempt.cache_read_input_tokens == 0:
                    return outcome(f"stopping: call {calls} read no cache")
                reported_before = reported_before or reported
                if settled:
                    break
                if _is_model_failure(attempt):
                    model_failures += 1
                if model_failures >= BLOCKING_MODEL_FAILURES:
                    break
            if settled:
                continue
            if model_failures >= BLOCKING_MODEL_FAILURES:
                return outcome(
                    f"stopping: {target.address} run {owed.run} failed after its retry "
                    f"({model_failures} model failures). The unit is recorded as it stands "
                    "and is not run again"
                )
            return outcome(
                f"stopping: {target.address} run {owed.run} is not settled after "
                f"{ATTEMPTS_PER_COMMAND} attempts in this command, with {model_failures} "
                "model failures. The run is owed: resume the unit with `extract --resume`"
            )
    return outcome(None)


def _attempt_line(
    where: str, attempt: Attempt, cost: float, total: float, path: Path, root: Path
) -> str:
    """One line per attempt, as it settles: what it was, what it cost, where it went."""
    shown = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    if attempt.output is not None:
        state = (
            f"settled, {attempt.input_tokens or 0:,} in, {attempt.output_tokens or 0:,} out, "
            f"cache write {attempt.cache_creation_input_tokens:,}, "
            f"read {attempt.cache_read_input_tokens:,}, ${cost:.4f}"
        )
    else:
        kind = attempt.failure_kind or FailureKind.MODEL
        state = f"failed, {kind} ({attempt.error}), counted at its bound ${cost:.4f}"
    return f"{where}: {state}; running total ${total:.4f} → {shown}"


def summary_lines(result: RunOutcome) -> tuple[str, ...]:
    """The closing summary: both totals (AC-14b), and every null usage attempt (AC-14)."""
    settled = sum(1 for w in result.written if w.settled)
    lines = [
        f"{len(result.written)} calls, {settled} settled, "
        f"{len(result.written) - settled} failed or dropped. Spent ${result.total_usd:.4f} "
        "by the running total's rule (a failed attempt at its per call bound), "
        f"${result.recorded_usd:.4f} by the usage the artifacts recorded."
    ]
    nulls = [w for w in result.written if w.null_usage]
    if nulls:
        lines.append("Attempts with null usage:")
        lines += [f"  {w.address} run {w.run} attempt {w.attempt}: {w.path.name}" for w in nulls]
    else:
        lines.append("Attempts with null usage: none.")
    return tuple(lines)


# The one call `tracepath ask` makes (spec 0009).


@dataclass(frozen=True)
class AskAttempt:
    """One ask call: its usage, its reply, and its answer when the reply validated.

    `answer` is null when the call failed (AC-24); the usage is kept all the same, null
    meaning unmeasured.
    """

    input_tokens: int | None
    output_tokens: int | None
    answer: Answer | None = None
    raw_response: str | None = None
    stop_reason: str | None = None
    error: str | None = None
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


#: One ask call over one pack, failure returned as an attempt.
AskCall = Callable[[Pack], AskAttempt]


@dataclass(frozen=True)
class AskOutcome:
    """What one ask spent, what it answered, and where its record went.

    `stop` is set when the ceiling stopped it before the call, and nothing else is.
    `lost` says why a paid call's record could not be written (AC-27c).
    """

    attempt: AskAttempt | None
    checked: tuple[CheckedClaim, ...]
    cost_usd: float
    recorded_usd: float
    path: Path | None
    lost: str | None
    stop: str | None

    @property
    def settled(self) -> bool:
        """Whether the call returned an answer that validated."""
        return self.attempt is not None and self.attempt.answer is not None


def ask_output_format() -> JSONOutputFormatParam:
    """The `Answer` schema exactly as the SDK builds it for structured output (AC-15)."""
    schema = anthropic.transform_schema(TypeAdapter(Answer).json_schema())
    return {"type": "json_schema", "schema": schema}


def count_ask_input(client: anthropic.Anthropic, settings: AnthropicSettings, pack: Pack) -> int:
    """An ask call's whole input as the free token count endpoint counts it (AC-23).

    The same system prompt, message and output schema the call sends.

    Raises:
        CountUnreadable: the endpoint answered with a body the SDK could not parse.
    """
    try:
        return client.messages.count_tokens(
            model=settings.model,
            system=asking.system_prompt(),
            messages=[{"role": "user", "content": pack_message(pack)}],
            output_config={"format": ask_output_format()},
        ).input_tokens
    except ValueError as exc:
        raise CountUnreadable(f"its answer for the ask call could not be read ({exc!r})") from exc


def _ask_text(message: Message) -> str | None:
    blocks = [block.text for block in message.content if block.type == "text"]
    return "\n".join(blocks) if blocks else None


def _ask_failed(error: str, snapshot: Message | None) -> AskAttempt:
    """A failed ask call, with whatever usage had arrived."""
    if snapshot is None:
        return AskAttempt(input_tokens=None, output_tokens=None, error=error)
    usage = snapshot.usage
    return AskAttempt(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens if snapshot.stop_reason is not None else None,
        raw_response=_ask_text(snapshot),
        stop_reason=snapshot.stop_reason,
        error=error,
        cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
        cache_read_input_tokens=usage.cache_read_input_tokens or 0,
    )


def ask_calls_through(client: anthropic.Anthropic, settings: AnthropicSettings) -> AskCall:
    """The real ask call: one streamed request, no cache, no retry (AC-24, AC-26).

    A transport or API error, a stop on `max_tokens` or a refusal, and a reply that does
    not validate as `Answer` each come back as a failed attempt, usage included.
    """

    def call(pack: Pack) -> AskAttempt:
        config: OutputConfigParam = {"format": ask_output_format()}
        if settings.effort is not None:
            config["effort"] = cast("Effort", settings.effort)
        try:
            with client.messages.stream(
                model=settings.model,
                max_tokens=ASK_MAX_TOKENS,
                system=asking.system_prompt(),
                messages=[{"role": "user", "content": pack_message(pack)}],
                output_config=config,
            ) as stream:
                try:
                    response = stream.get_final_message()
                except (httpx2.TransportError, anthropic.APIError) as exc:
                    try:
                        snapshot: Message | None = stream.current_message_snapshot
                    except AssertionError:  # the SDK holds none before `message_start`
                        snapshot = None
                    return _ask_failed(f"the call failed mid stream ({exc})", snapshot)
        except anthropic.APIError as exc:
            return _ask_failed(f"the call failed ({exc})", None)

        if response.stop_reason in ("max_tokens", "refusal"):
            return _ask_failed(f"the call stopped on {response.stop_reason}", response)
        text = _ask_text(response)
        try:
            answer = None if text is None else Answer.model_validate_json(text)
        except ValidationError as exc:
            return _ask_failed(f"the reply did not validate as an Answer ({exc})", response)
        if answer is None:
            return _ask_failed("the reply held no text", response)
        return AskAttempt(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            answer=answer,
            raw_response=text,
            stop_reason=response.stop_reason,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens or 0,
            cache_read_input_tokens=response.usage.cache_read_input_tokens or 0,
        )

    return call


def ask_metered(
    pack: Pack,
    call: AskCall,
    settings: AnthropicSettings,
    *,
    root: Path,
    name: str,
    asked_at: datetime,
    commit: str,
    counted: int,
    bound: float,
    ceiling: float,
    source: EvalSource | None = None,
) -> AskOutcome:
    """Make one ask call if its bound fits the ceiling, and write its record as it settles.

    A failed call counts at its bound (AC-24); a settled one at its recorded usage.

    Raises:
        ArtifactCollisionError: a record already sits where this one would land,
            checked before the call is paid for.
    """
    if bound > ceiling:
        return AskOutcome(None, (), 0.0, 0.0, None, None, "stopping here before the call: ceiling")
    ensure_record_unwritten(root, name)
    attempt = call(pack)
    checked = check_claims(attempt.answer, pack) if attempt.answer is not None else ()
    recorded = tokens_cost(
        settings.model,
        attempt.input_tokens or 0,
        attempt.output_tokens or 0,
        attempt.cache_creation_input_tokens,
        attempt.cache_read_input_tokens,
    )
    cost = recorded if attempt.answer is not None else bound
    record = AskRecord(
        asked_at=asked_at.isoformat(timespec="seconds"),
        question=pack.question,
        pack=pack,
        called=True,
        counted_input_tokens=counted,
        bound_usd=bound,
        ceiling_usd=ceiling,
        model=settings.model,
        effort=settings.effort or "default",
        prompt_version=asking.PROMPT_VERSION,
        corpus_commit=commit,
        settled=attempt.answer is not None,
        answer=attempt.answer,
        checked=checked,
        raw_response=attempt.raw_response,
        stop_reason=attempt.stop_reason,
        error=attempt.error,
        usage=Usage(
            input_tokens=attempt.input_tokens,
            output_tokens=attempt.output_tokens,
            cache_creation_input_tokens=attempt.cache_creation_input_tokens,
            cache_read_input_tokens=attempt.cache_read_input_tokens,
        ),
        cost_usd=cost,
        recorded_usd=recorded,
        source=source,
    )
    try:
        path: Path | None = write_record(root, name, record)
    except (OSError, ArtifactCollisionError) as exc:
        return AskOutcome(attempt, checked, cost, recorded, None, str(exc), None)
    return AskOutcome(attempt, checked, cost, recorded, path, None, None)


def _tokens(count: int | None) -> str:
    return "unmeasured" if count is None else f"{count:,}"


def ask_cost_line(outcome: AskOutcome, ceiling: float) -> str:
    """The one cost line `ask` prints (AC-25): calls, tokens, both costs, the ceiling."""
    attempt = outcome.attempt
    calls = 0 if attempt is None else 1
    tokens_in = _tokens(attempt.input_tokens) if attempt else "0"
    tokens_out = _tokens(attempt.output_tokens) if attempt else "0"
    return (
        f"Cost: {calls} call{'' if calls == 1 else 's'}, {tokens_in} in, {tokens_out} out, "
        f"${outcome.recorded_usd:.4f} by recorded usage, ${outcome.cost_usd:.4f} by the "
        f"guard's rule, ceiling ${ceiling:.2f}."
    )
