"""The answer gallery build (spec 0010): what the page shows and what the build touches."""

import json
import os
import re
import shutil
import socket
from collections.abc import Callable
from html import escape, unescape
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.citations import JOBHUNT_COMMIT, item_link, parse_item_line
from tracepath.gallery.inline import runs, to_html
from tracepath.gallery.records import MARKS_FILE, SNAPSHOT_DOCS
from tracepath.gallery.render import (
    LABEL_KEY,
    MARK_CAPTION,
    MARK_KEY,
    STYLE,
    VERDICT_CAPTION,
    VERDICT_WORDS,
)

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
        "section": "realistic",
        "mark": "wrong",
        "note": "A fixture note,\nover two lines.",
        "source_path": "experiments/0018-realistic-usage-questions/README.md",
        "source_row": "Q2",
    },
    {
        "record": DEV,
        "label": "Eval 1",
        "section": "development",
        "mark": "right",
        "note": None,
        "source_path": "experiments/0016-link-hops/README.md",
        "source_row": "Q1",
    },
    {
        "record": HELD,
        "label": "Held out 3",
        "section": "held out",
        "mark": "partly right",
        "note": "Retrieval missed one item.",
        "source_path": "docs/scope/scope.md",
        "source_row": "v1 finish line",
    },
)

runner = CliRunner()

#: An entry's opening tag, which carries its slug as `id` (spec 0012 AC-82).
_ARTICLE = re.compile(r'<article id="[a-z0-9-]+">')


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


def _shown(text: str, code_words: bool = True) -> str:
    """A stored text as the page writes it, by the inline rule of spec 0012."""
    return to_html(runs(text, code_words))


def _cited_item(record: dict[str, Any]) -> dict[str, Any]:
    """The item the record's first claim cites first."""
    cited = record["claims"][0]["cites"][0]
    item: dict[str, Any] = next(i for i in record["items"] if i["id"] == cited)
    return item


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root with four records, a marks file naming three of them, the
    snapshot files those records' items sit in, and the rulings its marks link to."""
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
    for marks in MARKS:
        source = str(marks["source_path"])
        if source.startswith("experiments/"):
            (tmp_path / source).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(PROJECT_ROOT / source, tmp_path / source)
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
    found = [a for a in _ARTICLE.split(page)[1:] if f'<h3><span class="stored">{label}<' in a]
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

    assert len(_ARTICLE.findall(page)) == len(MARKS)
    for name in (DEV, HELD, REAL):
        assert _shown(str(_stored(name)["question"])) in page
    assert _shown(str(_stored(UNNAMED)["question"])) not in page


