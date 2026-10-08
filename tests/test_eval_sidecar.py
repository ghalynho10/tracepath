"""The sidecar `eval/runner.json`, the evidence lines and the `examples/` digest (spec 0006
AC-8c, AC-18 to AC-21). No Neo4j: every command here stops before the graph is read.
"""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tracepath.cli import app
from tracepath.report import (
    EVAL_FILE,
    SIDECAR_FILE,
    Evidence,
    SidecarInvalid,
    evidence_line,
    examples_digest,
    read_sidecar,
)

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


# AC-18: the evidence line.


@pytest.mark.parametrize(
    ("level", "words"),
    [("weaker", "weaker"), ("light", "light"), ("none", "no overlap with a worked example")],
)
def test_ac_18_an_evidence_line_names_its_level_then_its_reason(level: str, words: str) -> None:
    """covers: AC-18."""
    evidence = Evidence(level, "the reason")  # type: ignore[arg-type]

    assert evidence_line(evidence) == f"Evidence: {words} · the reason"


def test_ac_18_no_sidecar_entry_reads_not_assessed() -> None:
    """covers: AC-18 (not assessed)."""
    assert evidence_line(None) == "Evidence: not assessed"


# AC-19: the levels as written.


def test_ac_19_the_sidecar_holds_the_levels_spec_0006_set() -> None:
    """covers: AC-19."""
    sidecar = read_sidecar(ROOT, ROOT / EVAL_FILE)

    assert sidecar is not None
    assert {n: q.evidence.level for n, q in sidecar.questions.items()} == {
        1: "light",
        2: "weaker",
        3: "none",
        4: "light",
        5: "weaker",
    }


# AC-20: the digest of `examples/`.


def test_ac_20_the_examples_digest_matches_the_one_the_sidecar_recorded() -> None:
    """covers: AC-20."""
    sidecar = read_sidecar(ROOT, ROOT / EVAL_FILE)
    assert sidecar is not None

    assert examples_digest(ROOT) == sidecar.examples_sha256, (
        "examples/ changed since eval/runner.json's evidence flags were written: re-check "
        "each question's flag against the examples, then record the new examples_sha256"
    )


def git_root(tmp_path: Path, files: dict[str, bytes]) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name, data in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    return tmp_path


def test_ac_20_the_digest_is_the_one_its_definition_gives(tmp_path: Path) -> None:
    """covers: AC-20 (path relative to examples/, NUL, length, NUL, bytes, sorted)."""
    root = git_root(tmp_path, {"examples/b.md": b"two", "examples/a.md": b"one!"})

    expected = hashlib.sha256(b"a.md\x004\x00one!" + b"b.md\x003\x00two").hexdigest()

    assert examples_digest(root) == expected


def test_ac_20_one_changed_byte_changes_the_digest(tmp_path: Path) -> None:
    """covers: AC-20 (a drifted example is caught)."""
    root = git_root(tmp_path, {"examples/a.md": b"one"})
    before = examples_digest(root)

    (root / "examples" / "a.md").write_bytes(b"onE")

    assert examples_digest(root) != before


def test_ac_20_a_file_git_does_not_track_is_left_out(tmp_path: Path) -> None:
    """covers: AC-20 (`git ls-files examples/` only)."""
    root = git_root(tmp_path, {"examples/a.md": b"one"})
    before = examples_digest(root)

    (root / "examples" / "scratch.md").write_bytes(b"not tracked")

    assert examples_digest(root) == before


def test_outside_a_git_work_tree_there_is_no_digest(tmp_path: Path) -> None:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "a.md").write_text("one")

    assert examples_digest(tmp_path) is None


# Reading the sidecar, and AC-8c's failures.


def write_sidecar(root: Path, text: str) -> None:
    path = root / SIDECAR_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_a_missing_sidecar_is_not_assessed(tmp_path: Path) -> None:
    """covers: AC-8c (a missing file is not a failure)."""
    assert read_sidecar(tmp_path, tmp_path / EVAL_FILE) is None


