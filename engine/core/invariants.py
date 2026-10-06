"""State invariant checks — fail safely after apply and after load."""

from __future__ import annotations

from engine.core.state import GameState, RelationshipState

DISPOSITION_MIN = -100
DISPOSITION_MAX = 100

PERSONALITY_MIN = 0
PERSONALITY_MAX = 100
GOAL_PRIORITY_MIN = 0
GOAL_PRIORITY_MAX = 100
GOAL_STATUSES = frozenset({"active", "paused", "completed", "failed", "abandoned"})
GOAL_KINDS = frozenset({"passive", "move_to", "follow_npc", "meet_npc", "patrol", "survive"})
EVENT_STATUSES = frozenset({"inactive", "active", "resolved", "failed", "cancelled"})
EVENT_TERMINAL = frozenset({"resolved", "failed", "cancelled"})

_PERSONALITY_FIELDS = (
    "courage", "aggression", "sociability", "honesty",
    "greed", "curiosity", "loyalty", "patience",
)


class InvariantError(Exception):
    """Authoritative state violates a required invariant."""


def check_invariants(state: GameState) -> None:
    _check_locations(state)
    _check_items(state)
    _check_npcs(state)
    _check_character(state)
    _check_relationships(state)
    _check_events(state)
    _check_quests(state)
    _check_progression(state)


def _check_locations(state: GameState) -> None:
    for loc_id, exits in state.world.exits.items():
        if loc_id not in state.world.locations:
            raise InvariantError(f"exits key references unknown location '{loc_id}'")
        for dest in exits:
            if dest not in state.world.locations:
                raise InvariantError(
                    f"exit from '{loc_id}' references unknown location '{dest}'")


def _check_items(state: GameState) -> None:
    inventory_set = set(state.character.inventory)
    if len(state.character.inventory) != len(inventory_set):
        raise InvariantError("character.inventory contains duplicate item ids")

    for item_id, item in state.world.items.items():
        if item.id != item_id:
            raise InvariantError(
                f"item dict key '{item_id}' != item.id '{item.id}'")
        has_loc = item.location_id is not None
        has_owner = item.owner is not None
        if has_loc == has_owner:
            raise InvariantError(
                f"item '{item_id}' must have exactly one of location_id/owner "
                f"(location_id={item.location_id!r}, owner={item.owner!r})")
        if has_loc and item.location_id not in state.world.locations:
            raise InvariantError(
                f"item '{item_id}' at unknown location '{item.location_id}'")
        if has_owner:
            if item.owner == "player":
                if item_id not in inventory_set:
                    raise InvariantError(
                        f"item '{item_id}' owned by player but missing from inventory")
            elif item.owner not in state.world.npcs:
                raise InvariantError(
                    f"item '{item_id}' owned by unknown entity '{item.owner}'")

    for inv_id in state.character.inventory:
        item = state.world.items.get(inv_id)
        if item is None:
            raise InvariantError(f"inventory references unknown item '{inv_id}'")
        if item.owner != "player":
            raise InvariantError(
                f"inventory item '{inv_id}' has owner={item.owner!r}, expected 'player'")


