"""GameSession integration tests, including PROTOTYPE_MVP.md T1/T2/T3 checks."""

from engine.ai.fake import FakeAdapter
from engine.cli import build_session


def test_T1_move_updates_engine_state(session):
    out = session.handle_input("go forest")
    assert session.state.character.location_id == "forest"
    assert "forest" in out.lower()


def test_T2_take_engine_owned_and_fake_item_rejected(session):
    out = session.handle_input("take rope")
    assert "rope" in session.state.character.inventory
    assert session.state.world.items["rope"].owner == "player"

    # Fabricated AI proposal to gain a nonexistent item must be rejected.
    fake = FakeAdapter(handlers={
        "wish": {
            "narrative": "A magic sword appears in your hands!",
            "state_changes": [{"type": "inventory", "target": "sword",
                               "operation": "take", "value": "player"}],
        }
    })
    s = build_session(adapter=fake)
    out = s.handle_input("wish for a sword")
    assert "sword" not in s.state.character.inventory
    assert s.last_report is not None and len(s.last_report.rejected) == 1
    assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())


def test_T3_combat_rule_overrides_ai_narration(session):
    session.handle_input("go forest")
    out = session.handle_input("attack wolf")
    wolf = session.state.world.npcs["wolf"]
    assert wolf.hp == wolf.max_hp - 15  # exact rule damage, regardless of narration
    assert session.state.character.stamina == 90
    assert out  # some player-facing output produced


def test_ai_narrative_only_never_changes_state(session):
    fake = FakeAdapter(handlers={
        "sing": {"narrative": "Your song is beautiful. (+100 HP, says the song.)"},
    })
    s = build_session(adapter=fake)
    hp_before = s.state.character.hp
    out = s.handle_input("sing a song")
    assert s.state.character.hp == hp_before  # narrative claims ignored
    assert "beautiful" in out


def test_meta_commands(session):
    assert "Sleepy Village" in session.handle_input("look")
    assert "carry nothing" in session.handle_input("inventory")
    assert "HP 100/100" in session.handle_input("status")
    assert "Commands" in session.handle_input("help")


def test_quit_stops_loop(session):
    session.handle_input("quit")
    assert not session.running


def test_unknown_location_message(session):
    out = session.handle_input("go moon")
    assert "no place" in out.lower()


def test_attack_requires_stamina(session):
    session.state.character.stamina = 5
    session.handle_input("go forest")
    out = session.handle_input("attack wolf")
    assert "exhausted" in out.lower()
    assert session.state.world.npcs["wolf"].hp == 40  # unchanged


def test_rule_path_logs_actual_player_input(session):
    """Regression: deterministic turns log the player's input, not the narration."""
    out = session.handle_input("go forest")
    assert session.recent_turns == [
        "T1 player: go forest",
        f"T1 outcome: {out}",
    ]


def test_rule_path_log_keeps_raw_input_not_parsed_form(session):
    session.handle_input("head forest")  # synonym parsed as go; raw must be kept
    assert session.recent_turns[0] == "T1 player: head forest"
    assert not any("player: You " in t for t in session.recent_turns)


def test_ai_path_logs_actual_player_input_and_narrative():
    fake = FakeAdapter(handlers={"sing": {"narrative": "Your song echoes."}})
    s = build_session(adapter=fake)
    s.handle_input("sing a song")
    assert s.recent_turns == [
        "T1 player: sing a song",
        "T1 outcome: Your song echoes.",
    ]



def test_unexpected_turn_failure_rolls_back_clock_simulation_status_and_state():
    from engine.ai.adapter_base import AIAdapter
    from engine.core.state import StatusEffectState, CharacterState, GameState, NPCState, WorldState
    from engine.core.game import GameSession
    from engine.scenario.registry import ScenarioRegistry

    class ExplodingAdapter(AIAdapter):
        def generate(self, context):
            raise RuntimeError("provider exploded")

    state = GameState(
        character=CharacterState(location_id="village", hp=100, status_effects=[
            StatusEffectState("poison", remaining_turns=3, potency=5)
        ]),
        world=WorldState(
            locations={"village": "Village", "forest": "Forest"},
            exits={"village": ["forest"], "forest": ["village"]},
            npcs={"elder": NPCState("elder", "Elder", "village")},
        ),
    )
    registry = ScenarioRegistry.from_documents({"characters.json": {
        "elder": {"id": "elder", "schedule": [{"cycle_turns": 2, "from_turn": 0, "to_turn": 0, "location_id": "forest"}]},
    }})
    session = GameSession(state, adapter=ExplodingAdapter(), scenario_registry=registry)
    before = session.state.character.hp
    before_npc = session.state.world.npcs["elder"].location_id

    try:
        session.handle_input("tell me a story")
    except RuntimeError as exc:
        assert str(exc) == "provider exploded"
    else:
        raise AssertionError("expected provider failure")

    assert session.clock.turn == 0
    assert session.state.character.hp == before
    assert session.state.character.status_effects[0].remaining_turns == 3
    assert session.state.world.npcs["elder"].location_id == before_npc
    assert session.recent_turns == []
