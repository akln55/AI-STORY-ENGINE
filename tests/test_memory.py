from engine.memory.system import (
    MemorySystem, MemoryRecord, MemoryValidationError, STORES,
)
from engine.memory.retrieval import retrieve


def test_all_stores_accepted():
    ms = MemorySystem()
    for store in STORES:
        rec = ms.add(store, f"fact about {store}", visibility="system", importance=1)
        assert rec.store == store
    assert len(ms) == len(STORES)


def test_invalid_store_rejected():
    ms = MemorySystem()
    try:
        ms.add("nonexistent", "x")
        ok = False
    except MemoryValidationError:
        ok = True
    assert ok


def test_empty_content_rejected():
    ms = MemorySystem()
    try:
        ms.add("recent", "   ")
        ok = False
    except MemoryValidationError:
        ok = True
    assert ok


def test_visibility_variants():
    ms = MemorySystem()
    ms.add("secret", "hidden truth", visibility="system")
    ms.add("rumor", "player heard this", visibility="player")
    ms.add("knowledge", "elder knows", visibility="npc:elder")
    ms.add("event", "guild secret", visibility="faction:guild")
    assert len(ms) == 4
    try:
        ms.add("secret", "bad", visibility="everyone")
        ok = False
    except MemoryValidationError:
        ok = True
    assert ok


def test_importance_bounds():
    ms = MemorySystem()
    ms.add("recent", "ok", importance=0)
    ms.add("recent", "ok2", importance=100)
    try:
        ms.add("recent", "bad", importance=101)
        ok = False
    except MemoryValidationError:
        ok = True
    assert ok


def test_player_cannot_see_system_or_npc():
    ms = MemorySystem()
    ms.add("secret", "system only", visibility="system", importance=50)
    ms.add("knowledge", "npc only", visibility="npc:elder", importance=50)
    ms.add("rumor", "player knows", visibility="player", importance=10)
    player_view = retrieve(ms, viewer="player")
    assert len(player_view) == 1
    assert player_view[0].content == "player knows"


def test_system_sees_all():
    ms = MemorySystem()
    ms.add("secret", "a", visibility="system")
    ms.add("rumor", "b", visibility="player")
    ms.add("knowledge", "c", visibility="npc:wolf")
    assert len(retrieve(ms, viewer="system")) == 3


def test_npc_sees_own_and_player():
    ms = MemorySystem()
    ms.add("knowledge", "elder secret", visibility="npc:elder")
    ms.add("knowledge", "wolf secret", visibility="npc:wolf")
    ms.add("rumor", "public", visibility="player")
    ms.add("secret", "sys", visibility="system")
    view = retrieve(ms, viewer="npc:elder")
    contents = {r.content for r in view}
    assert "elder secret" in contents
    assert "public" in contents
    assert "wolf secret" not in contents
    assert "sys" not in contents


def test_filter_by_store_entity_location_tags():
    ms = MemorySystem()
    ms.add("location", "forest fire", visibility="player", location_id="forest",
           tags=["fire", "danger"], importance=20, created_turn=1)
    ms.add("location", "village feast", visibility="player", location_id="village",
           tags=["feast"], importance=5, created_turn=2)
    ms.add("item", "rope worn", visibility="player", entity_id="rope",
           tags=["wear"], importance=3, created_turn=3)
    assert len(retrieve(ms, viewer="player", store="location")) == 2
    assert len(retrieve(ms, viewer="player", location_id="forest")) == 1
    assert len(retrieve(ms, viewer="player", entity_id="rope")) == 1
    assert len(retrieve(ms, viewer="player", tags=["fire"])) == 1


def test_ranking_importance_and_recency():
    ms = MemorySystem()
    ms.add("recent", "old low", visibility="player", importance=1, created_turn=1)
    ms.add("recent", "new high", visibility="player", importance=90, created_turn=5)
    ms.add("recent", "mid", visibility="player", importance=50, created_turn=3)
    ranked = retrieve(ms, viewer="player", limit=10)
    assert ranked[0].content == "new high"
    assert ranked[-1].content == "old low"


def test_query_terms_boost():
    ms = MemorySystem()
    ms.add("event", "the wolf attacked", visibility="player", importance=10, created_turn=1)
    ms.add("event", "quiet day", visibility="player", importance=50, created_turn=2)
    ranked = retrieve(ms, viewer="player", query_terms=["wolf"], limit=2)
    assert ranked[0].content == "the wolf attacked"


