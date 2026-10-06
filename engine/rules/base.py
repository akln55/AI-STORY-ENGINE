"""Rule interfaces: deterministic, engine-owned game rules (ADR-0001)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.core.state import GameState

RESOURCE = "resource"
INVENTORY = "inventory"
LOCATION = "location"
NPC_FLAG = "npc"
RELATIONSHIP = "relationship"
REPUTATION = "reputation"
EVENT = "event"
PROGRESSION = "progression"
STATUS = "status"
QUEST = "quest"

_ALLOWED_OPS = {
    RESOURCE: {"add", "set"},
    INVENTORY: {"take", "drop"},
    LOCATION: {"move"},
    NPC_FLAG: {"set"},
    RELATIONSHIP: {"set", "add", "flag_add", "flag_remove"},
    REPUTATION: {"set", "add"},
    EVENT: {"trigger", "resolve", "fail", "cancel"},
    PROGRESSION: {"xp"},
    STATUS: {"add", "remove", "tick"},
    QUEST: {"activate", "abandon"},
}


@dataclass
class Effect:
    """A proposed state change, from a rule OR from the AI adapter.

    `target` meaning depends on kind:
      resource      -> "player" or npc id (optionally .field)
      inventory     -> item id
      location      -> "player" or npc id
      npc           -> npc id
      relationship  -> "party_a|party_b" canonical or "a:b"
    """

    kind: str
    target: str
    operation: str
    value: object
    reason: str = ""

    def allowed(self) -> bool:
        return self.operation in _ALLOWED_OPS.get(self.kind, set())


@dataclass
class RuleResult:
    effects: list[Effect]
    narration_hint: str = ""


class Rule(Protocol):
    name: str

    def resolve(self, intent: "Intent", state: GameState) -> RuleResult | None: ...


from engine.parser.intents import Intent  # noqa: E402
