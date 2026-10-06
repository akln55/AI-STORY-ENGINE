from pathlib import Path
import json
import tempfile
import zipfile
import warnings


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

from engine.scenario.loader import ScenarioError, load_scenario
from engine.scenario.registry import CATEGORY_FILES

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "scenarios" / "demo-bootstrap"


def test_demo_registry_indexes_canonical_categories_and_ids():
    pack = load_scenario(DEMO)
    assert pack.registry is not None
    assert pack.registry.has("characters", "elder")
    assert pack.registry.require("locations", "village").data["name"] == "Sleepy Village"
    assert pack.registry.ids("items") == ("rope", "torch", "mushroom")
    assert pack.registry.find("characters", "first_appearance", 1)


def test_registry_is_immutable():
    pack = load_scenario(DEMO)
    record = pack.registry.require("items", "rope")
    with raises(TypeError):
        record.data["name"] = "changed"
    with raises(TypeError):
        pack.manifest["name"] = "changed"


def test_embedded_id_must_match_record_key():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "bad"
        (root / "data").mkdir(parents=True)
        (root / "manifest.json").write_text(json.dumps({"scenario_id":"bad","name":"Bad","version":"1"}))
        (root / "world.json").write_text(json.dumps({"character":{},"locations":{}}))
        (root / "data" / "characters.json").write_text(json.dumps({"hero":{"id":"other","name":"Hero"}}))
        with raises(ScenarioError, match="embedded id must match key"):
            load_scenario(root)


def test_missing_stable_id_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "bad"
        (root / "data").mkdir(parents=True)
        (root / "manifest.json").write_text(json.dumps({"scenario_id":"bad","name":"Bad","version":"1"}))
        (root / "world.json").write_text(json.dumps({"character":{},"locations":{}}))
        (root / "data" / "characters.json").write_text(json.dumps({"hero":{"name":"Hero"}}))
        with raises(ScenarioError, match="missing a stable id"):
            load_scenario(root)


def test_cross_references_are_validated():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "bad"
        (root / "data").mkdir(parents=True)
        (root / "manifest.json").write_text(json.dumps({"scenario_id":"bad","name":"Bad","version":"1"}))
        (root / "world.json").write_text(json.dumps({"character":{},"locations":{}}))
        (root / "data" / "characters.json").write_text(json.dumps({"hero":{"id":"hero","name":"Hero","references":{"locations":["missing"]}}}))
        with raises(ScenarioError, match="references missing"):
            load_scenario(root)


def test_cross_references_can_target_existing_records():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "ok"
        (root / "data").mkdir(parents=True)
        (root / "manifest.json").write_text(json.dumps({"scenario_id":"ok","name":"OK","version":"1"}))
        (root / "world.json").write_text(json.dumps({"character":{},"locations":{}}))
        (root / "data" / "locations.json").write_text(json.dumps({"village":{"id":"village","name":"Village"}}))
        (root / "data" / "characters.json").write_text(json.dumps({"hero":{"id":"hero","name":"Hero","references":{"locations":["village"]}}}))
        pack = load_scenario(root)
        assert pack.registry.has("characters", "hero")


def test_unknown_data_file_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "bad"
        (root / "data").mkdir(parents=True)
        (root / "manifest.json").write_text(json.dumps({"scenario_id":"bad","name":"Bad","version":"1"}))
        (root / "world.json").write_text(json.dumps({"character":{},"locations":{}}))
        (root / "data" / "unknown.json").write_text("{}")
        with raises(ScenarioError, match="unsupported canonical scenario data path"):
            load_scenario(root)


def test_zip_duplicate_names_are_rejected():
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "dup.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("manifest.json", json.dumps({"scenario_id":"dup","name":"Dup","version":"1"}))
                z.writestr("manifest.json", json.dumps({"scenario_id":"dup","name":"Dup2","version":"1"}))
                z.writestr("world.json", json.dumps({"character":{},"locations":{}}))
        with raises(ScenarioError, match="duplicate file names"):
            load_scenario(archive)


def test_zip_pack_exposes_same_registry():
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "demo.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for path in DEMO.rglob("*"):
                if path.is_file():
                    z.write(path, path.relative_to(DEMO).as_posix())
        pack = load_scenario(archive)
        assert pack.registry.require("characters", "elder").data["name"] == "village elder"


def test_nested_manifest_and_world_data_are_immutable():
    pack = load_scenario(DEMO)
    with raises((TypeError, AttributeError)):
        pack.manifest["chapter_packs"].append("x")
    with raises(TypeError):
        pack.world_payload["locations"]["village"] = "changed"


