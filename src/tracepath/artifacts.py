"""Reading and writing the JSON run artifacts, which are the source of truth.

The graph is derived and disposable; these files are what it is rebuilt from
(spec 0001). Each run records its model id, prompt version, the corpus commit, the
record and section it came from, and a timestamp, so a later prompt change can be
told apart from a stable one when two runs disagree.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tracepath.extract.compare import ReviewItem
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit

#: Where the artifacts live, relative to the repository root. Tracked in git: they
#: are the source of truth, and a clone that could not rebuild the graph from them
#: would make spec 0001's durability claim false everywhere but one machine.
ARTIFACTS_DIR = Path("artifacts")
RUNS_DIR = ARTIFACTS_DIR / "runs"
REVIEW_QUEUE = ARTIFACTS_DIR / "review-queue.json"
REVIEW_LOG = ARTIFACTS_DIR / "review-log.json"


@dataclass(frozen=True)
class RunArtifact:
    """One run of one unit, with everything needed to read it back later."""

    record: str
    section: str
    section_slug: str
    file: str
    unit_kind: str
    run: int
    model: str
    prompt_version: str
    commit: str
    extracted_at: str
    max_output_tokens: int
    effort: str
    output: ExtractionOutput


def now_utc() -> str:
    """The current time, as the artifacts record it. Passed in, never reached for."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def build_artifact(
    unit: Unit,
    section_slug: str,
    run: int,
    output: ExtractionOutput,
    model: str,
    prompt_version: str,
    commit: str,
    extracted_at: str,
    max_output_tokens: int,
    effort: str,
) -> RunArtifact:
    """Assemble one run artifact. Pure: every value is given, none is looked up."""
    return RunArtifact(
        record=unit.record_id,
        section=unit.section,
        section_slug=section_slug,
        file=unit.path,
        unit_kind=str(unit.kind),
        run=run,
        model=model,
        prompt_version=prompt_version,
        commit=commit,
        extracted_at=extracted_at,
        max_output_tokens=max_output_tokens,
        effort=effort,
        output=output,
    )


def artifact_payload(artifact: RunArtifact) -> dict[str, Any]:
    """The JSON shape one run artifact is written as."""
    return {
        "record": artifact.record,
        "section": artifact.section,
        "section_slug": artifact.section_slug,
        "file": artifact.file,
        "unit_kind": artifact.unit_kind,
        "run": artifact.run,
        "model": artifact.model,
        "prompt_version": artifact.prompt_version,
        "commit": artifact.commit,
        "extracted_at": artifact.extracted_at,
        "max_output_tokens": artifact.max_output_tokens,
        "effort": artifact.effort,
        "output": artifact.output.model_dump(mode="json"),
    }


def run_path(root: Path, artifact: RunArtifact) -> Path:
    """Where one run artifact is written."""
    return root / RUNS_DIR / artifact.record / artifact.section_slug / f"run-{artifact.run}.json"


def write_run(root: Path, artifact: RunArtifact) -> Path:
    """Write one run artifact and return the path it landed at."""
    path = run_path(root, artifact)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact_payload(artifact), indent=2) + "\n")
    return path


def read_run(path: Path) -> RunArtifact:
    """Read one run artifact back, validating its output against the schema."""
    payload = json.loads(path.read_text())
    return RunArtifact(
        record=payload["record"],
        section=payload["section"],
        section_slug=payload["section_slug"],
        file=payload["file"],
        unit_kind=payload["unit_kind"],
        run=payload["run"],
        model=payload["model"],
        prompt_version=payload["prompt_version"],
        commit=payload["commit"],
        extracted_at=payload["extracted_at"],
        max_output_tokens=payload["max_output_tokens"],
        effort=payload["effort"],
        output=ExtractionOutput.model_validate(payload["output"]),
    )


def review_entry(
    record: str, section: str, item: ReviewItem, model: str, extracted_at: str
) -> dict[str, Any]:
    """One item held back from the graph, and every reason it was held.

    `canonical_id` is null for a relationship, which has no id of its own; its
    `signature` already carries its type and both endpoints. A reason is a name plus
    an optional detail, because `endpoint_not_accepted` must name the entity the link
    is waiting on, and a bare word cannot carry it.
    """
    return {
        "record": record,
        "section": section,
        "canonical_id": item.canonical_id,
        "line": item.line,
        "signature": list(item.signature),
        "reasons": [{"name": str(reason.name), "detail": reason.detail} for reason in item.reasons],
        "model": model,
        "queued_at": extracted_at,
    }


def write_review_queue(root: Path, entries: list[dict[str, Any]]) -> Path:
    """Write the review queue, replacing whatever was there."""
    path = root / REVIEW_QUEUE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
    return path


def write_review_log(root: Path, entries: list[dict[str, Any]]) -> Path:
    """Write the review log, the record of what a person actually ruled on."""
    path = root / REVIEW_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
    return path
