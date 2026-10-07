"""A fake local Anthropic API and a fault proxy in front of it, for tests with no paid call.

The same arrangement `/check verify` used on 2026-10-06, with the paid API swapped for
a fake: the command under test talks to the proxy over real HTTP through the real SDK,
and the proxy relays to the fake API or injects one fault on a chosen messages call.

The fake answers the token count endpoint (the calibration unit at its measured
61,108, every other unit at `COUNTED`) and streams a valid, empty extraction for every
messages call. Its first messages call writes the 57,494 token cache and every later
one reads it, as the real API did in experiment 0009.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx2

#: What the fake counts for a unit other than the calibration unit: `0010 Context`'s
#: real count (57,494 cached prefix plus 65 uncached).
COUNTED = 57_559
CALIBRATION = 61_108
CACHED_PREFIX = 57_494
UNCACHED = 65
OUTPUT_TOKENS = 80
EMPTY_OUTPUT = '{"entities":[],"relationships":[]}'

#: The faults the proxy can inject on one messages call.
DROP_BEFORE_USAGE = "drop-before-usage"
CUT_AFTER_OUTPUT = "cut-after-output"
OVERLOADED = "overloaded"


def _event(name: str, data: dict[str, Any]) -> bytes:
    return f"event: {name}\ndata: {json.dumps(data)}\n\n".encode()


def response_events(cache_write: int, cache_read: int) -> list[bytes]:
    """One complete streamed response: an empty extraction, then its final usage."""
    return [
        _event(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_fake",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-5",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": UNCACHED,
                        "output_tokens": 1,
                        "cache_creation_input_tokens": cache_write,
                        "cache_read_input_tokens": cache_read,
                    },
                },
            },
        ),
        _event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        _event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": EMPTY_OUTPUT},
            },
        ),
        _event("content_block_stop", {"type": "content_block_stop", "index": 0}),
        _event(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": OUTPUT_TOKENS},
            },
        ),
        _event("message_stop", {"type": "message_stop"}),
    ]


def _send_chunked(handler: BaseHTTPRequestHandler, status: int, chunks: list[bytes]) -> None:
    handler.send_response(status)
    handler.send_header("content-type", "text/event-stream")
    handler.send_header("transfer-encoding", "chunked")
    handler.end_headers()
    for chunk in chunks:
        handler.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
    handler.wfile.write(b"0\r\n\r\n")
    handler.wfile.flush()


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("content-type", "application/json")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    handler.wfile.flush()


@dataclass
class FakeApi:
    """The fake API's state: how many messages calls it answered."""

    messages_calls: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


def _fake_handler(state: FakeApi) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
            path = self.path.split("?")[0]
            if path == "/v1/messages/count_tokens":
                content = body["messages"][0]["content"]
                calibration = content.startswith("Record: 0014\n") and (
                    "Section: Requirements\n" in content
                )
                _send_json(self, 200, {"input_tokens": CALIBRATION if calibration else COUNTED})
                return
            with state.lock:
                state.messages_calls += 1
                first = state.messages_calls == 1
            events = response_events(
                cache_write=CACHED_PREFIX if first else 0, cache_read=0 if first else CACHED_PREFIX
            )
            _send_chunked(self, 200, events)

    return Handler


@dataclass
class FaultProxy:
    """The proxy's state: the fault planned for each messages call, and what it saw."""

    upstream: str
    faults: dict[int, str] = field(default_factory=dict)
    messages_calls: int = 0
    log: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _proxy_handler(state: FaultProxy) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def _cut(self) -> None:
            self.wfile.flush()
            self.close_connection = True
            self.connection.shutdown(2)

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("content-length", 0)))
            path = self.path.split("?")[0]
            fault = ""
            if path == "/v1/messages":
                with state.lock:
                    state.messages_calls += 1
                    number = state.messages_calls
                fault = state.faults.get(number, "")
                state.log.append(f"messages call {number}: {fault or 'relayed'}")
            if fault == OVERLOADED:
                _send_json(
                    self,
                    529,
                    {"type": "error", "error": {"type": "overloaded_error", "message": "x"}},
                )
                return
            if fault == DROP_BEFORE_USAGE:
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("transfer-encoding", "chunked")
                self.end_headers()
                self._cut()
                return
            with httpx2.Client() as client:
                reply = client.post(
                    state.upstream + self.path,
                    content=body,
                    headers={"content-type": "application/json"},
                )
            if fault == CUT_AFTER_OUTPUT:
                # Everything up to and including the output, then nothing: the final
                # usage (`message_delta`) and `message_stop` never arrive.
                events = [e + b"\n\n" for e in reply.content.split(b"\n\n") if e]
                kept = [e for e in events if b"message_delta" not in e and b"message_stop" not in e]
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("transfer-encoding", "chunked")
                self.end_headers()
                for chunk in kept:
                    self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                self._cut()
                return
            if reply.headers.get("content-type", "").startswith("text/event-stream"):
                events = [e + b"\n\n" for e in reply.content.split(b"\n\n") if e]
                _send_chunked(self, reply.status_code, events)
            else:
                _send_json(self, reply.status_code, reply.json())

    return Handler


class _QuietServer(ThreadingHTTPServer):
    """A server that does not print the broken pipes a deliberate cut leaves behind."""

    daemon_threads = True

    def handle_error(self, request: object, client_address: object) -> None:
        pass


@contextmanager
def _serving(handler: type[BaseHTTPRequestHandler]) -> Iterator[str]:
    server = _QuietServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def fake_api_behind_proxy(faults: dict[int, str]) -> Iterator[tuple[str, FakeApi, FaultProxy]]:
    """Serve the fake API and the proxy in front of it; yield the proxy's base URL."""
    api = FakeApi()
    with _serving(_fake_handler(api)) as upstream:
        proxy = FaultProxy(upstream=upstream, faults=dict(faults))
        with _serving(_proxy_handler(proxy)) as base_url:
            yield base_url, api, proxy
