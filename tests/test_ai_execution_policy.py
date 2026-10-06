from __future__ import annotations

from engine.ai.schema import StructuredResponse
from engine.core.game import GameSession, MAX_AI_CALLS_PER_PLAYER_ACTION


class CountingAdapter:
    def __init__(self, response: StructuredResponse):
        self.response = response
        self.calls = 0

    def generate(self, context: str) -> StructuredResponse:
        self.calls += 1
        return self.response


def _session(adapter):
    from engine.demo import build_demo_state
    return GameSession(build_demo_state(), adapter=adapter)


def test_one_player_action_gets_one_ai_transaction():
    adapter = CountingAdapter(StructuredResponse(narrative="ok"))
    session = _session(adapter)
    session.handle_input("search the room")
    assert adapter.calls == 1


def test_same_player_action_is_not_automatically_repeated():
    adapter = CountingAdapter(StructuredResponse(narrative="ok"))
    session = _session(adapter)
    session.handle_input("search the room")
    assert adapter.calls == 1
    # A second call only occurs because the player explicitly submits a second
    # action; the engine never loops on its own after the first response.
    session.handle_input("search the room")
    assert adapter.calls == 2


def test_reentrant_ai_call_is_blocked_without_extra_provider_call():
    class ReentrantAdapter(CountingAdapter):
        def __init__(self):
            super().__init__(StructuredResponse(narrative="outer"))
            self.session = None

        def generate(self, context: str) -> StructuredResponse:
            self.calls += 1
            self.session._handle_ai(self.session.parser_intent("inner"))
            return self.response

    # Use the public parser rather than exposing a second execution path.
    from engine.parser.intents import parse_input
    adapter = ReentrantAdapter()
    session = _session(adapter)
    adapter.session = session
    adapter.session.parser_intent = parse_input
    session.handle_input("search the room")
    assert adapter.calls == 1


def test_retry_budget_is_hard_capped():
    assert MAX_AI_CALLS_PER_PLAYER_ACTION == 2


def test_generate_with_retry_caps_even_if_caller_requests_more():
    class MalformedAdapter:
        def __init__(self):
            self.calls = 0

        def generate(self, context):
            self.calls += 1
            raise ValueError("bad json")

    from engine.core.game import AIResponseExhaustedError
    adapter = MalformedAdapter()
    session = _session(adapter)
    try:
        session._generate_with_retry("context", attempts=99)
    except AIResponseExhaustedError:
        pass
    else:
        raise AssertionError("expected AIResponseExhaustedError")
    assert adapter.calls == MAX_AI_CALLS_PER_PLAYER_ACTION
