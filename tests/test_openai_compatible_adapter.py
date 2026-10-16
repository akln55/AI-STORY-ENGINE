from __future__ import annotations

from engine.ai.openai_compatible_adapter import OpenAICompatibleAdapter


def test_openai_adapter_allows_https():
    adapter = OpenAICompatibleAdapter("https://api.openai.com/v1", "key", "model")
    assert adapter.url.endswith("/v1/chat/completions")


def test_openai_adapter_allows_local_http():
    adapter = OpenAICompatibleAdapter("http://127.0.0.1:8080/v1", "key", "model")
    assert adapter.url.endswith("/v1/chat/completions")


def test_openai_adapter_rejects_remote_http():
    try:
        OpenAICompatibleAdapter("http://example.com/v1", "key", "model")
    except ValueError as exc:
        assert "localhost" in str(exc)
    else:
        raise AssertionError("expected insecure HTTP endpoint rejection")


def test_openai_adapter_rejects_embedded_credentials():
    try:
        OpenAICompatibleAdapter("https://user:pass@example.com/v1", "key", "model")
    except ValueError:
        pass
    else:
        raise AssertionError("expected endpoint credential rejection")


def test_raw_source_generation_returns_non_gameplay_json_text():
    import json
    from unittest.mock import patch

    expected = '{"entities":[],"relations":[],"unresolved":[]}'
    captured = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": expected}}],
            }).encode("utf-8")

    def open_request(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    adapter = OpenAICompatibleAdapter("https://api.example/v1", "test-key", "test-model")
    with patch("engine.ai.openai_compatible_adapter.open_url", side_effect=open_request):
        text = adapter.generate_text(
            "extract source", system_instruction="Return source extraction JSON only."
        )

    assert text == expected
    payload = captured["payload"]
    assert payload["messages"][0]["content"] == "Return source extraction JSON only."
    assert payload["messages"][1]["content"] == "extract source"
    assert payload["response_format"] == {"type": "json_object"}


def test_adapter_retries_without_json_mode_when_provider_rejects_it():
    import io
    import json
    from unittest.mock import patch
    from urllib.error import HTTPError

    expected = '{"narrative":"Works","state_changes":[],"memory_updates":[],"npc_changes":[],"events_triggered":[],"available_actions":[]}'
    calls = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": expected}}]}).encode()

    def opener(request, timeout):
        payload = json.loads(request.data.decode())
        calls.append(payload)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 400, "Bad Request", {}, io.BytesIO(
                b"response_format is not supported by this endpoint"
            ))
        return Response()

    adapter = OpenAICompatibleAdapter("https://api.example/v1", "test-key", "test-model")
    with patch("engine.ai.openai_compatible_adapter.open_url", side_effect=opener):
        text = adapter.generate_text("do work", system_instruction="Return JSON.")
    assert text == expected
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]


def test_adapter_does_not_retry_authentication_failures():
    import io
    from unittest.mock import patch
    from urllib.error import HTTPError
    from engine.ai.openai_compatible_adapter import OpenAICompatibleProviderError

    calls = []
    def opener(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b"bad key"))

    adapter = OpenAICompatibleAdapter("https://api.example/v1", "test-key", "test-model")
    with patch("engine.ai.openai_compatible_adapter.open_url", side_effect=opener):
        try:
            adapter.generate_text("do work")
        except OpenAICompatibleProviderError as exc:
            assert "HTTP 401" in str(exc)
        else:
            raise AssertionError("expected authentication error")
    assert len(calls) == 1

def test_adapter_reports_non_object_json_as_provider_error():
    from unittest.mock import patch
    from engine.ai.openai_compatible_adapter import OpenAICompatibleProviderError

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b"[]"

    adapter = OpenAICompatibleAdapter("https://api.example/v1", "test-key", "test-model")
    with patch("engine.ai.openai_compatible_adapter.open_url", return_value=Response()):
        try:
            adapter.generate_text("do work")
        except OpenAICompatibleProviderError as exc:
            assert "invalid API response envelope" in str(exc)
        else:
            raise AssertionError("expected malformed response envelope error")
