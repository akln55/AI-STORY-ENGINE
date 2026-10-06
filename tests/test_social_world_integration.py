from engine.ai.context import assemble_context
from engine.ai.schema import parse_structured_response
from engine.core.state import CharacterState, GameState, NPCState, QuestState, QuestObjective, RelationshipState, WorldState
from engine.core.validation import apply_effects
from engine.memory.system import MemorySystem
from engine.npc.encounter import EncounterResolver
from engine.rules.base import Effect
from engine.rules.basic import AcceptQuestRule
from engine.parser.intents import parse_input
from engine.scenario.registry import ScenarioRegistry


def make_state():
    world = WorldState(
        locations={"village": "Village"}, exits={"village": []},
        npcs={"elder": NPCState(id="elder", name="Elder", location_id="village")},
        relationships={"elder|player": RelationshipState("elder", "player")},
        quests={
            "q": QuestState(
                id="q", title="Secret", status="available",
                prerequisites=[{"type": "relationship_flag", "target": "elder", "flag": "trusted"}],
                objectives=[QuestObjective("o", "talk", "talk", "elder")],
            )
        },
    )
    return GameState(CharacterState(location_id="village"), world)


def test_reputation_effect_is_bounded_and_persistent_in_state():
    state = make_state()
    report = apply_effects([Effect("reputation", "faction:royal", "add", 150)], state)
    assert report.clean
    assert state.character.reputation["royal"] == 100
    report = apply_effects([Effect("reputation", "faction:royal", "add", -250)], state)
    assert report.clean
    assert state.character.reputation["royal"] == -100


def test_relationship_flag_controls_encounter_and_quest_prerequisite():
    state = make_state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"elder": {"id": "elder", "name": "Elder", "encounter_conditions": [
            {"type": "relationship_flag", "target": "elder", "flag": "trusted"}
        ]}},
    })
    assert not EncounterResolver(registry).check(state, "elder").encounterable
    assert not AcceptQuestRule().resolve(parse_input("accept q"), state).effects
    state.world.relationships["elder|player"].flags.append("trusted")
    assert EncounterResolver(registry).check(state, "elder").encounterable
    result = AcceptQuestRule().resolve(parse_input("accept q"), state)
    assert result is not None and result.effects[0].operation == "activate"


def test_ai_context_exposes_reputation_and_relationship_flags():
    state = make_state()
    state.character.reputation["royal"] = 25
    state.world.relationships["elder|player"].flags.append("trusted")
    text = assemble_context(state, [], "talk to elder", memory=MemorySystem(), current_turn=1)
    assert "reputation={'royal': 25}" in text
    assert "elder:affinity=0,trust=0,flags=['trusted']" in text


def test_structured_response_accepts_reputation_state_change():
    response = parse_structured_response({
        "narrative": "The herald recognizes your standing.",
        "state_changes": [{"type": "reputation", "target": "faction:royal", "operation": "add", "value": 5}],
        "memory_updates": [], "npc_changes": [], "events_triggered": [], "available_actions": [],
    })
    assert response.state_changes[0].type == "reputation"