def test_entry_shows_question_verdict_and_claims_in_order(root: Path, tmp_path: Path) -> None:
    """AC-17, AC-18, AC-19: stored text as stored, escaped, formatted by spec 0012's rule."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")
    record = _stored(DEV)
    claims = record["claims"]
    assert isinstance(claims, list)

    assert _shown(str(record["question"])) in entry
    assert '<p class="verdict-word">answered</p>' in entry
    places = [entry.index(_shown(str(claim["text"]))) for claim in claims]
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
def test_entry_appears_in_the_section_its_marks_entry_names(
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

    assert f'<span class="swipe" data-mark="{marks["mark"]}">{marks["mark"]}</span>' in entry
    if marks["note"] is None:
        assert 'class="note"' not in entry
        assert "My note." not in entry
    else:
        assert (
            f'<p class="note"><strong>My note.</strong> <span class="stored">{marks["note"]}</span>'
            "</p>"
        ) in entry


def test_mark_and_verdict_are_labelled_by_whose_they_are(root: Path, tmp_path: Path) -> None:
    """AC-14, AC-15 as amended: each word carries the caption that says whose it is."""
    page = _build(root, tmp_path / "site")
    entry = _article(page, "Held out 3")

    assert f'<p class="caption">{escape(VERDICT_CAPTION)}</p>' in entry
    assert f'<p class="caption">{escape(MARK_CAPTION)}</p>' in entry
    assert "<h3>My marks</h3>" in page
    assert "each with my own mark." in page
    words = re.sub(r"<script[^>]*>.*?</script>", "", page, flags=re.S)
    assert "engineer" not in re.sub(r"<[^>]+>", "", words).lower()


def _rule(selector: str) -> str:
    """The body of the one style rule for `selector`."""
    found = re.findall(rf"(?:^|\n){re.escape(selector)} \{{([^}}]*)\}}", STYLE)
    assert len(found) == 1, selector
    return str(found[0])


@pytest.mark.parametrize(
    ("mark", "colour"),
    [
        pytest.param("right", "#B9E3EE", id="AC-49"),
        pytest.param("partly right", "#F6E27F", id="AC-50"),
        pytest.param("wrong", "#FFC8C2", id="AC-51"),
        pytest.param("declined", "#CBD3DC", id="AC-52"),
    ],
)
def test_each_mark_is_bold_on_its_own_swipe(
    root: Path, tmp_path: Path, mark: str, colour: str
) -> None:
    """Spec 0012 AC-49 to AC-52."""
    _write_marks(root, [dict(m, mark=mark) if m["label"] == "Eval 1" else m for m in MARKS])

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert f'<p class="mark-word"><span class="swipe" data-mark="{mark}">{mark}</span></p>' in entry
    assert _rule(f'.swipe[data-mark="{mark}"]').strip() == f"background: {colour};"
    assert "font-weight: 700;" in _rule(".swipe")


def test_the_mark_is_no_button_and_has_no_border(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-54."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")
    mark = entry.split('<div class="mark">', 1)[1].split("</div>", 1)[0]

    assert "<button" not in mark
    assert "border:" not in _rule(".swipe") + _rule(".mark-word") + _rule(".mark-word .swipe")
    assert not re.search(r"\.mark\b[^{]*\{[^}]*border", STYLE)


def test_the_verdict_and_the_mark_share_one_block_verdict_first(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-41: one block, the model's verdict then the engineer's mark."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert entry.count('<div class="verdict-mark">') == 1
    block = entry.split('<div class="verdict-mark">', 1)[1]
    assert block.startswith('<div class="verdict"><p class="verdict-word">')
    assert block.index('<div class="verdict">') < block.index('<div class="mark">')
    assert entry.index('<p class="details">') < entry.index('<div class="verdict-mark">')


@pytest.mark.parametrize(
    ("code", "words"),
    [
        pytest.param("answered", "answered", id="AC-42"),
        pytest.param("partly", "partly answered", id="AC-43"),
        pytest.param("not_supported", "not supported by the records", id="AC-44"),
        pytest.param("no_documented_link", "no documented link", id="AC-45"),
    ],
)
def test_each_verdict_code_shows_its_words_in_mono_with_its_caption(
    root: Path, tmp_path: Path, code: str, words: str
) -> None:
    """Spec 0012 AC-42 to AC-46."""
    _edit_record(root, DEV, lambda r: r.update(verdict=code))

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert (
        f'<div class="verdict"><p class="verdict-word">{words}</p>'
        '<p class="caption">\u2014 the model&#x27;s verdict on its own answer</p></div>'
    ) in entry
    assert "var(--mono)" in _rule(".verdict-word")


def test_no_verdict_wording_is_a_mark_word() -> None:
    """Spec 0012 AC-47, over every stored code."""
    assert set(VERDICT_WORDS) == {"answered", "partly", "not_supported", "no_documented_link"}
    assert not set(VERDICT_WORDS.values()) & {mark for mark, _ in MARK_KEY}


def test_build_fails_on_a_verdict_it_does_not_know(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-48: exit 1, naming the record."""
    _edit_record(root, DEV, lambda r: r.update(verdict="maybe"))

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert DEV in output
    assert "verdict" in output
    assert not (tmp_path / "site" / "index.html").exists()


def test_a_ruling_under_experiments_is_linked_and_followed_by_its_row(
    root: Path, tmp_path: Path
) -> None:
    """AC-16 as amended, spec 0012 AC-59, AC-105."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert (
        '<p class="source"><a href="https://github.com/ghalynho10/tracepath/blob/main/'
        'experiments/0016-link-hops/README.md">My full ruling</a>, '
        '<span class="stored">Q1</span></p>'
    ) in entry


def test_a_ruling_elsewhere_is_plain_text_with_no_link(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-60."""
    entry = _article(_build(root, tmp_path / "site"), "Held out 3")
    source = entry.split('<p class="source">', 1)[1].split("</p>", 1)[0]

    assert re.sub(r"<[^>]+>", "", unescape(source)) == (
        "My full ruling: the v1 finish line in the project's scope notes (not published)."
    )
    assert "<a " not in source