def _check_npcs(state: GameState) -> None:
    for npc_id, npc in state.world.npcs.items():
        if npc.id != npc_id:
            raise InvariantError(f"npc dict key '{npc_id}' != npc.id '{npc.id}'")
        if npc.location_id not in state.world.locations:
            raise InvariantError(
                f"npc '{npc_id}' at unknown location '{npc.location_id}'")
        if npc.hp < 0 or npc.hp > npc.max_hp:
            raise InvariantError(
                f"npc '{npc_id}' hp {npc.hp} outside [0, {npc.max_hp}]")
        if npc.max_hp < 0:
            raise InvariantError(f"npc '{npc_id}' max_hp is negative")
        if not npc.alive and npc.hp > 0:
            raise InvariantError(f"npc '{npc_id}' is dead but hp={npc.hp} > 0")
        if npc.alive and npc.hp <= 0:
            raise InvariantError(f"npc '{npc_id}' is alive but hp={npc.hp} <= 0")
        if not (DISPOSITION_MIN <= npc.disposition <= DISPOSITION_MAX):
            raise InvariantError(
                f"npc '{npc_id}' disposition {npc.disposition} outside "
                f"[{DISPOSITION_MIN}, {DISPOSITION_MAX}]")
        if not isinstance(npc.traits, list):
            raise InvariantError(f"npc '{npc_id}' traits must be a list")
        if not isinstance(npc.fears, list):
            raise InvariantError(f"npc '{npc_id}' fears must be a list")
        if not isinstance(npc.preferences, list):
            raise InvariantError(f"npc '{npc_id}' preferences must be a list")
        _check_status_effects(npc.status_effects, f"npc:{npc_id}")

        for pf in _PERSONALITY_FIELDS:
            value = getattr(npc.personality, pf)
            if not (PERSONALITY_MIN <= value <= PERSONALITY_MAX):
                raise InvariantError(
                    f"npc '{npc_id}' personality.{pf} {value} outside "
                    f"[{PERSONALITY_MIN}, {PERSONALITY_MAX}]")

        seen_goal_ids: set[str] = set()
        for goal in npc.goals:
            if goal.id in seen_goal_ids:
                raise InvariantError(
                    f"npc '{npc_id}' has duplicate goal id '{goal.id}'")
            seen_goal_ids.add(goal.id)
            if not (GOAL_PRIORITY_MIN <= goal.priority <= GOAL_PRIORITY_MAX):
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' priority {goal.priority} "
                    f"outside [{GOAL_PRIORITY_MIN}, {GOAL_PRIORITY_MAX}]")
            if goal.status not in GOAL_STATUSES:
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' has invalid status "
                    f"{goal.status!r}")
            if goal.kind not in GOAL_KINDS:
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' has invalid kind {goal.kind!r}")
            if goal.required_progress < 1 or goal.progress < 0:
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' has invalid progress")
            if goal.progress > goal.required_progress and goal.kind != "patrol":
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' progress exceeds required_progress")
            if goal.kind == "move_to" and goal.target_location not in state.world.locations:
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' targets unknown location {goal.target_location!r}")
            if goal.kind in {"follow_npc", "meet_npc"} and goal.target_id not in state.world.npcs:
                raise InvariantError(
                    f"npc '{npc_id}' goal '{goal.id}' targets unknown npc {goal.target_id!r}")
            if goal.kind == "patrol":
                locations = goal.data.get("locations") if isinstance(goal.data, dict) else None
                if not isinstance(locations, list) or not locations or any(x not in state.world.locations for x in locations):
                    raise InvariantError(
                        f"npc '{npc_id}' goal '{goal.id}' has invalid patrol locations")


def _check_status_effects(statuses, owner: str) -> None:
    seen = set()
    for effect in statuses:
        if not effect.effect_type or effect.effect_type in seen:
            raise InvariantError(f"{owner} has duplicate/empty status effect '{effect.effect_type}'")
        seen.add(effect.effect_type)
        if effect.remaining_turns < 1:
            raise InvariantError(f"{owner} status '{effect.effect_type}' has invalid duration")
        if effect.potency < 1 or effect.stacks < 1 or effect.max_stacks < 1 or effect.stacks > effect.max_stacks:
            raise InvariantError(f"{owner} status '{effect.effect_type}' has invalid stack/potency values")