def test_zip_unknown_canonical_data_path_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "bad.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("manifest.json", json.dumps({"scenario_id":"bad","name":"Bad","version":"1"}))
            z.writestr("world.json", json.dumps({"character":{},"locations":{}}))
            z.writestr("data/custom.json", "{}")
        with raises(ScenarioError, match="unsupported canonical scenario data path"):
            load_scenario(archive)


def test_chapter_manager_indexes_order_and_lookup():
    pack = load_scenario(DEMO)
    manager = pack.chapter_manager
    assert manager is not None
    assert manager.pack_ids == ("demo_0001_0001",)
    assert manager.chapter_count == 1
    assert manager.pack_for_chapter(1).pack_id == "demo_0001_0001"


def test_scenario_configuration_binds_scenario_version_and_selection():
    pack = load_scenario(DEMO)
    from engine.scenario.configuration import ScenarioConfiguration
    config = ScenarioConfiguration.from_pack(pack, mode="sequential", start_chapter=1)
    assert config.scenario_id == pack.scenario_id
    assert config.scenario_version == pack.version
    assert config.selected_pack_ids == pack.chapter_manager.pack_ids
    assert config.current_chapter == 1


def test_scenario_configuration_rejects_unknown_or_duplicate_packs():
    pack = load_scenario(DEMO)
    from engine.scenario.configuration import ScenarioConfiguration
    with raises(ScenarioError, match="unknown chapter pack"):
        ScenarioConfiguration.from_pack(pack, selected_pack_ids=("missing",))
    with raises(ScenarioError, match="duplicates"):
        ScenarioConfiguration.from_pack(pack, selected_pack_ids=("demo_0001_0001", "demo_0001_0001"))


def test_scenario_configuration_rejects_invalid_mode_and_chapter():
    pack = load_scenario(DEMO)
    from engine.scenario.configuration import ScenarioConfiguration
    with raises(ScenarioError, match="scenario mode"):
        ScenarioConfiguration.from_pack(pack, mode="invalid")
    with raises(ScenarioError, match="not available"):
        ScenarioConfiguration.from_pack(pack, start_chapter=2)


def test_scenario_configuration_is_immutable():
    pack = load_scenario(DEMO)
    from engine.scenario.configuration import ScenarioConfiguration
    config = ScenarioConfiguration.from_pack(pack)
    with raises(AttributeError):
        config.current_chapter = 2


def test_free_mode_can_select_noncontiguous_packs_without_reordering_canon():
    from engine.scenario.chapters import ChapterManager
    from engine.scenario.loader import ChapterPack
    from engine.scenario.configuration import ScenarioConfiguration
    packs = (
        ChapterPack("p1", 1, 10, 1),
        ChapterPack("p2", 11, 20, 2),
        ChapterPack("p3", 21, 30, 3),
    )
    manager = ChapterManager(packs)
    manager.validate_selection(("p3", "p1"), require_contiguous=False)
    config = ScenarioConfiguration("s", "1", "free", ("p3", "p1"), 21, 21)
    assert config.selected_pack_ids == ("p3", "p1")
    with raises(ScenarioError, match="canonical scenario order"):
        manager.validate_selection(("p3", "p1"))


def test_scenario_configuration_round_trip_and_pack_binding():
    from engine.scenario.configuration import ScenarioConfiguration
    pack = load_scenario(DEMO)
    config = ScenarioConfiguration.from_pack(pack)
    restored = ScenarioConfiguration.from_dict(config.to_dict())
    restored.validate_against(pack)
    assert restored == config

    wrong = ScenarioConfiguration("other", pack.version, "sequential", config.selected_pack_ids, 1, 1)
    with raises(ScenarioError, match="belongs to scenario"):
        wrong.validate_against(pack)


def test_free_mode_configuration_can_retain_explicit_pack_order():
    from engine.scenario.chapters import ChapterManager
    from engine.scenario.configuration import ScenarioConfiguration
    from engine.scenario.loader import ChapterPack
    packs = (ChapterPack("p1", 1, 10, 1), ChapterPack("p2", 11, 20, 2), ChapterPack("p3", 21, 30, 3))
    manager = ChapterManager(packs)
    manager.validate_selection(("p3", "p1"), require_contiguous=False)
    config = ScenarioConfiguration("s", "1", "free", ("p3", "p1"), 21, 21)
    assert config.to_dict()["selected_pack_ids"] == ["p3", "p1"]
