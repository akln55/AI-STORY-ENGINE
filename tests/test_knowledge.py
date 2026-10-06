from engine.cli import build_session
from engine.demo import build_demo_state
from engine.memory.system import MemorySystem, MemoryValidationError
from engine.npc.knowledge import grant_knowledge, npc_knows, player_visible_knowledge
from engine.ai.fake import FakeAdapter


def test_grant_and_visibility_isolation():
    state = build_demo_state()
    ms = MemorySystem()
    grant_knowledge(ms, "Vault under the temple", visibility="npc:elder",
                    importance=50, turn=1, state=state)
    grant_knowledge(ms, "Road is safe", visibility="player",
                    importance=10, turn=1, state=state)
    assert len(player_visible_knowledge(ms)) == 1
    elder = npc_knows(ms, "elder")
    contents = {r.content for r in elder}
    assert "Vault under the temple" in contents
    assert "Road is safe" in contents  # player-visible shared
    wolf = npc_knows(ms, "wolf")
    assert all("Vault" not in r.content for r in wolf)


def test_grant_rejects_unknown_npc_visibility():
    state = build_demo_state()
    ms = MemorySystem()
    try:
        grant_knowledge(ms, "secret", visibility="npc:dragon", state=state)
        ok = False
    except MemoryValidationError:
        ok = True
    assert ok


def test_grant_rejects_unknown_location_ref():
    state = build_demo_state()
    ms = MemorySystem()
    try:
        grant_knowledge(ms, "x", visibility="player", location_id="moon",
                        state=state)
        ok = False
    except MemoryValidationError:
        ok = True
    assert ok


def test_ai_memory_unknown_npc_visibility_skipped():
    fake = FakeAdapter(handlers={
        "whisper": {
            "narrative": "You hear something.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "Should not store",
                "visibility": "npc:dragon",
                "importance": 40,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("whisper secrets")
    assert len(s.memory) == 0


def test_ai_memory_valid_npc_visibility_stored():
    fake = FakeAdapter(handlers={
        "whisper": {
            "narrative": "The elder mutters.",
            "memory_updates": [{
                "store": "knowledge",
                "content": "Elder fears the cave",
                "visibility": "npc:elder",
                "importance": 40,
            }],
        },
    })
    s = build_session(adapter=fake)
    s.handle_input("whisper secrets")
    assert len(s.memory) == 1
    assert player_visible_knowledge(s.memory) == []
    assert any("cave" in r.content for r in npc_knows(s.memory, "elder"))
