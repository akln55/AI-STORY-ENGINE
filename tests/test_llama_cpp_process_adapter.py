"""Tests for engine/ai/llama_cpp_process_adapter.py.

No real llama-server or external network is required. A tiny scripted
HTTP server (stdlib `http.server`, bound to 127.0.0.1 on an ephemeral port)
stands in for llama-server -- this exercises the real HTTP request/response
path (request reaches the server, body shape is correct, response parsing
is correct) without any mocking library or third-party dependency
(CONVENTIONS §4). "Server unreachable" is tested by pointing at a port
nothing is listening on, not by mocking urllib.
"""

from __future__ import annotations

import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from engine.ai.adapter_base import AIAdapter
from engine.ai.llama_cpp_process_adapter import (
    LlamaCppProcessAdapter,
    LlamaCppProcessConfig,
    LlamaCppProcessConfigError,
    LlamaCppServerHTTPError,
    LlamaCppServerResponseError,
    LlamaCppServerUnreachableError,
)
from engine.cli import build_session


@contextmanager
def raises(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} was not raised")


# ------------------------------------------------------------- fake server

class _Script:
    """Mutable per-test response script, read by the handler below."""
    kind = "json"          # "json" | "raw" | "hang"
    status = 200
    body = {"content": '{"narrative": "ok"}'}
    raw_body = "not json"
    hang_seconds = 1.0
    received: list[dict] = []


