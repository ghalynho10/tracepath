"""Reading and writing the JSON run artifacts, which are the source of truth.

The graph is derived and disposable; these files are what it is rebuilt from
(spec 0001). Each run records its model id, prompt version, the corpus commit, the
record and section it came from, and a timestamp, so a later prompt change can be
told apart from a stable one when two runs disagree.
"""

import hashlib
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

#: Bumped whenever `RunArtifact`'s own field shape changes, so a reader can tell which
#: shape one artifact was written under (spec 0001's storage row, amended 2026-09-28).
#: `2` is the first version to carry `run_id`, `artifact_format_version` itself, a
#: `unit_sha256`, and `raw_response`/`stop_reason`; every artifact written before this
#: amendment reads back as version `None`, meaning unversioned, not version `1`.
ARTIFACT_FORMAT_VERSION = 2


class ArtifactCollisionError(Exception):
    """A write was about to replace an existing artifact instead of adding one.

    Every run id is unique and every superseded move goes to its own timestamped
    directory, so a real collision means something is wrong upstream (a re-run reusing
    a settled run number, a slug collision); silently overwriting would destroy
    evidence a rebuild depends on (spec 0001's storage row, amended 2026-09-28).
    """


@dataclass(frozen=True)
class RunArtifact:
    """One attempt at one run of one unit, with everything needed to read it back.

    `input_tokens` and `output_tokens` are what the API reported for **this attempt
    alone**, never a running total, so the cost of a failed attempt stays visible
    beside the retry that replaced it rather than folded into it (spec 0001).

    Three fields are nullable, each for one reason:

    * `output` is null when the call raised. Such a call still produces an artifact,
      because an artifact that only exists for calls that succeeded is exactly what
      made the first 21 call run's cost unrecoverable.
    * `error` says why, so a failed artifact is a record rather than a blank.
    * `input_tokens` and `output_tokens` are null only on an artifact written before
      the amendment that added them, where the numbers are unrecoverable. Null there
      means unmeasured, and the pipeline never writes one.

    The two cache counts are the system prompt written to the prompt cache and read
    from it, apart from `input_tokens` because each bills at its own rate (spec 0003,
    AC-19). An artifact written before caching reads them as 0, which is true rather
    than unmeasured: no call before `0003.0` sent a cache marker at all.

    Four fields amend spec 0001's storage row (2026-09-28): `run_id` (a fresh
    identifier per call, distinct from `attempt`'s retry accounting), the writer's own
    `artifact_format_version`, a `unit_sha256` of the unit text this run was actually
    made against (so a rebuild can confirm the committed corpus snapshot has not moved
    under a committed run), and the raw `raw_response`/`stop_reason` alongside the
    already parsed `output`. All four are null on an artifact written before this
    amendment, the same "null means unrecorded, not zero" reading `input_tokens`
    already carries; the pipeline itself never writes one null.
    """

    record: str
    section: str
    section_slug: str
    file: str
    unit_kind: str
    run: int
    attempt: int
    model: str
    prompt_version: str
    commit: str
    extracted_at: str
    max_output_tokens: int
    effort: str
    input_tokens: int | None
    output_tokens: int | None
    output: ExtractionOutput | None
    run_id: str | None = None
    artifact_format_version: int | None = None
    unit_sha256: str | None = None
    raw_response: str | None = None
    stop_reason: str | None = None
    error: str | None = None
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


