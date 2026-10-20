"""The items a question is answered from: search words, scores, neighbours, history.

Pure (spec 0009 AC-7 to AC-14b, key invariant 3): the same slice and question always
make the same pack. Code picks the search words; no model call is made here.
"""

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from tracepath.extract.schema import RelationshipType
from tracepath.traverse.graph_slice import GraphSlice, Link, Node, NodeKind

#: Words that carry no meaning in a why question (AC-7).
STOPLIST = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "rather",
        "than",
        "that",
        "the",
        "their",
        "there",
        "these",
        "this",
        "those",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "would",
    }
)

#: The shortest word kept unless it holds a digit, and the shortest part of a joined token.
MIN_WORD = 3

#: The most hits (AC-9), the hops followed from them (AC-10), and the most items sent (AC-11).
HIT_LIMIT = 16
HOPS = 2
ITEM_LIMIT = 90

#: The links whose source is history: both run old to new (AC-14). `amended-by` is not one.
HISTORY_LINKS = frozenset({RelationshipType.SUPERSEDED_BY.name, RelationshipType.CORRECTED_BY.name})

_SPLIT = re.compile(r"[\s/]+")
_JOINED = re.compile(r"[-_.]")


@dataclass(frozen=True)
class Item:
    """One node sent to the model: how it was reached, and whether it is history.

    `hop` is 0 for a hit. `replaced_by` names what a `superseded-by` or `corrected-by`
    link says replaces it, in the whole graph, held or accepted.
    """

    node: Node
    hop: int
    score: float
    history: bool
    replaced_by: tuple[str, ...]


@dataclass(frozen=True)
class Pack:
    """Everything one question sends: its words, its items in order, the links among them."""

    question: str
    words: tuple[str, ...]
    items: tuple[Item, ...]
    links: tuple[Link, ...]
    cut: int

    @property
    def hits(self) -> int:
        """How many items were found by their own words."""
        return sum(1 for item in self.items if item.hop == 0)

    @property
    def ids(self) -> frozenset[str]:
        """The canonical id of every item sent."""
        return frozenset(item.node.canonical_id for item in self.items)


def _stripped(token: str) -> str:
    """A token with every character that is not a letter or digit cut from both ends."""
    start, end = 0, len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[start:end]


def _kept(word: str) -> bool:
    if not word or word in STOPLIST:
        return False
    return len(word) >= MIN_WORD or any(ch.isdigit() for ch in word)


def tokenise(text: str) -> tuple[str, ...]:
    """The distinct words of `text`, in the order they first appear (AC-7).

    Lowercased, split on whitespace and `/`, each token's end punctuation stripped. A
    token holding a hyphen, underscore or dot is kept whole, and its parts of
    `MIN_WORD` or more characters are words too.
    """
    words: dict[str, None] = {}
    for raw in _SPLIT.split(text.lower()):
        token = _stripped(raw)
        if _kept(token):
            words.setdefault(token)
        if _JOINED.search(token):
            for part in (_stripped(p) for p in _JOINED.split(token)):
                if len(part) >= MIN_WORD and _kept(part):
                    words.setdefault(part)
    return tuple(words)


def _own_text(node: Node) -> str | None:
    """An entity's text, a Record's title, an Unresolved node's mention."""
    if node.kind is NodeKind.ENTITY:
        return node.text
    if node.kind is NodeKind.RECORD:
        return node.title
    return node.mention


def searchable(node: Node) -> frozenset[str]:
    """The words a node is found by: its own text joined with its canonical id (AC-8)."""
    return frozenset(tokenise(f"{_own_text(node) or ''} {node.canonical_id}"))


def scored(graph: GraphSlice, words: Iterable[str]) -> tuple[tuple[Node, float], ...]:
    """Every node with its score, highest first, ties by canonical id (AC-8b).

    A node scores ln(N / df) for each distinct search word found in it, where N is the
    node count and df the number of nodes the word is found in.
    """
    found = {node.canonical_id: searchable(node) for node in graph.nodes}
    wanted = tuple(dict.fromkeys(words))
    df = Counter(word for word in wanted for tokens in found.values() if word in tokens)
    total = len(graph.nodes)
    ranked = (
        (
            node,
            sum(math.log(total / df[word]) for word in wanted if word in found[node.canonical_id]),
        )
        for node in graph.nodes
    )
    return tuple(sorted(ranked, key=lambda pair: (-pair[1], pair[0].canonical_id)))


def replacements(graph: GraphSlice) -> dict[str, tuple[str, ...]]:
    """What replaces each history link source, by its id, held links included (AC-14)."""
    replaced: dict[str, dict[str, None]] = {}
    for link in graph.links:
        if link.type in HISTORY_LINKS and link.source != link.target:
            replaced.setdefault(link.source, {}).setdefault(link.target)
    return {source: tuple(targets) for source, targets in replaced.items()}


def is_history(node: Node, replaced: Mapping[str, tuple[str, ...]]) -> bool:
    """Whether a node is history: struck, or the source of a history link (AC-14)."""
    return node.struck is True or node.canonical_id in replaced


