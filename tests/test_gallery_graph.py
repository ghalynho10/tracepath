"""The answer graph (spec 0011): the data blocks, the inlined libraries and the button."""

import json
import re
import shutil
from collections.abc import Callable
from html import unescape
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tracepath.ask.record import ASKS_DIR
from tracepath.cli import app
from tracepath.gallery.citations import parse_item_line
from tracepath.gallery.graph import (
    CITED_RADIUS,
    OTHER_RADIUS,
    EntryGraph,
    GraphItem,
    data_block,
    slug_of,
)
from tracepath.gallery.inline import has_pair, runs
from tracepath.gallery.records import (
    GRAPH_SCRIPT,
    MARKS_FILE,
    SNAPSHOT_DOCS,
    VENDOR_DIR,
    VENDOR_PACKAGES,
    GalleryError,
    read_scripts,
)
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
    """AC-1, AC-2 as amended: one strip per entry, hidden until the script shows it."""
    articles = _articles(page)
    buttons = [re.findall(r"<button [^>]*data-graph=[^>]*>", article) for article in articles]

    assert len(articles) == len(_records())
    assert all(len(found) == 1 for found in buttons)
    assert all(re.search(r'\bdata-graph="[a-z0-9-]+"', b[0]) for b in buttons)
    assert all(b[0].endswith(" hidden>") for b in buttons)
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


