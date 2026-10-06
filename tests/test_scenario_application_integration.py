from pathlib import Path

from engine.app.controller import AppController
from engine.core.validation import apply_effects
from engine.rules.base import Effect
from engine.scenario.loader import load_scenario
from engine.persistence.saves import load_session

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "scenarios" / "demo-bootstrap"

def test_controller_start_scenario_threads_all_scenario_context():
    pack = load_scenario(DEMO)
    controller = AppController.demo()
    controller.start_scenario(pack)
    assert controller.session.scenario_registry is pack.registry
    assert controller.session.scenario_retriever is pack.retriever
    assert controller.session.scenario_configuration == controller.scenario_config
    assert controller.session.encounter_resolver.registry is pack.registry
    assert controller.session.event_engine.registry is pack.registry

def test_controller_save_load_preserves_scenario_context(tmp_path):
    pack = load_scenario(DEMO)
    controller = AppController.demo()
    controller.start_scenario(pack)
    controller.save(save_dir=tmp_path)
    controller.load(save_dir=tmp_path)
    assert controller.session.scenario_registry is pack.registry
    assert controller.session.scenario_retriever is pack.retriever
    assert controller.session.scenario_configuration == controller.scenario_config

def test_scenario_bootstrap_preserves_quest_prerequisites(tmp_path):
    import json
    import shutil
    data = json.loads((DEMO / "world.json").read_text(encoding="utf-8"))
    data.setdefault("quests", {})["q"] = {
        "id": "q", "title": "Q", "description": "", "status": "available",
        "prerequisites": [{"type": "level", "operator": ">=", "value": 99}],
    }
    fixture = tmp_path / "scenario"
    shutil.copytree(DEMO, fixture)
    (fixture / "world.json").write_text(json.dumps(data), encoding="utf-8")
    pack = load_scenario(fixture)
    assert pack.build_state().world.quests["q"].prerequisites

def test_shared_validation_gate_enforces_quest_prerequisites():
    pack = load_scenario(DEMO)
    state = pack.build_state()
    # Use a fresh quest with an unmet level prerequisite.
    from engine.core.state import QuestState
    state.world.quests["blocked"] = QuestState(id="blocked", title="Blocked", prerequisites=[{"type":"level","operator":">=","value":99}])
    report = apply_effects([Effect("quest", "blocked", "activate", True, "test")], state)
    assert not report.clean
    assert state.world.quests["blocked"].status == "available"
