"""The answer graph (spec 0011): the data blocks, the inlined libraries and the button."""

import json
import re
from html import unescape
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.graph import CITED_RADIUS, OTHER_RADIUS, slug_of
from tracepath.gallery.records import GRAPH_SCRIPT, MARKS_FILE, VENDOR_DIR, VENDOR_PACKAGES
from tracepath.gallery.render import DIALOG, GRAPH_STYLE, KEY, STYLE

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
    assert not re.search(r"url\((?!#)", page)
    assert not re.search(r'\b(src|href)="(?!https://|#)', page)


def _cited_by(record: dict[str, Any]) -> dict[str, list[int]]:
    """Each id some claim cites without rejecting it, with those claims' numbers."""
    found: dict[str, list[int]] = {}
    for number, claim in enumerate(record["claims"], start=1):
        for cited in claim["cites"]:
            if cited in claim["rejected_ids"]:
                continue
            numbers = found.setdefault(cited, [])
            if number not in numbers:
                numbers.append(number)
    return found


def _neighbours(record: dict[str, Any], item: str) -> list[str]:
    found: list[str] = []
    for link in record["links"]:
        if link["source"] == item:
            other = link["target"]
        elif link["target"] == item:
            other = link["source"]
        else:
            continue
        if other != item and other not in found:
            found.append(other)
    return found


