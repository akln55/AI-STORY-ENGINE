"""NPC foundation helpers: knowledge queries and relationship access."""

from engine.npc.knowledge import (
    grant_knowledge,
    npc_knows,
    player_visible_knowledge,
)

__all__ = ["grant_knowledge", "npc_knows", "player_visible_knowledge"]
