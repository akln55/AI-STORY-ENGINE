"""Phase 2 persistence tests, including PROTOTYPE_MVP.md T4 (save/load round-trip)."""

import sqlite3
import tempfile
from pathlib import Path

from engine.cli import build_session
from engine.persistence.db import SAVE_FORMAT_VERSION, SaveError
from engine.persistence.saves import (
    DEMO_SCENARIO_ID, delete_slot, list_save_slots, load_session, save_session, slot_path,
)


def test_T4_save_load_roundtrip(tmp_path=None):
    """Move, take, attack -> save -> mutate -> load -> identical state."""
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    session.handle_input("go forest")
    session.handle_input("take mushroom")
    session.handle_input("attack wolf")
    turn_before = session.clock.turn
    recent_before = list(session.recent_turns)

    path = save_session(session, slot="hero", save_dir=save_dir)
    assert path.exists()

    # Mutate the live session after saving; load must NOT see these changes.
    session.handle_input("go village")
    session.handle_input("drop mushroom")
    session.state.character.hp = 1

    loaded = load_session(slot="hero", save_dir=save_dir)
    c, w = loaded.state.character, loaded.state.world
    assert c.location_id == "forest"
    assert "mushroom" in c.inventory
    assert w.items["mushroom"].owner == "player"
    assert w.npcs["wolf"].hp == w.npcs["wolf"].max_hp - 15
    assert c.hp == 95 and c.stamina == 90
    assert loaded.clock.turn == turn_before
    assert loaded.recent_turns == recent_before


def test_corrupted_save_rejected():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    save_session(session, slot="bad", save_dir=save_dir)
    path = slot_path("bad", save_dir)
    path.write_bytes(b"this is not a database")
    try:
        load_session(slot="bad", save_dir=save_dir)
        raised = False
    except SaveError:
        raised = True
    assert raised, "corrupt save must raise SaveError"


def test_wrong_version_rejected():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    save_session(session, slot="old", save_dir=save_dir)
    conn = sqlite3.connect(str(slot_path("old", save_dir)))
    with conn:
        conn.execute("UPDATE header SET value='999' WHERE key='save_format_version'")
    conn.close()
    try:
        load_session(slot="old", save_dir=save_dir)
        raised = False
    except SaveError as err:
        raised = "not supported" in str(err)
    assert raised, "wrong save_format_version must raise SaveError"


def test_scenario_isolation_refusal():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    save_session(session, slot="iso", save_dir=save_dir)
    try:
        load_session(slot="iso", save_dir=save_dir, scenario_id="other-world")
        raised = False
    except SaveError as err:
        raised = "scenario" in str(err)
    assert raised, "loading save into wrong scenario must raise SaveError"


def test_invalid_slot_names():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    for bad in ("", "a/b", "a\\b", "..", "a:b"):
        try:
            save_session(session, slot=bad, save_dir=save_dir)
            raised = False
        except SaveError:
            raised = True
        assert raised, f"slot {bad!r} must be rejected"


def test_missing_save_is_explicit_error():
    save_dir = Path(tempfile.mkdtemp())
    try:
        load_session(slot="ghost", save_dir=save_dir)
        raised = False
    except SaveError:
        raised = True
    assert raised


def test_save_overwrite_keeps_created_timestamp(tmp_path=None):
    import engine.persistence.db as db
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    save_session(session, slot="t", save_dir=save_dir)
    conn = sqlite3.connect(str(slot_path("t", save_dir)))
    created_first = conn.execute(
        "SELECT value FROM header WHERE key='created'").fetchone()[0]
    conn.close()
    session.handle_input("go forest")
    save_session(session, slot="t", save_dir=save_dir)
    conn = sqlite3.connect(str(slot_path("t", save_dir)))
    created_second = conn.execute(
        "SELECT value FROM header WHERE key='created'").fetchone()[0]
    modified = conn.execute(
        "SELECT value FROM header WHERE key='modified'").fetchone()[0]
    conn.close()
    assert created_first == created_second and modified