def _each_item(
    blocks: dict[str, dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Every shown item: its record, its stored item and its item in the data block."""
    rows = []
    for label, record in _records().items():
        stored = {item["id"]: item for item in record["items"]}
        rows += [(record, stored[item["id"]], item) for item in blocks[label]["items"]]
    return rows


def test_cited_is_a_citation_no_claim_rejects(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-59, with AC-14 and AC-16's radius: 9 when cited, 3.5 when not."""
    rows = _each_item(blocks)

    assert any(item["cited"] for _, _, item in rows)
    assert any(not item["cited"] for _, _, item in rows)
    for record, _, item in rows:
        assert item["cited"] == (item["id"] in _cited_by(record))
        assert (
            item["radius"]
            == (CITED_RADIUS if item["cited"] else OTHER_RADIUS)
            == (9 if item["cited"] else 3.5)
        )


def test_held_is_the_stored_held(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-60."""
    rows = _each_item(blocks)

    assert {item["held"] for _, _, item in rows} == {True, False}
    assert all(item["held"] is stored["held"] for _, stored, item in rows)


def test_unresolved_is_the_type_in_the_stored_line(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-61."""
    rows = _each_item(blocks)

    assert {item["unresolved"] for _, _, item in rows} == {True, False}
    for _, stored, item in rows:
        kind = stored["line"].lstrip(" ").split("  ")[1]
        assert item["unresolved"] == (kind == "unresolved")
        assert item["type"] == kind


def test_neighbours_are_the_distinct_other_ends_in_first_link_order(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-62."""
    for record, _, item in _each_item(blocks):
        assert item["neighbours"] == _neighbours(record, item["id"])


def test_near_cited_is_cited_or_next_to_a_cited_item(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-63."""
    rows = _each_item(blocks)

    assert any(item["near_cited"] and not item["cited"] for _, _, item in rows)
    assert any(not item["near_cited"] for _, _, item in rows)
    for record, _, item in rows:
        cited = _cited_by(record)
        assert item["near_cited"] == (
            item["id"] in cited or any(n in cited for n in _neighbours(record, item["id"]))
        )


def test_cited_by_is_the_numbers_of_the_claims_that_cite_it(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-64."""
    for record, _, item in _each_item(blocks):
        assert item["cited_by"] == _cited_by(record).get(item["id"], [])


def test_an_answer_citing_no_item_has_no_cited_item(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-24, AC-33 on the data: Q11 and Q16 cite none; the script reads `cited_count`."""
    none = {label for label, graph in blocks.items() if graph["cited_count"] == 0}

    assert none == {"Q11", "Q16"}
    for graph in blocks.values():
        assert graph["cited_count"] == sum(1 for item in graph["items"] if item["cited"])


def test_a_link_from_an_item_to_itself_is_listed_once_and_not_drawn(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-13, AC-50 on the data: a loop has `drawn` false and sits once in `link_ids`."""
    loops = 0
    for graph in blocks.values():
        for item in graph["items"]:
            own = [n for n in item["link_ids"] if graph["links"][n]["source"] == item["id"]]
            for number in own:
                link = graph["links"][number]
                if link["target"] == item["id"]:
                    loops += 1
                    assert link["drawn"] is False
                    assert item["link_ids"].count(number) == 1
                    assert item["id"] not in item["neighbours"]
    assert loops == 23


def test_two_links_between_two_items_make_one_neighbour(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-62's edge: a pair joined twice lists that neighbour once."""
    pairs = 0
    for graph in blocks.values():
        ends = [frozenset((k["source"], k["target"])) for k in graph["links"] if k["drawn"]]
        for pair in {p for p in ends if ends.count(p) > 1}:
            pairs += 1
            first, second = sorted(pair)
            item = next(i for i in graph["items"] if i["id"] == first)
            assert item["neighbours"].count(second) == 1
    assert pairs == 25


def _rules(style: str) -> list[str]:
    return [rule.strip() for rule in re.findall(r"[^{}]+\{[^{}]*\}", style)]


def test_graph_styles_use_no_mark_colour_and_cyan_only_for_the_selection_ring() -> None:
    """AC-22: the canvas and key use neither the yellow nor the pink of the marks."""
    style = GRAPH_STYLE + DIALOG + GRAPH_SCRIPT.read_text(encoding="utf-8")

    for colour in ("--yellow", "--pink", "#F6E27F", "#FFC8C2", "yellow", "pink"):
        assert colour.lower() not in style.lower()
    assert [rule.split("{")[0].strip() for rule in _rules(GRAPH_STYLE) if "--cyan" in rule] == [
        ".gw-ring"
    ]
    assert "cyan" not in (DIALOG + GRAPH_SCRIPT.read_text(encoding="utf-8")).lower()


def test_key_shows_the_six_drawings_outside_the_canvas() -> None:
    """AC-23: cited, not cited, held item, held link, unresolved name, selected."""
    drawings = dict(KEY)
    key = DIALOG.split('<ul class="gw-key"')[1]

    assert list(drawings) == [
        "Cited",
        "Not cited",
        "Held item",
        "Held link",
        "Unresolved name",
        "Selected",
    ]
    assert f'class="is-cited"><circle class="gw-dot" r="{CITED_RADIUS}"' in drawings["Cited"]
    assert f'class="is-other"><circle class="gw-dot" r="{OTHER_RADIUS}"' in drawings["Not cited"]
    assert 'class="gw-held"' in drawings["Held item"]
    assert 'class="gw-link is-held"' in drawings["Held link"]
    assert '<rect class="gw-dot"' in drawings["Unresolved name"]
    assert 'class="gw-ring"' in drawings["Selected"]
    assert all(f"{words}</li>" in key for words in drawings)
    assert DIALOG.index('<ul class="gw-key"') > DIALOG.index("</svg>", DIALOG.index("gw-canvas"))


def test_only_cited_unrejected_ids_carry_data_item(page: str) -> None:
    """AC-39, AC-41: each such id in a claim's citation link names its item; no other does."""
    records = _records()
    for article in _articles(page):
        label = unescape(re.findall(r'<h3><span class="stored">(.*?)</span></h3>', article)[0])
        listed = article.split("<ol>")[1].split("</ol>")[0] if "<ol>" in article else ""
        claims = re.findall(r"<li>.*?</li>", listed)
        stored = records[label]["claims"]
        assert len(claims) == len(stored), label
        for shown, claim in zip(claims, stored, strict=True):
            named = [unescape(found) for found in re.findall(r'data-item="([^"]*)"', shown)]
            cited = [c for c in dict.fromkeys(claim["cites"]) if c not in claim["rejected_ids"]]
            assert named == cited, label


def test_script_never_turns_text_into_markup() -> None:
    """AC-53: the panel is filled with textContent; no call parses a string as markup."""
    script = GRAPH_SCRIPT.read_text(encoding="utf-8")

    for parser in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser"):
        assert parser not in script


def test_graphs_follow_page_order(page: str, blocks: dict[str, dict[str, Any]]) -> None:
    """AC-7 to AC-11 on the data: `n / N`, and previous and next along the page's order."""
    marks = json.loads((PROJECT_ROOT / MARKS_FILE).read_text(encoding="utf-8"))
    sections = ("development", "held out", "realistic")
    order = [m["label"] for s in sections for m in marks if m["section"] == s]
    on_page = [unescape(h) for h in re.findall(r'<h3><span class="stored">(.*?)</span></h3>', page)]
    graphs = [blocks[label] for label in order]

    assert on_page == order
    assert [g["position"] for g in graphs] == list(range(1, len(order) + 1))
    assert {g["total"] for g in graphs} == {len(order)}
    assert [g["previous"] for g in graphs] == [None] + [g["slug"] for g in graphs[:-1]]
    assert [g["next"] for g in graphs] == [g["slug"] for g in graphs[1:]] + [None]


def test_items_come_in_a_fixed_order(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-76's input: cited items first, then by hop, then by id, so the layout repeats."""
    for graph in blocks.values():
        keys = [(not item["cited"], item["hop"], item["id"]) for item in graph["items"]]
        assert keys == sorted(keys), graph["label"]


def test_script_makes_no_request() -> None:
    """AC-75: the script fetches nothing; everything it reads is in the page."""
    script = GRAPH_SCRIPT.read_text(encoding="utf-8")

    for request in ("fetch(", "XMLHttpRequest", "import(", "new Image", "sendBeacon", "src"):
        assert request not in script
