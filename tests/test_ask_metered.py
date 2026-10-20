"""The guarded ask call, its bound and its record (spec 0009 AC-21 to AC-28). No paid call.

Two layers: `ask_metered()` with a scripted call, and the real SDK over a mocked
transport for how `ask_calls_through()` reads a reply, the way the extract tests do.
"""

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import pytest

from tests import ask_fixture as fx
from tracepath.artifacts import ArtifactCollisionError
from tracepath.ask.answer import ASK_MAX_TOKENS, PROMPT_VERSION, Answer
from tracepath.ask.record import ASKS_DIR, record_name
from tracepath.ask.retrieve import Pack, build_pack
from tracepath.config import DEFAULT_MODEL, AnthropicSettings
from tracepath.extract.cost import EstimateUnavailable, ask_bound
from tracepath.extract.metered import (
    AskAttempt,
    AskOutcome,
    ask_calls_through,
    ask_cost_line,
    ask_metered,
    count_ask_input,
)

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = AnthropicSettings(
    api_key="sk-ant-test", model=DEFAULT_MODEL, runs_per_unit=3, effort="medium"
)
COUNTED = 6_000
BOUND = ask_bound(COUNTED, DEFAULT_MODEL)
ASKED_AT = datetime(2026, 10, 20, 9, 12, 31, tzinfo=UTC)
REPLY = json.dumps(
    {
        "verdict": "answered",
        "claims": [
            {"text": "It is amended.", "cites": ["9101/AC-1", "9101/AC-2"], "basis": "link"},
            {"text": "Elsewhere.", "cites": ["0001/AC-1"], "basis": "text"},
        ],
        "missing": [],
    }
)


@pytest.fixture
def pack() -> Pack:
    return build_pack(fx.graph(), "landing")


def answered(output_tokens: int = 900) -> AskAttempt:
    return AskAttempt(
        input_tokens=COUNTED,
        output_tokens=output_tokens,
        answer=Answer.model_validate_json(REPLY),
        raw_response=REPLY,
        stop_reason="end_turn",
    )


def failed() -> AskAttempt:
    return AskAttempt(input_tokens=None, output_tokens=None, error="the call failed (overloaded)")


class Script:
    """A scripted ask call: hands back each attempt in turn, keeps every pack it got."""

    def __init__(self, *attempts: AskAttempt) -> None:
        self.attempts = list(attempts)
        self.packs: list[Pack] = []

    def __call__(self, pack: Pack) -> AskAttempt:
        self.packs.append(pack)
        return self.attempts[len(self.packs) - 1]


def saved_record(outcome: AskOutcome) -> dict[str, Any]:
    assert outcome.path is not None
    loaded: dict[str, Any] = json.loads(outcome.path.read_text())
    return loaded


def metered(root: Path, pack: Pack, script: Script, ceiling: float = 1.0) -> AskOutcome:
    return ask_metered(
        pack,
        script,
        SETTINGS,
        root=root,
        name=record_name(ASKED_AT, "Why the landing rule?"),
        asked_at=ASKED_AT,
        commit="2e40bcf",
        counted=COUNTED,
        bound=BOUND,
        ceiling=ceiling,
    )


# AC-21: one spend path, inside the fence.


def test_ac_21_the_ask_package_names_no_paid_marker() -> None:
    """covers: AC-21, key invariant 4."""
    markers = ("import anthropic", "from anthropic", "build_client", "extract_once")
    sources = sorted((ROOT / "src" / "tracepath" / "ask").glob("*.py"))

    assert sources
    assert [p.name for p in sources if any(m in p.read_text() for m in markers)] == []


# AC-22, AC-23: the ceiling and the bound.


def test_ac_23_the_bound_is_the_counted_input_and_the_output_cap_at_their_rates() -> None:
    """covers: AC-23. claude-sonnet-5-5: input $2, output $10 per million."""
    assert math.isclose(BOUND, (COUNTED * 2.00 + ASK_MAX_TOKENS * 10.00) / 1e6)


def test_ac_23_a_model_with_no_recorded_rates_is_never_priced() -> None:
    """covers: AC-23."""
    with pytest.raises(EstimateUnavailable, match="no rates are recorded"):
        ask_bound(COUNTED, "claude-unpriced-1")


def test_ac_22_a_bound_above_the_ceiling_stops_before_the_call(tmp_path: Path, pack: Pack) -> None:
    """covers: AC-22."""
    script = Script(answered())

    outcome = metered(tmp_path, pack, script, ceiling=BOUND / 2)

    assert outcome.stop == "stopping here before the call: ceiling"
    assert script.packs == []
    assert not (tmp_path / ASKS_DIR).exists()


def test_ac_22_a_bound_equal_to_the_ceiling_makes_the_call(tmp_path: Path, pack: Pack) -> None:
    """covers: AC-22 (the bound must not pass the ceiling)."""
    script = Script(answered())

    metered(tmp_path, pack, script, ceiling=BOUND)

    assert len(script.packs) == 1


# AC-24, AC-25: what a call costs, settled or failed.


