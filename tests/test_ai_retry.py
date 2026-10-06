"""Tests for GameSession's bounded retry-with-feedback (ADR-0009).

Exercises engine/core/game.py's _generate_with_retry / _handle_ai using
scripted FakeAdapter sequences (see engine/ai/fake.py docstring) and the
already-existing typed provider errors from both llama.cpp adapters, to
prove they propagate uncaught rather than being treated as retryable
malformed output. No real LLM, mock library, or network is used anywhere.
"""

from __future__ import annotations

from contextlib import contextmanager

from engine.ai.fake import FakeAdapter
from engine.ai.llama_cpp_adapter import LlamaCppInferenceError
from engine.ai.llama_cpp_process_adapter import LlamaCppServerUnreachableError
from engine.cli import build_session
from engine.core.game import MAX_AI_RETRY_ATTEMPTS, AIResponseExhaustedError


@contextmanager
def raises(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} was not raised")


# Deliberately missing 'narrative' -> parse_structured_response raises
# ValueError, exactly like real malformed model output.
_MALFORMED = {"state_changes": []}
_MALFORMED_BAD_TYPE = {"narrative": "ok", "state_changes": "not-a-list"}


# --------------------------------------------------------- happy path / bound

def test_first_response_malformed_second_valid_turn_succeeds():
    fake = FakeAdapter(handlers={
        "sing": [_MALFORMED, {"narrative": "Your song echoes beautifully."}],
    })
    s = build_session(adapter=fake)
    out = s.handle_input("sing a song")
    assert out == "Your song echoes beautifully."
    assert len(fake.calls) == 2  # exactly one retry, not more


def test_valid_first_response_performs_exactly_one_ai_call():
    fake = FakeAdapter(handlers={"sing": {"narrative": "A pleasant tune."}})
    s = build_session(adapter=fake)
    s.handle_input("sing a song")
    assert len(fake.calls) == 1


def test_retry_count_is_bounded_never_exceeds_configured_maximum():
    # Every attempt malformed: adapter.generate() must be called exactly
    # MAX_AI_RETRY_ATTEMPTS times, never more, regardless of how long the
    # script is.
    fake = FakeAdapter(handlers={
        "sing": [_MALFORMED, _MALFORMED, _MALFORMED, _MALFORMED],
    })
    s = build_session(adapter=fake)
    s.handle_input("sing a song")
    assert len(fake.calls) == MAX_AI_RETRY_ATTEMPTS


def test_both_attempts_malformed_controlled_failure_no_mutation():
    fake = FakeAdapter(handlers={"sing": [_MALFORMED, _MALFORMED_BAD_TYPE]})
    s = build_session(adapter=fake)
    snapshot = (s.state.character.hp, s.state.character.stamina,
                s.state.character.location_id, list(s.state.character.inventory))
    out = s.handle_input("sing a song")
    assert (s.state.character.hp, s.state.character.stamina,
            s.state.character.location_id, list(s.state.character.inventory)) == snapshot
    assert s.last_report is None  # no validation ever ran -- nothing to apply
    assert out  # a clean player-facing message, not an exception/crash
    assert len(fake.calls) == MAX_AI_RETRY_ATTEMPTS


def test_generate_with_retry_raises_exhausted_error_directly():
    fake = FakeAdapter(handlers={"sing": [_MALFORMED, _MALFORMED]})
    s = build_session(adapter=fake)
    with raises(AIResponseExhaustedError):
        s._generate_with_retry("PLAYER ACTION: sing a song")


# ------------------------------------------------------- error classification

def test_invalid_json_shape_triggers_retry():
    """A payload FakeAdapter itself fails to parse (missing required field)
    is exactly what parse_structured_response raises ValueError for --
    schema-equivalent to invalid JSON reaching parse_structured_response_json
    in the real adapters."""
    fake = FakeAdapter(handlers={"sing": [_MALFORMED, {"narrative": "Fixed."}]})
    s = build_session(adapter=fake)
    out = s.handle_input("sing a song")
    assert out == "Fixed."
    assert len(fake.calls) == 2


