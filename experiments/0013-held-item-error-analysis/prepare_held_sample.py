"""Draw experiment 0013's blind sample of held items and write its packet, no API call.

Reads `artifacts/review-queue.json` and keeps only rows with one distinct reason name,
sorted into five groups by that reason and, for `runs_disagree`, by how many of the
three runs produced the row's signature:

- a: `runs_disagree`, in all three runs with differing counts;
- b: `runs_disagree`, in exactly two of three runs;
- c: `runs_disagree`, in exactly one of three runs;
- d: `known_trap_flag`, leaving out every item experiment 0012 drew;
- e: `endpoint_not_accepted`, one end waiting or both.

An item is left out when its source line falls inside a passage an expected chain step
of `eval/linked-records-research.json` cites: an entity by its own line, a link when
either local end's line does. Each group's population after the exclusions is printed
before any draw; a group with fewer than 4 takes all and states the shortfall.

Each row is joined to the rebuilt runs (`committed_units()`), which must reproduce the
committed queue, for its per run counts and its wording. The wording is the earliest
run's that holds the signature. Items are shuffled together under opaque ids, and the
packet shows only what ruling needs: an entity's span, type and source line; a link's
type, direction and both ends' spans and lines, with a cross unit end's exact words
and the entity they match, else `not resolved`. Nothing shows an item's group, reason,
run counts, model, or whether it or an end was accepted, held or waiting.

Three files are written under `data/`:

- `held-packet.md`, the packet the engineer rules;
- `held-arms.json`, the arm file: every seed, each item's group, per run counts, model
  and the run its wording came from. It stays uncommitted until the rulings are in;
- `held-arms.sha256`, the arm file's hash, committed before the rulings.

The seeds are drawn fresh by `secrets`, not written here, so the groups cannot be
recomputed from committed code before the arm file is committed. The script refuses to
run once any of the three files exists, so a sample is drawn once.

Run from the repository root: uv run python <this file>
"""

import hashlib
import json
import random
import re
import secrets
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tracepath.config import DEFAULT_MODEL
from tracepath.extract.compare import entity_signature, identities_of, relationship_signature
from tracepath.extract.ids import IdentifiedEntity
from tracepath.extract.schema import LocalEndpoint, ReferenceEndpoint, normalize_label
from tracepath.extract.units import Unit
from tracepath.measure import entity_mark
from tracepath.pipeline import UnitResult, resolve_accepted, review_rows
from tracepath.rebuild import committed_units, records_for_units
from tracepath.resolve.endpoints import LabelIndex, build_label_index

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"
QUEUE = ROOT / "artifacts" / "review-queue.json"
EVAL = ROOT / "eval" / "linked-records-research.json"
EARLIER_ARMS = (
    ROOT / "experiments" / "0012-extraction-accuracy-step-one" / "data" / "stage-one-arms.json"
)
PACKET = HERE / "data" / "held-packet.md"
ARMS = HERE / "data" / "held-arms.json"
HASH = HERE / "data" / "held-arms.sha256"

PER_GROUP = 4
GROUPS = ("a", "b", "c", "d", "e")

RUNS_DISAGREE = "runs_disagree"
KNOWN_TRAP_FLAG = "known_trap_flag"
ENDPOINT_NOT_ACCEPTED = "endpoint_not_accepted"

ENTITY = "entity"
LINK = "link"

IN_PASSAGE = "inside an eval chain passage"
DRAWN_BY_0012 = "drawn in experiment 0012"

#: The eval file's paths sit under the corpus root; a unit's path sits under `docs/`.
_DOCS = "docs/"

INTRO = """\
Experiment 0013, a blind error analysis. Each item is something the extraction produced
from the pinned JobHunt snapshot; source lines are relative to `corpus/jobhunt/docs/`.
The items are shuffled under opaque ids.

Rule each item by replacing its marks with one word:

- an entity: `agree` when its span is cut right and its type is right;
- a link: `agree` when its type, its direction (from, then to) and both ends are right;
- `disagree` otherwise, and write what it should have been after `should have been:`
  (the type, the direction or the ends);
- `unsure` when you cannot tell.

Write anything you notice after `note:`. For an end that names something outside its
own section, `words` are the exact words the text used and `target` the entity they
match in the corpus, or `not resolved` when they match none. There is no pass or fail:
the notes are read together afterwards."""


@dataclass(frozen=True)
class Passage:
    """Lines `start` to `end` of one file, both included, that an eval chain step cites."""

    file: str
    start: int
    end: int


@dataclass(frozen=True)
class Shown:
    """One thing the packet shows: an entity, or one end of a link.

    `words` is set only for an end naming something outside its section; `span` and
    `source` are then the entity those words match, both `None` when they match none.
    """

    span: str | None
    source: str | None
    words: str | None = None


