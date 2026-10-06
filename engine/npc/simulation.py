"""Deterministic NPC world simulation.

Combines scenario-authored schedules with engine-owned goal execution and
knowledge propagation. Every physical mutation still crosses apply_effects.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any, Mapping
from engine.core.state import GameState
from engine.core.validation import apply_effects
from engine.memory.system import MemorySystem
from engine.npc.goals import NPCGoalEngine
from engine.rules.base import Effect
from engine.scenario.registry import ScenarioRegistry

@dataclass(frozen=True)
class NPCMovement:
    npc_id: str
    from_location: str
    to_location: str

@dataclass(frozen=True)
class NPCGoalAction:
    npc_id: str
    goal_id: str
    reason: str

@dataclass(frozen=True)
class NPCKnowledgeTransfer:
    source_npc: str
    target_npc: str
    memory_id: str

@dataclass(frozen=True)
class NPCSimulationReport:
    turn: int
    movements: tuple[NPCMovement, ...] = ()
    goal_actions: tuple[NPCGoalAction, ...] = ()
    knowledge_transfers: tuple[NPCKnowledgeTransfer, ...] = ()

class NPCSimulationEngine:
    def __init__(self, registry: ScenarioRegistry | None = None) -> None:
        self.registry = registry
        self.goal_engine = NPCGoalEngine(registry)

    def advance(self, state: GameState, *, turn: int, memory: MemorySystem | None = None) -> NPCSimulationReport:
        if self.registry is None:
            return NPCSimulationReport(turn)
        effects: list[Effect] = []
        movements: list[NPCMovement] = []
        goal_actions: list[NPCGoalAction] = []
        goal_decisions = []
        # Goals are considered first; explicit schedules remain the fallback.
        for npc in sorted(state.world.npcs.values(), key=lambda x: x.id):
            if not npc.alive:
                continue
            decision = self.goal_engine.plan(state, npc.id, turn=turn)
            if decision is not None:
                goal_decisions.append((npc, decision))
                if decision.effects:
                    effects.extend(decision.effects)
                    for e in decision.effects:
                        if e.kind == "location":
                            movements.append(NPCMovement(npc.id, npc.location_id, str(e.value)))
                goal_actions.append(NPCGoalAction(npc.id, decision.goal_id, decision.reason))
                continue
            destination = self._scheduled_location(self._schedule_for(npc.id), turn)
            if destination is None or destination == npc.location_id or destination not in state.world.locations:
                continue
            effects.append(Effect("location", npc.id, "move", destination, reason="deterministic NPC schedule"))
            movements.append(NPCMovement(npc.id, npc.location_id, destination))
        if effects:
            report = apply_effects(effects, state)
            if not report.clean:
                return NPCSimulationReport(turn)
        for npc, decision in goal_decisions:
            if decision.reason not in {"advance patrol", "execute patrol"} and decision.effects and any(e.kind == "location" for e in decision.effects):
                if npc.location_id == str(decision.effects[-1].value):
                    decision = replace(decision, completed=True, progress=max(decision.progress or 0, 1))
            self._apply_goal_progress(npc, decision)
        transfers = self._propagate_knowledge(state, memory)
        return NPCSimulationReport(turn, tuple(movements), tuple(goal_actions), tuple(transfers))

    def _schedule_for(self, npc_id: str):
        if self.registry is None:
            return None
        record = self.registry.get("characters", npc_id)
        return record.data.get("schedule") if record is not None else None

    @staticmethod
    def _apply_goal_progress(npc, decision) -> None:
        goal = next((g for g in npc.goals if g.id == decision.goal_id), None)
        if goal is None:
            return
        if decision.progress is not None:
            goal.progress = max(0, min(decision.progress, max(goal.required_progress, decision.progress)))
        if decision.completed:
            goal.status = "completed"

    @staticmethod
    def _rollback_goal_progress(npc, goal_id: str) -> None:
        goal = next((g for g in npc.goals if g.id == goal_id), None)
        if goal is not None and goal.status == "completed":
            goal.status = "active"
            goal.progress = max(0, goal.progress - 1)
        elif goal is not None and goal.progress > 0:
            goal.progress -= 1

    def _propagate_knowledge(self, state: GameState, memory: MemorySystem | None):
        if memory is None:
            return []
        records = [r for r in memory.all_records() if r.store == "knowledge" and r.visibility.startswith("npc:")]
        transfers = []
        npcs = sorted([n for n in state.world.npcs.values() if n.alive], key=lambda n: n.id)
        for source in npcs:
            source_records = [r for r in records if r.visibility == f"npc:{source.id}" and "secret" not in r.tags]
            if not source_records:
                continue
            for target in npcs:
                if target.id == source.id or target.location_id != source.location_id:
                    continue
                rel = state.world.get_relationship(source.id, target.id)
                if rel is None or rel.trust < 50:
                    continue
                for rec in source_records[:8]:
                    memory.add(store="knowledge", content=rec.content, visibility=f"npc:{target.id}",
                               importance=rec.importance, created_turn=rec.created_turn,
                               entity_id=rec.entity_id, location_id=rec.location_id, event_id=rec.event_id,
                               tags=list(dict.fromkeys(rec.tags + ["propagated"])))
                    transfers.append(NPCKnowledgeTransfer(source.id, target.id, rec.id))
        return transfers

    @staticmethod
    def _scheduled_location(raw: Any, turn: int) -> str | None:
        if not isinstance(raw, (list, tuple)):
            return None
        matches: list[tuple[int, int, str]] = []
        for index, entry in enumerate(raw):
            if not isinstance(entry, Mapping): continue
            location = entry.get("location_id"); start = entry.get("from_turn", 0); end = entry.get("to_turn"); cycle = entry.get("cycle_turns")
            if not isinstance(location, str) or not location.strip() or not isinstance(start, int) or isinstance(start, bool): continue
            if end is not None and (not isinstance(end, int) or isinstance(end, bool)): continue
            if cycle is not None and (not isinstance(cycle, int) or isinstance(cycle, bool) or cycle <= 0): continue
            if end is not None and end < start: continue
            effective_turn = turn % cycle if cycle is not None else turn
            if start <= effective_turn and (end is None or effective_turn <= end): matches.append((start, index, location))
        if not matches: return None
        matches.sort(); return matches[-1][2]
