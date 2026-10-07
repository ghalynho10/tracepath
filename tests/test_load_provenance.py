"""Link provenance, entity file lines, the collapse count and the build manifest.

Spec 0004 build plan steps 2 and 3, the parts that need no database: every row the
load writes is settled here, before the first write, so each is checked as a value.
The rows are built from real committed units, rebuilt with no API call.
"""

import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from neo4j import Driver

from tracepath.artifacts import RUNS_DIR, read_run, write_graph_build
from tracepath.extract.schema import RelationshipType
from tracepath.graph.model import Provenance, entity_row, link_row
from tracepath.pipeline import (
    CorpusResolution,
    ProvenanceMismatch,
    UnitResult,
    collapsed_links,
    graph_build,
    link_provenances,
    load,
    resolve_accepted,
    unit_provenance,
)
from tracepath.rebuild import committed_units, partial_units, records_for_units, unit_passes
from tracepath.resolve.endpoints import (
    Resolution,
    ResolvedEndpoint,
    ResolvedLink,
    Target,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"

#: No database is touched before every row is settled, so a refused load never needs
#: one. Anything that did reach for it would fail loudly on this stand in.
NO_DRIVER = cast("Driver", object())


@pytest.fixture(scope="module")
def unit_0014() -> UnitResult:
    """`0014 ## Requirements`, which starts at file line 19 (spec 0004 AC-50)."""
    root = Path(__file__).resolve().parents[1]
    return next(r for r in committed_units(root, SNAPSHOT) if r.unit.record_id == "0014")


def two_unit_root(tmp_path: Path, *units: str) -> Path:
    """A repository root holding copies of the named committed units' runs."""
    for unit in units:
        shutil.copytree(ROOT / RUNS_DIR / unit, tmp_path / RUNS_DIR / unit)
    return tmp_path


def a_link(file: str, section: str, source: str = "a", target: str = "b") -> ResolvedLink:
    return ResolvedLink(
        type=RelationshipType.VERIFIES,
        source=ResolvedEndpoint(canonical_id=source, target=Target.ENTITY),
        target=ResolvedEndpoint(canonical_id=target, target=Target.ENTITY),
        phrase=None,
        date=None,
        source_record="0014",
        file=file,
        section=section,
        line=19,
    )


# AC-50: `file_line` is the line in the source file; `line` stays section relative.


def test_an_entity_file_line_counts_from_the_top_of_its_file(unit_0014: UnitResult) -> None:
    provenance = unit_provenance(unit_0014, "auto")
    located = [e for e in unit_0014.routed.accepted_entities if e.location is not None]
    assert unit_0014.unit.start_line == 19

    rows = [entity_row(e, unit_0014.unit, COMMIT, provenance) for e in located]

    assert rows, "0014 Requirements should hold located entities"
    for row in rows:
        assert row["file_line"] == 19 + row["line"] - 1


def test_the_first_0014_entities_land_on_file_lines_23_24_and_25(unit_0014: UnitResult) -> None:
    """The spec's own worked check: section lines 5, 6 and 7 are file lines 23 to 25."""
    provenance = unit_provenance(unit_0014, "auto")
    rows = [
        entity_row(e, unit_0014.unit, COMMIT, provenance)
        for e in unit_0014.routed.accepted_entities
    ]
    by_line = {row.get("line"): row.get("file_line") for row in rows}

    assert {line: by_line[line] for line in (5, 6, 7)} == {5: 23, 6: 24, 7: 25}


def test_an_unlocated_entity_has_neither_line_nor_file_line(unit_0014: UnitResult) -> None:
    entity = replace(unit_0014.routed.accepted_entities[0], location=None)

    row = entity_row(entity, unit_0014.unit, COMMIT, unit_provenance(unit_0014, "auto"))

    assert "line" not in row
    assert "file_line" not in row


# AC-16: every link carries the provenance of the unit it was written in.


def test_a_link_row_carries_prompt_version_model_and_commit() -> None:
    provenance = Provenance(
        model="claude-sonnet-5",
        prompt_version="0003.1",
        extracted_at="2026-10-05T00:00:00+00:00",
        accepted_by="auto",
        commit="2e40bcf",
    )

    row = link_row(a_link("specs/x/index.md", "Requirements"), provenance)

    assert row["properties"]["prompt_version"] == "0003.1"
    assert row["properties"]["model"] == "claude-sonnet-5"
    assert row["properties"]["commit"] == "2e40bcf"


def test_unit_provenance_reads_the_commit_off_the_units_own_runs(unit_0014: UnitResult) -> None:
    assert unit_provenance(unit_0014, "auto").commit == unit_0014.artifacts[0].commit


def test_runs_that_mix_corpus_commits_raise(unit_0014: UnitResult) -> None:
    first, *rest = unit_0014.artifacts
    mixed = replace(unit_0014, artifacts=(first, *(replace(a, commit="ffffff0") for a in rest)))

    with pytest.raises(ProvenanceMismatch, match="commits"):
        unit_provenance(mixed, "auto")


def test_two_units_sharing_a_section_with_different_provenance_raise(unit_0014: UnitResult) -> None:
    provenance = unit_provenance(unit_0014, "auto")
    other = replace(provenance, prompt_version="0002.3")

    with pytest.raises(ProvenanceMismatch, match="share this section"):
        link_provenances([unit_0014, unit_0014], [provenance, other])


def test_a_link_written_where_no_unit_was_loaded_stops_the_load_before_any_write(
    unit_0014: UnitResult,
) -> None:
    orphan = Resolution(links=(a_link("specs/elsewhere/index.md", "Consequences"),), unresolved=())

    with pytest.raises(ProvenanceMismatch, match="no loaded unit holds"):
        load(NO_DRIVER, "neo4j", [], [unit_0014], orphan, COMMIT, "auto", clear_first=True)


# AC-51: links that collapse into one relationship are counted.


def test_two_same_type_links_between_one_pair_collapse_into_one() -> None:
    links = [
        a_link("specs/x/index.md", "Requirements"),
        a_link("specs/y/index.md", "Feature design"),
        a_link("specs/x/index.md", "Requirements", target="c"),
    ]

    assert collapsed_links(links) == 1


def test_a_link_in_the_opposite_direction_does_not_collapse() -> None:
    links = [a_link("f", "s", "a", "b"), a_link("f", "s", "b", "a")]

    assert collapsed_links(links) == 0


# AC-17a to AC-17c and AC-18: the build manifest.


def manifest_for(root: Path) -> dict[str, object]:
    results = committed_units(root, SNAPSHOT)
    records = records_for_units(results, SNAPSHOT, COMMIT)
    corpus: CorpusResolution = resolve_accepted(results, records)
    provenances = [unit_provenance(r, "auto") for r in results]
    return graph_build(
        results, corpus, provenances, COMMIT, review_log_entries=0, passes=unit_passes(root)
    )


def test_the_manifest_lists_each_units_run_files_model_and_prompt_version(tmp_path: Path) -> None:
    root = two_unit_root(tmp_path, "0001/binding-rules", "0014/requirements")

    manifest = manifest_for(root)

    units = cast("list[dict[str, object]]", manifest["units"])
    assert [(u["record"], u["prompt_version"]) for u in units] == [
        ("0001", "0002.3"),
        ("0014", "0003.1"),
    ]
    assert units[1]["run_files"] == [
        f"artifacts/runs/0014/requirements/run-{n}.json" for n in (1, 2, 3)
    ]
    assert {u["model"] for u in units} == {"claude-sonnet-5"}


@pytest.fixture(scope="module")
def whole_corpus() -> tuple[tuple[UnitResult, ...], CorpusResolution, list[dict[str, object]]]:
    """Every committed unit, rebuilt with no API call, and the manifest built over them."""
    results = committed_units(ROOT, SNAPSHOT)
    corpus = resolve_accepted(results, records_for_units(results, SNAPSHOT, COMMIT))
    units = cast("list[dict[str, object]]", manifest_for(ROOT)["units"])
    return results, corpus, units


def counted(units: list[dict[str, object]], key: str) -> dict[tuple[object, object], object]:
    return {(u["record"], u["section"]): u[key] for u in units}


def test_ac_17b_every_units_held_links_count_links_only(
    whole_corpus: tuple[tuple[UnitResult, ...], CorpusResolution, list[dict[str, object]]],
) -> None:
    """covers: AC-17b (held link count, every committed unit).

    A held link is a review item with a relationship signature (type, source, target),
    plus a link held across units for an endpoint in another unit. A held entity with
    no id is not a link, however it was routed.
    """
    results, corpus, units = whole_corpus
    expected = {
        (r.unit.record_id, r.unit.section): sum(
            1 for item in r.routed.review if len(item.signature) == 3
        )
        + sum(1 for h in corpus.held if (h.record, h.section) == (r.unit.record_id, r.unit.section))
        for r in results
    }

    assert counted(units, "held_links") == expected


def test_ac_17b_every_units_accepted_entity_count(
    whole_corpus: tuple[tuple[UnitResult, ...], CorpusResolution, list[dict[str, object]]],
) -> None:
    """covers: AC-17b (accepted entity count, every committed unit)."""
    results, _, units = whole_corpus
    expected = {
        (r.unit.record_id, r.unit.section): len(r.routed.accepted_entities) for r in results
    }

    assert counted(units, "accepted_entities") == expected


def test_ac_17b_every_units_accepted_link_count(
    whole_corpus: tuple[tuple[UnitResult, ...], CorpusResolution, list[dict[str, object]]],
) -> None:
    """covers: AC-17b (accepted link count: the links the load writes from its section)."""
    results, corpus, units = whole_corpus
    expected = {
        (r.unit.record_id, r.unit.section): sum(
            1
            for k in corpus.resolution.links
            if (k.file, k.section) == (r.unit.path, r.unit.section)
        )
        for r in results
    }

    assert counted(units, "accepted_links") == expected


def test_the_manifest_lists_prompt_versions_and_the_review_log_count(tmp_path: Path) -> None:
    root = two_unit_root(tmp_path, "0001/binding-rules", "0014/requirements")

    manifest = manifest_for(root)

    assert manifest["prompt_versions"] == {"0002.3": 1, "0003.1": 1}
    assert manifest["review_log_entries"] == 0
    assert manifest["corpus_commit"] == COMMIT


def test_two_manifests_over_unchanged_artifacts_are_byte_identical(tmp_path: Path) -> None:
    root = two_unit_root(tmp_path, "0014/requirements")

    first = write_graph_build(root, manifest_for(root)).read_bytes()
    second = write_graph_build(root, manifest_for(root)).read_bytes()

    assert first == second
    # No value from the load's own clock: the only times are the artifacts' own (AC-65).
    recorded = sorted({read_run(p).extracted_at for p in (root / RUNS_DIR).rglob("*.json")})
    assert json.loads(first)["units"][0]["extracted_at"] == recorded


# AC-48: a unit cut short is never loaded and is named instead.


@pytest.mark.parametrize("kept", [1, 2])
def test_a_unit_short_of_its_runs_is_not_rebuilt_but_named(tmp_path: Path, kept: int) -> None:
    root = two_unit_root(tmp_path, "0014/requirements")
    for run in range(kept + 1, 4):
        (root / RUNS_DIR / "0014" / "requirements" / f"run-{run}.json").unlink()

    assert committed_units(root, SNAPSHOT) == ()
    [partial] = partial_units(root)
    assert (partial.record, partial.section, partial.settled_runs) == ("0014", "Requirements", kept)