@dataclass(frozen=True)
class HeldMark:
    """What the packet shows of one held item, and the local lines it is excluded by.

    An entity has one part, itself; a link has two, its source end then its target.
    `lines` holds `(file, line)` for the entity, or for each local end of a link.
    """

    kind: str
    type: str
    parts: tuple[Shown, ...]
    lines: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class HeldItem:
    """One queue row, its group, its per run counts and what the packet shows of it."""

    record: str
    section: str
    signature: tuple[str, ...]
    canonical_id: str | None
    model: str
    group: str
    counts: tuple[int, ...]
    run: int
    mark: HeldMark

    @property
    def key(self) -> str:
        """A stable identity for ordering before the shuffle."""
        return f"{self.record}|{self.section}|{self.signature}"


@dataclass(frozen=True)
class GroupDraw:
    """One random draw from one group, with the seed it used."""

    group: str
    seed: int
    asked: int
    pool: int
    items: tuple[HeldItem, ...]

    @property
    def shortfall(self) -> int:
        """How many fewer items there were than asked for."""
        return self.asked - len(self.items)


def _normalize(text: str) -> str:
    """The eval quotes shorten `[0014](../path)` links to `[0014]` and join wrapped lines."""
    return re.sub(r"\s+", " ", re.sub(r"\]\([^)]*\)", "]", text)).strip()


def passage(file: str, line: int, quote: str, lines: Sequence[str]) -> Passage:
    """The lines a quote covers, from its cited line to the first holding all its pieces.

    A quote may skip text with `[...]`; every piece must appear in the window.

    Raises:
        ValueError: the quote is not found from its cited line onward.
    """
    pieces = [_normalize(p) for p in quote.split("[...]") if _normalize(p)]
    for end in range(line, len(lines) + 1):
        window = _normalize(" ".join(lines[line - 1 : end]))
        if all(piece in window for piece in pieces):
            return Passage(file=file.removeprefix(_DOCS), start=line, end=end)
    raise ValueError(f"{file}:{line}: the quote is not found from its cited line")


def eval_passages(payload: Mapping[str, Any], corpus: Path) -> tuple[Passage, ...]:
    """Every passage cited by an expected chain step and its `also`, nothing else.

    `corroboration` is not a chain step and the `checked` list is free text, so
    neither is read.
    """
    found: list[Passage] = []
    for entry in payload["entries"]:
        for step in entry.get("trace", []):
            lines = (corpus / step["file"]).read_text().splitlines()
            for cited in (step, step.get("also")):
                if cited is not None:
                    found.append(passage(step["file"], cited["line"], cited["quote"], lines))
    return tuple(found)


def in_passage(lines: Sequence[tuple[str, int]], passages: Sequence[Passage]) -> bool:
    """Whether any `(file, line)` falls inside any passage."""
    return any(
        p.file == file and p.start <= line <= p.end for file, line in lines for p in passages
    )


def reason_names(row: Mapping[str, Any]) -> frozenset[str]:
    """The distinct reason names of one queue row."""
    return frozenset(r["name"] for r in row["reasons"])


def group_of(names: frozenset[str], counts: Sequence[int]) -> str | None:
    """The group a row with these reason names and per run counts belongs to, if any."""
    if len(names) != 1:
        return None
    (name,) = names
    if name == RUNS_DISAGREE:
        return {3: "a", 2: "b", 1: "c"}.get(sum(1 for n in counts if n))
    return {KNOWN_TRAP_FLAG: "d", ENDPOINT_NOT_ACCEPTED: "e"}.get(name)


def _source(entity: IdentifiedEntity, unit: Unit) -> tuple[str, tuple[tuple[str, int], ...]]:
    """An entity's source line as `entity_mark()` writes it, and its `(file, line)`."""
    shown = entity_mark(entity, unit, "").source
    if entity.location is None:
        return shown, ()
    return shown, ((unit.path, unit.start_line + entity.location.line - 1),)


@dataclass(frozen=True)
class Known:
    """Every entity the corpus identified, as cross unit ends are matched against it."""

    entities: Mapping[str, tuple[IdentifiedEntity, Unit]]
    labels: LabelIndex


def known_entities(results: Sequence[UnitResult]) -> Known:
    """Each unit's first run entities, the set `resolve_accepted()` calls known."""
    entities = {
        e.canonical_id: (e, r.unit)
        for r in results
        if r.identified
        for e in r.identified[0].entities
    }
    return Known(entities=entities, labels=build_label_index(e for e, _ in entities.values()))


def _target(endpoint: ReferenceEndpoint, known: Known) -> str | None:
    """The known entity a cross unit end names, matched as `_waiting_on()` matches it."""
    if endpoint.record is not None and endpoint.id is not None:
        qualified = f"{endpoint.record}/{endpoint.id}"
        return qualified if qualified in known.entities else None
    if endpoint.record is not None and endpoint.label is not None:
        matched: str | None = known.labels.get((endpoint.record, normalize_label(endpoint.label)))
        return matched
    return None