def test_ac_24_a_failed_call_counts_at_its_bound_is_saved_and_not_retried(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-24."""
    script = Script(failed(), answered())

    outcome = metered(tmp_path, pack, script)

    assert len(script.packs) == 1
    assert outcome.cost_usd == BOUND
    assert not outcome.settled
    saved = saved_record(outcome)
    assert saved["settled"] is False
    assert saved["error"] == "the call failed (overloaded)"
    assert saved["cost_usd"] == BOUND


class Raises:
    """An ask call that raises after the request is sent, and counts how often it ran."""

    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls = 0

    def __call__(self, pack: Pack) -> AskAttempt:
        self.calls += 1
        raise self.error


@pytest.mark.parametrize("error", [KeyboardInterrupt(), RuntimeError("stream broke")])
def test_ac_24_note_a_call_that_raises_is_saved_failed_at_its_bound_before_it_propagates(
    tmp_path: Path, pack: Pack, error: BaseException
) -> None:
    """covers: AC-24 note of 2026-10-19 (review finding 1)."""
    call = Raises(error)

    with pytest.raises(type(error)) as raised:
        ask_metered(
            pack,
            call,
            SETTINGS,
            root=tmp_path,
            name=record_name(ASKED_AT, "Why the landing rule?"),
            asked_at=ASKED_AT,
            commit="2e40bcf",
            counted=COUNTED,
            bound=BOUND,
            ceiling=1.0,
        )

    assert call.calls == 1
    (path,) = (tmp_path / ASKS_DIR).iterdir()
    saved = json.loads(path.read_text())
    assert saved["called"] is True
    assert saved["settled"] is False
    assert saved["error"].startswith(f"the call raised {type(error).__name__}")
    assert saved["cost_usd"] == BOUND
    assert saved["usage"]["input_tokens"] is None
    assert any(str(path) in note for note in raised.value.__notes__)


def test_ac_24_note_a_raising_call_whose_record_cannot_be_written_still_propagates(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-24 note of 2026-10-19: the original error is raised, and says the record
    is lost. `artifacts/asks` is a file, so nothing can be written under it.
    """
    (tmp_path / ASKS_DIR).parent.mkdir(parents=True)
    (tmp_path / ASKS_DIR).write_text("in the way")

    with pytest.raises(KeyboardInterrupt) as raised:
        ask_metered(
            pack,
            Raises(KeyboardInterrupt()),
            SETTINGS,
            root=tmp_path,
            name=record_name(ASKED_AT, "Why the landing rule?"),
            asked_at=ASKED_AT,
            commit="2e40bcf",
            counted=COUNTED,
            bound=BOUND,
            ceiling=1.0,
        )

    assert any("record is lost" in note for note in raised.value.__notes__)


def test_ac_25_the_cost_line_gives_calls_tokens_both_costs_and_the_ceiling(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-25. A settled call costs its recorded usage by both rules."""
    outcome = metered(tmp_path, pack, Script(answered(output_tokens=900)))
    cost = (COUNTED * 2.00 + 900 * 10.00) / 1e6

    assert ask_cost_line(outcome, 0.5) == (
        f"Cost: 1 call, 6,000 in, 900 out, ${cost:.4f} by recorded usage, ${cost:.4f} by "
        "the guard's rule, ceiling $0.50."
    )


def test_ac_25_a_failed_call_with_no_usage_says_unmeasured_and_costs_its_bound(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-25, AC-24."""
    line = ask_cost_line(metered(tmp_path, pack, Script(failed())), 0.5)

    assert line == (
        f"Cost: 1 call, unmeasured in, unmeasured out, $0.0000 by recorded usage, "
        f"${BOUND:.4f} by the guard's rule, ceiling $0.50."
    )


# AC-27 to AC-28: the record.


def test_ac_27_the_record_holds_everything_the_call_was_made_from_and_returned(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-27."""
    outcome = metered(tmp_path, pack, Script(answered()))
    saved = saved_record(outcome)

    assert saved["question"] == "landing"
    assert saved["search_words"] == ["landing"]
    assert [i["id"] for i in saved["items"]] == [i.node.canonical_id for i in pack.items]
    assert saved["items"][2]["line"].startswith("9101/AC-3  AcceptanceCriterion  accepted  STRUCK")
    assert {
        "type": "SUPERSEDED_BY",
        "source": "9101/AC-3",
        "target": "9101/AC-4",
        "phrase": "replaced",
        "held": True,
    } in saved["links"]
    assert saved["raw_response"] == REPLY
    assert saved["claims"][1]["rejected_ids"] == ["0001/AC-1"]
    assert saved["claims"][0]["held_ids"] == ["9101/AC-2"]
    assert saved["usage"]["input_tokens"] == COUNTED
    assert math.isclose(saved["cost_usd"], saved["recorded_usd"])
    assert (saved["model"], saved["effort"]) == (DEFAULT_MODEL, "medium")
    assert (saved["prompt_version"], saved["corpus_commit"]) == (PROMPT_VERSION, "2e40bcf")
    assert saved["asked_at"] == "2026-10-20T09:12:31+00:00"


def test_ac_27b_a_second_record_at_the_same_path_is_refused_before_the_call(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-27b."""
    metered(tmp_path, pack, Script(answered()))
    script = Script(answered())

    with pytest.raises(ArtifactCollisionError, match="already exists"):
        metered(tmp_path, pack, script)
    assert script.packs == []


def test_ac_27c_a_record_that_cannot_be_written_is_reported_lost_with_its_cost(
    tmp_path: Path, pack: Pack
) -> None:
    """covers: AC-27c. `artifacts/asks` is a file, so nothing can be written under it."""
    (tmp_path / ASKS_DIR).parent.mkdir(parents=True)
    (tmp_path / ASKS_DIR).write_text("in the way")

    outcome = metered(tmp_path, pack, Script(answered()))

    assert outcome.lost is not None
    assert outcome.path is None
    assert outcome.cost_usd > 0


def test_ac_28_a_typed_questions_record_is_named_by_utc_time_and_slug() -> None:
    """covers: AC-28."""
    local = datetime(2026, 10, 20, 11, 12, 31, tzinfo=UTC).astimezone()

    assert record_name(local, "Why does the landing rule's read exist?") == (
        "2026-10-20T11-12-31Z-why-does-the-landing-rule.json"
    )
    assert record_name(ASKED_AT, "???") == "2026-10-20T09-12-31Z-question.json"


# The real SDK over a mocked transport: how a reply is read (AC-15, AC-24, AC-26).


def ask_stream(text: str, stop_reason: str = "end_turn", output_tokens: int = 700) -> bytes:
    """The server sent events of one ask reply: `text`, then its stop reason and usage."""
    events: list[tuple[str, dict[str, object]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_ask",
                    "type": "message",
                    "role": "assistant",
                    "model": DEFAULT_MODEL,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": COUNTED, "output_tokens": 1},
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
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": output_tokens},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(f"event: {n}\ndata: {json.dumps(d)}\n\n" for n, d in events).encode()


def client_answering(
    status: int,
    body: bytes,
    requests: list[httpx2.Request],
    content_type: str = "text/event-stream",
) -> anthropic.Anthropic:
    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(status, headers={"content-type": content_type}, content=body)

    return anthropic.Anthropic(
        api_key="sk-ant-test",
        http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
        max_retries=0,
    )


def test_a_valid_reply_settles_with_its_usage_and_sends_the_pack(pack: Pack) -> None:
    """covers: AC-15, AC-26 (one request, the output cap, effort, no cache)."""
    requests: list[httpx2.Request] = []
    attempt = ask_calls_through(client_answering(200, ask_stream(REPLY), requests), SETTINGS)(pack)

    assert attempt.answer == Answer.model_validate_json(REPLY)
    assert (attempt.input_tokens, attempt.output_tokens) == (COUNTED, 700)
    (request,) = requests
    sent = json.loads(request.content)
    assert sent["max_tokens"] == ASK_MAX_TOKENS
    assert sent["output_config"]["effort"] == "medium"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert isinstance(sent["system"], str)
    assert "[9101/AC-3]" in sent["messages"][0]["content"]


@pytest.mark.parametrize(
    ("body", "said"),
    [
        (ask_stream(REPLY[:40], stop_reason="max_tokens"), "stopped on max_tokens"),
        (ask_stream("", stop_reason="refusal"), "stopped on refusal"),
        (ask_stream('{"verdict": "maybe"}'), "did not validate as an Answer"),
    ],
)
def test_ac_24_a_cut_off_refused_or_invalid_reply_is_a_failed_attempt_with_usage(
    pack: Pack, body: bytes, said: str
) -> None:
    """covers: AC-24."""
    requests: list[httpx2.Request] = []
    attempt = ask_calls_through(client_answering(200, body, requests), SETTINGS)(pack)

    assert attempt.answer is None
    assert attempt.error is not None and said in attempt.error
    assert attempt.input_tokens == COUNTED
    assert len(requests) == 1


def test_ac_24_an_api_error_is_a_failed_attempt_with_no_usage_and_no_retry(pack: Pack) -> None:
    """covers: AC-24."""
    requests: list[httpx2.Request] = []
    overloaded = json.dumps(
        {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
    ).encode()
    client = client_answering(529, overloaded, requests, content_type="application/json")

    attempt = ask_calls_through(client, SETTINGS)(pack)

    assert attempt.answer is None
    assert attempt.input_tokens is None
    assert attempt.error is not None and "the call failed" in attempt.error
    assert len(requests) == 1


def test_the_count_sends_the_same_system_message_and_schema_as_the_call(pack: Pack) -> None:
    """covers: AC-23 (the count is over the real request)."""
    requests: list[httpx2.Request] = []
    client = client_answering(
        200, json.dumps({"input_tokens": 1234}).encode(), requests, "application/json"
    )

    assert count_ask_input(client, SETTINGS, pack) == 1234
    sent = json.loads(requests[0].content)
    assert requests[0].url.path == "/v1/messages/count_tokens"
    assert "[9101/AC-3]" in sent["messages"][0]["content"]
    assert sent["output_config"]["format"]["type"] == "json_schema"
