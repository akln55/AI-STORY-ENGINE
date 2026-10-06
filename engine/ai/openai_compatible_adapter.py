"""OpenAI-compatible JSON chat-completions adapter.

This adapter is deliberately provider-neutral. It supports endpoints that expose
an OpenAI-style POST /chat/completions contract while preserving the engine's
single AIAdapter boundary and structured-response validation.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from engine.ai.adapter_base import AIAdapter
from engine.ai.reliability import AIProviderError, AICapabilities
from engine.ai.schema import StructuredResponse, parse_structured_response_json


class OpenAICompatibleProviderError(AIProviderError):
    """Transport/provider failure for an OpenAI-compatible endpoint."""


def _safe_detail(text: str, limit: int = 240) -> str:
    return " ".join(text.replace("\n", " ").split())[:limit]


class OpenAICompatibleAdapter(AIAdapter):
    """Call an OpenAI-compatible chat-completions endpoint."""

    def __init__(self, endpoint: str, api_key: str, model: str, timeout: float = 45.0):
        endpoint = endpoint.strip().rstrip("/")
        if not endpoint:
            raise ValueError("API endpoint is required")
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.scheme not in {"https", "http"}:
            raise ValueError("API endpoint must use https:// (localhost may use http://)")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("API endpoint must not contain credentials or fragments")
        hostname = (parsed.hostname or "").lower()
        local_hosts = {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme == "http" and hostname not in local_hosts:
            raise ValueError("insecure HTTP endpoints are only allowed for localhost")
        if endpoint.endswith("/chat/completions"):
            self.url = endpoint
        else:
            self.url = endpoint + "/chat/completions"
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = float(timeout)
        if not self.api_key:
            raise ValueError("API key is required")
        if not self.model:
            raise ValueError("API model is required")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    @property
    def capabilities(self) -> AICapabilities:
        return AICapabilities(structured_json=True, streaming=False, cancellation=False, local=False)

    def generate(self, context: str) -> StructuredResponse:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the narration component of a deterministic RPG engine. "
                        "The engine is authoritative. Return exactly one JSON object "
                        "matching the supplied structured response contract."
                    ),
                },
                {"role": "user", "content": context},
            ],
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAICompatibleProviderError(
                f"API HTTP {exc.code}: {_safe_detail(detail)}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OpenAICompatibleProviderError(
                f"API network error: {_safe_detail(str(exc))}"
            ) from exc

        try:
            body = json.loads(raw)
            choices = body.get("choices", [])
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                content = "".join(
                    item.get("text", "") for item in content if isinstance(item, dict)
                )
            if not content:
                raise OpenAICompatibleProviderError("API returned an empty response")
        except OpenAICompatibleProviderError:
            raise
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise OpenAICompatibleProviderError(
                f"invalid API response envelope: {_safe_detail(str(exc))}"
            ) from exc

        return parse_structured_response_json(str(content))
