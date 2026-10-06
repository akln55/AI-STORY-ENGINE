"""Deterministic multi-turn smoke tests (200 and 1000 turns)."""

from pathlib import Path
import tempfile

from engine.ai.fake import FakeAdapter
from engine.cli import build_session
from engine.core.invariants import check_invariants
from engine.memory.retrieval import retrieve
from engine.persistence.saves import load_session, save_session


def _cycling_handlers():
    """Deterministic FakeAdapter handlers that cycle legal actions."""
    return {
        "look around carefully": {
            "narrative": "You survey the area.",
            "memory_updates": [{
                "store": "recent",
                "content": "Surveyed surroundings",
                "visibility": "player",
                "importance": 5,
            }],
        },
        "think about the journey": {
            "narrative": "Memories of the road return.",
            "memory_updates": [{
                "store": "character",
                "content": "Reflected on the journey",
                "visibility": "player",
                "importance": 10,
            }],
        },
        "hum a tune": {
            "narrative": "A soft melody drifts.",
        },
    }


def test_200_turn_no_corruption():
    handlers = _cycling_handlers()
    fake = FakeAdapter(handlers=handlers)
    s = build_session(adapter=fake)
    actions = list(handlers.keys())
    rule_actions = ["look", "status", "inventory"]
    for t in range(200):
        if t % 7 == 0:
            s.handle_input("go forest" if s.state.character.location_id == "village"
                           else "go village")
        elif t % 5 == 0:
            s.handle_input(rule_actions[t % len(rule_actions)])
        else:
            s.handle_input(actions[t % len(actions)])
        check_invariants(s.state)
    assert s.clock.turn >= 150  # meta commands don't advance; most do
    # Memory still retrievable
    player_mems = retrieve(s.memory, viewer="player", limit=20)
    assert isinstance(player_mems, list)
    # Context still builds
    from engine.ai.context import assemble_context
    ctx = assemble_context(s.state, s.recent_turns, "check", memory=s.memory)
    assert len(ctx) <= 12000
    # Save/load
    save_dir = Path(tempfile.mkdtemp())
    save_session(s, slot="long200", save_dir=save_dir)
    loaded = load_session(slot="long200", save_dir=save_dir, adapter=fake)
    check_invariants(loaded.state)
    assert loaded.clock.turn == s.clock.turn
    assert len(loaded.memory) == len(s.memory)


def test_1000_turn_deterministic_retrieval():
    handlers = _cycling_handlers()
    fake = FakeAdapter(handlers=handlers)
    s = build_session(adapter=fake)
    actions = list(handlers.keys())
    for t in range(1000):
        if t % 11 == 0:
            s.handle_input("go forest" if s.state.character.location_id == "village"
                           else "go village")
        else:
            s.handle_input(actions[t % len(actions)])
        if t % 100 == 99:
            check_invariants(s.state)
    check_invariants(s.state)
    a = [r.id for r in retrieve(s.memory, viewer="player", limit=5)]
    b = [r.id for r in retrieve(s.memory, viewer="player", limit=5)]
    assert a == b
    save_dir = Path(tempfile.mkdtemp())
    save_session(s, slot="long1000", save_dir=save_dir)
    loaded = load_session(slot="long1000", save_dir=save_dir)
    assert loaded.clock.turn == s.clock.turn
    assert len(loaded.memory) == len(s.memory)


def test_large_memory_retrieval_and_lossless_compaction():
    from engine.memory.system import MemorySystem
    ms = MemorySystem()
    for i in range(5000):
        ms.add("recent", f"unique scene marker {i}", visibility="player", importance=i % 20, created_turn=i)
    assert len(ms) == 5000
    result = retrieve(ms, viewer="player", query_terms=["marker 4999"], limit=5)
    assert result and result[0].content == "unique scene marker 4999"
    archived = ms.archive_older_than(5000, max_age=100)
    assert archived == 4900
    assert len(ms) == 5000
    assert retrieve(ms, viewer="player", query_terms=["marker 10"], limit=5) == []
    archived_hits = retrieve(ms, viewer="player", query_terms=["marker 10"], limit=100, include_archive=True)
    assert any(r.content == "unique scene marker 10" for r in archived_hits)


def test_session_maintenance_archives_old_recent_memory():
    s = build_session(adapter=FakeAdapter(handlers={}))
    for i in range(500):
        s.memory.add("recent", f"old runtime note {i}", visibility="player", created_turn=1)
    s.clock.turn = 124
    s.handle_input("go forest")
    assert s.clock.turn == 125
    assert s.memory.archive_count() == 500
    assert retrieve(s.memory, viewer="player", query_terms=["runtime note 1"], limit=10) == []
