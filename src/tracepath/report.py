"""The report step: scoring a walked chain against one eval question (spec 0004 AC-34 to AC-41).

This is the only code that reads `eval/` (key invariant 1). It runs after the walk has
finished and changes nothing the walk did. Its rules are the locked ones of spec 0004's
held out discipline: one start rule, one matching rule, one fixed order of reasons for
an item not reached. None of them names a question.

Under the held item view (spec 0005) it scores two walks: an item the clean walk
reaches is `reached`, and one only the held walk reaches is `held only`, never reached.

The eval runner (spec 0006) adds two start rules where spec 0004's would refuse, absence
questions, a result built from the findings, and the evidence each question rests on.
The facts that name a question live in `eval/runner.json`, never in this code.
"""

import hashlib
import json
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from tracepath.extract.compare import ReviewItem
from tracepath.extract.ids import IdentifiedEntity, section_slugs
from tracepath.extract.schema import normalize_label
from tracepath.extract.units import Unit, split_units
from tracepath.pipeline import CorpusResolution, UnitResult
from tracepath.resolve.endpoints import ResolvedLink, Target
from tracepath.traverse.graph_slice import GraphSlice, NodeKind
from tracepath.traverse.walk import Chain, Step

#: The eval set, relative to the repository root.
EVAL_FILE = Path("eval") / "linked-records-research.json"

#: The runner's sidecar, relative to the repository root (spec 0006).
SIDECAR_FILE = Path("eval") / "runner.json"

#: The start rule and the AC token rule, one regex (AC-34, AC-35). Trailing text such
#: as " (struck)" is ignored.
SPEC_AC = re.compile(r"^spec (\d{4}) (AC-\d+[a-z]?)\b")

#: The start rule for a question with no `trace` list (spec 0006 AC-14).
CHECKED_START = re.compile(r"^docs/specs/(\d{4})-[^/]+/index\.md line (\d+) \((AC-\d+[a-z]?)\)$")

#: The settled runs a unit needs to count as extracted (spec 0001's run policy).
FULL_RUNS = 3

#: The eval file cites the corpus from JobHunt's repository root; the snapshot holds
#: its `docs/` directory, so entities cite the same files without this prefix.
DOCS_PREFIX = "docs/"

#: The line a report made with `--with-held` opens with (spec 0005 AC-15).
HELD_LABEL = "Held item view (spec 0005): a second result. Experiment 0009 stays the first."

#: What `held_for_review` means under the held item view (spec 0005 AC-16).
HELD_MEANING = (
    "held_for_review keeps spec 0004's meaning: the item is held, whether or not this view "
    "wrote it."
)

#: The line a released held out file opens with (spec 0006 AC-29).
HELD_OUT_LABEL = (
    "Held out check (spec 0006): a check of the choices features 13 and 11 made, not a measurement."
)

#: Printed once when `examples/` changed after the evidence flags were written (AC-21).
UNCHECKED_LINE = "Evidence flags unchecked: examples/ has changed since they were written."

#: How each evidence level reads in an evidence line (AC-18).
EVIDENCE_WORDS = {
    "weaker": "weaker",
    "light": "light",
    "none": "no overlap with a worked example",
}


class EvalEntryUnusable(Exception):
    """A question cannot be scored as it stands: missing, or no start by the rule."""


class HeldOutRefused(Exception):
    """A held out file read without `--release-held-out`, or that flag on any other file."""


class SidecarInvalid(Exception):
    """`eval/runner.json` exists but is not valid JSON in the runner's shape."""


class Reason(StrEnum):
    """Why an expected item was not reached, the first that applies in this order (AC-38)."""

    SECTION_NOT_EXTRACTED = "section_not_extracted"
    HELD_FOR_REVIEW = "held_for_review"
    UNRESOLVED_ENDPOINT = "unresolved_endpoint"
    RECORD_NOT_EXPANDED = "record_not_expanded"
    LINK_HELD = "link_held"
    NO_LINK = "no_link"


class Verdict(StrEnum):
    """One question's result (spec 0006 AC-5)."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class ExpectedItem:
    """One `(file, line)` the question's answer cites, and the AC token it carries."""

    label: str
    file: str
    line: int
    token: str | None


