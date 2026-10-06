"""Production AI reliability primitives.

Provider failures are observable, bounded, and distinguishable from malformed
model output.  Fallback is allowed only for provider/transport failures; a
malformed structured response remains a contract failure and is retried by
GameSession under its existing one-action retry budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from engine.ai.adapter_base import AIAdapter
from engine.ai.schema import StructuredResponse


@dataclass(frozen=True)
class AICapabilities:
    structured_json: bool = True
    streaming: bool = False
    cancellation: bool = False
    local: bool = False
    max_context_chars: int | None = None


@dataclass(frozen=True)
class AIHealthSnapshot:
    calls: int
    successes: int
    provider_failures: int
    malformed_responses: int
    consecutive_provider_failures: int
    last_latency_ms: float | None
    last_error: str | None


class AIProviderError(RuntimeError):
    """Base class for provider/transport/runtime failures.

    This is deliberately distinct from ValueError, which means malformed
    structured model output and provider failure can never be confused by the
    engine retry policy.
    """


class HealthTrackingAIAdapter(AIAdapter):
    """Bounded operational metrics wrapper around any AIAdapter."""

    def __init__(self, inner: AIAdapter):
        self.inner = inner
        self.calls = 0
        self.successes = 0
        self.provider_failures = 0
        self.malformed_responses = 0
        self.consecutive_provider_failures = 0
        self.last_latency_ms = None
        self.last_error = None

    @property
    def capabilities(self):
        return getattr(self.inner, "capabilities", None)

    def health(self) -> AIHealthSnapshot:
        return AIHealthSnapshot(self.calls, self.successes, self.provider_failures,
            self.malformed_responses, self.consecutive_provider_failures,
            self.last_latency_ms, self.last_error)

    def generate(self, context: str) -> StructuredResponse:
        self.calls += 1
        started = monotonic()
        try:
            result = self.inner.generate(context)
        except ValueError as exc:
            self.malformed_responses += 1
            self.last_latency_ms = (monotonic() - started) * 1000.0
            self.last_error = str(exc)[:240]
            raise
        except AIProviderError as exc:
            self.provider_failures += 1
            self.consecutive_provider_failures += 1
            self.last_latency_ms = (monotonic() - started) * 1000.0
            self.last_error = str(exc)[:240]
            raise
        else:
            self.successes += 1
            self.consecutive_provider_failures = 0
            self.last_latency_ms = (monotonic() - started) * 1000.0
            self.last_error = None
            return result


class FallbackAIAdapter(AIAdapter):
    """Primary/secondary adapter with deterministic failure semantics.

    Only AIProviderError triggers fallback. ValueError is propagated so the
    GameSession's bounded structured-output retry remains authoritative.
    """

    def __init__(self, primary: AIAdapter, fallback: AIAdapter):
        if primary is fallback:
            raise ValueError("primary and fallback adapters must differ")
        self.primary = primary
        self.fallback = fallback
        self._using_fallback = False

    @property
    def using_fallback(self) -> bool:
        return self._using_fallback

    def generate(self, context: str) -> StructuredResponse:
        try:
            response = self.primary.generate(context)
            self._using_fallback = False
            return response
        except AIProviderError:
            self._using_fallback = True
            return self.fallback.generate(context)


def timed_generate(
    adapter: AIAdapter,
    context: str,
    on_success: Callable[[float], None] | None = None,
    on_provider_failure: Callable[[Exception, float], None] | None = None,
) -> StructuredResponse:
    """Run an adapter call while measuring elapsed wall time.

    This helper intentionally does not retry, mutate state, or catch
    ValueError.  Policy belongs to GameSession/FallbackAIAdapter.
    """
    started = monotonic()
    try:
        result = adapter.generate(context)
    except AIProviderError as exc:
        elapsed = (monotonic() - started) * 1000.0
        if on_provider_failure is not None:
            on_provider_failure(exc, elapsed)
        raise
    elapsed = (monotonic() - started) * 1000.0
    if on_success is not None:
        on_success(elapsed)
    return result
