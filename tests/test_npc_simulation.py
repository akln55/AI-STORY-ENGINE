from engine.core.state import CharacterState, GameState, NPCState, WorldState
from engine.npc.simulation import NPCSimulationEngine
from engine.scenario.registry import ScenarioRegistry


def registry(schedule):
    return ScenarioRegistry.from_documents({
        "characters.json": {
            "elder": {"id": "elder", "name": "Elder", "schedule": schedule},
        },
    })


def state():
    return GameState(
        character=CharacterState(location_id="village"),
        world=WorldState(
            locations={"village": "Village", "market": "Market", "forest": "Forest"},
            exits={"village": ["market", "forest"], "market": ["village", "forest"], "forest": ["village"]},
            npcs={"elder": NPCState("elder", "Elder", "village")},
        ),
    )


def test_schedule_moves_npc_deterministically():
    engine = NPCSimulationEngine(registry([
        {"from_turn": 1, "to_turn": 2, "location_id": "market"},
        {"from_turn": 3, "to_turn": 4, "location_id": "forest"},
    ]))
    game = state()

    report = engine.advance(game, turn=1)
    assert game.world.npcs["elder"].location_id == "market"
    assert len(report.movements) == 1
    assert report.movements[0].from_location == "village"
    assert report.movements[0].to_location == "market"

    report = engine.advance(game, turn=2)
    assert report.movements == ()

    report = engine.advance(game, turn=3)
    assert game.world.npcs["elder"].location_id == "forest"
    assert report.movements[0].to_location == "forest"


def test_overlapping_schedule_windows_use_later_entry():
    engine = NPCSimulationEngine(registry([
        {"from_turn": 1, "to_turn": 5, "location_id": "market"},
        {"from_turn": 3, "to_turn": 4, "location_id": "forest"},
    ]))
    game = state()
    engine.advance(game, turn=3)
    assert game.world.npcs["elder"].location_id == "forest"


def test_invalid_schedule_destination_does_not_mutate_state():
    engine = NPCSimulationEngine(registry([
        {"from_turn": 1, "to_turn": 2, "location_id": "missing"},
    ]))
    game = state()
    report = engine.advance(game, turn=1)
    assert report.movements == ()
    assert game.world.npcs["elder"].location_id == "village"


def test_registry_rejects_invalid_schedule():
    try:
        registry([{"from_turn": 4, "to_turn": 2, "location_id": "market"}])
    except Exception as exc:
        assert "reversed turn range" in str(exc)
    else:
        raise AssertionError("invalid schedule was accepted")


def test_cyclic_schedule_repeats_across_turns():
    engine = NPCSimulationEngine(registry([
        {"cycle_turns": 4, "from_turn": 0, "to_turn": 1, "location_id": "market"},
        {"cycle_turns": 4, "from_turn": 2, "to_turn": 3, "location_id": "village"},
    ]))
    game = state()

    engine.advance(game, turn=1)
    assert game.world.npcs["elder"].location_id == "market"
    engine.advance(game, turn=2)
    assert game.world.npcs["elder"].location_id == "village"
    engine.advance(game, turn=5)
    assert game.world.npcs["elder"].location_id == "market"
    engine.advance(game, turn=6)
    assert game.world.npcs["elder"].location_id == "village"


def test_registry_rejects_invalid_cyclic_schedule():
    for schedule, message in [
        ([{"cycle_turns": 0, "location_id": "market"}], "cycle_turns must be > 0"),
        ([{"cycle_turns": 4, "from_turn": -1, "location_id": "market"}], "cyclic windows must fit"),
        ([{"cycle_turns": 4, "to_turn": 4, "location_id": "market"}], "cyclic windows must fit"),
    ]:
        try:
            registry(schedule)
        except Exception as exc:
            assert message in str(exc)
        else:
            raise AssertionError("invalid cyclic schedule was accepted")


def test_game_session_advances_cyclic_npc_schedule_through_real_turn_loop():
    from engine.core.game import GameSession
    from engine.core.state import CharacterState, GameState, NPCState, WorldState

    reg = registry([
        {"cycle_turns": 2, "from_turn": 0, "to_turn": 0, "location_id": "market"},
        {"cycle_turns": 2, "from_turn": 1, "to_turn": 1, "location_id": "village"},
    ])
    game = GameSession(
        GameState(
            character=CharacterState(location_id="village"),
            world=WorldState(
                locations={"village": "Village", "market": "Market"},
                exits={"village": ["market"], "market": ["village"]},
                npcs={"elder": NPCState("elder", "Elder", "village")},
            ),
        ),
        scenario_registry=reg,
    )

    game.handle_input("unknown action")
    assert game.clock.turn == 1
    assert game.state.world.npcs["elder"].location_id == "village"
    game.handle_input("unknown action")
    assert game.clock.turn == 2
    assert game.state.world.npcs["elder"].location_id == "market"