@dataclass(frozen=True)
class Question:
    """One eval question, reduced to what scoring needs.

    `start` is the start id when a rule gives it from the text (spec 0004 AC-34, spec
    0006 AC-14). `start_at` is the file and line a start is read from in the graph
    instead (AC-12), and then `start` is `None`. An `absence` question's items are the
    ones its walk must not reach (AC-16).
    """

    number: int
    text: str
    start: str | None
    start_label: str
    items: tuple[ExpectedItem, ...]
    start_at: tuple[str, int] | None = None
    absence: bool = False


@dataclass(frozen=True)
class Start:
    """The start a question resolved to against one graph read (AC-12, AC-13).

    `file` and `file_line` are the start node's own, `None` when the graph does not
    hold it. `candidates` counts the entities on the start line, for AC-12's rule.
    """

    id: str | None
    file: str | None = None
    file_line: int | None = None
    candidates: int = 1


@dataclass(frozen=True)
class Finding:
    """One expected item, reached or not, and the one reason when not.

    `reached_by` is the clean walk's step. `held_by` is the held walk's step for an item
    only the held walk reached (spec 0005 AC-12b), with `held_parts` the held nodes and
    links on its path from the start; such an item has no reason and is not reached.
    `accepted_here` says an accepted entity sits at the item's file and line (spec
    0006 AC-17).
    """

    item: ExpectedItem
    record: str
    reached_by: Step | None
    reason: Reason | None
    held_by: Step | None = None
    held_parts: tuple[str, ...] = ()
    accepted_here: bool = False


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
    start: Start
    start_in_clean_slice: bool
    with_held: bool = False


@dataclass(frozen=True)
class Outcome:
    """A question's result, from its findings only (AC-6 to AC-6c, AC-17 to AC-17c).

    `reached` and `expected` are K and M, besides the start (AC-10b). `first_reached`
    is the absence item a walk reached, for a `FAIL` (AC-17b). `causes` holds each
    absence item with its cause, `None` where its absence holds, for an
    `INCONCLUSIVE` (AC-17c).
    """

    verdict: Verdict
    reached: int
    expected: int
    first_reached: Finding | None = None
    causes: tuple[tuple[Finding, str | None], ...] = ()


@dataclass(frozen=True)
class Evidence:
    """How much a question's expected chain overlaps the worked examples (AC-18)."""

    level: Literal["weaker", "light", "none"]
    reason: str


@dataclass(frozen=True)
class QuestionNotes:
    """What the sidecar says of one question: its evidence, and its absence items if any."""

    evidence: Evidence
    absence: tuple[ExpectedItem, ...] | None = None


@dataclass(frozen=True)
class Sidecar:
    """The sidecar's entry for one eval file."""

    examples_sha256: str
    questions: Mapping[int, QuestionNotes]


@dataclass(frozen=True)
class EvalSet:
    """An eval file's entries, and whether it is a held out file (AC-22)."""

    path: Path
    entries: tuple[Mapping[str, Any], ...]
    held_out: bool


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


def _checked_start(entry: Mapping[str, Any], number: int) -> tuple[str, str]:
    """The start id and its `where` text, from the first `checked` entry in AC form (AC-14)."""
    for check in entry.get("checked") or ():
        where = str(check.get("where", ""))
        match = CHECKED_START.match(where)
        if match is not None:
            return f"{match.group(1)}/{match.group(3)}", where
    raise EvalEntryUnusable(
        f"question {number}: no checked entry reads `docs/specs/NNNN-<slug>/index.md line N "
        "(AC-N)`, so no start item is guessed"
    )


