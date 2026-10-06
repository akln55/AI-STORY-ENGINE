from pathlib import Path
import tempfile

from engine.ai.fake import FakeAdapter
from engine.core.game import GameSession
from engine.core.state import CharacterState, GameState, NPCState, QuestState, QuestObjective, WorldState
from engine.core.validation import apply_effects
from engine.parser.intents import parse_input
from engine.rules.base import Effect
from engine.events import EventEngine
from engine.scenario.registry import ScenarioRegistry


def state():
    return GameState(
        CharacterState(location_id="inn", level=2),
        WorldState(
            locations={"inn":"Inn", "street":"Street"},
            exits={"inn":["street"], "street":["inn"]},
            npcs={"elder":NPCState("elder", "Elder", "inn")},
            quests={
                "intro": QuestState("intro", "Meet Elder", status="available",
                    prerequisites=[{"type":"level","operator":">=","value":2}],
                    objectives=[QuestObjective("talk","Talk","talk","elder")]),
            },
        ),
    )


def test_relationship_flags_are_accepted_by_structured_ai():
    fake=FakeAdapter(handlers={"promise": {"narrative":"A promise is made.","state_changes":[{"type":"relationship","target":"player|elder","operation":"flag_add","value":"promise"}]}})
    s=GameSession(state(), adapter=fake)
    s.handle_input("promise")
    assert "promise" in s.state.world.get_relationship("player","elder").flags


def test_dialogue_cannot_mutate_unrelated_npc():
    st=state(); st.world.npcs["guard"]=NPCState("guard","Guard","inn")
    fake=FakeAdapter(handlers={"talk to elder": {"narrative":"hello","npc_changes":[{"npc":"guard","field":"disposition","value":-100}]}})
    s=GameSession(st, adapter=fake)
    s.handle_input("talk to elder")
    assert st.world.npcs["guard"].disposition == 0


def test_accept_and_abandon_quest_are_engine_rules():
    st=state(); s=GameSession(st)
    assert parse_input("accept intro").action == "accept"
    out=s.handle_input("accept intro")
    assert st.world.quests["intro"].status == "active"
    assert "accept" in out.lower()
    s.handle_input("abandon intro")
    assert st.world.quests["intro"].status == "abandoned"


def test_quest_prerequisite_blocks_acceptance():
    st=state(); st.character.level=1; s=GameSession(st)
    s.handle_input("accept intro")
    assert st.world.quests["intro"].status == "available"


def test_event_cascade_can_trigger_dependency_in_same_turn():
    st=state(); st.world.events.update({
        "a": __import__('engine.core.state',fromlist=['EventState']).EventState("a","story"),
        "b": __import__('engine.core.state',fromlist=['EventState']).EventState("b","story"),
    })
    reg=ScenarioRegistry.from_documents({"events.json":{
        "a":{"id":"a","type":"story","trigger_conditions":[{"type":"location","value":"inn"}],"effects":[]},
        "b":{"id":"b","type":"story","trigger_conditions":[{"type":"event","id":"a","operator":"==","value":"active"}],"effects":[]},
    }})
    result=EventEngine(reg).evaluate(st,turn=1)
    assert {r.event_id for r in result if r.triggered} == {"a","b"}


def test_available_actions_are_player_visible():
    fake=FakeAdapter(handlers={"free action": {"narrative":"Done","available_actions":["look","talk to elder"]}})
    s=GameSession(state(), adapter=fake)
    out=s.handle_input("free action")
    assert "Available actions:" in out
    assert "talk to elder" in out


def test_hostile_npc_retaliates_through_game_session():
    st=state()
    st.world.npcs["elder"].hp=40
    st.world.npcs["elder"].max_hp=40
    st.world.npcs["elder"].attack_power=6
    st.world.npcs["elder"].disposition=-50
    s=GameSession(st)
    out=s.handle_input("attack elder")
    assert "retaliates" in out
    assert st.character.hp == 94
    assert st.world.npcs["elder"].hp == 25


