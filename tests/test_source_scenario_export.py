from __future__ import annotations

import json
import zipfile

import pytest

from engine.scenario.errors import ScenarioError
from engine.scenario.loader import load_scenario
from engine.scenario.source_workspace import SourceWorkspaceManager


def _extraction():
    return {
        "entities": [
            {
                "category": "locations", "id_candidate": "loc_apartment", "name": "Apartman",
                "aliases": ["daire"],
                "facts": [{
                    "field": "summary", "value": "Hikâyenin başlangıç apartmanı.",
                    "support": "explicit", "evidence": {"location_hint": "ilk sahne"},
                }],
            },
            {
                "category": "items", "id_candidate": "item_phone", "name": "Telefon",
                "aliases": ["cep telefonu"],
                "facts": [{
                    "field": "summary", "value": "Oyuncu telefondan haberleri kontrol edebilir.",
                    "support": "explicit", "evidence": {"location_hint": "telefon sahnesi"},
                }],
            },
        ],
        "relations": [{
            "source_id": "item_phone", "relation": "located_at",
            "target_id": "loc_apartment", "support": "explicit",
            "evidence": {"location_hint": "telefon apartmanda"},
        }],
        "unresolved": [{"description": "Bir haberin doğruluğu henüz belli değil."}],
    }


def _complete_workspace(manager, root):
    source = root / "chapter-01.md"
    source.write_text("# Bölüm 1\n\nTelefon apartmandadır.", encoding="utf-8")
    workspace_id = manager.create("Kırılma Noktası", "Test workspace")
    manager.add_source(workspace_id, source, chapter_hint=1)
    batch = manager.next_batch(workspace_id)
    assert batch is not None
    manager.complete_batch(batch, _extraction())
    return workspace_id


