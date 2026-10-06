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
