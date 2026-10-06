"""The report step: scoring a walked chain against one eval question (spec 0004 AC-34 to AC-41).

This is the only code that reads `eval/` (key invariant 1). It runs after the walk has
finished and changes nothing the walk did. Its rules are the locked ones of spec 0004's
held out discipline: one start rule, one matching rule, one fixed order of reasons for
an item not reached. None of them names a question.
"""

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from tracepath.extract.compare import ReviewItem
from tracepath.extract.ids import IdentifiedEntity, section_slugs
from tracepath.extract.schema import normalize_label
from tracepath.extract.units import Unit, split_units
from tracepath.pipeline import CorpusResolution, UnitResult
from tracepath.resolve.endpoints import ResolvedLink, Target
from tracepath.traverse.graph_slice import NodeKind
from tracepath.traverse.walk import Chain, Step

#: The eval set, relative to the repository root.
EVAL_FILE = Path("eval") / "linked-records-research.json"

#: The start rule and the AC token rule, one regex (AC-34, AC-35). Trailing text such
#: as " (struck)" is ignored.
SPEC_AC = re.compile(r"^spec (\d{4}) (AC-\d+[a-z]?)\b")

#: The settled runs a unit needs to count as extracted (spec 0001's run policy).
FULL_RUNS = 3

#: The eval file cites the corpus from JobHunt's repository root; the snapshot holds
#: its `docs/` directory, so entities cite the same files without this prefix.
DOCS_PREFIX = "docs/"


class EvalEntryUnusable(Exception):
    """A question cannot be scored as it stands: missing, or no start by the rule."""


class Reason(StrEnum):
    """Why an expected item was not reached, the first that applies in this order (AC-38)."""

    SECTION_NOT_EXTRACTED = "section_not_extracted"
    HELD_FOR_REVIEW = "held_for_review"
    UNRESOLVED_ENDPOINT = "unresolved_endpoint"
    RECORD_NOT_EXPANDED = "record_not_expanded"
    LINK_HELD = "link_held"
    NO_LINK = "no_link"


@dataclass(frozen=True)
class ExpectedItem:
    """One `(file, line)` the question's answer cites, and the AC token it carries."""

    label: str
    file: str
    line: int
    token: str | None


@dataclass(frozen=True)
class Question:
    """One eval question, reduced to what scoring needs."""

    number: int
    text: str
    start: str
    start_label: str
    items: tuple[ExpectedItem, ...]


@dataclass(frozen=True)
class Finding:
    """One expected item, reached or not, and the one reason when not."""

    item: ExpectedItem
    record: str
    reached_by: Step | None
    reason: Reason | None


@dataclass(frozen=True)
class OutsideLink:
    """An accepted link written outside the expected sections that touches their records."""

    type: str
    source: str
    target: str
    file: str
    section: str


@dataclass(frozen=True)
class Report:
    """Everything the report prints for one question."""

    question: Question
    findings: tuple[Finding, ...]
    unmatched_steps: int
    outside_links: tuple[OutsideLink, ...]
    item_records: tuple[str, ...]


def _strip_docs(file: str) -> str:
    return file.removeprefix(DOCS_PREFIX)


def _token(record: str) -> str | None:
    match = SPEC_AC.match(record)
    return match.group(2) if match else None