def test_deterministic_retrieval():
    ms = MemorySystem()
    for i in range(20):
        ms.add("recent", f"event {i}", visibility="player", importance=i % 7,
               created_turn=i)
    a = [r.id for r in retrieve(ms, viewer="player", limit=5)]
    b = [r.id for r in retrieve(ms, viewer="player", limit=5)]
    assert a == b


def test_limit_bounds_results():
    ms = MemorySystem()
    for i in range(15):
        ms.add("recent", f"x{i}", visibility="player", importance=i)
    assert len(retrieve(ms, viewer="player", limit=3)) == 3
    assert len(retrieve(ms, viewer="player", limit=0)) == 0


def test_add_from_proposal_clamps_and_defaults():
    ms = MemorySystem()
    rec = ms.add_from_proposal(
        "rumor", "something", visibility="bogus", importance=999, created_turn=4)
    assert rec.visibility == "system"
    assert rec.importance == 100


def test_serialization_roundtrip():
    ms = MemorySystem()
    ms.add("permanent", "world exists", visibility="system", importance=100,
           created_turn=0, tags=["core"])
    ms.add("rumor", "dragon nearby", visibility="player", importance=40,
           created_turn=3, location_id="forest")
    data = ms.to_list()
    ms2 = MemorySystem.from_list(data)
    assert len(ms2) == 2
    assert {r.content for r in ms2.all_records()} == {
        "world exists", "dragon nearby"}


def test_remove_and_clear_store():
    ms = MemorySystem()
    r = ms.add("recent", "temp", visibility="system")
    assert ms.remove(r.id)
    assert not ms.remove(r.id)
    ms.add("recent", "a", visibility="system")
    ms.add("event", "b", visibility="system")
    assert ms.clear_store("recent") == 1
    assert len(ms) == 1


def test_structural_dedup_refreshes_existing():
    ms = MemorySystem()
    r1 = ms.add("rumor", "Bandits on the road", visibility="player",
                importance=10, created_turn=1)
    r2 = ms.add("rumor", "bandits on the road", visibility="player",
                importance=25, created_turn=5)  # same after normalize
    assert r1.id == r2.id
    assert len(ms) == 1
    assert r2.importance == 25
    assert r2.last_updated_turn == 5


def test_distinct_content_not_deduped():
    ms = MemorySystem()
    ms.add("event", "Wolf attacked once", visibility="player", created_turn=1)
    ms.add("event", "Wolf attacked twice", visibility="player", created_turn=2)
    assert len(ms) == 2


def test_dedup_respects_visibility_and_store():
    ms = MemorySystem()
    ms.add("secret", "Hidden fact", visibility="system", created_turn=1)
    ms.add("secret", "Hidden fact", visibility="player", created_turn=2)
    ms.add("rumor", "Hidden fact", visibility="system", created_turn=3)
    assert len(ms) == 3


def test_archive_is_lossless_and_hidden_by_default():
    ms = MemorySystem()
    old = ms.add("recent", "old scene", visibility="player", created_turn=1)
    new = ms.add("recent", "new scene", visibility="player", created_turn=150)
    archived = ms.archive_older_than(150, max_age=100)
    assert archived == 1
    assert old.tier == "archive"
    assert new.tier == "active"
    assert [r.content for r in retrieve(ms, viewer="player")] == ["new scene"]
    assert [r.content for r in retrieve(ms, viewer="player", include_archive=True)] == ["new scene", "old scene"]


def test_archive_tier_persists():
    ms = MemorySystem()
    rec = ms.add("recent", "archived fact", visibility="player", created_turn=1)
    ms.archive_older_than(200, max_age=100)
    restored = MemorySystem.from_list(ms.to_list())
    assert restored.get(rec.id).tier == "archive"
    assert retrieve(restored, viewer="player") == []
    assert len(retrieve(restored, viewer="player", include_archive=True)) == 1


def test_indexed_retrieval_preserves_substring_semantics():
    ms = MemorySystem()
    ms.add("event", "the wolf attacked", visibility="player", importance=10, created_turn=1)
    ms.add("event", "wolf tracks", visibility="player", importance=5, created_turn=2)
    ms.add("event", "quiet day", visibility="player", importance=100, created_turn=3)
    ranked = retrieve(ms, viewer="player", query_terms=["olf"], limit=10)
    assert [r.content for r in ranked] == ["the wolf attacked", "wolf tracks"]
