import json
from unittest.mock import patch

from engine.ai.gemini_adapter import GeminiAdapter, GeminiProviderError


class _Resp:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.body).encode()


def _valid_body():
    payload = {
        "narrative": "You move forward.", "state_changes": [], "memory_updates": [],
        "npc_changes": [], "events_triggered": [], "available_actions": ["look"]
    }
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}], "usageMetadata": {"totalTokenCount": 12}}


def test_gemini_adapter_parses_structured_response():
    adapter = GeminiAdapter("test-key")
    with patch("urllib.request.urlopen", return_value=_Resp(_valid_body())):
        result = adapter.generate("PLAYER ACTION: look")
    assert result.narrative == "You move forward."
    assert adapter.calls == 1
    assert adapter.last_usage["totalTokenCount"] == 12


def test_gemini_adapter_provider_error_is_not_value_error():
    adapter = GeminiAdapter("test-key")
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        try:
            adapter.generate("PLAYER ACTION: look")
        except GeminiProviderError as exc:
            assert "network" in str(exc)
        else:
            raise AssertionError("expected GeminiProviderError")


def test_gemini_http_error_detail_is_bounded_and_compacted():
    import io
    from engine.ai import gemini_adapter as mod

    original = mod.urllib.request.urlopen
    def fail(*args, **kwargs):
        raise mod.urllib.error.HTTPError(
            "https://example.invalid", 500, "server", {},
            io.BytesIO(("secret\n" * 1000).encode())
        )
    mod.urllib.request.urlopen = fail
    try:
        adapter = mod.GeminiAdapter("key")
        try:
            adapter.generate("context")
        except mod.GeminiProviderError as exc:
            msg = str(exc)
            assert len(msg) < 300
            assert "\n" not in msg
        else:
            raise AssertionError("expected GeminiProviderError")
    finally:
        mod.urllib.request.urlopen = original