def question_from(
    entries: Sequence[Mapping[str, Any]],
    number: int,
    *,
    absence: Sequence[ExpectedItem] | None = None,
    held_out: bool = False,
) -> Question:
    """One question, its start item and its expected items, by the locked rules.

    A first `trace` entry in `spec NNNN AC-N` form gives the start by spec 0004 AC-34.
    Any other first entry gives a file and line the start is read from in the graph
    (spec 0006 AC-12). A question the sidecar lists `absence` items for takes its start
    from its `checked` entries (AC-14) and its items from the sidecar (AC-16).

    Raises:
        EvalEntryUnusable: no such question, or no rule gives it a start or items
            (AC-15, AC-15b). Nothing is guessed.
    """
    if not 1 <= number <= len(entries):
        raise EvalEntryUnusable(
            f"question {number} is not in the eval set, which holds questions 1 to {len(entries)}"
        )
    entry = entries[number - 1]
    text = str(entry.get("question", ""))
    trace = entry.get("trace")
    if absence is not None:
        if held_out:
            raise EvalEntryUnusable(
                f"question {number}: the sidecar lists absence items for a held out file, "
                "which may hold no absence question"
            )
        if trace:
            raise EvalEntryUnusable(
                f"question {number} has a trace list and absence items in the sidecar, "
                "so it is neither kind"
            )
        if not absence:
            raise EvalEntryUnusable(
                f"question {number}: the sidecar lists no absence items, so it has nothing to score"
            )
        start, where = _checked_start(entry, number)
        return Question(number, text, start, where, tuple(absence), absence=True)
    if not trace:
        raise EvalEntryUnusable(
            f"question {number} has no trace list and no absence entry in the sidecar, "
            "so it has no start item"
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
    first = items[0]
    match = SPEC_AC.match(first.label)
    if match is not None:
        return Question(
            number, text, f"{match.group(1)}/{match.group(2)}", first.label, tuple(items)
        )
    return Question(
        number, text, None, first.label, tuple(items), start_at=(first.file, first.line)
    )


def read_eval_set(path: Path, *, release_held_out: bool = False) -> EvalSet:
    """Read an eval file, refusing a held out one unless it is released (AC-28).

    Every command that reads an eval file reads it here, so the refusal comes before
    any graph is read.

    Raises:
        EvalEntryUnusable: the file is missing, unreadable, or holds no entries list.
        HeldOutRefused: a held out file without `release_held_out`, or the flag on a
            file that is not held out.
    """
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvalEntryUnusable(f"the eval file {path} cannot be read ({exc})") from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("entries"), list):
        raise EvalEntryUnusable(f"the eval file {path} holds no `entries` list")
    held_out = payload.get("held_out") is True
    if held_out and not release_held_out:
        raise HeldOutRefused(
            f"{path} is held out (spec 0006): it runs only with --release-held-out, once "
            "features 13 and 11 have both committed their choices."
        )
    if release_held_out and not held_out:
        raise HeldOutRefused(
            f'--release-held-out: {path} is not a held out file (no top level "held_out": '
            "true), so there is nothing to release."
        )
    return EvalSet(path, tuple(payload["entries"]), held_out)


def read_question(path: Path, number: int) -> Question:
    """Read one question from an eval file that is not held out, with no sidecar.

    Raises:
        EvalEntryUnusable: the file is missing or unreadable, or the question is.
        HeldOutRefused: the file is held out.
    """
    return question_from(read_eval_set(path).entries, number)


class _AbsenceRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    label: str
    file: str
    line: int


class _QuestionRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence: Literal["weaker", "light", "none"]
    reason: str
    absence: tuple[_AbsenceRow, ...] | None = None


class _SidecarRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    examples_sha256: str
    questions: dict[int, _QuestionRow]


_SIDECAR = TypeAdapter(dict[str, _SidecarRow])


def read_sidecar(root: Path, eval_file: Path) -> Sidecar | None:
    """The sidecar's entry for one eval file, keyed by its basename.

    `None` when `eval/runner.json` is missing or has no entry for the file: every
    question then reads `not assessed` (AC-8c).

    Raises:
        SidecarInvalid: the file is unreadable, not JSON, or not in the runner's shape,
            an unknown evidence level included.
    """
    path = root / SIDECAR_FILE
    if not path.exists():
        return None
    try:
        parsed = _SIDECAR.validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        raise SidecarInvalid(f"{SIDECAR_FILE.as_posix()} cannot be used ({exc})") from exc
    row = parsed.get(eval_file.name)
    if row is None:
        return None
    return Sidecar(
        examples_sha256=row.examples_sha256,
        questions={
            number: QuestionNotes(
                evidence=Evidence(notes.evidence, notes.reason),
                absence=(
                    tuple(
                        ExpectedItem(a.label, _strip_docs(a.file), a.line, _token(a.label))
                        for a in notes.absence
                    )
                    if notes.absence is not None
                    else None
                ),
            )
            for number, notes in row.questions.items()
        },
    )


def examples_digest(root: Path) -> str | None:
    """The sha256 of `examples/` as AC-20 defines it, `None` outside a git work tree.

    Only files `git ls-files` lists count, each as its path relative to `examples/`, a
    NUL byte, its length, a NUL byte and its bytes, in sorted path order.
    """
    try:
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "examples/"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    digest = hashlib.sha256()
    for path in sorted(p for p in listed.decode().split("\0") if p):
        data = (root / path).read_bytes()
        digest.update(path.removeprefix("examples/").encode())
        digest.update(b"\0" + str(len(data)).encode() + b"\0")
        digest.update(data)
    return digest.hexdigest()


