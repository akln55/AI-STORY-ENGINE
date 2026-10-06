from engine.ai.context import assemble_npc_context
from engine.cli import build_session
from engine.demo import build_demo_state
from engine.core.state import RelationshipState
from engine.npc.behavior import NPCBehaviorResolver
from engine.scenario.registry import ScenarioRegistry
from engine.scenario.retrieval import ScenarioRetriever


def test_behavior_context_contains_personality_goals_relationship_and_allowed_actions():
    state = build_demo_state()
    elder = state.world.npcs["elder"]
    elder.goals = []
    state.character.location_id = elder.location_id
    rel = RelationshipState("elder", "player", affinity=40, trust=20)
    state.world.relationships[RelationshipState.canonical_key("elder", "player")] = rel
    ctx = NPCBehaviorResolver().build(state, "elder")
    assert ctx.can_interact
    assert ctx.relationship_affinity == 40
    assert "talk" in ctx.allowed_action_types
    assert ctx.personality["courage"] == 50


def test_non_encounterable_npc_gets_observe_only():
    state = build_demo_state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "elder": {"id": "elder", "encounter_conditions": [
                {"type": "reputation", "key": "royal", "operator": ">=", "value": 100}
            ]}
        }
    })
    resolver = NPCBehaviorResolver(registry=registry)
    ctx = resolver.build(state, "elder")
    assert not ctx.can_interact
    assert ctx.allowed_action_types == ("observe",)


def test_dead_npc_gets_observe_only():
    state = build_demo_state()
    state.world.npcs["elder"].alive = False
    state.world.npcs["elder"].hp = 0
    ctx = NPCBehaviorResolver().build(state, "elder")
    assert not ctx.can_interact
    assert ctx.allowed_action_types == ("observe",)


def test_hostile_npc_behavior_boundary_allows_combat_proposal():
    state = build_demo_state()
    state.character.location_id = state.world.npcs["wolf"].location_id
    state.world.npcs["wolf"].disposition = -80
    ctx = NPCBehaviorResolver().build(state, "wolf")
    assert ctx.can_interact
    assert "attack" in ctx.allowed_action_types


def test_npc_context_uses_scenario_encounter_rules():
    state = build_demo_state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "elder": {"id": "elder", "encounter_conditions": [
                {"type": "reputation", "key": "royal", "operator": ">=", "value": 100}
            ]}
        }
    })
    text = assemble_npc_context(state, "elder", scenario_registry=registry)
    assert "encounterable: False" in text
    assert "allowed_action_types: observe" in text


def test_npc_context_can_include_scoped_canonical_character_data():
    state = build_demo_state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "elder": {
                "id": "elder",
                "faction_id": "village",
                "first_appearance_chapter": 1,
                "speech_style": {"tone": "formal"},
            }
        }
    })
    retriever = ScenarioRetriever(registry)
    text = assemble_npc_context(state, "elder", scenario_registry=registry,
                                scenario_retriever=retriever)
    assert "CANONICAL NPC DATA:" in text
    assert "faction_id: village" in text
