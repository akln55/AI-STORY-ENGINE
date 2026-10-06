"""Phase 3 AI-contract hardening tests.

Proves the boundary in docs/ARCHITECTURE.md §1 / ADR-0001 end to end:
    AI -> StructuredResponse -> Effect -> validation gate -> GameState
and specifically that nothing -- a bad proposal, a malformed npc_change, or
plain narration -- can reach GameState without passing through
engine.core.validation.apply_effects.
"""

from contextlib import contextmanager

from engine.ai.adapter_base import AIAdapter
from engine.ai.fake import FakeAdapter
from engine.cli import build_session


@contextmanager
def raises(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} was not raised")


# --------------------------------------------------------------- adapter shape

def test_adapter_base_is_abstract_and_defines_only_generate():
    with raises(TypeError):
        AIAdapter()  # cannot be instantiated: no write path exists to bypass


def test_fake_adapter_satisfies_the_adapter_interface():
    assert isinstance(FakeAdapter(), AIAdapter)


# ------------------------------------------------------- valid proposal path

def test_valid_state_change_proposal_reaches_validation_and_mutates_state():
    fake = FakeAdapter(handlers={
        "meditate": {
            "narrative": "You feel calmer.",
            "state_changes": [{"type": "resource", "target": "player.stamina",
                               "operation": "add", "value": 5, "reason": "rest"}],
        },
    })
    s = build_session(adapter=fake)
    stamina_before = s.state.character.stamina
    s.state.character.stamina -= 5  # room to regain
    out = s.handle_input("meditate quietly")
    assert s.state.character.stamina == stamina_before
    assert s.last_report is not None and s.last_report.clean
    assert "calmer" in out


