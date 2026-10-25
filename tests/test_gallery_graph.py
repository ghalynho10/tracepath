"""The answer graph (spec 0011): the data blocks, the inlined libraries and the button."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.graph import slug_of
from tracepath.gallery.records import GRAPH_SCRIPT, MARKS_FILE, VENDOR_DIR, VENDOR_PACKAGES
from tracepath.gallery.render import STYLE

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The versions the Decision pins (spec 0011).
VERSIONS = {
    "d3-dispatch": "3.0.1",
    "d3-quadtree": "3.0.1",
    "d3-timer": "3.0.1",
    "d3-force": "3.0.0",
}

_BLOCK = re.compile(r'<script type="application/json" id="graph-([a-z0-9-]+)">(.*?)</script>', re.S)


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> str:
    """The page built from the committed records and marks file."""
    out = tmp_path_factory.mktemp("site")
    result = CliRunner().invoke(
        app, ["gallery", "build", "--out", str(out), "--root", str(PROJECT_ROOT)]
    )
    assert result.exit_code == 0, result.output
    return (out / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def blocks(page: str) -> dict[str, dict[str, Any]]:
    """Each data block, parsed, by its entry's label."""
    parsed = [json.loads(data) for _, data in _BLOCK.findall(page)]
    return {graph["label"]: graph for graph in parsed}


def _records() -> dict[str, dict[str, Any]]:
    """Each shown record, by its marks entry's label."""
    marks = json.loads((PROJECT_ROOT / MARKS_FILE).read_text(encoding="utf-8"))
    return {
        entry["label"]: json.loads(
            (PROJECT_ROOT / ASKS_DIR / entry["record"]).read_text(encoding="utf-8")
        )
        for entry in marks
    }


def _articles(page: str) -> list[str]:
    return [a.split("</article>")[0] for a in page.split("<article>")[1:]]


@pytest.mark.parametrize(
    ("label", "slug"), [("Eval 3", "eval-3"), ("Held out 2", "held-out-2"), ("Q7", "q7")]
)
def test_slug_follows_the_rule_of_the_data_model(label: str, slug: str) -> None:
    """The slug rule's own examples."""
    assert slug_of(label) == slug


def test_every_entry_has_one_graph_button_written_hidden(page: str) -> None:
    """AC-1, AC-2: one Graph button per entry, hidden until the script shows it."""
    articles = _articles(page)
    buttons = [re.findall(r"<button [^>]*>Graph</button>", article) for article in articles]

    assert len(articles) == len(_records())
    assert all(len(found) == 1 for found in buttons)
    assert all(re.search(r'\bdata-graph="[a-z0-9-]+"', b[0]) for b in buttons)
    assert all(b[0].endswith(" hidden>Graph</button>") for b in buttons)
    assert "[hidden] { display: none !important; }" in STYLE


def test_one_data_block_per_entry(page: str, blocks: dict[str, dict[str, Any]]) -> None:
    """AC-57: each entry carries one data block, named by its slug."""
    slugs = [slug for slug, _ in _BLOCK.findall(page)]

    assert set(blocks) == set(_records())
    assert len(slugs) == len(set(slugs)) == len(blocks)
    assert all(blocks[label]["slug"] == slug_of(label) for label in blocks)


def test_data_block_holds_every_stored_item_and_no_other(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-57, AC-12: one item per stored item, with its id, text, hop and held."""
    for label, record in _records().items():
        shown = sorted((i["id"], i["text"], i["hop"], i["held"]) for i in blocks[label]["items"])
        stored = sorted((i["id"], i["text"], i["hop"], i["held"]) for i in record["items"])
        assert shown == stored, label


def test_data_block_holds_every_stored_link_in_order(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-57, AC-13: one link per stored link, in stored order, drawn unless a loop."""
    for label, record in _records().items():
        links = blocks[label]["links"]
        assert [
            {k: link[k] for k in ("type", "source", "target", "phrase", "held")} for link in links
        ] == record["links"], label
        assert [link["drawn"] for link in links] == [
            link["source"] != link["target"] for link in record["links"]
        ], label


def test_data_block_holds_no_stored_line(page: str, blocks: dict[str, dict[str, Any]]) -> None:
    """AC-58: no item carries its stored `line`, and no stored line is in any block."""
    data = "".join(json.dumps(graph, ensure_ascii=False) for graph in blocks.values())

    assert all("line" not in item for graph in blocks.values() for item in graph["items"])
    for record in _records().values():
        for item in record["items"]:
            assert item["line"] not in data


def _vendored(name: str) -> str:
    return (VENDOR_DIR / name).read_text(encoding="utf-8")


def test_page_inlines_the_four_libraries_in_dependency_order(page: str) -> None:
    """AC-71: d3-dispatch, d3-quadtree, d3-timer, d3-force, then the page's own script."""
    found = [page.find(_vendored(f"{name}.min.js")) for name in VENDOR_PACKAGES]
    script = page.find(GRAPH_SCRIPT.read_text(encoding="utf-8"))

    assert VENDOR_PACKAGES == ("d3-dispatch", "d3-quadtree", "d3-timer", "d3-force")
    assert -1 not in found
    assert found == sorted(found)
    assert script > found[-1]


def test_each_inlined_library_is_followed_by_its_licence(page: str) -> None:
    """AC-72: the licence the package ships, word for word, right after its file."""
    for name in VENDOR_PACKAGES:
        licence = _vendored(f"{name}.LICENSE")
        assert licence.startswith("Copyright 2010-2021 Mike Bostock")
        assert f"{_vendored(f'{name}.min.js')}\n/*\n{licence}*/</script>" in page


def _sources() -> list[dict[str, str]]:
    """The rows of `vendor/SOURCES.md`'s table, by its header."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in _vendored("SOURCES.md").splitlines()
        if line.startswith("|") and not line.startswith("|---")
    ]
    header, *body = rows
    return [dict(zip(header, row, strict=True)) for row in body]


def test_sources_lists_each_vendored_file_once(page: str) -> None:
    """AC-73: one row per file with its package, version, file name and source."""
    rows = _sources()

    assert [row["package"] for row in rows] == list(VENDOR_PACKAGES)
    for row in rows:
        package, version = row["package"], row["version"]
        assert version == VERSIONS[package]
        assert row["file"] == f"{package}.min.js"
        assert (VENDOR_DIR / row["file"]).is_file()
        assert row["url"] == (f"https://registry.npmjs.org/{package}/-/{package}-{version}.tgz")
        assert _vendored(row["file"]).startswith(
            f"// https://d3js.org/{package}/ v{version} Copyright"
        )


def test_page_refers_to_no_script_style_or_font_file(page: str) -> None:
    """AC-74: every script and style is inline; nothing names another file."""
    assert sorted(re.findall(r"<script[^>]*>", page)) == sorted(
        ["<script>"] * 5
        + [
            f'<script type="application/json" id="graph-{slug}">'
            for slug, _ in _BLOCK.findall(page)
        ]
    )
    assert "<link" not in page
    assert "@import" not in page
    assert "url(" not in page
    assert not re.search(r'\b(src|href)="(?!https://|#)', page)