def test_player_defeat_locks_ordinary_gameplay_until_recovery():
    from engine.core.state import CharacterState, GameState, WorldState, NPCState
    from engine.core.game import GameSession

    state = GameState(
        character=CharacterState(location_id="camp", hp=0, max_hp=100),
        world=WorldState(
            locations={"camp": "Camp", "road": "Road"},
            exits={"camp": ["road"]},
            npcs={"guard": NPCState("guard", "Guard", "camp", hp=50, max_hp=50)},
        ),
    )
    session = GameSession(state)
    assert session.is_defeated
    turn = session.clock.turn
    assert "DEFEATED" in session.handle_input("status")
    assert session.handle_input("go road").startswith("You are defeated.")
    assert session.handle_input("attack guard").startswith("You are defeated.")
    assert session.clock.turn == turn
    assert state.character.location_id == "camp"
    assert state.world.npcs["guard"].hp == 50


def test_lethal_retaliation_enters_defeated_phase():
    from engine.core.game import GameSession
    from engine.core.state import CharacterState, GameState, NPCState, WorldState
    from engine.rules.basic import AttackRule
    from engine.parser.intents import parse_input
    from engine.core.validation import apply_effects

    state = GameState(
        character=CharacterState(location_id="camp", hp=3, max_hp=100, defense=0),
        world=WorldState(
            locations={"camp": "Camp"},
            npcs={"goblin": NPCState("goblin", "Goblin", "camp", hp=30, max_hp=30, attack_power=5, disposition=-50)},
        ),
    )
    result = AttackRule().resolve(parse_input("attack goblin"), state)
    assert result is not None
    assert apply_effects(result.effects, state).clean
    session = GameSession(state)
    assert session.is_defeated
    assert state.character.hp == 0


def test_defeat_phase_survives_save_load(tmp_path):
    from engine.core.game import GameSession
    from engine.core.state import CharacterState, GameState, WorldState
    from engine.persistence.saves import load_session, save_session

    state = GameState(
        character=CharacterState(location_id="camp", hp=0, max_hp=100),
        world=WorldState(locations={"camp": "Camp"}),
    )
    session = GameSession(state)
    save_session(session, slot="dead", save_dir=tmp_path)
    restored = load_session(slot="dead", save_dir=tmp_path)
    assert restored.is_defeated
    assert restored.state.character.hp == 0


def test_defeat_recovery_restores_pre_lethal_turn():
    from engine.core.game import GameSession
    from engine.core.state import CharacterState, GameState, NPCState, WorldState

    state = GameState(
        character=CharacterState(location_id="camp", hp=4, max_hp=100, attack_power=20),
        world=WorldState(
            locations={"camp": "Camp"},
            npcs={"goblin": NPCState("goblin", "Goblin", "camp", hp=30, max_hp=30, attack_power=5, disposition=-50)},
        ),
    )
    session = GameSession(state)
    session.handle_input("attack goblin")
    assert session.is_defeated
    assert session.clock.turn == 1
    assert session.can_recover
    out = session.handle_input("recover")
    assert "Recovery complete" in out
    assert not session.is_defeated
    assert session.state.character.hp == 4
    assert session.state.world.npcs["goblin"].hp == 30
    assert session.clock.turn == 0
    assert not session.can_recover


def test_persisted_defeat_recovery_survives_save_load(tmp_path):
    from engine.core.game import GameSession
    from engine.core.state import CharacterState, GameState, NPCState, WorldState
    from engine.persistence.saves import load_session, save_session

    state = GameState(
        character=CharacterState(location_id="camp", hp=4, max_hp=100, attack_power=20),
        world=WorldState(
            locations={"camp": "Camp"},
            npcs={"goblin": NPCState("goblin", "Goblin", "camp", hp=30, max_hp=30, attack_power=5, disposition=-50)},
        ),
    )
    session = GameSession(state)
    session.handle_input("attack goblin")
    assert session.is_defeated and session.can_recover
    save_session(session, slot="defeat", save_dir=tmp_path)

    restored = load_session(slot="defeat", save_dir=tmp_path)
    assert restored.is_defeated
    assert restored.can_recover
    assert restored.handle_input("recover").startswith("Recovery complete")
    assert restored.state.character.hp == 4
    assert restored.state.world.npcs["goblin"].hp == 30
    assert restored.clock.turn == 0
