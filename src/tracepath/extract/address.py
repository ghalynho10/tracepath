"""Unit addresses: `RECORD:SECTION`, such as `0002:Requirements` (spec 0004, Commands).

An address names one unit of the pinned snapshot. A section name that more than one
unit of a record carries is refused as ambiguous, naming the candidates, rather than
guessed.
"""

from dataclasses import dataclass
from pathlib import Path

from tracepath.extract.ids import section_slugs
from tracepath.extract.units import Unit, UnitKind, split_units


class UnitAddressError(Exception):
    """An address is malformed, names nothing in the snapshot, or names more than one unit."""


@dataclass(frozen=True)
class Target:
    """One unit to extract, with the section slug its artifacts and derived ids carry."""

    address: str
    unit: Unit
    section_slug: str


def _document(snapshot: Path, record: str) -> Path:
    """The snapshot file a record lives in."""
    if record == "scope" or record.startswith("feature-"):
        path = snapshot / "scope" / "scope.md"
        if not path.exists():
            raise UnitAddressError(f"the snapshot at {snapshot} holds no scope/scope.md")
        return path
    found = sorted(snapshot.glob(f"specs/{record}-*/index.md"))
    if not found:
        raise UnitAddressError(f"no spec {record} in the snapshot at {snapshot}")
    if len(found) > 1:
        raise UnitAddressError(f"more than one spec directory starts with {record}: {found}")
    return found[0]


def resolve_address(snapshot: Path, address: str) -> Target:
    """The one unit an address names.

    Raises:
        UnitAddressError: the address has no `:`, its record is not in the snapshot, no
            unit of the record has that section, or more than one does.
    """
    record, colon, section = address.partition(":")
    if not colon or not record or not section:
        raise UnitAddressError(f"{address!r} is not RECORD:SECTION, e.g. 0002:Requirements")
    path = _document(snapshot, record)
    units = split_units(path.relative_to(snapshot).as_posix(), path.read_text())
    own = [unit for unit in units if unit.record_id == record]
    slugs = section_slugs(tuple(unit.section for unit in own))
    found = [
        (unit, slug)
        for unit, slug in zip(own, slugs, strict=True)
        if unit.section == section and unit.kind is not UnitKind.INTRO
    ]
    if not found:
        names = ", ".join(dict.fromkeys(unit.section for unit in own))
        raise UnitAddressError(f"{record} has no section {section!r}. Its sections: {names}")
    if len(found) > 1:
        lines = ", ".join(f"line {unit.start_line}" for unit, _ in found)
        raise UnitAddressError(
            f"{address} is ambiguous: {len(found)} units of {record} are called {section!r} "
            f"({lines}), so none is guessed"
        )
    unit, slug = found[0]
    return Target(address=f"{record}:{section}", unit=unit, section_slug=slug)


def resolve_addresses(snapshot: Path, addresses: list[str]) -> tuple[Target, ...]:
    """Every address resolved, in the order given, which is the order they run in.

    Raises:
        UnitAddressError: any one address fails, or two name the same unit.
    """
    targets = tuple(resolve_address(snapshot, address) for address in addresses)
    seen: set[tuple[str, str]] = set()
    for target in targets:
        key = (target.unit.record_id, target.section_slug)
        if key in seen:
            raise UnitAddressError(f"{target.address} is named twice")
        seen.add(key)
    return targets
