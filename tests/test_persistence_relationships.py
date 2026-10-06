import tempfile
from pathlib import Path

from engine.cli import build_session
from engine.core.validation import apply_effects
from engine.rules.base import Effect
from engine.persistence.saves import load_session, save_session
from engine.npc.knowledge import grant_knowledge


def test_save_load_relationships_and_traits():
    save_dir = Path(tempfile.mkdtemp())
    s = build_session()
    apply_effects([
        Effect("relationship", "player|elder", "set", ("affinity", 25)),
        Effect("relationship", "player|elder", "set", ("trust", 10)),
    ], s.state)
    grant_knowledge(s.memory, "Elder trusts you a little",
                    visibility="player", turn=1, state=s.state)
    save_session(s, slot="rel", save_dir=save_dir)
    loaded = load_session(slot="rel", save_dir=save_dir)
    rel = loaded.state.world.get_relationship("player", "elder")
    assert rel is not None
    assert rel.affinity == 25 and rel.trust == 10
    assert "wise" in loaded.state.world.npcs["elder"].traits
    assert len(loaded.memory) == 1


def test_player_popularity_and_reputation_roundtrip(tmp_path):
    from engine.core.state import CharacterState, GameState, WorldState
    from engine.persistence.db import write_save, read_save
    state = GameState(character=CharacterState(location_id="camp", popularity=42, reputation={"royal": -15}), world=WorldState(locations={"camp": "Camp"}, exits={"camp": []}))
    path = tmp_path / "save.db"
    write_save(path, state, 0, [], "test")
    loaded, *_ = read_save(path)
    assert loaded.character.popularity == 42
    assert loaded.character.reputation == {"royal": -15}