@pytest.mark.parametrize(
    "source", ["experiments/0099-missing/README.md", "experiments/../../outside.md"]
)
def test_build_fails_on_a_ruling_that_is_not_a_file_under_the_root(
    root: Path, tmp_path: Path, source: str
) -> None:
    """Spec 0012 AC-61: exit 1, naming the entry."""
    (tmp_path / "outside.md").write_text("x", encoding="utf-8")
    _write_marks(root, [dict(m, source_path=source) if m["label"] == "Q2" else m for m in MARKS])

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert "(Q2)" in output
    assert source in output


@pytest.mark.parametrize("marks", MARKS)
def test_the_note_and_source_sit_below_the_verdict_and_mark(
    root: Path, tmp_path: Path, marks: dict[str, object]
) -> None:
    """Spec 0012 AC-57, AC-58: "My note." only with a note, after the verdict and mark."""
    entry = _article(_build(root, tmp_path / "site"), str(marks["label"]))

    assert entry.index('<div class="verdict-mark">') < entry.index('<div class="ruling">')
    assert ("My note." in entry) is (marks["note"] is not None)
    if marks["note"] is not None:
        assert entry.index('<div class="mark">') < entry.index("My note.")


def test_build_fails_on_a_record_not_in_asks(root: Path, tmp_path: Path) -> None:
    """AC-5."""
    (root / ASKS_DIR / HELD).unlink()

    code, output = _run(root, tmp_path / "site")

    assert code == 1
    assert f"entry 3 (Held out 3) names {HELD}, which is not in artifacts/asks/" in output
    assert not (tmp_path / "site" / "index.html").exists()


@pytest.mark.parametrize("record", [f"../asks/{HELD}", f"./{HELD}", f"..\\asks\\{HELD}", ".."])
def test_build_fails_on_a_record_that_is_not_a_plain_name(
    root: Path, tmp_path: Path, record: str
) -> None:
    """AC-1: only files directly in artifacts/asks/ are shown, even when the path resolves."""
    _write_marks(root, [MARKS[0], MARKS[1], {**MARKS[2], "record": record}])

    output = _refused(root, tmp_path)

    assert (
        f"entry 3 (Held out 3) names {record}, which is not a plain file name in artifacts/asks/"
    ) in output


#: Each marks entry of the fixture by position, with the section its record fits.
FITS = (
    (1, "Q2", REAL, "realistic"),
    (2, "Eval 1", DEV, "development"),
    (3, "Held out 3", HELD, "held out"),
)


@pytest.mark.parametrize(
    ("position", "section"),
    [
        (2, "held out"),
        (2, "realistic"),
        (3, "development"),
        (3, "realistic"),
        (1, "development"),
        (1, "held out"),
    ],
)
def test_build_fails_on_a_section_its_record_disagrees_with(
    root: Path, tmp_path: Path, position: int, section: str
) -> None:
    """AC-6: development needs the development eval file, realistic needs none, held out needs
    another one."""
    number, label, record, fits = FITS[position - 1]
    marks = [dict(m) for m in MARKS]
    marks[position - 1]["section"] = section
    _write_marks(root, marks)

    assert (
        f"entry {number} ({label}) is in section {section!r}, but {record} has eval_file "
        f"{_stored(record).get('eval_file')!r}, which belongs in {fits!r}"
    ) in _refused(root, tmp_path)


def test_build_fails_on_a_development_entry_whose_record_names_another_eval_file(
    root: Path, tmp_path: Path
) -> None:
    """AC-6: any eval file other than the development one must be marked held out."""
    _edit_record(root, DEV, lambda r: r.update(eval_file="eval/some-other.json"))

    assert (
        f"entry 2 (Eval 1) is in section 'development', but {DEV} has eval_file "
        "'eval/some-other.json', which belongs in 'held out'"
    ) in _refused(root, tmp_path)


def test_build_fails_on_a_section_it_does_not_know(root: Path, tmp_path: Path) -> None:
    """AC-9."""
    marks = [dict(m) for m in MARKS]
    marks[0]["section"] = "held-out"
    _write_marks(root, marks)

    assert f"entry 1 ({REAL}): section:" in _refused(root, tmp_path)


@pytest.mark.parametrize(
    "field", ["record", "label", "section", "mark", "note", "source_path", "source_row"]
)
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


