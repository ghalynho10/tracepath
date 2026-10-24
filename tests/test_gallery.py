"""The answer gallery build (spec 0010): what the page shows and what the build touches."""

import json
import re
import shutil
import socket
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.citations import JOBHUNT_COMMIT, parse_item_line
from tracepath.gallery.records import MARKS_FILE, SNAPSHOT_DOCS

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Real records, one per section: eval question 1 at 2 hops, held out question 3 and
#: a realistic question; plus a fourth the marks file does not name.
DEV = "2026-10-20T17-36-09Z-eval-linked-records-research-q1.json"
HELD = "2026-10-19T22-17-49Z-eval-held-out-q3.json"
REAL = "2026-10-22T20-24-07Z-what-did-we-decide-about.json"
UNNAMED = "2026-10-22T20-24-13Z-why-does-the-design-system.json"

#: Marks for the fixture, in an order that differs from the page's section order.
MARKS: tuple[dict[str, object], ...] = (
    {
        "record": REAL,
        "label": "Q2",
        "mark": "wrong",
        "note": "A fixture note,\nover two lines.",
        "source_path": "experiments/0018-realistic-usage-questions/README.md",
        "source_row": "Q2",
    },
    {
        "record": DEV,
        "label": "Eval 1",
        "mark": "right",
        "note": None,
        "source_path": "experiments/0016-hops/README.md",
        "source_row": "Q1",
    },
    {
        "record": HELD,
        "label": "Held out 3",
        "mark": "partly right",
        "note": "Retrieval missed one item.",
        "source_path": "docs/scope/scope.md",
        "source_row": "v1 finish line",
    },
)

runner = CliRunner()