def test_neighbours_are_every_other_item_a_stored_link_joins(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-62."""
    for record, _, item in _each_item(blocks):
        assert set(item["neighbours"]) == set(_neighbours(record, item["id"]))


def test_neighbours_list_each_id_once(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-97."""
    for _, _, item in _each_item(blocks):
        assert len(item["neighbours"]) == len(set(item["neighbours"]))


def test_neighbours_come_in_first_link_order(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-98."""
    for record, _, item in _each_item(blocks):
        assert item["neighbours"] == _neighbours(record, item["id"])


def test_an_item_is_never_its_own_neighbour(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-99, on the 23 items with a link to themselves and every other."""
    looped = 0
    for record, _, item in _each_item(blocks):
        looped += any(k["source"] == k["target"] == item["id"] for k in record["links"])
        assert item["id"] not in item["neighbours"]
    assert looped > 0


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
    """AC-97's edge: a pair joined twice lists that neighbour once."""
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


@pytest.mark.parametrize(
    "names",
    [
        pytest.param(("--yellow", "#F6E27F", "yellow"), id="yellow"),
        pytest.param(("--pink", "#FFC8C2", "pink"), id="pink"),
    ],
)
def test_graph_styles_use_no_mark_colour(names: tuple[str, ...]) -> None:
    """AC-22 (yellow), AC-95 (pink): the canvas and key use neither colour of the marks."""
    style = GRAPH_STYLE + DIALOG + GRAPH_SCRIPT.read_text(encoding="utf-8")

    for colour in names:
        assert colour.lower() not in style.lower()


def test_graph_styles_use_cyan_only_for_the_selection_ring() -> None:
    """AC-96."""
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
    """AC-53, spec 0012 AC-78: the panel is filled with textContent, runs included; no call
    parses a string as markup, and `innerHTML` is never set."""
    script = GRAPH_SCRIPT.read_text(encoding="utf-8")

    for parser in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser"):
        assert parser not in script


def test_the_panels_source_link_opens_in_a_new_tab() -> None:
    """AC-103, statically: the item view's link to JobHunt sets a new tab, without an opener."""
    script = GRAPH_SCRIPT.read_text(encoding="utf-8")
    view = script[script.index("function showItem(") :]

    assert 'link.target = "_blank";' in view
    assert 'link.rel = "noopener";' in view


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


#: Two real records for the guard fixtures: eval question 1, and held out question 3.
DEV = "2026-10-20T17-36-09Z-eval-linked-records-research-q1.json"
HELD = "2026-10-19T22-17-49Z-eval-held-out-q3.json"

#: Stored text that would break a page that did not escape it (AC-53, AC-69, AC-70).
HOSTILE = "a </script><script>alert(1)</script> <figure> & \u2028 \u2029 <!-- b </SCRIPT"


def _fixture(tmp_path: Path, entries: tuple[tuple[str, str, str], ...]) -> Path:
    """A repository root holding `entries` (record, label, section) and their snapshot files."""
    root = tmp_path / "repo"
    (root / ASKS_DIR).mkdir(parents=True)
    (root / MARKS_FILE).parent.mkdir(parents=True)
    marks = []
    for record, label, section in entries:
        shutil.copy(PROJECT_ROOT / ASKS_DIR / record, root / ASKS_DIR / record)
        for item in json.loads((root / ASKS_DIR / record).read_text(encoding="utf-8"))["items"]:
            line = parse_item_line(item["line"])
            assert line is not None
            if line.file is not None:
                target = root / SNAPSHOT_DOCS / line.file
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(PROJECT_ROOT / SNAPSHOT_DOCS / line.file, target)
        marks.append(
            {
                "record": record,
                "label": label,
                "section": section,
                "mark": "right",
                "note": None,
                "source_path": "docs/scope/scope.md",
                "source_row": "fixture",
            }
        )
    (root / MARKS_FILE).write_text(json.dumps(marks), encoding="utf-8")
    return root


def _edit(root: Path, record: str, change: Callable[[dict[str, Any]], None]) -> None:
    path = root / ASKS_DIR / record
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _build_at(root: Path, out: Path) -> tuple[int, str]:
    result = CliRunner().invoke(app, ["gallery", "build", "--out", str(out), "--root", str(root)])
    return result.exit_code, " ".join(result.output.split())


def test_build_fails_on_a_link_whose_end_is_not_an_item(tmp_path: Path) -> None:
    """AC-65: exit 1, naming the record and the link."""
    root = _fixture(tmp_path, ((DEV, "Eval 1", "development"),))

    def retarget(record: dict[str, Any]) -> None:
        record["links"][2]["target"] = "9999/AC-1"

    _edit(root, DEV, retarget)
    code, output = _build_at(root, tmp_path / "site")

    assert code == 1
    assert f"{DEV}: link 3 (" in output
    assert "names 9999/AC-1, which is not among the record's items" in output
    assert not (tmp_path / "site" / "index.html").exists()


def test_build_fails_on_two_items_with_one_id(tmp_path: Path) -> None:
    """AC-66: exit 1, naming the record and the id."""
    root = _fixture(tmp_path, ((DEV, "Eval 1", "development"),))
    repeated = json.loads((root / ASKS_DIR / DEV).read_text(encoding="utf-8"))["items"][1]

    def repeat(record: dict[str, Any]) -> None:
        record["items"].append(dict(record["items"][1]))

    _edit(root, DEV, repeat)
    code, output = _build_at(root, tmp_path / "site")

    assert code == 1
    assert f"{DEV}: item id repeated: {repeated['id']}" in output
    assert not (tmp_path / "site" / "index.html").exists()


def test_build_fails_on_two_labels_with_one_slug(tmp_path: Path) -> None:
    """AC-67: exit 1, naming both entries."""
    root = _fixture(tmp_path, ((DEV, "Eval 1", "development"), (HELD, "eval-1", "held out")))

    code, output = _build_at(root, tmp_path / "site")

    assert code == 1
    assert "'Eval 1' and 'eval-1' both make the slug 'eval-1'" in output
    assert not (tmp_path / "site" / "index.html").exists()


def _scripts_copy(tmp_path: Path) -> tuple[Path, Path]:
    vendor = tmp_path / "vendor"
    shutil.copytree(VENDOR_DIR, vendor)
    graph = tmp_path / "graph.js"
    shutil.copy(GRAPH_SCRIPT, graph)
    return vendor, graph


@pytest.mark.parametrize("breaker", ["</script>", "</SCRIPT", "</sCrIpT ", "<!--"])
@pytest.mark.parametrize("name", ["d3-timer.min.js", "d3-force.LICENSE", "graph.js"])
def test_an_inlined_script_that_could_break_out_is_refused(
    tmp_path: Path, breaker: str, name: str
) -> None:
    """AC-68: in any letter case, in a library, its licence, or the page's own script."""
    vendor, graph = _scripts_copy(tmp_path)
    path = graph if name == "graph.js" else vendor / name
    path.write_text(path.read_text(encoding="utf-8") + f"\n// {breaker}\n", encoding="utf-8")

    with pytest.raises(GalleryError, match=re.escape(str(path))):
        read_scripts(vendor, graph)


def test_the_build_exits_1_naming_the_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-68 through the command: exit 1, the script named, no page written."""
    vendor, graph = _scripts_copy(tmp_path)
    graph.write_text("const x = '<!-- y';\n", encoding="utf-8")
    monkeypatch.setattr("tracepath.cli.read_scripts", lambda: read_scripts(vendor, graph))
    root = _fixture(tmp_path, ((DEV, "Eval 1", "development"),))

    code, output = _build_at(root, tmp_path / "site")

    assert code == 1
    assert f"{graph}: holds '<!--'" in output
    assert not (tmp_path / "site" / "index.html").exists()


def test_the_committed_scripts_are_accepted() -> None:
    """AC-68's other side: the vendored files and the script as committed pass the check."""
    scripts = read_scripts()

    assert len(scripts.libraries) == len(VENDOR_PACKAGES)


def _hostile_graph() -> EntryGraph:
    item = GraphItem(
        id="0001/AC-1",
        type="AcceptanceCriterion",
        text=HOSTILE,
        hop=0,
        cited=False,
        held=False,
        unresolved=False,
        radius=OTHER_RADIUS,
        marker=None,
        cited_by=(),
        cite_order=None,
        neighbours=(),
        near_cited=False,
        link_ids=(),
        source=None,
        location="no file stored",
    )
    return EntryGraph(
        slug="q1",
        label="Q1 <b>&",
        position=1,
        total=1,
        previous=None,
        next=None,
        cited_count=0,
        items=(item,),
        links=(),
    )


def test_a_data_block_writes_markup_characters_as_escapes() -> None:
    """AC-69: `<`, `>`, `&`, U+2028 and U+2029 never appear raw in a data block."""
    block = data_block(_hostile_graph())

    for raw in ("<", ">", "&", "\u2028", "\u2029"):
        assert raw not in block
    for escaped in ("\\u003c", "\\u003e", "\\u0026", "\\u2028", "\\u2029"):
        assert escaped in block


def test_a_data_block_parses_back_to_the_stored_text() -> None:
    """AC-70: parsing the block gives each stored text back exactly."""
    parsed = json.loads(data_block(_hostile_graph()))

    assert parsed["items"][0]["text"] == HOSTILE
    assert parsed["label"] == "Q1 <b>&"


def test_hostile_stored_text_survives_the_page(tmp_path: Path) -> None:
    """AC-53, AC-70 through a build: the text comes back whole from the page's data block."""
    root = _fixture(tmp_path, ((DEV, "Eval 1", "development"),))

    def hostile(record: dict[str, Any]) -> None:
        record["items"][4]["text"] = HOSTILE

    _edit(root, DEV, hostile)
    code, output = _build_at(root, tmp_path / "site")
    page = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    graph = json.loads(_BLOCK.findall(page)[0][1])

    assert code == 0, output
    assert HOSTILE in [item["text"] for item in graph["items"]]
    assert page.count("<script") == page.count("</script>")


def test_cite_order_is_the_order_of_first_citation(blocks: dict[str, dict[str, Any]]) -> None:
    """AC-94: claims in stored order, each claim's cites in stored order; null when not cited."""
    for label, record in _records().items():
        first: list[str] = []
        for claim in record["claims"]:
            for cited in claim["cites"]:
                if cited not in claim["rejected_ids"] and cited not in first:
                    first.append(cited)
        for item in blocks[label]["items"]:
            want = first.index(item["id"]) + 1 if item["id"] in first else None
            assert item["cite_order"] == want, (label, item["id"])


#: JobHunt's docs at the pinned commit, written out here rather than imported (AC-46).
PINNED_DOCS = (
    "https://github.com/ghalynho10/JobHunt/blob/2e40bcfe1078cc93ab2f951e6c7c708e4825aa1b/docs/"
)


def _location(stored_line: str) -> tuple[str, str | None]:
    """The words and the JobHunt link an item's stored line should give, rebuilt by hand."""
    place = stored_line.lstrip(" ").split("  ")[-2]
    if place in ("no file stored", "no path stored"):
        return "no file stored", None
    found = re.fullmatch(r"(.+):(\d+)", place)
    if found is None:
        return f"{place}, whole file", PINNED_DOCS + place
    return place, f"{PINNED_DOCS}{found.group(1)}?plain=1#L{found.group(2)}"


def test_location_and_source_are_read_from_the_stored_line(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """AC-46, AC-44 on the data: the panel's location, its JobHunt link and the marker."""
    for _, stored, item in _each_item(blocks):
        line = parse_item_line(stored["line"])
        assert line is not None
        assert (item["location"], item["source"]) == _location(stored["line"]), item["id"]
        assert item["marker"] == line.marker
    seven = next(i for i in blocks["Eval 1"]["items"] if i["id"] == "0008/AC-7")
    assert seven["location"] == "specs/0008-app-shell-and-navigation/index.md:54"
    assert seven["source"] == (
        f"{PINNED_DOCS}specs/0008-app-shell-and-navigation/index.md?plain=1#L54"
    )


def _set_place(item: dict[str, Any], place: str) -> None:
    fields = item["line"].split("  ")
    item["line"] = "  ".join([*fields[:-2], place, fields[-1]])


def _fixture_items(tmp_path: Path, change: Callable[[dict[str, Any]], None]) -> str:
    """Eval 1 alone, changed by `change`, built; returns the built page."""
    root = _fixture(tmp_path, ((DEV, "Eval 1", "development"),))
    _edit(root, DEV, change)
    code, output = _build_at(root, tmp_path / "site")
    assert code == 0, output
    return (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


def _block_items(page: str) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in json.loads(_BLOCK.findall(page)[0][1])["items"]}


def test_an_item_with_no_file_shows_no_link_and_a_file_with_no_line_shows_whole_file(
    tmp_path: Path,
) -> None:
    """AC-47, and AC-46's whole file form: the words and link come from the changed line."""
    nameless = "0008#consequences:24"
    whole = "0021#feature-design:13"

    def change(record: dict[str, Any]) -> None:
        by_id = {item["id"]: item for item in record["items"]}
        _set_place(by_id[nameless], "no file stored")
        _set_place(by_id[whole], "specs/0021-seeded-demo-account/index.md")

    items = _block_items(_fixture_items(tmp_path, change))

    assert (items[nameless]["location"], items[nameless]["source"]) == ("no file stored", None)
    assert items[whole]["location"] == "specs/0021-seeded-demo-account/index.md, whole file"
    assert items[whole]["source"] == f"{PINNED_DOCS}specs/0021-seeded-demo-account/index.md"


def test_a_rejected_or_repeated_citation_counts_once_and_only_where_not_rejected(
    tmp_path: Path,
) -> None:
    """AC-59, AC-64, AC-94, AC-41: rejection is per claim, and a repeat counts once."""
    only_rejected = "feature-14#14-fit-scoring-with-shown-reasoning-done-ga:8"
    rejected_then_cited = "0001#binding-rules:30"

    def change(record: dict[str, Any]) -> None:
        first, second, _, fourth = record["claims"]
        first["cites"] += [only_rejected, rejected_then_cited]
        first["rejected_ids"] += [only_rejected, rejected_then_cited]
        second["cites"].append("0008/AC-7")
        fourth["cites"].append(rejected_then_cited)

    page = _fixture_items(tmp_path, change)
    items = _block_items(page)

    assert items[only_rejected]["cited"] is False
    assert items[only_rejected]["cited_by"] == []
    assert items[only_rejected]["cite_order"] is None
    assert items[only_rejected]["radius"] == OTHER_RADIUS
    assert items[rejected_then_cited]["cited"] is True
    assert items[rejected_then_cited]["cited_by"] == [4]
    assert items[rejected_then_cited]["cite_order"] == 6
    assert items["0008/AC-7"]["cited_by"] == [1, 2]
    assert f'data-item="{only_rejected}"' not in page
    assert page.count(f'data-item="{rejected_then_cited}"') == 1


def test_build_fails_on_a_label_that_makes_no_slug(tmp_path: Path) -> None:
    """The data model's rule: a slug is never empty, so the build fails, naming the entry."""
    root = _fixture(tmp_path, ((DEV, "***", "development"),))

    code, output = _build_at(root, tmp_path / "site")

    assert code == 1
    assert "'***': its label makes an empty slug" in output
    assert not (tmp_path / "site" / "index.html").exists()


def _flags(text: str) -> list[list[Any]] | None:
    """The `runs` a data block should hold for a text: explicit markers only, or none."""
    found = runs(text)
    if not has_pair(found):
        return None
    return [[run.text, int(run.code) + 2 * int(run.bold)] for run in found]


def test_an_item_carries_runs_exactly_when_its_text_holds_a_marker_pair(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """Spec 0012 AC-79, AC-98, AC-19 (the data the panel draws), AC-28 (no code words)."""
    items = [item for graph in blocks.values() for item in graph["items"]]

    for item in items:
        assert item.get("runs") == _flags(item["text"]), item["id"]
    assert any("runs" in item for item in items)
    assert any("runs" not in item for item in items)


@pytest.mark.parametrize(
    ("label", "item", "run"),
    [
        pytest.param("Held out 2", "0021#feature-design:25", ["skillCounts", 3], id="bold code"),
        pytest.param(
            "Held out 2",
            "0017#build-plan:2",
            ['include: ["test/eval/**/*.test.ts"]', 1],
            id="stars inside code",
        ),
    ],
)
def test_a_real_item_carries_its_runs(
    blocks: dict[str, dict[str, Any]], label: str, item: str, run: list[Any]
) -> None:
    """Spec 0012 AC-3, AC-4, AC-79 on the real records the spec names."""
    found = next(i for i in blocks[label]["items"] if i["id"] == item)

    assert run in found["runs"]


def test_a_real_item_keeps_double_backticks_and_single_stars_as_typed(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """Spec 0012 AC-7 (Held out 2, 0017#build-plan:4) and AC-8 (Eval 1, 0021#feature-design:13)."""
    double = next(i for i in blocks["Held out 2"]["items"] if i["id"] == "0017#build-plan:4")
    single = next(i for i in blocks["Eval 1"]["items"] if i["id"] == "0021#feature-design:13")

    assert any("``" in text for text, flags in double["runs"] if not flags)
    assert any(
        "*succeeds and returns nothing*" in text for text, flags in single["runs"] if not flags
    )


def test_a_link_carries_phrase_runs_exactly_when_its_phrase_holds_a_marker_pair(
    blocks: dict[str, dict[str, Any]],
) -> None:
    """Spec 0012 AC-99 (explicit markers only), AC-100, AC-101."""
    links = [link for graph in blocks.values() for link in graph["links"]]

    for link in links:
        expected = None if link["phrase"] is None else _flags(link["phrase"])
        assert link.get("phrase_runs") == expected, link
    assert sum("phrase_runs" in link for link in links) == 1579
    assert any("phrase_runs" not in link and link["phrase"] for link in links)
