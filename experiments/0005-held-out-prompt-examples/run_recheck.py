"""Run experiment 0006, the accuracy bar re check: 18 calls, 3 fresh held out units.

Spec 0003, AC-30. Three units, none in group A/B/C, any worked example, or the type
coverage set: `0014 ## Requirements`, `0015 ## Feature design`, and JobHunt's feature
33 scope row (Band anchor review). Each gets 3 before calls under `0002.3` (the prompt
and schema of commit `972907b`, the commit group A's lost links were measured against)
and 3 after calls under `0003.1`, 18 calls in all.

The before calls use the current code throughout (`build_artifact`, `write_run`, the
comparator, the router): only the system prompt text and the entity `label` field's
sample sentence come from `972907b`, everything else, including the four storage
safeguards spec 0001 now names, is today's code. `972907b`'s schema is otherwise
byte identical to today's (the only diff is that one sample string), so today's
`ExtractionOutput` reads a `972907b`-shaped response back with no loss.

Stop points, checked between units, never mid unit:

* The 9 before calls run first. If their running total passes $2.05, stop before the
  after calls and report what was spent.
* Otherwise the 9 after calls run as one cached session (`run_units.py`'s own cache
  read check at position 0 still applies). If the running total (before + after so
  far) would pass $5.70, the current unit finishes and the run stops before the next.

Run from the repository root:
    uv run python <this file> <expected prompt version>
"""

import ast
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import cast

import anthropic
import httpx2
from anthropic.types import OutputConfigParam
from pydantic import ConfigDict, Field, ValidationError

from tracepath.artifacts import RUNS_DIR, RunArtifact, build_artifact, now_utc, read_run, write_run
from tracepath.config import AnthropicSettings, load_anthropic_settings
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    RETRIES,
    Attempt,
    Effort,
    ExtractionFailed,
    RunOutcome,
    _attempt_from_usage,
    _raw_text,
    user_prompt,
)
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import assign_ids, label_binding_rules, locate_output, section_slugs
from tracepath.extract.schema import ExtractedEntity, ExtractionOutput
from tracepath.extract.units import Unit, UnitKind, split_units
from tracepath.pipeline import UnitFailed, UnitResult, run_unit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_units
from run_units import cache_tokens, describe, move_superseded

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent
COMMIT = "2e40bcf"
SUPERSEDED_DATE = "2026-09-28"

#: The commit the before calls run under (AC-30), the same one group A's lost links
#: were measured against.
OLD_PROMPT_COMMIT = "972907b"

#: The re check's three fresh held out units (AC-30).
UNITS = [
    ("specs/0014-", "Requirements"),
    ("specs/0015-", "Feature design"),
    ("scope/scope.md", "33. Band anchor review · done"),
]

STOP_BEFORE_USD = 2.05
STOP_CEILING_USD = 5.70

#: A failed or crashed attempt's recorded usage can undercount badly: the schema
#: validation failure path snapshots usage before the API's final usage event lands
#: (observed: 2 output tokens recorded for a ~15k character near complete response).
#: For the running totals that gate a real spend, every failed attempt counts at this
#: flat figure instead, the heaviest measured single call in experiment 0005's data
#: (recheck-cost-estimate.json's Section-kind wide after figure), never its own,
#: possibly wrong, recorded tokens. The artifact itself still keeps what the API
#: actually reported, wrong or not; only the stop-condition accounting is corrected.
FAILED_ATTEMPT_FLAT_USD = 0.35

#: The entity/relationship ruling sample sizes (AC-30), and the dropped link sample.
ENTITY_SAMPLE, RELATIONSHIP_SAMPLE, DROPPED_SAMPLE = 10, 5, 15


class OldExtractedEntity(ExtractedEntity):
    """`972907b`'s `ExtractedEntity`: identical, except the `label` sample sentence.

    AC-7's fix (spec 0002, 2026-09-23) replaced the schema's own bad sample
    (`key invariant 1`, which appears nowhere in the corpus) with a real one. The
    before calls need the pre fix sample back, since that string is part of what a
    `0002.3` measurement means. `title` is pinned back to `ExtractedEntity` so the
    schema's model facing text matches `972907b` exactly; only the internal `$defs`
    key this class's own Python name produces (`OldExtractedEntity`) differs, and
    that key carries no description or other model facing content.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", title="ExtractedEntity")

    label: str | None = Field(
        default=None,
        description="The author's own label for an unnumbered item, e.g. `key invariant 1`.",
    )


class OldExtractionOutput(ExtractionOutput):
    """`972907b`'s `ExtractionOutput`, narrowed to `OldExtractedEntity`.

    Inherits every validator `ExtractionOutput` already has (placeholder id
    uniqueness, local endpoints resolving); only the entity type changes. `title`
    pinned back to `ExtractionOutput`, matching `OldExtractedEntity`'s own note.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", title="ExtractionOutput")

    entities: tuple[OldExtractedEntity, ...] = ()


