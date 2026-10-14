"""The units a measured step of spec 0007 is scored on, and the blind sample drawn from them.

Pure apart from `read_step_units()`, which reads one file. The list is written by
hand and committed before any paid call (AC-22, AC-22b), and the step is scored from
no other list. Code refuses a list naming a unit the step must not use (AC-23, AC-24).
The sample is drawn per unit and per arm with a given seed (AC-25 to AC-25d), then
mixed into one packet under opaque ids that shows nothing of an item's arm (AC-26,
AC-26d); the arm key that names each item's arm is a separate value (AC-26b). Once
ruled, the packet is parsed, the flip of AC-26e applied, and each unit scored against
stage one's gate (AC-19 to AC-19c).
"""

import json
import random
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tracepath.extract.ids import IdentifiedEntity
from tracepath.extract.units import Unit
from tracepath.pipeline import CorpusResolution, UnitResult

#: Records no chosen unit may come from, each with why (spec 0007 AC-23). The held out
#: records are listed by number only: the held out file itself is never opened (AC-30).
EXCLUDED_RECORDS: dict[str, str] = {
    **dict.fromkeys(
        ("0004", "0005", "0010", "0016", "0017", "0018", "0020"),
        "the held out questions may cite it",
    ),
    **dict.fromkeys(("0006", "0008", "0012", "0019", "scope"), "worked examples draw on it"),
    **dict.fromkeys(("0002", "0021"), "the code pass was checked on it"),
}

#: The experiments whose READMEs list the units they ruled (AC-24).
RULED_BY = (
    Path("experiments") / "0005-held-out-prompt-examples" / "README.md",
    Path("experiments") / "0006-accuracy-bar-recheck" / "README.md",
)

#: A unit in one of those READMEs' unit tables: a backticked record, then the backticked
#: `## Section` when the unit is a section. A feature row has no section.
_TABLE_UNIT = re.compile(r"^\|(?: [A-Z] \|)? `(\d{4}|feature-\d+)`(?: `## ([^`]+)`)?", re.MULTILINE)


class UnitsRefused(Exception):
    """The units list cannot be used for the step as it stands."""


@dataclass(frozen=True)
class StepUnit:
    """One chosen unit: its record and section, and the address `extract` takes."""

    record: str
    section: str

    @property
    def address(self) -> str:
        """`RECORD:SECTION`, as `tracepath extract` takes it."""
        return f"{self.record}:{self.section}"


@dataclass(frozen=True)
class StepUnits:
    """A step's chosen units and the model every one of their runs must name (AC-22)."""

    expected_model: str
    units: tuple[StepUnit, ...]


def ruled_units(readme: str) -> frozenset[tuple[str, str | None]]:
    """Every unit a README's unit tables list, `(record, section)`; `None` for a feature row."""
    return frozenset((match.group(1), match.group(2)) for match in _TABLE_UNIT.finditer(readme))


def check_units(units: Iterable[StepUnit], ruled: frozenset[tuple[str, str | None]]) -> None:
    """Refuse a unit from an excluded record (AC-23) or one already ruled (AC-24).

    Raises:
        UnitsRefused: naming every unit refused and why.
    """
    refused: list[str] = []
    for unit in units:
        why = EXCLUDED_RECORDS.get(unit.record)
        if why is not None:
            refused.append(f"{unit.address}: record {unit.record} is excluded, {why}")
        elif (unit.record, unit.section) in ruled or (unit.record, None) in ruled:
            refused.append(f"{unit.address}: experiments 0005 or 0006 already ruled it")
    if refused:
        raise UnitsRefused("; ".join(refused))


