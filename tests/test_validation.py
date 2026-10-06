from engine.core.validation import apply_effects, validate_effect
from engine.core.invariants import check_invariants, InvariantError
from engine.rules.base import Effect


def test_move_to_unknown_location_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("location", "player", "move", "moon"), demo_state)
    assert not ok and "moon" in reason


def test_move_npc_unknown_rejected(demo_state):
    ok, _, _ = validate_effect(Effect("location", "dragon", "move", "forest"), demo_state)
    assert not ok


def test_unreachable_move_rejected(demo_state):
    # village -> cave is not direct
    ok, _, reason = validate_effect(
        Effect("location", "player", "move", "cave"), demo_state)
    assert not ok
    assert "reachable" in reason


def test_reachable_move_accepted(demo_state):
    ok, _, _ = validate_effect(
        Effect("location", "player", "move", "forest"), demo_state)
    assert ok


def test_take_unowned_item_ok_but_owned_rejected(demo_state):
    ok, _, _ = validate_effect(Effect("inventory", "rope", "take", "player"), demo_state)
    assert ok
    demo_state.world.items["rope"].owner = "elder"
    demo_state.world.items["rope"].location_id = None
    ok, _, reason = validate_effect(Effect("inventory", "rope", "take", "player"), demo_state)
    assert not ok and "owned" in reason


def test_remote_take_rejected(demo_state):
    # torch is in cave; player in village
    ok, _, reason = validate_effect(
        Effect("inventory", "torch", "take", "player"), demo_state)
    assert not ok
    assert "not at player location" in reason


def test_unknown_item_rejected(demo_state):
    ok, _, _ = validate_effect(Effect("inventory", "sword", "take", "player"), demo_state)
    assert not ok


def test_resource_clamped(demo_state):
    ok, sanitized, _ = validate_effect(
        Effect("resource", "player", "add", -9999), demo_state)
    assert ok and sanitized == -demo_state.character.hp


def test_resource_unknown_target_rejected(demo_state):
    ok, _, _ = validate_effect(Effect("resource", "dragon", "add", -5), demo_state)
    assert not ok


def test_npc_unknown_field_rejected(demo_state):
    ok, _, _ = validate_effect(Effect("npc", "wolf", "set", ("treasure", 5)), demo_state)
    assert not ok


def test_disposition_out_of_range_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("disposition", 999)), demo_state)
    assert not ok and "disposition" in reason


def test_disposition_in_range_ok(demo_state):
    ok, _, _ = validate_effect(
        Effect("npc", "wolf", "set", ("disposition", -50)), demo_state)
    assert ok


def test_resurrect_dead_npc_rejected(demo_state):
    demo_state.world.npcs["wolf"].alive = False
    demo_state.world.npcs["wolf"].hp = 0
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("alive", True)), demo_state)
    assert not ok
    assert "resurrect" in reason


def test_dead_npc_disposition_rejected(demo_state):
    demo_state.world.npcs["wolf"].alive = False
    demo_state.world.npcs["wolf"].hp = 0
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("disposition", 10)), demo_state)
    assert not ok
    assert "dead" in reason


def test_dead_npc_move_rejected(demo_state):
    demo_state.world.npcs["wolf"].alive = False
    demo_state.world.npcs["wolf"].hp = 0
    ok, _, reason = validate_effect(
        Effect("location", "wolf", "move", "village"), demo_state)
    assert not ok
    assert "dead" in reason


def test_dead_npc_resource_rejected(demo_state):
    demo_state.world.npcs["wolf"].alive = False
    demo_state.world.npcs["wolf"].hp = 0
    ok, _, reason = validate_effect(
        Effect("resource", "wolf", "add", -5), demo_state)
    assert not ok
    assert "dead" in reason


def test_apply_effects_is_only_mutation_path(demo_state):
    report = apply_effects(
        [Effect("location", "player", "move", "forest"),
         Effect("resource", "wolf", "add", -1000)],
        demo_state)
    assert demo_state.character.location_id == "forest"
    assert demo_state.world.npcs["wolf"].hp == 0
    assert demo_state.world.npcs["wolf"].alive is False
    assert report.clean


def test_atomic_batch_rejects_all_on_any_failure(demo_state):
    loc_before = demo_state.character.location_id
    report = apply_effects(
        [Effect("location", "player", "move", "forest"),
         Effect("location", "player", "move", "moon")],  # second invalid
        demo_state)
    assert not report.clean
    assert report.accepted == []
    assert demo_state.character.location_id == loc_before  # unchanged


def test_conflicting_take_drop_batch(demo_state):
    # take then drop same item in one batch — sequential sim should work
    report = apply_effects(
        [Effect("inventory", "rope", "take", "player"),
         Effect("inventory", "rope", "drop", "village")],
        demo_state)
    assert report.clean
    assert "rope" not in demo_state.character.inventory
    assert demo_state.world.items["rope"].location_id == "village"
    assert demo_state.world.items["rope"].owner is None


def test_invariants_hold_after_apply(demo_state):
    apply_effects([Effect("location", "player", "move", "forest")], demo_state)
    check_invariants(demo_state)  # must not raise


def test_invariant_detects_inventory_desync(demo_state):
    demo_state.character.inventory.append("rope")
    # rope still has location, not owner=player
    try:
        check_invariants(demo_state)
        raised = False
    except InvariantError:
        raised = True
    assert raised