def _break_marks(root: Path, contents: str | None) -> None:
    if contents is None:
        (root / MARKS_FILE).unlink()
    else:
        (root / MARKS_FILE).write_text(contents, encoding="utf-8")


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (None, "marks.json: not found"),
        ("[{", "marks.json: not valid JSON"),
        ('{"record": "x.json"}', "gallery/marks.json: expected a JSON list of entries"),
    ],
)
def test_build_fails_cleanly_on_a_marks_file_it_cannot_read(
    root: Path, tmp_path: Path, contents: str | None, message: str
) -> None:
    """A clear message and exit 1, never a traceback (AGENTS.md rules)."""
    _break_marks(root, contents)

    result = runner.invoke(
        app, ["gallery", "build", "--out", str(tmp_path / "site"), "--root", str(root)]
    )

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert message in " ".join(result.output.split())
    assert not (tmp_path / "site" / "index.html").exists()


def test_build_fails_cleanly_on_a_record_it_cannot_read(root: Path, tmp_path: Path) -> None:
    """A record with no verdict is refused by name, not shown with a gap."""
    _edit_record(root, DEV, lambda r: r.pop("verdict"))

    assert f"{DEV}: not an ask record the gallery can read" in _refused(root, tmp_path)


def test_build_fails_cleanly_when_the_page_cannot_be_written(root: Path, tmp_path: Path) -> None:
    """An --out that is a file: exit 1 naming the page, never a traceback."""
    out = tmp_path / "site"
    out.write_text("a file, not a folder", encoding="utf-8")

    code, output = _run(root, out)

    assert code == 1
    assert f"{out / 'index.html'}: could not be written" in output


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
    """AC-58: inline styles, no stylesheet or other file of the site; scripts are inline
    since spec 0011 (its AC-74)."""
    page = _build(root, tmp_path / "site")

    assert "<style>" in page
    assert "<link" not in page
    assert not re.search(r"<script(?! type=\"application/json\")[^>]", page)
    assert not re.search(r'\b(src|href)="(?!https://|#)', page)


def test_build_from_the_committed_marks_file(tmp_path: Path) -> None:
    """AC-1, AC-55 on the real data: one entry per marks entry."""
    marks = json.loads((PROJECT_ROOT / MARKS_FILE).read_text(encoding="utf-8"))

    page = _build(PROJECT_ROOT, tmp_path / "site")

    assert len(_ARTICLE.findall(page)) == len(marks) > 0


def test_cited_item_links_to_its_line_in_jobhunt(root: Path, tmp_path: Path) -> None:
    """AC-34: the first claim of eval question 1 cites 0008/AC-7, stored at line 54."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert (
        f'<a href="https://github.com/ghalynho10/JobHunt/blob/{JOBHUNT_COMMIT}/docs/'
        'specs/0008-app-shell-and-navigation/index.md?plain=1#L54" data-item="0008/AC-7">'
        "0008/AC-7</a>"
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
        'specs/0008-app-shell-and-navigation/index.md" data-item="0008/AC-7">'
        "0008/AC-7, whole file</a>"
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


@pytest.mark.parametrize("unreadable", ["not utf-8", "no permission"])
def test_build_fails_cleanly_on_a_snapshot_file_it_cannot_read(
    root: Path, tmp_path: Path, unreadable: str
) -> None:
    """A clear message naming the record and file, never a traceback (AGENTS.md rules)."""
    target = root / SNAPSHOT_DOCS / "specs/unreadable.md"
    if unreadable == "not utf-8":
        target.write_bytes(b"\xff\xfe not utf-8\n")
    else:
        target.write_text("line 1\n", encoding="utf-8")
        target.chmod(0)
        if os.access(target, os.R_OK):
            pytest.skip("running as a user that reads any file")

    def move(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        item["line"] = item["line"].replace(
            "specs/0008-app-shell-and-navigation/index.md:54", "specs/unreadable.md:1"
        )

    _edit_record(root, DEV, move)

    assert f"{DEV}: corpus/jobhunt/docs/specs/unreadable.md cannot be read" in _refused(
        root, tmp_path
    )


@pytest.mark.parametrize("line", [0, 100_000])
def test_build_fails_on_a_line_outside_its_file(root: Path, tmp_path: Path, line: int) -> None:
    """AC-39."""

    def shift(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        item["line"] = item["line"].replace("index.md:54", f"index.md:{line}")

    _edit_record(root, DEV, shift)

    assert f"{DEV}: item 0008/AC-7: line {line} is outside" in _refused(root, tmp_path)


def _move_to_line(line: int) -> Callable[[dict[str, Any]], None]:
    def move(record: dict[str, Any]) -> None:
        item = _cited_item(record)
        item["line"] = item["line"].replace("index.md:54", f"index.md:{line}")

    return move


def _last_line() -> int:
    """The last line of the file eval question 1's first citation sits in."""
    path = PROJECT_ROOT / SNAPSHOT_DOCS / "specs/0008-app-shell-and-navigation/index.md"
    return len(path.read_text(encoding="utf-8").splitlines())


