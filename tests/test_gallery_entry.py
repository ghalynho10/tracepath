"""The shape of each gallery entry (spec 0012): headings, claim lines, ruling and strip.

Built once from the committed records and marks file, so every check covers all 31
entries.
"""

import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.graph import slug_of
from tracepath.gallery.records import GRAPH_SCRIPT, MARKS_FILE
from tracepath.gallery.render import STRIP_DRAWING

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Elements that never hold anything, so they open no level.
_VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"})

#: The mark of each entry as it stands on 2026-10-26 (AC-64).
MARKS_ON_2026_10_26 = {
    "Eval 1": "right",
    "Eval 2": "right",
    "Eval 3": "right",
    "Eval 4": "right",
    "Eval 5": "right",
    "Held out 1": "right",
    "Held out 2": "right",
    "Held out 3": "partly right",
    "Held out 4": "right",
    "Q1": "wrong",
    "Q2": "wrong",
    "Q3": "right",
    "Q4": "partly right",
    "Q5": "right",
    "Q6": "right",
    "Q7": "right",
    "Q8": "right",
    "Q9": "right",
    "Q10": "right",
    "Q11": "declined",
    "Q12": "declined",
    "Q13": "declined",
    "Q14": "declined",
    "Q15": "declined",
    "Q16": "declined",
    "Q17": "declined",
    "Q18": "declined",
    "Q19": "right",
    "Q20": "declined",
    "Q21": "declined",
    "Q22": "right",
}


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> str:
    """The page built from the committed records and marks file."""
    out = tmp_path_factory.mktemp("site")
    result = CliRunner().invoke(
        app, ["gallery", "build", "--out", str(out), "--root", str(PROJECT_ROOT)]
    )
    assert result.exit_code == 0, result.output
    return (out / "index.html").read_text(encoding="utf-8")


def _marks() -> list[dict[str, Any]]:
    marks: list[dict[str, Any]] = json.loads((PROJECT_ROOT / MARKS_FILE).read_text("utf-8"))
    return marks


def _records() -> dict[str, dict[str, Any]]:
    """Each shown record, by its marks entry's label."""
    return {
        entry["label"]: json.loads(
            (PROJECT_ROOT / ASKS_DIR / entry["record"]).read_text(encoding="utf-8")
        )
        for entry in _marks()
    }


@pytest.fixture(scope="module")
def articles(page: str) -> dict[str, str]:
    """Each entry's inner HTML, by its label."""
    found = {}
    for article in page.split("<article>")[1:]:
        inner = article.split("</article>")[0]
        label = re.search(r'^<h3><span class="stored">(.*?)</span></h3>', inner)
        assert label is not None
        found[unescape(label.group(1))] = inner
    return found


class _Children(HTMLParser):
    """The top level elements of a piece of HTML: tag, attributes and own text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.children: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.depth == 0:
            self.children.append((tag, dict(attrs)))
        if tag not in _VOID:
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.depth == 0:
            self.children.append((tag, dict(attrs)))

    def handle_endtag(self, tag: str) -> None:
        if tag not in _VOID:
            self.depth -= 1


def _children(inner: str) -> list[tuple[str, dict[str, str | None]]]:
    parser = _Children()
    parser.feed(inner)
    return parser.children


def _headings(inner: str) -> list[str]:
    return [unescape(h) for h in re.findall(r"<h4[^>]*>(.*?)</h4>", inner)]


def _class_count(inner: str, name: str) -> int:
    """How many elements carry `name` as one of their classes."""
    return sum(name in found.split() for found in re.findall(r'class="([^"]*)"', inner))


def _cited(record: dict[str, Any]) -> set[str]:
    return {
        c for claim in record["claims"] for c in claim["cites"] if c not in claim["rejected_ids"]
    }


def _claims(inner: str) -> list[str]:
    """Each claim's HTML; none when the entry shows "No claims." instead of a list."""
    if "<ol>" not in inner:
        assert "<p>No claims.</p>" in inner
        return []
    return inner.split("<ol>", 1)[1].split("</ol>", 1)[0].split("<li>")[1:]


def _strip(inner: str) -> str:
    found = re.findall(r"<button [^>]*data-graph=[^>]*>.*?</button>", inner, flags=re.S)
    assert len(found) == 1
    return str(found[0])


def test_the_title_is_h3_and_each_section_heading_h4(articles: dict[str, str]) -> None:
    """AC-30."""
    for label, inner in articles.items():
        tags = [tag for tag, _ in _children(inner)]
        assert tags.count("h3") == 1, label
        assert not {"h1", "h2", "h5", "h6"} & set(tags), label
        assert tags.count("h4") >= 3, label


def test_the_section_headings_come_in_order(articles: dict[str, str]) -> None:
    """AC-31, AC-32, AC-33: the missing section shows exactly when the record lists some."""
    records = _records()
    for label, inner in articles.items():
        lack = ["What the answer says the records lack"] if records[label]["missing"] else []
        assert _headings(inner) == ["Question", "Answer", *lack, "Items sent"], label
    assert sum(bool(r["missing"]) for r in records.values()) == 25


def test_the_old_missing_heading_is_gone(page: str) -> None:
    """AC-34."""
    assert "Missing, as the answer says" not in page


def test_cited_and_not_cited_are_h5_inside_items_sent(articles: dict[str, str]) -> None:
    """AC-35."""
    for inner in articles.values():
        sent = inner.split("<details>", 1)[1].split("</details>", 1)[0]
        assert re.findall(r"<h5>(.*?)</h5>", sent) == ["Cited", "Not cited"]


