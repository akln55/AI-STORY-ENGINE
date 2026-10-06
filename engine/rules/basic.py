"""MVP deterministic rules: movement, item ownership, basic combat.

Combat is deliberately minimal (Phase 1 scope per PROTOTYPE_MVP.md): fixed
damage, stamina cost, no weapons/skills yet (Phase 6). The rule — not the AI —
decides HP/stamina outcomes (ADR-0001).
"""

from __future__ import annotations

from engine.core.state import GameState
from engine.npc.encounter import EncounterResolver
from engine.rules.base import PROGRESSION
from engine.parser.intents import Intent
from engine.rules.base import Effect, RuleResult

ATTACK_DAMAGE = 15
ATTACK_STAMINA_COST = 10
NPC_HOSTILE_DISPOSITION = -25


class MovementRule:
    name = "movement"

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "go":
            return None
        if not intent.target:
            return RuleResult([], "Go where?")
        if not state.world.location_exists(intent.target):
            return RuleResult([], f"There is no place called '{intent.target}'.")
        if not state.world.reachable(state.character.location_id, intent.target):
            return RuleResult([], "You can't go there from here.")
        effects = [Effect(
            kind="location", target="player", operation="move",
            value=intent.target, reason="player movement",
        )]
        return RuleResult(effects, f"You head to {state.world.locations[intent.target]}.")


class TakeRule:
    name = "take"

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "take":
            return None
        if not intent.target:
            return RuleResult([], "Take what?")
        item = state.world.items.get(intent.target)
        if item is None:
            return RuleResult([], f"You see no '{intent.target}' here.")
        if item.owner is not None:
            return RuleResult([], f"The {item.name} is not yours to take.")
        if item.location_id != state.character.location_id:
            return RuleResult([], f"There is no {item.name} here.")
        effects = [Effect(
            kind="inventory", target=item.id, operation="take",
            value="player", reason="player picks up item",
        )]
        return RuleResult(effects, f"You take the {item.name}.")


class DropRule:
    name = "drop"

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "drop":
            return None
        if not intent.target:
            return RuleResult([], "Drop what?")
        if not state.character.has_item(intent.target):
            return RuleResult([], f"You are not carrying '{intent.target}'.")
        effects = [Effect(
            kind="inventory", target=intent.target, operation="drop",
            value=state.character.location_id, reason="player drops item",
        )]
        return RuleResult(effects, f"You drop the {intent.target}.")



class AcceptQuestRule:
    name = "accept_quest"

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "accept":
            return None
        if not intent.target:
            return RuleResult([], "Accept which quest?")
        quest = state.world.quests.get(intent.target)
        if quest is None:
            return RuleResult([], f"There is no quest '{intent.target}'.")
        if quest.status != "available":
            return RuleResult([], f"Quest '{quest.title}' is not available.")
        missing = [req for req in quest.prerequisites if not _quest_prerequisite_met(state, req)]
        if missing:
            return RuleResult([], f"Quest '{quest.title}' cannot be accepted yet.")
        return RuleResult([Effect("quest", quest.id, "activate", True, "player accepts quest")],
                          f"You accept the quest: {quest.title}.")


class AbandonQuestRule:
    name = "abandon_quest"

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "abandon":
            return None
        if not intent.target:
            return RuleResult([], "Abandon which quest?")
        quest = state.world.quests.get(intent.target)
        if quest is None:
            return RuleResult([], f"There is no quest '{intent.target}'.")
        if quest.status != "active":
            return RuleResult([], f"Quest '{quest.title}' is not active.")
        return RuleResult([Effect("quest", quest.id, "abandon", True, "player abandons quest")],
                          f"You abandon the quest: {quest.title}.")


def _quest_prerequisite_met(state: GameState, req) -> bool:
    if not isinstance(req, dict):
        return False
    kind = req.get("type")
    if kind == "quest":
        q = state.world.quests.get(req.get("id"))
        return q is not None and q.status == req.get("status", "completed")
    if kind == "level":
        return _compare(state.character.level, req.get("operator", ">="), req.get("value"))
    if kind == "realm":
        if req.get("realm_id") is not None and state.character.realm_id != req.get("realm_id"):
            return False
        return _compare(state.character.realm_stage, req.get("operator", ">="), req.get("value"))
    if kind == "item":
        present = state.character.has_item(str(req.get("item_id", "")))
        return present if "operator" not in req else _compare(present, req["operator"], req.get("value", True))
    if kind == "relationship_flag":
        target = req.get("target")
        flag = req.get("flag")
        rel = state.world.get_relationship("player", target) if isinstance(target, str) else None
        present = rel is not None and isinstance(flag, str) and flag in rel.flags
        return present if "operator" not in req else _compare(present, req["operator"], req.get("value", True))
    if kind == "reputation":
        key = req.get("key")
        if not isinstance(key, str): return False
        return _compare(state.character.reputation.get(key, 0), req.get("operator", ">="), req.get("value", 0))
    return False


