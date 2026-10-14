from engine.core.game import GameSession
from engine.scenario.context import ScenarioContext
from engine.scenario.loader import load_scenario
from engine.scenario.errors import ScenarioError


def test_context_bundles_one_pack_configuration():
    pack = load_scenario("scenarios/demo-bootstrap")
    context = ScenarioContext.from_pack(pack)
    assert context.registry is pack.registry
    assert context.retriever is pack.retriever
    assert context.configuration.scenario_id == pack.scenario_id
    assert context.configuration.scenario_version == pack.version


def test_context_rejects_mismatched_configuration():
    pack = load_scenario("scenarios/demo-bootstrap")
    config = ScenarioContext.from_pack(pack).configuration
    bad = config.__class__("other", config.scenario_version, config.mode, config.selected_pack_ids, config.start_chapter, config.current_chapter)
    try:
        ScenarioContext(pack, bad)
    except ScenarioError:
        pass
    else:
        raise AssertionError("mismatched scenario context must be rejected")


def test_session_factory_wires_complete_scenario_context():
    pack = load_scenario("scenarios/demo-bootstrap")
    session = GameSession.from_scenario_pack(pack)
    assert session.scenario_registry is pack.registry
    assert session.scenario_retriever is pack.retriever
    assert session.scenario_configuration.scenario_id == pack.scenario_id
    assert session.state.world.locations


def test_game_session_rejects_partial_scenario_composition():
    from engine.core.game import GameSession
    from engine.core.state import CharacterState, GameState, WorldState
    from engine.scenario.registry import ScenarioRegistry

    state = GameState(CharacterState(location_id="village"), WorldState(locations={"village": "Village"}))
    registry = ScenarioRegistry.from_documents({"characters.json": {}})
    try:
        GameSession(state, scenario_registry=registry, scenario_configuration=object())
    except ValueError as exc:
        assert "scenario_retriever" in str(exc)
    else:
        raise AssertionError("partial scenario composition must be rejected")


def test_runtime_context_includes_world_simulation_contract():
    from engine.ai.context import assemble_context

    pack = load_scenario("scenarios/demo-bootstrap")
    context = assemble_context(
        pack.build_state(),
        recent_turns=[],
        player_input="Look around",
        scenario_retriever=pack.retriever,
        scenario_configuration=ScenarioContext.from_pack(pack).configuration,
        scenario_registry=pack.registry,
        current_turn=1,
    )
    assert "GAMEPLAY BEHAVIOUR CONTRACT:" in context
    assert "Never teleport the player, NPCs, or items" in context
    assert "Do not force a future event when its conditions no longer hold" in context
    assert "the engine accepts" in context
