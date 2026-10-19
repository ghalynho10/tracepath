"""The answer: its shape, the prompt it is asked with, and the checks code makes on it.

Pure (spec 0009 AC-15 to AC-20, key invariant 3). The model's reply is read as an
`Answer`; every mark printed beside a claim is set here by code, from the pack sent,
never from anything the model says about itself.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from tracepath.ask.retrieve import Item, Pack
from tracepath.extract.schema import RelationshipType
from tracepath.traverse.graph_slice import Link, NodeKind

#: The version of the instructions below, stored on every ask record.
PROMPT_VERSION = "ask-1"

#: The output cap of one ask call, thinking included (spec 0009, decided 2026-10-19).
ASK_MAX_TOKENS = 16_000

Verdict = Literal["answered", "partly", "not_supported"]
Basis = Literal["link", "text", "inferred"]


class Claim(BaseModel):
    """One claim of the answer, the ids it rests on, and how it rests on them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    cites: tuple[str, ...]
    basis: Basis


class Answer(BaseModel):
    """The structured reply the model is asked for (AC-15)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: Verdict
    claims: tuple[Claim, ...]
    missing: tuple[str, ...]


SYSTEM_PROMPT = """\
You answer a why question about one software project, using only the items you are \
given from its decision records.

You receive the question, then the items, each under its id in square brackets, then \
the typed links between those items. Each item is one statement read from a spec or \
the scope document.

Rules:
- Answer only from the items given. Never use outside knowledge, of this project or of \
software in general, to fill a gap.
- Every claim cites at least one item, by its id exactly as written between the square \
brackets. Cite only ids from the list.
- Set each claim's `basis`. `link`: the claim rests on a link listed between two of the \
items it cites; cite both ends. `text`: the claim rests on what an item's own text \
says. `inferred`: the claim connects items that no listed link joins and no item's \
text connects.
- An item marked HELD has not been reviewed. You may use it.
- An item marked HISTORY was struck through, or replaced by a later item. It no longer \
stands as written. When a claim uses a HISTORY item, say so in the claim itself, and \
when the item says what replaced it, name that item in the claim and cite it.
- `verdict` is `answered` when the claims answer the question, `partly` when they \
answer only part of it, and `not_supported` when the items do not support an answer.
- `missing` lists what the question needs that the items do not hold. Leave it empty \
when nothing is missing.
- Keep each claim to one or two sentences.
"""


def system_prompt() -> str:
    """The instructions every ask call is made with (AC-18b)."""
    return SYSTEM_PROMPT


def _flat(text: str | None) -> str:
    return " ".join((text or "").split())


def _item_block(item: Item) -> str:
    """One item as the model reads it: id, kind, held, history, then its text."""
    node = item.node
    if node.kind is NodeKind.RECORD:
        kind, where, text = "record", node.path, f"Title: {_flat(node.title)}"
    elif node.kind is NodeKind.UNRESOLVED:
        kind, where = "unresolved", node.file
        text = f"A name the records use that matches no item: {_flat(node.mention)}"
    else:
        kind, where, text = node.type or "untyped", node.file, _flat(node.text)
    marks = [kind, "HELD" if node.held else "accepted"]
    if item.history:
        struck = "struck through" if node.struck is True else "no longer stands"
        replaced = f", replaced by {', '.join(item.replaced_by)}" if item.replaced_by else ""
        marks.append(f"HISTORY ({struck}{replaced})")
    origin = f" from {where}" if where else ""
    return f"[{node.canonical_id}] {', '.join(marks)}{origin}\n{text}"


def _link_line(link: Link) -> str:
    name = (
        RelationshipType[link.type].value
        if link.type in RelationshipType.__members__
        else link.type
    )
    held = ", HELD" if link.held else ""
    phrase = f': "{_flat(link.phrase)}"' if link.phrase else ""
    return f"{link.source} {name} {link.target}{held}{phrase}"


def pack_message(pack: Pack) -> str:
    """The user message of one ask call: the question, the items, the links among them."""
    items = "\n\n".join(_item_block(item) for item in pack.items)
    links = "\n".join(_link_line(link) for link in pack.links) or "none"
    return (
        f"Question: {pack.question}\n\n"
        f"Items:\n\n{items}\n\n"
        f"Links between the items, each written source, type, target:\n{links}"
    )


@dataclass(frozen=True)
class CheckedClaim:
    """One claim with the marks code set on it (AC-16 to AC-19)."""

    claim: Claim
    rejected_ids: tuple[str, ...]
    uncited: bool
    inferred: bool
    history: bool
    held_ids: tuple[str, ...]


def _linked(cited: frozenset[str], links: tuple[Link, ...]) -> bool:
    """Whether a typed link sent joins two of the cited ids, either direction (AC-17)."""
    return any(link.source != link.target and {link.source, link.target} <= cited for link in links)


def check_claims(answer: Answer, pack: Pack) -> tuple[CheckedClaim, ...]:
    """Every claim checked against the pack sent: ids, links, history, held."""
    by_id = {item.node.canonical_id: item for item in pack.items}
    checked: list[CheckedClaim] = []
    for claim in answer.claims:
        cites = tuple(dict.fromkeys(claim.cites))
        found = tuple(c for c in cites if c in by_id)
        inferred = claim.basis == "inferred" or (
            claim.basis == "link" and not _linked(frozenset(found), pack.links)
        )
        checked.append(
            CheckedClaim(
                claim=claim,
                rejected_ids=tuple(c for c in cites if c not in by_id),
                uncited=not cites,
                inferred=inferred,
                history=any(by_id[c].history for c in found),
                held_ids=tuple(c for c in found if by_id[c].node.held),
            )
        )
    return tuple(checked)


def _claim_line(number: int, checked: CheckedClaim) -> str:
    """One claim as printed: its text, its ids, then its marks in AC-20's order."""
    held = set(checked.held_ids)
    cites = [f"[{c} held]" if c in held else f"[{c}]" for c in dict.fromkeys(checked.claim.cites)]
    marks: list[str] = []
    if checked.history:
        marks.append("HISTORY")
    if checked.inferred:
        marks.append("INFERRED")
    if checked.rejected_ids:
        marks.append(f"CITATION REJECTED: {', '.join(checked.rejected_ids)}")
    if checked.uncited:
        marks.append("UNCITED")
    if not checked.inferred:
        marks.append("link" if checked.claim.basis == "link" else "read from text")
    return "  " + " ".join([f"{number}.", _flat(checked.claim.text), *cites, *marks])


def answer_lines(answer: Answer, checked: tuple[CheckedClaim, ...]) -> tuple[str, ...]:
    """The answer as printed: the verdict, the numbered claims, then what is missing."""
    lines = [f"Answer (verdict: {answer.verdict}):"]
    lines += [_claim_line(n, claim) for n, claim in enumerate(checked, start=1)]
    if not checked:
        lines.append("  (no claims)")
    if answer.missing:
        lines.append(f"Missing: {'; '.join(_flat(m) for m in answer.missing)}")
    return tuple(lines)
