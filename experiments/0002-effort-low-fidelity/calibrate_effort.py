"""Calibrate one effort level on a single section, three runs, with spans persisted.

Thinking is billed as output, so effort is this pipeline's real cost dial. Spec 0001
never decided a level, which meant the first runs used the model's default (`high`) by
accident rather than by choice. This measures one level so the choice can be made on
numbers.

    uv run python experiments/0002-effort-low-fidelity/calibrate_effort.py low
"""

import json
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "0001-ac14-type-stability"))

from run import find

from tracepath.artifacts import build_artifact, now_utc, write_run
from tracepath.config import load_anthropic_settings
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    Attempt,
    ExtractionFailed,
    build_client,
    run_with_retry,
)
from tracepath.extract.compare import compare_runs, route_runs
from tracepath.extract.ids import assign_ids, locate_output

DATA = Path(__file__).parent / "data"
RECORD, SECTION = "0012", "Consequences"
COMMIT = "2e40bcf"


def main(level: str) -> int:
    """Run one section three times at one effort level and record what it cost."""
    base = load_anthropic_settings()
    settings = replace(base, effort=None if level == "default" else level)
    client = build_client(settings)
    unit, slug = find(RECORD, SECTION)
    print(f"{unit.record_id} / {unit.section} ({len(unit.text)} chars) | effort={level}")

    identified, rows = [], []
    started = time.time()
    started_at = now_utc()

    def record(run: int, attempt: Attempt) -> None:
        """Write one artifact per **attempt**, the failed ones included (spec 0001).

        The same rule `run_unit()`'s own `record()` follows: usage counts this attempt
        alone, so a retry's cost sits beside the call it replaced rather than folded
        into it, and a call that raised still leaves a record of what it spent.

        Written under the experiment's own data/, never into `artifacts/`: these are a
        calibration's output, and overwriting the committed production run would
        destroy the evidence it stands on.
        """
        write_run(
            DATA / f"effort-{level}",
            build_artifact(
                unit=unit,
                section_slug=slug,
                run=run,
                attempt=attempt.number,
                output=attempt.output,
                model=settings.model,
                prompt_version=PROMPT_VERSION,
                commit=COMMIT,
                extracted_at=started_at,
                max_output_tokens=MAX_TOKENS,
                effort=level,
                input_tokens=attempt.input_tokens,
                output_tokens=attempt.output_tokens,
                error=attempt.error,
            ),
        )

    for run in range(1, settings.runs_per_unit + 1):
        at = time.time()
        try:
            result = run_with_retry(client, settings, unit, run)
        except ExtractionFailed as exc:
            # The attempts ride out of the failure rather than dying with it. A
            # calibration that crashes without writing what it spent is the same
            # unrecoverable cost spec 0001's artifact storage row exists to close.
            for attempt in exc.attempts:
                record(run, attempt)
            raise
        seconds = time.time() - at
        for attempt in result.attempts:
            record(run, attempt)
        ids = assign_ids(locate_output(unit, result.output), unit.record_id, slug)
        identified.append(ids)
        types = Counter(str(e.entity.type) for e in ids.entities)
        flags = Counter(str(f) for e in ids.entities for f in e.entity.known_trap_flags)
        rows.append(
            {
                "run": run,
                "seconds": round(seconds),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "wasted_input_tokens": result.wasted_input_tokens,
                "wasted_output_tokens": result.wasted_output_tokens,
                "entities": len(ids.entities),
                "relationships": len(ids.relationships),
                "types": dict(types),
                "flags": dict(flags),
            }
        )
        print(
            f"  run {run}: {seconds:5.0f}s out={result.output_tokens:6,d} "
            f"entities={len(ids.entities):2d} types={dict(types)} flags={dict(flags)}"
        )

    comparison = compare_runs(identified)
    routed = route_runs(identified)
    total_in = sum(r["input_tokens"] + r["wasted_input_tokens"] for r in rows)
    total_out = sum(r["output_tokens"] + r["wasted_output_tokens"] for r in rows)
    summary = {
        "effort": level,
        "model": settings.model,
        "prompt_version": PROMPT_VERSION,
        "max_output_tokens": MAX_TOKENS,
        "record": unit.record_id,
        "section": unit.section,
        "runs": rows,
        "wall_clock_seconds": round(time.time() - started),
        "runs_agree": comparison.agree,
        "differing_entity_signatures": len(comparison.differing_entities),
        "accepted_entities": len(routed.accepted_entities),
        "review_items": len(routed.review),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "cost_usd": round(total_in / 1e6 * 2 + total_out / 1e6 * 10, 4),
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"effort-{level}-calibration.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "runs_agree",
                    "differing_entity_signatures",
                    "accepted_entities",
                    "review_items",
                    "wall_clock_seconds",
                    "total_output_tokens",
                    "cost_usd",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "default"))
