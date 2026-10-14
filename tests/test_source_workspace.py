from __future__ import annotations

import json

import pytest

from engine.scenario.errors import ScenarioError
from engine.scenario.source_workspace import SourceWorkspaceManager


def _valid_extraction(name="Telefon"):
    return {
        "entities": [{
            "category": "items",
            "id_candidate": "item_phone",
            "name": name,
            "aliases": ["telefon"],
            "facts": [{
                "field": "summary",
                "value": "Oyuncunun telefonundan haberleri kontrol edebildiği anlatılır.",
                "support": "explicit",
                "evidence": {"location_hint": "telefon sahnesi"},
            }],
        }],
        "relations": [],
        "unresolved": [],
    }


def test_workspace_copies_source_bytes_and_lists_durable_metadata(tmp_path):
    source = tmp_path / "chapter-01.md"
    source.write_bytes(b"# Bolum 1\n\nMerhaba dunya.\n")
    manager = SourceWorkspaceManager(tmp_path / "workspaces")
    workspace_id = manager.create("Kirilma Noktasi", "Survival scenario")

    added = manager.add_source(workspace_id, source, chapter_hint=1)

    assert added.sequence == 1
    assert added.status == "pending"
    workspace = SourceWorkspaceManager(tmp_path / "workspaces").get_workspace(workspace_id)
    stored = tmp_path / "workspaces" / workspace_id / "sources" / workspace["sources"][0]["stored_name"]
    assert stored.read_bytes() == source.read_bytes()
    assert workspace["sources"][0]["sha256"] == added.sha256
    assert manager.list_workspaces()[0]["source_count"] == 1


def test_workspace_rejects_unsupported_empty_invalid_and_oversize_sources(tmp_path, monkeypatch):
    manager = SourceWorkspaceManager(tmp_path / "workspaces")
    workspace_id = manager.create("Test")
    unsupported = tmp_path / "chapter.pdf"
    unsupported.write_bytes(b"not parsed")
    with pytest.raises(ScenarioError, match="unsupported source type"):
        manager.add_source(workspace_id, unsupported)

    empty = tmp_path / "empty.md"
    empty.write_text("  \n", encoding="utf-8")
    with pytest.raises(ScenarioError, match="empty"):
        manager.add_source(workspace_id, empty)

    from engine.scenario import source_workspace as source_module
    oversized = tmp_path / "oversized.txt"
    oversized.write_text("more than three bytes", encoding="utf-8")
    monkeypatch.setattr(source_module, "MAX_SOURCE_BYTES", 3)
    with pytest.raises(ScenarioError, match="exceeds"):
        manager.add_source(workspace_id, oversized)

    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff\xfe\x80")
    with pytest.raises(ScenarioError, match="UTF-8"):
        manager.add_source(workspace_id, invalid)


def test_source_reordering_is_stable_and_validated(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "workspaces")
    wid = manager.create("Ordering")
    first_path, second_path, third_path = (tmp_path / f"{name}.txt" for name in ("a", "b", "c"))
    for path in (first_path, second_path, third_path):
        path.write_text(path.stem * 12, encoding="utf-8")
    a = manager.add_source(wid, first_path)
    b = manager.add_source(wid, second_path)
    c = manager.add_source(wid, third_path)

    statuses = manager.reorder_source(wid, c.source_id, -1)
    assert [(s.name, s.sequence) for s in statuses] == [("a.txt", 1), ("c.txt", 2), ("b.txt", 3)]
    statuses = manager.reorder_source(wid, a.source_id, -1)
    assert [(s.name, s.sequence) for s in statuses] == [("a.txt", 1), ("c.txt", 2), ("b.txt", 3)]
    with pytest.raises(ScenarioError, match="delta"):
        manager.reorder_source(wid, b.source_id, 0)


def test_chunk_checkpoint_survives_manager_restart_and_does_not_repeat_completed_batch(tmp_path):
    root = tmp_path / "workspaces"
    source = tmp_path / "chapter.md"
    source.write_text(("\n\n".join(f"Paragraph {i}: story facts and setting." for i in range(50))), encoding="utf-8")
    manager = SourceWorkspaceManager(root)
    wid = manager.create("Long Story")
    added = manager.add_source(wid, source, chapter_hint=1)

    first_batch = manager.next_batch(wid, chunk_chars=300, overlap=40)
    assert first_batch is not None
    assert first_batch.source_id == added.source_id
    output = manager.complete_batch(first_batch, _valid_extraction())
    assert output.is_file()
    first_id = first_batch.batch_id

    restarted = SourceWorkspaceManager(root)
    next_batch = restarted.next_batch(wid, chunk_chars=300, overlap=40)
    assert next_batch is not None
    assert next_batch.batch_id != first_id
    assert next_batch.chunk_index == 1
    status = restarted.status(wid)[0]
    assert status.chunks_completed == 1
    assert status.chunks_total > 1

    restarted_again = SourceWorkspaceManager(root)
    retry = restarted_again.next_batch(wid, chunk_chars=300, overlap=40)
    assert retry is not None
    assert retry.batch_id == next_batch.batch_id


