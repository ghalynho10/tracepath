"""Run experiment 0008, the type coverage rerun: 8 units, 3 calls each, under `0003.1`.

Spec 0003, AC-18, build plan step 31. The eight units are experiment 0001's seven plus
`0006 ## Feature design`. Each unit's current runs move to
`artifacts/superseded/<run date>-prompt-<their version>/` before its first call, with a
note naming this experiment. The run date is the day this script runs, not a constant.

Safeguards carried over from experiment 0006 (`run_recheck.py`), and why:

* **A failed attempt counts at a flat figure, never its recorded tokens.** A failed
  attempt's recorded usage can undercount badly (experiment 0006 saw 2 output tokens
  recorded for a near complete response), so the running total counts each failed or
  crashed attempt at `FAILED_ATTEMPT_USD`, or its recorded cost if that is higher.
* **A dropped connection still writes a failed attempt.** `client.extract_once()`
  catches only a failure to open the stream; a connection that drops mid stream
  escapes it and its paid call goes unrecorded (experiment 0006's `0015` crash). This
  script's own `call_once()` catches transport errors at both points.
* **Every attempt is written the moment it settles**, so nothing paid for exists only
  in memory if the process dies.

Stop points, each a plain stop with its reason printed, never a crash:

* Before a unit starts: if the running total plus that unit's wider figure would pass
  `CEILING_USD`.
* Before any call: if the running total plus one heaviest call would pass the ceiling.
* After the second call: if it read nothing from the cache (AC-19).
* A run that fails again after its retry: the run stops there.

Run from the repository root:
    uv run python <this file> <expected prompt version>
"""

import json
import shutil
import sys
import uuid
from collections import Counter
from datetime import date
from pathlib import Path
from typing import cast

import anthropic
import httpx2
from anthropic.types import OutputConfigParam
from pydantic import ValidationError

from tracepath.artifacts import (
    RUNS_DIR,
    ArtifactCollisionError,
    RunArtifact,
    build_artifact,
    now_utc,
    read_run,
    write_run,
)
from tracepath.config import AnthropicSettings, load_anthropic_settings
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    RETRIES,
    Attempt,
    Effort,
    ExtractionFailed,
    _attempt_from_usage,
    _raw_text,
    system_blocks,
    user_prompt,
)
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import IdentifiedOutput, assign_ids, label_binding_rules, locate_output
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit
from tracepath.pipeline import UnitResult

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "0005-held-out-prompt-examples"))
import run_units
from run_units import describe, target

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
COMMIT = "2e40bcf"

#: The engineer's ceiling for this run (2026-10-04): the estimate's $12.04 wider total,
#: with `0006 ## Feature design` and the `feature-21` row raised to the heaviest
#: measured call, 39,234 output tokens.
CEILING_USD = 13.32

#: The heaviest measured `0003.x` call (experiment 0005, `0021` run 2), and the units
#: the engineer raised to it.
HEAVIEST_OUTPUT = 39_234
RAISED_TO_HEAVIEST = (
    "0006 Feature design",
    "feature-21 21. Terms & privacy notices · done · Alpha",
)

#: One heaviest call that reads the cache: 39,234 output tokens, the largest uncached
#: input among the eight units (`0006`, 5,276), and one 57,494 token cache read.
#: Every failed or crashed attempt counts at this, or its recorded cost if higher.
FAILED_ATTEMPT_USD = round((HEAVIEST_OUTPUT * 10.0 + 5_276 * 2.0 + 57_494 * 0.2) / 1e6, 4)

#: The eight units, in run order (spec 0003, AC-18). The first writes the cache.
UNITS = [
    "0012:Requirements",
    "0012:Consequences",
    "0012:Follow-up",
    "0012:Build plan",
    "feature-21:21. Terms & privacy notices · done · Alpha",
    "0008:Preamble",
    "0021:Requirements",
    "0006:Feature design",
]


class Stop(Exception):
    """A stop point was reached; the run ends here by design, not by failure."""


def run_date() -> str:
    """The day the run happens, which names the superseded folder."""
    return date.today().isoformat()


def budgets() -> dict[str, tuple[float, float]]:
    """Each unit's central and wider figure, from the committed estimate.

    The two units the engineer raised get their wider figure recomputed at the
    heaviest measured call for all four priced calls.
    """
    estimate = json.loads((HERE / "data" / "cost-estimate.json").read_text())
    figures: dict[str, tuple[float, float]] = {}
    for row in estimate["units"]:
        wider = float(row["wider_usd"])
        if row["unit"] in RAISED_TO_HEAVIEST:
            extra = (HEAVIEST_OUTPUT - int(row["wider"])) * int(row["calls_priced"])
            wider += extra * run_units.OUTPUT_RATE / 1e6
        figures[str(row["unit"])] = (float(row["central_usd"]), round(wider, 4))
    return figures


