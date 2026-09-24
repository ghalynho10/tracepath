"""The rebuild path, and how it refuses when the committed artifacts cannot be replayed.

Spec 0001 makes the JSON run artifacts the source of truth and the graph derived and
disposable. That claim rests on there being a real path from the files back to a run,
so `test_reload_artifacts.py` drives that path against the whole committed run. It
needs Neo4j, and it only ever walks the happy path.

These cover what that test never reaches: the three ways a rebuild can fail, and the
one number a rebuild deliberately refuses to recover. The standing rule here is that a
real failure raises a typed exception and the CLI turns it into a clear message and
exit code 1, never a raw traceback. A `RebuildFailed` that does not name what is
missing leaves the reader nothing to act on, so each test asserts the message too.

Nothing here calls the API or the database, and nothing here writes into the committed
artifacts: every case builds its own root under `tmp_path`.
"""

import dataclasses
import shutil
from pathlib import Path

import pytest

from tracepath.artifacts import RUNS_DIR, RunArtifact, read_run, write_run
from tracepath.rebuild import RebuildFailed, committed_units, unit_for

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"

#: The smallest committed unit, so a rebuild in a test stays cheap. Re-aligning every
#: span of every run is the expensive part, and one unit proves the same path as eight.
UNIT = Path("0012") / "requirements"
UNIT_FILE = "specs/0012-model-client-router/index.md"


@pytest.fixture
def one_unit_root(tmp_path: Path) -> Path:
    """A repository root holding one unit's three run artifacts and nothing else."""
    destination = tmp_path / RUNS_DIR / UNIT
    destination.parent.mkdir(parents=True)
    shutil.copytree(ROOT / RUNS_DIR / UNIT, destination)
    return tmp_path


def an_artifact() -> RunArtifact:
    """One real committed artifact, read back through the real reader."""
    return read_run(ROOT / RUNS_DIR / UNIT / "run-1.json")


def test_a_root_holding_no_run_artifacts_names_the_directory_it_looked_in(
    tmp_path: Path,
) -> None:
    """Saying nothing can be rebuilt is useless alone; the path is the actionable part."""
    with pytest.raises(RebuildFailed) as caught:
        committed_units(tmp_path, SNAPSHOT)

    assert str(tmp_path / RUNS_DIR) in str(caught.value)


def test_a_unit_whose_file_left_the_snapshot_names_the_record_that_cannot_be_rebuilt(
    tmp_path: Path,
) -> None:
    """The snapshot is pinned and read only, so this means the pin moved under us."""
    with pytest.raises(RebuildFailed) as caught:
        unit_for(an_artifact(), tmp_path)

    message = str(caught.value)
    assert UNIT_FILE in message
    assert "0012" in message


def test_a_file_that_no_longer_holds_the_section_says_which_section_went_missing(
    tmp_path: Path,
) -> None:
    """The file surviving while the section does not is the subtler half of the same
    failure, and the two need telling apart: one means the document moved, the other
    means it was edited. A snapshot that is still read only should produce neither."""
    stand_in = tmp_path / UNIT_FILE
    stand_in.parent.mkdir(parents=True)
    stand_in.write_text("# 0012 Model client router\n\n## Consequences\n\nNothing here.\n")

    with pytest.raises(RebuildFailed) as caught:
        unit_for(an_artifact(), tmp_path)

    message = str(caught.value)
    assert "Requirements" in message
    assert "0012" in message


def test_a_rebuilt_unit_reports_zero_tokens_because_that_cost_was_only_paid_once(
    one_unit_root: Path,
) -> None:
    """A rebuild recovers everything except what the original calls cost.

    The committed artifacts predate the token fields and read back as null, so summing
    them here would be inventing a number. Adding up a rebuilt run's spend would also
    double count a cost paid once, by the run that made the calls. Zero is the value
    that says "this run spent nothing", which is true of a rebuild.
    """
    results = committed_units(one_unit_root, SNAPSHOT)

    assert len(results) == 1
    assert results[0].input_tokens == 0
    assert results[0].output_tokens == 0


def test_a_failed_attempt_beside_a_settled_run_is_not_rebuilt_as_a_fourth_run(
    one_unit_root: Path,
) -> None:
    """The naming rule of spec 0001, proven where it actually matters.

    `test_artifacts.py` proves the glob does not match the name. This proves the
    rebuild agrees: a unit is three runs, and a failure sitting beside them must not
    quietly become a fourth, because the count of three per unit is what the
    durability claim rests on.
    """
    failed = dataclasses.replace(
        an_artifact(), attempt=1, output=None, error="attempt 1 did not satisfy the schema"
    )
    written = write_run(one_unit_root, failed)

    assert written.name == "failed-run-1-attempt-1.json", "the writer must use the failed name"

    results = committed_units(one_unit_root, SNAPSHOT)

    assert len(results) == 1
    assert len(results[0].artifacts) == 3, "three settled runs, and the failure is not one of them"
