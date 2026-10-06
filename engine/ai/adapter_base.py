"""AI adapter interface (ADR-0003): the engine talks only to this.

An adapter receives the assembled context string and returns a
StructuredResponse. Adapters have NO write path to game state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.ai.schema import StructuredResponse


class AIAdapter(ABC):
    @abstractmethod
    def generate(self, context: str) -> StructuredResponse:
        """Produce a structured response for the assembled context."""