def move_superseded(root: Path, record: str, slug: str, day: str) -> list[Path]:
    """Move one unit's current runs aside, filed under the prompt that made them."""
    source = root / RUNS_DIR / record / slug
    moved: list[Path] = []
    for path in sorted(source.glob("*.json")):
        version = read_run(path).prompt_version
        destination = root / "artifacts" / "superseded" / f"{day}-prompt-{version}" / record / slug
        destination.mkdir(parents=True, exist_ok=True)
        target_path = destination / path.name
        if target_path.exists():
            raise ArtifactCollisionError(f"a superseded artifact already exists at {target_path}")
        moved.append(Path(shutil.move(path, target_path)))
        note = destination / "NOTE.md"
        if not note.exists():
            note.write_text(
                f"Prompt `{version}` runs of `{record}` / `{slug}`, superseded {day} by a "
                f"prompt `{PROMPT_VERSION}` run of experiment 0008, the type coverage rerun "
                "(spec 0003, AC-18).\n"
            )
    return moved


def failed(number: int, message: str, snapshot: object | None) -> ExtractionFailed:
    """A failed attempt carrying whatever usage and content arrived before the failure."""
    usage = getattr(snapshot, "usage", None)
    content = getattr(snapshot, "content", None)
    attempt = _attempt_from_usage(
        number,
        usage,
        error=message,
        raw_response=_raw_text(content) if content else None,
        stop_reason=getattr(snapshot, "stop_reason", None),
    )
    return ExtractionFailed(message, (attempt,))


def call_once(
    client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit, number: int
) -> Attempt:
    """One `0003.1` call, as `client.extract_once()` makes it, transport errors caught.

    Raises:
        ExtractionFailed: the call failed, dropped, or did not satisfy the schema. It
            carries the attempt, with whatever usage arrived, so it can be written.
    """
    config: OutputConfigParam = {}
    if settings.effort is not None:
        config["effort"] = cast("Effort", settings.effort)
    name = f"{unit.record_id} {unit.section}"
    try:
        with client.messages.stream(
            model=settings.model,
            max_tokens=MAX_TOKENS,
            system=system_blocks(),
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_format=ExtractionOutput,
            output_config=config,
        ) as stream:
            try:
                response = stream.get_final_message()
            except ValidationError as exc:
                message = f"{name}: the output did not satisfy the schema ({exc})"
                raise failed(number, message, stream.current_message_snapshot) from exc
            except (anthropic.APIError, httpx2.HTTPError) as exc:
                message = f"{name}: the call dropped mid stream ({exc})"
                raise failed(number, message, stream.current_message_snapshot) from exc
    except (anthropic.APIError, httpx2.HTTPError) as exc:
        message = f"{name}: the call failed ({exc})"
        attempt = Attempt(
            number=number, input_tokens=0, output_tokens=0, run_id=uuid.uuid4().hex, error=message
        )
        raise ExtractionFailed(message, (attempt,)) from exc

    parsed = response.parsed_output
    if parsed is None:
        message = (
            f"{name}: the model returned no parsed output (stop_reason={response.stop_reason}, "
            f"output_tokens={response.usage.output_tokens} of max {MAX_TOKENS})"
        )
        raise failed(number, message, response)
    return _attempt_from_usage(
        number,
        response.usage,
        output=parsed,
        raw_response=_raw_text(response.content),
        stop_reason=response.stop_reason,
    )


def recorded_cost(artifact: RunArtifact) -> float:
    """What one attempt's recorded tokens cost, each kind at its own rate."""
    return (
        (artifact.input_tokens or 0) * run_units.INPUT_RATE
        + (artifact.output_tokens or 0) * run_units.OUTPUT_RATE
        + (artifact.cache_creation_input_tokens or 0) * run_units.CACHE_WRITE_RATE
        + (artifact.cache_read_input_tokens or 0) * run_units.CACHE_READ_RATE
    ) / 1e6


def safe_cost(artifact: RunArtifact) -> float:
    """The running total's figure for one attempt: a failure never counts below the flat."""
    cost = recorded_cost(artifact)
    return max(cost, FAILED_ATTEMPT_USD) if artifact.error is not None else cost


def types_per_run(identified: tuple[IdentifiedOutput, ...]) -> list[dict[str, int]]:
    """Each run's entity count by type, the figures AC-36 to AC-38 are judged on."""
    return [
        dict(sorted(Counter(str(e.entity.type) for e in output.entities).items()))
        for output in identified
    ]