def test_save_records_demo_scenario_id():
    save_dir = Path(tempfile.mkdtemp())
    session = build_session()
    save_session(session, slot="id", save_dir=save_dir)
    loaded = load_session(slot="id", save_dir=save_dir,
                          scenario_id=DEMO_SCENARIO_ID)
    assert loaded.state.character.location_id == "village"

def test_quest_prerequisites_and_rewards_claimed_roundtrip(tmp_path):
    from engine.core.state import QuestState
    from engine.persistence.saves import save_session, load_session
    from engine.cli import build_session
    s = build_session()
    s.state.world.quests["q_round"] = QuestState(
        "q_round", "Roundtrip", prerequisites=[{"type": "level", "operator": ">=", "value": 2}],
        rewards=[{"type": "xp", "amount": 10}], rewards_claimed=True)
    save_session(s, slot="q", save_dir=tmp_path)
    loaded = load_session(slot="q", save_dir=tmp_path)
    q = loaded.state.world.quests["q_round"]
    assert q.prerequisites == [{"type": "level", "operator": ">=", "value": 2}]
    assert q.rewards_claimed is True


def test_overwrite_creates_last_known_good_backup(tmp_path):
    from engine.persistence.saves import backup_path
    session = build_session()
    save_session(session, slot="backup", save_dir=tmp_path)
    session.handle_input("go forest")
    save_session(session, slot="backup", save_dir=tmp_path)
    backup = backup_path("backup", tmp_path)
    assert backup.exists()
    recovered = load_session(slot="backup", save_dir=tmp_path)
    assert recovered.state.character.location_id == "forest"
    # The backup is the previous valid campaign state.
    primary = slot_path("backup", tmp_path)
    primary.write_bytes(b"corrupt")
    recovered = load_session(slot="backup", save_dir=tmp_path, recover=True)
    assert recovered.state.character.location_id == "village"


def test_recovery_is_explicit(tmp_path):
    from engine.persistence.saves import backup_path
    session = build_session()
    save_session(session, slot="explicit", save_dir=tmp_path)
    session.handle_input("go forest")
    save_session(session, slot="explicit", save_dir=tmp_path)
    slot_path("explicit", tmp_path).write_bytes(b"corrupt")
    try:
        load_session(slot="explicit", save_dir=tmp_path)
        raised = False
    except SaveError:
        raised = True
    assert raised
    assert backup_path("explicit", tmp_path).exists()


def test_campaign_identity_persists_across_overwrite(tmp_path):
    session = build_session()
    save_session(session, slot="campaign", save_dir=tmp_path,
                 campaign_id="campaign-001", campaign_name="First Journey")
    session.handle_input("go forest")
    save_session(session, slot="campaign", save_dir=tmp_path,
                 campaign_name="Renamed Journey")
    slots = list_save_slots(tmp_path)
    assert len(slots) == 1
    meta = slots[0]
    assert meta.valid is True
    assert meta.campaign_id == "campaign-001"
    assert meta.campaign_name == "Renamed Journey"
    assert meta.scenario_id == DEMO_SCENARIO_ID


def test_new_slots_get_distinct_campaign_identity(tmp_path):
    session = build_session()
    save_session(session, slot="a", save_dir=tmp_path, campaign_name="A")
    save_session(session, slot="b", save_dir=tmp_path, campaign_name="B")
    slots = {item.slot: item for item in list_save_slots(tmp_path)}
    assert set(slots) == {"a", "b"}
    assert slots["a"].campaign_id
    assert slots["b"].campaign_id
    assert slots["a"].campaign_id != slots["b"].campaign_id


def test_list_slots_reports_corrupt_slot_without_mutating_it(tmp_path):
    session = build_session()
    save_session(session, slot="good", save_dir=tmp_path)
    bad = slot_path("bad", tmp_path)
    bad.write_bytes(b"not sqlite")
    before = bad.read_bytes()
    slots = {item.slot: item for item in list_save_slots(tmp_path)}
    assert slots["good"].valid is True
    assert slots["bad"].valid is False
    assert bad.read_bytes() == before


