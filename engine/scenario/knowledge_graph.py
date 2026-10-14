"""A deterministic, provenance-preserving graph over canonical scenario entities.

This v1 graph links entities already declared in canonical JSON. It does not guess
new facts from prose; source-text entity extraction is a separate ingestion stage.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Iterable, Mapping

from engine.scenario.registry import ScenarioRecord, ScenarioRegistry

NodeKey = tuple[str, str]


@dataclass(frozen=True, order=True)
class KnowledgeNode:
    category: str
    id: str
    name: str
    aliases: tuple[str, ...]
    summary: str


@dataclass(frozen=True, order=True)
class KnowledgeEdge:
    source: NodeKey
    relation: str
    target: NodeKey
    source_field: str


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[_/\\-]+", " ", text)
    return " ".join(re.findall(r"[\w]+", text, flags=re.UNICODE))


def _string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if isinstance(item, str) and item.strip())
    return ()


class ScenarioKnowledgeGraph:
    """Read-only entity and relationship index derived from a ScenarioRegistry."""

    def __init__(self, nodes: Iterable[KnowledgeNode], edges: Iterable[KnowledgeEdge] = ()) -> None:
        self.nodes: dict[NodeKey, KnowledgeNode] = {
            (node.category, node.id): node for node in nodes
        }
        self.edges: tuple[KnowledgeEdge, ...] = tuple(sorted(set(edges)))
        self._id_index: dict[str, list[NodeKey]] = {}
        self._alias_index: dict[str, list[NodeKey]] = {}
        self._adjacency: dict[NodeKey, list[tuple[NodeKey, str]]] = {
            key: [] for key in self.nodes
        }
        for key, node in sorted(self.nodes.items()):
            self._id_index.setdefault(node.id, []).append(key)
            for value in (node.id, node.name, *node.aliases):
                normalized = _normalize(value)
                if normalized:
                    self._alias_index.setdefault(normalized, []).append(key)
        for edge in self.edges:
            self._adjacency.setdefault(edge.source, []).append((edge.target, edge.relation))
            self._adjacency.setdefault(edge.target, []).append((edge.source, f"inverse:{edge.relation}"))
        for values in self._alias_index.values():
            values.sort()
        for values in self._id_index.values():
            values.sort()
        for values in self._adjacency.values():
            values.sort(key=lambda item: (item[1], item[0]))

    @classmethod
    def from_registry(cls, registry: ScenarioRegistry) -> "ScenarioKnowledgeGraph":
        nodes: list[KnowledgeNode] = []
        records: dict[NodeKey, ScenarioRecord] = {}
        id_lookup: dict[str, list[NodeKey]] = {}
        for category in registry.categories():
            for record in registry.all(category):
                key = (category, record.id)
                records[key] = record
                id_lookup.setdefault(record.id, []).append(key)
                aliases = _string_list(record.data.get("aliases"))
                nodes.append(KnowledgeNode(
                    category=category,
                    id=record.id,
                    name=str(record.data.get("name") or record.id),
                    aliases=aliases,
                    summary=str(record.data.get("summary") or record.data.get("description") or ""),
                ))

        edges: set[KnowledgeEdge] = set()

        def connect(source: NodeKey, raw_target: object, relation: str, field: str,
                    allowed_categories: tuple[str, ...] | None = None) -> None:
            if not isinstance(raw_target, str) or not raw_target.strip():
                return
            candidates = list(id_lookup.get(raw_target.strip(), ()))
            if allowed_categories:
                candidates = [candidate for candidate in candidates if candidate[0] in allowed_categories]
            if len(candidates) == 1 and candidates[0] != source:
                edges.add(KnowledgeEdge(source, relation, candidates[0], field))

        category_fields = {
            "location_id": ("located_at", ("locations",)),
            "target_location": ("targets_location", ("locations",)),
            "origin_location": ("originates_at", ("locations",)),
            "item_id": ("references_item", ("items",)),
            "character_id": ("references_character", ("characters",)),
            "npc_id": ("references_character", ("characters",)),
            "faction_id": ("belongs_to_faction", ("factions",)),
            "creature_id": ("references_creature", ("creatures",)),
            "event_id": ("references_event", ("events",)),
            "technique_id": ("references_technique", ("techniques",)),
            "realm_id": ("references_realm", ("realms",)),
            "party_a": ("relationship_party_a", ("characters",)),
            "party_b": ("relationship_party_b", ("characters",)),
        }
        list_fields = {
            "connected_locations": ("connected_to", ("locations",)),
            "member_ids": ("member_of", ("characters", "creatures")),
            "related_ids": ("related_to", None),
            "related_entities": ("related_to", None),
            "participants": ("participates_in", ("characters", "creatures")),
        }

        for source, record in records.items():
            data = record.data
            references = data.get("references")
            if isinstance(references, Mapping):
                for target_category, raw_ids in references.items():
                    if not isinstance(target_category, str):
                        continue
                    for target_id in _string_list(raw_ids):
                        connect(source, target_id, "references", "references", (target_category,))

            for field, value in data.items():
                if field in category_fields:
                    relation, categories = category_fields[field]
                    connect(source, value, relation, field, categories)
                elif field in list_fields:
                    relation, categories = list_fields[field]
                    for target_id in _string_list(value):
                        connect(source, target_id, relation, field, categories)
                elif field.endswith("_id") and field not in {"id", "owner_id"}:
                    # Resolve unknown but explicit *_id fields only when their target
                    # exists unambiguously in the registry. Never infer from names.
                    connect(source, value, field[:-3] or "references", field)

        return cls(nodes, edges)

    def resolve(
        self,
        query: str,
        *,
        categories: Iterable[str] | None = None,
        limit: int = 10,
    ) -> tuple[KnowledgeNode, ...]:
        """Resolve names, stable IDs, and aliases deterministically."""
        if limit <= 0:
            return ()
        normalized = _normalize(query)
        if not normalized:
            return ()
        allowed = set(categories) if categories is not None else None
        exact_keys = self._alias_index.get(normalized, ())
        if exact_keys:
            return tuple(
                self.nodes[key] for key in exact_keys
                if allowed is None or key[0] in allowed
            )[:limit]

        query_terms = set(normalized.split())
        scored: list[tuple[int, NodeKey]] = []
        for key, node in self.nodes.items():
            if allowed is not None and node.category not in allowed:
                continue
            values = (node.id, node.name, *node.aliases)
            best = 0
            for value in values:
                candidate = _normalize(value)
                if not candidate:
                    continue
                if normalized in candidate or candidate in normalized:
                    best = max(best, 70)
                overlap = len(query_terms & set(candidate.split()))
                if overlap:
                    best = max(best, 10 * overlap)
            if best:
                scored.append((best, key))
        scored.sort(key=lambda item: (-item[0], item[1][0], item[1][1]))
        return tuple(self.nodes[key] for _, key in scored[:limit])

    def related(
        self,
        category: str,
        record_id: str,
        *,
        limit: int = 10,
    ) -> tuple[tuple[KnowledgeNode, str], ...]:
        """Return directly connected nodes, with relation direction preserved."""
        if limit <= 0:
            return ()
        key = (category, record_id)
        results = []
        for target, relation in self._adjacency.get(key, ()):
            node = self.nodes.get(target)
            if node is not None:
                results.append((node, relation))
        results.sort(key=lambda item: (item[1], item[0].category, item[0].id))
        return tuple(results[:limit])
