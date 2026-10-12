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

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from tracepath.artifacts import RUNS_DIR, RunArtifact, read_run
from tracepath.config import RUNS_PER_UNIT
from tracepath.extract.codepass import code_decided_ids, parse_bullets
from tracepath.extract.compare import route_runs
from tracepath.extract.ids import assign_ids, label_binding_rules, locate_output
from tracepath.extract.records import Record, records_for
from tracepath.extract.units import Unit, split_units
from tracepath.pipeline import CorpusResolution, UnitResult
from tracepath.resolve.endpoints import ResolvedLink


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


@dataclass(frozen=True)
class PartialUnit:
    """A unit with fewer settled runs than the run policy asks for, so never loaded."""

    record: str
    section: str
    section_slug: str
    settled_runs: int


def _settled_by_unit(root: Path) -> dict[tuple[str, str], list[RunArtifact]]:
    """Every settled run artifact, grouped by `(record, section_slug)` in path order.

    A failed attempt is written under its own name, which this glob does not match, so
    it is counted in the cost and never mistaken for a run.
    """
    by_unit: dict[tuple[str, str], list[RunArtifact]] = {}
    for path in sorted((root / RUNS_DIR).glob("*/*/run-*.json")):
        artifact = read_run(path)
        by_unit.setdefault((artifact.record, artifact.section_slug), []).append(artifact)
    return by_unit


def unit_passes(root: Path) -> dict[tuple[str, str], tuple[str, ...]]:
    """Each unit's distinct `extracted_at` values, sorted, keyed by `(record, section_slug)`.

    Read from every artifact the unit holds, failed attempts included, since one command
    stamps one `extracted_at` on all it writes: a unit resumed after an earlier pass
    left only failed files still shows two values (spec 0004 AC-65, AC-66).
    """
    found: dict[tuple[str, str], set[str]] = {}
    for path in sorted((root / RUNS_DIR).glob("*/*/*.json")):
        artifact = read_run(path)
        found.setdefault((artifact.record, artifact.section_slug), set()).add(artifact.extracted_at)
    return {key: tuple(sorted(values)) for key, values in found.items()}


def settled_run_counts(root: Path) -> dict[tuple[str, str], int]:
    """How many settled runs each unit holds, keyed by `(record, section_slug)`."""
    return {key: len(artifacts) for key, artifacts in _settled_by_unit(root).items()}


def partial_units(root: Path) -> tuple[PartialUnit, ...]:
    """Every unit an interrupted or failed extraction left short of its runs.

    Until `extract --resume` completes it (spec 0004 AC-56), such a unit is not
    extracted: it stays out of the graph and the report names it
    `section_not_extracted` (AC-48b).
    """
    return tuple(
        PartialUnit(
            record=record,
            section=artifacts[0].section,
            section_slug=slug,
            settled_runs=len(artifacts),
        )
        for (record, slug), artifacts in _settled_by_unit(root).items()
        if len(artifacts) < RUNS_PER_UNIT
    )


def apply_code_pass(results: Sequence[UnitResult]) -> tuple[UnitResult, ...]:
    """The same units routed again with the code pass (spec 0007).

    Only routing is redone, from the very outputs already identified, so every span,
    entity and link the runs wrote is what it was; only acceptance can differ (AC-15).
    """
    return tuple(
        replace(
            result,
            routed=route_runs(result.identified, code_decided_ids(result.unit, result.identified)),
        )
        for result in results
    )


def committed_units(
    root: Path, snapshot: Path, *, code_pass: bool = False
) -> tuple[UnitResult, ...]:
    """Every fully extracted unit, re-identified from its artifacts. No API calls.

    Only settled runs are read, and only a unit holding the run policy's full count of
    them is rebuilt. A unit cut short is not extracted (`partial_units()`): comparing
    fewer runs than the policy asks for says nothing about stability, and one run
    cannot be compared at all. With `code_pass`, each unit is routed with the code
    pass applied (spec 0007, `apply_code_pass()`).

    Raises:
        RebuildFailed: there are no artifacts to rebuild from.
    """
    by_unit = _settled_by_unit(root)
    if not by_unit:
        raise RebuildFailed(f"no run artifacts found under {root / RUNS_DIR}")

    results: list[UnitResult] = []
    for artifacts in by_unit.values():
        if len(artifacts) < RUNS_PER_UNIT:
            continue
        ordered = sorted(artifacts, key=lambda a: a.run)
        unit = unit_for(ordered[0], snapshot)
        identified = tuple(
            assign_ids(
                label_binding_rules(unit, locate_output(unit, a.output)),
                unit.record_id,
                a.section_slug,
            )
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
    return apply_code_pass(results) if code_pass else tuple(results)


def released_links(
    without: CorpusResolution, with_pass: CorpusResolution
) -> tuple[ResolvedLink, ...]:
    """The links accepted with the code pass and not without it (spec 0007 AC-17, AC-25b).

    Found by resolving the whole corpus both ways, so a link that waited on a released
    entity in another unit counts too. Compared as a multiset: two equal links in one
    resolution are two links.
    """
    before = Counter(without.resolution.links)
    found: list[ResolvedLink] = []
    for link in with_pass.resolution.links:
        if before[link] > 0:
            before[link] -= 1
        else:
            found.append(link)
    return tuple(found)


@dataclass(frozen=True)
class CodePassUnit:
    """What `load --code-pass` prints for one unit (spec 0007 AC-17).

    `not_decided` counts parsed bullets whose id is not code decided, `repeated` names
    the ids two parsed bullets carry (AC-11), `struck` counts bullets opening with `~~`
    after the colon, and `unparsed` the other top level `- **AC-` bullets.
    """

    record: str
    section: str
    decided: tuple[str, ...]
    released_entities: int
    released_links: int
    not_decided: int
    repeated: tuple[str, ...]
    struck: int
    unparsed: int


def code_pass_report(
    with_pass: Sequence[UnitResult], links: Sequence[ResolvedLink]
) -> tuple[CodePassUnit, ...]:
    """One report row per unit, `links` being `released_links()` of the whole corpus.

    A released link is counted in the unit whose section it was written in, the same
    place `graph_build()` counts a unit's accepted links by.
    """
    rows: list[CodePassUnit] = []
    for result in with_pass:
        parse = parse_bullets(result.unit)
        decided = code_decided_ids(result.unit, result.identified)
        place = (result.unit.path, result.unit.section)
        rows.append(
            CodePassUnit(
                record=result.unit.record_id,
                section=result.unit.section,
                decided=tuple(
                    i
                    for i in dict.fromkeys(parse.parsed)
                    if f"{result.unit.record_id}/{i}" in decided
                ),
                released_entities=len(result.released),
                released_links=sum(1 for link in links if (link.file, link.section) == place),
                not_decided=sum(
                    1 for i in parse.parsed if f"{result.unit.record_id}/{i}" not in decided
                ),
                repeated=parse.repeated,
                struck=parse.struck,
                unparsed=parse.unparsed,
            )
        )
    return tuple(rows)


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
