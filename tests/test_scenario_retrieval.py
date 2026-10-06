"""Scenario retrieval and canonical Markdown indexing tests."""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path


from contextlib import contextmanager

@contextmanager
def raises(exc, match=None):
    try:
        yield
    except exc as caught:
        if match is not None and match not in str(caught):
            raise AssertionError(f"expected exception message to contain {match!r}, got {caught!r}")
        return
    raise AssertionError(f"expected {exc!r} to be raised")

from engine.scenario.loader import load_scenario
from engine.scenario.retrieval import ScenarioRetriever
from engine.scenario.errors import ScenarioError


DEMO = Path(__file__).resolve().parent.parent / "scenarios" / "demo-bootstrap"


def test_demo_indexes_lore_and_chapter_markdown_for_retrieval():
    pack = load_scenario(DEMO)
    assert pack.retriever is not None
    hits = pack.retriever.documents_for(query="development scenario", chapter=1)
    assert hits
    assert hits[0].document is not None
    assert hits[0].document.kind == "overview"
    assert hits[0].document.pack_id == "demo_0001_0001"


def test_demo_zip_and_directory_retrieval_are_equivalent():
    temp = Path(tempfile.mkdtemp())
    archive = temp / "demo.rpgscenario.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in DEMO.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(DEMO).as_posix())
    directory_pack = load_scenario(DEMO)
    zip_pack = load_scenario(archive)
    d = directory_pack.retriever.documents_for(query="chapter", chapter=1)
    z = zip_pack.retriever.documents_for(query="chapter", chapter=1)
    assert [(h.document.path, h.score) for h in d] == [(h.document.path, h.score) for h in z]


def test_record_retrieval_respects_first_appearance_chapter():
    retriever = ScenarioRetriever(load_scenario(DEMO).registry)
    early = retriever.record(category="characters", query="elder", chapter=1)
    future = retriever.record(category="characters", query="elder", chapter=0)
    assert early and early[0].record_id == "elder"
    assert not future


def test_record_retrieval_is_deterministic_with_stable_ties():
    retriever = ScenarioRetriever(load_scenario(DEMO).registry)
    first = retriever.record(category="characters", query="", limit=10)
    second = retriever.record(category="characters", query="", limit=10)
    assert [(h.record_id, h.score) for h in first] == [(h.record_id, h.score) for h in second]


def test_retrieval_limit_zero_returns_no_hits():
    pack = load_scenario(DEMO)
    assert pack.retriever.search("village", limit=0) == ()


def test_chapter_markdown_outside_declared_pack_is_rejected():
    root = Path(tempfile.mkdtemp())
    (root / "manifest.json").write_text(json.dumps({
        "pack_format": 2, "scenario_id": "bad-docs", "name": "Bad", "version": "1",
        "chapter_count": 1, "chapter_packs": ["p1"], "chapter_pack_size": 1,
    }), encoding="utf-8")
    (root / "world.json").write_text(json.dumps({"character": {}, "locations": {}}), encoding="utf-8")
    chapter = root / "chapters" / "p1"
    chapter.mkdir(parents=True)
    (chapter / "chapter_manifest.json").write_text(json.dumps({
        "pack_id": "p1", "chapter_start": 1, "chapter_end": 1, "sequence": 1,
    }), encoding="utf-8")
    (root / "chapters" / "unlisted.md").write_text("# Bad", encoding="utf-8")
    with raises(ScenarioError, match="outside a declared chapter pack"):
        load_scenario(root)


def test_invalid_markdown_utf8_becomes_scenario_error():
    root = Path(tempfile.mkdtemp())
    (root / "manifest.json").write_text(json.dumps({
        "pack_format": 2, "scenario_id": "bad-utf8", "name": "Bad", "version": "1",
    }), encoding="utf-8")
    (root / "world.json").write_text(json.dumps({"character": {}, "locations": {}}), encoding="utf-8")
    lore = root / "lore"
    lore.mkdir()
    (lore / "bad.md").write_bytes(b"# bad\xff")
    with raises(ScenarioError, match="UTF-8"):
        load_scenario(root)


def test_chapter_scoped_retrieval_excludes_global_lore_by_default():
    pack = load_scenario(DEMO)
    hits = pack.retriever.documents_for(query="development", chapter=1)
    assert all(h.document.scope == "chapter" for h in hits)
    hits_with_lore = pack.retriever.documents_for(query="development", chapter=1, include_global_lore=True)
    assert any(h.document.scope == "lore" for h in hits_with_lore)


def test_knowledge_visibility_and_chapter_timing_are_enforced():
    from engine.scenario.registry import ScenarioRegistry
    registry = ScenarioRegistry.from_documents({
        "knowledge.json": {
            "public_fact": {"id": "public_fact", "summary": "known fact", "visibility": "public", "known_from_chapter": 1},
            "future_fact": {"id": "future_fact", "summary": "future fact", "visibility": "public", "known_from_chapter": 10},
            "secret_fact": {"id": "secret_fact", "summary": "secret fact", "visibility": "secret"},
            "private_fact": {"id": "private_fact", "summary": "private fact", "known_by": ["npc:elder"]},
        }
    })
    retriever = ScenarioRetriever(registry)
    player = retriever.record(category="knowledge", query="fact", chapter=1, viewer="player", limit=10)
    ids = {h.record_id for h in player}
    assert "public_fact" in ids
    assert "future_fact" not in ids
    assert "secret_fact" not in ids
    assert "private_fact" not in ids
    npc = retriever.record(category="knowledge", query="fact", chapter=10, viewer="npc:elder", limit=10)
    npc_ids = {h.record_id for h in npc}
    assert "private_fact" in npc_ids
    system = retriever.record(category="knowledge", query="fact", chapter=10, viewer="system", limit=10)
    assert "secret_fact" in {h.record_id for h in system}


def test_indexed_retrieval_preserves_substring_matching_for_long_terms():
    pack = load_scenario(DEMO)
    hits = pack.retriever.documents_for(query="development", chapter=1, include_global_lore=True)
    assert any(h.document is not None and h.document.scope == "lore" for h in hits)


def test_indexed_record_retrieval_keeps_deterministic_order():
    pack = load_scenario(DEMO)
    first = pack.retriever.record(query="relic", limit=10)
    second = pack.retriever.record(query="relic", limit=10)
    assert [(h.category, h.record_id, h.score) for h in first] == [(h.category, h.record_id, h.score) for h in second]
