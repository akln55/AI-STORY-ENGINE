"""v1.5 deterministic quest foundation tests."""

import json
import sqlite3
import tempfile
from pathlib import Path

from engine.core.invariants import InvariantError, check_invariants
from engine.core.state import QuestObjective, QuestState
from engine.core.validation import apply_effects
from engine.cli import build_session
from engine.persistence.saves import load_session, save_session
from engine.quest.system import activate_quest, abandon_quest, evaluate_quests
from engine.rules.base import Effect


def _quest():
    return QuestState(
        id="find_relic", title="Find the Relic", description="Recover the relic.",
        status="available", giver="elder",
        objectives=[QuestObjective(
            id="collect_relic", description="Recover the relic", type="collect",
            target_id="rope", required_count=1,
        )],
        rewards=[{"type": "resource", "target": "player", "value": 50}],
    )


def test_quest_activation_and_collect_completion():
    s = build_session()
    s.state.world.quests["find_relic"] = _quest()
    activate_quest(s.state, "find_relic")
    assert s.state.world.quests["find_relic"].status == "active"
    report = apply_effects([Effect("inventory", "rope", "take", None)], s.state)
    assert report.clean
    evaluation = evaluate_quests(s.state)
    q = s.state.world.quests["find_relic"]
    assert evaluation.completed_quest_ids == ("find_relic",)
    assert q.status == "completed"
    assert q.objectives[0].completed


def test_reach_objective_is_authoritative():
    s = build_session()
    s.state.world.quests["travel"] = QuestState(
        id="travel", title="Travel", status="active",
        objectives=[QuestObjective("reach", "Reach town", "reach", "forest")],
    )
    assert evaluate_quests(s.state).completed_quest_ids == ()
    assert apply_effects([Effect("location", "player", "move", "forest")], s.state).clean
    assert evaluate_quests(s.state).completed_quest_ids == ("travel",)


def test_defeat_objective_uses_npc_state_not_narrative():
    s = build_session()
    s.state.world.quests["defeat"] = QuestState(
        id="defeat", title="Defeat Wolf", status="active",
        objectives=[QuestObjective("kill", "Defeat guard", "defeat", "wolf")],
    )
    assert evaluate_quests(s.state).completed_quest_ids == ()
    assert apply_effects([Effect("resource", "wolf.hp", "set", 0)], s.state).clean
    assert s.state.world.npcs["wolf"].alive is False
    assert evaluate_quests(s.state).completed_quest_ids == ("defeat",)


def test_talk_objective_does_not_complete_from_narrative_or_generic_evaluation():
    s = build_session()
    s.state.world.quests["talk"] = QuestState(
        id="talk", title="Talk", status="active",
        objectives=[QuestObjective("talk", "Talk to elder", "talk", "elder")],
    )
    assert evaluate_quests(s.state).completed_quest_ids == ()
    assert s.state.world.quests["talk"].status == "active"


def test_ai_cannot_mutate_quest_through_npc_changes():
    s = build_session()
    s.state.world.quests["q"] = _quest()
    report = apply_effects(
        [Effect("npc", "elder", "set", ("goals", []))], s.state
    )
    assert report.rejected


def test_invalid_quest_reference_detected_by_invariants():
    s = build_session()
    s.state.world.quests["bad"] = QuestState(
        id="bad", title="Bad", status="active",
        objectives=[QuestObjective("x", "Reach nowhere", "reach", "missing")],
    )
    try:
        check_invariants(s.state)
        raised = False
    except InvariantError:
        raised = True
    assert raised


def test_quest_save_load_roundtrip():
    save_dir = Path(tempfile.mkdtemp())
    s = build_session()
    s.state.world.quests["find_relic"] = _quest()
    activate_quest(s.state, "find_relic")
    path = save_session(s, slot="quest", save_dir=save_dir)
    loaded = load_session(slot="quest", save_dir=save_dir)
    q = loaded.state.world.quests["find_relic"]
    assert q.status == "active"
    assert q.giver == "elder"
    assert q.objectives[0].target_id == "rope"
    assert q.rewards[0]["value"] == 50


def test_old_save_without_quests_loads():
    save_dir = Path(tempfile.mkdtemp())
    s = build_session()
    path = save_session(s, slot="old", save_dir=save_dir)
    conn = sqlite3.connect(str(path))
    row = conn.execute("SELECT json FROM game_state WHERE id=1").fetchone()
    payload = json.loads(row[0])
    payload["world"].pop("quests", None)
    with conn:
        conn.execute("UPDATE game_state SET json=? WHERE id=1", (json.dumps(payload),))
    conn.close()
    loaded = load_session(slot="old", save_dir=save_dir)
    assert loaded.state.world.quests == {}


