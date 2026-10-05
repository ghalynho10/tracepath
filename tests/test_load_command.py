"""The `load` command, against a real Neo4j (spec 0004 AC-15, AC-16, AC-19, AC-44, AC-50).

Every command here runs over a copy of committed artifacts under `tmp_path`, so the
repository's own `artifacts/graph-build.json` is never rewritten by a test.
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tracepath.artifacts import GRAPH_BUILD, RUNS_DIR
from tracepath.cli import app
from tracepath.config import Neo4jSettings
from tracepath.extract.schema import RelationshipType
from tracepath.graph import connect
from tracepath.graph.load import write_links, write_records
from tracepath.graph.schema import clear, constraint_names, create_constraints

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"

runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


def root_with(tmp_path: Path, *units: str) -> Path:
    for unit in units:
        shutil.copytree(ROOT / RUNS_DIR / unit, tmp_path / RUNS_DIR / unit)
    return tmp_path


def run_load(root: Path, env: dict[str, str | None] | None = None) -> tuple[int, str, str]:
    result = runner.invoke(app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT)], env=env)
    return result.exit_code, result.stdout, result.stderr


@pytest.fixture
def driver(neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    with connect(neo4j_settings) as opened:
        yield opened
        clear(opened, neo4j_settings.database)


@pytest.fixture(scope="module")
def corpus_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of every committed unit's runs, so the repository's manifest is untouched."""
    root = tmp_path_factory.mktemp("corpus")
    shutil.copytree(ROOT / RUNS_DIR, root / RUNS_DIR)
    return root


@pytest.fixture
def whole_corpus(corpus_root: Path, neo4j_settings: Neo4jSettings) -> Iterator[Driver]:
    """The whole committed corpus in the graph, loaded through the command.

    Loaded once and reused while the graph still holds it: another test's load or
    clear replaces it, and then it is loaded again rather than read stale.
    """
    with connect(neo4j_settings) as opened:
        manifest = corpus_root / GRAPH_BUILD
        expected = (
            sum(u["accepted_entities"] for u in json.loads(manifest.read_text())["units"])
            if manifest.exists()
            else -1
        )
        found, _, _ = opened.execute_query(
            "MATCH (e:Entity) RETURN count(e) AS n", database_=neo4j_settings.database
        )
        if found[0]["n"] != expected:
            code, _, stderr = run_load(corpus_root)
            assert code == 0, stderr
        yield opened


# AC-15: the graph is cleared, the constraints made, and every unit loaded.


