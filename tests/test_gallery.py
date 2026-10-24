"""The answer gallery build (spec 0010): what the page shows and what the build touches."""

import json
import re
import shutil
import socket
from html import escape
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.records import MARKS_FILE

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Two real records: eval question 1 at 2 hops, and one realistic question.
SHOWN = "2026-10-20T17-36-09Z-eval-linked-records-research-q1.json"
OTHER = "2026-10-22T20-24-07Z-what-did-we-decide-about.json"

runner = CliRunner()


def _stored(name: str) -> dict[str, object]:
    data = json.loads((PROJECT_ROOT / ASKS_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root with two records and a marks file naming only the first."""
    asks = tmp_path / ASKS_DIR
    asks.mkdir(parents=True)
    for name in (SHOWN, OTHER):
        shutil.copy(PROJECT_ROOT / ASKS_DIR / name, asks / name)
    marks = tmp_path / MARKS_FILE
    marks.parent.mkdir()
    marks.write_text(json.dumps([{"record": SHOWN}]), encoding="utf-8")
    (tmp_path / "corpus").mkdir()
    return tmp_path


def _build(root: Path, out: Path) -> str:
    result = runner.invoke(app, ["gallery", "build", "--out", str(out), "--root", str(root)])
    assert result.exit_code == 0, result.output
    return (out / "index.html").read_text(encoding="utf-8")


def test_build_writes_index_html_and_exits_0(root: Path, tmp_path: Path) -> None:
    """AC-55."""
    result = runner.invoke(
        app, ["gallery", "build", "--out", str(tmp_path / "site"), "--root", str(root)]
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "site" / "index.html").is_file()
    assert "1 entries" in result.output


def test_page_shows_only_the_records_the_marks_file_names(root: Path, tmp_path: Path) -> None:
    """AC-1."""
    page = _build(root, tmp_path / "site")

    assert page.count("<article>") == 1
    assert str(_stored(OTHER)["question"])[:40] not in page


def test_entry_shows_question_verdict_and_claims_in_order(root: Path, tmp_path: Path) -> None:
    """AC-17, AC-18, AC-19: stored text as stored, escaped."""
    page = _build(root, tmp_path / "site")
    record = _stored(SHOWN)
    claims = record["claims"]
    assert isinstance(claims, list)

    assert escape(str(record["question"])) in page
    assert f'Model\'s verdict: <span class="stored">{record["verdict"]}</span>' in page
    places = [page.index(escape(str(claim["text"]))) for claim in claims]
    assert places == sorted(places)
    assert len(places) == len(claims) > 0


def test_build_makes_no_network_call(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-56: the build still passes with every socket refused."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the gallery build opened a socket")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    _build(root, tmp_path / "site")


def _files(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    } | {p.relative_to(folder).as_posix(): b"" for p in folder.rglob("*") if p.is_dir()}


def test_build_writes_nothing_under_artifacts_or_corpus(root: Path, tmp_path: Path) -> None:
    """AC-57."""
    before = {d: _files(root / d) for d in ("artifacts", "corpus")}

    _build(root, tmp_path / "site")

    assert {d: _files(root / d) for d in ("artifacts", "corpus")} == before


@pytest.mark.parametrize("inside", ["artifacts", "artifacts/asks/site", "corpus/site"])
def test_build_refuses_an_out_folder_inside_artifacts_or_corpus(root: Path, inside: str) -> None:
    """AC-57: an --out inside a read only folder exits 1 before writing."""
    result = runner.invoke(
        app, ["gallery", "build", "--out", str(root / inside), "--root", str(root)]
    )

    assert result.exit_code == 1
    assert "never writes inside" in result.output
    assert not (root / inside / "index.html").exists()


def test_page_is_self_contained(root: Path, tmp_path: Path) -> None:
    """AC-58: inline styles, no stylesheet, script or other file of the site."""
    page = _build(root, tmp_path / "site")

    assert "<style>" in page
    assert "<link" not in page
    assert "<script" not in page
    assert not re.search(r'\b(src|href)="(?!https://|#)', page)


def test_build_from_the_committed_marks_file(tmp_path: Path) -> None:
    """AC-1, AC-55 on the real data: one entry per marks entry."""
    marks = json.loads((PROJECT_ROOT / MARKS_FILE).read_text(encoding="utf-8"))

    page = _build(PROJECT_ROOT, tmp_path / "site")

    assert page.count("<article>") == len(marks) > 0
