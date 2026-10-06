"""Scenario pack loader/validator tests."""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from engine.core.invariants import InvariantError
from engine.demo import build_demo_state
from engine.scenario.loader import ScenarioError, load_scenario


def _demo_pack_path() -> Path:
    return Path(__file__).resolve().parent.parent / "scenarios" / "demo-bootstrap"


def test_demo_world_is_loaded_from_pack():
    state = build_demo_state()
    assert state.character.name == "Wanderer"
    assert set(state.world.locations) == {"village", "forest", "cave"}
    assert state.world.npcs["elder"].personality.courage == 50


def test_directory_pack_metadata_and_lore():
    pack = load_scenario(_demo_pack_path())
    assert pack.scenario_id == "demo-bootstrap"
    assert pack.version == "1.0.0"
    assert "lore/README.md" in pack.lore_documents
    assert pack.build_state().world.items["rope"].location_id == "village"


def test_directory_pack_round_trips_through_zip():
    root = _demo_pack_path()
    temp = Path(tempfile.mkdtemp())
    archive = temp / "demo.rpgscenario.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in root.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(root).as_posix())
    pack = load_scenario(archive)
    assert pack.scenario_id == "demo-bootstrap"
    assert pack.build_state().world.npcs["wolf"].name == "grey wolf"


def test_missing_manifest_is_rejected():
    temp = Path(tempfile.mkdtemp())
    (temp / "world.json").write_text("{}", encoding="utf-8")
    try:
        load_scenario(temp)
        assert False
    except ScenarioError:
        pass


def test_unknown_reference_is_rejected_before_pack_use():
    temp = Path(tempfile.mkdtemp())
    (temp / "manifest.json").write_text(json.dumps({
        "pack_format": 1, "scenario_id": "bad-pack", "name": "Bad", "version": "1"
    }), encoding="utf-8")
    (temp / "world.json").write_text(json.dumps({
        "character": {"name": "P", "location_id": "missing"},
        "locations": {"town": "Town"}, "exits": {}, "items": {}, "npcs": {},
        "relationships": {}, "events": {}, "quests": {}
    }), encoding="utf-8")
    try:
        load_scenario(temp)
        assert False
    except InvariantError:
        pass


def test_unsupported_pack_format_is_rejected():
    temp = Path(tempfile.mkdtemp())
    (temp / "manifest.json").write_text(json.dumps({
        "pack_format": 999, "scenario_id": "bad-pack", "name": "Bad", "version": "1"
    }), encoding="utf-8")
    (temp / "world.json").write_text(json.dumps({"character": {}, "locations": {}}), encoding="utf-8")
    try:
        load_scenario(temp)
        assert False
    except ScenarioError:
        pass


def test_zip_path_traversal_is_rejected():
    temp = Path(tempfile.mkdtemp())
    archive = temp / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../manifest.json", "{}")
        z.writestr("world.json", "{}")
    try:
        load_scenario(archive)
        assert False
    except ScenarioError:
        pass


def test_v2_pack_exposes_machine_data_and_chapter_packs():
    pack = load_scenario(_demo_pack_path())
    assert "data/characters.json" in pack.data_documents
    assert len(pack.chapter_packs) == 1
    assert pack.chapter_packs[0].chapter_start == 1
    assert pack.chapter_packs[0].chapter_end == 1


def test_chapter_ranges_must_be_contiguous():
    temp = Path(tempfile.mkdtemp())
    (temp / "manifest.json").write_text(json.dumps({"pack_format": 2, "scenario_id": "bad-pack", "name": "Bad", "version": "1", "chapter_pack_size": 400}), encoding="utf-8")
    (temp / "world.json").write_text(json.dumps({"character": {}, "locations": {}}), encoding="utf-8")
    for name, start, end, seq in (("a",1,400,1),("b",500,800,2)):
        d=temp/"chapters"/name; d.mkdir(parents=True)
        (d/"chapter_manifest.json").write_text(json.dumps({"pack_id":name,"chapter_start":start,"chapter_end":end,"sequence":seq}),encoding="utf-8")
    try:
        load_scenario(temp)
        assert False
    except ScenarioError:
        pass


def _write_minimal_v2_with_chapters(root: Path, manifest_overrides=None):
    manifest = {
        "pack_format": 2,
        "scenario_id": "chapter-check",
        "name": "Chapter Check",
        "version": "1",
        "chapter_pack_size": 400,
        "chapter_count": 800,
        "chapter_packs": ["p1", "p2"],
    }
    manifest.update(manifest_overrides or {})
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "world.json").write_text(json.dumps({"character": {}, "locations": {}}), encoding="utf-8")
    for name, start, end, seq in (("p1", 1, 400, 1), ("p2", 401, 800, 2)):
        d = root / "chapters" / name
        d.mkdir(parents=True)
        (d / "chapter_manifest.json").write_text(json.dumps({
            "pack_id": name, "chapter_start": start, "chapter_end": end, "sequence": seq,
        }), encoding="utf-8")


def test_manifest_chapter_metadata_matches_actual_manifests():
    root = Path(tempfile.mkdtemp())
    _write_minimal_v2_with_chapters(root)
    pack = load_scenario(root)
    assert [p.pack_id for p in pack.chapter_packs] == ["p1", "p2"]


def test_manifest_chapter_count_mismatch_is_rejected():
    root = Path(tempfile.mkdtemp())
    _write_minimal_v2_with_chapters(root, {"chapter_count": 799})
    try:
        load_scenario(root)
        assert False
    except ScenarioError as exc:
        assert "chapter_count" in str(exc)


def test_manifest_chapter_pack_order_mismatch_is_rejected():
    root = Path(tempfile.mkdtemp())
    _write_minimal_v2_with_chapters(root, {"chapter_packs": ["p2", "p1"]})
    try:
        load_scenario(root)
        assert False
    except ScenarioError as exc:
        assert "chapter_packs" in str(exc)


def test_manifest_chapter_pack_size_is_enforced():
    root = Path(tempfile.mkdtemp())
    _write_minimal_v2_with_chapters(root, {"chapter_pack_size": 399})
    try:
        load_scenario(root)
        assert False
    except ScenarioError as exc:
        assert "chapter_pack_size" in str(exc)
