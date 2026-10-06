"""Deterministic dialogue targeting and prompt context.

Dialogue is an AI-assisted interaction, but access to an NPC is still owned by
engine state.  The AI may narrate and propose validated relationship/NPC effects;
it cannot bypass encounter conditions or invent canonical character facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.core.state import GameState, NPCState
from engine.npc.behavior import NPCBehaviorResolver
from engine.npc.encounter import EncounterResolver
from engine.scenario.registry import ScenarioRegistry


@dataclass(frozen=True)
class DialogueTarget:
    npc: NPCState
    encounterable: bool
    reasons: tuple[str, ...] = ()


def resolve_dialogue_target(
    state: GameState,
    target: str,
    encounter_resolver: EncounterResolver,
) -> DialogueTarget | None:
    """Resolve an NPC by stable id first, then case-insensitive display name."""
    raw = target.strip().lower()
    if not raw:
        return None
    npc = state.world.npcs.get(raw)
    if npc is None:
        matches = [n for n in state.world.npcs.values() if n.name.lower() == raw]
        if len(matches) != 1:
            return None
        npc = matches[0]
    check = encounter_resolver.check(state, npc.id)
    return DialogueTarget(npc, check.encounterable, check.reasons)


def build_dialogue_context(
    state: GameState,
    target: DialogueTarget,
    *,
    registry: ScenarioRegistry | None = None,
    current_turn: int = 0,
    topic: str = "",
) -> str:
    """Return compact, authoritative instructions for one NPC conversation."""
    npc = target.npc
    behavior = NPCBehaviorResolver(registry=registry).build(state, npc.id, turn=current_turn)
    lines = [
        "DIALOGUE MODE:",
        "  The player is directly interacting with this NPC.",
        "  Speak as the NPC, not as an omniscient narrator.",
        "  Do not reveal facts the NPC does not know.",
        "  Do not decide hidden world state; propose changes only through the schema.",
        f"  target_npc: {npc.id}",
        f"  encounterable: {behavior.can_interact}",
        f"  disposition: {behavior.disposition}",
        f"  relationship_affinity: {behavior.relationship_affinity}",
        f"  relationship_trust: {behavior.relationship_trust}",
        f"  relationship_flags: {list(behavior.relationship_flags)}",
        f"  faction_id: {behavior.faction_id}",
        f"  allowed_action_types: {', '.join(behavior.allowed_action_types)}",
        f"  requested_topic: {topic!r}",
    ]
    if behavior.active_goals:
        lines.append("  active_goals: " + "; ".join(behavior.active_goals))
    if behavior.fears:
        lines.append("  fears: " + "; ".join(behavior.fears))
    if behavior.preferences:
        lines.append("  preferences: " + "; ".join(behavior.preferences))

    if registry is not None and registry.has("characters", npc.id):
        data = registry.require("characters", npc.id).data
        for key in ("speech_style", "dialogue_rules", "knowledge_boundary", "dialogue_topics", "aliases"):
            value = data.get(key)
            if value:
                lines.append(f"  canonical_{key}: {value!r}")
    return "\n".join(lines)
