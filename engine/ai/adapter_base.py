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

    def generate_text(self, prompt: str, *, system_instruction: str | None = None) -> str:
        """Return raw model text for non-gameplay tasks such as scenario extraction.

        Concrete providers should implement this without parsing the response as the
        gameplay StructuredResponse schema. External adapters that do not support raw
        text may keep the default and report NotImplementedError to the caller.
        """
        raise NotImplementedError("this AI adapter does not support raw text generation")