def test_a_sidecar_with_no_entry_for_the_eval_file_is_not_assessed(tmp_path: Path) -> None:
    write_sidecar(tmp_path, json.dumps({"other.json": {"examples_sha256": "x", "questions": {}}}))

    assert read_sidecar(tmp_path, tmp_path / EVAL_FILE) is None


@pytest.mark.parametrize(
    "text",
    [
        "{not json",
        json.dumps({EVAL_FILE.name: {"examples_sha256": "x", "questions": {"1": {}}}}),
        json.dumps(
            {
                EVAL_FILE.name: {
                    "examples_sha256": "x",
                    "questions": {"1": {"evidence": "strong", "reason": "r"}},
                }
            }
        ),
    ],
    ids=["bad JSON", "no level", "unknown level"],
)
def test_a_malformed_sidecar_raises(tmp_path: Path, text: str) -> None:
    """covers: AC-8c (a malformed `eval/runner.json`)."""
    write_sidecar(tmp_path, text)

    with pytest.raises(SidecarInvalid):
        read_sidecar(tmp_path, tmp_path / EVAL_FILE)


def test_ac_8c_eval_with_a_malformed_sidecar_exits_1_before_any_question(tmp_path: Path) -> None:
    """covers: AC-8c (stderr, exit 1, no question, no traceback, no graph read)."""
    (tmp_path / "eval").mkdir()
    shutil.copy(ROOT / EVAL_FILE, tmp_path / EVAL_FILE)
    write_sidecar(tmp_path, "{not json")

    result = runner.invoke(
        app, ["eval", "--root", str(tmp_path)], env={"NEO4J_URI": UNREACHABLE_URI}
    )

    assert result.exit_code == 1
    assert "eval/runner.json cannot be used" in flat(result.stderr)
    assert result.stdout == ""
    assert "Traceback" not in result.stdout + result.stderr


def test_ac_8c_eval_with_an_unreadable_eval_file_exits_1_before_any_question(
    tmp_path: Path,
) -> None:
    """covers: AC-8c (an unreadable eval file)."""
    result = runner.invoke(
        app, ["eval", "--root", str(tmp_path)], env={"NEO4J_URI": UNREACHABLE_URI}
    )

    assert result.exit_code == 1
    assert "cannot be read" in flat(result.stderr)
    assert result.stdout == ""


@pytest.mark.parametrize(
    "payload", [[], {}, {"entries": {}}], ids=["a list", "no entries", "entries not a list"]
)
def test_ac_8c_eval_with_an_eval_file_holding_no_entries_list_exits_1_before_any_question(
    tmp_path: Path, payload: object
) -> None:
    """covers: AC-8c (an eval file that is JSON but not in the eval file's shape)."""
    (tmp_path / "eval").mkdir()
    (tmp_path / EVAL_FILE).write_text(json.dumps(payload))

    result = runner.invoke(
        app, ["eval", "--root", str(tmp_path)], env={"NEO4J_URI": UNREACHABLE_URI}
    )

    assert result.exit_code == 1
    assert "holds no `entries` list" in flat(result.stderr)
    assert result.stdout == ""


def test_ac_8c_eval_with_an_unreachable_graph_exits_1_before_any_question(tmp_path: Path) -> None:
    """covers: AC-8c (`GraphUnavailable`)."""
    (tmp_path / "eval").mkdir()
    shutil.copy(ROOT / EVAL_FILE, tmp_path / EVAL_FILE)

    result = runner.invoke(
        app, ["eval", "--root", str(tmp_path)], env={"NEO4J_URI": UNREACHABLE_URI}
    )

    assert result.exit_code == 1
    assert result.stderr.strip()
    assert result.stdout == ""
    assert "Traceback" not in result.stdout + result.stderr