def test_build_accepts_the_last_line_of_a_file(root: Path, tmp_path: Path) -> None:
    """AC-39, Value sourcing row 10: lines are counted from 1, so the last one is in range."""
    last = _last_line()
    _edit_record(root, DEV, _move_to_line(last))

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert f'index.md?plain=1#L{last}" data-item="0008/AC-7">0008/AC-7</a>' in entry


def test_build_refuses_the_line_one_past_the_end(root: Path, tmp_path: Path) -> None:
    """AC-39, Value sourcing row 10."""
    last = _last_line()
    _edit_record(root, DEV, _move_to_line(last + 1))

    assert f"line {last + 1} is outside" in _refused(root, tmp_path)


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


def _first_claim(page: str, label: str = "Eval 1") -> str:
    entry = _article(page, label)
    return entry.split("<ol><li>", 1)[1].split("</li>", 1)[0]


def _labels(page: str) -> str:
    """The first claim's labels as words, without the "Labels:" lead or the chips."""
    line = _first_claim(page).split('<p class="labels">', 1)[1].split("</p>", 1)[0]
    assert line.startswith("Labels: ")
    return re.sub(r"<[^>]+>", "", line.removeprefix("Labels: "))


def _items_sent(page: str, label: str = "Eval 1") -> str:
    return _article(page, label).split("<details>", 1)[1].split("</details>", 1)[0]


def test_missing_notes_shown_when_the_record_has_any(root: Path, tmp_path: Path) -> None:
    """AC-20: shown when the record lists some, absent when it lists none."""
    assert _stored(DEV)["missing"] == []
    assert "records lack" not in _article(_build(root, tmp_path / "a"), "Eval 1")

    _edit_record(root, DEV, lambda r: r.update(missing=["A first gap", "A second gap"]))

    assert (
        '<h4 class="lack">What the answer says the records lack</h4><ul class="lack">'
        '<li><span class="stored">A first gap</span></li>'
        '<li><span class="stored">A second gap</span></li></ul>'
    ) in _article(_build(root, tmp_path / "b"), "Eval 1")


def test_details_show_date_prompt_and_hops(root: Path, tmp_path: Path) -> None:
    """AC-21, AC-22, AC-23: hops shown when stored."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert '<p class="details">Asked 2026-10-20 · prompt ask-2 · 2 hops</p>' in entry


def test_details_show_no_hops_when_the_record_stores_none(root: Path, tmp_path: Path) -> None:
    """AC-23: an `ask-1` record without `hops` or `eval_file`'s later keys."""
    assert "hops" not in _stored(HELD)

    entry = _article(_build(root, tmp_path / "site"), "Held out 3")

    assert '<p class="details">Asked 2026-10-19 · prompt ask-1</p>' in entry


def test_stored_markup_shows_as_text(root: Path, tmp_path: Path) -> None:
    """AC-24."""
    _edit_record(root, DEV, lambda r: r.update(question='Why <figure class="x">?'))

    page = _build(root, tmp_path / "site")

    assert "Why &lt;figure class=&quot;x&quot;&gt;?" in page
    assert "<figure" not in page


def test_line_breaks_kept_and_no_other_markdown_rendered(root: Path, tmp_path: Path) -> None:
    """AC-25, as spec 0012 changes it: line breaks kept, bold drawn, a heading left as typed."""
    _edit_record(root, DEV, lambda r: r["claims"][0].update(text="# First line\n**bold**"))

    claim = _first_claim(_build(root, tmp_path / "site"))

    assert '<span class="stored"># First line\n<strong>bold</strong></span>' in claim
    assert "<h1>" not in claim
    assert ".stored { white-space: pre-wrap; }" in _build(root, tmp_path / "site2")


