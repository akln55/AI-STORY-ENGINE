"""Game time / turn counter (authoritative, per ARCHITECTURE.md §2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameClock:
    turn: int = 0

    def advance(self) -> int:
        self.turn += 1
        return self.turn
