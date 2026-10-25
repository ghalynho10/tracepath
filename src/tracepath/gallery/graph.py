"""Each shown answer's graph data, every item's state decided here (spec 0011). Pure.

The page's script only draws from these flags; it decides nothing about an item.
"""

import json
import re

from pydantic import BaseModel, ConfigDict

from tracepath.gallery.citations import ItemLine, item_link
from tracepath.gallery.records import Entry, GalleryError, Section

#: A cited item's radius, in pixels at the starting scale (AC-14).
CITED_RADIUS = 9.0

#: Any other item's radius (AC-16).
OTHER_RADIUS = 3.5

#: The type of an unresolved name's stored line (AC-61).
UNRESOLVED_TYPE = "unresolved"

_NOT_SLUG = re.compile(r"[^a-z0-9]+")

#: Characters a data block writes as `\u` escapes, so stored text cannot close the
#: script element or end a line inside it (AC-69).
_ESCAPES = str.maketrans(
    {
        "<": "\\u003c",
        ">": "\\u003e",
        "&": "\\u0026",
        "\u2028": "\\u2028",
        "\u2029": "\\u2029",
    }
)


class GraphItem(BaseModel):
    """One item as the page draws it, its state already decided."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: str
    text: str
    hop: int
    cited: bool
    held: bool
    unresolved: bool
    radius: float
    marker: str | None
    cited_by: tuple[int, ...]
    neighbours: tuple[str, ...]
    near_cited: bool
    link_ids: tuple[int, ...]
    source: str | None
    location: str


class GraphLink(BaseModel):
    """One stored link; `drawn` is false for a link from an item to itself."""

    model_config = ConfigDict(frozen=True)

    type: str
    source: str
    target: str
    phrase: str | None
    held: bool
    drawn: bool


class EntryGraph(BaseModel):
    """One entry's graph: its place in page order and every item and link of its record."""

    model_config = ConfigDict(frozen=True)

    slug: str
    label: str
    position: int
    total: int
    previous: str | None
    next: str | None
    cited_count: int
    items: tuple[GraphItem, ...]
    links: tuple[GraphLink, ...]


def slug_of(label: str) -> str:
    """The label lowercased, each run of other than ASCII letters and digits one `-`."""
    return _NOT_SLUG.sub("-", label.lower()).strip("-")


def page_order(entries: tuple[Entry, ...]) -> tuple[Entry, ...]:
    """The entries as the page shows them: sections in order, each in marks file order."""
    return tuple(entry for section in Section for entry in entries if entry.section is section)


def location(item: ItemLine) -> str:
    """The words the page shows for an item's location, as the list's `_link` does."""
    if item.file is None:
        return "no file stored"
    return f"{item.file}, whole file" if item.line is None else f"{item.file}:{item.line}"


def _cited_by(entry: Entry) -> dict[str, tuple[int, ...]]:
    """Each cited id, with the numbers of the claims that cite it and do not reject it."""
    numbers: dict[str, list[int]] = {}
    for number, claim in enumerate(entry.record.claims, start=1):
        for cited in dict.fromkeys(claim.cites):
            if cited not in claim.rejected_ids:
                numbers.setdefault(cited, []).append(number)
    return {cited: tuple(found) for cited, found in numbers.items()}


def _neighbours(item: str, links: tuple[GraphLink, ...]) -> tuple[str, ...]:
    """The distinct other ends of the item's links, in first link order, never itself."""
    ends = (
        link.target if link.source == item else link.source
        for link in links
        if item in (link.source, link.target)
    )
    return tuple(dict.fromkeys(end for end in ends if end != item))


def entry_graph(
    entry: Entry, slug: str, position: int, total: int, previous: str | None, next: str | None
) -> EntryGraph:
    """One entry's graph data, every flag computed from its record (AC-57 to AC-64)."""
    record = entry.record
    links = tuple(
        GraphLink(
            type=link.type,
            source=link.source,
            target=link.target,
            phrase=link.phrase,
            held=link.held,
            drawn=link.source != link.target,
        )
        for link in record.links
    )
    cited_by = _cited_by(entry)
    neighbours = {item.id: _neighbours(item.id, links) for item in record.items}
    lines = dict(zip((item.id for item in record.items), entry.items, strict=True))
    items = tuple(
        GraphItem(
            id=item.id,
            type=lines[item.id].type,
            text=item.text,
            hop=item.hop,
            cited=item.id in cited_by,
            held=item.held,
            unresolved=lines[item.id].type == UNRESOLVED_TYPE,
            radius=CITED_RADIUS if item.id in cited_by else OTHER_RADIUS,
            marker=lines[item.id].marker,
            cited_by=cited_by.get(item.id, ()),
            neighbours=neighbours[item.id],
            near_cited=item.id in cited_by or any(n in cited_by for n in neighbours[item.id]),
            link_ids=tuple(
                number for number, link in enumerate(links) if item.id in (link.source, link.target)
            ),
            source=item_link(lines[item.id]),
            location=location(lines[item.id]),
        )
        for item in sorted(record.items, key=lambda i: (i.id not in cited_by, i.hop, i.id))
    )
    return EntryGraph(
        slug=slug,
        label=entry.marks.label,
        position=position,
        total=total,
        previous=previous,
        next=next,
        cited_count=sum(1 for item in items if item.cited),
        items=items,
        links=links,
    )


def entry_graphs(entries: tuple[Entry, ...]) -> tuple[EntryGraph, ...]:
    """Every entry's graph, in page order, each slug unique and never empty (AC-67)."""
    ordered = page_order(entries)
    slugs = tuple(slug_of(entry.marks.label) for entry in ordered)
    for number, (entry, slug) in enumerate(zip(ordered, slugs, strict=True)):
        if not slug:
            raise GalleryError(f"{entry.marks.label!r}: its label makes an empty slug")
        if slug in slugs[:number]:
            first = ordered[slugs.index(slug)]
            raise GalleryError(
                f"{first.marks.label!r} and {entry.marks.label!r} both make the slug {slug!r}"
            )
    total = len(ordered)
    return tuple(
        entry_graph(
            entry,
            slug,
            number,
            total,
            slugs[number - 2] if number > 1 else None,
            slugs[number] if number < total else None,
        )
        for number, (entry, slug) in enumerate(zip(ordered, slugs, strict=True), start=1)
    )


def data_block(graph: EntryGraph) -> str:
    """The graph as JSON safe inside a script element: no `<`, `>`, `&` or line separator."""
    text = json.dumps(graph.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    return text.translate(_ESCAPES)