def _check_progression(state: GameState) -> None:
    c = state.character
    if c.level < 1:
        raise InvariantError("player level must be >= 1")
    if c.xp < 0 or c.xp >= c.xp_to_next:
        raise InvariantError(f"player xp {c.xp} outside [0, {c.xp_to_next})")
    if c.xp_to_next <= 0:
        raise InvariantError("player xp_to_next must be positive")
    if c.attack_power < 0 or c.defense < 0:
        raise InvariantError("player combat stats cannot be negative")
    for technique_id, technique in state.world.techniques.items():
        if technique.id != technique_id or not technique.id.strip() or not technique.name.strip():
            raise InvariantError(f"invalid technique identity '{technique_id}'")
        if technique.power < 0 or technique.stamina_cost < 0:
            raise InvariantError(f"technique '{technique_id}' has negative combat cost/power")
    if len(c.techniques) != len(set(c.techniques)):
        raise InvariantError("player techniques contain duplicates")
    for technique_id in c.techniques:
        if technique_id not in state.world.techniques:
            raise InvariantError(f"player knows unknown technique '{technique_id}'")
    for npc_id, npc in state.world.npcs.items():
        if npc.attack_power < 0 or npc.defense < 0 or npc.xp_reward < 0:
            raise InvariantError(f"npc '{npc_id}' has invalid combat stats")


def _check_character(state: GameState) -> None:
    c = state.character
    if c.location_id and c.location_id not in state.world.locations:
        raise InvariantError(f"character at unknown location '{c.location_id}'")
    if c.hp < 0 or c.hp > c.max_hp:
        raise InvariantError(f"character hp {c.hp} outside [0, {c.max_hp}]")
    if c.stamina < 0 or c.stamina > c.max_stamina:
        raise InvariantError(
            f"character stamina {c.stamina} outside [0, {c.max_stamina}]")
    if c.max_hp < 0 or c.max_stamina < 0:
        raise InvariantError("character max resource is negative")
    if not (-100 <= c.popularity <= 100):
        raise InvariantError("player popularity must be between -100 and 100")
    _check_status_effects(c.status_effects, "player")
    for key, value in c.reputation.items():
        if not isinstance(key, str) or not key.strip():
            raise InvariantError("player reputation keys must be non-empty strings")
        if not isinstance(value, int) or not (-100 <= value <= 100):
            raise InvariantError(f"player reputation for {key!r} must be between -100 and 100")


def _check_relationships(state: GameState) -> None:
    for key, rel in state.world.relationships.items():
        expected = RelationshipState.canonical_key(rel.party_a, rel.party_b)
        if key != expected:
            raise InvariantError(
                f"relationship key '{key}' != canonical '{expected}'")
        if rel.party_a == rel.party_b:
            raise InvariantError(f"relationship has identical parties '{rel.party_a}'")
        if not state.world.party_exists(rel.party_a):
            raise InvariantError(
                f"relationship party_a unknown '{rel.party_a}'")
        if not state.world.party_exists(rel.party_b):
            raise InvariantError(
                f"relationship party_b unknown '{rel.party_b}'")
        if not (DISPOSITION_MIN <= rel.affinity <= DISPOSITION_MAX):
            raise InvariantError(
                f"relationship {key} affinity {rel.affinity} out of bounds")
        if not (DISPOSITION_MIN <= rel.trust <= DISPOSITION_MAX):
            raise InvariantError(
                f"relationship {key} trust {rel.trust} out of bounds")
        if len(rel.flags) != len(set(rel.flags)):
            raise InvariantError(f"relationship {key} has duplicate flags")
        if any(not isinstance(flag, str) or not flag.strip() for flag in rel.flags):
            raise InvariantError(f"relationship {key} has invalid flags")


