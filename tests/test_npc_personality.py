"""v1.3: NPC personality, goals, fears/preferences — validation, invariants,
persistence, AI mutation gate, and per-NPC context assembly.
"""

from engine.ai.context import assemble_npc_context
from engine.ai.fake import FakeAdapter
from engine.cli import build_session
from engine.core.invariants import InvariantError, check_invariants
from engine.core.state import NPCGoal, NPCPersonality
from engine.core.validation import apply_effects, validate_effect
from engine.demo import build_demo_state
from engine.npc.knowledge import grant_knowledge
from engine.rules.base import Effect


# --- defaults / data model -------------------------------------------------

def test_npc_has_default_personality_goals_fears_preferences(demo_state):
    elder = demo_state.world.npcs["elder"]
    assert elder.personality == NPCPersonality()
    assert elder.goals == []
    assert elder.fears == []
    assert elder.preferences == []


# --- validation: personality mutation via npc_changes gate ------------------

def test_personality_field_set_in_range_ok(demo_state):
    ok, _, _ = validate_effect(
        Effect("npc", "wolf", "set", ("personality.courage", 70)), demo_state)
    assert ok


def test_personality_field_out_of_range_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("personality.courage", 150)), demo_state)
    assert not ok and "personality.courage" in reason


def test_personality_field_negative_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("personality.aggression", -1)), demo_state)
    assert not ok and "personality.aggression" in reason


def test_personality_unknown_subfield_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("personality.charisma", 50)), demo_state)
    assert not ok and "not settable" in reason


def test_personality_field_wrong_type_rejected(demo_state):
    ok, _, _ = validate_effect(
        Effect("npc", "wolf", "set", ("personality.courage", "high")), demo_state)
    assert not ok


def test_personality_apply_mutates_only_target_field(demo_state):
    report = apply_effects(
        [Effect("npc", "wolf", "set", ("personality.loyalty", 80))], demo_state)
    assert report.clean
    wolf = demo_state.world.npcs["wolf"]
    assert wolf.personality.loyalty == 80
    assert wolf.personality.courage == 50  # untouched default
    check_invariants(demo_state)


def test_dead_npc_personality_change_rejected(demo_state):
    demo_state.world.npcs["wolf"].alive = False
    demo_state.world.npcs["wolf"].hp = 0
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("personality.courage", 60)), demo_state)
    assert not ok and "dead" in reason


# --- validation: traits/fears/preferences mutation --------------------------

def test_traits_replace_ok(demo_state):
    report = apply_effects(
        [Effect("npc", "wolf", "set", ("traits", ["predator", "territorial"]))],
        demo_state)
    assert report.clean
    assert demo_state.world.npcs["wolf"].traits == ["predator", "territorial"]


def test_fears_replace_ok(demo_state):
    report = apply_effects(
        [Effect("npc", "elder", "set", ("fears", ["fire", "caves"]))], demo_state)
    assert report.clean
    assert demo_state.world.npcs["elder"].fears == ["fire", "caves"]


def test_preferences_replace_ok(demo_state):
    report = apply_effects(
        [Effect("npc", "elder", "set", ("preferences", ["quiet places"]))], demo_state)
    assert report.clean
    assert demo_state.world.npcs["elder"].preferences == ["quiet places"]


def test_fears_non_string_list_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "elder", "set", ("fears", [1, 2])), demo_state)
    assert not ok and "list of strings" in reason


def test_dead_npc_traits_change_rejected(demo_state):
    demo_state.world.npcs["wolf"].alive = False
    demo_state.world.npcs["wolf"].hp = 0
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("traits", ["calm"])), demo_state)
    assert not ok and "dead" in reason


# --- identity and goals are NOT AI-mutable ----------------------------------

def test_identity_fields_not_settable(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("id", "dragon")), demo_state)
    assert not ok and "not settable" in reason

    ok, _, reason = validate_effect(
        Effect("npc", "wolf", "set", ("name", "Dragon Emperor")), demo_state)
    assert not ok and "not settable" in reason


def test_goals_not_settable_via_npc_changes(demo_state):
    ok, _, reason = validate_effect(
        Effect("npc", "elder", "set", ("goals", [])), demo_state)
    assert not ok and "not settable" in reason