def test_held_cited_id_shows_held_after_it(root: Path, tmp_path: Path) -> None:
    """AC-26."""
    _edit_record(root, DEV, lambda r: r["claims"][0].update(held_ids=["0008/AC-7"]))

    assert ">0008/AC-7</a> held</p>" in _first_claim(_build(root, tmp_path / "site"))


@pytest.mark.parametrize(
    ("change", "labels"),
    [
        ({"history": True}, "HISTORY read from text"),
        ({"basis": "inferred", "inferred": True}, "INFERRED"),
        (
            {"cites": ["0008/AC-7", "0099/AC-1"], "rejected_ids": ["0099/AC-1"]},
            "CITATION REJECTED: 0099/AC-1 read from text",
        ),
        ({"cites": [], "uncited": True}, "UNCITED read from text"),
        (
            {"cites": ["0099/AC-1"], "rejected_ids": ["0099/AC-1"]},
            "CITATION REJECTED: 0099/AC-1 unsupported",
        ),
        ({"basis": "link"}, "link"),
        ({"basis": "link", "inferred": True}, "INFERRED"),
        ({}, "read from text"),
    ],
)
def test_claim_labels_follow_the_stored_fields(
    root: Path, tmp_path: Path, change: dict[str, Any], labels: str
) -> None:
    """AC-27 to AC-32."""
    _edit_record(root, DEV, lambda r: r["claims"][0].update(change))

    assert _labels(_build(root, tmp_path / "site")) == labels


@pytest.mark.parametrize("rule", ["labels", "details"])
def test_labels_and_details_keep_their_stored_case(rule: str) -> None:
    """AC-21, AC-27 to AC-32, verify finding 1 of 2026-10-24: no CSS recasing, so a claim
    reads `HISTORY link` as the key teaches it, not `HISTORY LINK`."""
    found = re.search(rf"\.{rule} \{{([^}}]*)\}}", STYLE)

    assert found is not None
    assert "text-transform" not in found.group(1)


#: The failed claims tally, a second caption under the verdict's (AC-33, as amended).
TALLY = '<p class="caption">1 of 4 claims failed a check</p>'


@pytest.mark.parametrize(
    ("change", "tally"),
    [
        ({}, ""),
        ({"cites": [], "uncited": True}, TALLY),
        ({"cites": ["0099/AC-1"], "rejected_ids": ["0099/AC-1"]}, TALLY),
        ({"basis": "link", "inferred": True}, TALLY),
        ({"basis": "inferred", "inferred": True}, ""),
    ],
)
def test_verdict_line_counts_claims_that_failed_a_check(
    root: Path, tmp_path: Path, change: dict[str, Any], tally: str
) -> None:
    """AC-33: a claim inferred by its own basis has not failed a check."""
    _edit_record(root, DEV, lambda r: r["claims"][0].update(change))

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert f"own answer</p>{tally}</div>" in entry


def test_items_sent_is_closed_until_opened(root: Path, tmp_path: Path) -> None:
    """AC-44."""
    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert entry.count("<details>") == 1
    assert "<details open" not in entry
    assert "<summary>Show all (" in entry


def test_cited_items_are_shown_in_full(root: Path, tmp_path: Path) -> None:
    """AC-45."""
    record = _stored(DEV)
    cited = {c for claim in record["claims"] for c in claim["cites"]}
    sent = _items_sent(_build(root, tmp_path / "site")).split("<h5>Not cited</h5>")[0]

    for item in record["items"]:
        if item["id"] in cited:
            assert f'<span class="stored">{_shown(item["text"], False)}</span>' in sent
    assert sent.count('<div class="item">') == len(cited) > 0


def test_other_items_are_one_row_each(root: Path, tmp_path: Path) -> None:
    """AC-46, AC-48: id, type, held or accepted, and the location's link."""
    record = _stored(DEV)
    cited = {c for claim in record["claims"] for c in claim["cites"]}
    rows = _items_sent(_build(root, tmp_path / "site")).split("<h5>Not cited</h5>")[1]

    assert rows.count("<li>") == len(record["items"]) - len(cited)
    for stored in record["items"]:
        item = parse_item_line(stored["line"])
        assert item is not None
        if item.id in cited or item.marker is not None:
            continue
        status = "held" if item.held else "accepted"
        assert (
            f"<li>{escape(item.id)} · {item.type} · {status} · "
            f'<a href="{escape(item_link(item) or "")}">{item.file}:{item.line}</a></li>'
        ) in rows