def _id_order(canonical_id: str) -> tuple[tuple[int, str], ...]:
    """A sort key that compares the numbers inside an id as numbers (`:9` before `:10`)."""
    parts = re.split(r"(\d+)", canonical_id)
    pieces = ((int(p), p) if i % 2 else (-1, p) for i, p in enumerate(parts))
    return (*pieces, (-1, canonical_id))


def resolve_start(question: Question, graph: GraphSlice) -> Start:
    """The id a question's walk starts from, read against one graph (AC-12 to AC-13).

    A start given by the text keeps its id, with its node's file and line when the
    graph holds it. A start read from a file and line is the lowest id among the
    accepted entities there; a held one is a candidate only when no accepted one is
    (AC-12d). `Start(None)` when no entity holds the line (AC-12c).
    """
    if question.start_at is None:
        node = next((n for n in graph.nodes if n.canonical_id == question.start), None)
        if node is None:
            return Start(question.start)
        return Start(question.start, node.file, node.file_line)
    file, line = question.start_at
    here = [
        n
        for n in graph.nodes
        if n.kind is NodeKind.ENTITY and n.file == file and n.file_line == line
    ]
    pool = [n for n in here if not n.held] or here
    if not pool:
        return Start(None, candidates=0)
    first = min(pool, key=lambda n: _id_order(n.canonical_id))
    return Start(first.canonical_id, first.file, first.file_line, len(pool))


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
    """The unit a line sits in: the last one starting at or before it.

    Raises:
        EvalEntryUnusable: the line sits before the first unit of its file (AC-8d).
    """
    before = [h for h in split[item.file] if h.unit.start_line <= item.line]
    if not before:
        raise EvalEntryUnusable(
            f"{item.label} cites {item.file} line {item.line}, before the first unit of its file"
        )
    return before[-1]


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


#: Each accepted entity by its id, with the `(record, section)` of the unit it is in.
EntityIndex = Mapping[str, tuple[IdentifiedEntity, tuple[str, str]]]


def _entity_index(results: Sequence[UnitResult]) -> EntityIndex:
    return {
        entity.canonical_id: (entity, (r.unit.record_id, r.unit.section))
        for r in results
        for entity in r.routed.accepted_entities
    }


def _names_visited(
    endpoint: str, link: HeldRelationship, steps: Sequence[Step], index: EntityIndex
) -> bool:
    """Whether a held link's endpoint names a node the walk visited (AC-17d)."""
    for step in steps:
        node = step.node
        if endpoint == node.canonical_id:
            return True
        if node.kind is NodeKind.RECORD and endpoint == f"ref:{node.canonical_id}/":
            return True
        known = index.get(node.canonical_id)
        if known is not None:
            entity, unit = known
            if _names_entity(endpoint, entity, unit == (link.record, link.section)):
                return True
    return False


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


def _accepted_here(
    item: ExpectedItem, holding: Holding, result: UnitResult | None, settled_runs: int
) -> bool:
    """Whether an accepted entity sits at the item's line, read as `_reason()` reads it."""
    if settled_runs < FULL_RUNS or result is None:
        return False
    return any(_file_line(e, holding.unit) == item.line for e in result.routed.accepted_entities)


def _reason(
    item: ExpectedItem,
    holding: Holding,
    steps: Sequence[Step],
    result: UnitResult | None,
    settled_runs: int,
    held: Sequence[HeldRelationship],
    *,
    absence_index: EntityIndex | None = None,
) -> Reason:
    """The one reason an item was not reached, by AC-38's fixed priority.

    For an absence item (`absence_index` given), a held link counts only when its other
    endpoint names a node the walk visited (spec 0006 AC-17d).
    """
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
        ends = tuple(str(end) for end in link.item.signature[1:])
        for entity in candidates:
            named = [i for i, end in enumerate(ends) if _names_entity(end, entity, same_unit)]
            if not named:
                continue
            if absence_index is None or any(
                _names_visited(ends[1 - i], link, steps, absence_index) for i in named
            ):
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


