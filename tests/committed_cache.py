"""An in memory memo around `committed_units` for one test run, never written to disk.

`committed_units()` re-identifies every run file, about 35 s over the real corpus, and
dozens of tests asked for the same answer from the same bytes. The memo is keyed by the
bytes of the run files it reads, the snapshot's files (path, size, modified time) and the
`code_pass` flag, so a test that edits a run file or builds another root gets its own
build. A call that raises is never stored. A test that checks the rebuild itself is
repeatable asks for the real one with `@pytest.mark.uncached_rebuild` or
`uncached_rebuild()`.
"""

import hashlib
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from tracepath import rebuild
from tracepath.artifacts import RUNS_DIR
from tracepath.pipeline import UnitResult

CommittedUnits = Callable[..., tuple[UnitResult, ...]]


def fingerprint(root: Path, snapshot: Path, code_pass: bool) -> str:
    """What `committed_units()` reads, as one hash: the settled run files and the snapshot."""
    digest = hashlib.sha256()
    runs = root / RUNS_DIR
    for path in sorted(runs.glob("*/*/run-*.json")):
        digest.update(path.relative_to(runs).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    found = snapshot.rglob("*") if snapshot.is_dir() else iter((snapshot,))
    files = sorted(p for p in found if p.is_file())
    for path in files:
        stat = path.stat()
        name = path.name if path == snapshot else path.relative_to(snapshot).as_posix()
        digest.update(f"{name}\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
    digest.update(b"code_pass\0" if code_pass else b"plain\0")
    return digest.hexdigest()


@dataclass
class RebuildMemo:
    """The memo: `original` is the real `committed_units`, called on a miss or a bypass."""

    original: CommittedUnits
    bypass: bool = False
    entries: dict[str, tuple[UnitResult, ...]] = field(default_factory=dict)
    calls: int = 0

    def __call__(
        self, root: Path, snapshot: Path, *, code_pass: bool = False
    ) -> tuple[UnitResult, ...]:
        """The memoised `committed_units()`; the real one when bypassed."""
        if self.bypass:
            return self.original(root, snapshot, code_pass=code_pass)
        key = fingerprint(root, snapshot, code_pass)
        if key not in self.entries:
            self.calls += 1
            self.entries[key] = self.original(root, snapshot, code_pass=code_pass)
        return self.entries[key]


@dataclass
class Installed:
    """The memo in place, and every module attribute that now holds it."""

    memo: RebuildMemo
    patched: list[tuple[object, str]] = field(default_factory=list)


@dataclass
class Active:
    """Holds the installed memo, so a context manager can reach it."""

    installed: Installed | None = None


ACTIVE = Active()


def install() -> Installed:
    """Replace `committed_units` everywhere it was imported by name, once per test run."""
    original = rebuild.committed_units
    installed = Installed(memo=RebuildMemo(original=original))
    for module in list(sys.modules.values()):
        for name, value in list(getattr(module, "__dict__", {}).items()):
            if value is original:
                setattr(module, name, installed.memo)
                installed.patched.append((module, name))
    ACTIVE.installed = installed
    return installed


def uninstall() -> None:
    """Put the real `committed_units` back where `install()` found it."""
    installed = ACTIVE.installed
    if installed is None:
        return
    for module, name in installed.patched:
        setattr(module, name, installed.memo.original)
    ACTIVE.installed = None


@contextmanager
def uncached_rebuild() -> Iterator[None]:
    """Inside the block, `committed_units()` is the real one: no read from the memo, no write."""
    installed = ACTIVE.installed
    if installed is None:
        yield
        return
    before = installed.memo.bypass
    installed.memo.bypass = True
    try:
        yield
    finally:
        installed.memo.bypass = before
