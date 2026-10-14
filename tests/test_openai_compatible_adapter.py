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
