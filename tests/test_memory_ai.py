"""AI memory_updates and combined state+memory paths."""

from engine.ai.fake import FakeAdapter
from engine.cli import build_session
from engine.memory.retrieval import retrieve


def test_valid_memory_update_stored():
    fake = FakeAdapter(handlers={
        "recall": {
            "narrative": "You remember the old path.",
            "memory_updates": [{
                "store": "location",
                "content": "An old path leads through the forest",
                "visibility": "player",
                "importance": 30,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("recall the path")
    recs = retrieve(s.memory, viewer="player")
    assert any("old path" in r.content for r in recs)


def test_invalid_memory_store_skipped():
    fake = FakeAdapter(handlers={
        "forget": {
            "narrative": "Nothing happens.",
            "memory_updates": [{
                "store": "not_a_real_store",
                "content": "should not land",
                "visibility": "player",
                "importance": 10,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("forget nonsense")
    assert len(s.memory) == 0


def test_system_memory_not_in_player_retrieval():
    fake = FakeAdapter(handlers={
        "secret": {
            "narrative": "A chill passes.",
            "memory_updates": [{
                "store": "secret",
                "content": "The elder is a spy",
                "visibility": "system",
                "importance": 90,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("sense a secret")
    assert len(s.memory) == 1
    assert retrieve(s.memory, viewer="player") == []
    assert len(retrieve(s.memory, viewer="system")) == 1


def test_state_change_and_memory_together():
    fake = FakeAdapter(handlers={
        "rest": {
            "narrative": "You rest and recall a rumor.",
            "state_changes": [{
                "type": "resource", "target": "player.stamina",
                "operation": "add", "value": 5,
            }],
            "memory_updates": [{
                "store": "rumor",
                "content": "Merchants speak of bandits",
                "visibility": "player",
                "importance": 20,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.state.character.stamina = 50
    s.handle_input("rest by the fire")
    assert s.state.character.stamina == 55
    assert any("bandits" in r.content for r in retrieve(s.memory, viewer="player"))


def test_rejected_state_blocks_accompanying_memory():
    """Rejected state_changes must not let accompanying memory_updates become facts."""
    fake = FakeAdapter(handlers={
        "wish": {
            "narrative": "A sword appears!",
            "state_changes": [{
                "type": "inventory", "target": "sword",
                "operation": "take", "value": "player",
            }],
            "memory_updates": [{
                "store": "recent",
                "content": "Player received a magic sword",
                "visibility": "player",
                "importance": 5,
            }],
        },
    })
    s = build_session(adapter=fake)
    out = s.handle_input("wish for a sword")
    assert "sword" not in s.state.character.inventory
    assert "does not fully succeed" in out or "could not apply" in out or "attempt" in out.lower()
    assert len(s.memory) == 0
    assert retrieve(s.memory, viewer="player") == []


def test_pure_memory_turn_without_state_changes_allowed():
    fake = FakeAdapter(handlers={
        "journal": {
            "narrative": "You jot a note.",
            "memory_updates": [{
                "store": "character",
                "content": "Noted the weather",
                "visibility": "player",
                "importance": 8,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("journal the weather")
    assert any("weather" in r.content for r in retrieve(s.memory, viewer="player"))


def test_multiple_memory_updates():
    fake = FakeAdapter(handlers={
        "journal": {
            "narrative": "You write in your journal.",
            "memory_updates": [
                {"store": "character", "content": "Day one", "visibility": "player", "importance": 10},
                {"store": "location", "content": "Village is quiet", "visibility": "player", "importance": 15},
            ],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("write in journal")
    assert len(retrieve(s.memory, viewer="player")) == 2
