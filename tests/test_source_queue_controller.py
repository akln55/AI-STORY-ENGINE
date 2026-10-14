from __future__ import annotations

import json

import pytest

from engine.ai.schema import StructuredResponse
from engine.app.controller import AppController
from engine.scenario.errors import ScenarioError
from engine.scenario.source_workspace import SourceWorkspaceManager


def _extraction_payload():
    return json.dumps({
        "entities": [{
            "category": "items",
            "id_candidate": "item_phone",
            "name": "Telefon",
            "aliases": ["cep telefonu"],
            "facts": [{
                "field": "summary",
                "value": "Telefon üzerinden haberler incelenebilir.",
                "support": "explicit",
                "evidence": {"location_hint": "ilk bölüm"},
            }],
        }],
        "relations": [],
        "unresolved": [],
    }, ensure_ascii=False)


class ScriptedAdapter:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        value = self.outputs.pop(0)
        return StructuredResponse(narrative=value)


def test_controller_processes_source_queue_and_only_saves_intermediate_candidates(tmp_path):
    adapter = ScriptedAdapter([_extraction_payload()])
    controller = AppController.demo(adapter=adapter)
    manager = SourceWorkspaceManager(tmp_path / "workspaces")
    controller._source_workspaces = manager
    source = tmp_path / "chapter.md"
    source.write_text("The player checks the phone for local news.", encoding="utf-8")
    workspace_id = controller.create_source_workspace("Survival", "Test source pipeline")
    controller.add_source_to_workspace(workspace_id, source, chapter_hint=1)
    initial_turn = controller.turn
    initial_location = controller.session.state.character.location_id

    processed = controller.process_source_queue(workspace_id)

    assert processed == 1
    assert len(adapter.prompts) == 1
    assert "The player checks the phone for local news." in adapter.prompts[0]
    assert manager.status(workspace_id)[0].status == "completed"
    results = manager.read_batch_results(workspace_id)
    assert results[0]["extraction"]["entities"][0]["id_candidate"] == "item_phone"
    assert controller.turn == initial_turn
    assert controller.session.state.character.location_id == initial_location
    assert controller.session.state.character.inventory == []


def test_controller_failed_extraction_checkpoint_can_be_retried(tmp_path):
    adapter = ScriptedAdapter(["not json", _extraction_payload()])
    controller = AppController.demo(adapter=adapter)
    manager = SourceWorkspaceManager(tmp_path / "workspaces")
    controller._source_workspaces = manager
    source = tmp_path / "chapter.txt"
    source.write_text("The phone has a cracked screen.", encoding="utf-8")
    workspace_id = controller.create_source_workspace("Retryable")
    controller.add_source_to_workspace(workspace_id, source)

    with pytest.raises(RuntimeError, match="Kaynak işleme durdu"):
        controller.process_source_queue(workspace_id)
    failed = manager.status(workspace_id)[0]
    assert failed.status == "failed"
    assert failed.chunks_completed == 0

    processed = controller.process_source_queue(workspace_id)
    assert processed == 1
    assert manager.status(workspace_id)[0].status == "completed"
    assert len(manager.read_batch_results(workspace_id)) == 1


def test_controller_requires_active_ai_provider_before_claiming_work(tmp_path):
    controller = AppController.demo(adapter=None)
    manager = SourceWorkspaceManager(tmp_path / "workspaces")
    controller._source_workspaces = manager
    source = tmp_path / "chapter.md"
    source.write_text("One chapter line.", encoding="utf-8")
    workspace_id = controller.create_source_workspace("No provider")
    controller.add_source_to_workspace(workspace_id, source)

    with pytest.raises(RuntimeError, match="AI modeli yok"):
        controller.process_source_queue(workspace_id)
    assert manager.status(workspace_id)[0].status == "pending"
    assert manager.read_batch_results(workspace_id) == ()
