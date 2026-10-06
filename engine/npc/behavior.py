"""Deterministic NPC behavior context and action eligibility.

The AI may use this information to propose dialogue/actions, but this module does
not let the AI execute behavior.  It converts authoritative runtime state,
personality, goals, fears, preferences, relationships, and encounterability into
an explicit, bounded behavior context.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.core.state import GameState, NPCState
from engine.npc.encounter import EncounterResolver
from engine.scenario.registry import ScenarioRegistry


@dataclass(frozen=True)
class NPCBehaviorContext:
    npc_id: str
    can_interact: bool
    disposition: int
    personality: dict[str, int]
    active_goals: tuple[str, ...]
    fears: tuple[str, ...]
    preferences: tuple[str, ...]
    relationship_affinity: int | None
    relationship_trust: int | None
    allowed_action_types: tuple[str, ...]
    relationship_flags: tuple[str, ...]
    faction_id: str | None


class NPCBehaviorResolver:
    """Build behavior constraints; never mutates GameState."""

    def __init__(self, encounter_resolver: EncounterResolver | None = None, registry: ScenarioRegistry | None = None) -> None:
        self.encounter_resolver = encounter_resolver or EncounterResolver(registry)

    def build(self, state: GameState, npc_id: str, *, turn: int = 0) -> NPCBehaviorContext:
        npc = state.world.npcs[npc_id]
        encounter = self.encounter_resolver.check(state, npc_id, turn=turn)
        rel = state.world.get_relationship("player", npc_id)
        faction_id = None
        if self.encounter_resolver.registry is not None and self.encounter_resolver.registry.has("characters", npc_id):
            raw_faction = self.encounter_resolver.registry.require("characters", npc_id).data.get("faction_id")
            if isinstance(raw_faction, str):
                faction_id = raw_faction
        if not npc.alive:
            actions = ("observe",)
        elif not encounter.encounterable:
            actions = ("observe",)
        elif npc.disposition <= -60:
            actions = ("talk", "flee", "attack")
        elif npc.disposition < 0:
            actions = ("talk", "flee")
        else:
            actions = ("talk", "trade", "assist", "flee")
        personality = {
            name: int(getattr(npc.personality, name))
            for name in (
                "courage", "aggression", "sociability", "honesty",
                "greed", "curiosity", "loyalty", "patience",
            )
        }
        goals = tuple(g.description for g in npc.goals if g.status == "active")
        return NPCBehaviorContext(
            npc_id=npc_id,
            can_interact=encounter.encounterable,
            disposition=npc.disposition,
            personality=personality,
            active_goals=goals,
            fears=tuple(npc.fears),
            preferences=tuple(npc.preferences),
            relationship_affinity=rel.affinity if rel else None,
            relationship_trust=rel.trust if rel else None,
            allowed_action_types=actions,
            relationship_flags=tuple(sorted(rel.flags)) if rel else (),
            faction_id=faction_id,
        )