def _end(
    endpoint: LocalEndpoint | ReferenceEndpoint,
    run: Mapping[str, IdentifiedEntity],
    unit: Unit,
    known: Known,
) -> tuple[Shown, tuple[tuple[str, int], ...]]:
    """One link end as the packet shows it, and its local line when it has one."""
    if isinstance(endpoint, LocalEndpoint):
        entity = run[endpoint.id]
        source, lines = _source(entity, unit)
        return Shown(span=entity.entity.span, source=source), lines
    target = _target(endpoint, known)
    if target is None:
        return Shown(span=None, source=None, words=endpoint.mention), ()
    entity, home = known.entities[target]
    source, _ = _source(entity, home)
    return Shown(span=entity.entity.span, source=source, words=endpoint.mention), ()


def held_mark(signature: tuple[str, ...], result: UnitResult, known: Known) -> tuple[int, HeldMark]:
    """The earliest run holding a signature, and the item as that run words it.

    Raises:
        LookupError: no run of the unit holds the signature.
    """
    runs = [a.run for a in result.artifacts if a.output is not None]
    for run, output in zip(runs, result.identified, strict=True):
        if len(signature) == 2:
            for entity in output.entities:
                if entity_signature(entity) == signature:
                    source, lines = _source(entity, result.unit)
                    shown = Shown(span=entity.entity.span, source=source)
                    return run, HeldMark(ENTITY, str(entity.entity.type), (shown,), lines)
            continue
        identities = identities_of(output)
        by_id = {e.canonical_id: e for e in output.entities}
        for link in output.relationships:
            if relationship_signature(link, identities) == signature:
                start, from_lines = _end(link.source, by_id, result.unit, known)
                finish, to_lines = _end(link.target, by_id, result.unit, known)
                return run, HeldMark(LINK, str(link.type), (start, finish), from_lines + to_lines)
    raise LookupError(f"no run of {result.unit.record_id} holds {signature}")


def held_items(
    rows: Sequence[Mapping[str, Any]], results: Sequence[UnitResult], known: Known
) -> tuple[HeldItem, ...]:
    """Every queue row that falls in a group, joined to its runs."""
    by_unit = {(r.unit.record_id, r.unit.section): r for r in results}
    items: list[HeldItem] = []
    for row in rows:
        result = by_unit[(row["record"], row["section"])]
        signature = tuple(row["signature"])
        comparison = result.routed.comparison
        tallies: dict[tuple[str, ...], tuple[int, ...]] = dict(
            comparison.entity_counts + comparison.relationship_counts
        )
        counts = tallies[signature]
        group = group_of(reason_names(row), counts)
        if group is None:
            continue
        run, mark = held_mark(signature, result, known)
        items.append(
            HeldItem(
                record=row["record"],
                section=row["section"],
                signature=signature,
                canonical_id=row["canonical_id"],
                model=row["model"],
                group=group,
                counts=counts,
                run=run,
                mark=mark,
            )
        )
    return tuple(items)


def exclusion(
    item: HeldItem, passages: Sequence[Passage], drawn_before: frozenset[str]
) -> str | None:
    """Why an item is left out of its group's pool, or `None` when it stays."""
    if in_passage(item.mark.lines, passages):
        return IN_PASSAGE
    if item.group == "d" and item.canonical_id in drawn_before:
        return DRAWN_BY_0012
    return None


def draw(group: str, pool: Sequence[HeldItem], asked: int, seed: int) -> GroupDraw:
    """Up to `asked` items drawn at random from `pool`; all of them when it is smaller."""
    ordered = sorted(pool, key=lambda i: i.key)
    chosen = random.Random(seed).sample(ordered, min(asked, len(ordered)))
    return GroupDraw(group=group, seed=seed, asked=asked, pool=len(pool), items=tuple(chosen))


def build_packet(draws: Sequence[GroupDraw], shuffle_seed: int) -> tuple[tuple[str, HeldItem], ...]:
    """Every drawn item under an opaque id, all groups shuffled together.

    Ids are numbered after the shuffle, so neither an id nor a position says which
    group drew an item.
    """
    items = sorted((i for d in draws for i in d.items), key=lambda i: i.key)
    random.Random(shuffle_seed).shuffle(items)
    return tuple((f"H{n:02d}", item) for n, item in enumerate(items, start=1))


