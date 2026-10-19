"""The file every paid ask call is written to as it settles (spec 0009 AC-27 to AC-29).

Append only, like the run artifacts: a write never replaces an existing file. Nothing
reads a record back except the held out guard (AC-32), and only its name and its
`settled` field.
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tracepath.artifacts import ARTIFACTS_DIR, ArtifactCollisionError
from tracepath.ask.answer import Answer, CheckedClaim
from tracepath.ask.retrieve import Item, Pack, item_line

#: Where the records live, relative to the repository root. Tracked in git.
ASKS_DIR = ARTIFACTS_DIR / "asks"

#: How many of the question's words name its record file.
SLUG_WORDS = 5


def record_name(asked_at: datetime, question: str) -> str:
    """`<UTC time>-<slug>.json` for a typed question (AC-28)."""
    words = re.findall(r"[a-z0-9]+", question.lower())[:SLUG_WORDS]
    return f"{_stamp(asked_at)}-{'-'.join(words) or 'question'}.json"


@dataclass(frozen=True)
class EvalSource:
    """The eval file and entry number an `--eval` ask took its question from."""

    file: str
    number: int

    @property
    def stem(self) -> str:
        """The eval file's name without its extension, as record names carry it."""
        return Path(self.file).stem


class RecordUnreadable(Exception):
    """A record the held out guard must read cannot be read as a JSON object."""


def _stamp(asked_at: datetime) -> str:
    return asked_at.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def eval_record_name(asked_at: datetime, source: EvalSource) -> str:
    """`<UTC time>-eval-<stem>-q<N>.json` for an `--eval` ask (AC-28)."""
    return f"{_stamp(asked_at)}-eval-{source.stem}-q{source.number}.json"


def settled_eval_record(root: Path, source: EvalSource) -> Path | None:
    """The first record of a settled call for this eval file and entry, if any (AC-32).

    Matched by the exact name pattern of AC-28, so `-q1` never matches `-q10`. A record
    of a failed call, or of no call, does not count.

    Raises:
        RecordUnreadable: a matching record is not a readable JSON object, so whether
            the question was already answered cannot be told.
    """
    pattern = re.compile(
        r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z-eval-"
        + re.escape(source.stem)
        + rf"-q{source.number}\.json"
    )
    directory = root / ASKS_DIR
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else ():
        if not pattern.fullmatch(path.name):
            continue
        try:
            payload = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RecordUnreadable(f"the ask record {path} cannot be read ({exc})") from exc
        if not isinstance(payload, dict):
            raise RecordUnreadable(f"the ask record {path} is not a JSON object")
        if payload.get("settled") is True:
            return path
    return None


def record_path(root: Path, name: str) -> Path:
    """Where a record of that name lands under `root`."""
    return root / ASKS_DIR / name


def ensure_record_unwritten(root: Path, name: str) -> None:
    """Refuse before the call when a record already sits where this one would land.

    Raises:
        ArtifactCollisionError: a file already exists at that path.
    """
    path = record_path(root, name)
    if path.exists():
        raise ArtifactCollisionError(f"an ask record already exists at {path}")


@dataclass(frozen=True)
class Usage:
    """What one call reported, null meaning unmeasured."""

    input_tokens: int | None
    output_tokens: int | None
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


@dataclass(frozen=True)
class AskRecord:
    """One ask, everything AC-27 names, as it settled.

    `called` is false only for an `--eval` ask that matched no item (AC-29), which
    has no count, bound, reply or usage.
    """

    asked_at: str
    question: str
    pack: Pack
    called: bool
    counted_input_tokens: int | None
    bound_usd: float | None
    ceiling_usd: float
    model: str
    effort: str
    prompt_version: str
    corpus_commit: str
    settled: bool
    answer: Answer | None
    checked: tuple[CheckedClaim, ...]
    raw_response: str | None
    stop_reason: str | None
    error: str | None
    usage: Usage
    cost_usd: float
    recorded_usd: float
    source: EvalSource | None = None

    def payload(self) -> dict[str, Any]:
        """The record as the JSON it is written as."""
        return {
            "asked_at": self.asked_at,
            "question": self.question,
            "eval_file": self.source.file if self.source else None,
            "eval_question": self.source.number if self.source else None,
            "called": self.called,
            "search_words": list(self.pack.words),
            "items": [_item(item) for item in self.pack.items],
            "links": [
                {
                    "type": link.type,
                    "source": link.source,
                    "target": link.target,
                    "phrase": link.phrase,
                    "held": link.held,
                }
                for link in self.pack.links
            ],
            "cut": self.pack.cut,
            "counted_input_tokens": self.counted_input_tokens,
            "bound_usd": self.bound_usd,
            "ceiling_usd": self.ceiling_usd,
            "model": self.model,
            "effort": self.effort,
            "prompt_version": self.prompt_version,
            "corpus_commit": self.corpus_commit,
            "settled": self.settled,
            "raw_response": self.raw_response,
            "stop_reason": self.stop_reason,
            "error": self.error,
            "verdict": self.answer.verdict if self.answer else None,
            "missing": list(self.answer.missing) if self.answer else None,
            "claims": [
                {
                    "text": c.claim.text,
                    "cites": list(c.claim.cites),
                    "basis": c.claim.basis,
                    "rejected_ids": list(c.rejected_ids),
                    "uncited": c.uncited,
                    "inferred": c.inferred,
                    "history": c.history,
                    "held_ids": list(c.held_ids),
                }
                for c in self.checked
            ],
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "cache_creation_input_tokens": self.usage.cache_creation_input_tokens,
                "cache_read_input_tokens": self.usage.cache_read_input_tokens,
            },
            "cost_usd": self.cost_usd,
            "recorded_usd": self.recorded_usd,
        }


def _item(item: Item) -> dict[str, Any]:
    """One item sent, with the line `ask` printed for it."""
    node = item.node
    return {
        "id": node.canonical_id,
        "line": item_line(item).strip(),
        "held": node.held,
        "history": item.history,
        "replaced_by": list(item.replaced_by),
        "hop": item.hop,
        "text": node.text if node.text is not None else node.title or node.mention,
    }


def write_record(root: Path, name: str, record: AskRecord) -> Path:
    """Write one record and return its path.

    Raises:
        ArtifactCollisionError: a file already sits at that path (AC-27b).
        OSError: the file cannot be written.
    """
    ensure_record_unwritten(root, name)
    path = record_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.payload(), indent=2, ensure_ascii=False) + "\n")
    return path


def no_call_record(
    *,
    asked_at: datetime,
    pack: Pack,
    ceiling: float,
    model: str,
    effort: str,
    prompt_version: str,
    commit: str,
    source: EvalSource,
) -> AskRecord:
    """The record of an `--eval` ask that matched no item, so made no call (AC-29)."""
    return AskRecord(
        asked_at=asked_at.isoformat(timespec="seconds"),
        question=pack.question,
        pack=pack,
        called=False,
        counted_input_tokens=None,
        bound_usd=None,
        ceiling_usd=ceiling,
        model=model,
        effort=effort,
        prompt_version=prompt_version,
        corpus_commit=commit,
        settled=False,
        answer=None,
        checked=(),
        raw_response=None,
        stop_reason=None,
        error="no item matched the search words, so no call was made",
        usage=Usage(None, None, 0, 0),
        cost_usd=0.0,
        recorded_usd=0.0,
        source=source,
    )