def held_parts(chain: Chain, step: Step) -> tuple[str, ...]:
    """The held nodes and links on the walk's path to `step`, from the start (AC-13).

    The path is the one the walk took, followed by `parent` back to the start. A node
    is named by its id, a link as `SOURCE -[TYPE]-> TARGET`, the link before the node
    it led to.
    """
    by_id = {s.node.canonical_id: s for s in chain.steps}
    path: list[Step] = [step]
    while path[-1].parent is not None:
        path.append(by_id[path[-1].parent])
    parts: list[str] = []
    for on_path in reversed(path):
        via = on_path.via
        if via is not None and via.held:
            parts.append(f"{via.source} -[{via.type}]-> {via.target}")
        if on_path.node.held:
            parts.append(on_path.node.canonical_id)
    return tuple(parts)


def score(
    question: Question,
    chain: Chain | None,
    results: Sequence[UnitResult],
    corpus: CorpusResolution,
    settled_runs: Mapping[tuple[str, str], int],
    split: Mapping[str, tuple[Holding, ...]],
    *,
    with_held: bool = False,
    held: Chain | None = None,
    start: Start | None = None,
) -> Report:
    """Score one walked chain against one question.

    `chain` is `None` when the start item was not in the graph, and then every item is
    not reached, each with its reason (AC-52). Pure: every input is given.
    `settled_runs` is keyed by `(record, section_slug)`; `split` holds every unit of
    each cited file (`holding_units()`). `start` is the start `resolve_start()` gave,
    by default the question's own id.

    With `with_held`, `chain` is the clean walk and `held` the held walk over the same
    graph (spec 0005 AC-12). Only the clean walk can reach an item; one only the held
    walk reaches is `held only`. Reasons for an item neither reaches keep spec 0004's
    meaning, so they are read off the clean walk. Visited steps are counted over the
    held walk, the chain `trace` prints.

    Raises:
        EvalEntryUnusable: an item's line sits before the first unit of its file.
    """
    steps = chain.steps if chain is not None else ()
    held_steps = held.steps if held is not None else ()
    by_unit = {(r.unit.record_id, r.section_slug): r for r in results}
    held_links = held_relationships(results, corpus)
    index = _entity_index(results) if question.absence else None

    findings: list[Finding] = []
    for item in question.items:
        holding = _holding(split, item)
        key = (holding.unit.record_id, holding.section_slug)
        result, settled = by_unit.get(key), settled_runs.get(key, 0)
        step = _reached(steps, item)
        held_step = _reached(held_steps, item) if step is None and with_held else None
        reason = (
            _reason(item, holding, steps, result, settled, held_links, absence_index=index)
            if step is None and held_step is None
            else None
        )
        findings.append(
            Finding(
                item=item,
                record=holding.unit.record_id,
                reached_by=step,
                reason=reason,
                held_by=held_step,
                held_parts=(held_parts(held, held_step) if held is not None and held_step else ()),
                accepted_here=_accepted_here(item, holding, result, settled),
            )
        )

    visited = held_steps if with_held else steps
    unmatched = sum(
        1
        for s in visited
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
        start=start if start is not None else Start(question.start),
        start_in_clean_slice=chain is not None,
        with_held=with_held,
    )


def _start_line(question: Question, start: Start) -> str:
    """The `Start item:` line, naming where the start came from (AC-10c)."""
    if question.absence:
        return f'Start item: {start.id}, from the first checked entry "{question.start_label}".'
    if question.start_at is None:
        return f'Start item: {start.id}, from the first trace entry "{question.start_label}".'
    file, line = question.start_at
    if start.id is None:
        return f"Start item: none, no entity at {file}:{line}."
    among = (
        f", the lowest id of the {start.candidates} entities on that line"
        if start.candidates > 1
        else ""
    )
    return (
        f'Start item: {start.id}, from the first trace entry "{question.start_label}", '
        f"the entity at {file}:{line}{among}."
    )


def _hop(step: Step) -> str:
    """A step's hop, marked when it is the start itself (AC-10)."""
    return "hop 0 · the start" if step.hop == 0 else f"hop {step.hop}"


def _start_record(report: Report) -> str:
    """The record the walk started in: the start's, else the first item's (AC-12c)."""
    if report.start.id is not None:
        return _record_of(report.start.id)
    return report.findings[0].record if report.findings else ""


