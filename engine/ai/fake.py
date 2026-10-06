"""Scripted fake AI adapter for deterministic tests (CONVENTIONS §4).

No network, no model, no cost. The adapter matches the assembled context
against scripted handlers (substring match on the player action line) or
returns a harmless default. Tests use this to prove that:
  - AI proposals pass the validation gate like everything else (ADR-0001),
  - narrative never changes state, even if it claims to,
  - GameSession's bounded retry-with-feedback works (ADR-0009).

A handler value is either:
  - a single response dict (original behaviour, unchanged): every matching
    call returns the same parsed StructuredResponse (or raises ValueError,
    if the dict is itself malformed -- useful for a single-shot invalid
    response test).
  - a list of "script steps", consumed one per call to the SAME matching
    action (advancing per handler, not per adapter): each step is either a
    response dict, or an Exception *instance* to raise as-is (e.g. a
    provider error like LlamaCppServerUnreachableError("..."), to test that
    non-ValueError failures are not treated as retryable malformed output).
    Once the list is exhausted, the last step repeats. This is what makes
    "first response malformed, second valid" retry tests possible without
    a real/mocked LLM.
"""

from __future__ import annotations

from collections.abc import Callable

from engine.ai.adapter_base import AIAdapter
from engine.ai.schema import StructuredResponse, parse_structured_response


class FakeAdapter(AIAdapter):
    def __init__(
        self,
        handlers: dict[str, dict | list] | None = None,
        default_narrative: str = "Nothing unusual happens.",
    ):
        # handlers: {"<substring of player action>": <raw response dict>
        #            | [<raw response dict or Exception instance>, ...]}
        self._handlers = handlers or {}
        self._default_narrative = default_narrative
        self.calls: list[str] = []  # record of contexts, for assertions
        self._step_index: dict[str, int] = {}  # per-handler-key call count

    def generate(self, context: str) -> StructuredResponse:
        self.calls.append(context)
        action_line = _extract_action_line(context)
        for needle, scripted in self._handlers.items():
            if needle.lower() in action_line.lower():
                step = self._next_step(needle, scripted)
                if isinstance(step, BaseException):
                    raise step
                return parse_structured_response(step)
        return StructuredResponse(narrative=self._default_narrative)

    def _next_step(self, needle: str, scripted: dict | list):
        if not isinstance(scripted, list):
            return scripted  # single-payload handler: same response every call
        idx = self._step_index.get(needle, 0)
        self._step_index[needle] = idx + 1
        return scripted[min(idx, len(scripted) - 1)]  # repeat last once exhausted


def _extract_action_line(context: str) -> str:
    marker = "PLAYER ACTION:"
    if marker in context:
        return context.split(marker, 1)[1].strip().splitlines()[0]
    return ""
