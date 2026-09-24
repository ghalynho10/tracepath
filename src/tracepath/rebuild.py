"""Rebuilding a corpus run from the committed artifacts, with no model call.

Spec 0001 makes the JSON run artifacts the source of truth and the graph derived and
disposable. That claim only means something if there is a real path from the files
back to a full run, so this is it: read `artifacts/runs/`, re-split each unit from the
pinned snapshot, re-locate and re-identify every span, and hand back the same
`UnitResult` values the live pipeline produces.

Nothing here calls the API or the database. The one thing a rebuild cannot recover is
what the original calls cost, so a rebuilt `UnitResult` reports zero tokens: the spend
belongs to the run that made the calls, and adding it up again here would double count
a cost that was never paid twice.
"""

from pathlib import Path

from tracepath.artifacts import RUNS_DIR, RunArtifact, read_run
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import assign_ids, locate_output
from tracepath.extract.records import Record, records_for
from tracepath.extract.units import Unit, split_units
from tracepath.pipeline import UnitResult


class RebuildFailed(Exception):
    """The committed artifacts cannot be rebuilt into a run as they stand."""


def unit_for(artifact: RunArtifact, snapshot: Path) -> Unit:
    """The unit one artifact came from, re-split from the pinned snapshot.

    Raises:
        RebuildFailed: the snapshot no longer holds the unit the artifact names.
    """
    path = snapshot / artifact.file
    if not path.exists():
        raise RebuildFailed(
            f"{artifact.file} is not in the snapshot, so {artifact.record} cannot be rebuilt"
        )
    units = split_units(artifact.file, path.read_text())
    found = [
        unit
        for unit in units
        if unit.record_id == artifact.record and unit.section == artifact.section
    ]
    if not found:
        raise RebuildFailed(
            f"{artifact.file} no longer holds {artifact.record} / {artifact.section}"
        )
    return found[0]


def committed_units(root: Path, snapshot: Path) -> tuple[UnitResult, ...]:
    """Every committed unit of a run, re-identified from its artifacts. No API calls.

    Only settled runs are read. A failed attempt is written under its own name, which
    this glob does not match, so it is counted in the cost and never mistaken for a run.

    Raises:
        RebuildFailed: there are no artifacts to rebuild from.
    """
    by_unit: dict[tuple[str, str], list[RunArtifact]] = {}
    for path in sorted((root / RUNS_DIR).glob("*/*/run-*.json")):
        artifact = read_run(path)
        by_unit.setdefault((artifact.record, artifact.section_slug), []).append(artifact)
    if not by_unit:
        raise RebuildFailed(f"no run artifacts found under {root / RUNS_DIR}")

    results: list[UnitResult] = []
    for artifacts in by_unit.values():
        ordered = sorted(artifacts, key=lambda a: a.run)
        unit = unit_for(ordered[0], snapshot)
        identified = tuple(
            assign_ids(locate_output(unit, a.output), unit.record_id, a.section_slug)
            for a in ordered
            if a.output is not None
        )
        results.append(
            UnitResult(
                unit=unit,
                section_slug=ordered[0].section_slug,
                artifacts=tuple(ordered),
                identified=identified,
                routed=route_runs(identified),
                input_tokens=0,
                output_tokens=0,
            )
        )
    return tuple(results)


def records_for_units(
    results: tuple[UnitResult, ...], snapshot: Path, commit: str
) -> tuple[Record, ...]:
    """Every Record the rebuilt entities hang from, one pass per source document."""
    paths = list(dict.fromkeys(result.unit.path for result in results))
    built: list[Record] = []
    seen: set[str] = set()
    for path in paths:
        text = (snapshot / path).read_text()
        # `records_for` needs the document's whole unit list to find its feature rows.
        for record in records_for(split_units(path, text), text, commit):
            if record.canonical_id not in seen:
                seen.add(record.canonical_id)
                built.append(record)

    needed = {result.unit.record_id for result in results}
    if any(result.unit.record_id.startswith("feature-") for result in results):
        needed.add("scope")
    return tuple(record for record in built if record.canonical_id in needed & seen)
