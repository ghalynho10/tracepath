# ruff: noqa: F401, F811  (tests take the shared `fake_api` fixture, imported from the extract command tests)
"""Three failures `extract` handled badly, each pinned by a regression test (2026-10-06).

Routed from `/check verify` and `/check review` of the first traced chain
(`docs/session-notes.md`). No paid call: the real SDK runs over a mocked transport.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from tests.test_extract_client import (
    answering,
    first_events,
    recorded_stream,
    requirements_0021,
    settings_for,
)
from tests.test_extract_command import (
    BOUND,
    SETTINGS,
    Script,
    fake_api,
    first_call,
    flat,
    invoke,
    settled,
    targets,
)
from tracepath import cli
from tracepath.artifacts import RunArtifact, write_run
from tracepath.extract.client import FailureKind
from tracepath.extract.metered import Plan, calls_through, fresh_runs, run_metered, summary_lines

OVERLOADED = {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}


# 1. A count response the SDK cannot parse.


def garbled_counts(_: object) -> anthropic.Anthropic:
    """A client whose count endpoint answers 200 with a body that is not JSON."""

    def respond(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, headers={"content-type": "application/json"}, content=b"\x1f\x8b\x08\x00garbled"
        )

    return anthropic.Anthropic(
        api_key="sk-ant-test",
        http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
        max_retries=0,
    )


def test_a_garbled_count_response_exits_1_with_a_message_and_no_traceback(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AGENTS.md: a real failure is a clear message and exit 1, never a raw traceback."""
    monkeypatch.setattr(cli, "build_client", garbled_counts)

    code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run")

    assert code == 1
    assert "the token count endpoint" in flat(stderr)
    assert "Traceback" not in stdout + stderr


# 2. A call the API refuses: its usage was never reported, so it is null, not zero.


def test_a_refused_call_records_null_usage_not_zero() -> None:
    """Spec 0001's storage row: a zero asserts a measurement that was never made."""
    client = answering(lambda: httpx2.Response(529, json=OVERLOADED))

    attempt = calls_through(client, settings_for())(requirements_0021(), 1)

    assert (attempt.input_tokens, attempt.output_tokens) == (None, None)


def test_the_summary_names_a_refused_call_as_an_attempt_with_null_usage(tmp_path: Path) -> None:
    """AC-14: every attempt with null usage is named, a refused call included."""
    body = recorded_stream('{"entities":[],"relationships":[]}', 80)
    client = answering(
        lambda: httpx2.Response(529, json=OVERLOADED),
        *[lambda: httpx2.Response(200, content=body)] * 3,
    )
    plans = [Plan(t, fresh_runs(3), BOUND) for t in targets("0002:Requirements")]

    outcome = run_metered(
        plans,
        calls_through(client, settings_for()),
        SETTINGS,
        tmp_path,
        "2e40bcf",
        "2026-10-06T00:00:00+00:00",
        100.0,
        print,
    )

    assert "  0002:Requirements run 1 attempt 1: failed-run-1-attempt-1.json" in summary_lines(
        outcome
    )


def test_an_error_event_mid_stream_keeps_the_usage_message_start_reported() -> None:
    """The same cause one step later: an error event after `message_start` (the open
    thread in `docs/session-notes.md`) kept 0 where the input and cache counts were known."""
    error = b"event: error\ndata: " + json.dumps(OVERLOADED).encode() + b"\n\n"
    body = first_events(recorded_stream('{"entities":[]}', 80), 2) + error
    client = answering(lambda: httpx2.Response(200, content=body))

    attempt = calls_through(client, settings_for())(requirements_0021(), 1)

    assert (attempt.input_tokens, attempt.cache_read_input_tokens) == (4357, 49114)
    assert attempt.output_tokens is None
    assert attempt.failure_kind is FailureKind.TRANSPORT


# 3. An artifact that cannot be written after its call was paid for.


def test_a_write_error_after_a_paid_call_stops_plainly_with_the_summary(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The call is paid, so the command must say so and stop, not raise mid run."""
    real = write_run
    writes: list[int] = []

    def failing_second(root: Path, artifact: object) -> Path:
        writes.append(1)
        if len(writes) == 2:
            raise OSError(28, "No space left on device")
        assert isinstance(artifact, RunArtifact)
        return real(root, artifact)

    monkeypatch.setattr("tracepath.extract.metered.write_run", failing_second)

    code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert "Traceback" not in stdout + stderr
    assert "2 calls" in flat(stdout), "the summary counts the paid call it could not write"
    assert "could not be written" in flat(stderr)