def _neighbours(graph: GraphSlice, known: frozenset[str]) -> dict[str, tuple[str, ...]]:
    """Each node's typed link neighbours, either direction, in link order (AC-10)."""
    around: dict[str, dict[str, None]] = {}
    for link in graph.links:
        if link.source == link.target or not {link.source, link.target} <= known:
            continue
        around.setdefault(link.source, {}).setdefault(link.target)
        around.setdefault(link.target, {}).setdefault(link.source)
    return {node: tuple(others) for node, others in around.items()}


def _reached(
    hits: tuple[str, ...], around: Mapping[str, tuple[str, ...]]
) -> tuple[tuple[str, ...], dict[str, int]]:
    """Hits, then each hop in the order of the highest ranked hit that reached it (AC-11).

    Returns the ids in order and each id's hop.
    """
    hop = {node: 0 for node in hits}
    origin = {node: rank for rank, node in enumerate(hits)}
    ordered = list(hits)
    frontier = hits
    for distance in range(1, HOPS + 1):
        reached: dict[str, int] = {}
        for node in frontier:
            for other in around.get(node, ()):
                if other in hop:
                    continue
                reached[other] = min(reached.get(other, origin[node]), origin[node])
        layer = tuple(sorted(reached, key=lambda n: (reached[n], n)))
        for node in layer:
            hop[node] = distance
            origin[node] = reached[node]
        ordered += layer
        frontier = layer
    return tuple(ordered), hop


def build_pack(graph: GraphSlice, question: str) -> Pack:
    """The items and links one question sends to the model (AC-7 to AC-12b, AC-14b).

    The hits are the `HIT_LIMIT` best scoring nodes above 0, then their neighbours up to
    `HOPS` hops. A history item brings what replaces it in right behind it, counted
    against `ITEM_LIMIT`; an item whose replacements would not fit is cut, with every
    item after it. The cut counts every item left out, a replacement cut with its
    history item included (AC-11 note).
    """
    words = tokenise(question)
    nodes = {node.canonical_id: node for node in graph.nodes}
    ranked = scored(graph, words)
    score = {node.canonical_id: value for node, value in ranked}
    hits = tuple(node.canonical_id for node, value in ranked[:HIT_LIMIT] if value > 0)
    ordered, hop = _reached(hits, _neighbours(graph, frozenset(nodes)))
    replaced = replacements(graph)

    wanted: dict[str, int] = {}
    taken: dict[str, int] = {}
    full = False
    for node in ordered:
        if node in wanted:
            continue
        group = {node: hop[node]}
        queue = [node]
        while queue:
            current = queue.pop(0)
            for newer in replaced.get(current, ()):
                if newer in nodes and newer not in wanted and newer not in group:
                    group[newer] = hop.get(newer, group[current] + 1)
                    queue.append(newer)
        wanted.update(group)
        full = full or len(taken) + len(group) > ITEM_LIMIT
        if not full:
            taken.update(group)

    items = tuple(
        Item(
            node=nodes[node],
            hop=distance,
            score=score.get(node, 0.0),
            history=is_history(nodes[node], replaced),
            replaced_by=replaced.get(node, ()),
        )
        for node, distance in taken.items()
    )
    sent = frozenset(taken)
    return Pack(
        question=question,
        words=words,
        items=items,
        links=tuple(link for link in graph.links if {link.source, link.target} <= sent),
        cut=len(wanted) - len(taken),
    )


def _kind(node: Node) -> str:
    if node.kind is NodeKind.RECORD:
        return "record"
    if node.kind is NodeKind.UNRESOLVED:
        return "unresolved"
    return node.type or "untyped"


def _where(node: Node) -> str:
    """An item's citation: a Record's path, an Unresolved node's own line (AC-13)."""
    if node.kind is NodeKind.RECORD:
        return node.path or "no path stored"
    line = node.line if node.kind is NodeKind.UNRESOLVED else node.file_line
    if node.file is None:
        return "no file stored"
    return node.file if line is None else f"{node.file}:{line}"


def item_line(item: Item) -> str:
    """One item as printed: id, type, held or not, history, citation, how it was reached."""
    node = item.node
    parts = [node.canonical_id, _kind(node), "held" if node.held else "accepted"]
    if node.struck is True:
        parts.append("STRUCK")
    elif item.history:
        parts.append("HISTORY")
    parts += [_where(node), "hit" if item.hop == 0 else f"hop {item.hop}"]
    return "  " + "  ".join(parts)


def pack_lines(pack: Pack) -> tuple[str, ...]:
    """The search words and every item sent, as `ask` prints them before the answer."""
    words = ", ".join(pack.words) if pack.words else "none"
    lines = [f"Search words: {words}"]
    if not pack.items:
        return (*lines, "No item matches the search words, so no call is made.")
    lines.append(
        f"Items sent: {len(pack.items)} ({pack.hits} hits, {len(pack.items) - pack.hits} "
        f"neighbours, {pack.cut} cut)."
    )
    lines += [item_line(item) for item in pack.items]
    return tuple(lines)