def now_utc() -> str:
    """The current time, as the artifacts record it. Passed in, never reached for."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def build_artifact(
    unit: Unit,
    section_slug: str,
    run: int,
    output: ExtractionOutput | None,
    model: str,
    prompt_version: str,
    commit: str,
    extracted_at: str,
    max_output_tokens: int,
    effort: str,
    input_tokens: int,
    output_tokens: int,
    attempt: int = 1,
    run_id: str | None = None,
    raw_response: str | None = None,
    stop_reason: str | None = None,
    error: str | None = None,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> RunArtifact:
    """Assemble one run artifact. Pure: every value is given, none is looked up.

    `unit_sha256` is derived from `unit.text` here, never passed in, since it is a
    pure function of an argument this call already has (spec 0001's storage row,
    amended 2026-09-28). `run_id` stays a parameter: the caller's own call is what
    mints it, this function only carries it through.
    """
    return RunArtifact(
        record=unit.record_id,
        section=unit.section,
        section_slug=section_slug,
        file=unit.path,
        unit_kind=str(unit.kind),
        run=run,
        attempt=attempt,
        model=model,
        prompt_version=prompt_version,
        commit=commit,
        extracted_at=extracted_at,
        max_output_tokens=max_output_tokens,
        effort=effort,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        output=output,
        run_id=run_id,
        artifact_format_version=ARTIFACT_FORMAT_VERSION,
        unit_sha256=hashlib.sha256(unit.text.encode()).hexdigest(),
        raw_response=raw_response,
        stop_reason=stop_reason,
        error=error,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
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
        "attempt": artifact.attempt,
        "model": artifact.model,
        "prompt_version": artifact.prompt_version,
        "commit": artifact.commit,
        "extracted_at": artifact.extracted_at,
        "max_output_tokens": artifact.max_output_tokens,
        "effort": artifact.effort,
        "input_tokens": artifact.input_tokens,
        "output_tokens": artifact.output_tokens,
        "cache_creation_input_tokens": artifact.cache_creation_input_tokens,
        "cache_read_input_tokens": artifact.cache_read_input_tokens,
        "run_id": artifact.run_id,
        "artifact_format_version": artifact.artifact_format_version,
        "unit_sha256": artifact.unit_sha256,
        "raw_response": artifact.raw_response,
        "stop_reason": artifact.stop_reason,
        "error": artifact.error,
        "output": None if artifact.output is None else artifact.output.model_dump(mode="json"),
    }


def run_path(root: Path, artifact: RunArtifact) -> Path:
    """Where one run artifact is written.

    A settled run takes `run-N.json`, which is also its batch `custom_id` (spec 0001).
    A failed attempt lands beside it under a name the `run-*.json` glob does not
    match, so a rebuild reads the runs and never mistakes a failure for a fourth run.
    A retry that succeeds takes the original `run-N.json`, because the retry replaces
    the failed attempt rather than adding a run.
    """
    directory = root / RUNS_DIR / artifact.record / artifact.section_slug
    if artifact.output is None:
        return directory / f"failed-run-{artifact.run}-attempt-{artifact.attempt}.json"
    return directory / f"run-{artifact.run}.json"


def write_run(root: Path, artifact: RunArtifact) -> Path:
    """Write one run artifact and return the path it landed at.

    Raises:
        ArtifactCollisionError: a file already sits at the path this artifact would
            take. A settled run or a failed attempt each has its own path (`run_path()`
            above); an existing file there means something upstream reused a number
            rather than a genuine retry, and silently replacing it would destroy the
            evidence a rebuild depends on (spec 0001's storage row, amended 2026-09-28).
    """
    path = run_path(root, artifact)
    if path.exists():
        raise ArtifactCollisionError(f"an artifact already exists at {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact_payload(artifact), indent=2) + "\n")
    return path


def read_run(path: Path) -> RunArtifact:
    """Read one run artifact back, validating its output against the schema.

    Token usage is read with `.get()`, alone among these fields. Every other one has
    been written since the first artifact; usage was added by the amendment of
    2026-09-23, and the 24 artifacts written before it cannot recover the numbers
    without re-calling the model. Absent therefore reads as null, meaning unmeasured,
    which is the honest value. The pipeline itself never writes one.
    """
    payload = json.loads(path.read_text())
    output = payload.get("output")
    return RunArtifact(
        record=payload["record"],
        section=payload["section"],
        section_slug=payload["section_slug"],
        file=payload["file"],
        unit_kind=payload["unit_kind"],
        run=payload["run"],
        attempt=payload.get("attempt", 1),
        model=payload["model"],
        prompt_version=payload["prompt_version"],
        commit=payload["commit"],
        extracted_at=payload["extracted_at"],
        max_output_tokens=payload["max_output_tokens"],
        effort=payload["effort"],
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        output=None if output is None else ExtractionOutput.model_validate(output),
        run_id=payload.get("run_id"),
        artifact_format_version=payload.get("artifact_format_version"),
        unit_sha256=payload.get("unit_sha256"),
        raw_response=payload.get("raw_response"),
        stop_reason=payload.get("stop_reason"),
        error=payload.get("error"),
        cache_creation_input_tokens=payload.get("cache_creation_input_tokens", 0),
        cache_read_input_tokens=payload.get("cache_read_input_tokens", 0),
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
    """Write the review log, the record of what a person actually ruled on.

    Only a caller holding real rulings calls this. A pipeline run holds none, so it
    calls `ensure_review_log()` instead.
    """
    path = root / REVIEW_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
    return path


def ensure_review_log(root: Path) -> Path:
    """Create an empty review log if there is none, and never touch an existing one.

    The log records what a person ruled on, and a pipeline run rules on nothing, so it
    has nothing to put here. Overwriting would erase a reviewer's work on every run.
    Spec 0002 states plainly that no review workflow is designed yet; this keeps the
    file the specs name present and tracked without pretending one exists.
    """
    path = root / REVIEW_LOG
    if path.exists():
        return path
    return write_review_log(root, [])