def report_lines(report: Report) -> tuple[str, ...]:
    """The report as `trace --eval` prints it, after the chain (AC-37 to AC-41).

    Under the held item view it opens with its label and the meaning line, prints
    `held only` items, and adds the across records line for them (spec 0005).
    """
    question = report.question
    start_record = _start_record(report)
    lines = [HELD_LABEL, HELD_MEANING, ""] if report.with_held else []
    lines += [
        f"Question {question.number}: {question.text}",
        _start_line(question, report.start),
        "",
        "Items that should not be reached:" if question.absence else "Expected items:",
    ]
    for finding in report.findings:
        item = finding.item
        where = f"{item.file}:{item.line}"
        if finding.reached_by is not None:
            step = finding.reached_by
            lines.append(
                f"  reached      {item.label} · {where} · {_hop(step)} · {step.node.canonical_id}"
            )
        elif finding.held_by is not None:
            step = finding.held_by
            lines.append(
                f"  held only    {item.label} · {where} · {_hop(step)} · "
                f"{step.node.canonical_id} · via {', '.join(finding.held_parts)}"
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
    if report.with_held:
        through = [
            f"{f.held_by.node.canonical_id}, hop {f.held_by.hop}"
            for f in report.findings
            if f.held_by is not None and f.record != start_record
        ]
        lines.append(
            f"Across records through held items: yes ({', '.join(through)})"
            if through
            else "Across records through held items: no."
        )
    return tuple(lines)


def _besides_start(report: Report) -> tuple[Finding, ...]:
    """The findings K and M count: all but the items the start node sits on (AC-10b)."""
    start = report.start
    if report.question.absence or start.file is None or start.file_line is None:
        return report.findings
    return tuple(
        f for f in report.findings if (f.item.file, f.item.line) != (start.file, start.file_line)
    )


def _absence_cause(report: Report, finding: Finding) -> str | None:
    """Why one absence item's absence is not proven, the first that applies (AC-17c)."""
    if not report.start_in_clean_slice:
        return "start not in the clean slice"
    if finding.reason is not None and finding.reason is not Reason.NO_LINK:
        return str(finding.reason)
    if not finding.accepted_here:
        return "no accepted entity at the line"
    if finding.held_by is not None:
        return "held only"
    return None


def verdict(report: Report) -> Outcome:
    """A question's result, from its findings only (AC-6 to AC-6c, AC-17 to AC-17c).

    A question with a `trace` list passes only when its start is in the clean slice and
    the clean walk reached every item; a `held only` item is not reached. An absence
    question fails when the clean walk reached an item, passes only when every item's
    absence is proven, and is otherwise `INCONCLUSIVE`, never `PASS`.
    """
    counted = _besides_start(report)
    reached = sum(1 for f in counted if f.reached_by is not None)
    expected = len(counted)
    if not report.question.absence:
        passed = report.start_in_clean_slice and all(
            f.reached_by is not None for f in report.findings
        )
        return Outcome(Verdict.PASS if passed else Verdict.FAIL, reached, expected)
    first = next((f for f in report.findings if f.reached_by is not None), None)
    if first is not None:
        return Outcome(Verdict.FAIL, reached, expected, first_reached=first)
    causes = tuple((f, _absence_cause(report, f)) for f in report.findings)
    if all(cause is None for _, cause in causes):
        return Outcome(Verdict.PASS, reached, expected)
    return Outcome(Verdict.INCONCLUSIVE, reached, expected, causes=causes)


def evidence_line(evidence: Evidence | None) -> str:
    """The evidence line, or `not assessed` when the sidecar has no entry (AC-18)."""
    if evidence is None:
        return "Evidence: not assessed"
    return f"Evidence: {EVIDENCE_WORDS[evidence.level]} · {evidence.reason}"


def result_lines(report: Report, outcome: Outcome, evidence: Evidence | None) -> tuple[str, ...]:
    """The result line, any absence causes, then the evidence line (AC-5, AC-17b, AC-17c)."""
    number = report.question.number
    lines: list[str]
    if outcome.first_reached is not None and outcome.first_reached.reached_by is not None:
        item, step = outcome.first_reached.item, outcome.first_reached.reached_by
        lines = [
            f"Question {number}: FAIL · {item.label} was reached at hop {step.hop}, "
            "a connection the record does not document."
        ]
    elif outcome.verdict is Verdict.INCONCLUSIVE:
        lines = [f"Question {number}: INCONCLUSIVE · absence not provable."]
        lines += [
            f"  {f.item.label} · {f.item.file}:{f.item.line} · {cause or 'none, its absence holds'}"
            for f, cause in outcome.causes
        ]
    else:
        lines = [
            f"Question {number}: {outcome.verdict} · {outcome.reached} of {outcome.expected} "
            "expected items reached besides the start."
        ]
    return (*lines, evidence_line(evidence))