def test_the_items_sent_summary_counts_items_sent_and_cited(articles: dict[str, str]) -> None:
    """AC-36."""
    for label, record in _records().items():
        summary = f"<summary>Show all ({len(record['items'])}, {len(_cited(record))} cited)"
        assert summary in articles[label], label


def test_a_citing_claim_has_a_cites_line_holding_every_id(articles: dict[str, str]) -> None:
    """AC-37."""
    for label, record in _records().items():
        claims = _claims(articles[label])
        for claim, stored in zip(claims, record["claims"], strict=True):
            line = re.search(r'<p class="cites">(.*?)</p>', claim)
            if not stored["cites"]:
                assert line is None
                continue
            assert line is not None
            words = re.sub(r"<[^>]+>", "", line.group(1))
            assert words.startswith("Cites: ")
            assert all(cited in words for cited in stored["cites"]), label


def test_each_claim_has_a_labels_line_of_chips(articles: dict[str, str]) -> None:
    """AC-38."""
    for inner in articles.values():
        claims = _claims(inner)
        for claim in claims:
            line = re.search(r'<p class="labels">(.*?)</p>', claim)
            assert line is not None
            assert line.group(1).startswith("Labels: ")
            rest = line.group(1).removeprefix("Labels: ")
            assert re.fullmatch(
                r'<span class="chip">[^<]+</span>( <span class="chip">[^<]+</span>)*', rest
            )


def test_the_page_links_nowhere_into_docs(page: str) -> None:
    """AC-62."""
    links = re.findall(r'href="([^"]*)"', page)

    assert not [link for link in links if re.search(r"tracepath/(?:blob|tree)/[^/]+/docs/", link)]
    assert not [link for link in links if link.startswith("docs/")]


def test_the_v1_finish_line_is_plain_text(page: str) -> None:
    """AC-63."""
    assert "I also marked them right (v1 finish line).</p>" in page
    assert ">v1 finish line</a>" not in page


def test_the_marks_are_pinned() -> None:
    """AC-64: 17 right, 2 partly right, 2 wrong, 10 declined, on 2026-10-26."""
    assert {entry["label"]: entry["mark"] for entry in _marks()} == MARKS_ON_2026_10_26
    assert sorted(MARKS_ON_2026_10_26.values()).count("right") == 17


def test_the_strip_is_a_hidden_button_right_inside_the_article(articles: dict[str, str]) -> None:
    """AC-65, AC-93, AC-94, AC-95: a direct child after the source line, before the claims."""
    for label, inner in articles.items():
        children = _children(inner)
        buttons = [attrs for tag, attrs in children if tag == "button"]
        assert len(buttons) == 1, label
        assert buttons[0]["data-graph"] == slug_of(label)
        assert "hidden" in buttons[0]
        tags = [(tag, attrs.get("class")) for tag, attrs in children]
        ruling = tags.index(("div", "ruling"))
        assert tags[ruling + 1] == ("button", "strip"), label
        assert tags[ruling + 2][0] in ("ol", "p"), label
        assert inner.index('<p class="source">') < inner.index(
            '<button type="button" class="strip"'
        )


def test_the_strip_reads_explore_the_graph_with_the_items_sent_counts(
    articles: dict[str, str],
) -> None:
    """AC-66, AC-67, AC-97."""
    for label, record in _records().items():
        sent, cited = len(record["items"]), len(_cited(record))
        strip = _strip(articles[label])
        assert '<span class="strip-title">Explore the graph</span>' in strip
        assert f'<span class="strip-counts">{sent} sent · {cited} cited</span>' in strip
        assert f"<summary>Show all ({sent}, {cited} cited)" in articles[label]
        name = re.search(r'aria-label="([^"]*)"', strip)
        assert name is not None
        assert unescape(name.group(1)) == f"Explore the graph: {label}, {sent} sent, {cited} cited"


def test_the_strip_drawing_is_the_same_in_every_entry(articles: dict[str, str]) -> None:
    """AC-68."""
    drawings = {
        re.search(r"<svg .*?</svg>", _strip(inner), flags=re.S).group()  # type: ignore[union-attr]
        for inner in articles.values()
    }

    assert drawings == {STRIP_DRAWING}


def test_the_strip_drawing_highlights_no_node() -> None:
    """AC-69: every dot the same size and the same ink."""
    assert set(re.findall(r'<circle [^>]*r="([^"]+)"', STRIP_DRAWING)) == {"1.8"}
    assert set(re.findall(r'<g fill="([^"]+)"', STRIP_DRAWING)) == {"rgba(1,25,54,.3)"}
    assert "fill=" not in "".join(re.findall(r"<circle [^>]*>", STRIP_DRAWING))


def test_the_script_finds_the_cloned_parts_anywhere_in_the_entry() -> None:
    """AC-76."""
    script = GRAPH_SCRIPT.read_text(encoding="utf-8")
    view = script[script.index("function showAnswer(") : script.index("function twoDigits(")]

    assert ":scope" not in view
    assert 'for (const part of [".question", ".verdict", "ol"])' in view
    assert "state.article.querySelector(part)" in view


def test_each_entry_holds_one_question_one_verdict_and_at_most_one_list(
    articles: dict[str, str],
) -> None:
    """AC-77, AC-103, AC-104."""
    for label, inner in articles.items():
        assert _class_count(inner, "question") == 1, label
        assert _class_count(inner, "verdict") == 1, label
        assert inner.count("<ol") <= 1, label