def test_row_shows_struck_or_history_marker(root: Path, tmp_path: Path) -> None:
    """AC-47."""
    rows = _items_sent(_build(root, tmp_path / "site"))

    assert "<li>0021#feature-design:12 · Constraint · accepted · STRUCK · <a " in rows
    assert "<li>0007/AC-1 · AcceptanceCriterion · accepted · HISTORY · <a " in rows


def test_row_with_no_location_has_no_link(root: Path, tmp_path: Path) -> None:
    """AC-48 by AC-36."""

    def unplace(record: dict[str, Any]) -> None:
        item = record["items"][-1]
        location = item["line"].split("  ")[-2]
        item["line"] = item["line"].replace(location, "no path stored")

    _edit_record(root, DEV, unplace)
    last = _stored(DEV)["items"][-1]["id"]

    assert f"<li>{escape(last)} · " in _items_sent(_build(root, tmp_path / "site"))
    assert " · no file stored</li>" in _items_sent(_build(root, tmp_path / "site2"))


def test_key_gives_the_engineers_words_for_each_mark(root: Path, tmp_path: Path) -> None:
    """The key, task 6, and spec 0012 AC-102: the engineer's words, each mark a swipe."""
    page = _build(root, tmp_path / "site")

    for mark, meaning in MARK_KEY:
        assert (
            f'<dt><span class="swipe" data-mark="{mark}">{mark}</span></dt>'
            f"<dd>{escape(meaning)}</dd>"
        ) in page


def _key_section(page: str) -> str:
    return page.split('<section class="key">', 1)[1].split("</section>", 1)[0]


