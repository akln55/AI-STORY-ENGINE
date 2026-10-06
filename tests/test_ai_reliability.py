from engine.ai.fake import FakeAdapter
from engine.ai.reliability import (
    AICapabilities, AIProviderError, FallbackAIAdapter, HealthTrackingAIAdapter,
)
from engine.ai.schema import StructuredResponse


def _ok():
    return {"narrative":"ok", "state_changes":[], "memory_updates":[], "npc_changes":[], "events_triggered":[], "available_actions":[]}


def test_health_tracks_success_and_latency():
    adapter = HealthTrackingAIAdapter(FakeAdapter({"": _ok()}))
    result = adapter.generate("ctx")
    assert result.narrative == "ok"
    health = adapter.health()
    assert (health.calls, health.successes, health.provider_failures) == (1, 1, 0)
    assert health.last_latency_ms is not None
    assert health.consecutive_provider_failures == 0


def test_health_distinguishes_malformed_from_provider_failure():
    class Bad:
        def __init__(self, exc): self.exc = exc
        def generate(self, context): raise self.exc
    malformed = HealthTrackingAIAdapter(Bad(ValueError("bad json")))
    try: malformed.generate("ctx")
    except ValueError: pass
    assert malformed.health().malformed_responses == 1
    provider = HealthTrackingAIAdapter(Bad(AIProviderError("offline")))
    try: provider.generate("ctx")
    except AIProviderError: pass
    h = provider.health()
    assert h.provider_failures == 1
    assert h.malformed_responses == 0


def test_fallback_only_handles_provider_errors():
    class Primary:
        def __init__(self, exc): self.exc = exc
        def generate(self, context): raise self.exc
    fallback = FakeAdapter({"": _ok()})
    wrapped = FallbackAIAdapter(Primary(AIProviderError("offline")), fallback)
    assert wrapped.generate("ctx").narrative == "ok"
    assert wrapped.using_fallback is True

    malformed = FallbackAIAdapter(Primary(ValueError("bad")), FakeAdapter({"": _ok()}))
    try: malformed.generate("ctx")
    except ValueError: pass
    else: raise AssertionError("ValueError must not trigger fallback")


def test_capabilities_contract_is_plain_data():
    caps = AICapabilities(structured_json=True, local=True, max_context_chars=1000)
    assert caps.structured_json and caps.local and caps.max_context_chars == 1000


def test_timed_generate_does_not_misclassify_unexpected_errors():
    from engine.ai.reliability import timed_generate
    seen = []
    class Broken:
        def generate(self, context):
            raise RuntimeError("programming bug")
    try:
        timed_generate(Broken(), "ctx", on_provider_failure=lambda exc, ms: seen.append(type(exc)))
    except RuntimeError:
        pass
    else:
        raise AssertionError("unexpected error must propagate")
    assert seen == []
