import json
from pathlib import Path

from engine.core.game import GameSession
from engine.core.state import CharacterState, GameState, NPCState, RelationshipState, WorldState, QuestState, EventState, ItemState
from engine.npc.encounter import EncounterResolver
from engine.scenario.loader import load_scenario
from engine.scenario.registry import ScenarioRegistry


def _state():
    return GameState(
        character=CharacterState(name="Player", location_id="palace", popularity=10, reputation={"royal": 20}, level=3, realm_id="qi", realm_stage=2),
        world=WorldState(
            locations={"palace": "Palace", "street": "Street"},
            exits={"palace": ["street"], "street": ["palace"]},
            npcs={
                "king": NPCState("king", "King", "palace", hp=100, max_hp=100),
                "guard": NPCState("guard", "Guard", "palace", hp=50, max_hp=50),
            },
            relationships={RelationshipState.canonical_key("player", "king"): RelationshipState("player", "king", affinity=60, trust=40)},
        ),
    )


def test_location_is_hard_presence_gate():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"king": {"id": "king", "presence": [{"location_id": "palace"}]}}
    })
    resolver = EncounterResolver(registry)
    assert resolver.check(state, "king").encounterable
    state.character.location_id = "street"
    assert not resolver.check(state, "king").encounterable


def test_conditions_are_and_gates():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"king": {"id": "king", "encounter_conditions": [
            {"type": "location", "operator": "==", "value": "palace"},
            {"type": "reputation", "key": "royal", "operator": ">=", "value": 10},
            {"type": "popularity", "operator": ">=", "value": 10},
            {"type": "level", "operator": ">=", "value": 3},
            {"type": "realm", "realm_id": "qi", "operator": ">=", "value": 2},
            {"type": "relationship_affinity", "target": "king", "operator": ">=", "value": 50},
        ]}}
    })
    resolver = EncounterResolver(registry)
    assert resolver.check(state, "king").encounterable
    state.character.popularity = 9
    assert not resolver.check(state, "king").encounterable


def test_guard_can_block_until_absent():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"king": {"id": "king", "encounter_conditions": [
            {"type": "npc_absent", "npc_id": "guard"}
        ]}}
    })
    resolver = EncounterResolver(registry)
    assert not resolver.check(state, "king").encounterable
    state.world.npcs["guard"].alive = False
    state.world.npcs["guard"].hp = 0
    assert resolver.check(state, "king").encounterable


def test_look_hides_non_encounterable_npcs_and_talk_is_gated():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"king": {"id": "king", "encounter_conditions": [{"type": "npc_absent", "npc_id": "guard"}]},
                             "guard": {"id": "guard"}}
    })
    session = GameSession(state, scenario_registry=registry)
    assert "King" not in session.handle_input("look")
    assert "Guard" in session.handle_input("look")
    assert "cannot reach" in session.handle_input("talk to king")
    state.world.npcs["guard"].alive = False
    state.world.npcs["guard"].hp = 0
    assert "King" in session.handle_input("look")
    assert "speak" in session.handle_input("talk to king")


def test_attack_cannot_bypass_encounter_gate():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"king": {"id": "king", "encounter_conditions": [{"type": "npc_absent", "npc_id": "guard"}]},
                             "guard": {"id": "guard"}}
    })
    session = GameSession(state, scenario_registry=registry)
    hp = state.world.npcs["king"].hp
    session.handle_input("attack king")
    assert state.world.npcs["king"].hp == hp


def test_presence_turn_window_uses_session_clock():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"king": {"id": "king", "presence": [{"location_id": "palace", "from_turn": 2, "to_turn": 3}]}}
    })
    session = GameSession(state, scenario_registry=registry)
    assert not session.encounter_resolver.check(state, "king").encounterable
    session.clock.turn = 2
    session.encounter_resolver.current_turn = session.clock.turn
    assert session.encounter_resolver.check(state, "king").encounterable
    session.clock.turn = 4
    session.encounter_resolver.current_turn = session.clock.turn
    assert not session.encounter_resolver.check(state, "king").encounterable
