from engine.core.state import RelationshipState
from engine.core.validation import apply_effects, validate_effect
from engine.core.invariants import check_invariants, InvariantError
from engine.rules.base import Effect
from engine.demo import build_demo_state
from engine.ai.fake import FakeAdapter
from engine.cli import build_session


def test_relationship_set_affinity(demo_state):
    report = apply_effects([
        Effect("relationship", "player|elder", "set", ("affinity", 40),
               reason="helped"),
    ], demo_state)
    assert report.clean
    rel = demo_state.world.get_relationship("player", "elder")
    assert rel is not None and rel.affinity == 40
    check_invariants(demo_state)


def test_relationship_add_clamped(demo_state):
    apply_effects([
        Effect("relationship", "player:elder", "set", ("affinity", 90)),
    ], demo_state)
    report = apply_effects([
        Effect("relationship", "player|elder", "add", ("affinity", 50)),
    ], demo_state)
    assert report.clean
    assert demo_state.world.get_relationship("player", "elder").affinity == 100


def test_relationship_unknown_party_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("relationship", "player|dragon", "set", ("trust", 10)),
        demo_state)
    assert not ok and "unknown" in reason


def test_relationship_same_party_rejected(demo_state):
    ok, _, reason = validate_effect(
        Effect("relationship", "elder|elder", "set", 5), demo_state)
    assert not ok


def test_ai_relationship_proposal():
    fake = FakeAdapter(handlers={
        "befriend": {
            "narrative": "The elder softens.",
            "state_changes": [{
                "type": "relationship",
                "target": "player|elder",
                "operation": "add",
                "value": ["affinity", 15],
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("befriend the elder")
    rel = s.state.world.get_relationship("player", "elder")
    assert rel is not None and rel.affinity == 15


def test_relationship_invariant_unknown_party():
    s = build_demo_state()
    s.world.relationships["player|ghost"] = RelationshipState(
        party_a="player", party_b="ghost", affinity=1)
    try:
        check_invariants(s)
        ok = False
    except InvariantError:
        ok = True
    assert ok


def test_canonical_key_order_independent():
    assert RelationshipState.canonical_key("player", "elder") == \
        RelationshipState.canonical_key("elder", "player")


def test_relationship_flags_are_deterministic(demo_state):
    report = apply_effects([
        Effect("relationship", "player|elder", "flag_add", "promise"),
        Effect("relationship", "player|elder", "flag_remove", "missing"),
    ], demo_state)
    assert report.clean
    rel = demo_state.world.get_relationship("player", "elder")
    assert rel is not None and rel.flags == ["promise"]
    report = apply_effects([Effect("relationship", "player|elder", "flag_remove", "promise")], demo_state)
    assert report.clean and demo_state.world.get_relationship("player", "elder").flags == []