def test_load_clears_the_graph_first_and_creates_the_constraints(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    driver.execute_query("CREATE (:Stray {canonical_id: 'stray'})", database_=database)
    root = root_with(tmp_path, "0014/requirements")

    code, stdout, stderr = run_load(root)

    assert code == 0, stderr
    stray, _, _ = driver.execute_query("MATCH (n:Stray) RETURN count(n) AS n", database_=database)
    assert stray[0]["n"] == 0
    assert {"entity_canonical_id_unique", "record_canonical_id_unique"} <= constraint_names(
        driver, database
    )
    assert "Loaded 1 units" in flat(stdout)


def test_load_writes_the_manifest_under_the_root_it_was_given(tmp_path: Path) -> None:
    root = root_with(tmp_path, "0014/requirements")

    code, stdout, _ = run_load(root)

    assert code == 0
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    assert [u["record"] for u in manifest["units"]] == ["0014"]
    assert "artifacts/graph-build.json" in stdout


# AC-19: a mix of prompt versions is counted and loaded, never refused.


def test_load_over_two_prompt_versions_prints_each_count_and_loads_both(tmp_path: Path) -> None:
    root = root_with(tmp_path, "0001/binding-rules", "0014/requirements")

    code, stdout, stderr = run_load(root)

    assert code == 0, stderr
    assert "Units per prompt version: 0002.3: 1, 0003.1: 1." in flat(stdout)


# AC-16 and AC-50, read back from the whole committed corpus.


def test_every_typed_relationship_carries_prompt_version_model_and_commit(
    whole_corpus: Driver, corpus_root: Path, neo4j_settings: Neo4jSettings
) -> None:
    driver = whole_corpus
    rows, _, _ = driver.execute_query(
        "MATCH ()-[r]->() WHERE type(r) <> 'PART_OF' "
        "RETURN count(r) AS all, "
        "count(CASE WHEN r.prompt_version IS NULL OR r.model IS NULL OR r.commit IS NULL "
        "THEN 1 END) AS missing",
        database_=neo4j_settings.database,
    )

    assert rows[0]["all"] > 0
    assert rows[0]["missing"] == 0


def test_a_link_carries_the_prompt_version_of_the_unit_it_was_written_in(
    whole_corpus: Driver, corpus_root: Path, neo4j_settings: Neo4jSettings
) -> None:
    driver = whole_corpus
    """The committed units span three prompt versions, so a single stamp would show."""
    manifest = json.loads((corpus_root / GRAPH_BUILD).read_text())
    by_section = {(u["record"], u["section"]): u["prompt_version"] for u in manifest["units"]}
    rows, _, _ = driver.execute_query(
        "MATCH ()-[r]->() WHERE type(r) <> 'PART_OF' "
        "RETURN r.source_record AS record, r.section AS section, r.prompt_version AS version",
        database_=neo4j_settings.database,
    )

    assert {row["version"] for row in rows} > {"0003.1"}
    for row in rows:
        assert row["version"] == by_section[(row["record"], row["section"])]


def test_every_located_entity_carries_its_file_line(
    whole_corpus: Driver, corpus_root: Path, neo4j_settings: Neo4jSettings
) -> None:
    driver = whole_corpus
    rows, _, _ = driver.execute_query(
        "MATCH (e:Entity {file: $file, section: 'Requirements'}) "
        "WHERE e.line IS NOT NULL RETURN e.line AS line, e.file_line AS file_line",
        file="specs/0014-apply-redirect-and-application-record/index.md",
        database_=neo4j_settings.database,
    )

    assert rows
    assert all(row["file_line"] == 19 + row["line"] - 1 for row in rows)


def test_records_and_part_of_links_carry_no_model_provenance(
    whole_corpus: Driver, corpus_root: Path, neo4j_settings: Neo4jSettings
) -> None:
    driver = whole_corpus
    rows, _, _ = driver.execute_query(
        "MATCH (e)-[p:PART_OF]->(r:Record) "
        "RETURN count(CASE WHEN p.prompt_version IS NOT NULL OR r.prompt_version IS NOT NULL "
        "THEN 1 END) AS stamped",
        database_=neo4j_settings.database,
    )

    assert rows[0]["stamped"] == 0


# AC-16: two same type links between one pair collapse, and the last write wins.


def test_two_same_type_links_between_one_pair_become_one_relationship_set_by_the_last(
    driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    clear(driver, database)
    create_constraints(driver, database)
    write_records(
        driver,
        database,
        [{"canonical_id": c, "kind": "spec", "path": f"{c}.md", "commit": "x"} for c in "ab"],
    )
    rows = [
        {
            "from_id": "a",
            "to_id": "b",
            "properties": {"file": f, "section": s, "line": n, "prompt_version": v},
        }
        for f, s, n, v in (
            ("one.md", "Requirements", 10, "0003.0"),
            ("two.md", "Build plan", 40, "0003.1"),
        )
    ]

    written = write_links(driver, database, {RelationshipType.VERIFIES: rows})

    assert written == 2, "each row is matched, so the row count assertion still holds"
    found, _, _ = driver.execute_query(
        "MATCH ({canonical_id: 'a'})-[r:VERIFIES]->({canonical_id: 'b'}) "
        "RETURN r.file AS file, r.section AS section, r.line AS line, r.prompt_version AS v",
        database_=database,
    )
    assert [dict(row) for row in found] == [
        {"file": "two.md", "section": "Build plan", "line": 40, "v": "0003.1"}
    ]


# AC-44: every typed failure is a message and exit 1, never a traceback.


def test_load_with_no_artifacts_names_the_directory_it_looked_in(tmp_path: Path) -> None:
    code, stdout, stderr = run_load(tmp_path)

    assert code == 1
    assert str(tmp_path / RUNS_DIR) in flat(stderr)
    assert "Traceback" not in stderr + stdout


def test_load_when_neo4j_is_down_says_how_to_start_it(tmp_path: Path) -> None:
    root = root_with(tmp_path, "0014/requirements")

    code, stdout, stderr = run_load(root, env={"NEO4J_URI": UNREACHABLE_URI})

    assert code == 1
    assert "docker compose up -d" in flat(stderr)
    assert "Traceback" not in stderr + stdout
    assert not (root / GRAPH_BUILD).exists(), "a failed load writes no manifest"


def test_load_over_runs_that_mix_prompt_versions_refuses_before_touching_the_graph(
    tmp_path: Path, driver: Driver, neo4j_settings: Neo4jSettings
) -> None:
    database = neo4j_settings.database
    driver.execute_query("CREATE (:Stray {canonical_id: 'kept'})", database_=database)
    root = root_with(tmp_path, "0014/requirements")
    run_2 = root / RUNS_DIR / "0014" / "requirements" / "run-2.json"
    payload = json.loads(run_2.read_text())
    payload["prompt_version"] = "0002.3"
    run_2.write_text(json.dumps(payload))

    code, stdout, stderr = run_load(root)

    assert code == 1
    assert "prompt versions" in flat(stderr)
    assert "Traceback" not in stderr + stdout
    kept, _, _ = driver.execute_query("MATCH (n:Stray) RETURN count(n) AS n", database_=database)
    assert kept[0]["n"] == 1, "the refused load left the previous graph standing"