def test_delete_slot_removes_primary_and_recovery_backup(tmp_path):
    session = build_session()
    save_session(session, slot="gone", save_dir=tmp_path)
    session.handle_input("go forest")
    save_session(session, slot="gone", save_dir=tmp_path)
    assert delete_slot("gone", tmp_path) is True
    assert not slot_path("gone", tmp_path).exists()
    assert not slot_path("gone", tmp_path).with_suffix(".db.bak").exists()
    assert list_save_slots(tmp_path) == []


def test_npc_combat_stats_roundtrip(tmp_path):
    """Every authoritative NPC combat/progression stat survives save/load."""
    session = build_session()
    npc = session.state.world.npcs["elder"]
    npc.hp = 17
    npc.max_hp = 83
    npc.attack_power = 41
    npc.defense = 23
    npc.xp_reward = 77
    npc.disposition = -31
    npc.alive = True
    save_session(session, slot="npc_stats", save_dir=tmp_path)
    loaded = load_session(slot="npc_stats", save_dir=tmp_path)
    restored = loaded.state.world.npcs["elder"]
    assert (restored.hp, restored.max_hp, restored.attack_power,
            restored.defense, restored.xp_reward, restored.disposition,
            restored.alive) == (17, 83, 41, 23, 77, -31, True)


def test_direct_load_restores_saved_scenario_configuration(tmp_path):
    """Persistence must restore runtime scenario configuration, not only JSON."""
    from engine.scenario.configuration import ScenarioConfiguration
    from engine.scenario.loader import load_scenario
    from engine.scenario.context import ScenarioContext

    pack = load_scenario(Path(__file__).resolve().parents[1] / "scenarios" / "demo-bootstrap")
    session = __import__("engine.core.game", fromlist=["GameSession"]).GameSession(
        pack.build_state(), scenario_registry=pack.registry,
        scenario_retriever=pack.retriever,
        scenario_configuration=ScenarioConfiguration.from_pack(pack),
    )
    save_session(
        session, slot="scenario_direct", save_dir=tmp_path,
        scenario_id=pack.scenario_id,
        scenario_config=session.scenario_configuration,
    )
    loaded = load_session(
        slot="scenario_direct", save_dir=tmp_path,
        scenario_id=pack.scenario_id,
        scenario_registry=pack.registry,
        scenario_retriever=pack.retriever,
    )
    assert loaded.scenario_configuration == session.scenario_configuration


def test_save_session_derives_scenario_identity_from_session_configuration(tmp_path):
    from engine.ai.fake import FakeAdapter
    from engine.core.game import GameSession
    from engine.scenario.loader import load_scenario
    from engine.scenario.context import ScenarioContext
    from engine.persistence.saves import save_session, load_session

    pack = load_scenario(Path(__file__).resolve().parents[1] / "scenarios" / "demo-bootstrap")
    session = GameSession.from_scenario_pack(pack, adapter=FakeAdapter())
    path = save_session(session, slot="derived", save_dir=tmp_path)
    loaded = load_session(
        slot="derived", save_dir=tmp_path, adapter=FakeAdapter(),
        scenario_context=ScenarioContext.from_pack(pack),
    )
    assert path.exists()
    assert loaded.scenario_configuration == session.scenario_configuration


def test_npc_goal_state_roundtrip(tmp_path):
    from engine.core.state import NPCGoal
    session = build_session()
    session.state.world.npcs["elder"].goals = [NPCGoal(
        "patrol", "Patrol the market", 9, status="active", kind="patrol",
        required_progress=4, progress=2, data={"locations": ["village", "forest"]},
    )]
    save_session(session, slot="npc_goal", save_dir=tmp_path)
    loaded = load_session(slot="npc_goal", save_dir=tmp_path)
    goal = loaded.state.world.npcs["elder"].goals[0]
    assert (goal.id, goal.kind, goal.required_progress, goal.progress, goal.data) == (
        "patrol", "patrol", 4, 2, {"locations": ["village", "forest"]}
    )


def test_new_save_records_canonical_engine_version(tmp_path):
    from engine import __version__
    session = build_session()
    save_session(session, slot="version", save_dir=tmp_path)
    conn = sqlite3.connect(str(slot_path("version", tmp_path)))
    value = conn.execute("SELECT value FROM header WHERE key='engine_version'").fetchone()[0]
    conn.close()
    assert value == __version__