def _stored(name: str) -> dict[str, Any]:
    data = json.loads((PROJECT_ROOT / ASKS_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write_marks(root: Path, marks: object) -> None:
    (root / MARKS_FILE).write_text(json.dumps(marks), encoding="utf-8")


def _edit_record(root: Path, name: str, change: Callable[[dict[str, Any]], None]) -> None:
    """Rewrite one fixture record after `change` edits its JSON."""
    path = root / ASKS_DIR / name
    record = json.loads(path.read_text(encoding="utf-8"))
    change(record)
    path.write_text(json.dumps(record), encoding="utf-8")


def _cited_item(record: dict[str, Any]) -> dict[str, Any]:
    """The item the record's first claim cites first."""
    cited = record["claims"][0]["cites"][0]
    item: dict[str, Any] = next(i for i in record["items"] if i["id"] == cited)
    return item


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root with four records, a marks file naming three of them, and the
    snapshot files those records' items sit in."""
    asks = tmp_path / ASKS_DIR
    asks.mkdir(parents=True)
    for name in (DEV, HELD, REAL, UNNAMED):
        shutil.copy(PROJECT_ROOT / ASKS_DIR / name, asks / name)
        for item in _stored(name)["items"]:
            line = parse_item_line(item["line"])
            assert line is not None
            if line.file is not None:
                target = tmp_path / SNAPSHOT_DOCS / line.file
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(PROJECT_ROOT / SNAPSHOT_DOCS / line.file, target)
    (tmp_path / MARKS_FILE).parent.mkdir()
    _write_marks(tmp_path, list(MARKS))
    return tmp_path


def _run(root: Path, out: Path) -> tuple[int, str]:
    result = runner.invoke(app, ["gallery", "build", "--out", str(out), "--root", str(root)])
    return result.exit_code, " ".join(result.output.split())


def _build(root: Path, out: Path) -> str:
    code, output = _run(root, out)
    assert code == 0, output
    return (out / "index.html").read_text(encoding="utf-8")


def _article(page: str, label: str) -> str:
    """The one entry whose heading is `label`."""
    found = [a for a in page.split("<article>")[1:] if f'<h3><span class="stored">{label}<' in a]
    assert len(found) == 1, label
    return found[0].split("</article>")[0]


def test_build_writes_index_html_and_exits_0(root: Path, tmp_path: Path) -> None:
    """AC-55."""
    code, output = _run(root, tmp_path / "site")

    assert code == 0, output
    assert (tmp_path / "site" / "index.html").is_file()
    assert "3 entries" in output


def test_page_shows_only_the_records_the_marks_file_names(root: Path, tmp_path: Path) -> None:
    """AC-1."""
    page = _build(root, tmp_path / "site")

    assert page.count("<article>") == len(MARKS)
    for name in (DEV, HELD, REAL):
        assert escape(str(_stored(name)["question"])) in page
    assert escape(str(_stored(UNNAMED)["question"])) not in page


def test_entry_shows_question_verdict_and_claims_in_order(root: Path, tmp_path: Path) -> None:
    """AC-17, AC-18, AC-19: stored text as stored, escaped."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")
    record = _stored(DEV)
    claims = record["claims"]
    assert isinstance(claims, list)

    assert escape(str(record["question"])) in entry
    assert f'verdict: <span class="stored">{record["verdict"]}</span>' in entry
    places = [entry.index(escape(str(claim["text"]))) for claim in claims]
    assert places == sorted(places)
    assert len(places) == len(claims) > 0


@pytest.mark.parametrize(
    ("label", "section"),
    [
        ("Eval 1", "Development questions"),
        ("Held out 3", "Held out questions"),
        ("Q2", "Realistic questions"),
    ],
)
def test_entry_appears_in_the_section_its_eval_file_names(
    root: Path, tmp_path: Path, label: str, section: str
) -> None:
    """AC-2, AC-3, AC-4."""
    page = _build(root, tmp_path / "site")
    sections = {
        s.split("</h2>")[0]: s for s in re.split(r"<section><h2>", page)[1:] if "</h2>" in s
    }

    assert set(sections) == {"Development questions", "Held out questions", "Realistic questions"}
    assert f'<h3><span class="stored">{label}<' in sections[section]


def test_held_out_section_carries_its_line(root: Path, tmp_path: Path) -> None:
    """AC-8."""
    page = _build(root, tmp_path / "site")

    assert (
        "<h2>Held out questions</h2>"
        "<p>Asked once at the end of v1, never used to tune the tool.</p>"
    ) in page


@pytest.mark.parametrize("marks", MARKS)
def test_entry_shows_mark_and_note_exactly(
    root: Path, tmp_path: Path, marks: dict[str, object]
) -> None:
    """AC-12, AC-13: the mark as given, the note as given, no note when it is null."""
    entry = _article(_build(root, tmp_path / "site"), str(marks["label"]))

    assert f'<span class="stored">{marks["mark"]}</span>' in entry
    if marks["note"] is None:
        assert 'class="note"' not in entry
    else:
        assert f'<p class="note"><span class="stored">{marks["note"]}</span></p>' in entry


def test_mark_and_verdict_are_labelled_by_whose_they_are(root: Path, tmp_path: Path) -> None:
    """AC-15 (and the text of AC-14, whose look is task 8)."""
    entry = _article(_build(root, tmp_path / "site"), "Held out 3")

    assert "Model's own verdict: " in entry
    assert "Engineer's mark: " in entry


def test_entry_links_to_the_source_of_its_mark(root: Path, tmp_path: Path) -> None:
    """AC-16."""
    entry = _article(_build(root, tmp_path / "site"), "Held out 3")

    assert (
        '<a href="https://github.com/ghalynho10/tracepath/blob/main/docs/scope/scope.md">'
        "docs/scope/scope.md</a>, "
        '<span class="stored">v1 finish line</span>'
    ) in entry


def test_build_fails_on_a_record_not_in_asks(root: Path, tmp_path: Path) -> None:
    """AC-5."""
    (root / ASKS_DIR / HELD).unlink()

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert f"entry 3 (Held out 3) names {HELD}, which is not in artifacts/asks/" in output
    assert not (tmp_path / "site" / "index.html").exists()


def test_build_fails_on_an_eval_file_it_does_not_show(root: Path, tmp_path: Path) -> None:
    """AC-6."""
    path = root / ASKS_DIR / DEV
    record = json.loads(path.read_text(encoding="utf-8"))
    record["eval_file"] = "eval/some-other.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert f"{DEV}: eval_file 'eval/some-other.json' is not one the gallery shows" in output


@pytest.mark.parametrize("field", ["record", "label", "mark", "note", "source_path", "source_row"])
def test_build_fails_on_an_entry_missing_a_field(root: Path, tmp_path: Path, field: str) -> None:
    """AC-9, AC-10: every field is required, a null note included."""
    marks = [dict(m) for m in MARKS]
    del marks[1][field]
    _write_marks(root, marks)

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert "entry 2" in output
    assert f"{field}: Field required" in output


def test_build_fails_on_a_mark_it_does_not_know(root: Path, tmp_path: Path) -> None:
    """AC-11."""
    marks = [dict(m) for m in MARKS]
    marks[0]["mark"] = "mostly right"
    _write_marks(root, marks)

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert f"entry 1 ({REAL}): mark:" in output


@pytest.mark.parametrize("field", ["record", "label"])
def test_build_fails_on_a_repeated_record_or_label(root: Path, tmp_path: Path, field: str) -> None:
    """The data model's rule: `record` and `label` are unique across entries."""
    marks = [dict(m) for m in MARKS]
    marks[2][field] = marks[0][field]
    _write_marks(root, marks)

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert f"`{field}` repeated: {marks[0][field]}" in output


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
    code, output = _run(root, root / inside)

    assert code == 1
    assert "never writes inside" in output
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


def test_cited_item_links_to_its_line_in_jobhunt(root: Path, tmp_path: Path) -> None:
    """AC-34: the first claim of eval question 1 cites 0008/AC-7, stored at line 54."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert (
        f'<a href="https://github.com/ghalynho10/JobHunt/blob/{JOBHUNT_COMMIT}/docs/'
        'specs/0008-app-shell-and-navigation/index.md?plain=1#L54">0008/AC-7</a>'
    ) in entry


def test_cited_item_with_a_file_and_no_line_links_to_the_whole_file(
    root: Path, tmp_path: Path
) -> None:
    """AC-35: no line anchor, and the link text says "whole file"."""

    def drop_line(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        item["line"] = item["line"].replace("index.md:54", "index.md")

    _edit_record(root, DEV, drop_line)

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert (
        f'<a href="https://github.com/ghalynho10/JobHunt/blob/{JOBHUNT_COMMIT}/docs/'
        'specs/0008-app-shell-and-navigation/index.md">0008/AC-7, whole file</a>'
    ) in entry


def test_rejected_id_is_shown_with_no_link(root: Path, tmp_path: Path) -> None:
    """AC-41: an id code rejected at ask time is named, never linked."""

    def reject(record: dict[str, Any]) -> None:
        record["claims"][0]["cites"].append("0099/AC-1")
        record["claims"][0]["rejected_ids"].append("0099/AC-1")

    _edit_record(root, DEV, reject)

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert "</a>, 0099/AC-1</p>" in entry
    assert ">0099/AC-1</a>" not in entry


def _refused(root: Path, tmp_path: Path) -> str:
    code, output = _run(root, tmp_path / "site")
    assert code == 1, output
    assert not (tmp_path / "site" / "index.html").exists()
    return output


def test_build_fails_on_a_record_cut_on_another_commit(root: Path, tmp_path: Path) -> None:
    """AC-7."""
    _edit_record(root, HELD, lambda r: r.update(corpus_commit="abcdef1"))

    assert f"{HELD}: corpus_commit 'abcdef1' is not the pinned commit" in _refused(root, tmp_path)


def test_build_accepts_the_pinned_commit_in_full(root: Path, tmp_path: Path) -> None:
    """AC-7: the full form of the pinned commit is the same commit as the short one."""
    _edit_record(root, HELD, lambda r: r.update(corpus_commit=JOBHUNT_COMMIT))

    _build(root, tmp_path / "site")


def test_build_fails_on_an_item_line_of_unknown_shape(root: Path, tmp_path: Path) -> None:
    """AC-37: three spaces where the grammar has two."""

    def widen(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        item["line"] = item["line"].replace("  accepted  ", "   accepted  ")

    _edit_record(root, DEV, widen)

    assert f"{DEV}: item 0008/AC-7: stored line" in _refused(root, tmp_path)


def test_build_fails_on_a_file_not_in_the_snapshot(root: Path, tmp_path: Path) -> None:
    """AC-38: checked for every item that gets a link, cited or not."""

    def move(record: dict[str, Any]) -> None:
        item = record["items"][-1]
        location = item["line"].split("  ")[-2]
        item["line"] = item["line"].replace(location, "specs/no-such-spec/index.md:3")

    _edit_record(root, DEV, move)

    assert "specs/no-such-spec/index.md is not in corpus/jobhunt/docs/" in _refused(root, tmp_path)


@pytest.mark.parametrize("line", [0, 100_000])
def test_build_fails_on_a_line_outside_its_file(root: Path, tmp_path: Path, line: int) -> None:
    """AC-39."""

    def shift(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        item["line"] = item["line"].replace("index.md:54", f"index.md:{line}")

    _edit_record(root, DEV, shift)

    assert f"{DEV}: item 0008/AC-7: line {line} is outside" in _refused(root, tmp_path)


def test_build_fails_on_a_cited_id_not_among_the_items(root: Path, tmp_path: Path) -> None:
    """AC-40."""
    _edit_record(root, DEV, lambda r: r["claims"][0]["cites"].append("0099/AC-1"))

    assert f"{DEV}: a claim cites 0099/AC-1, which is neither" in _refused(root, tmp_path)


def test_build_fails_on_a_cited_item_with_no_file(root: Path, tmp_path: Path) -> None:
    """AC-42."""

    def unplace(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        location = item["line"].split("  ")[-2]
        item["line"] = item["line"].replace(location, "no file stored")

    _edit_record(root, DEV, unplace)

    assert f"{DEV}: item 0008/AC-7 is cited but has no stored file" in _refused(root, tmp_path)


def test_pinned_commit_matches_the_snapshot_record() -> None:
    """AC-43."""
    snapshot = (PROJECT_ROOT / "corpus" / "jobhunt" / "SNAPSHOT.md").read_text(encoding="utf-8")

    assert re.findall(r"\*\*Commit\*\*: `([0-9a-f]{40})`", snapshot) == [JOBHUNT_COMMIT]
