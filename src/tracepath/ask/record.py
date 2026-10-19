"""The file every paid ask call is written to as it settles (spec 0009 AC-27 to AC-28).

Append only, like the run artifacts: a write never replaces an existing file. Nothing
reads a record back except the held out guard of build plan step 5.
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
    stamp = asked_at.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{stamp}-{'-'.join(words) or 'question'}.json"


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
    """One paid ask call, everything AC-27 names, as it settled."""

    asked_at: str
    question: str
    pack: Pack
    counted_input_tokens: int
    bound_usd: float
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

    def payload(self) -> dict[str, Any]:
        """The record as the JSON it is written as."""
        return {
            "asked_at": self.asked_at,
            "question": self.question,
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