def _compare(left, operator, right):
    try:
        return {"==": lambda: left == right, "!=": lambda: left != right, ">=": lambda: left >= right, "<=": lambda: left <= right, ">": lambda: left > right, "<": lambda: left < right}[operator]()
    except (KeyError, TypeError, ValueError):
        return False


class AttackRule:
    name = "attack"

    def __init__(self, encounter_resolver: EncounterResolver | None = None):
        self.encounter_resolver = encounter_resolver or EncounterResolver()

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "attack":
            return None
        if not intent.target:
            return RuleResult([], "Attack what?")
        npc = state.world.npcs.get(intent.target)
        if npc is None or not npc.alive:
            return RuleResult([], f"There is no '{intent.target}' to attack.")
        check = self.encounter_resolver.check(state, npc.id)
        if not check.encounterable:
            return RuleResult([], f"You cannot reach {npc.name} right now.")
        if state.character.stamina < ATTACK_STAMINA_COST:
            return RuleResult([], "You are too exhausted to attack.")
        damage = max(1, state.character.attack_power - npc.defense)
        effects = [
            Effect(kind="resource", target=npc.id, operation="add",
                   value=-damage, reason="combat damage"),
            Effect(kind="resource", target="player.stamina", operation="add",
                   value=-ATTACK_STAMINA_COST, reason="combat exertion"),
        ]
        remaining_hp = npc.hp - damage
        hint = f"You strike the {npc.name} for {damage} damage."
        if remaining_hp <= 0:
            effects.append(Effect(kind="npc", target=npc.id, operation="set",
                                  value=("alive", False), reason="npc slain"))
            effects.append(Effect(kind=PROGRESSION, target="player", operation="xp",
                                  value=npc.xp_reward, reason="combat victory reward"))
        elif npc.disposition <= NPC_HOSTILE_DISPOSITION:
            retaliation = max(1, npc.attack_power - state.character.defense)
            effects.append(Effect(kind="resource", target="player.hp", operation="add",
                                  value=-retaliation, reason="hostile npc retaliation"))
            hint += f" The {npc.name} retaliates for {retaliation} damage."
        return RuleResult(effects, hint)


class TechniqueRule:
    name = "technique"

    def __init__(self, encounter_resolver: EncounterResolver | None = None):
        self.encounter_resolver = encounter_resolver or EncounterResolver()

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        if intent.action != "use":
            return None
        parts = intent.target.split(None, 1)
        if len(parts) != 2:
            return RuleResult([], "Use which technique on whom?")
        technique_id, target_id = parts
        technique = state.world.techniques.get(technique_id)
        if technique is None or technique_id not in state.character.techniques:
            return RuleResult([], f"You do not know '{technique_id}'.")
        npc = state.world.npcs.get(target_id)
        if npc is None or not npc.alive:
            return RuleResult([], f"There is no '{target_id}' to target.")
        check = self.encounter_resolver.check(state, npc.id)
        if not check.encounterable:
            return RuleResult([], f"You cannot reach {npc.name} right now.")
        if state.character.stamina < technique.stamina_cost:
            return RuleResult([], "You are too exhausted to use that technique.")
        damage = max(1, state.character.attack_power + technique.power - npc.defense)
        effects = [
            Effect(kind="resource", target=npc.id, operation="add", value=-damage, reason="technique damage"),
            Effect(kind="resource", target="player.stamina", operation="add", value=-technique.stamina_cost, reason="technique exertion"),
        ]
        remaining_hp = npc.hp - damage
        hint = f"You use {technique.name} on {npc.name} for {damage} damage."
        if remaining_hp <= 0:
            effects.append(Effect(kind="npc", target=npc.id, operation="set", value=("alive", False), reason="technique kill"))
            effects.append(Effect(kind=PROGRESSION, target="player", operation="xp", value=npc.xp_reward, reason="combat victory reward"))
        elif npc.disposition <= NPC_HOSTILE_DISPOSITION:
            retaliation = max(1, npc.attack_power - state.character.defense)
            effects.append(Effect(kind="resource", target="player.hp", operation="add",
                                  value=-retaliation, reason="hostile npc retaliation"))
            hint += f" The {npc.name} retaliates for {retaliation} damage."
        return RuleResult(effects, hint)