def _part_lines(prefix: str, part: Shown) -> list[str]:
    if part.words is None:
        return [f"  - {prefix}source: {part.source}", f"  - {prefix}span: {part.span}"]
    lines = [f"  - {prefix}words: {part.words}"]
    if part.span is None:
        return [*lines, f"  - {prefix}target: not resolved"]
    return [*lines, f"  - {prefix}target: {part.source}", f"  - {prefix}target span: {part.span}"]


def packet_markdown(items: Sequence[tuple[str, HeldItem]], heading: str, intro: str) -> str:
    """The packet the engineer rules: per item its opaque id, kind, type and what it names.

    Nothing else of an item is written: no group, reason, run count, model, canonical
    id or acceptance state.
    """
    lines = [f"# {heading}", "", intro, ""]
    for opaque_id, item in items:
        mark = item.mark
        lines.append(f"- [ ] agree / disagree / unsure · `{opaque_id}` · {mark.kind} · {mark.type}")
        if mark.kind == ENTITY:
            lines += _part_lines("", mark.parts[0])
        else:
            lines += _part_lines("from ", mark.parts[0]) + _part_lines("to ", mark.parts[1])
        lines += ["  - note: ", "  - should have been: ", ""]
    return "\n".join(lines)


def arm_key(
    items: Sequence[tuple[str, HeldItem]],
    draws: Sequence[GroupDraw],
    shuffle_seed: int,
    excluded: Mapping[str, Mapping[str, int]],
) -> dict[str, object]:
    """The arm file's content: every seed and draw, and each item's group and provenance."""
    return {
        "shuffle_seed": shuffle_seed,
        "excluded": {g: dict(excluded.get(g, {})) for g in GROUPS},
        "draws": [
            {
                "group": d.group,
                "seed": d.seed,
                "asked": d.asked,
                "pool": d.pool,
                "drawn": len(d.items),
                "shortfall": d.shortfall,
            }
            for d in draws
        ],
        "items": [
            {
                "opaque_id": opaque_id,
                "group": i.group,
                "record": i.record,
                "section": i.section,
                "signature": list(i.signature),
                "canonical_id": i.canonical_id,
                "counts": list(i.counts),
                "model": i.model,
                "wording_run": i.run,
            }
            for opaque_id, i in items
        ],
    }


def _seed() -> int:
    """A fresh seed, recorded in the arm file, not in code."""
    return secrets.randbits(48)


def _without_time(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in row.items() if k != "queued_at"} for row in rows]


def build() -> None:
    """Group the queue, print each pool, draw, write the packet, the arm file and its hash."""
    existing = [p.name for p in (PACKET, ARMS, HASH) if p.exists()]
    if existing:
        raise SystemExit(f"{', '.join(existing)} already exist; a sample is drawn once")

    rows = json.loads(QUEUE.read_text())
    results = committed_units(ROOT, SNAPSHOT)
    corpus = resolve_accepted(results, records_for_units(results, SNAPSHOT, COMMIT))
    rebuilt = review_rows(results, corpus.held, DEFAULT_MODEL, "")
    if _without_time(rebuilt) != _without_time(rows):
        raise SystemExit(f"{QUEUE.name} differs from the queue the run files rebuild to")

    passages = eval_passages(json.loads(EVAL.read_text()), SNAPSHOT.parent)
    drawn_before = frozenset(
        i["canonical_id"] for i in json.loads(EARLIER_ARMS.read_text())["items"]
    )
    items = held_items(rows, results, known_entities(results))

    pools: dict[str, list[HeldItem]] = {g: [] for g in GROUPS}
    excluded: dict[str, Counter[str]] = {g: Counter() for g in GROUPS}
    for item in items:
        why = exclusion(item, passages, drawn_before)
        if why is None:
            pools[item.group].append(item)
        else:
            excluded[item.group][why] += 1

    for g in GROUPS:
        left_out = ", ".join(f"{n} {why}" for why, n in sorted(excluded[g].items())) or "none"
        print(f"group {g}: {len(pools[g])} after exclusions (left out: {left_out})")

    draws = [draw(g, pools[g], PER_GROUP, _seed()) for g in GROUPS]
    shuffle_seed = _seed()
    packet = build_packet(draws, shuffle_seed)

    PACKET.parent.mkdir(exist_ok=True)
    PACKET.write_text(packet_markdown(packet, "Held item packet, experiment 0013", INTRO))
    arms = (json.dumps(arm_key(packet, draws, shuffle_seed, excluded), indent=2) + "\n").encode()
    ARMS.write_bytes(arms)
    HASH.write_text(f"{hashlib.sha256(arms).hexdigest()}  {ARMS.name}\n")

    print(f"packet: {PACKET.relative_to(ROOT)}, {len(packet)} items")
    for d in draws:
        line = f"group {d.group}: drew {len(d.items)} of {d.pool}"
        print(line + (f", shortfall {d.shortfall}" if d.shortfall else ""))


if __name__ == "__main__":
    build()