def find(prefix: str, section: str) -> tuple[Unit, str]:
    """The unit a manifest key names, and the section slug its derived ids carry.

    The scope document holds many records, one per feature row, so the target
    unit's own record is read off the unit itself (matched by section text alone,
    unique across the file), never assumed from the file's first unit.
    """
    if prefix.endswith(".md"):
        path = SNAPSHOT / prefix
    else:
        path = next(SNAPSHOT.glob(f"{prefix}*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    target = next(u for u in units if u.section == section and u.kind is not UnitKind.INTRO)
    own = [u for u in units if u.record_id == target.record_id]
    slugs = section_slugs(tuple(u.section for u in own))
    for unit, slug in zip(own, slugs, strict=True):
        if unit.section == section and unit.kind is not UnitKind.INTRO:
            return unit, slug
    raise SystemExit(f"no unit {section!r} in {path.relative_to(SNAPSHOT)}")


def old_system_prompt() -> str:
    """The `0002.3` system prompt, read from git, matching `measure_prefix.py`."""
    source = subprocess.run(
        ["git", "show", f"{OLD_PROMPT_COMMIT}:src/tracepath/extract/client.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    found = re.search(r'^SYSTEM_PROMPT = ("""\\\n.*?\n""")$', source, re.MULTILINE | re.DOTALL)
    if found is None:
        raise SystemExit(f"no SYSTEM_PROMPT literal at {OLD_PROMPT_COMMIT}")
    value = ast.literal_eval(found.group(1))
    assert isinstance(value, str)
    return value


def before_once(
    client: anthropic.Anthropic,
    settings: AnthropicSettings,
    unit: Unit,
    system: str,
    number: int = 1,
) -> Attempt:
    """One `0002.3` call: `972907b`'s prompt and schema, today's call machinery.

    Mirrors `client.extract_once()` exactly (retries, error handling, the safeguarded
    `Attempt` construction), except `system` and `output_format` are the caller's own,
    uncached (`0002.3` predates prompt caching, AC-19).

    Raises:
        ExtractionFailed: the call failed, or its output did not satisfy the schema.
    """
    config: OutputConfigParam = {}
    if settings.effort is not None:
        config["effort"] = cast("Effort", settings.effort)
    try:
        with client.messages.stream(
            model=settings.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_format=OldExtractionOutput,
            output_config=config,
        ) as stream:
            try:
                response = stream.get_final_message()
            except ValidationError as exc:
                snapshot = stream.current_message_snapshot
                message = (
                    f"{unit.record_id} {unit.section}: the output did not satisfy "
                    f"the 0002.3 schema ({exc})"
                )
                raise ExtractionFailed(
                    message,
                    (
                        _attempt_from_usage(
                            number,
                            snapshot.usage if snapshot else None,
                            error=message,
                            raw_response=_raw_text(snapshot.content) if snapshot else None,
                            stop_reason=snapshot.stop_reason if snapshot else None,
                        ),
                    ),
                ) from exc
            except (anthropic.APIError, httpx2.HTTPError) as exc:
                # A connection dropped mid stream (not caught by the outer clause,
                # which only covers a failure to establish the stream at all): the
                # snapshot still holds whatever partial content and usage arrived
                # before the drop, null when nothing did. Not caught in production
                # `client.extract_once()` either (spec 0001; flagged, not fixed here).
                snapshot = stream.current_message_snapshot
                message = f"{unit.record_id} {unit.section}: the call dropped mid stream ({exc})"
                raise ExtractionFailed(
                    message,
                    (
                        _attempt_from_usage(
                            number,
                            snapshot.usage if snapshot else None,
                            error=message,
                            raw_response=_raw_text(snapshot.content) if snapshot else None,
                            stop_reason=snapshot.stop_reason if snapshot else None,
                        ),
                    ),
                ) from exc
    except anthropic.APIError as exc:
        # No stream object exists here: the connection never established at all.
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

    parsed = response.parsed_output
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
    # The two schemas are structurally identical bar one field's description, which
    # carries no data, so today's `ExtractionOutput` reads the dump back with no loss.
    current = ExtractionOutput.model_validate(parsed.model_dump(mode="json"))
    return _attempt_from_usage(
        number,
        response.usage,
        output=current,
        raw_response=_raw_text(response.content),
        stop_reason=response.stop_reason,
    )


def before_with_retry(
    client: anthropic.Anthropic, settings: AnthropicSettings, unit: Unit, system: str, run: int
) -> RunOutcome:
    """One before run, retrying once on a failed or malformed call.

    Matches `client.run_with_retry()`'s policy (spec 0001).
    """
    last: Exception | None = None
    attempts: list[Attempt] = []
    for number in range(1, RETRIES + 2):
        try:
            attempts.append(before_once(client, settings, unit, system, number))
            return RunOutcome(attempts=tuple(attempts))
        except ExtractionFailed as exc:
            last = exc
            attempts.extend(exc.attempts)
    message = f"{unit.record_id} {unit.section}: failed after retry"
    raise ExtractionFailed(message, tuple(attempts)) from last


def run_unit_before(
    client: anthropic.Anthropic,
    settings: AnthropicSettings,
    unit: Unit,
    section_slug: str,
    system: str,
) -> UnitResult:
    """One unit's 3 before runs, matching `pipeline.run_unit()`'s shape exactly.

    Prompt version is stamped `0002.3` on every artifact, the commit is still the
    corpus snapshot commit (`COMMIT`), never the code commit: `commit` records corpus
    provenance, not code provenance, matching every other committed artifact.
    """
    artifacts: list[RunArtifact] = []
    identified = []
    input_tokens = output_tokens = 0
    extracted_at = now_utc()

    def record(run: int, attempt: Attempt) -> None:
        artifacts.append(
            build_artifact(
                unit=unit,
                section_slug=section_slug,
                run=run,
                attempt=attempt.number,
                output=attempt.output,
                model=settings.model,
                prompt_version="0002.3",
                commit=COMMIT,
                extracted_at=extracted_at,
                max_output_tokens=MAX_TOKENS,
                effort=settings.effort or "default",
                input_tokens=attempt.input_tokens,
                output_tokens=attempt.output_tokens,
                run_id=attempt.run_id,
                raw_response=attempt.raw_response,
                stop_reason=attempt.stop_reason,
                error=attempt.error,
            )
        )

    for run in range(1, settings.runs_per_unit + 1):
        try:
            outcome = before_with_retry(client, settings, unit, system, run)
        except ExtractionFailed as exc:
            for attempt in exc.attempts:
                record(run, attempt)
            raise UnitFailed(str(exc), tuple(artifacts)) from exc
        for attempt in outcome.attempts:
            record(run, attempt)
            input_tokens += attempt.input_tokens
            output_tokens += attempt.output_tokens
        located = label_binding_rules(unit, locate_output(unit, outcome.output))
        identified.append(assign_ids(located, unit.record_id, section_slug))
    return UnitResult(
        unit=unit,
        section_slug=section_slug,
        artifacts=tuple(artifacts),
        identified=tuple(identified),
        routed=route_runs(identified),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def safe_cost(result: UnitResult) -> float:
    """The running-total cost of one unit's artifacts, a failed attempt counted flat.

    Unlike `run_units.cost()` (which trusts every attempt's own recorded tokens),
    this is what gates a real spend: a failed attempt's recorded usage can be badly
    undercounted (`FAILED_ATTEMPT_FLAT_USD`'s own note), so it is never trusted here.
    """
    total = 0.0
    for artifact in result.artifacts:
        if artifact.error is not None:
            total += FAILED_ATTEMPT_FLAT_USD
            continue
        total += (
            (artifact.input_tokens or 0) * run_units.INPUT_RATE
            + (artifact.output_tokens or 0) * run_units.OUTPUT_RATE
            + (artifact.cache_creation_input_tokens or 0) * run_units.CACHE_WRITE_RATE
            + (artifact.cache_read_input_tokens or 0) * run_units.CACHE_READ_RATE
        ) / 1e6
    return round(total, 4)


def existing_before_result(unit: Unit, section_slug: str) -> UnitResult | None:
    """A unit's before result, rebuilt from already committed `0002.3` artifacts.

    `None` when fewer than 3 settled runs sit there, or any carry a different prompt
    version: only an already complete, already paid-for before run is reused; a
    partial one is not silently treated as done.
    """
    directory = ROOT / RUNS_DIR / unit.record_id / section_slug
    if not directory.exists():
        return None
    all_artifacts = sorted(
        (read_run(p) for p in directory.glob("*.json")), key=lambda a: (a.run, a.attempt)
    )
    settled = [a for a in all_artifacts if a.output is not None and a.prompt_version == "0002.3"]
    if len({a.run for a in settled}) < 3:
        return None
    identified = tuple(
        assign_ids(
            label_binding_rules(unit, locate_output(unit, a.output)), unit.record_id, section_slug
        )
        for a in sorted(settled, key=lambda a: a.run)
    )
    return UnitResult(
        unit=unit,
        section_slug=section_slug,
        artifacts=tuple(all_artifacts),
        identified=identified,
        routed=route_runs(identified),
        input_tokens=sum(a.input_tokens or 0 for a in all_artifacts),
        output_tokens=sum(a.output_tokens or 0 for a in all_artifacts),
    )


def main(argv: list[str]) -> None:
    """Run the 9 before calls, then, budget permitting, the 9 after calls."""
    if len(argv) < 1:
        raise SystemExit(__doc__)
    expected = argv[0]
    if expected != PROMPT_VERSION:
        raise SystemExit(f"PROMPT_VERSION is {PROMPT_VERSION}, not {expected}: refusing to run")

    settings = load_anthropic_settings()
    client = anthropic.Anthropic(api_key=settings.api_key)
    old = old_system_prompt()
    targets = [find(prefix, section) for prefix, section in UNITS]

    print(f"=== before (0002.3, uncached), stop if total > ${STOP_BEFORE_USD} ===")
    before_total = 0.0
    before_report: list[dict[str, object]] = []
    for unit, slug in targets:
        reused = existing_before_result(unit, slug)
        if reused is not None:
            result = reused
            print(f"  {unit.record_id} {unit.section}: reusing 3 already committed 0002.3 runs")
        else:
            result = run_unit_before(client, settings, unit, slug, old)
            for artifact in result.artifacts:
                print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
        entry = describe(result)
        entry["prompt_version"] = "0002.3"
        unit_cost = safe_cost(result)
        entry["safe_cost_usd"] = unit_cost
        before_report.append(entry)
        before_total += unit_cost
        print(f"  {unit.record_id} {unit.section}: ${unit_cost:.4f} (running ${before_total:.4f})")
        if before_total > STOP_BEFORE_USD:
            print(f"STOP: before total ${before_total:.4f} exceeds ${STOP_BEFORE_USD}")
            (HERE / "data").mkdir(exist_ok=True)
            (HERE / "data" / "recheck-before.json").write_text(
                json.dumps(before_report, indent=2) + "\n"
            )
            return
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "recheck-before.json").write_text(json.dumps(before_report, indent=2) + "\n")
    print(f"before total: ${before_total:.4f}")

    print(f"\n=== after (0003.1, cached), ceiling ${STOP_CEILING_USD} ===")
    running_total = before_total
    after_report: list[dict[str, object]] = []
    for position, (unit, slug) in enumerate(targets):
        for path in move_superseded(ROOT, unit.record_id, slug):
            print("  moved", path.relative_to(ROOT))
        try:
            result = run_unit(client, settings, unit, slug, COMMIT, now_utc())
        except UnitFailed as exc:
            for artifact in exc.artifacts:
                print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
            raise
        for artifact in result.artifacts:
            print("  wrote", write_run(ROOT, artifact).relative_to(ROOT))
        entry = describe(result)
        unit_cost = safe_cost(result)
        entry["safe_cost_usd"] = unit_cost
        after_report.append(entry)
        running_total += unit_cost
        print(f"  {unit.record_id} {unit.section}: ${unit_cost:.4f} (running ${running_total:.4f})")
        if position == 0 and cache_tokens(result, "cache_read_input_tokens") == 0:
            raise SystemExit(
                "AC-19: the first unit's later calls read nothing from the cache. Stopped."
            )
        if running_total > STOP_CEILING_USD:
            print(f"STOP: running total ${running_total:.4f} exceeds ${STOP_CEILING_USD}")
            break

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "recheck-after.json").write_text(json.dumps(after_report, indent=2) + "\n")
    after_total = sum(float(str(e["safe_cost_usd"])) for e in after_report)
    print(f"\nafter total: ${after_total:.4f}")
    print(f"grand total (before + after): ${before_total + after_total:.4f}")


if __name__ == "__main__":
    main(sys.argv[1:])
