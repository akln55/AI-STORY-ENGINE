from engine.core.game import GameSession
from engine.core.state import CharacterState, GameState, NPCState, WorldState
from engine.core.status import is_action_blocked, tick_status_effects
from engine.core.validation import apply_effects, validate_effect
from engine.rules.base import Effect
from engine.persistence.db import state_from_dict, state_to_dict


def state():
    return GameState(
        character=CharacterState(location_id="village"),
        world=WorldState(
            locations={"village": "Village"},
            exits={"village": []},
            npcs={"wolf": NPCState("wolf", "Wolf", "village", hp=30, max_hp=30)},
        ),
    )


def test_status_add_is_validated_and_persisted():
    game = state()
    report = apply_effects([Effect("status", "player", "add", {"effect_type": "poison", "duration": 3, "potency": 4})], game)
    assert report.clean
    assert game.character.status_effects[0].remaining_turns == 3
    assert game.character.status_effects[0].potency == 4


def test_status_tick_damages_and_expires():
    game = state()
    assert apply_effects([Effect("status", "player", "add", {"effect_type": "poison", "duration": 2, "potency": 5})], game).clean
    start_hp = game.character.hp
    report = tick_status_effects(game, turn=1)
    assert game.character.hp == start_hp - 5
    assert game.character.status_effects[0].remaining_turns == 1
    assert report.applied
    tick_status_effects(game, turn=2)
    assert game.character.hp == start_hp - 10
    assert game.character.status_effects == []


def test_blocking_status_prevents_action():
    game = state()
    assert apply_effects([Effect("status", "player", "add", "stunned")], game).clean
    assert is_action_blocked(game)
    session = GameSession(game)
    assert session.handle_input("go village") == "You are unable to act right now."
    assert session.clock.turn == 1


def test_status_stacking_is_bounded():
    game = state()
    effect = Effect("status", "player", "add", {"effect_type": "poison", "duration": 2, "potency": 2, "stacks": 1, "max_stacks": 2})
    assert apply_effects([effect], game).clean
    assert apply_effects([effect], game).clean
    status = game.character.status_effects[0]
    assert status.stacks == 2
    assert status.max_stacks == 2


def test_unknown_status_rejected():
    ok, _, reason = validate_effect(Effect("status", "player", "add", "teleporting"), state())
    assert not ok and "unknown status" in reason


def test_status_round_trip():
    game = state()
    assert apply_effects([Effect("status", "wolf", "add", {"effect_type": "bleed", "duration": 4, "potency": 3})], game).clean
    payload = state_to_dict(game, 7, [], None)
    restored, turn, recent, memory = state_from_dict(payload)
    status = restored.world.npcs["wolf"].status_effects[0]
    assert turn == 7
    assert status.effect_type == "bleed"
    assert status.remaining_turns == 4
    assert status.potency == 3


def test_status_is_exposed_to_ai_context():
    from engine.ai.context import assemble_context
    game = state()
    assert apply_effects([Effect("status", "player", "add", {"effect_type": "stunned", "duration": 2})], game).clean
    context = assemble_context(game, [], "look")
    assert "stunned" in context
    assert "turns=2" in context