def test_ai_cannot_mutate_goals_via_npc_change():
    fake = FakeAdapter(handlers={
        "meddle": {
            "narrative": "Nothing changes.",
            "npc_changes": [{"npc": "elder", "field": "goals", "value": []}],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("meddle with the elder")
    assert s.last_report.rejected


# --- invariants --------------------------------------------------------------

def test_invariant_rejects_personality_out_of_range():
    s = build_demo_state()
    s.world.npcs["elder"].personality.courage = 500
    raised = False
    try:
        check_invariants(s)
    except InvariantError as err:
        raised = "personality.courage" in str(err)
    assert raised


def test_invariant_rejects_duplicate_goal_ids():
    s = build_demo_state()
    s.world.npcs["elder"].goals = [
        NPCGoal(id="g1", description="a", priority=10),
        NPCGoal(id="g1", description="b", priority=20),
    ]
    raised = False
    try:
        check_invariants(s)
    except InvariantError as err:
        raised = "duplicate goal id" in str(err)
    assert raised


def test_invariant_rejects_invalid_goal_status():
    s = build_demo_state()
    s.world.npcs["elder"].goals = [
        NPCGoal(id="g1", description="a", priority=10, status="daydreaming"),
    ]
    raised = False
    try:
        check_invariants(s)
    except InvariantError as err:
        raised = "invalid status" in str(err)
    assert raised


def test_invariant_rejects_goal_priority_out_of_range():
    s = build_demo_state()
    s.world.npcs["elder"].goals = [
        NPCGoal(id="g1", description="a", priority=999),
    ]
    raised = False
    try:
        check_invariants(s)
    except InvariantError as err:
        raised = "priority" in str(err)
    assert raised


def test_valid_goal_passes_invariants():
    s = build_demo_state()
    s.world.npcs["elder"].goals = [
        NPCGoal(id="protect_elder", description="Keep the elder alive.",
                priority=90, status="active"),
    ]
    check_invariants(s)  # must not raise


# --- MemoryUpdate reference fields end-to-end --------------------------------

def test_ai_memory_update_with_valid_entity_and_location_stored():
    fake = FakeAdapter(handlers={
        "inspect": {
            "narrative": "You notice something.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "The rope is frayed.",
                "visibility": "player",
                "importance": 30,
                "entity_id": "rope",
                "location_id": "village",
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("inspect the rope")
    assert len(s.memory) == 1
    rec = s.memory.all_records()[0]
    assert rec.entity_id == "rope"
    assert rec.location_id == "village"


def test_ai_memory_update_with_unknown_entity_id_rejected():
    fake = FakeAdapter(handlers={
        "inspect": {
            "narrative": "You notice something.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "A ghost item.",
                "visibility": "player",
                "entity_id": "nonexistent_item",
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("inspect the void")
    assert len(s.memory) == 0


def test_ai_memory_update_with_unknown_location_id_rejected():
    fake = FakeAdapter(handlers={
        "inspect": {
            "narrative": "You notice something.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "A distant rumor.",
                "visibility": "player",
                "location_id": "moon",
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("inspect the sky")
    assert len(s.memory) == 0


def test_ai_memory_update_tags_stored():
    fake = FakeAdapter(handlers={
        "inspect": {
            "narrative": "You notice something.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "The cave is dangerous.",
                "visibility": "player",
                "tags": ["danger", "cave"],
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("inspect the cave")
    rec = s.memory.all_records()[0]
    assert set(rec.tags) == {"danger", "cave"}


def test_ai_memory_update_event_id_passed_through_uncross_checked():
    """event_id is now validated against the authoritative event registry."""
    fake = FakeAdapter(handlers={
        "inspect": {
            "narrative": "You notice something.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "Bandits were seen nearby.",
                "visibility": "player",
                "event_id": "bandit_sighting_1",
            }],
        },
    })
    s = build_session(adapter=fake)
    from engine.core.state import EventState
    s.state.world.events["bandit_sighting_1"] = EventState(
        id="bandit_sighting_1", type="sighting"
    )
    s.handle_input("inspect the road")
    rec = s.memory.all_records()[0]
    assert rec.event_id == "bandit_sighting_1"


# --- per-NPC context assembly / knowledge isolation --------------------------

def test_assemble_npc_context_includes_personality_and_goals():
    s = build_demo_state()
    s.world.npcs["elder"].personality.courage = 20
    s.world.npcs["elder"].goals = [
        NPCGoal(id="protect_temple", description="Protect the temple",
                priority=90, status="active"),
        NPCGoal(id="old_quest", description="Retired goal",
                priority=10, status="completed"),
    ]
    ctx = assemble_npc_context(s, "elder")
    assert "low courage" in ctx
    assert "Protect the temple" in ctx
    assert "Retired goal" not in ctx  # only active goals surface


def test_assemble_npc_context_includes_relationship():
    s = build_demo_state()
    apply_effects(
        [Effect("relationship", "player|elder", "set", ("trust", 40))], s)
    ctx = assemble_npc_context(s, "elder")
    assert "trust: 40" in ctx


def test_assemble_npc_context_isolates_other_npc_private_knowledge():
    s = build_demo_state()
    from engine.memory.system import MemorySystem
    memory = MemorySystem()
    grant_knowledge(memory, "Elder's secret vault", visibility="npc:elder",
                    importance=50, turn=1, state=s)
    grant_knowledge(memory, "Wolf's secret den", visibility="npc:wolf",
                    importance=50, turn=1, state=s)
    elder_ctx = assemble_npc_context(s, "elder", memory=memory)
    assert "Elder's secret vault" in elder_ctx
    assert "Wolf's secret den" not in elder_ctx


def test_assemble_npc_context_no_memory_arg_ok():
    s = build_demo_state()
    ctx = assemble_npc_context(s, "wolf")
    assert "id: wolf" in ctx


# --- persistence: backward compatibility -------------------------------------

def test_v1_2_save_loads_with_npc_defaults():
    """A save written before personality/goals/fears/preferences existed
    (no such keys under world.npcs.<id>) must still load, with engine
    defaults filled in — proving the additive mechanism, not assuming it.
    """
    from engine.persistence.db import SAVE_FORMAT_VERSION, state_from_dict

    old_style_npc = {
        "id": "elder", "name": "village elder", "location_id": "village",
        "hp": 30, "max_hp": 30, "disposition": 20, "alive": True,
        "traits": ["wise", "cautious"],
        # deliberately no 'personality' / 'goals' / 'fears' / 'preferences'
    }
    data = {
        "schema": SAVE_FORMAT_VERSION,
        "turn": 3,
        "recent_turns": [],
        "character": {
            "name": "Wanderer", "hp": 100, "max_hp": 100,
            "stamina": 100, "max_stamina": 100,
            "location_id": "village", "inventory": [],
        },
        "world": {
            "locations": {"village": "Sleepy Village"},
            "exits": {"village": []},
            "items": {},
            "npcs": {"elder": old_style_npc},
            "relationships": {},
        },
        "memories": [],
    }
    state, turn, recent, memory = state_from_dict(data)
    elder = state.world.npcs["elder"]
    assert elder.personality == NPCPersonality()
    assert elder.goals == []
    assert elder.fears == []
    assert elder.preferences == []
    check_invariants(state)


def test_save_load_roundtrip_preserves_personality_and_goals():
    import tempfile
    from pathlib import Path

    from engine.persistence.saves import load_session, save_session

    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    session.state.world.npcs["elder"].personality.honesty = 85
    session.state.world.npcs["elder"].goals = [
        NPCGoal(id="protect_elder", description="Keep the elder alive.",
                priority=90, status="active"),
    ]
    session.state.world.npcs["elder"].fears = ["fire"]
    session.state.world.npcs["elder"].preferences = ["wealth"]

    save_session(session, slot="npc_v13", save_dir=save_dir)
    loaded = load_session(slot="npc_v13", save_dir=save_dir)
    elder = loaded.state.world.npcs["elder"]
    assert elder.personality.honesty == 85
    assert [g.id for g in elder.goals] == ["protect_elder"]
    assert elder.fears == ["fire"]
    assert elder.preferences == ["wealth"]
