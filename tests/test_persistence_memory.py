import json
import sqlite3
import tempfile
from pathlib import Path

from engine.cli import build_session
from engine.memory.system import MemorySystem
from engine.persistence.db import SAVE_FORMAT_VERSION, SaveError, read_save, write_save
from engine.persistence.saves import load_session, save_session, slot_path
from engine.demo import build_demo_state
from engine.core.clock import GameClock


def test_save_load_preserves_memories():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    session.memory.add(
        "rumor", "Bandits on the road", visibility="player",
        importance=25, created_turn=1, tags=["danger"])
    session.memory.add(
        "secret", "Hidden vault", visibility="system",
        importance=90, created_turn=1)
    save_session(session, slot="mem", save_dir=save_dir)
    loaded = load_session(slot="mem", save_dir=save_dir)
    assert len(loaded.memory) == 2
    contents = {r.content for r in loaded.memory.all_records()}
    assert "Bandits on the road" in contents
    assert "Hidden vault" in contents


def test_v1_save_loads_with_empty_memory():
    """Backward compatible: schema 1 payload without memories key."""
    save_dir = Path(tempfile.mkdtemp())
    state = build_demo_state()
    path = slot_path("v1", save_dir)
    # Manually write a v1-shaped payload via low-level API simulation
    from engine.persistence import db as dbmod
    old_ver = dbmod.SAVE_FORMAT_VERSION
    # Build v1 dict
    payload = {
        "schema": 1,
        "turn": 3,
        "recent_turns": ["T1 player: go forest"],
        "character": {
            "name": state.character.name,
            "hp": state.character.hp,
            "max_hp": state.character.max_hp,
            "stamina": state.character.stamina,
            "max_stamina": state.character.max_stamina,
            "location_id": state.character.location_id,
            "inventory": list(state.character.inventory),
        },
        "world": {
            "locations": dict(state.world.locations),
            "exits": {k: list(v) for k, v in state.world.exits.items()},
            "items": {
                k: {"id": v.id, "name": v.name,
                    "location_id": v.location_id, "owner": v.owner}
                for k, v in state.world.items.items()
            },
            "npcs": {
                k: {"id": v.id, "name": v.name, "location_id": v.location_id,
                    "hp": v.hp, "max_hp": v.max_hp,
                    "disposition": v.disposition, "alive": v.alive}
                for k, v in state.world.npcs.items()
            },
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    with conn:
        conn.executescript(dbmod._SCHEMA)
        for key, value in (
            ("engine_version", "0.2.0"),
            ("save_format_version", "1"),
            ("scenario_id", "demo-bootstrap"),
            ("created", "2026-01-01T00:00:00+00:00"),
            ("modified", "2026-01-01T00:00:00+00:00"),
        ):
            conn.execute("INSERT INTO header VALUES (?, ?)", (key, value))
        conn.execute("INSERT INTO game_state (id, json) VALUES (1, ?)",
                     (json.dumps(payload),))
    conn.close()
    loaded = load_session(slot="v1", save_dir=save_dir)
    assert len(loaded.memory) == 0
    assert loaded.clock.turn == 3


def test_load_runs_invariants():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    save_session(session, slot="inv", save_dir=save_dir)
    # Corrupt inventory in the JSON
    path = slot_path("inv", save_dir)
    state, turn, recent, header, memory = read_save(path)
    state.character.inventory.append("rope")  # desync
    write_save(path, state, turn, recent, header["scenario_id"], memory)
    try:
        load_session(slot="inv", save_dir=save_dir)
        raised = False
    except Exception:
        raised = True
    assert raised


def test_save_format_is_v5():
    assert SAVE_FORMAT_VERSION == 5


def test_save_load_preserves_memory_archive_tier():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    rec = session.memory.add(
        "recent", "old archived scene", visibility="player", importance=10, created_turn=1
    )
    session.memory.archive_older_than(200, max_age=100)
    save_session(session, slot="archive", save_dir=save_dir)
    loaded = load_session(slot="archive", save_dir=save_dir)
    restored = loaded.memory.get(rec.id)
    assert restored is not None
    assert restored.tier == "archive"
