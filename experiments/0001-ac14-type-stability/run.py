"""Run build plan tasks 7 and 10 and record what came back.

Task 7 is the thin thread: one `## Requirements` section, end to end, loaded.
Task 10 is AC-14's coverage set: a Consequences, a Follow-up, a Build plan, a section
holding struck text, a Preamble and a scope feature row.

Run from the repository root:  uv run python experiments/0001-ac14-type-stability/run.py
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

from tracepath.artifacts import (
    ensure_review_log,
    now_utc,
    write_review_queue,
    write_run,
)
from tracepath.config import load_anthropic_settings, load_neo4j_settings
from tracepath.extract.client import MAX_TOKENS, PROMPT_VERSION, build_client
from tracepath.extract.ids import section_slugs
from tracepath.extract.records import Record, read_commit, scope_document_record, spec_record
from tracepath.extract.records import feature_record as build_feature_record
from tracepath.extract.units import Unit, UnitKind, split_units
from tracepath.graph import connect
from tracepath.graph.model import Provenance
from tracepath.graph.schema import clear, create_constraints
from tracepath.pipeline import UnitResult, load, resolve_accepted, review_rows, run_unit

#: The decided effort for this run. Chosen by measurement, not by default: see this
#: experiment's README and `data/effort-*-calibration.json`. Thinking is billed as
#: output, so this is the pipeline's real cost dial.
EFFORT = "medium"

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
DATA = Path(__file__).parent / "data"

#: The unit each phase covers: (phase, label, spec or scope, section).
TASK_7 = [("Requirements (thin thread)", "0012", "Requirements")]
TASK_10 = [
    ("Consequences", "0012", "Consequences"),
    ("Follow-up", "0012", "Follow-up"),
    ("Build plan", "0012", "Build plan"),
    ("struck text", "0021", "Requirements"),
    ("Preamble", "0008", "Preamble"),
    ("scope feature row", "scope", "feature-21"),
]


def units_of(path: Path) -> tuple[Unit, ...]:
    """Every unit of one snapshot file."""
    return split_units(str(path.relative_to(SNAPSHOT)), path.read_text())


def find(record: str, section: str) -> tuple[Unit, str]:
    """The unit, and its section slug made unique within its own record."""
    if record == "scope":
        path = SNAPSHOT / "scope" / "scope.md"
        every = units_of(path)
        unit = next(u for u in every if u.kind is UnitKind.FEATURE_ROW and u.record_id == section)
    else:
        path = next(SNAPSHOT.glob(f"specs/{record}-*/index.md"))
        every = units_of(path)
        unit = next(u for u in every if u.section == section)
    own = [u for u in every if u.record_id == unit.record_id]
    slugs = section_slugs(tuple(u.section for u in own))
    return unit, slugs[own.index(unit)]


def records_for_units(units: list[Unit], commit: str) -> list[Record]:
    """Every Record node the loaded entities need to hang from."""
    built: dict[str, Record] = {}
    for unit in units:
        if unit.record_id in built:
            continue
        if unit.record_id.startswith("feature-"):
            built[unit.record_id] = build_feature_record(unit, commit)
            scope_path = SNAPSHOT / "scope" / "scope.md"
            built.setdefault(
                "scope", scope_document_record("scope/scope.md", scope_path.read_text(), commit)
            )
        else:
            path = next(SNAPSHOT.glob(f"specs/{unit.record_id}-*/index.md"))
            built[unit.record_id] = spec_record(
                str(path.relative_to(SNAPSHOT)), path.read_text(), commit
            )
    return list(built.values())


def describe(label: str, result: UnitResult) -> dict[str, object]:
    """What this run is being judged on: agreement, types, and what was held back."""
    per_run_types = [
        sorted({str(e.entity.type) for e in output.entities}) for output in result.identified
    ]
    counts_per_run = [
        {t: sum(1 for e in o.entities if str(e.entity.type) == t) for t in sorted(types)}
        for o, types in zip(result.identified, per_run_types, strict=True)
    ]
    return {
        "label": label,
        "record": result.unit.record_id,
        "section": result.unit.section,
        "unit_kind": str(result.unit.kind),
        "runs_agree": result.routed.comparison.agree,
        "entities_per_run": [len(o.entities) for o in result.identified],
        "relationships_per_run": [len(o.relationships) for o in result.identified],
        "types_per_run": per_run_types,
        "type_counts_per_run": counts_per_run,
        "types_stable_across_runs": len({tuple(t) for t in per_run_types}) == 1,
        "accepted_entities": [e.canonical_id for e in result.routed.accepted_entities],
        "accepted_relationships": len(result.routed.accepted_relationships),
        "review": [
            {"signature": list(item.signature), "reasons": [str(r) for r in item.reasons]}
            for item in result.routed.review
        ],
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "artifacts": [str(write_run(ROOT, a).relative_to(ROOT)) for a in result.artifacts],
    }


def main() -> int:
    """Run both phases, write the artifacts, load the graph, record the measurements."""
    commit = read_commit((ROOT / "corpus" / "jobhunt" / "SNAPSHOT.md").read_text())
    settings = replace(load_anthropic_settings(), effort=EFFORT)
    neo4j = load_neo4j_settings()
    client = build_client(settings)
    extracted_at = now_utc()
    DATA.mkdir(parents=True, exist_ok=True)

    report: list[dict[str, object]] = []
    results: list[UnitResult] = []
    for phase, picks in (("task 7", TASK_7), ("task 10", TASK_10)):
        for label, record, section in picks:
            unit, slug = find(record, section)
            print(f"[{phase}] {label}: {unit.record_id} / {unit.section} ({len(unit.text)} chars)")
            result = run_unit(client, settings, unit, slug, commit, extracted_at)
            results.append(result)
            entry = describe(label, result)
            entry["phase"] = phase
            report.append(entry)
            print(
                f"    agree={entry['runs_agree']} "
                f"entities={entry['entities_per_run']} "
                f"types_stable={entry['types_stable_across_runs']} "
                f"accepted={len(result.routed.accepted_entities)} "
                f"review={len(result.routed.review)}"
            )

    records = records_for_units([r.unit for r in results], commit)
    corpus = resolve_accepted(results, records)

    with connect(neo4j) as driver:
        clear(driver, neo4j.database)
        create_constraints(driver, neo4j.database)
        written = load(
            driver,
            neo4j.database,
            records,
            results,
            corpus.resolution,
            commit,
            Provenance(
                model=settings.model,
                prompt_version=PROMPT_VERSION,
                extracted_at=extracted_at,
                accepted_by="auto",
            ),
        )
        counts, _, _ = driver.execute_query(
            "MATCH (n) RETURN labels(n) AS labels, count(n) AS n", database_=neo4j.database
        )
        live = {", ".join(sorted(r["labels"])): r["n"] for r in counts}

    # Both kinds of held item, or AC-11c's promise covers only half of them: the ones
    # routing held inside a unit, and the ones `resolve_accepted()` held across units.
    queue = list(review_rows(results, corpus.held, settings.model, extracted_at))
    write_review_queue(ROOT, queue)
    ensure_review_log(ROOT)

    totals = {
        "input_tokens": sum(r.input_tokens for r in results),
        "output_tokens": sum(r.output_tokens for r in results),
        "calls": sum(len(r.artifacts) for r in results),
    }
    totals["cost_usd"] = round(
        totals["input_tokens"] / 1e6 * 2 + totals["output_tokens"] / 1e6 * 10, 4
    )

    summary = {
        "corpus_commit": commit,
        "model": settings.model,
        "runs_per_unit": settings.runs_per_unit,
        "effort": EFFORT,
        "max_output_tokens": MAX_TOKENS,
        "prompt_version": PROMPT_VERSION,
        "extracted_at": extracted_at,
        "sections": report,
        "written": written,
        "graph_nodes": live,
        "review_queue_size": len(queue),
        "totals": totals,
    }
    (DATA / "results.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("\n--- written to the graph ---")
    print(json.dumps(written, indent=2))
    print(json.dumps(live, indent=2))
    print("\n--- cost ---")
    print(json.dumps(totals, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
