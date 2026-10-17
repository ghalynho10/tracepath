"""The accept to review ratio per unit and per unit kind (spec 0008 AC-7).

Pure. Counted from routing rebuilt from the run files, never from the committed
`artifacts/review-queue.json`, which can be stale. Held rows are the queue's rows: an
entity row for each held entity, a link row for each link routing held inside its unit,
and a link row for each link held for an endpoint in another unit, counted in the unit
whose section it was written in, the same place `review_rows()` puts it.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from tracepath.extract.units import Unit, UnitKind
from tracepath.pipeline import CorpusResolution, UnitResult

#: What a feature row of the scope document is grouped under.
SCOPE_ROW = "scope row"

#: What a grouping with no accepted entity reports instead of a ratio.
NO_ACCEPTED = "no accepted entities"


@dataclass(frozen=True)
class HoldCount:
    """Accepted entities and held rows, entity and link, for one grouping."""

    accepted_entities: int
    held_entities: int
    held_links: int

    @property
    def held_rows(self) -> int:
        """Every held row, entity and link alike."""
        return self.held_entities + self.held_links

    def __add__(self, other: "HoldCount") -> "HoldCount":
        """Two groupings counted together."""
        return HoldCount(
            self.accepted_entities + other.accepted_entities,
            self.held_entities + other.held_entities,
            self.held_links + other.held_links,
        )


@dataclass(frozen=True)
class UnitHold:
    """One unit's counts, with the unit kind it is grouped under."""

    record: str
    section: str
    kind: str
    count: HoldCount


def unit_kind(unit: Unit) -> str:
    """The section's shape: `Preamble`, a scope row, or the `##` heading it sits under."""
    if unit.kind is UnitKind.PREAMBLE:
        return "Preamble"
    if unit.kind is UnitKind.FEATURE_ROW:
        return SCOPE_ROW
    return unit.section


def unit_holds(results: Sequence[UnitResult], corpus: CorpusResolution) -> tuple[UnitHold, ...]:
    """Each unit's accepted entities and held rows, sorted by record and section."""
    holds: list[UnitHold] = []
    for result in sorted(results, key=lambda r: (r.unit.record_id, r.section_slug)):
        place = (result.unit.record_id, result.unit.section)
        across = sum(1 for link in corpus.held if (link.record, link.section) == place)
        review = result.routed.review
        holds.append(
            UnitHold(
                record=result.unit.record_id,
                section=result.unit.section,
                kind=unit_kind(result.unit),
                count=HoldCount(
                    accepted_entities=len(result.routed.accepted_entities),
                    held_entities=sum(1 for item in review if len(item.signature) == 2),
                    held_links=sum(1 for item in review if len(item.signature) == 3) + across,
                ),
            )
        )
    return tuple(holds)


def kind_holds(holds: Sequence[UnitHold]) -> tuple[tuple[str, HoldCount], ...]:
    """The units' counts summed per unit kind, sorted by kind."""
    by_kind: dict[str, HoldCount] = {}
    for hold in holds:
        by_kind[hold.kind] = by_kind.get(hold.kind, HoldCount(0, 0, 0)) + hold.count
    return tuple(sorted(by_kind.items()))


def ratio(count: HoldCount) -> str:
    """Accepted entities to held rows, as `1 : N` held rows per accepted entity."""
    if count.accepted_entities == 0:
        return NO_ACCEPTED
    return f"1 : {count.held_rows / count.accepted_entities:.2f}"


def _row(name: str, count: HoldCount) -> str:
    return (
        f"| {name} | {count.accepted_entities} | {count.held_entities} | "
        f"{count.held_links} | {count.held_rows} | {ratio(count)} |"
    )


HEADER = (
    "| {} | accepted entities | held entity rows | held link rows | held rows | "
    "accepted : held |\n|---|---|---|---|---|---|"
)


def ratio_lines(holds: Sequence[UnitHold]) -> tuple[str, ...]:
    """The two tables, per unit kind then per unit, with a total row under each."""
    total = sum((hold.count for hold in holds), HoldCount(0, 0, 0))
    lines = ["Per unit kind:", "", HEADER.format("unit kind")]
    lines += [_row(kind, count) for kind, count in kind_holds(holds)]
    lines += [_row("**total**", total), "", "Per unit:", "", HEADER.format("unit (kind)")]
    lines += [_row(f"{h.record} {h.section} ({h.kind})", h.count) for h in holds]
    lines.append(_row("**total**", total))
    return tuple(lines)