def test_abandon_only_active_quest():
    s = build_session()
    s.state.world.quests["q"] = _quest()
    activate_quest(s.state, "q")
    abandon_quest(s.state, "q")
    assert s.state.world.quests["q"].status == "abandoned"


def test_quest_xp_reward_is_applied_once():
    s = build_session()
    s.state.world.quests["rewarded"] = QuestState(
        id="rewarded", title="Rewarded", status="active",
        objectives=[QuestObjective("reach", "Reach forest", "reach", "forest")],
        rewards=[{"type": "xp", "amount": 25}],
    )
    apply_effects([Effect("location", "player", "move", "forest")], s.state)
    assert evaluate_quests(s.state).completed_quest_ids == ("rewarded",)
    assert s.state.character.xp == 25
    evaluate_quests(s.state)
    assert s.state.character.xp == 25
    assert s.state.world.quests["rewarded"].rewards_claimed is True


def test_quest_resource_and_relationship_rewards():
    s = build_session()
    s.state.character.hp = 50
    s.state.world.quests["rewarded"] = QuestState(
        id="rewarded", title="Rewarded", status="active",
        objectives=[QuestObjective("talk", "Talk to elder", "talk", "elder")],
        rewards=[
            {"type": "resource", "target": "player.hp", "operation": "add", "amount": 10},
            {"type": "relationship", "target": "player|elder", "field": "trust", "operation": "add", "amount": 5},
        ],
    )
    evaluate_quests(s.state, talked_to="elder")
    assert s.state.character.hp == 60
    assert s.state.world.get_relationship("player", "elder").trust == 5
    assert s.state.world.quests["rewarded"].rewards_claimed is True


def test_quest_reward_transaction_rolls_back_completion_on_invalid_reward():
    s = build_session()
    q = QuestState(
        id="atomic", title="Atomic", status="active",
        objectives=[QuestObjective("obj", "Take rope", "collect", "rope")],
        rewards=[{"type": "relationship", "target": "missing|npc", "field": "trust", "amount": 10}],
    )
    s.state.world.quests[q.id] = q
    assert apply_effects([Effect("inventory", "rope", "take", None)], s.state).clean
    result = evaluate_quests(s.state)
    assert result.completed_quest_ids == ()
    assert q.status == "active"
    assert not q.rewards_claimed


def test_quest_deadline_fails_and_unlocks_followup():
    s = build_session()
    s.state.world.quests["expired"] = QuestState(
        id="expired", title="Timed", status="active",
        expires_turn=2, unlocks_on_fail=["failure_followup"],
        objectives=[QuestObjective("obj", "Reach forest", "reach", "forest")],
    )
    s.state.world.quests["failure_followup"] = QuestState(
        id="failure_followup", title="Failure Followup", status="available",
        objectives=[QuestObjective("obj", "Reach forest", "reach", "forest")],
    )
    result = evaluate_quests(s.state, current_turn=3)
    assert result.failed_quest_ids == ("expired",)
    assert "failure_followup" in result.activated_quest_ids
    assert s.state.world.quests["expired"].failed_turn == 3
    assert s.state.world.quests["failure_followup"].status == "active"


def test_quest_completion_unlocks_followup_and_persists_round_trip():
    import tempfile
    from pathlib import Path
    from engine.persistence.saves import save_session, load_session

    s = build_session()
    s.state.world.quests["first"] = QuestState(
        id="first", title="First", status="active",
        unlocks_on_complete=["second"],
        objectives=[QuestObjective("obj", "Take rope", "collect", "rope")],
        rewards=[{"type": "xp", "amount": 10}],
    )
    s.state.world.quests["second"] = QuestState(
        id="second", title="Second", status="available",
        objectives=[QuestObjective("obj", "Reach forest", "reach", "forest")],
    )
    assert apply_effects([Effect("inventory", "rope", "take", None)], s.state).clean
    result = evaluate_quests(s.state, current_turn=4)
    assert result.completed_quest_ids == ("first",)
    assert result.activated_quest_ids == ("second",)
    assert s.state.world.quests["first"].completed_turn == 4
    assert s.state.world.quests["second"].status == "active"
    with tempfile.TemporaryDirectory() as td:
        save_session(s, "questchain", Path(td))
        loaded = load_session("questchain", Path(td))
        assert loaded.state.world.quests["first"].completed_turn == 4
        assert loaded.state.world.quests["second"].status == "active"
