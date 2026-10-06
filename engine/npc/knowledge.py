"""Knowledge foundation on top of MemorySystem visibility.

Knowledge facts are memory records in the 'knowledge' store.
Visibility controls who may retrieve them:
  - player: shared/world knowledge the player has learned
  - npc:<id>: private to that NPC (and system)
  - system: engine-only
"""

from __future__ import annotations

from engine.core.state import GameState
from engine.memory.retrieval import retrieve
from engine.memory.system import MemoryRecord, MemorySystem, MemoryValidationError


def grant_knowledge(
    memory: MemorySystem,
    content: str,
    *,
    visibility: str,
    importance: int = 20,
    turn: int = 0,
    entity_id: str | None = None,
    location_id: str | None = None,
    tags: list[str] | None = None,
    state: GameState | None = None,
) -> MemoryRecord:
    """Insert a knowledge fact after optional world-ID cross-check."""
    if state is not None:
        cross_check_refs(state, entity_id=entity_id, location_id=location_id,
                         visibility=visibility)
    return memory.add(
        store="knowledge",
        content=content,
        visibility=visibility,
        importance=importance,
        created_turn=turn,
        entity_id=entity_id,
        location_id=location_id,
        tags=tags or ["knowledge"],
    )


def npc_knows(
    memory: MemorySystem,
    npc_id: str,
    *,
    query_terms: list[str] | None = None,
    limit: int = 20,
) -> list[MemoryRecord]:
    """Facts visible to this NPC (npc:<id> + player-visible)."""
    return retrieve(
        memory,
        viewer=f"npc:{npc_id}",
        store="knowledge",
        query_terms=query_terms,
        limit=limit,
    )


def player_visible_knowledge(
    memory: MemorySystem,
    *,
    query_terms: list[str] | None = None,
    limit: int = 20,
) -> list[MemoryRecord]:
    return retrieve(
        memory,
        viewer="player",
        store="knowledge",
        query_terms=query_terms,
        limit=limit,
    )


def cross_check_refs(
    state: GameState,
    *,
    entity_id: str | None,
    location_id: str | None,
    visibility: str,
    event_id: str | None = None,
) -> None:
    """Shared world-reference cross-check for any proposed memory record.

    Used by grant_knowledge (engine-side knowledge grants) and by
    engine.core.game.GameSession._ingest_memory_updates (AI memory_updates
    proposals) so both paths reject the same unknown references the same
    way — one validation rule, not two.

    event_id is cross-checked against the authoritative event registry.
    Unknown event references are rejected before persistence.
    """
    if entity_id is not None:
        if entity_id != "player" and not state.world.item_exists(entity_id) \
                and not state.world.npc_exists(entity_id):
            raise MemoryValidationError(
                f"entity_id '{entity_id}' not found in world")
    if location_id is not None and not state.world.location_exists(location_id):
        raise MemoryValidationError(
            f"location_id '{location_id}' not found in world")
    if visibility.startswith("npc:"):
        npc_id = visibility[4:]
        if not state.world.npc_exists(npc_id):
            raise MemoryValidationError(
                f"visibility references unknown npc '{npc_id}'")
    if event_id is not None and not state.world.event_exists(event_id):
        raise MemoryValidationError(
            f"event_id '{event_id}' not found in world")
