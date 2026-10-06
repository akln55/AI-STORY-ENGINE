"""Deterministic, engine-owned temporary status effects."""
from __future__ import annotations

from dataclasses import dataclass

from engine.core.state import GameState, StatusEffectState
from engine.core.validation import apply_effects
from engine.rules.base import Effect


@dataclass(frozen=True)
class StatusTickReport:
    turn: int
    expired: tuple[tuple[str, str], ...] = ()
    applied: tuple[Effect, ...] = ()


# Engine-owned semantics. Scenario data can use these stable IDs without
# inventing arbitrary code through AI responses.
STATUS_DAMAGE = {"poison", "bleed", "burn"}
STATUS_HEAL = {"regeneration"}
STATUS_STAMINA = {"stamina_regen"}
STATUS_BLOCKING = {"stunned", "rooted"}
KNOWN_STATUS_EFFECTS = frozenset(
    STATUS_DAMAGE | STATUS_HEAL | STATUS_STAMINA | STATUS_BLOCKING
)


def is_action_blocked(state: GameState) -> bool:
    return any(
        effect.effect_type in STATUS_BLOCKING and effect.remaining_turns > 0
        for effect in state.character.status_effects
    )


def tick_status_effects(state: GameState, *, turn: int) -> StatusTickReport:
    """Apply one deterministic tick and remove expired effects.

    All runtime mutations go through ``apply_effects``. Expiration and damage
    therefore participate in the same validation/invariant boundary as normal
    gameplay effects.
    """
    effects: list[Effect] = []
    expired: list[tuple[str, str]] = []

    for target_id, statuses in _iter_targets(state):
        for status in list(statuses):
            if status.remaining_turns <= 0:
                expired.append((target_id, status.effect_type))
                effects.append(Effect("status", target_id, "remove", status.effect_type, "status expired"))
                continue
            delta = _tick_delta(status)
            if delta:
                resource = "stamina" if status.effect_type in STATUS_STAMINA else "hp"
                effects.append(Effect("resource", target_id + "." + resource, "add", delta, "status tick"))
            if status.remaining_turns == 1:
                expired.append((target_id, status.effect_type))
                effects.append(Effect("status", target_id, "remove", status.effect_type, "status expired"))
            else:
                effects.append(Effect("status", target_id, "tick", status.effect_type, "status duration tick"))

    if not effects:
        return StatusTickReport(turn)
    report = apply_effects(effects, state)
    if not report.clean:
        return StatusTickReport(turn)
    return StatusTickReport(turn, tuple(expired), tuple(report.accepted))


def _tick_delta(status: StatusEffectState) -> int:
    if status.effect_type in STATUS_DAMAGE:
        return -max(1, status.potency * status.stacks)
    if status.effect_type in STATUS_HEAL:
        return max(1, status.potency * status.stacks)
    if status.effect_type in STATUS_STAMINA:
        return max(1, status.potency * status.stacks)
    return 0


def _iter_targets(state: GameState):
    yield "player", state.character.status_effects
    for npc_id, npc in state.world.npcs.items():
        if npc.alive:
            yield npc_id, npc.status_effects
