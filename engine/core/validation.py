"""Validation gate — the single hard path for ALL state changes (ADR-0001).

Atomic batch: any rejection → entire batch rejected; post-apply invariants
with snapshot rollback on failure.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from engine.core.invariants import (
    DISPOSITION_MAX,
    DISPOSITION_MIN,
    InvariantError,
    PERSONALITY_MAX,
    PERSONALITY_MIN,
    check_invariants,
)
from engine.core.state import GameState, RelationshipState
from engine.rules.base import (
    EVENT, INVENTORY, LOCATION, NPC_FLAG, RELATIONSHIP, REPUTATION, RESOURCE, PROGRESSION, STATUS, Effect,
)

_PERSONALITY_SETTABLE_FIELDS = {
    "courage", "aggression", "sociability", "honesty",
    "greed", "curiosity", "loyalty", "patience",
}
# List-of-string NPC fields settable via ordinary AI npc_changes (whole-list
# replace, not append; see _apply). Deliberately excludes 'goals': goals are
# engine/scenario-owned in this phase (plan §38) — no AI mutation path.
_NPC_SETTABLE_LIST_FIELDS = {"traits", "fears", "preferences"}
# Explicitly NOT settable via AI npc_changes: 'id', 'name' (identity, plan §9),
# 'goals' (engine/scenario-owned, plan §38), 'hp'/'max_hp'/'location_id'
# (owned by the 'resource'/'location' effect kinds instead).
_REL_SETTABLE_FIELDS = {"affinity", "trust"}


@dataclass
class Rejection:
    effect: Effect
    reason: str


@dataclass
class ValidationReport:
    accepted: list[Effect] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.rejected


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _parse_relationship_target(target: str) -> tuple[str, str] | None:
    """Accept 'a|b' or 'a:b'."""
    if "|" in target:
        parts = target.split("|", 1)
    elif ":" in target:
        parts = target.split(":", 1)
    else:
        return None
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]



def _quest_prerequisites_met(state: GameState, quest) -> bool:
    """Validate quest prerequisites at the shared effect gate.

    This deliberately duplicates the small deterministic prerequisite vocabulary
    used by the player-facing quest rule so scenario events and every future
    effect producer cannot bypass the same authority boundary.
    """
    def compare(left, operator, right):
        try:
            return {"==": lambda: left == right, "!=": lambda: left != right,
                    ">=": lambda: left >= right, "<=": lambda: left <= right,
                    ">": lambda: left > right, "<": lambda: left < right}[operator]()
        except (KeyError, TypeError, ValueError):
            return False

    for req in quest.prerequisites:
        if not isinstance(req, dict):
            return False
        kind = req.get("type")
        if kind == "quest":
            q = state.world.quests.get(req.get("id"))
            ok = q is not None and q.status == req.get("status", "completed")
        elif kind == "level":
            ok = compare(state.character.level, req.get("operator", ">="), req.get("value"))
        elif kind == "realm":
            if req.get("realm_id") is not None and state.character.realm_id != req.get("realm_id"):
                ok = False
            else:
                ok = compare(state.character.realm_stage, req.get("operator", ">="), req.get("value"))
        elif kind == "item":
            present = state.character.has_item(str(req.get("item_id", "")))
            ok = present if "operator" not in req else compare(present, req["operator"], req.get("value", True))
        elif kind == "relationship_flag":
            target = req.get("target")
            flag = req.get("flag")
            rel = state.world.get_relationship("player", target) if isinstance(target, str) else None
            present = rel is not None and isinstance(flag, str) and flag in rel.flags
            ok = present if "operator" not in req else compare(present, req["operator"], req.get("value", True))
        elif kind == "reputation":
            key = req.get("key")
            ok = isinstance(key, str) and compare(state.character.reputation.get(key, 0), req.get("operator", ">="), req.get("value", 0))
        else:
            ok = False
        if not ok:
            return False
    return True

def validate_effect(effect: Effect, state: GameState) -> tuple[bool, object, str]:
    if not effect.allowed():
        return False, None, f"operation '{effect.operation}' not allowed for kind '{effect.kind}'"

    if effect.kind == LOCATION:
        if effect.target not in ("player",) and not state.world.npc_exists(effect.target):
            return False, None, f"unknown move target '{effect.target}'"
        if not state.world.location_exists(str(effect.value)):
            return False, None, f"unknown location '{effect.value}'"
        if effect.target == "player":
            current = state.character.location_id
        else:
            npc = state.world.npcs[effect.target]
            if not npc.alive:
                return False, None, f"cannot move dead npc '{effect.target}'"
            current = npc.location_id
        dest = str(effect.value)
        if current and current != dest and not state.world.reachable(current, dest):
            return False, None, (
                f"location '{dest}' is not reachable from '{current}'")
        return True, effect.value, ""

    if effect.kind == INVENTORY:
        item = state.world.items.get(effect.target)
        if item is None:
            return False, None, f"unknown item '{effect.target}'"
        if effect.operation == "take":
            if item.owner is not None:
                return False, None, f"item '{effect.target}' already owned by {item.owner}"
            if item.location_id is None:
                return False, None, f"item '{effect.target}' is nowhere"
            if item.location_id != state.character.location_id:
                return False, None, (
                    f"item '{effect.target}' is not at player location "
                    f"'{state.character.location_id}'")
            return True, effect.value, ""
        if item.owner != "player":
            return False, None, f"cannot drop item not owned by player"
        if not state.world.location_exists(str(effect.value)):
            return False, None, f"unknown drop location '{effect.value}'"
        return True, effect.value, ""

    if effect.kind == RESOURCE:
        entity_id, _, fld = effect.target.partition(".")
        fld = fld or "hp"
        target = state.character if entity_id == "player" else state.world.npcs.get(entity_id)
        if target is None:
            return False, None, f"unknown resource target '{effect.target}'"
        if entity_id != "player":
            if not state.world.npcs[entity_id].alive:
                return False, None, f"cannot change resources on dead npc '{entity_id}'"
        if not hasattr(target, fld):
            return False, None, f"unknown resource field '{fld}'"
        max_field = f"max_{fld}"
        ceiling = getattr(target, max_field, None)
        if ceiling is None:
            return False, None, f"resource field '{fld}' has no '{max_field}' bound"
        if not isinstance(effect.value, int):
            return False, None, "resource value must be int"
        current = getattr(target, fld)
        if effect.operation == "set":
            return True, _clamp(effect.value, 0, ceiling), ""
        new_value = _clamp(current + effect.value, 0, ceiling)
        return True, new_value - current, ""

    if effect.kind == NPC_FLAG:
        npc = state.world.npcs.get(effect.target)
        if npc is None:
            return False, None, f"unknown npc '{effect.target}'"
        if not (isinstance(effect.value, (tuple, list)) and len(effect.value) == 2):
            return False, None, (
                f"npc change value must be a (field, value) pair, got {effect.value!r}")
        field_name, field_value = effect.value
        if not isinstance(field_name, str):
            return False, None, f"npc field name must be a string, got {field_name!r}"

        if field_name == "alive":
            if not isinstance(field_value, bool):
                return False, None, "alive value must be bool"
            if field_value is True and not npc.alive:
                return False, None, (
                    f"cannot resurrect dead npc '{effect.target}' via ordinary npc effect")
            return True, effect.value, ""

        if field_name == "disposition":
            if not isinstance(field_value, int):
                return False, None, "disposition value must be int"
            if not (DISPOSITION_MIN <= field_value <= DISPOSITION_MAX):
                return False, None, (
                    f"disposition {field_value} outside "
                    f"[{DISPOSITION_MIN}, {DISPOSITION_MAX}]")
            if not npc.alive:
                return False, None, (
                    f"cannot change disposition of dead npc '{effect.target}'")
            return True, effect.value, ""

        if field_name.startswith("personality."):
            sub = field_name[len("personality."):]
            if sub not in _PERSONALITY_SETTABLE_FIELDS:
                return False, None, f"npc personality field '{sub}' is not settable"
            if not isinstance(field_value, int) or isinstance(field_value, bool):
                return False, None, f"personality.{sub} value must be int"
            if not (PERSONALITY_MIN <= field_value <= PERSONALITY_MAX):
                return False, None, (
                    f"personality.{sub} {field_value} outside "
                    f"[{PERSONALITY_MIN}, {PERSONALITY_MAX}]")
            if not npc.alive:
                return False, None, (
                    f"cannot change personality of dead npc '{effect.target}'")
            return True, effect.value, ""

        if field_name in _NPC_SETTABLE_LIST_FIELDS:
            if not (isinstance(field_value, list)
                    and all(isinstance(v, str) for v in field_value)):
                return False, None, f"npc field '{field_name}' value must be a list of strings"
            if not npc.alive:
                return False, None, (
                    f"cannot change {field_name} of dead npc '{effect.target}'")
            return True, effect.value, ""

        return False, None, f"npc field '{field_name}' is not settable"

    if effect.kind == STATUS:
        target = state.character if effect.target == "player" else state.world.npcs.get(effect.target)
        if target is None:
            return False, None, f"unknown status target '{effect.target}'"
        if effect.operation == "add":
            if isinstance(effect.value, str):
                raw = {"effect_type": effect.value}
            elif isinstance(effect.value, dict):
                raw = dict(effect.value)
            else:
                return False, None, "status add value must be a string or object"
            effect_type = str(raw.get("effect_type", "")).strip().lower()
            allowed_types = {"poison", "bleed", "burn", "regeneration", "stamina_regen", "stunned", "rooted"}
            if effect_type not in allowed_types:
                return False, None, f"unknown status effect '{effect_type}'"
            try:
                duration = int(raw.get("remaining_turns", raw.get("duration", 3)))
                potency = int(raw.get("potency", 1))
                stacks = int(raw.get("stacks", 1))
                max_stacks = int(raw.get("max_stacks", 1))
            except (TypeError, ValueError):
                return False, None, "status duration/potency/stacks must be integers"
            if duration < 1 or potency < 1 or stacks < 1 or max_stacks < 1 or stacks > max_stacks:
                return False, None, "invalid status duration/potency/stacks"
            existing = next((x for x in target.status_effects if x.effect_type == effect_type), None)
            if existing is not None:
                return True, {"effect_type": effect_type, "remaining_turns": max(existing.remaining_turns, duration),
                              "potency": max(existing.potency, potency), "stacks": min(max_stacks, existing.stacks + stacks),
                              "max_stacks": max_stacks, "source_id": raw.get("source_id")}, ""
            return True, {"effect_type": effect_type, "remaining_turns": duration, "potency": potency,
                          "stacks": stacks, "max_stacks": max_stacks, "source_id": raw.get("source_id")}, ""
        if effect.operation in {"remove", "tick"}:
            effect_type = str(effect.value).strip().lower() if isinstance(effect.value, str) else ""
            if not effect_type or not any(x.effect_type == effect_type for x in target.status_effects):
                return False, None, f"status '{effect_type}' is not active on '{effect.target}'"
            return True, effect_type, ""
        return False, None, f"unknown status operation '{effect.operation}'"

    if effect.kind == PROGRESSION:
        if effect.target != "player" or effect.operation != "xp":
            return False, None, "invalid progression effect"
        if not isinstance(effect.value, int) or isinstance(effect.value, bool) or effect.value < 0:
            return False, None, "xp reward must be a non-negative int"
        return True, effect.value, ""

    if effect.kind == "quest":
        quest = state.world.quests.get(effect.target)
        if quest is None:
            return False, None, f"unknown quest '{effect.target}'"
        if effect.operation == "activate":
            if quest.status != "available":
                return False, None, f"cannot activate quest '{effect.target}' from status '{quest.status}'"
            if not _quest_prerequisites_met(state, quest):
                return False, None, f"cannot activate quest '{effect.target}': prerequisites not met"
            return True, True, ""
        if effect.operation == "abandon":
            if quest.status != "active":
                return False, None, f"cannot abandon quest '{effect.target}' from status '{quest.status}'"
            return True, True, ""
        return False, None, f"unknown quest operation '{effect.operation}'"

    if effect.kind == EVENT:
        event = state.world.events.get(effect.target)
        if event is None:
            return False, None, f"unknown event '{effect.target}'"
        if effect.operation == "trigger":
            if event.status != "inactive":
                return False, None, (
                    f"cannot trigger event '{effect.target}' from status '{event.status}'")
            if not isinstance(effect.value, int) or isinstance(effect.value, bool) or effect.value < 0:
                return False, None, "event trigger turn must be a non-negative int"
            return True, effect.value, ""
        if effect.operation in {"resolve", "fail", "cancel"}:
            if event.status != "active":
                return False, None, (
                    f"cannot {effect.operation} event '{effect.target}' from status '{event.status}'")
            if not isinstance(effect.value, int) or isinstance(effect.value, bool) or effect.value < 0:
                return False, None, "event terminal turn must be a non-negative int"
            if event.start_turn is not None and effect.value < event.start_turn:
                return False, None, (
                    f"event terminal turn {effect.value} cannot precede "
                    f"start turn {event.start_turn}")
            return True, effect.value, ""
        return False, None, f"unknown event operation '{effect.operation}'"

    if effect.kind == REPUTATION:
        target = effect.target
        if not isinstance(target, str) or not target.startswith("faction:"):
            return False, None, "reputation target must be 'faction:<id>'"
        faction_id = target.split(":", 1)[1].strip()
        if not faction_id:
            return False, None, "reputation faction id must be non-empty"
        if not isinstance(effect.value, int) or isinstance(effect.value, bool):
            return False, None, "reputation value must be int"
        current = state.character.reputation.get(faction_id, 0)
        if effect.operation == "set":
            return True, (faction_id, _clamp(effect.value, DISPOSITION_MIN, DISPOSITION_MAX)), ""
        new_value = _clamp(current + effect.value, DISPOSITION_MIN, DISPOSITION_MAX)
        return True, (faction_id, new_value - current), ""

    if effect.kind == RELATIONSHIP:
        parties = _parse_relationship_target(effect.target)
        if parties is None:
            return False, None, (
                f"relationship target must be 'a|b' or 'a:b', got {effect.target!r}")
        a, b = parties
        if a == b:
            return False, None, "relationship parties must be distinct"
        if not state.world.party_exists(a):
            return False, None, f"unknown relationship party '{a}'"
        if not state.world.party_exists(b):
            return False, None, f"unknown relationship party '{b}'"
        # value: (field, value) for set/add on affinity|trust, or int for affinity set
        if isinstance(effect.value, (tuple, list)) and len(effect.value) == 2:
            field_name, field_value = effect.value
            if field_name not in _REL_SETTABLE_FIELDS:
                return False, None, f"relationship field '{field_name}' is not settable"
            if not isinstance(field_value, int):
                return False, None, f"relationship {field_name} must be int"
            existing = state.world.get_relationship(a, b)
            current = getattr(existing, field_name) if existing else 0
            if effect.operation == "set":
                sanitized = _clamp(field_value, DISPOSITION_MIN, DISPOSITION_MAX)
            else:
                sanitized = _clamp(current + field_value, DISPOSITION_MIN, DISPOSITION_MAX)
                field_value = sanitized - current  # store delta for apply
            return True, (field_name, sanitized if effect.operation == "set" else field_value), ""
        if effect.operation in {"flag_add", "flag_remove"}:
            if not isinstance(effect.value, str) or not effect.value.strip():
                return False, None, "relationship flag must be a non-empty string"
            if len(effect.value) > 80:
                return False, None, "relationship flag is too long"
            return True, effect.value.strip(), ""
        if isinstance(effect.value, int):
            # shorthand: set/add affinity
            if effect.operation == "set":
                return True, ("affinity", _clamp(effect.value, DISPOSITION_MIN, DISPOSITION_MAX)), ""
            existing = state.world.get_relationship(a, b)
            current = existing.affinity if existing else 0
            delta = _clamp(current + effect.value, DISPOSITION_MIN, DISPOSITION_MAX) - current
            return True, ("affinity", delta), ""
        return False, None, f"invalid relationship value {effect.value!r}"

    return False, None, f"unknown effect kind '{effect.kind}'"


def validate_effects(effects: list[Effect], state: GameState) -> ValidationReport:
    report = ValidationReport()
    working = copy.deepcopy(state)
    for effect in effects:
        ok, sanitized, reason = validate_effect(effect, working)
        if ok:
            if sanitized is not effect.value:
                effect = Effect(
                    effect.kind, effect.target, effect.operation,
                    sanitized, effect.reason + " [clamped]")
            report.accepted.append(effect)
            _apply(effect, working)
        else:
            report.rejected.append(Rejection(effect, reason))
    return report


def apply_effects(effects: list[Effect], state: GameState) -> ValidationReport:
    report = validate_effects(effects, state)
    if report.rejected:
        report.accepted = []
        return report
    if not report.accepted:
        return report

    snapshot = copy.deepcopy(state)
    try:
        for effect in report.accepted:
            _apply(effect, state)
        check_invariants(state)
    except InvariantError as err:
        _restore_state(state, snapshot)
        report.accepted = []
        report.rejected.append(
            Rejection(
                effects[0] if effects else Effect("resource", "player", "set", 0),
                f"invariant violation after apply: {err}",
            )
        )
    return report


def _restore_state(live: GameState, snapshot: GameState) -> None:
    live.character = snapshot.character
    live.world = snapshot.world


def _award_xp(character, amount: int) -> None:
    character.xp += amount
    while character.xp >= character.xp_to_next:
        character.xp -= character.xp_to_next
        character.level += 1
        character.xp_to_next = max(character.xp_to_next + 50, character.level * 100)
        character.max_hp += 10
        character.hp = character.max_hp
        character.max_stamina += 5
        character.stamina = character.max_stamina
        character.attack_power += 2
        character.defense += 1


def _apply(effect: Effect, state: GameState) -> None:
    if effect.kind == LOCATION:
        if effect.target == "player":
            state.character.location_id = str(effect.value)
        else:
            state.world.npcs[effect.target].location_id = str(effect.value)

    elif effect.kind == INVENTORY:
        item = state.world.items[effect.target]
        if effect.operation == "take":
            item.owner = "player"
            item.location_id = None
            if item.id not in state.character.inventory:
                state.character.inventory.append(item.id)
        else:
            item.owner = None
            item.location_id = str(effect.value)
            if item.id in state.character.inventory:
                state.character.inventory.remove(item.id)

    elif effect.kind == RESOURCE:
        entity_id, _, fld = effect.target.partition(".")
        fld = fld or "hp"
        target = state.character if entity_id == "player" else state.world.npcs[entity_id]
        if effect.operation == "set":
            setattr(target, fld, int(effect.value))
        else:
            setattr(target, fld, getattr(target, fld) + int(effect.value))
        if entity_id != "player" and fld == "hp":
            npc = state.world.npcs[entity_id]
            if npc.hp <= 0 and npc.alive:
                npc.alive = False

    elif effect.kind == NPC_FLAG:
        npc = state.world.npcs[effect.target]
        field_name, field_value = effect.value
        if field_name.startswith("personality."):
            sub = field_name[len("personality."):]
            setattr(npc.personality, sub, field_value)
        else:
            setattr(npc, field_name, field_value)
        if field_name == "alive" and field_value is False and npc.hp > 0:
            npc.hp = 0

    elif effect.kind == STATUS:
        target = state.character if effect.target == "player" else state.world.npcs[effect.target]
        effect_type = (effect.value.get("effect_type") if isinstance(effect.value, dict) else str(effect.value))
        if effect.operation == "add":
            existing = next((x for x in target.status_effects if x.effect_type == effect_type), None)
            if existing is None:
                from engine.core.state import StatusEffectState
                data = effect.value
                target.status_effects.append(StatusEffectState(
                    effect_type=data["effect_type"], remaining_turns=data["remaining_turns"],
                    potency=data["potency"], stacks=data["stacks"],
                    max_stacks=data["max_stacks"], source_id=data.get("source_id")))
            else:
                data = effect.value
                existing.remaining_turns = max(existing.remaining_turns, int(data["remaining_turns"]))
                existing.potency = max(existing.potency, int(data["potency"]))
                existing.max_stacks = int(data["max_stacks"])
                existing.stacks = min(existing.max_stacks, existing.stacks + int(data["stacks"]))
        elif effect.operation == "tick":
            for existing in target.status_effects:
                if existing.effect_type == effect_type:
                    existing.remaining_turns -= 1
                    break
        elif effect.operation == "remove":
            target.status_effects[:] = [x for x in target.status_effects if x.effect_type != effect_type]

    elif effect.kind == PROGRESSION:
        if effect.operation == "xp":
            _award_xp(state.character, int(effect.value))

    elif effect.kind == "quest":
        quest = state.world.quests[effect.target]
        quest.status = "active" if effect.operation == "activate" else "abandoned"

    elif effect.kind == EVENT:
        event = state.world.events[effect.target]
        if effect.operation == "trigger":
            event.status = "active"
            event.start_turn = int(effect.value)
            event.resolved_turn = None
        else:
            event.status = {"resolve": "resolved", "fail": "failed", "cancel": "cancelled"}[effect.operation]
            event.resolved_turn = int(effect.value)

    elif effect.kind == REPUTATION:
        faction_id, value = effect.value
        if effect.operation == "set":
            state.character.reputation[faction_id] = int(value)
        else:
            current = state.character.reputation.get(faction_id, 0)
            state.character.reputation[faction_id] = _clamp(current + int(value), DISPOSITION_MIN, DISPOSITION_MAX)

    elif effect.kind == RELATIONSHIP:
        parties = _parse_relationship_target(effect.target)
        assert parties is not None
        a, b = parties
        key = RelationshipState.canonical_key(a, b)
        rel = state.world.relationships.get(key)
        if rel is None:
            # store with sorted parties for stable identity
            sa, sb = sorted([a, b])
            rel = RelationshipState(party_a=sa, party_b=sb)
            state.world.relationships[key] = rel
        if effect.operation in {"flag_add", "flag_remove"}:
            flag = str(effect.value)
            if effect.operation == "flag_add":
                if flag not in rel.flags:
                    rel.flags.append(flag)
            elif flag in rel.flags:
                rel.flags.remove(flag)
            return
        field_name, field_value = effect.value
        if effect.operation == "set":
            setattr(rel, field_name, int(field_value))
        else:
            setattr(rel, field_name, getattr(rel, field_name) + int(field_value))