def read_step_units(path: Path, root: Path) -> StepUnits:
    """Read a step's `units.json` and check it against AC-23 and AC-24.

    Raises:
        UnitsRefused: the file is unreadable or not in the expected shape, or names a
            unit `check_units()` refuses.
    """
    try:
        payload = json.loads(path.read_text())
        units = tuple(StepUnit(record=u["record"], section=u["section"]) for u in payload["units"])
        expected = payload["expected_model"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise UnitsRefused(f"{path} cannot be read as a units list ({exc!r})") from exc
    if not isinstance(expected, str) or not units:
        raise UnitsRefused(f"{path} names no expected model or no units")
    ruled: frozenset[tuple[str, str | None]] = frozenset()
    for readme in RULED_BY:
        ruled |= ruled_units((root / readme).read_text())
    check_units(units, ruled)
    return StepUnits(expected_model=expected, units=units)


#: The two arms of a step (AC-20): the run files read without the code pass, and the
#: entities the pass releases when they are read with it.
CONTROL = "control"
RELEASED = "released"


@dataclass(frozen=True)
class EntityMark:
    """One entity as the engineer rules it, and the identity AC-27 dedupes on."""

    unit: str
    canonical_id: str
    span: str
    type: str
    source: str


@dataclass(frozen=True)
class Draw:
    """One random draw of marks from one arm of one unit, with the seed it used (AC-25c)."""

    unit: str
    arm: str
    seed: int
    asked: int
    pool: int
    marks: tuple[EntityMark, ...]

    @property
    def shortfall(self) -> int:
        """How many fewer marks there were than asked for (AC-25d)."""
        return self.asked - len(self.marks)


@dataclass(frozen=True)
class PacketItem:
    """One item to rule: its opaque id, its mark, and the arms that drew it (AC-27)."""

    opaque_id: str
    mark: EntityMark
    arms: tuple[str, ...]


def entity_mark(entity: IdentifiedEntity, unit: Unit, address: str) -> EntityMark:
    """The mark of one entity, its source line counted from the top of its file."""
    where = (
        f"{unit.path}:{unit.start_line + entity.location.line - 1}"
        if entity.location is not None
        else f"{unit.path} (line not located)"
    )
    return EntityMark(
        unit=address,
        canonical_id=entity.canonical_id,
        span=entity.entity.span,
        type=entity.entity.type.value,
        source=where,
    )


def control_marks(without_pass: UnitResult, address: str) -> tuple[EntityMark, ...]:
    """Every entity the control arm accepts in one unit, in canonical id order (AC-25)."""
    return tuple(
        sorted(
            (
                entity_mark(e, without_pass.unit, address)
                for e in without_pass.routed.accepted_entities
            ),
            key=lambda m: m.canonical_id,
        )
    )


def released_marks(with_pass: UnitResult, address: str) -> tuple[EntityMark, ...]:
    """Every entity the code pass releases in one unit, in canonical id order (AC-25b)."""
    return tuple(
        sorted(
            (
                entity_mark(e, with_pass.unit, address)
                for e in with_pass.routed.accepted_entities
                if e.canonical_id in with_pass.released
            ),
            key=lambda m: m.canonical_id,
        )
    )


def draw(unit: str, arm: str, pool: Sequence[EntityMark], asked: int, seed: int) -> Draw:
    """Up to `asked` marks drawn at random from `pool`; all of them when it is smaller."""
    rng = random.Random(seed)
    chosen = rng.sample(list(pool), min(asked, len(pool)))
    return Draw(unit=unit, arm=arm, seed=seed, asked=asked, pool=len(pool), marks=tuple(chosen))


def build_packet(
    draws: Sequence[Draw], units: Sequence[str], shuffle_seed: int
) -> tuple[PacketItem, ...]:
    """Every drawn mark under an opaque id, units in the given order, shuffled within each.

    A mark two arms drew, the same canonical id with the same span, is one item that
    names both arms (AC-27). Opaque ids are numbered after the shuffle, so neither an
    id nor a position says which arm drew an item.
    """
    rng = random.Random(shuffle_seed)
    items: list[PacketItem] = []
    for unit in units:
        arms: dict[tuple[str, str], list[str]] = {}
        marks: dict[tuple[str, str], EntityMark] = {}
        for d in draws:
            if d.unit != unit:
                continue
            for mark in d.marks:
                key = (mark.canonical_id, mark.span)
                marks.setdefault(key, mark)
                if d.arm not in arms.setdefault(key, []):
                    arms[key].append(d.arm)
        keys = sorted(marks)
        rng.shuffle(keys)
        for key in keys:
            items.append(
                PacketItem(
                    opaque_id=f"P{len(items) + 1:02d}",
                    mark=marks[key],
                    arms=tuple(sorted(arms[key])),
                )
            )
    return tuple(items)


def packet_markdown(items: Sequence[PacketItem], heading: str, intro: str) -> str:
    """The packet the engineer rules: per item its opaque id, span, type and source line.

    Nothing else of an item is written: no flag, no reason, no canonical id and no arm
    (AC-26d).
    """
    lines = [f"# {heading}", "", intro, ""]
    unit = None
    for item in items:
        if item.mark.unit != unit:
            unit = item.mark.unit
            lines += [f"## {unit}", ""]
        lines += [
            f"- [ ] agree / disagree / unsure · `{item.opaque_id}` · {item.mark.type}",
            f"  - source: {item.mark.source}",
            f"  - span: {item.mark.span}",
            "  - reason: ",
            "",
        ]
    return "\n".join(lines)


def arm_key(
    items: Sequence[PacketItem], draws: Sequence[Draw], shuffle_seed: int
) -> dict[str, object]:
    """The arm file's content: every draw with its seed, and each item's arms (AC-26b)."""
    return {
        "shuffle_seed": shuffle_seed,
        "draws": [
            {
                "unit": d.unit,
                "arm": d.arm,
                "seed": d.seed,
                "asked": d.asked,
                "pool": d.pool,
                "drawn": len(d.marks),
                "shortfall": d.shortfall,
            }
            for d in draws
        ],
        "items": [
            {
                "opaque_id": i.opaque_id,
                "unit": i.mark.unit,
                "canonical_id": i.mark.canonical_id,
                "span": i.mark.span,
                "arms": list(i.arms),
            }
            for i in items
        ],
    }


#: Stage one's gate (AC-19, AC-19c): per unit, 5 released marks drawn, 4 ruled agree.
STAGE_ONE_RELEASED = 5
STAGE_ONE_AGREE = 4

AGREE = "agree"
DISAGREE = "disagree"
UNSURE = "unsure"
#: The tag the engineer gives a bundled criterion ruled agree by the convention (AC-26e).
BUNDLED_TAG = "gap:bundled-ac"

PASS = "pass"
FAIL = "fail"
INCONCLUSIVE = "inconclusive"

_RULED_HEAD = re.compile(r"^- \[x\] (agree|disagree|unsure) · `(P\d+)` · ")
_ANY_HEAD = re.compile(r"^- \[[ x]\] .*`(P\d+)`")
_REASON = "  - reason:"


class RulingsRefused(Exception):
    """A ruled packet cannot be read as it stands."""


@dataclass(frozen=True)
class Ruling:
    """One ruled item: its mark and the engineer's reason, which carries any tag."""

    opaque_id: str
    mark: str
    reason: str


def parse_rulings(text: str) -> dict[str, Ruling]:
    """Every ruled item of a packet, keyed by opaque id. An unruled item is absent.

    A ruled item's line reads `- [x] <mark> · `Pnn` · <type>`.

    Raises:
        RulingsRefused: an item line is ticked but its mark is not one word of the
            three, or an id appears twice, so a ruling would be misread.
    """
    rulings: dict[str, Ruling] = {}
    current: str | None = None
    for line in text.splitlines():
        head = _ANY_HEAD.match(line)
        if head is not None:
            current = None
            ruled = _RULED_HEAD.match(line)
            if line.startswith("- [x]") and ruled is None:
                raise RulingsRefused(f"cannot read the mark of {head.group(1)}: {line!r}")
            if ruled is not None:
                current = ruled.group(2)
                if current in rulings:
                    raise RulingsRefused(f"{current} is ruled twice")
                rulings[current] = Ruling(current, ruled.group(1), "")
        elif current is not None and line.startswith(_REASON):
            reason = line.removeprefix(_REASON).strip()
            rulings[current] = Ruling(current, rulings[current].mark, reason)
    return rulings


def flip_bundled(
    rulings: Mapping[str, Ruling], flagged: frozenset[str]
) -> tuple[dict[str, Ruling], tuple[str, ...]]:
    """AC-26e: an item tagged bundled and ruled agree whose entity is unflagged disagrees.

    `flagged` names the items whose entity carries `multi_condition_split`. Returns the
    rulings with the flip applied and the ids it flipped.
    """
    flipped = tuple(
        sorted(
            i
            for i, r in rulings.items()
            if r.mark == AGREE and BUNDLED_TAG in r.reason and i not in flagged
        )
    )
    after = {i: Ruling(i, DISAGREE, r.reason) if i in flipped else r for i, r in rulings.items()}
    return after, flipped


@dataclass(frozen=True)
class ArmScore:
    """One arm's drawn marks in one unit and how they were ruled (AC-27b).

    `knowledge` counts the disagreements whose reason says they come from knowledge
    not in the text, reported apart (AC-18d); they are also counted in `disagree`.
    """

    drawn: int
    agree: int
    disagree: int
    unsure: int
    unruled: int
    knowledge: int


def arm_score(ids: Sequence[str], rulings: Mapping[str, Ruling]) -> ArmScore:
    """Score the items `ids` names from the rulings; a missing ruling is unruled (AC-18e)."""
    marks = Counter(rulings[i].mark if i in rulings else "" for i in ids)
    knowledge = sum(
        1
        for i in ids
        if i in rulings and rulings[i].mark == DISAGREE and "knowledge" in rulings[i].reason.lower()
    )
    return ArmScore(
        drawn=len(ids),
        agree=marks[AGREE],
        disagree=marks[DISAGREE],
        unsure=marks[UNSURE],
        unruled=marks[""],
        knowledge=knowledge,
    )


def unit_gate(released: ArmScore) -> str:
    """Stage one's gate on one unit (AC-19, AC-19c).

    Fewer than 5 released marks drawn is inconclusive. Otherwise the unit passes when
    at least 4 are ruled agree: `unsure`, disagree and unruled all count against.
    """
    if released.drawn < STAGE_ONE_RELEASED:
        return INCONCLUSIVE
    return PASS if released.agree >= STAGE_ONE_AGREE else FAIL


def stage_one_verdict(gates: Iterable[str], regressions: Sequence[str]) -> str:
    """Stage one over every unit, from each unit's gate and the regression check.

    Any unit failing, or anything lost, fails it (AC-19, AC-19b); otherwise it passes
    only when no unit is inconclusive (AC-19c).
    """
    found = set(gates)
    if FAIL in found or regressions:
        return FAIL
    return INCONCLUSIVE if INCONCLUSIVE in found else PASS


def regressions(
    without: Sequence[UnitResult],
    with_pass: Sequence[UnitResult],
    corpus_without: CorpusResolution,
    corpus_with: CorpusResolution,
    units: Iterable[tuple[str, str]],
) -> tuple[str, ...]:
    """AC-19b over the chosen units: what is accepted without the pass and not with it.

    Each entry names one lost entity or link; empty when nothing is lost.
    """
    chosen = set(units)
    found: list[str] = []
    after = {(r.unit.record_id, r.unit.section): r for r in with_pass}
    places: set[tuple[str, str]] = set()
    for result in without:
        key = (result.unit.record_id, result.unit.section)
        if key not in chosen:
            continue
        places.add((result.unit.path, result.unit.section))
        kept = {e.canonical_id for e in after[key].routed.accepted_entities}
        found += [
            f"entity {e.canonical_id} lost"
            for e in result.routed.accepted_entities
            if e.canonical_id not in kept
        ]
    lost = Counter(
        link for link in corpus_without.resolution.links if (link.file, link.section) in places
    ) - Counter(link for link in corpus_with.resolution.links)
    found += [
        f"link {link.source_record} {link.type.value} at {link.file}:{link.line} lost"
        for link in lost.elements()
    ]
    return tuple(found)


def held_items(result: UnitResult, corpus: CorpusResolution) -> int:
    """How many items one unit holds back, the rows it puts in the review queue (AC-28b).

    Its routed review items, then the links held because an endpoint in another unit
    was not accepted.
    """
    key = (result.unit.record_id, result.unit.section)
    return len(result.routed.review) + sum(
        1 for link in corpus.held if (link.record, link.section) == key
    )