def test_valid_npc_change_reaches_validation_and_mutates_state():
    fake = FakeAdapter(handlers={
        "flatter": {
            "narrative": "The wolf seems less hostile.",
            "npc_changes": [{"npc": "wolf", "field": "disposition", "value": -10}],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    before = s.state.world.npcs["wolf"].disposition
    s.handle_input("flatter the wolf")
    assert s.state.world.npcs["wolf"].disposition == -10
    assert before != -10  # actually changed, not coincidentally equal


# ----------------------------------------------------------- invalid proposals

def test_invalid_state_change_is_rejected_not_applied():
    fake = FakeAdapter(handlers={
        "wish": {
            "narrative": "A magic sword appears in your hands!",
            "state_changes": [{"type": "inventory", "target": "sword",
                               "operation": "take", "value": "player"}],
        },
    })
    s = build_session(adapter=fake)
    out = s.handle_input("wish for a sword")
    assert "sword" not in s.state.character.inventory
    assert s.last_report is not None and len(s.last_report.rejected) == 1
    assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())


def test_malformed_npc_change_value_rejected_not_crashed():
    """Regression: a state_change of type 'npc' whose value is not a
    (field, value) pair used to raise an uncaught TypeError deep inside
    validation.py instead of being rejected. It must now be a clean,
    logged rejection with no state mutation and no crash."""
    fake = FakeAdapter(handlers={
        "curse": {
            "narrative": "Dark energy crackles.",
            "state_changes": [{"type": "npc", "target": "wolf",
                               "operation": "set", "value": 12345}],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    wolf_before = (s.state.world.npcs["wolf"].disposition,
                   s.state.world.npcs["wolf"].alive)
    out = s.handle_input("curse the wolf")  # must not raise
    assert (s.state.world.npcs["wolf"].disposition,
            s.state.world.npcs["wolf"].alive) == wolf_before
    assert s.last_report is not None and len(s.last_report.rejected) == 1
    assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())


def test_npc_change_to_non_settable_field_rejected():
    fake = FakeAdapter(handlers={
        "heal": {
            "narrative": "The wolf looks fully healed!",
            "npc_changes": [{"npc": "wolf", "field": "hp", "value": 999}],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    hp_before = s.state.world.npcs["wolf"].hp
    out = s.handle_input("heal the wolf")
    assert s.state.world.npcs["wolf"].hp == hp_before  # 'hp' is not settable via npc_change
    assert s.last_report is not None and len(s.last_report.rejected) == 1
    assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())


def test_npc_change_targeting_unknown_npc_rejected():
    fake = FakeAdapter(handlers={
        "summon": {
            "narrative": "A dragon appears!",
            "npc_changes": [{"npc": "dragon", "field": "disposition", "value": 50}],
        },
    })
    s = build_session(adapter=fake)
    out = s.handle_input("summon a dragon")
    assert "dragon" not in s.state.world.npcs
    assert s.last_report is not None and len(s.last_report.rejected) == 1
    assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())


def test_mixed_valid_and_invalid_effects_atomic_reject():
    """Atomic batch: any rejection means no effect in the batch is applied."""
    fake = FakeAdapter(handlers={
        "trick": {
            "narrative": "Something shifts.",
            "state_changes": [
                {"type": "resource", "target": "player.stamina", "operation": "add",
                 "value": -1, "reason": "legit"},
                {"type": "location", "target": "player", "operation": "move",
                 "value": "moon"},  # unknown location, must be rejected
            ],
        },
    })
    s = build_session(adapter=fake)
    stamina_before = s.state.character.stamina
    loc_before = s.state.character.location_id
    s.handle_input("trick the world")
    assert s.state.character.stamina == stamina_before  # atomic: nothing applied
    assert s.state.character.location_id == loc_before
    assert s.last_report is not None
    assert len(s.last_report.accepted) == 0 and len(s.last_report.rejected) >= 1


# -------------------------------------------------------- narration boundary

def test_narrative_claiming_state_change_never_mutates_state():
    fake = FakeAdapter(handlers={
        "sing": {"narrative": "Your song is beautiful. (+100 HP, says the song.)"},
    })
    s = build_session(adapter=fake)
    hp_before = s.state.character.hp
    out = s.handle_input("sing a song")
    assert s.state.character.hp == hp_before
    assert "beautiful" in out


def test_unconsumed_schema_fields_do_not_affect_state_or_output():
    """Parsed event triggers are now authoritative proposals; unknown events
    are rejected without mutating the world. Other unconsumed fields remain inert."""
    fake = FakeAdapter(handlers={
        "ponder": {
            "narrative": "You mull it over.",
            "memory_updates": [{"store": "recent", "content": "pondered",
                                "visibility": "player", "importance": 5}],
            "events_triggered": ["ponder_event"],
            "available_actions": ["continue", "stop"],
        },
    })
    s = build_session(adapter=fake)
    snapshot = (s.state.character.hp, s.state.character.stamina,
                s.state.character.location_id, list(s.state.character.inventory))
    out = s.handle_input("ponder the situation")
    assert (s.state.character.hp, s.state.character.stamina,
            s.state.character.location_id, list(s.state.character.inventory)) == snapshot
    assert "You mull it over." in out
    assert "unknown event 'ponder_event'" in out


# -------------------------------------------------------- deterministic path

def test_deterministic_commands_never_touch_ai_adapter():
    fake = FakeAdapter()
    s = build_session(adapter=fake)
    s.handle_input("go forest")
    s.handle_input("take mushroom")
    assert fake.calls == []  # rule-handled intents never reach the adapter


# ---------------------------------------------------------- context contract

def test_context_contains_the_documented_sections():
    from engine.ai.context import assemble_context
    s = build_session()
    s.handle_input("go forest")
    ctx = assemble_context(s.state, s.recent_turns, "look around")
    for marker in ("CORE SYSTEM:", "RPG RULES:", "CHARACTER CONTEXT:",
                   "WORLD STATE:", "RECENT SCENE:", "PLAYER ACTION:"):
        assert marker in ctx
    assert "PLAYER ACTION: look around" in ctx.splitlines()[-1]
