"""The paid extraction run behind `tracepath extract` (spec 0004 AC-4 to AC-14).

Every attempt is checked before it is made and written the moment it settles:

* Before the first paid call, no artifact may sit where any run's first attempt would
  land (`preflight()`, AC-4). Before every retry, the same for that attempt (AC-5).
* Before every call, the running total plus one flat failure must stay within the
  ceiling (AC-9).
* Each attempt's artifact is written as it settles, before the next call (AC-12a).
* After any call but the command's first, a call that reported usage and read nothing
  from the cache stops the run (AC-11).
* A run that fails again after its one retry stops the command; its unit is recorded
  as it stands and never run again (AC-13, AC-48).

Each stop is a value the run returns, said plainly, never an error raised to halt it.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import anthropic

from tracepath.artifacts import (
    ArtifactCollisionError,
    build_artifact,
    ensure_attempt_unwritten,
    write_run,
)
from tracepath.config import AnthropicSettings
from tracepath.extract import client as extraction
from tracepath.extract.address import Target
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    RETRIES,
    Attempt,
    ExtractionFailed,
    output_format,
    system_blocks,
    user_prompt,
)
from tracepath.extract.cost import FLAT_FAILURE_USD, attempt_cost
from tracepath.extract.units import Unit

#: One extraction call for one unit and attempt number, failure returned as an attempt.
Call = Callable[[Unit, int], Attempt]


@dataclass(frozen=True)
class Written:
    """One attempt as it was paid for and written."""

    address: str
    run: int
    attempt: int
    path: Path
    cost_usd: float
    settled: bool
    null_usage: bool
    error: str | None


@dataclass(frozen=True)
class RunOutcome:
    """Everything one command spent and wrote, and the stop it ended on, if any."""

    written: tuple[Written, ...]
    total_usd: float
    stop: str | None


def calls_through(client: anthropic.Anthropic, settings: AnthropicSettings) -> Call:
    """The real call: `extract_once()` on the interactive streaming API (AC-49).

    A failed or dropped call comes back as its attempt, usage included, so it can be
    written and counted like any other.
    """

    def call(unit: Unit, number: int) -> Attempt:
        try:
            return extraction.extract_once(client, settings, unit, number)
        except ExtractionFailed as exc:
            if exc.attempts:
                return exc.attempts[-1]
            return Attempt(
                number=number,
                input_tokens=None,
                output_tokens=None,
                run_id=uuid.uuid4().hex,
                error=str(exc),
            )

    return call


def count_input(client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit) -> int:
    """A unit's whole input as the free token count endpoint counts it.

    The same system blocks, message and output schema `extract_once()` sends, so the
    count matches what a call would bill as input, cached and uncached together.
    """
    return client.messages.count_tokens(
        model=settings.model,
        system=system_blocks(),
        messages=[{"role": "user", "content": user_prompt(unit)}],
        output_config={"format": output_format()},
    ).input_tokens


def preflight(root: Path, targets: Sequence[Target], runs: int) -> None:
    """Check every run's first attempt of every unit before anything is paid (AC-4).

    Raises:
        ArtifactCollisionError: one artifact already sits where an attempt would land.
    """
    for target in targets:
        for run in range(1, runs + 1):
            ensure_attempt_unwritten(root, target.unit.record_id, target.section_slug, run, 1)


def _null_usage(attempt: Attempt) -> bool:
    return attempt.input_tokens is None or attempt.output_tokens is None


def _reported_usage(attempt: Attempt) -> bool:
    """Whether the API reported any usage for the call at all.

    A call refused before it reached the model reports zeros, and one dropped before
    `message_start` reports nulls. Neither says anything about the cache, so the no
    cache stop (AC-11) reads only calls that did report.
    """
    if attempt.input_tokens is None:
        return False
    return (
        attempt.input_tokens + attempt.cache_creation_input_tokens + attempt.cache_read_input_tokens
        > 0
    )


def run_metered(
    targets: Sequence[Target],
    call: Call,
    settings: AnthropicSettings,
    root: Path,
    commit: str,
    extracted_at: str,
    ceiling: float,
    say: Callable[[str], None],
) -> RunOutcome:
    """Extract every target in order, three runs each, until done or a stop is reached."""
    written: list[Written] = []
    total = 0.0
    calls = 0

    def outcome(stop: str | None) -> RunOutcome:
        return RunOutcome(written=tuple(written), total_usd=total, stop=stop)

    for target in targets:
        unit = target.unit
        for run in range(1, settings.runs_per_unit + 1):
            settled = False
            for number in range(1, RETRIES + 2):
                where = f"{target.address} run {run} attempt {number}"
                if number > 1:
                    # AC-5: before a retry is paid for, not after, when its artifact
                    # could no longer be written.
                    try:
                        ensure_attempt_unwritten(
                            root, unit.record_id, target.section_slug, run, number
                        )
                    except ArtifactCollisionError as exc:
                        return outcome(f"stopping here before {where}: {exc}")
                if total + FLAT_FAILURE_USD > ceiling:
                    return outcome(f"stopping here before {where}: ceiling")
                attempt = call(unit, number)
                artifact = build_artifact(
                    unit=unit,
                    section_slug=target.section_slug,
                    run=run,
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
                )
                path = write_run(root, artifact)
                cost = attempt_cost(attempt)
                total += cost
                calls += 1
                settled = attempt.output is not None
                written.append(
                    Written(
                        address=target.address,
                        run=run,
                        attempt=number,
                        path=path,
                        cost_usd=cost,
                        settled=settled,
                        null_usage=_null_usage(attempt),
                        error=attempt.error,
                    )
                )
                say(_attempt_line(where, attempt, cost, total, path, root))
                if calls > 1 and _reported_usage(attempt) and attempt.cache_read_input_tokens == 0:
                    return outcome(f"stopping: call {calls} read no cache")
                if settled:
                    break
            if not settled:
                return outcome(
                    f"stopping: {target.address} run {run} failed after its retry. The unit is "
                    "recorded as it stands and is not run again"
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
        state = f"failed ({attempt.error}), counted at the flat ${cost:.4f}"
    return f"{where}: {state}; running total ${total:.4f} → {shown}"


def summary_lines(result: RunOutcome) -> tuple[str, ...]:
    """The closing summary, naming every attempt with null usage (AC-14)."""
    settled = sum(1 for w in result.written if w.settled)
    lines = [
        f"{len(result.written)} calls, {settled} settled, "
        f"{len(result.written) - settled} failed or dropped. Spent ${result.total_usd:.4f} "
        "by the running total's rule."
    ]
    nulls = [w for w in result.written if w.null_usage]
    if nulls:
        lines.append("Attempts with null usage:")
        lines += [f"  {w.address} run {w.run} attempt {w.attempt}: {w.path.name}" for w in nulls]
    else:
        lines.append("Attempts with null usage: none.")
    return tuple(lines)