def test_completed_batches_keep_source_provenance_and_validated_candidates(tmp_path):
    source = tmp_path / "one.txt"
    source.write_text("The phone is in the apartment.", encoding="utf-8")
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = manager.create("Provenance")
    added = manager.add_source(wid, source)
    selected = manager.next_batch(wid)
    assert selected is not None
    path = manager.complete_batch(selected, _valid_extraction("Phone"))
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["batch_id"] == selected.batch_id
    assert stored["provenance"]["source_name"] == "one.txt"
    assert stored["provenance"]["source_sha256"] == added.sha256
    assert stored["extraction"]["entities"][0]["category"] == "items"
    assert manager.status(wid)[0].status == "completed"
    assert len(manager.read_batch_results(wid)) == 1
    assert manager.next_batch(wid) is None


def test_failed_batch_can_resume_and_keeps_a_bounded_error(tmp_path):
    source = tmp_path / "text.txt"
    source.write_text("A sufficiently long story paragraph for an extraction batch.", encoding="utf-8")
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = manager.create("Retry")
    manager.add_source(wid, source)
    batch = manager.next_batch(wid)
    assert batch is not None
    status = manager.fail_batch(batch, "  request failed\n" + "x" * 1000)
    assert status.status == "failed"
    assert len(status.last_error) <= 500
    resumed = SourceWorkspaceManager(tmp_path / "ws").next_batch(wid)
    assert resumed is not None
    assert resumed.batch_id == batch.batch_id


def test_invalid_extraction_never_advances_checkpoint(tmp_path):
    source = tmp_path / "story.md"
    source.write_text("The phone is important.", encoding="utf-8")
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = manager.create("Validation")
    manager.add_source(wid, source)
    batch = manager.next_batch(wid)
    assert batch is not None
    with pytest.raises(ScenarioError, match="unsupported category"):
        manager.complete_batch(batch, {
            "entities": [{"category": "objects", "id_candidate": "item_x", "name": "Phone"}],
            "relations": [],
            "unresolved": [],
        })
    status = manager.status(wid)[0]
    assert status.chunks_completed == 0
    assert manager.read_batch_results(wid) == ()


def test_extraction_parser_accepts_fenced_json_and_rejects_malformed_content():
    fence = chr(96) * 3
    parsed = SourceWorkspaceManager.parse_extraction_response(
        fence + 'json\n{"entities":[],"relations":[],"unresolved":[]}\n' + fence
    )
    assert parsed == {"entities": [], "relations": [], "unresolved": []}
    with pytest.raises(ScenarioError, match="valid JSON"):
        SourceWorkspaceManager.parse_extraction_response("Here are some story facts, not JSON.")


def test_extraction_prompt_contains_order_provenance_and_no_runtime_mutation_permission(tmp_path):
    source = tmp_path / "story.txt"
    source.write_text("A person enters the hospital.", encoding="utf-8")
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = manager.create("Prompt")
    manager.add_source(wid, source, chapter_hint=7)
    batch = manager.next_batch(wid)
    assert batch is not None
    prompt = manager.build_extraction_prompt(batch, existing_entities=[
        {"category": "locations", "id": "loc_hospital", "name": "Hospital"}
    ])
    assert "chapter_hint" in prompt
    assert "loc_hospital" in prompt
    assert "Do not write canonical files or mutate gameplay state" in prompt
    assert "A person enters the hospital." in prompt

def test_source_order_and_removal_lock_after_first_checkpoint(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    source_a = tmp_path / "a.md"
    source_b = tmp_path / "b.md"
    source_a.write_text("First chapter source.", encoding="utf-8")
    source_b.write_text("Second chapter source.", encoding="utf-8")
    wid = manager.create("Locked order")
    a = manager.add_source(wid, source_a)
    b = manager.add_source(wid, source_b)
    batch = manager.next_batch(wid)
    assert batch is not None
    manager.complete_batch(batch, {
        "entities": [{
            "category": "locations", "id_candidate": "loc_start", "name": "Starting location",
            "aliases": [], "facts": [],
        }],
        "relations": [], "unresolved": [],
    })
    with pytest.raises(ScenarioError, match="order is locked"):
        manager.reorder_source(wid, b.source_id, -1)
    with pytest.raises(ScenarioError, match="cannot remove"):
        manager.remove_source(wid, a.source_id)
