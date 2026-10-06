"""Deterministic quest lifecycle and transaction system.

Quest state is authoritative. AI does not directly mutate quests. Objective
progress is derived from authoritative GameState, rewards are applied
atomically, deadlines can fail active quests, and completion/failure can unlock
follow-up quests without granting narrative text authority over state.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from engine.core.state import GameState, QuestState
from engine.core.validation import apply_effects
from engine.rules.base import Effect

QUEST_STATUSES = frozenset({"available", "active", "completed", "failed", "abandoned"})
OBJECTIVE_TYPES = frozenset({"collect", "reach", "defeat", "talk"})


@dataclass(frozen=True)
class QuestEvaluation:
    changed_quest_ids: tuple[str, ...] = ()
    completed_quest_ids: tuple[str, ...] = ()
    failed_quest_ids: tuple[str, ...] = ()
    activated_quest_ids: tuple[str, ...] = ()


def evaluate_objective(state: GameState, objective, *, talked_to: str | None = None) -> int | None:
    """Return authoritative progress for an objective, or None if not automatic."""
    if objective.type == "collect":
        return sum(1 for item_id in state.character.inventory if item_id == objective.target_id)
    if objective.type == "reach":
        return int(state.character.location_id == objective.target_id)
    if objective.type == "defeat":
        npc = state.world.npcs.get(objective.target_id)
        return int(npc is not None and not npc.alive)
    if objective.type == "talk":
        return int(talked_to == objective.target_id)
    return None


def evaluate_quests(
    state: GameState,
    *,
    talked_to: str | None = None,
    current_turn: int | None = None,
) -> QuestEvaluation:
    """Reconcile active quests and atomically apply lifecycle consequences."""
    changed: list[str] = []
    completed: list[str] = []
    failed: list[str] = []
    activated: list[str] = []

    # Process failures before completion so an expired quest can never complete
    # on the same reconciliation pass.
    for quest in list(state.world.quests.values()):
        if quest.status != "active" or current_turn is None:
            continue
        if quest.expires_turn is not None and current_turn > quest.expires_turn:
            snapshot = copy.deepcopy(state)
            quest.status = "failed"
            quest.failed_turn = current_turn
            try:
                _unlock_quests(state, quest.unlocks_on_fail, activated, current_turn)
                changed.append(quest.id)
                failed.append(quest.id)
            except Exception:
                _restore_state(state, snapshot)

    for quest in list(state.world.quests.values()):
        if quest.status != "active":
            continue
        quest_changed = False
        all_complete = bool(quest.objectives)
        for objective in quest.objectives:
            if objective.completed:
                continue
            progress = evaluate_objective(state, objective, talked_to=talked_to)
            if progress is None:
                all_complete = False
                continue
            new_progress = min(max(progress, 0), objective.required_count)
            if new_progress != objective.current_count:
                objective.current_count = new_progress
                quest_changed = True
            if objective.current_count >= objective.required_count:
                objective.completed = True
                quest_changed = True
            if not objective.completed:
                all_complete = False

        if all_complete:
            snapshot = copy.deepcopy(state)
            reward_effects = _reward_effects(quest)
            report = apply_effects(reward_effects, state) if reward_effects else None
            if report is not None and not report.clean:
                _restore_state(state, snapshot)
                continue
            quest.status = "completed"
            quest.rewards_claimed = True
            quest.completed_turn = current_turn
            quest_changed = True
            try:
                _unlock_quests(state, quest.unlocks_on_complete, activated, current_turn)
            except Exception:
                _restore_state(state, snapshot)
                continue
            completed.append(quest.id)

        if quest_changed:
            changed.append(quest.id)

    return QuestEvaluation(tuple(dict.fromkeys(changed)), tuple(completed), tuple(failed), tuple(activated))


def activate_quest(state: GameState, quest_id: str, *, current_turn: int | None = None) -> None:
    """Convenience API for engine/tests; enforce the same prerequisite vocabulary."""
    quest = state.world.quests[quest_id]
    if quest.status != "available":
        raise ValueError(f"cannot activate quest '{quest_id}' from status '{quest.status}'")
    if not _prerequisites_met(state, quest):
        raise ValueError(f"cannot activate quest '{quest_id}': prerequisites not met")
    quest.status = "active"
    quest.started_turn = current_turn
    evaluate_quests(state, current_turn=current_turn)


def abandon_quest(state: GameState, quest_id: str) -> None:
    quest = state.world.quests[quest_id]
    if quest.status != "active":
        raise ValueError(f"cannot abandon quest '{quest_id}' from status '{quest.status}'")
    quest.status = "abandoned"


def _unlock_quests(state: GameState, quest_ids: list[str], activated: list[str], current_turn: int | None) -> None:
    for quest_id in quest_ids:
        quest = state.world.quests.get(quest_id)
        if quest is None or quest.status != "available" or not _prerequisites_met(state, quest):
            continue
        report = apply_effects([Effect("quest", quest_id, "activate", True, "quest chain unlock")], state)
        if not report.clean:
            continue
        quest.started_turn = current_turn
        activated.append(quest_id)


def _prerequisites_met(state: GameState, quest: QuestState) -> bool:
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
            ok = (req.get("realm_id") is None or state.character.realm_id == req.get("realm_id")) and compare(state.character.realm_stage, req.get("operator", ">="), req.get("value"))
        elif kind == "item":
            present = state.character.has_item(str(req.get("item_id", "")))
            ok = present if "operator" not in req else compare(present, req["operator"], req.get("value", True))
        elif kind == "relationship_flag":
            target, flag = req.get("target"), req.get("flag")
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


def _restore_state(live: GameState, snapshot: GameState) -> None:
    live.character = snapshot.character
    live.world = snapshot.world


def _reward_effects(quest: QuestState) -> list[Effect]:
    """Convert the deterministic reward vocabulary into engine effects."""
    effects: list[Effect] = []
    for reward in quest.rewards:
        if not isinstance(reward, dict):
            continue
        kind = reward.get("type")
        if kind == "xp":
            amount = reward.get("amount", reward.get("value"))
            if isinstance(amount, int) and amount >= 0:
                effects.append(Effect("progression", "player", "xp", amount, f"quest reward: {quest.id}"))
        elif kind == "resource":
            target = reward.get("target", "player.hp")
            amount = reward.get("amount", reward.get("value"))
            operation = reward.get("operation", "add")
            if isinstance(target, str) and isinstance(amount, int) and operation in {"add", "set"}:
                effects.append(Effect("resource", target, operation, amount, f"quest reward: {quest.id}"))
        elif kind == "relationship":
            target = reward.get("target")
            field = reward.get("field", "affinity")
            amount = reward.get("amount", reward.get("value"))
            operation = reward.get("operation", "add")
            if isinstance(target, str) and isinstance(field, str) and isinstance(amount, int) and operation in {"add", "set"}:
                effects.append(Effect("relationship", target, operation, (field, amount), f"quest reward: {quest.id}"))
            elif isinstance(target, str) and isinstance(reward.get("flag"), str) and operation in {"flag_add", "flag_remove"}:
                effects.append(Effect("relationship", target, operation, reward["flag"], f"quest reward: {quest.id}"))
        elif kind == "reputation":
            faction_id = reward.get("faction_id", reward.get("target"))
            amount = reward.get("amount", reward.get("value"))
            operation = reward.get("operation", "add")
            if isinstance(faction_id, str) and isinstance(amount, int) and operation in {"add", "set"}:
                effects.append(Effect("reputation", f"faction:{faction_id}", operation, amount, f"quest reward: {quest.id}"))
    return effects
