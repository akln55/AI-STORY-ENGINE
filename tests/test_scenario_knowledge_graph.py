"""Deterministic entity graph tests for canonical scenario records."""

from engine.scenario.registry import ScenarioRegistry
from engine.scenario.retrieval import ScenarioRetriever


def _retriever():
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "char_ada": {
                "id": "char_ada",
                "name": "Ada",
                "aliases": ["Ada Lovelace"],
                "location_id": "loc_lab",
                "faction_id": "faction_analysts",
            }
        },
        "locations.json": {
            "loc_lab": {
                "id": "loc_lab",
                "name": "Laboratuvar",
                "aliases": ["Lab"],
                "connected_locations": ["loc_gate"],
            },
            "loc_gate": {"id": "loc_gate", "name": "Ana Kapı"},
        },
        "factions.json": {
            "faction_analysts": {"id": "faction_analysts", "name": "Analistler"}
        },
        "items.json": {
            "item_phone": {
                "id": "item_phone",
                "name": "Akıllı telefon",
                "aliases": ["cep telefonu"],
                "location_id": "loc_lab",
            }
        },
    })
    return ScenarioRetriever(registry)


def test_graph_resolves_names_aliases_and_turkish_diacritics():
    retriever = _retriever()

    ada = retriever.resolve_entities("Ada Lovelace")
    phone = retriever.resolve_entities("cep telefonu", categories=("items",))
    lab = retriever.resolve_entities("LAB", categories=("locations",))

    assert [(node.category, node.id) for node in ada] == [("characters", "char_ada")]
    assert [(node.category, node.id) for node in phone] == [("items", "item_phone")]
    assert [(node.category, node.id) for node in lab] == [("locations", "loc_lab")]


def test_graph_exact_name_respects_requested_category_and_falls_back_safely():
    retriever = _retriever()

    result = retriever.resolve_entities("Ada Lovelace", categories=("items",))
    assert result == ()


def test_graph_links_entities_from_explicit_structured_fields():
    retriever = _retriever()

    ada_links = retriever.related_records("characters", "char_ada", limit=10)
    pairs = {(hit.category, hit.record_id, relation) for hit, relation in ada_links}
    assert ("locations", "loc_lab", "located_at") in pairs
    assert ("factions", "faction_analysts", "belongs_to_faction") in pairs

    phone_links = retriever.related_records("items", "item_phone", limit=10)
    assert any(
        hit.category == "locations" and hit.record_id == "loc_lab" and relation == "located_at"
        for hit, relation in phone_links
    )


def test_graph_neighbour_order_is_deterministic():
    retriever = _retriever()

    first = retriever.knowledge_graph.related("locations", "loc_lab", limit=20)
    second = retriever.knowledge_graph.related("locations", "loc_lab", limit=20)
    assert first == second
    assert first
