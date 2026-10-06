from contextlib import contextmanager

from engine.ai.schema import parse_structured_response, parse_structured_response_json


@contextmanager
def raises(exc):
    """Local substitute for pytest.raises (suite must run without pytest)."""
    try:
        yield
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} was not raised")


def test_minimal_valid():
    resp = parse_structured_response({"narrative": "ok"})
    assert resp.narrative == "ok" and resp.state_changes == []


def test_unknown_top_level_field_rejected():
    with raises(ValueError):
        parse_structured_response({"narrative": "x", "hidden_truth": "leak"})


def test_missing_narrative_rejected():
    with raises(ValueError):
        parse_structured_response({"state_changes": []})


def test_bad_operation_for_type_rejected():
    with raises(ValueError):
        parse_structured_response({
            "narrative": "x",
            "state_changes": [{"type": "location", "target": "player",
                               "operation": "add", "value": "forest"}],
        })


def test_missing_state_change_field_rejected():
    with raises(ValueError):
        parse_structured_response({
            "narrative": "x",
            "state_changes": [{"type": "resource", "target": "player", "operation": "add"}],
        })


def test_state_changes_wrong_container_type_rejected():
    with raises(ValueError):
        parse_structured_response({"narrative": "x", "state_changes": "move player to forest"})


def test_state_change_item_not_object_rejected():
    with raises(ValueError):
        parse_structured_response({"narrative": "x", "state_changes": ["not a dict"]})


def test_non_dict_top_level_rejected():
    with raises(ValueError):
        parse_structured_response("this is not json at all")
    with raises(ValueError):
        parse_structured_response(None)
    with raises(ValueError):
        parse_structured_response([1, 2, 3])


def test_unhashable_type_field_rejected_safely():
    """A malformed 'type' (e.g. a list) must raise ValueError, not TypeError,
    so it stays inside the adapter retry contract (`except ValueError`)."""
    with raises(ValueError):
        parse_structured_response({
            "narrative": "x",
            "state_changes": [{"type": ["resource"], "target": "player",
                               "operation": "add", "value": 1}],
        })


def test_unhashable_operation_field_rejected_safely():
    with raises(ValueError):
        parse_structured_response({
            "narrative": "x",
            "state_changes": [{"type": "resource", "target": "player",
                               "operation": {"op": "add"}, "value": 1}],
        })


def test_malformed_json_text_rejected_as_value_error():
    with raises(ValueError):
        parse_structured_response_json("{not valid json")
    with raises(ValueError):
        parse_structured_response_json("")
    with raises(ValueError):
        parse_structured_response_json("42")  # valid JSON, not an object


def test_valid_json_text_parses():
    resp = parse_structured_response_json(
        '{"narrative": "The door creaks open.", "state_changes": []}'
    )
    assert resp.narrative == "The door creaks open."


def test_full_payload_roundtrip():
    resp = parse_structured_response({
        "narrative": "The wolf snarls.",
        "state_changes": [{"type": "resource", "target": "player",
                           "operation": "add", "value": -5, "reason": "bite"}],
        "memory_updates": [{"store": "recent", "content": "wolf bite",
                            "visibility": "player", "importance": 3}],
        "npc_changes": [{"npc": "wolf", "field": "disposition", "value": -60}],
        "events_triggered": ["wolf_attack"],
        "available_actions": ["flee", "attack wolf"],
    })
    assert resp.state_changes[0].value == -5
    assert resp.npc_changes[0].field == "disposition"
    assert resp.events_triggered == ["wolf_attack"]

def test_structured_response_rejects_oversized_narrative():
    payload = {
        "narrative": "x" * 4001,
        "state_changes": [], "memory_updates": [], "npc_changes": [],
        "events_triggered": [], "available_actions": [],
    }
    with raises(ValueError):
        parse_structured_response(payload)


def test_structured_response_rejects_effect_flood():
    payload = {
        "narrative": "ok",
        "state_changes": [
            {"type": "resource", "target": "player.stamina", "operation": "add", "value": 1}
        ] * 33,
        "memory_updates": [], "npc_changes": [],
        "events_triggered": [], "available_actions": [],
    }
    with raises(ValueError):
        parse_structured_response(payload)


def test_structured_response_rejects_oversized_memory_content():
    payload = {
        "narrative": "ok", "state_changes": [],
        "memory_updates": [{"store": "recent", "content": "x" * 1001}],
        "npc_changes": [], "events_triggered": [], "available_actions": [],
    }
    with raises(ValueError):
        parse_structured_response(payload)
