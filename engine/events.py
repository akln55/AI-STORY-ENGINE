"""Deterministic scenario event engine.

Canonical event definitions live in scenario ``data/events.json``. Runtime
EventState remains authoritative. Events are evaluated after an action's
validated state changes and may apply only engine-approved Effect objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from engine.core.state import GameState
from engine.core.validation import apply_effects
from engine.rules.base import Effect
from engine.scenario.configuration import ScenarioConfiguration
from engine.scenario.registry import ScenarioRegistry


@dataclass(frozen=True)
class EventEvaluation:
    event_id: str
    triggered: bool
    reason: str = ""
    new_chapter: int | None = None


class EventEngine:
    def __init__(self, registry: ScenarioRegistry | None = None):
        self.registry = registry

    def evaluate(self, state: GameState, *, turn: int, configuration: ScenarioConfiguration | None = None) -> tuple[EventEvaluation, ...]:
        """Evaluate scenario events with bounded same-turn cascading.

        Triggered events may unlock later events in the same action. Each event
        can trigger at most once because its runtime status changes to active.
        The bound prevents malformed scenario graphs from creating an infinite
        event loop.
        """
        if self.registry is None or not self.registry.all("events"):
            return ()
        results: list[EventEvaluation] = []
        max_passes = max(1, len(self.registry.all("events")))
        for _ in range(max_passes):
            changed = False
            for record in self.registry.all("events"):
                event = state.world.events.get(record.id)
                if event is None or event.status != "inactive":
                    continue
                data = record.data
                if not self._conditions_pass(state, data.get("trigger_conditions", ()), turn, configuration):
                    continue
                effects = self._effects(data.get("effects", ()), event.id, turn)
                if not effects:
                    effects = [Effect("event", event.id, "trigger", turn, "scenario event trigger")]
                elif not any(e.kind == "event" and e.target == event.id for e in effects):
                    effects.insert(0, Effect("event", event.id, "trigger", turn, "scenario event trigger"))
                report = apply_effects(effects, state)
                if report.clean:
                    new_chapter = None
                    if configuration is not None and data.get("advance_chapter_to") is not None:
                        try:
                            new_chapter = int(data["advance_chapter_to"])
                        except (TypeError, ValueError):
                            new_chapter = None
                    results.append(EventEvaluation(event.id, True, new_chapter=new_chapter))
                    changed = True
                else:
                    results.append(EventEvaluation(event.id, False, report.rejected[0].reason if report.rejected else "rejected"))
            if not changed:
                break
        return tuple(results)

    @staticmethod
    def _conditions_pass(state: GameState, conditions: Any, turn: int, configuration: ScenarioConfiguration | None) -> bool:
        if not isinstance(conditions, (list, tuple)):
            return False
        for c in conditions:
            if not isinstance(c, Mapping) or not _condition(state, c, turn, configuration):
                return False
        return True

    @staticmethod
    def _effects(raw: Any, event_id: str, turn: int) -> list[Effect]:
        if not isinstance(raw, (list, tuple)):
            return []
        result: list[Effect] = []
        for item in raw:
            if not isinstance(item, Mapping):
                return []
            kind, target, operation = item.get("kind"), item.get("target"), item.get("operation")
            if not all(isinstance(x, str) and x for x in (kind, target, operation)):
                return []
            result.append(Effect(kind, target, operation, item.get("value"), "scenario event"))
        return result


def _condition(state: GameState, c: Mapping[str, Any], turn: int, configuration: ScenarioConfiguration | None) -> bool:
    kind = c.get("type")
    op = c.get("operator", ">=")
    value = c.get("value")
    if kind == "turn": return _compare(turn, op, value)
    if kind == "chapter": return configuration is not None and _compare(configuration.current_chapter, op, value)
    if kind == "location": return _compare(state.character.location_id, op, value)
    if kind == "level": return _compare(state.character.level, op, value)
    if kind == "realm":
        if c.get("realm_id") is not None and state.character.realm_id != c.get("realm_id"): return False
        return _compare(state.character.realm_stage, op, value)
    if kind == "popularity": return _compare(state.character.popularity, op, value)
    if kind == "reputation":
        key = c.get("key")
        return isinstance(key, str) and _compare(state.character.reputation.get(key, 0), op, value)
    if kind in ("relationship_affinity", "relationship_trust"):
        target = c.get("target")
        if not isinstance(target, str): return False
        rel = state.world.get_relationship("player", target)
        if rel is None: return False
        return _compare(rel.affinity if kind.endswith("affinity") else rel.trust, op, value)
    if kind == "relationship_flag":
        target = c.get("target")
        flag = c.get("flag")
        if not isinstance(target, str) or not isinstance(flag, str): return False
        rel = state.world.get_relationship("player", target)
        present = rel is not None and flag in rel.flags
        return _compare(present, op, value if value is not None else True)
    if kind == "inventory":
        item = c.get("item_id")
        if not isinstance(item, str): return False
        return _compare(item in state.character.inventory, op, value)
    if kind in ("quest", "event"):
        ident = c.get("id")
        if not isinstance(ident, str): return False
        obj = (state.world.quests if kind == "quest" else state.world.events).get(ident)
        return obj is not None and _compare(obj.status, op, value)
    if kind in ("npc_present", "npc_absent"):
        ident = c.get("npc_id")
        npc = state.world.npcs.get(ident) if isinstance(ident, str) else None
        present = npc is not None and npc.alive and npc.location_id == state.character.location_id
        return present if kind == "npc_present" else not present
    return False


def _compare(left: Any, op: str, right: Any) -> bool:
    try:
        return {"==": lambda: left == right, "!=": lambda: left != right,
                ">=": lambda: left >= right, "<=": lambda: left <= right,
                ">": lambda: left > right, "<": lambda: left < right,
                "in": lambda: left in right}[op]()
    except (KeyError, TypeError, ValueError):
        return False
