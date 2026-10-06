"""v1.4 event foundation tests."""

from engine.core.invariants import InvariantError, check_invariants
from engine.core.state import EventState
from engine.core.validation import apply_effects
from engine.ai.schema import parse_structured_response
from engine.cli import build_session
from engine.persistence.saves import load_session, save_session
from engine.rules.base import Effect


def test_event_trigger_changes_existing_inactive_event():
    session = build_session()
    session.state.world.events["attack"] = EventState(
        id="attack", type="bandit_attack", location_id="village"
    )
    report = apply_effects(
        [Effect("event", "attack", "trigger", 7)],
        session.state,
    )
    assert report.clean
    event = session.state.world.events["attack"]
    assert event.status == "active"
    assert event.start_turn == 7


def test_event_lifecycle_allows_active_to_terminal():
    session = build_session()
    session.state.world.events["attack"] = EventState(
        id="attack", type="bandit_attack"
    )
    assert apply_effects(
        [Effect("event", "attack", "trigger", 3)], session.state
    ).clean
    assert apply_effects(
        [Effect("event", "attack", "resolve", 9)], session.state
    ).clean
    event = session.state.world.events["attack"]
    assert event.status == "resolved"
    assert event.resolved_turn == 9


def test_invalid_event_transition_rejected_atomically():
    session = build_session()
    session.state.world.events["done"] = EventState(
        id="done", type="old_event", status="resolved",
        start_turn=1, resolved_turn=2,
    )
    before = session.state.world.events["done"].status
    report = apply_effects(
        [
            Effect("event", "done", "trigger", 4),
            Effect("resource", "player.hp", "set", 50),
        ],
        session.state,
    )
    assert report.rejected
    assert not report.accepted
    assert session.state.world.events["done"].status == before
    assert session.state.character.hp == 100


def test_unknown_event_rejected():
    session = build_session()
    report = apply_effects(
        [Effect("event", "missing", "trigger", 1)],
        session.state,
    )
    assert report.rejected


def test_event_invariant_rejects_unknown_location():
    session = build_session()
    session.state.world.events["bad"] = EventState(
        id="bad", type="x", location_id="missing"
    )
    try:
        check_invariants(session.state)
        raised = False
    except InvariantError:
        raised = True
    assert raised


def test_ai_events_triggered_becomes_engine_effect():
    session = build_session()
    session.state.world.events["festival"] = EventState(
        id="festival", type="festival"
    )
    response = parse_structured_response({
        "narrative": "The festival begins.",
        "state_changes": [],
        "memory_updates": [],
        "npc_changes": [],
        "events_triggered": ["festival"],
        "available_actions": [],
    })
    effects = session._effects_from_response(response)
    effects.extend(
        Effect("event", event_id, "trigger", session.clock.turn)
        for event_id in response.events_triggered
    )
    report = apply_effects(effects, session.state)
    assert report.clean
    assert session.state.world.events["festival"].status == "active"


def test_event_save_load_roundtrip():
    import tempfile
    from pathlib import Path
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    session.state.world.events["festival"] = EventState(
        id="festival", type="festival", status="active",
        start_turn=5, location_id="village", participants=["player"],
        metadata={"kind": "public"},
    )
    path = save_session(session, slot="events", save_dir=save_dir)
    loaded = load_session(slot="events", save_dir=save_dir)
    event = loaded.state.world.events["festival"]
    assert event.type == "festival"
    assert event.status == "active"
    assert event.start_turn == 5
    assert event.location_id == "village"
    assert event.participants == ["player"]
    assert event.metadata == {"kind": "public"}


def test_old_save_without_events_loads():
    import tempfile
    from pathlib import Path
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    path = save_session(session, slot="old", save_dir=save_dir)
    # Remove events from the serialized game-state payload to emulate v1.3.
    import sqlite3, json
    conn = sqlite3.connect(str(path))
    row = conn.execute("SELECT json FROM game_state WHERE id=1").fetchone()
    payload = json.loads(row[0])
    payload["world"].pop("events", None)
    with conn:
        conn.execute("UPDATE game_state SET json=? WHERE id=1",
                     (json.dumps(payload),))
    conn.close()
    loaded = load_session(slot="old", save_dir=save_dir)
    assert loaded.state.world.events == {}
