from engine.parser.intents import parse_input
from engine.rules.basic import ATTACK_DAMAGE, ATTACK_STAMINA_COST
from engine.rules.registry import RuleRegistry


def _resolve(state, text):
    return RuleRegistry().resolve(parse_input(text), state)


def test_movement_valid(demo_state):
    result = _resolve(demo_state, "go forest")
    assert result is not None and len(result.effects) == 1
    assert result.effects[0].value == "forest"


def test_movement_unknown_location(demo_state):
    result = _resolve(demo_state, "go moon")
    assert result is not None and result.effects == []


def test_movement_no_exit(demo_state):
    result = _resolve(demo_state, "go cave")  # village -> cave not direct
    assert result is not None and result.effects == []


def test_take_requires_presence(demo_state):
    result = _resolve(demo_state, "take torch")  # torch is in the cave
    assert result is not None and result.effects == []


def test_attack_wrong_location_blocked_by_rule(demo_state):
    result = _resolve(demo_state, "attack wolf")  # wolf is in forest, player in village
    # Rule BLOCKS the action (blocking outcome, empty effects) rather than
    # delegating to the AI — combat outcomes are always engine-decided (ADR-0001).
    assert result is not None and result.effects == []


def test_attack_in_range(demo_state):
    demo_state.character.location_id = "forest"
    result = _resolve(demo_state, "attack wolf")
    assert result is not None
    kinds = [(e.kind, e.target, e.value) for e in result.effects]
    assert ("resource", "wolf", -ATTACK_DAMAGE) in kinds
    assert ("resource", "player.stamina", -ATTACK_STAMINA_COST) in kinds
    # lethal blow also flags death
    demo_state.world.npcs["wolf"].hp = ATTACK_DAMAGE
    result = _resolve(demo_state, "attack wolf")
    assert any(e.kind == "npc" and e.value == ("alive", False) for e in result.effects)
