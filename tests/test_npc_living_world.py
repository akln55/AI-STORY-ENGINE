from engine.core.state import CharacterState, GameState, NPCGoal, NPCState, RelationshipState, WorldState
from engine.memory.system import MemorySystem
from engine.npc.simulation import NPCSimulationEngine
from engine.scenario.registry import ScenarioRegistry


def make_world(goals_a=None, goals_b=None):
    registry = ScenarioRegistry.from_documents({"characters.json": {
        "alice": {"id": "alice", "goals": goals_a or []},
        "bob": {"id": "bob", "goals": goals_b or []},
    }})
    state = GameState(
        character=CharacterState(location_id="village"),
        world=WorldState(
            locations={"village":"Village", "market":"Market", "forest":"Forest"},
            exits={"village":["market","forest"], "market":["village","forest"], "forest":["village"]},
            npcs={
                "alice": NPCState("alice", "Alice", "village", personality=__import__('engine.core.state', fromlist=['NPCPersonality']).NPCPersonality(sociability=80)),
                "bob": NPCState("bob", "Bob", "market"),
            },
            relationships={RelationshipState.canonical_key("alice","bob"): RelationshipState("alice","bob", trust=60)},
        ),
    )
    if goals_a:
        state.world.npcs["alice"].goals = [NPCGoal(
            id=g["id"], description=g["description"], priority=g["priority"],
            kind=g.get("kind", "passive"), target_id=g.get("target_id"),
            target_location=g.get("target_location"), required_progress=g.get("required_progress", 1),
            data=dict(g.get("data") or {}),
        ) for g in goals_a]
    if goals_b:
        state.world.npcs["bob"].goals = [NPCGoal(
            id=g["id"], description=g["description"], priority=g["priority"], kind=g.get("kind", "passive"),
            target_id=g.get("target_id"), target_location=g.get("target_location"),
            required_progress=g.get("required_progress", 1), data=dict(g.get("data") or {}),
        ) for g in goals_b]
    return state, registry


def test_move_goal_executes_and_completes():
    state, registry = make_world(goals_a=[{"id":"go","description":"Go market","priority":10,"kind":"move_to","target_location":"market"}])
    report = NPCSimulationEngine(registry).advance(state, turn=1)
    assert state.world.npcs["alice"].location_id == "market"
    assert report.goal_actions and report.goal_actions[0].goal_id == "go"
    assert state.world.npcs["alice"].goals[0].status == "completed"


def test_goal_priority_is_deterministic():
    state, registry = make_world(goals_a=[
        {"id":"low","description":"forest","priority":1,"kind":"move_to","target_location":"forest"},
        {"id":"high","description":"market","priority":9,"kind":"move_to","target_location":"market"},
    ])
    NPCSimulationEngine(registry).advance(state, turn=1)
    assert state.world.npcs["alice"].location_id == "market"
    assert state.world.npcs["alice"].goals[1].status == "completed"


def test_meet_goal_follows_target_location():
    state, registry = make_world(goals_a=[{"id":"meet","description":"Meet Bob","priority":5,"kind":"meet_npc","target_id":"bob"}])
    NPCSimulationEngine(registry).advance(state, turn=1)
    assert state.world.npcs["alice"].location_id == "market"
    NPCSimulationEngine(registry).advance(state, turn=2)
    assert state.world.npcs["alice"].goals[0].status == "completed"


def test_patrol_progress_is_persistent():
    state, registry = make_world(goals_a=[{"id":"patrol","description":"Patrol","priority":5,"kind":"patrol","required_progress":2,"data":{"locations":["market","forest"]}}])
    engine = NPCSimulationEngine(registry)
    engine.advance(state, turn=1)
    assert state.world.npcs["alice"].location_id == "market"
    engine.advance(state, turn=2)
    assert state.world.npcs["alice"].location_id == "forest"
    assert state.world.npcs["alice"].goals[0].progress >= 1


