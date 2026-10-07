"""LlamaCppProcessAdapter: Android-primary AIAdapter backend over a local
`llama-server` process, reached via localhost HTTP.

Per the durable architecture decisions recorded in docs/PROJECT_HISTORY.md: the Android/Termux target uses a native
`llama-server` process instead of embedding `llama-cpp-python` into the
Python engine, because upstream llama.cpp ships official prebuilt Android
arm64 binaries while `llama-cpp-python` does not document or reliably
support Termux. `LlamaCppAdapter` (llama-cpp-python) is retained unchanged as
the desktop/development backend; this module is a second, independent
`AIAdapter` implementation for the same provider family.

Responsibility boundary is identical to LlamaCppAdapter's:

    GameSession -> AIAdapter -> LlamaCppProcessAdapter -> localhost HTTP
        -> llama-server -> raw text -> parse_structured_response_json()
        -> StructuredResponse
        -> (back in GameSession) effect conversion -> validation gate -> GameState

This module turns an assembled context string into a StructuredResponse and
does nothing else. It never touches GameState, never applies Effects, never
runs RPG rules, never writes persistence, and does not launch or manage the
`llama-server` process -- it assumes one is already running at the
configured URL (process lifecycle is a separate, later concern per ADR-0008).

Stdlib-only by design (CONVENTIONS §4, Android/Termux constraint in this
task's brief): uses `urllib.request`/`urllib.error`/`json`, no `requests` or
other third-party HTTP dependency, so this module never adds a native
dependency to the Python project the way `llama-cpp-python` does.

Talks to llama-server's native `POST /completion` endpoint (not the
OpenAI-compatible chat route): it takes a single prompt string and returns
`{"content": "...", ...}`, matching the single assembled-string prompt
`engine/ai/context.py` already produces -- no chat-message reshaping needed.
Verified against the current upstream `tools/server/README.md` docs before
implementing (not guessed).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from engine.ai.adapter_base import AIAdapter
from engine.ai.reliability import AIProviderError, AICapabilities
from engine.ai.llama_cpp_adapter import _strip_code_fence  # shared model-output
                                                             # quirk, not duplicated
from engine.ai.schema import StructuredResponse, parse_structured_response_json


def _safe_provider_detail(text: str, limit: int = 240) -> str:
    """Bound provider diagnostics so server payloads cannot flood logs/UI."""
    compact = " ".join(str(text).replace("\n", " ").split())
    return compact[:limit]


# --------------------------------------------------------------- exceptions

class LlamaCppProcessError(AIProviderError):
    """Base class for every LlamaCppProcessAdapter provider-specific failure.

    Deliberately NOT a subclass of ValueError, for the same reason as
    LlamaCppError in llama_cpp_adapter.py: ValueError is reserved for
    "this is malformed structured output", which GameSession's existing
    retry hook already catches. A provider/transport failure is a different
    kind of problem and must stay distinguishable from it (this task's
    "keep malformed structured output distinguishable from infrastructure/
    provider failure" requirement) -- retry-with-feedback itself is not
    implemented here.
    """


class LlamaCppProcessConfigError(LlamaCppProcessError):
    """Raised for invalid adapter configuration (e.g. no server_url)."""


class LlamaCppServerUnreachableError(LlamaCppProcessError):
    """Raised when the configured llama-server cannot be reached at all:
    connection refused, DNS failure, or the request timed out. Typically
    means the server process isn't running."""


class LlamaCppServerHTTPError(LlamaCppProcessError):
    """Raised when llama-server responded but with a non-2xx status. This is
    also how llama-server itself reports an inference/provider-side failure
    (its error responses are non-2xx with a JSON error body), so a distinct
    "inference failure" type is not needed on top of this one."""


class LlamaCppServerResponseError(LlamaCppProcessError):
    """Raised when llama-server's response body isn't valid JSON, or is
    valid JSON but missing the expected `content` field. This is about the
    HTTP envelope shape, not the model's generated text -- the text itself
    (once extracted) still goes through parse_structured_response_json and
    raises ValueError there if malformed, unchanged from LlamaCppAdapter."""


# ----------------------------------------------------------------- config

@dataclass
class LlamaCppProcessConfig:
    """Explicit runtime configuration for LlamaCppProcessAdapter.

    No field points at a specific model or GGUF filename -- that is entirely
    the already-running server's concern, not this adapter's. `server_url`
    defaults to the conventional llama-server loopback address (localhost
    only; this adapter is not meant to reach a remote or public server).
    """

    server_url: str = "http://127.0.0.1:8080"
    timeout: float = 30.0          # seconds, per HTTP request
    max_tokens: int = 512          # -> llama-server's `n_predict`
    temperature: float = 0.7
    stop: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.server_url:
            raise LlamaCppProcessConfigError(
                "LlamaCppProcessConfig.server_url must be set")
        if not self.server_url.startswith(("http://", "https://")):
            raise LlamaCppProcessConfigError(
                f"server_url must be an http(s) URL, got {self.server_url!r}")
        parsed = urllib.parse.urlparse(self.server_url)
        if parsed.username or parsed.password:
            raise LlamaCppProcessConfigError("server_url must not contain credentials")
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise LlamaCppProcessConfigError(
                "server_url must target the local llama-server loopback host")
        if parsed.port is not None and not 1024 <= parsed.port <= 65535:
            raise LlamaCppProcessConfigError("server_url port must be in the unprivileged range")
        if self.timeout <= 0:
            raise LlamaCppProcessConfigError("timeout must be positive")


# ----------------------------------------------------------------- adapter

class LlamaCppProcessAdapter(AIAdapter):
    """AIAdapter backend that talks to an already-running local llama-server
    over HTTP. Does not launch, stop, or manage that process."""

    def __init__(self, config: LlamaCppProcessConfig):
        self.config = config
        self._endpoint = config.server_url.rstrip("/") + "/completion"

    # --------------------------------------------------------- AIAdapter

    @property
    def capabilities(self) -> AICapabilities:
        return AICapabilities(structured_json=True, streaming=False, cancellation=False, local=True)

    def generate(self, context: str) -> StructuredResponse:
        """Assembled context in -> StructuredResponse out. See module
        docstring for the full request/response boundary."""
        prompt = self._build_prompt(context)
        envelope = self._call_server(prompt)
        text = self._extract_text(envelope)
        text = _strip_code_fence(text)
        return parse_structured_response_json(text)

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _build_prompt(context: str) -> str:
        """Same instruction LlamaCppAdapter appends -- the context itself
        (system+rules+state+recent+action) comes from engine/ai/context.py,
        unmodified by this adapter."""
        return (
            context
            + "\n\nRespond with ONLY a single JSON object matching the "
              "structured response contract above. No prose, no markdown "
              "code fences, no commentary before or after the JSON."
        )

    def _call_server(self, prompt: str) -> dict:
        body = {
            "prompt": prompt,
            "n_predict": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }
        if self.config.stop:
            body["stop"] = self.config.stop
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint, data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            raise LlamaCppServerHTTPError(
                f"llama-server returned HTTP {err.code}: {_safe_provider_detail(detail)}"
            ) from err
        except urllib.error.URLError as err:
            raise LlamaCppServerUnreachableError(
                f"could not reach llama-server: {_safe_provider_detail(err.reason)}"
            ) from err
        except OSError as err:  # e.g. socket.timeout on some platforms/py versions
            raise LlamaCppServerUnreachableError(
                f"could not reach llama-server: {_safe_provider_detail(err)}"
            ) from err

        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise LlamaCppServerResponseError(
                f"llama-server response was not valid JSON: {_safe_provider_detail(err)}"
            ) from err

    @staticmethod
    def _extract_text(envelope: dict) -> str:
        if not isinstance(envelope, dict) or not isinstance(envelope.get("content"), str):
            raise LlamaCppServerResponseError(
                "unexpected llama-server response shape")
        return envelope["content"]