class _FakeLlamaServerHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # keep test output quiet

    def do_POST(self):
        import time
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            parsed_body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed_body = None
        _Script.received.append({"path": self.path, "body": parsed_body})

        if _Script.kind == "hang":
            time.sleep(_Script.hang_seconds)

        if _Script.kind == "raw":
            payload = _Script.raw_body.encode("utf-8")
        else:
            payload = json.dumps(_Script.body).encode("utf-8")
        self.send_response(_Script.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            # The adapter timeout test intentionally closes the socket before
            # the scripted server responds. This is an expected test condition.
            pass
        finally:
            self.close_connection = True


@contextmanager
def _fake_server():
    _Script.received.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLlamaServerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _closed_port_url() -> str:
    """A loopback URL with nothing listening: bind, learn the port, close it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


# ------------------------------------------------------------- adapter shape

def test_process_adapter_implements_ai_adapter():
    assert issubclass(LlamaCppProcessAdapter, AIAdapter)


# ----------------------------------------------------------------- config

def test_empty_server_url_rejected():
    with raises(LlamaCppProcessConfigError):
        LlamaCppProcessConfig(server_url="")


def test_non_http_server_url_rejected():
    with raises(LlamaCppProcessConfigError):
        LlamaCppProcessConfig(server_url="ftp://127.0.0.1:8080")


def test_remote_server_url_rejected():
    for url in ("http://example.com:8080", "https://8.8.8.8:8080"):
        with raises(LlamaCppProcessConfigError):
            LlamaCppProcessConfig(server_url=url)


def test_loopback_server_url_allowed():
    for url in ("http://127.0.0.1:8080", "http://localhost:8080"):
        assert LlamaCppProcessConfig(server_url=url).server_url == url


def test_server_url_credentials_rejected():
    with raises(LlamaCppProcessConfigError):
        LlamaCppProcessConfig(server_url="http://user:secret@127.0.0.1:8080")


def test_non_positive_timeout_rejected():
    with raises(LlamaCppProcessConfigError):
        LlamaCppProcessConfig(server_url="http://127.0.0.1:8080", timeout=0)


# -------------------------------------------------------- valid round trip

def test_valid_server_response_becomes_structured_response():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": (
            '{"narrative": "A door creaks open.", '
            '"state_changes": [{"type": "inventory", "target": "key", '
            '"operation": "take", "value": "player"}]}'
        )}
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        resp = adapter.generate("PLAYER ACTION: search the drawer")
        assert resp.narrative == "A door creaks open."
        assert resp.state_changes[0].target == "key"


def test_fenced_model_output_is_stripped_and_parsed():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": '```json\n{"narrative": "Fenced."}\n```'}
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        resp = adapter.generate("PLAYER ACTION: look")
        assert resp.narrative == "Fenced."


def test_correct_request_sent_to_configured_endpoint():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": '{"narrative": "ok"}'}
        cfg = LlamaCppProcessConfig(server_url=url, max_tokens=77,
                                    temperature=0.33, stop=["END"])
        adapter = LlamaCppProcessAdapter(cfg)
        adapter.generate("PLAYER ACTION: look")
        assert len(_Script.received) == 1
        req = _Script.received[0]
        assert req["path"] == "/completion"
        assert req["body"]["n_predict"] == 77
        assert req["body"]["temperature"] == 0.33
        assert req["body"]["stop"] == ["END"]


def test_context_reaches_server_in_the_prompt():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": '{"narrative": "ok"}'}
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        adapter.generate("PLAYER ACTION: search the ancient chest")
        assert "search the ancient chest" in _Script.received[0]["body"]["prompt"]


def test_stop_omitted_from_request_when_not_configured():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": '{"narrative": "ok"}'}
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        adapter.generate("PLAYER ACTION: look")
        assert "stop" not in _Script.received[0]["body"]


# -------------------------------------------------------------- failures

def test_server_unreachable_raises_typed_error():
    dead_url = _closed_port_url()
    adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=dead_url, timeout=2.0))
    with raises(LlamaCppServerUnreachableError):
        adapter.generate("PLAYER ACTION: look")


def test_request_timeout_raises_server_unreachable():
    with _fake_server() as url:
        _Script.kind, _Script.hang_seconds = "hang", 0.3
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url, timeout=0.05))
        with raises(LlamaCppServerUnreachableError):
            adapter.generate("PLAYER ACTION: look")


def test_http_error_status_raises_typed_error():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 500
        _Script.body = {"error": {"code": 500, "message": "inference failed"}}
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        with raises(LlamaCppServerHTTPError):
            adapter.generate("PLAYER ACTION: look")


def test_non_json_server_response_raises_response_error():
    with _fake_server() as url:
        _Script.kind, _Script.status = "raw", 200
        _Script.raw_body = "<html>not json at all</html>"
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        with raises(LlamaCppServerResponseError):
            adapter.generate("PLAYER ACTION: look")


def test_missing_content_field_raises_response_error():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"unexpected": "shape"}
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        with raises(LlamaCppServerResponseError):
            adapter.generate("PLAYER ACTION: look")


def test_malformed_model_json_reaches_shared_boundary_and_is_rejected():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": "I think the player finds a key."}  # not JSON at all
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        with raises(ValueError):
            adapter.generate("PLAYER ACTION: search the drawer")


def test_json_missing_required_narrative_field_rejected():
    with _fake_server() as url:
        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": '{"state_changes": []}'}  # missing 'narrative'
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        with raises(ValueError):
            adapter.generate("PLAYER ACTION: look")


# -------------------------------------------------- does not touch GameState

def test_adapter_never_mutates_state_directly_only_through_validation_gate():
    with _fake_server() as url:
        adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(server_url=url))
        session = build_session(adapter=adapter)

        _Script.kind, _Script.status = "json", 200
        _Script.body = {"content": (
            '{"narrative": "A sword materializes!", '
            '"state_changes": [{"type": "inventory", "target": "excalibur", '
            '"operation": "take", "value": "player"}]}'
        )}
        out = session.handle_input("wish for a sword")
        # 'excalibur' is not a real item in the demo world -> validation rejects it
        assert "excalibur" not in session.state.character.inventory
        assert session.last_report is not None and len(session.last_report.rejected) == 1
        assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())

        _Script.body = {"content": '{"narrative": "Nothing happens."}'}
        hp_before = session.state.character.hp
        session.handle_input("do nothing")
        assert session.state.character.hp == hp_before  # narration-only, no mutation


def test_process_adapter_has_no_state_or_apply_or_persistence_attributes():
    forbidden = {"apply_effects", "validate_effect", "validate_effects",
                 "save_session", "load_session", "mutate_state", "state"}
    present = forbidden & set(dir(LlamaCppProcessAdapter))
    assert not present, f"LlamaCppProcessAdapter must not define: {present}"