def test_trusted_colocated_npcs_share_nonsecret_knowledge():
    state, registry = make_world()
    state.world.npcs["alice"].location_id = "market"
    memory = MemorySystem()
    memory.add("knowledge", "The gate closes at dusk", visibility="npc:alice", importance=50, created_turn=1, tags=["world"])
    transfers = NPCSimulationEngine(registry).advance(state, turn=1, memory=memory).knowledge_transfers
    assert transfers
    assert any(r.visibility == "npc:bob" and "gate closes" in r.content for r in memory.all_records())


def test_secret_knowledge_does_not_propagate():
    state, registry = make_world()
    state.world.npcs["alice"].location_id = "market"
    memory = MemorySystem()
    memory.add("knowledge", "Hidden identity", visibility="npc:alice", importance=90, created_turn=1, tags=["secret"])
    NPCSimulationEngine(registry).advance(state, turn=1, memory=memory)
    assert not any(r.visibility == "npc:bob" and "Hidden identity" in r.content for r in memory.all_records())


def test_untrusted_npcs_do_not_share_knowledge():
    state, registry = make_world()
    state.world.relationships["alice|bob"].trust = 10
    state.world.npcs["alice"].location_id = "market"
    memory = MemorySystem()
    memory.add("knowledge", "Private plan", visibility="npc:alice", importance=50, created_turn=1)
    NPCSimulationEngine(registry).advance(state, turn=1, memory=memory)
    assert not any(r.visibility == "npc:bob" and "Private plan" in r.content for r in memory.all_records())


def test_legacy_goal_without_execution_metadata_remains_passive():
    state, registry = make_world()
    state.world.npcs["alice"].goals = [NPCGoal("legacy", "Legacy goal", 10)]
    report = NPCSimulationEngine(registry).advance(state, turn=1)
    assert report.goal_actions == ()


def test_talk_reaction_changes_relationship_deterministically():
    from engine.npc.reactions import NPCReactionEngine
    state, _ = make_world()
    effects = NPCReactionEngine().effects_for_player_interaction(state, "alice", outcome="talk")
    from engine.core.validation import apply_effects
    report = apply_effects(list(effects), state)
    assert report.clean
    rel = state.world.get_relationship("player", "alice")
    assert rel is not None and rel.affinity == 1 and rel.trust == 1


def test_invalid_goal_kind_rejected_by_scenario_registry():
    try:
        ScenarioRegistry.from_documents({"characters.json": {"alice": {
            "id":"alice", "goals":[{"id":"x","description":"x","priority":1,"kind":"teleport"}]
        }}})
        raise AssertionError("invalid goal kind was accepted")
    except Exception as exc:
        assert "unsupported kind" in str(exc)


def test_goal_target_reference_is_checked_by_invariants():
    from engine.core.invariants import InvariantError, check_invariants
    state, _ = make_world()
    state.world.npcs["alice"].goals = [NPCGoal(
        "meet", "Meet nobody", 1, kind="meet_npc", target_id="ghost"
    )]
    try:
        check_invariants(state)
        raise AssertionError("invalid goal target was accepted")
    except InvariantError as exc:
        assert "unknown npc" in str(exc)


def test_npc_simulation_1000_turn_determinism():
    goals = [{"id":"patrol","description":"Patrol","priority":5,"kind":"patrol","required_progress":5000,"data":{"locations":["market","forest"]}}]
    state_a, registry = make_world(goals_a=goals)
    state_b, _ = make_world(goals_a=goals)
    engine_a = NPCSimulationEngine(registry)
    engine_b = NPCSimulationEngine(registry)
    for turn in range(1, 1001):
        engine_a.advance(state_a, turn=turn)
        engine_b.advance(state_b, turn=turn)
    assert state_a.world.npcs["alice"].location_id == state_b.world.npcs["alice"].location_id
    assert state_a.world.npcs["alice"].goals[0].progress == state_b.world.npcs["alice"].goals[0].progress