def test_the_total_counts_each_mark_shown(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-71 to AC-73, AC-75: the fixture's three entries, one mark carried by none."""
    total = _key_section(_build(root, tmp_path / "site")).split('<p class="total">', 1)[1]

    assert total.split("</p>", 1)[0] == (
        "My marks on the 3 shown answers: "
        '<span class="swipe" data-mark="right">right</span> 1 · '
        '<span class="swipe" data-mark="partly right">partly right</span> 1 · '
        '<span class="swipe" data-mark="wrong">wrong</span> 1 · '
        '<span class="swipe" data-mark="declined">declined</span> 0'
    )


def test_the_total_sits_in_the_key_above_the_marks_list(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-74."""
    key = _key_section(_build(root, tmp_path / "site"))

    assert key.index("<h3>My marks</h3>") < key.index('<p class="total">') < key.index("<dl>")


def test_the_total_of_the_committed_marks(tmp_path: Path) -> None:
    """Spec 0012 AC-71, AC-72: 31 shown, 17 right, 2 partly right, 2 wrong, 10 declined."""
    total = _key_section(_build(PROJECT_ROOT, tmp_path / "site")).split('<p class="total">')[1]

    assert re.sub(r"<[^>]+>", "", total.split("</p>", 1)[0]) == (
        "My marks on the 31 shown answers: right 17 · partly right 2 · wrong 2 · declined 10"
    )


def test_key_gives_each_label_its_meaning(root: Path, tmp_path: Path) -> None:
    """Value sourcing row 17: the label key as `LABEL_KEY` gives it, terms in stored case."""
    page = _build(root, tmp_path / "site")

    for label, meaning in LABEL_KEY:
        assert f"<dt>{escape(label)}</dt><dd>{escape(meaning)}</dd>" in page


def test_entries_in_a_section_follow_the_marks_file_order(root: Path, tmp_path: Path) -> None:
    """AC-1 to AC-4: marks file order, not label order or record name order."""
    later = {
        "record": UNNAMED,
        "label": "Q9",
        "section": "realistic",
        "mark": "right",
        "note": None,
        "source_path": "experiments/0018-realistic-usage-questions/README.md",
        "source_row": "Q9",
    }
    _write_marks(root, [later, *MARKS])

    page = _build(root, tmp_path / "site")

    assert page.index('<h3><span class="stored">Q9<') < page.index('<h3><span class="stored">Q2<')


def _section_html(page: str, title: str) -> str:
    return _ARTICLE.split(page.split(f"<section><h2>{title}</h2>", 1)[1], maxsplit=1)[0]


def test_page_counts_the_records_asks_holds(root: Path, tmp_path: Path) -> None:
    """AC-49: four records in the fixture, three of them shown."""
    page = _build(root, tmp_path / "site")

    assert "</a> holds 4 records. This page shows 3 of them: " in page


def test_page_links_to_the_records_directory(root: Path, tmp_path: Path) -> None:
    """AC-50."""
    page = _build(root, tmp_path / "site")

    assert (
        '<a href="https://github.com/ghalynho10/tracepath/tree/main/artifacts/asks">'
        "artifacts/asks/</a>"
    ) in page


def test_page_states_which_questions_it_shows(root: Path, tmp_path: Path) -> None:
    """AC-51."""
    page = _build(root, tmp_path / "site")

    assert (
        "eval questions 1 to 5, held out questions 1 to 4, and experiment 0018&#x27;s 22."
    ) in page


def test_development_section_states_the_ask_1_marks(root: Path, tmp_path: Path) -> None:
    """AC-52."""
    line = _section_html(_build(root, tmp_path / "site"), "Development questions")

    assert (
        "Earlier runs of eval questions 1 to 5 on prompt ask-1, from 2026-10-19: "
        "I also marked them right"
    ) in line


def test_realistic_section_links_to_experiment_0018(root: Path, tmp_path: Path) -> None:
    """AC-53."""
    line = _section_html(_build(root, tmp_path / "site"), "Realistic questions")

    assert (
        '<a href="https://github.com/ghalynho10/tracepath/blob/main/experiments/'
        "0018-realistic-usage-questions/README.md\">experiment 0018's README</a>"
    ) in line
    assert "How these questions were set and run" in line


def test_page_names_jobhunt_at_the_pinned_commit(root: Path, tmp_path: Path) -> None:
    """AC-54."""
    page = _build(root, tmp_path / "site")

    assert (
        'Every citation points into <a href="https://github.com/ghalynho10/JobHunt">JobHunt</a> '
        f'at commit <a href="https://github.com/ghalynho10/JobHunt/tree/{JOBHUNT_COMMIT}">'
        "2e40bcf</a>"
    ) in page


#: A stored text with an explicit code span, a bold pair and a bare file name.
MARKED = "Read `x_y` and **z** in a.ts"

#: How the page writes `MARKED` with code words on, and with them off.
WITH_WORDS = (
    'Read <code><span class="w">x_y</span></code> and <strong>z</strong> in '
    '<code><span class="w">a.ts</span></code>'
)
WITHOUT_WORDS = 'Read <code><span class="w">x_y</span></code> and <strong>z</strong> in a.ts'


def test_the_question_is_formatted_with_code_words(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-14, AC-20."""
    _edit_record(root, DEV, lambda r: r.update(question=MARKED))

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert f'<p class="question"><span class="stored">{WITH_WORDS}</span></p>' in entry


def test_each_claim_is_formatted_with_code_words(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-15, AC-20."""
    _edit_record(root, DEV, lambda r: r["claims"][0].update(text=MARKED))

    claim = _first_claim(_build(root, tmp_path / "site"))

    assert claim.startswith(f'<span class="stored">{WITH_WORDS}</span>')


def test_each_missing_note_is_formatted_with_code_words(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-16, AC-27."""
    _edit_record(root, DEV, lambda r: r.update(missing=[MARKED]))

    entry = _article(_build(root, tmp_path / "site"), "Eval 1")

    assert f'<li><span class="stored">{WITH_WORDS}</span></li>' in entry


def test_the_note_is_formatted_from_its_markers_only(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-17, AC-29: the fixture's own marks file, never the committed one."""
    marks = [dict(m, note=MARKED) if m["label"] == "Q2" else m for m in MARKS]
    _write_marks(root, marks)

    entry = _article(_build(root, tmp_path / "site"), "Q2")

    assert (
        f'<p class="note"><strong>My note.</strong> <span class="stored">{WITHOUT_WORDS}</span></p>'
    ) in entry


def test_cited_item_text_is_formatted_from_its_markers_only(root: Path, tmp_path: Path) -> None:
    """Spec 0012 AC-18, AC-28."""
    _edit_record(root, DEV, lambda r: _cited_item(r).update(text=MARKED))

    sent = _items_sent(_build(root, tmp_path / "site")).split("<h5>Not cited</h5>")[0]

    assert f'<span class="stored">{WITHOUT_WORDS}</span>' in sent