class Runner:
    """The running total, the call count, and the stop points, across all units."""

    def __init__(self, client: anthropic.Anthropic, settings: AnthropicSettings) -> None:
        """Start at zero spent and zero calls."""
        self.client = client
        self.settings = settings
        self.total = 0.0
        self.calls = 0

    def run_unit(self, unit: Unit, slug: str) -> UnitResult:
        """Three runs, each retried once, every attempt written as it settles."""
        artifacts: list[RunArtifact] = []
        identified: list[IdentifiedOutput] = []
        extracted_at = now_utc()
        for run in range(1, self.settings.runs_per_unit + 1):
            output: ExtractionOutput | None = None
            for number in range(1, RETRIES + 2):
                if self.total + FAILED_ATTEMPT_USD > CEILING_USD:
                    raise Stop(
                        f"one more call could pass ${CEILING_USD} "
                        f"(spent ${self.total:.4f}), before {unit.record_id} run {run}"
                    )
                try:
                    attempt = call_once(self.client, self.settings, unit, number)
                except ExtractionFailed as exc:
                    attempt = exc.attempts[-1]
                artifact = build_artifact(
                    unit=unit,
                    section_slug=slug,
                    run=run,
                    attempt=attempt.number,
                    output=attempt.output,
                    model=self.settings.model,
                    prompt_version=PROMPT_VERSION,
                    commit=COMMIT,
                    extracted_at=extracted_at,
                    max_output_tokens=MAX_TOKENS,
                    effort=self.settings.effort or "default",
                    input_tokens=attempt.input_tokens,
                    output_tokens=attempt.output_tokens,
                    run_id=attempt.run_id,
                    raw_response=attempt.raw_response,
                    stop_reason=attempt.stop_reason,
                    error=attempt.error,
                    cache_creation_input_tokens=attempt.cache_creation_input_tokens,
                    cache_read_input_tokens=attempt.cache_read_input_tokens,
                )
                print("  wrote", write_run(ROOT, artifact).relative_to(ROOT), flush=True)
                artifacts.append(artifact)
                self.total += safe_cost(artifact)
                self.calls += 1
                if self.calls == 2 and attempt.cache_read_input_tokens == 0:
                    raise Stop("the second call read nothing from the cache (AC-19)")
                if attempt.output is not None:
                    output = attempt.output
                    break
                print(f"  attempt failed: {attempt.error}", flush=True)
            if output is None:
                raise Stop(f"{unit.record_id} {unit.section} run {run} failed after its retry")
            located = label_binding_rules(unit, locate_output(unit, output))
            identified.append(assign_ids(located, unit.record_id, slug))
        settled = [a for a in artifacts if a.output is not None]
        return UnitResult(
            unit=unit,
            section_slug=slug,
            artifacts=tuple(artifacts),
            identified=tuple(identified),
            routed=route_runs(identified),
            input_tokens=sum(a.input_tokens or 0 for a in settled),
            output_tokens=sum(a.output_tokens or 0 for a in settled),
            cache_creation_input_tokens=sum(a.cache_creation_input_tokens or 0 for a in settled),
            cache_read_input_tokens=sum(a.cache_read_input_tokens or 0 for a in settled),
        )


def main(argv: list[str]) -> None:
    """Run the eight units in order, stopping at the first stop point reached."""
    if len(argv) != 1:
        raise SystemExit(__doc__)
    if argv[0] != PROMPT_VERSION:
        raise SystemExit(f"PROMPT_VERSION is {PROMPT_VERSION}, not {argv[0]}: refusing to run")
    settings = load_anthropic_settings()
    runner = Runner(anthropic.Anthropic(api_key=settings.api_key), settings)
    figures = budgets()
    day = run_date()
    report: list[dict[str, object]] = []
    (HERE / "data").mkdir(exist_ok=True)
    print(f"prompt {PROMPT_VERSION}, ceiling ${CEILING_USD}, failed attempt ${FAILED_ATTEMPT_USD}")
    try:
        for key in UNITS:
            unit, slug = target(key)
            name = f"{unit.record_id} {unit.section}"
            central, wider = figures[name]
            if runner.total + wider > CEILING_USD:
                raise Stop(
                    f"${runner.total:.4f} spent plus {name}'s wider ${wider:.4f} "
                    f"would pass ${CEILING_USD}"
                )
            print(f"\n=== {name} (central ${central:.4f}, wider ${wider:.4f}) ===", flush=True)
            for path in move_superseded(ROOT, unit.record_id, slug, day):
                print("  moved", path.relative_to(ROOT), flush=True)
            before = runner.total
            result = runner.run_unit(unit, slug)
            spent = round(runner.total - before, 4)
            entry = describe(result)
            entry["types_per_run"] = types_per_run(result.identified)
            entry["safe_cost_usd"] = spent
            entry["central_usd"] = central
            entry["wider_usd"] = wider
            report.append(entry)
            (HERE / "data" / "run.json").write_text(json.dumps(report, indent=2) + "\n")
            print(
                f"  {name}: ${spent:.4f} against central ${central:.4f}, wider ${wider:.4f} "
                f"(running ${runner.total:.4f}, {runner.calls} calls)",
                flush=True,
            )
            print(f"  types per run: {entry['types_per_run']}", flush=True)
    except Stop as stop:
        print(f"\nStopping here: {stop}. Spent ${runner.total:.4f} in {runner.calls} calls.")
        return
    print(f"\nAll 8 units done. Spent ${runner.total:.4f} in {runner.calls} calls.")


if __name__ == "__main__":
    main(sys.argv[1:])