def test_schema_type_validation_failure_triggers_retry():
    fake = FakeAdapter(handlers={"sing": [_MALFORMED_BAD_TYPE, {"narrative": "Fixed."}]})
    s = build_session(adapter=fake)
    out = s.handle_input("sing a song")
    assert out == "Fixed."
    assert len(fake.calls) == 2


def test_provider_failure_is_not_treated_as_malformed_output_retry():
    """A non-ValueError provider error must propagate immediately -- exactly
    one adapter call, no retry, no AIResponseExhaustedError."""
    fake = FakeAdapter(handlers={
        "sing": [LlamaCppInferenceError("model crashed"), {"narrative": "unreachable"}],
    })
    s = build_session(adapter=fake)
    with raises(LlamaCppInferenceError):
        s.handle_input("sing a song")
    assert len(fake.calls) == 1  # did not retry into the second scripted step


def test_server_unreachable_does_not_enter_feedback_loop():
    fake = FakeAdapter(handlers={
        "sing": [LlamaCppServerUnreachableError("connection refused"),
                 {"narrative": "unreachable"}],
    })
    s = build_session(adapter=fake)
    with raises(LlamaCppServerUnreachableError):
        s.handle_input("sing a song")
    assert len(fake.calls) == 1


def test_provider_error_propagates_with_original_message_intact():
    fake = FakeAdapter(handlers={"sing": [LlamaCppInferenceError("boom: bad shape")]})
    s = build_session(adapter=fake)
    try:
        s.handle_input("sing a song")
        raise AssertionError("expected LlamaCppInferenceError")
    except LlamaCppInferenceError as err:
        assert "boom: bad shape" in str(err)


# ------------------------------------------------------------- feedback shape

def test_retry_feedback_is_informative_but_safe():
    s = build_session()  # no adapter needed; testing the static helper directly
    err = ValueError("missing required field: narrative")
    feedback = s._retry_feedback("PLAYER ACTION: sing", err)
    assert "missing required field: narrative" in feedback
    assert "ONLY valid JSON" in feedback
    assert "Markdown" in feedback
    assert "Traceback" not in feedback
    assert "File \"" not in feedback  # no stack-trace-style frame lines


def test_retry_feedback_never_permanently_enters_recent_turns():
    fake = FakeAdapter(handlers={"sing": [_MALFORMED, {"narrative": "Fixed."}]})
    s = build_session(adapter=fake)
    s.handle_input("sing a song")
    joined = "\n".join(s.recent_turns)
    assert "SYSTEM NOTE" not in joined
    assert "Validation error" not in joined
    assert "missing required field" not in joined


# ------------------------------------------------------------- one turn only

def test_player_action_remains_exactly_one_turn_despite_retries():
    fake = FakeAdapter(handlers={"go forest": [_MALFORMED, {"narrative": "You arrive."}]})
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    player_lines = [t for t in s.recent_turns if "player: go forest" in t]
    assert len(player_lines) == 1


def test_player_action_remains_one_turn_even_when_exhausted():
    fake = FakeAdapter(handlers={"go forest": [_MALFORMED, _MALFORMED]})
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    player_lines = [t for t in s.recent_turns if "player: go forest" in t]
    assert len(player_lines) == 1


# ------------------------------------------------------- deterministic path

def test_deterministic_commands_never_invoke_retry_machinery():
    fake = FakeAdapter()
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    s.handle_input("take mushroom")
    assert fake.calls == []


# --------------------------------------------- adapter-agnostic (no branching)

def test_retry_mechanism_is_identical_across_adapter_types():
    """GameSession must not special-case adapter identity: the same
    _generate_with_retry code path handles FakeAdapter, LlamaCppAdapter, and
    LlamaCppProcessAdapter purely through the AIAdapter interface and
    exception types -- proven here by asserting no adapter-type checks exist
    in the retry method's own behaviour (already exercised against
    FakeAdapter above; llama_cpp_adapter/llama_cpp_process_adapter tests
    separately prove those two raise the same ValueError/non-ValueError
    shapes this method depends on)."""
    import inspect

    from engine.core.game import GameSession
    src = inspect.getsource(GameSession._generate_with_retry)
    assert "isinstance" not in src
