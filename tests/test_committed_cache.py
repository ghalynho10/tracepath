"""The test run's memo of `committed_units` returns what a fresh build returns."""

import shutil
from pathlib import Path

from tests.committed_cache import fingerprint, uncached_rebuild
from tracepath.artifacts import RUNS_DIR
from tracepath.rebuild import committed_units

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"


def test_the_memoised_result_equals_a_fresh_build_of_the_real_corpus(
    real_corpus_root: Path, tmp_path: Path
) -> None:
    """The memo holds the same units as a real rebuild, and its key moves with each input."""
    with uncached_rebuild():
        fresh = committed_units(real_corpus_root, SNAPSHOT)

    memoised = committed_units(ROOT, SNAPSHOT)

    assert fresh, "the real corpus holds committed units"
    assert memoised == fresh
    assert committed_units(real_corpus_root, SNAPSHOT) is memoised

    plain = fingerprint(ROOT, SNAPSHOT, code_pass=False)
    assert fingerprint(real_corpus_root, SNAPSHOT, code_pass=False) == plain
    assert fingerprint(ROOT, SNAPSHOT, code_pass=True) != plain
    edited = tmp_path / "edited"
    shutil.copytree(real_corpus_root / RUNS_DIR, edited / RUNS_DIR)
    first_run = sorted((edited / RUNS_DIR).glob("*/*/run-*.json"))[0]
    first_run.write_bytes(first_run.read_bytes() + b" ")
    assert fingerprint(edited, SNAPSHOT, code_pass=False) != plain
