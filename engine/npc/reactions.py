"""Deterministic NPC reactions to explicit player interactions."""
from __future__ import annotations
from engine.core.state import GameState
from engine.rules.base import Effect

class NPCReactionEngine:
    """Translate interaction outcomes into small, bounded relationship changes."""
    def effects_for_player_interaction(self, state: GameState, npc_id: str, *, outcome: str) -> tuple[Effect, ...]:
        npc = state.world.npcs.get(npc_id)
        if npc is None or not npc.alive:
            return ()
        if outcome == "talk":
            da = 1 if npc.personality.sociability >= 50 else 0
            dt = 1 if npc.personality.honesty >= 50 else 0
        elif outcome == "help":
            da = 2 + (1 if npc.personality.loyalty >= 50 else 0)
            dt = 2
        elif outcome == "harm":
            da = -2
            dt = -3
        else:
            return ()
        if da == 0 and dt == 0:
            return ()
        return (
            Effect("relationship", f"player|{npc_id}", "add", ("affinity", da), reason="deterministic NPC reaction"),
            Effect("relationship", f"player|{npc_id}", "add", ("trust", dt), reason="deterministic NPC reaction"),
        )
