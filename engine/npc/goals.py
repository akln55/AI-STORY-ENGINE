"""Deterministic NPC goal execution.

Goals are scenario-authored plans. The engine selects the highest-priority
executable goal and emits ordinary validated effects; it never asks an AI to
decide whether a goal succeeded. Supported goal kinds are intentionally small:
move_to, follow_npc, meet_npc, patrol, and survive.
"""
from __future__ import annotations
from dataclasses import dataclass
from engine.core.state import GameState, NPCGoal
from engine.rules.base import Effect
from engine.scenario.registry import ScenarioRegistry

_TERMINAL = {"completed", "failed", "abandoned"}

@dataclass(frozen=True)
class NPCGoalDecision:
    npc_id: str
    goal_id: str
    effects: tuple[Effect, ...] = ()
    completed: bool = False
    progress: int | None = None
    reason: str = ""

class NPCGoalEngine:
    """Plan one deterministic action per NPC from scenario-authored goals."""
    def __init__(self, registry: ScenarioRegistry | None = None):
        self.registry = registry

    def plan(self, state: GameState, npc_id: str, *, turn: int) -> NPCGoalDecision | None:
        npc = state.world.npcs.get(npc_id)
        if npc is None or not npc.alive:
            return None
        goals = sorted((g for g in npc.goals if g.status not in _TERMINAL), key=lambda g: (-g.priority, g.id))
        for goal in goals:
            decision = self._plan_goal(state, npc_id, goal, turn=turn)
            if decision is not None:
                return decision
        return None

    def _plan_goal(self, state: GameState, npc_id: str, goal: NPCGoal, *, turn: int) -> NPCGoalDecision | None:
        npc = state.world.npcs[npc_id]
        kind = goal.kind.lower().strip()
        destination = None
        if kind == "move_to":
            destination = goal.target_location
        elif kind in {"follow_npc", "meet_npc"}:
            target = state.world.npcs.get(goal.target_id or "")
            if target is None or not target.alive:
                return NPCGoalDecision(npc_id, goal.id, completed=(kind == "meet_npc"), reason="target unavailable")
            destination = target.location_id
            if kind == "meet_npc" and npc.location_id == destination:
                return NPCGoalDecision(npc_id, goal.id, completed=True, progress=goal.required_progress, reason="met target")
        elif kind == "patrol":
            points = goal.data.get("locations", [])
            if not isinstance(points, list) or not points:
                return None
            points = [x for x in points if isinstance(x, str) and x in state.world.locations]
            if not points:
                return None
            idx = (goal.progress % len(points))
            destination = points[idx]
            if npc.location_id == destination:
                next_progress = goal.progress + 1
                if next_progress >= goal.required_progress:
                    return NPCGoalDecision(npc_id, goal.id, completed=True, progress=next_progress, reason="patrol complete")
                destination = points[next_progress % len(points)]
                return NPCGoalDecision(npc_id, goal.id, progress=next_progress, effects=self._move_effect(npc_id, npc.location_id, destination, state), reason="advance patrol")
        elif kind == "survive":
            return NPCGoalDecision(npc_id, goal.id, progress=goal.progress + 1, completed=(goal.progress + 1 >= goal.required_progress), reason="survival tick")
        else:
            return None
        if destination is None:
            return None
        if destination not in state.world.locations:
            return None
        if npc.location_id == destination:
            return NPCGoalDecision(npc_id, goal.id, completed=True, progress=goal.required_progress, reason="destination reached")
        effects = self._move_effect(npc_id, npc.location_id, destination, state)
        if not effects:
            return None
        return NPCGoalDecision(npc_id, goal.id, effects=effects, reason=f"execute {kind}")

    @staticmethod
    def _move_effect(npc_id: str, current: str, destination: str, state: GameState) -> tuple[Effect, ...]:
        if current and current != destination and not state.world.reachable(current, destination):
            return ()
        return (Effect("location", npc_id, "move", destination, reason="NPC goal execution"),)
