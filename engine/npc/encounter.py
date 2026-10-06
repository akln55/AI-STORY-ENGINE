"""Deterministic NPC presence and encounter gating.

NPC existence, physical presence, and encounterability are separate concepts.
The runtime state owns the NPC's actual location/alive state; scenario data may
add declarative conditions that decide whether the player can actually engage it.
All conditions are ANDed. Unknown condition types are rejected by validation
rather than silently granting access.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from engine.core.state import GameState, NPCState
from engine.scenario.registry import ScenarioRegistry

SUPPORTED_CONDITIONS = frozenset({
    "location",
    "popularity",
    "reputation",
    "level",
    "realm",
    "relationship_affinity",
    "relationship_trust",
    "relationship_flag",
    "inventory",
    "quest",
    "event",
    "npc_present",
    "npc_absent",
})


@dataclass(frozen=True)
class EncounterCheck:
    npc_id: str
    encounterable: bool
    reasons: tuple[str, ...] = ()


class EncounterResolver:
    def __init__(self, registry: ScenarioRegistry | None = None) -> None:
        self.registry = registry
        self.current_turn = 0

    def check(self, state: GameState, npc_id: str, *, turn: int | None = None) -> EncounterCheck:
        if turn is None:
            turn = self.current_turn
        npc = state.world.npcs.get(npc_id)
        if npc is None:
            return EncounterCheck(npc_id, False, ("unknown NPC",))
        if not npc.alive:
            return EncounterCheck(npc_id, False, ("NPC is dead",))
        if npc.location_id != state.character.location_id:
            return EncounterCheck(npc_id, False, ("NPC is not at the player's location",))
        if self.registry is None or not self.registry.has("characters", npc_id):
            return EncounterCheck(npc_id, True)

        record = self.registry.require("characters", npc_id).data
        reasons: list[str] = []
        presence = record.get("presence")
        if presence is not None and not self._presence_allows(state, presence, turn):
            reasons.append("NPC is not currently present")
        conditions = record.get("encounter_conditions", ())
        if not isinstance(conditions, (list, tuple)):
            return EncounterCheck(npc_id, False, ("invalid encounter_conditions",))
        for condition in conditions:
            if not isinstance(condition, Mapping) or not self._condition(state, condition, turn):
                reasons.append(self._reason(condition))
        return EncounterCheck(npc_id, not reasons, tuple(reasons))

    def encounterable_npcs(self, state: GameState, *, turn: int = 0) -> tuple[NPCState, ...]:
        result = [
            npc for npc in state.world.npcs.values()
            if self.check(state, npc.id, turn=turn).encounterable
        ]
        result.sort(key=lambda npc: npc.id)
        return tuple(result)

    def _presence_allows(self, state: GameState, raw: Any, turn: int) -> bool:
        if not isinstance(raw, (list, tuple)):
            return False
        for entry in raw:
            if not isinstance(entry, Mapping):
                continue
            location = entry.get("location_id")
            if location is not None and location != state.character.location_id:
                continue
            start = entry.get("from_turn")
            end = entry.get("to_turn")
            if isinstance(start, int) and turn < start:
                continue
            if isinstance(end, int) and turn > end:
                continue
            return True
        return False

    def _condition(self, state: GameState, condition: Mapping[str, Any], turn: int) -> bool:
        kind = condition.get("type")
        if kind not in SUPPORTED_CONDITIONS:
            return False
        op = condition.get("operator", ">=")
        value = condition.get("value")
        if kind == "location":
            return _compare(state.character.location_id, op, value)
        if kind == "popularity":
            return _compare(state.character.popularity, op, value)
        if kind == "reputation":
            key = condition.get("key")
            if not isinstance(key, str):
                return False
            return _compare(state.character.reputation.get(key, 0), op, value)
        if kind == "level":
            return _compare(state.character.level, op, value)
        if kind == "realm":
            if condition.get("realm_id") is not None and state.character.realm_id != condition.get("realm_id"):
                return False
            return _compare(state.character.realm_stage, op, value)
        if kind in ("relationship_affinity", "relationship_trust"):
            target = condition.get("target")
            if not isinstance(target, str):
                return False
            rel = state.world.get_relationship("player", target)
            if rel is None:
                return False
            current = rel.affinity if kind == "relationship_affinity" else rel.trust
            return _compare(current, op, value)
        if kind == "relationship_flag":
            target = condition.get("target")
            flag = condition.get("flag")
            if not isinstance(target, str) or not isinstance(flag, str):
                return False
            rel = state.world.get_relationship("player", target)
            present = rel is not None and flag in rel.flags
            return _compare(present, op, True if value is None else value)
        if kind == "inventory":
            item_id = condition.get("item_id")
            if not isinstance(item_id, str):
                return False
            present = state.character.has_item(item_id)
            return present if value is None else _compare(present, op, value)
        if kind in ("quest", "event"):
            identifier = condition.get("id")
            if not isinstance(identifier, str):
                return False
            container = state.world.quests if kind == "quest" else state.world.events
            obj = container.get(identifier)
            if obj is None:
                return False
            return _compare(obj.status, op, value)
        target = condition.get("npc_id")
        if not isinstance(target, str):
            return False
        npc = state.world.npcs.get(target)
        if npc is None:
            return False if kind == "npc_present" else True
        present = npc.alive and npc.location_id == state.character.location_id
        return present if kind == "npc_present" else not present

    @staticmethod
    def _reason(condition: Any) -> str:
        if isinstance(condition, Mapping):
            return f"encounter condition failed: {condition.get('type', 'unknown')}"
        return "invalid encounter condition"


def _compare(left: Any, operator: str, right: Any) -> bool:
    try:
        if operator == "==": return left == right
        if operator == "!=": return left != right
        if operator == ">=": return left >= right
        if operator == "<=": return left <= right
        if operator == ">": return left > right
        if operator == "<": return left < right
        if operator == "in": return left in right
    except (TypeError, ValueError):
        return False
    return False
