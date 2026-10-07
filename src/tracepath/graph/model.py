"""Turning pipeline values into the plain rows Cypher writes.

Neo4j stores no null: setting a property to null removes it, so an unlocated `line`
is an absent property, which reads back as `None`. That is the same value AC-4 asks
for, recorded as absence rather than as a stored null.
"""

from dataclasses import dataclass
from typing import Any

from tracepath.extract.ids import IdentifiedEntity
from tracepath.extract.records import Record
from tracepath.extract.units import Unit
from tracepath.resolve.endpoints import ResolvedLink, UnresolvedNode


@dataclass(frozen=True)
class Provenance:
    """Where an accepted item came from, carried onto every entity and every link.

    `commit` is the corpus commit the unit's own runs pinned, read off its artifacts.
    """

    model: str
    prompt_version: str
    extracted_at: str
    accepted_by: str
    commit: str


def _without_nulls(row: dict[str, Any]) -> dict[str, Any]:
    """Drop null valued keys, since Neo4j stores absence rather than null."""
    return {key: value for key, value in row.items() if value is not None}


def record_row(record: Record) -> dict[str, Any]:
    """One `:Record` node's properties."""
    return _without_nulls(
        {
            "canonical_id": record.canonical_id,
            "kind": str(record.kind),
            "title": record.title,
            "status": record.status,
            "path": record.path,
            "commit": record.commit,
            "aliases": list(record.aliases),
        }
    )


def entity_row(
    entity: IdentifiedEntity, unit: Unit, commit: str, provenance: Provenance
) -> dict[str, Any]:
    """One `:Entity` node's properties, citation and provenance included.

    `line` stays relative to its section (spec 0002 AC-4). `file_line` is the same line
    counted from the top of the source file, the one a reader opens the file at
    (spec 0004 AC-50), and is absent when `line` is.
    """
    line = entity.location.line if entity.location else None
    return _without_nulls(
        {
            "canonical_id": entity.canonical_id,
            "type": str(entity.entity.type),
            "text": entity.entity.span,
            "rationale": list(entity.entity.rejected_spans),
            "flags": [str(flag) for flag in entity.entity.known_trap_flags],
            "unclassified_note": entity.entity.unclassified_note,
            "id_source": str(entity.entity.id_source),
            "label": entity.entity.label,
            "struck": entity.struck,
            "followup_status": (
                str(entity.followup_status) if entity.followup_status is not None else None
            ),
            "file": unit.path,
            "section": unit.section,
            "line": line,
            "file_line": unit.start_line + line - 1 if line is not None else None,
            "commit": commit,
            "model": provenance.model,
            "prompt_version": provenance.prompt_version,
            "extracted_at": provenance.extracted_at,
            "accepted_by": provenance.accepted_by,
        }
    )


def held_entity_row(
    entity: IdentifiedEntity,
    unit: Unit,
    commit: str,
    provenance: Provenance,
    reasons: tuple[str, ...],
) -> dict[str, Any]:
    """A held entity's properties: `entity_row()` without `accepted_by`, marked held.

    No one accepted it, so it carries no `accepted_by` (spec 0005 AC-18). `held` is
    `true` and `held_reasons` lists why, each reason as `name` or `name:detail`.
    """
    row = entity_row(entity, unit, commit, provenance)
    del row["accepted_by"]
    return {**row, "held": True, "held_reasons": list(reasons)}


def unresolved_row(node: UnresolvedNode) -> dict[str, Any]:
    """One `:Unresolved` node's properties."""
    return _without_nulls(
        {
            "canonical_id": node.canonical_id,
            "mention": node.mention,
            "source_record": node.source_record,
            "record": node.record,
            "label": node.label,
            "file": node.file,
            "section": node.section,
            "line": node.line,
        }
    )


def link_row(link: ResolvedLink, provenance: Provenance) -> dict[str, Any]:
    """One relationship's endpoints and its own properties, provenance included.

    `provenance` is the unit the link was written in, so a chain step can say which
    prompt made it (spec 0004 AC-16). Records and `PART_OF` links are code's, not the
    model's, and never pass through here.
    """
    return {
        "from_id": link.source.canonical_id,
        "to_id": link.target.canonical_id,
        "properties": _without_nulls(
            {
                "phrase": link.phrase,
                "date": link.date,
                "source_record": link.source_record,
                "file": link.file,
                "section": link.section,
                "line": link.line,
                "prompt_version": provenance.prompt_version,
                "model": provenance.model,
                "commit": provenance.commit,
            }
        ),
    }


def held_unresolved_row(node: UnresolvedNode) -> dict[str, Any]:
    """An `:Unresolved` node only held links reach: `held`, and no reasons of its own."""
    return {**unresolved_row(node), "held": True}


def held_link_row(
    link: ResolvedLink, provenance: Provenance, reasons: tuple[str, ...]
) -> dict[str, Any]:
    """A held relationship: `link_row()` with `held` and `held_reasons` among its properties."""
    row = link_row(link, provenance)
    return {
        **row,
        "properties": {**row["properties"], "held": True, "held_reasons": list(reasons)},
    }