def _check_events(state: GameState) -> None:
    for event_id, event in state.world.events.items():
        if event.id != event_id:
            raise InvariantError(
                f"event dict key '{event_id}' != event.id '{event.id}'")
        if event.status not in EVENT_STATUSES:
            raise InvariantError(
                f"event '{event_id}' has invalid status {event.status!r}")
        if event.location_id is not None and event.location_id not in state.world.locations:
            raise InvariantError(
                f"event '{event_id}' references unknown location '{event.location_id}'")
        if len(event.participants) != len(set(event.participants)):
            raise InvariantError(f"event '{event_id}' has duplicate participants")
        for participant in event.participants:
            if not state.world.party_exists(participant):
                raise InvariantError(
                    f"event '{event_id}' references unknown participant '{participant}'")
        if event.start_turn is not None and event.start_turn < 0:
            raise InvariantError(f"event '{event_id}' has negative start_turn")
        if event.resolved_turn is not None and event.resolved_turn < 0:
            raise InvariantError(f"event '{event_id}' has negative resolved_turn")
        if not event.id.strip():
            raise InvariantError(f"event '{event_id}' has empty id")
        if not event.type.strip():
            raise InvariantError(f"event '{event_id}' has empty type")
        if event.start_turn is not None and event.resolved_turn is not None:
            if event.resolved_turn < event.start_turn:
                raise InvariantError(
                    f"event '{event_id}' resolved before it started")
        if event.status == "inactive":
            if event.start_turn is not None:
                raise InvariantError(f"inactive event '{event_id}' has start_turn")
            if event.resolved_turn is not None:
                raise InvariantError(f"inactive event '{event_id}' has resolved_turn")
        elif event.status == "active":
            if event.start_turn is None:
                raise InvariantError(f"active event '{event_id}' has no start_turn")
            if event.resolved_turn is not None:
                raise InvariantError(f"active event '{event_id}' has resolved_turn")
        else:
            if event.start_turn is None:
                raise InvariantError(f"terminal event '{event_id}' has no start_turn")
            if event.resolved_turn is None:
                raise InvariantError(f"terminal event '{event_id}' has no resolved_turn")


def _check_quests(state: GameState) -> None:
    quest_statuses = {"available", "active", "completed", "failed", "abandoned"}
    objective_types = {"collect", "reach", "defeat", "talk"}
    for quest_id, quest in state.world.quests.items():
        if quest.id != quest_id:
            raise InvariantError(f"quest dict key '{quest_id}' != quest.id '{quest.id}'")
        if not quest.id.strip() or not quest.title.strip():
            raise InvariantError(f"quest '{quest_id}' has empty id/title")
        if quest.status not in quest_statuses:
            raise InvariantError(f"quest '{quest_id}' has invalid status {quest.status!r}")
        if not isinstance(quest.prerequisites, list):
            raise InvariantError(f"quest '{quest_id}' prerequisites must be a list")
        if not isinstance(quest.rewards, list):
            raise InvariantError(f"quest '{quest_id}' rewards must be a list")
        for req in quest.prerequisites:
            if not isinstance(req, dict) or req.get("type") not in {"quest", "level", "realm", "item", "relationship_flag", "reputation"}:
                raise InvariantError(f"quest '{quest_id}' has invalid prerequisite {req!r}")
        if quest.giver is not None and not state.world.party_exists(quest.giver):
            raise InvariantError(f"quest '{quest_id}' references unknown giver '{quest.giver}'")
        for participant in quest.participants:
            if not state.world.party_exists(participant):
                raise InvariantError(
                    f"quest '{quest_id}' references unknown participant '{participant}'")
        objective_ids: set[str] = set()
        for objective in quest.objectives:
            if objective.id in objective_ids:
                raise InvariantError(
                    f"quest '{quest_id}' has duplicate objective id '{objective.id}'")
            objective_ids.add(objective.id)
            if not objective.id.strip() or not objective.description.strip():
                raise InvariantError(f"quest '{quest_id}' has invalid objective '{objective.id}'")
            if objective.type not in objective_types:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' has invalid type {objective.type!r}")
            if objective.required_count <= 0:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' has non-positive required_count")
            if objective.current_count < 0 or objective.current_count > objective.required_count:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' progress out of bounds")
            if objective.completed and objective.current_count < objective.required_count:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' marked complete below required_count")
            if objective.type == "reach" and objective.target_id not in state.world.locations:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' references unknown location '{objective.target_id}'")
            if objective.type == "defeat" and objective.target_id not in state.world.npcs:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' references unknown npc '{objective.target_id}'")
            if objective.type == "collect" and objective.target_id not in state.world.items:
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' references unknown item '{objective.target_id}'")
            if objective.type == "talk" and not state.world.party_exists(objective.target_id):
                raise InvariantError(
                    f"quest '{quest_id}' objective '{objective.id}' references unknown party '{objective.target_id}'")
