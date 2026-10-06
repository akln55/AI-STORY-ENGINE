from engine.core.state import CharacterState, EventState, GameState, WorldState
from engine.events import EventEngine
from engine.scenario.configuration import ScenarioConfiguration
from engine.scenario.registry import ScenarioRegistry


def _state():
    return GameState(CharacterState(location_id="village"), WorldState(
        locations={"village": "Village", "forest": "Forest"},
        exits={"village": ["forest"]},
        events={"arrival": EventState("arrival", "story")},
    ))


def test_event_engine_triggers_by_location():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "events.json": {"arrival": {"id": "arrival", "type": "story",
            "trigger_conditions": [{"type": "location", "operator": "==", "value": "village"}]}}
    })
    result = EventEngine(registry).evaluate(state, turn=4)
    assert result[0].triggered
    assert state.world.events["arrival"].status == "active"
    assert state.world.events["arrival"].start_turn == 4


def test_event_engine_requires_all_conditions():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "events.json": {"arrival": {"id": "arrival", "type": "story",
            "trigger_conditions": [{"type": "location", "value": "village"}, {"type": "level", "operator": ">=", "value": 2}]}}
    })
    assert EventEngine(registry).evaluate(state, turn=1) == ()
    assert state.world.events["arrival"].status == "inactive"


def test_event_engine_applies_valid_scenario_effects():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "events.json": {"arrival": {"id": "arrival", "type": "story",
            "trigger_conditions": [{"type": "location", "value": "village"}],
            "effects": [{"kind": "resource", "target": "player.hp", "operation": "set", "value": 70}]}}
    })
    assert EventEngine(registry).evaluate(state, turn=2)[0].triggered
    assert state.character.hp == 70


def test_event_engine_rejects_invalid_effect_atomically():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "events.json": {"arrival": {"id": "arrival", "type": "story",
            "trigger_conditions": [{"type": "location", "value": "village"}],
            "effects": [{"kind": "resource", "target": "player.hp", "operation": "set", "value": 70},
                        {"kind": "resource", "target": "missing.hp", "operation": "set", "value": 1}]}}
    })
    result = EventEngine(registry).evaluate(state, turn=2)
    assert not result[0].triggered
    assert state.character.hp == 100
    assert state.world.events["arrival"].status == "inactive"


def test_event_engine_chapter_condition():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "events.json": {"arrival": {"id": "arrival", "type": "story",
            "trigger_conditions": [{"type": "chapter", "operator": ">=", "value": 5}]}}
    })
    cfg = ScenarioConfiguration("demo", "1", "sequential", ("p1",), 1, 4)
    assert EventEngine(registry).evaluate(state, turn=1, configuration=cfg) == ()


def test_event_engine_can_advance_scenario_chapter():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "events.json": {"arrival": {"id": "arrival", "type": "story",
            "trigger_conditions": [{"type": "location", "value": "village"}],
            "advance_chapter_to": 5}}
    })
    cfg = ScenarioConfiguration("demo", "1", "sequential", ("p1",), 1, 1)
    result = EventEngine(registry).evaluate(state, turn=2, configuration=cfg)
    assert result[0].new_chapter == 5