def _also_entries(entry: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    also = entry.get("also")
    if also is None:
        return []
    return [also] if isinstance(also, Mapping) else list(also)


def question_from(entries: Sequence[Mapping[str, Any]], number: int) -> Question:
    """One question, its start item and its expected items, by the locked rules.

    Raises:
        EvalEntryUnusable: no such question, no `trace` list, or a first entry whose
            `record` does not match `spec NNNN AC-N` (AC-34). Nothing is guessed.
    """
    if not 1 <= number <= len(entries):
        raise EvalEntryUnusable(
            f"question {number} is not in the eval set, which holds questions 1 to {len(entries)}"
        )
    entry = entries[number - 1]
    trace = entry.get("trace")
    if not trace:
        raise EvalEntryUnusable(f"question {number} has no trace list, so it has no start item")
    first = str(trace[0].get("record", ""))
    match = SPEC_AC.match(first)
    if match is None:
        raise EvalEntryUnusable(
            f"question {number}: its first trace entry, {first!r}, does not match "
            "`spec NNNN AC-N`, so no start item is guessed"
        )
    items: list[ExpectedItem] = []
    for step in trace:
        label = str(step["record"])
        file = _strip_docs(str(step["file"]))
        items.append(ExpectedItem(label, file, int(step["line"]), _token(label)))
        # An `also` line has no AC token of its own: the parent's token belongs to the
        # parent's line only (AC-35).
        items.extend(
            ExpectedItem(f"{label} (also)", file, int(also["line"]), None)
            for also in _also_entries(step)
        )
    return Question(
        number=number,
        text=str(entry.get("question", "")),
        start=f"{match.group(1)}/{match.group(2)}",
        start_label=first,
        items=tuple(items),
    )


def read_question(path: Path, number: int) -> Question:
    """Read one question from the eval file.

    Raises:
        EvalEntryUnusable: the file is missing or unreadable, or the question is.
    """
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalEntryUnusable(f"the eval file {path} cannot be read ({exc})") from exc
    return question_from(payload["entries"], number)


@dataclass(frozen=True)
class Holding:
    """The unit a cited line sits in, with the section slug its artifacts carry."""

    unit: Unit
    section_slug: str


def holding_units(snapshot: Path, files: Iterable[str]) -> dict[str, tuple[Holding, ...]]:
    """Every unit of each cited file, split from the snapshot, with its section slug."""
    split: dict[str, tuple[Holding, ...]] = {}
    for file in dict.fromkeys(files):
        units = split_units(file, (snapshot / file).read_text())
        holdings: list[Holding] = []
        for record in dict.fromkeys(unit.record_id for unit in units):
            own = [unit for unit in units if unit.record_id == record]
            slugs = section_slugs(tuple(unit.section for unit in own))
            holdings.extend(Holding(u, s) for u, s in zip(own, slugs, strict=True))
        split[file] = tuple(sorted(holdings, key=lambda h: h.unit.start_line))
    return split


def _holding(split: Mapping[str, tuple[Holding, ...]], item: ExpectedItem) -> Holding:
    """The unit a line sits in: the last one starting at or before it."""
    return [h for h in split[item.file] if h.unit.start_line <= item.line][-1]


def _file_line(entity: IdentifiedEntity, unit: Unit) -> int | None:
    return unit.start_line + entity.location.line - 1 if entity.location else None


def _record_of(canonical_id: str) -> str:
    """A canonical id read up to its first `/` or `#`: the Record it hangs from."""
    return canonical_id.split("/", 1)[0].split("#", 1)[0]


def _names_entity(endpoint: str, entity: IdentifiedEntity, same_unit: bool) -> bool:
    """Whether one endpoint of a held link's signature names `entity`.

    A signature keeps a verbatim id as it is, a derived one by its section line (only
    meaningful inside its own unit), and a reference as `ref:record/id|label:...`.
    """
    if endpoint == entity.canonical_id:
        return True
    if same_unit and entity.location is not None and endpoint == f"line:{entity.location.line}":
        return True
    if not endpoint.startswith("ref:"):
        return False
    reference, _, label = endpoint.removeprefix("ref:").partition("|label:")
    record, _, identifier = reference.partition("/")
    if identifier and f"{record}/{identifier}" == entity.canonical_id:
        return True
    return bool(
        label
        and record == _record_of(entity.canonical_id)
        and entity.entity.label is not None
        and normalize_label(entity.entity.label) == label
    )


@dataclass(frozen=True)
class HeldRelationship:
    """A link held for review, with the unit it was written in."""

    record: str
    section: str
    item: ReviewItem


def held_relationships(
    results: Sequence[UnitResult], corpus: CorpusResolution
) -> tuple[HeldRelationship, ...]:
    """Every held link: routed for review inside a unit, or held for another unit's entity."""
    inside = [
        HeldRelationship(r.unit.record_id, r.unit.section, item)
        for r in results
        for item in r.routed.review
        if item.canonical_id is None and len(item.signature) == 3
    ]
    across = [HeldRelationship(h.record, h.section, h.item) for h in corpus.held]
    return (*inside, *across)


def _reached(steps: Sequence[Step], item: ExpectedItem) -> Step | None:
    """The visited entity at the item's file and file line, if any (AC-36)."""
    return next(
        (
            s
            for s in steps
            if s.node.kind is NodeKind.ENTITY
            and s.node.file == item.file
            and s.node.file_line == item.line
        ),
        None,
    )


def _reason(
    item: ExpectedItem,
    holding: Holding,
    steps: Sequence[Step],
    result: UnitResult | None,
    settled_runs: int,
    held: Sequence[HeldRelationship],
) -> Reason:
    """The one reason an item was not reached, by AC-38's fixed priority."""
    if settled_runs < FULL_RUNS or result is None:
        return Reason.SECTION_NOT_EXTRACTED

    unit = holding.unit
    at_line = [
        entity
        for output in result.identified
        for entity in output.entities
        if _file_line(entity, unit) == item.line
    ]
    accepted = [e for e in result.routed.accepted_entities if _file_line(e, unit) == item.line]
    if at_line and not accepted:
        return Reason.HELD_FOR_REVIEW

    if item.token is not None:
        mention = re.compile(rf"(?<![\w-]){re.escape(item.token)}(?!\w)")
        for step in steps:
            node = step.node
            if (
                node.kind is NodeKind.UNRESOLVED
                and node.record == unit.record_id
                and mention.search(node.mention or "")
            ):
                return Reason.UNRESOLVED_ENDPOINT

    if any(s.node.kind is NodeKind.RECORD and s.node.canonical_id == unit.record_id for s in steps):
        return Reason.RECORD_NOT_EXPANDED

    candidates = {e.canonical_id: e for e in (*accepted, *at_line)}.values()
    for link in held:
        same_unit = (link.record, link.section) == (unit.record_id, unit.section)
        endpoints = link.item.signature[1:]
        if any(_names_entity(str(end), e, same_unit) for e in candidates for end in endpoints):
            return Reason.LINK_HELD
    return Reason.NO_LINK


def _touches(link: ResolvedLink, records: frozenset[str], unresolved: Mapping[str, str]) -> bool:
    """Whether either endpoint names one of `records` (AC-40)."""
    for endpoint in (link.source, link.target):
        if endpoint.target is Target.UNRESOLVED:
            if unresolved.get(endpoint.canonical_id) in records:
                return True
        elif _record_of(endpoint.canonical_id) in records:
            return True
    return False


def score(
    question: Question,
    chain: Chain | None,
    results: Sequence[UnitResult],
    corpus: CorpusResolution,
    settled_runs: Mapping[tuple[str, str], int],
    split: Mapping[str, tuple[Holding, ...]],
) -> Report:
    """Score one walked chain against one question.

    `chain` is `None` when the start item was not in the graph, and then every item is
    not reached, each with its reason (AC-52). Pure: every input is given.
    `settled_runs` is keyed by `(record, section_slug)`; `split` holds every unit of
    each cited file (`holding_units()`).
    """
    steps = chain.steps if chain is not None else ()
    by_unit = {(r.unit.record_id, r.section_slug): r for r in results}
    held = held_relationships(results, corpus)

    findings: list[Finding] = []
    for item in question.items:
        holding = _holding(split, item)
        key = (holding.unit.record_id, holding.section_slug)
        step = _reached(steps, item)
        findings.append(
            Finding(
                item=item,
                record=holding.unit.record_id,
                reached_by=step,
                reason=None
                if step is not None
                else _reason(
                    item, holding, steps, by_unit.get(key), settled_runs.get(key, 0), held
                ),
            )
        )

    unmatched = sum(
        1
        for s in steps
        if not any(
            s.node.kind is NodeKind.ENTITY and s.node.file == i.file and s.node.file_line == i.line
            for i in question.items
        )
    )

    item_records = tuple(dict.fromkeys(f.record for f in findings))
    expected_sections = {
        (_holding(split, i).unit.path, _holding(split, i).unit.section) for i in question.items
    }
    unresolved = {
        node.canonical_id: node.record
        for node in corpus.resolution.unresolved
        if node.record is not None
    }
    outside = tuple(
        OutsideLink(str(k.type), k.source.canonical_id, k.target.canonical_id, k.file, k.section)
        for k in corpus.resolution.links
        if (k.file, k.section) not in expected_sections
        and _touches(k, frozenset(item_records), unresolved)
    )
    return Report(
        question=question,
        findings=tuple(findings),
        unmatched_steps=unmatched,
        outside_links=outside,
        item_records=item_records,
    )


def report_lines(report: Report) -> tuple[str, ...]:
    """The report as `trace --eval` prints it, after the chain (AC-37 to AC-41)."""
    question = report.question
    start_record = _record_of(question.start)
    lines = [
        f"Question {question.number}: {question.text}",
        f'Start item: {question.start}, from the first trace entry "{question.start_label}".',
        "",
        "Expected items:",
    ]
    for finding in report.findings:
        item = finding.item
        where = f"{item.file}:{item.line}"
        if finding.reached_by is not None:
            step = finding.reached_by
            lines.append(
                f"  reached      {item.label} · {where} · hop {step.hop} · {step.node.canonical_id}"
            )
        else:
            lines.append(f"  not reached  {item.label} · {where} · {finding.reason}")

    records = " or ".join(report.item_records)
    lines += [
        "",
        f"Visited steps matching no expected item: {report.unmatched_steps} "
        "(information, not a verdict).",
        f"Accepted links written outside the expected sections that touch {records}: "
        f"{len(report.outside_links)}.",
    ]
    lines += [
        f"  {k.source} -[{k.type}]-> {k.target} · {k.file} · {k.section}"
        for k in report.outside_links
    ]
    across = [f for f in report.findings if f.reached_by is not None and f.record != start_record]
    if across:
        named = ", ".join(
            f"{f.item.label} (hop {f.reached_by.hop})" for f in across if f.reached_by
        )
        lines.append(
            f"Across records: yes. An expected item outside {start_record} was reached from "
            f"the start: {named}."
        )
    else:
        lines.append(
            f"Across records: no. No expected item outside {start_record} was reached from "
            "the start."
        )
    return tuple(lines)