def test_candidate_index_preserves_conflicts_and_source_evidence(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = _complete_workspace(manager, tmp_path)
    index = manager.candidate_index(wid)

    assert index["source_batch_count"] == 1
    phone = next(item for item in index["entities"] if item["id_candidate"] == "item_phone")
    assert phone["aliases"] == ["cep telefonu"]
    assert phone["facts"][0]["source_provenance"]["source_name"] == "chapter-01.md"
    assert index["unresolved"][0]["description"] == "Bir haberin doğruluğu henüz belli değil."
    assert index["canonical_pack_modified"] is False


def test_export_builds_and_loads_scenario_without_touching_workspace_sources(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = _complete_workspace(manager, tmp_path)
    source_path = tmp_path / "ws" / wid / "sources"
    original = next(source_path.iterdir()).read_bytes()
    archive = tmp_path / "exports" / "survival.rpgscenario.zip"

    exported = manager.export_scenario_archive(
        wid, archive, scenario_id="survival-demo",
        scenario_name="Survival Demo", player_name="Player",
        start_location_id="loc_apartment",
    )

    assert exported.is_file()
    pack = load_scenario(exported)
    assert pack.scenario_id == "survival-demo"
    assert pack.build_state().character.location_id == "loc_apartment"
    assert "item_phone" in pack.build_state().world.items
    assert pack.build_state().world.items["item_phone"].location_id == "loc_apartment"
    assert next(source_path.iterdir()).read_bytes() == original
    with zipfile.ZipFile(exported) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["chapter_count"] == 1
        assert "lore/extraction-review.md" in bundle.namelist()
        assert "chapters/chapter_0001_0001/chapter.md" in bundle.namelist()


def test_export_refuses_unfinished_sources_conflicts_and_unknown_start_location(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    source = tmp_path / "pending.md"
    source.write_text("Not processed yet.", encoding="utf-8")
    wid = manager.create("Pending")
    manager.add_source(wid, source)

    with pytest.raises(ScenarioError, match="finish every source"):
        manager.export_scenario_archive(
            wid, tmp_path / "pending.rpgscenario.zip",
            scenario_id="pending-test", scenario_name="Pending",
            player_name="Player", start_location_id="loc_apartment",
        )

    batch = manager.next_batch(wid)
    assert batch is not None
    invalid = _extraction()
    invalid["entities"].append({
        "category": "locations", "id_candidate": "loc_apartment",
        "name": "Different Location", "aliases": [], "facts": [],
    })
    manager.complete_batch(batch, invalid)
    with pytest.raises(ScenarioError, match="conflicts"):
        manager.export_scenario_archive(
            wid, tmp_path / "conflict.rpgscenario.zip",
            scenario_id="pending-test", scenario_name="Pending",
            player_name="Player", start_location_id="loc_apartment",
        )

def test_candidate_index_flags_shared_names_without_automatic_merge(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    source = tmp_path / "duplicates.md"
    source.write_text("Two differently named people appear.", encoding="utf-8")
    wid = manager.create("Duplicates")
    manager.add_source(wid, source)
    batch = manager.next_batch(wid)
    assert batch is not None
    manager.complete_batch(batch, {
        "entities": [
            {"category": "characters", "id_candidate": "char_lee_1", "name": "Lee", "aliases": ["L."], "facts": []},
            {"category": "characters", "id_candidate": "char_lee_2", "name": "Different Person", "aliases": ["Lee"], "facts": []},
        ],
        "relations": [], "unresolved": [],
    })
    index = manager.candidate_index(wid)
    assert any(
        item["matching_name_or_alias"] == "lee"
        and item["candidate_ids"] == ["char_lee_1", "char_lee_2"]
        for item in index["possible_duplicates"]
    )
    assert {entity["id_candidate"] for entity in index["entities"]} == {"char_lee_1", "char_lee_2"}

def test_typed_relation_endpoints_resolve_duplicate_ids_across_categories(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    source = tmp_path / "typed-relations.md"
    source.write_text("The item is inside the place.", encoding="utf-8")
    wid = manager.create("Typed relation")
    manager.add_source(wid, source)
    batch = manager.next_batch(wid)
    assert batch is not None
    manager.complete_batch(batch, {
        "entities": [
            {"category": "locations", "id_candidate": "shared_id", "name": "Apartment", "aliases": [], "facts": []},
            {"category": "items", "id_candidate": "shared_id", "name": "Token", "aliases": [], "facts": []},
            {"category": "items", "id_candidate": "item_phone", "name": "Phone", "aliases": [], "facts": []},
        ],
        "relations": [{
            "source_id": "item_phone", "source_category": "items",
            "relation": "located_at", "target_id": "shared_id", "target_category": "locations",
            "support": "explicit", "evidence": {"location_hint": "scene"},
        }],
        "unresolved": [],
    })
    candidates = manager.candidate_index(wid)
    assert candidates["relations"][0]["target_category"] == "locations"
    archive = manager.export_scenario_archive(
        wid, tmp_path / "typed-relations.rpgscenario.zip",
        scenario_id="typed-relations", scenario_name="Typed Relations",
        player_name="Player", start_location_id="shared_id",
    )
    from engine.scenario.loader import load_scenario
    pack = load_scenario(archive)
    assert pack.build_state().world.items["item_phone"].location_id == "shared_id"

def test_user_confirmed_identity_merge_preserves_facts_aliases_and_relations(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    source = tmp_path / "identity-merge.md"
    source.write_text("Kim and Min-jae are the same character in this example.", encoding="utf-8")
    wid = manager.create("Identity merge")
    manager.add_source(wid, source)
    batch = manager.next_batch(wid)
    assert batch is not None
    manager.complete_batch(batch, {
        "entities": [
            {
                "category": "locations", "id_candidate": "loc_start", "name": "Apartment",
                "aliases": [], "facts": [],
            },
            {
                "category": "characters", "id_candidate": "char_kim", "name": "Kim",
                "aliases": ["K."], "facts": [{
                    "field": "summary", "value": "Kim lives nearby.",
                    "support": "explicit", "evidence": {"location_hint": "scene one"},
                }],
            },
            {
                "category": "characters", "id_candidate": "char_minjae", "name": "Min-jae",
                "aliases": ["Kim"], "facts": [{
                    "field": "location_id", "value": "loc_start",
                    "support": "explicit", "evidence": {"location_hint": "scene two"},
                }],
            },
        ],
        "relations": [{
            "source_id": "char_minjae", "source_category": "characters",
            "relation": "located_at", "target_id": "loc_start", "target_category": "locations",
            "support": "explicit", "evidence": {"location_hint": "scene two"},
        }],
        "unresolved": [],
    })

    before = manager.candidate_index(wid)
    assert before["possible_duplicates"]
    with pytest.raises(ScenarioError, match="possible duplicate"):
        manager.export_scenario_archive(
            wid, tmp_path / "blocked.rpgscenario.zip",
            scenario_id="identity-merge", scenario_name="Identity Merge",
            player_name="Player", start_location_id="loc_start",
        )

    after = manager.resolve_candidate_identity(
        wid, category="characters", source_id="char_minjae", target_id="char_kim",
    )
    assert not after["possible_duplicates"]
    assert not after["conflicts"]
    survivors = [entity for entity in after["entities"] if entity["category"] == "characters"]
    assert len(survivors) == 1
    survivor = survivors[0]
    assert survivor["id_candidate"] == "char_kim"
    assert survivor["name"] == "Kim"
    assert "Min-jae" in survivor["aliases"]
    assert {fact["field"] for fact in survivor["facts"]} == {"summary", "location_id"}
    assert after["relations"][0]["source_id"] == "char_kim"

    decisions = json.loads((tmp_path / "ws" / wid / "identity_decisions.json").read_text(encoding="utf-8"))
    assert decisions[0]["action"] == "merge_candidate_identity"
    assert decisions[0]["updated_relation_endpoints"] == 1

    archive = manager.export_scenario_archive(
        wid, tmp_path / "merged.rpgscenario.zip",
        scenario_id="identity-merge", scenario_name="Identity Merge",
        player_name="Player", start_location_id="loc_start",
    )
    pack = load_scenario(archive)
    assert pack.build_state().world.npcs["char_kim"].location_id == "loc_start"


def test_user_confirmed_canonical_name_choice_resolves_same_id_conflict(tmp_path):
    manager = SourceWorkspaceManager(tmp_path / "ws")
    wid = manager.create("Name conflict")
    for filename, name in (("one.md", "Kim"), ("two.md", "Min-jae")):
        source = tmp_path / filename
        source.write_text(f"Evidence naming {name}.", encoding="utf-8")
        manager.add_source(wid, source)
        batch = manager.next_batch(wid)
        assert batch is not None
        manager.complete_batch(batch, {
            "entities": [{
                "category": "characters", "id_candidate": "char_kim", "name": name,
                "aliases": [], "facts": [{
                    "field": "summary", "value": f"Known as {name}.",
                    "support": "explicit", "evidence": {"location_hint": filename},
                }],
            }],
            "relations": [], "unresolved": [],
        })

    before = manager.candidate_index(wid)
    assert before["conflicts"]
    after = manager.resolve_candidate_identity(
        wid, category="characters", source_id="char_kim", target_id="char_kim",
        preferred_name="Kim",
    )
    assert not after["conflicts"]
    assert len([item for item in after["entities"] if item["id_candidate"] == "char_kim"]) == 1
    survivor = after["entities"][0]
    assert survivor["name"] == "Kim"
    assert "Min-jae" in survivor["aliases"]
    assert len(survivor["facts"]) == 2
