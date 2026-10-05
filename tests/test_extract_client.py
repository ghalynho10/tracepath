import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import anthropic
import httpx2
import pytest
from pydantic import ValidationError

from tracepath.config import (
    DEFAULT_MODEL,
    RUNS_PER_UNIT,
    AnthropicSettings,
    SettingsInvalid,
    load_anthropic_settings,
)
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    ExtractionFailed,
    extract_once,
    system_blocks,
    system_prompt,
    user_prompt,
)
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, split_units

SNAPSHOT = Path(__file__).resolve().parents[1] / "corpus" / "jobhunt" / "docs"


# A missing key fails at startup, not at the first call.


def test_a_missing_api_key_fails_with_a_message_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(SettingsInvalid) as caught:
        load_anthropic_settings()

    assert "ANTHROPIC_API_KEY" in str(caught.value)
    assert ".env.example" in str(caught.value)


def test_an_empty_api_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    with pytest.raises(SettingsInvalid):
        load_anthropic_settings()


def test_settings_carry_the_model_and_run_policy_the_spec_chose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

    settings = load_anthropic_settings()

    assert settings.model == DEFAULT_MODEL == "claude-sonnet-5"
    assert settings.runs_per_unit == RUNS_PER_UNIT == 3


def test_the_model_can_be_overridden_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5")

    assert load_anthropic_settings().model == "claude-opus-5"


def test_the_example_env_file_names_the_key_so_a_fresh_clone_knows_to_set_it() -> None:
    example = (Path(__file__).resolve().parents[1] / ".env.example").read_text()

    assert "ANTHROPIC_API_KEY" in example


# The prompt and the message are built from the unit, with no schema of their own.


def test_the_prompt_carries_the_unit_and_everything_a_citation_needs() -> None:
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"
    unit = next(
        u
        for u in split_units("specs/0012-model-client-router/index.md", path.read_text())
        if u.section == "Requirements"
    )

    message = user_prompt(unit)

    assert "0012" in message
    assert "Requirements" in message
    assert unit.text in message


def test_the_prompt_tells_the_model_not_to_own_identity_or_the_markers() -> None:
    assert "Never invent an id" in system_prompt()
    assert "derived:N" in system_prompt()
    assert "read from the characters by code" in system_prompt()
    assert "unclassified" in system_prompt()


def test_the_prompt_version_is_recorded_so_a_prompt_change_is_visible() -> None:
    assert PROMPT_VERSION
    assert MAX_TOKENS >= 16000


# Known defect, owed to /debug on its own fix/ branch (docs/session-notes.md): a
# connection that drops mid stream escapes `extract_once()` as a raw transport error,
# so the attempt is never recorded and `run_with_retry()` never retries it. Experiment
# 0006 lost a paid call to this. Strict, so the fix turns it into a failing XPASS and
# the marker gets removed with it.


class DroppedStream:
    """A stream that opens, then loses its connection before the final message."""

    current_message_snapshot = None

    def __enter__(self) -> "DroppedStream":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get_final_message(self) -> object:
        raise httpx2.RemoteProtocolError(
            "peer closed connection without sending complete message body"
        )


@pytest.mark.xfail(
    strict=True,
    raises=httpx2.RemoteProtocolError,
    reason="owed to /debug: extract_once() does not catch a mid stream transport error",
)
def test_a_connection_dropped_mid_stream_is_recorded_as_a_failed_attempt() -> None:
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"
    unit = next(
        u
        for u in split_units("specs/0012-model-client-router/index.md", path.read_text())
        if u.section == "Requirements"
    )
    settings = AnthropicSettings(
        api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort="medium"
    )
    client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **_: DroppedStream()))

    with pytest.raises(ExtractionFailed) as failed:
        extract_once(cast("anthropic.Anthropic", client), settings, unit)

    (attempt,) = failed.value.attempts
    assert attempt.error is not None
    assert attempt.output is None


# A schema failure is recorded with the whole response's usage, not the placeholder
# `message_start` carries. Driven through the real SDK stream over a mocked transport,
# replaying a committed failed attempt's own response text, so no paid call is made.

FAILED_ATTEMPT = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "runs"
    / "0021"
    / "requirements"
    / "failed-run-2-attempt-1.json"
)


def recorded_stream(text: str, output_tokens: int) -> bytes:
    """The server sent events of one response: `text`, then its final usage."""
    events: list[tuple[str, dict[str, object]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_recorded",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-5",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": 4357,
                        "output_tokens": 2,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 49114,
                    },
                },
            },
        ),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": text},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": output_tokens},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events).encode()


def replaying_client(body: bytes, requests: list[httpx2.Request]) -> anthropic.Anthropic:
    """A real client whose every request gets `body` back, and is kept in `requests`."""

    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    return anthropic.Anthropic(
        api_key="sk-ant-test",
        http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
        max_retries=0,
    )


def requirements_0021() -> Unit:
    """`0021 ## Requirements`, the unit the recorded failure was made against."""
    path = SNAPSHOT / "specs" / "0021-seeded-demo-account" / "index.md"
    return next(
        u
        for u in split_units("specs/0021-seeded-demo-account/index.md", path.read_text())
        if u.section == "Requirements"
    )


def test_a_schema_failure_records_the_whole_responses_output_tokens() -> None:
    recorded = json.loads(FAILED_ATTEMPT.read_text())
    client = replaying_client(recorded_stream(recorded["raw_response"], 8123), [])
    settings = AnthropicSettings(
        api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort="medium"
    )

    with pytest.raises(ExtractionFailed, match="did not satisfy the schema") as failed:
        extract_once(client, settings, requirements_0021())

    (attempt,) = failed.value.attempts
    assert attempt.output is None
    assert attempt.output_tokens == 8123
    assert attempt.stop_reason == "end_turn"
    assert attempt.input_tokens == 4357
    assert attempt.cache_read_input_tokens == 49114
    assert attempt.raw_response == recorded["raw_response"]


def test_the_request_is_the_one_the_sdk_builds_from_output_format() -> None:
    recorded = json.loads(FAILED_ATTEMPT.read_text())
    body = recorded_stream(recorded["raw_response"], 8123)
    settings = AnthropicSettings(
        api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort="medium"
    )
    unit = requirements_0021()
    ours: list[httpx2.Request] = []
    sdk: list[httpx2.Request] = []

    with pytest.raises(ExtractionFailed):
        extract_once(replaying_client(body, ours), settings, unit)
    with (
        pytest.raises(ValidationError),
        replaying_client(body, sdk).messages.stream(
            model=settings.model,
            max_tokens=MAX_TOKENS,
            system=system_blocks(),
            messages=[{"role": "user", "content": user_prompt(unit)}],
            output_format=ExtractionOutput,
            output_config={"effort": "medium"},
        ) as stream,
    ):
        stream.get_final_message()

    assert json.loads(ours[0].content) == json.loads(sdk[0].content)
