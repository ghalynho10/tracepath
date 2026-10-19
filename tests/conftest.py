"""Shared fixtures. Integration tests use the real Neo4j from `docker compose up -d`."""

import logging
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.committed_cache import install, uncached_rebuild, uninstall
from tracepath.artifacts import RUNS_DIR
from tracepath.config import Neo4jSettings, load_neo4j_settings
from tracepath.graph import GraphUnavailable, connect

ROOT = Path(__file__).resolve().parents[1]

# Nothing listens on port 1, so connecting there fails for real, with no mock.
UNREACHABLE_URI = "bolt://localhost:1"

#: The key and API address every test runs with (spec 0004 AC-74). Nothing listens on
#: port 1, so a test that forgot to point at the fake API fails instead of spending.
FAKE_API_KEY = "sk-ant-test"
UNREACHABLE_API = "http://localhost:1"

#: Feature 9 moved 26 units' runs here. With the three units it left in place, they are
#: `artifacts/runs/` as it stood before (`b65819f^`), byte for byte: the 29 unit corpus
#: that tests pinned to earlier experiments read, as frozen data.
SUPERSEDED_BY_FEATURE_9 = ROOT / "artifacts" / "superseded" / "2026-10-18-claude-sonnet-5"
KEPT_BY_FEATURE_9 = ("0009/requirements", "0013/requirements", "0015/requirements")


def pre_feature_9_runs(root: Path, *units: str) -> Path:
    """`root` holding the named units' runs as they stood before feature 9, or all 29.

    A unit is a record (`0002`) or a record and section slug (`0001/binding-rules`).
    """
    for unit in units or ("",):
        source = SUPERSEDED_BY_FEATURE_9 / unit
        if source.exists():
            skip = shutil.ignore_patterns("NOTE.md", "*-before-fix")
            shutil.copytree(source, root / RUNS_DIR / unit, ignore=skip, dirs_exist_ok=True)
        for kept in KEPT_BY_FEATURE_9:
            if not unit or kept == unit or kept.startswith(f"{unit}/"):
                shutil.copytree(ROOT / RUNS_DIR / kept, root / RUNS_DIR / kept)
    return root


@pytest.fixture(autouse=True)
def no_real_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test runs with a fake key and an unreachable API (spec 0004 AC-74).

    The developer's `.env` holds a real key and `config.py` loads `.env` on every
    settings read. `load_dotenv()` never replaces a variable already set, so setting
    these first means the real key cannot load in a test, while `.env` still supplies
    the Neo4j settings the integration tests need. A test that uses the fake API sets
    its own base URL.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_API_KEY)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", UNREACHABLE_API)


@pytest.fixture(scope="session")
def neo4j_settings() -> Neo4jSettings:
    """Settings for the running Neo4j; fails loudly if it is not up."""
    settings = load_neo4j_settings()
    try:
        connect(settings).close()
    except GraphUnavailable as exc:
        pytest.fail(f"Integration tests need Neo4j: {exc}")
    return settings


@pytest.fixture(autouse=True)
def reset_tracepath_log_level() -> Iterator[None]:
    """`--debug` raises the tracepath logger level; undo it so tests stay independent."""
    logger = logging.getLogger("tracepath")
    level = logger.level
    yield
    logger.setLevel(level)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Memoise `committed_units` once every test module has imported it."""
    install()


def pytest_unconfigure(config: pytest.Config) -> None:
    """Put the real `committed_units` back."""
    uninstall()


@pytest.fixture(autouse=True)
def rebuild_cache_mode(request: pytest.FixtureRequest) -> Iterator[None]:
    """A test marked `uncached_rebuild` gets the real rebuild, never the memo."""
    if request.node.get_closest_marker("uncached_rebuild") is None:
        yield
        return
    with uncached_rebuild():
        yield


@pytest.fixture(scope="session")
def real_corpus_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One copy of the committed run files for the whole test run, read only by its users."""
    root = tmp_path_factory.mktemp("real_corpus")
    shutil.copytree(ROOT / RUNS_DIR, root / RUNS_DIR)
    return root
