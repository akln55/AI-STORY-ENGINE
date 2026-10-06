"""Immutable registry for canonical scenario data.

The registry is deliberately separate from GameState. Canonical scenario records are
read-only reference data; gameplay mutations belong to GameState and its validation
pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from engine.scenario.errors import ScenarioError

CATEGORY_FILES: dict[str, str] = {
    "characters": "characters.json",
    "locations": "locations.json",
    "factions": "factions.json",
    "items": "items.json",
    "techniques": "techniques.json",
    "realms": "realms.json",
    "creatures": "creatures.json",
    "events": "events.json",
    "relationships": "relationships.json",
    "timeline": "timeline.json",
    "knowledge": "knowledge.json",
}
FILE_CATEGORIES = {filename: category for category, filename in CATEGORY_FILES.items()}


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


@dataclass(frozen=True)
class ScenarioRecord:
    category: str
    id: str
    data: Mapping[str, Any]


class ScenarioRegistry:
    """Typed-by-category, immutable index over canonical scenario JSON."""

    def __init__(self, documents: Mapping[str, Mapping[str, Any]]) -> None:
        normalized: dict[str, Mapping[str, ScenarioRecord]] = {}
        for category, filename in CATEGORY_FILES.items():
            payload = documents.get(filename, {})
            if not isinstance(payload, Mapping):
                raise ScenarioError(f"scenario data {filename} must be a JSON object")
            records: dict[str, ScenarioRecord] = {}
            for record_id, raw in payload.items():
                if not isinstance(record_id, str) or not record_id.strip():
                    raise ScenarioError(f"scenario data {filename} contains an invalid record id")
                if not isinstance(raw, Mapping):
                    raise ScenarioError(f"scenario data {filename}:{record_id} must be an object")
                embedded_id = raw.get("id")
                if not isinstance(embedded_id, str) or not embedded_id.strip():
                    raise ScenarioError(f"scenario data {filename}:{record_id} is missing a stable id")
                if embedded_id != record_id:
                    raise ScenarioError(
                        f"scenario data {filename}:{record_id} has id={embedded_id!r}; embedded id must match key"
                    )
                goals = raw.get("goals")
                if goals is not None:
                    if not isinstance(goals, list):
                        raise ScenarioError(f"scenario data {filename}:{record_id}.goals must be a list")
                    allowed_goal_kinds = {"passive", "move_to", "follow_npc", "meet_npc", "patrol", "survive"}
                    for goal in goals:
                        if not isinstance(goal, Mapping):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.goals entries must be objects")
                        for key in ("id", "description", "priority"):
                            if key not in goal:
                                raise ScenarioError(f"scenario data {filename}:{record_id}.goal requires {key}")
                        kind = str(goal.get("kind", "passive"))
                        if kind not in allowed_goal_kinds:
                            raise ScenarioError(f"scenario data {filename}:{record_id}.goal has unsupported kind {kind!r}")
                        if not isinstance(goal.get("priority"), int) or isinstance(goal.get("priority"), bool):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.goal priority must be an integer")
                        if "required_progress" in goal and (not isinstance(goal["required_progress"], int) or goal["required_progress"] < 1):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.goal required_progress must be >= 1")
                        if kind == "move_to" and not isinstance(goal.get("target_location"), str):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.move_to goal requires target_location")
                        if kind in {"follow_npc", "meet_npc"} and not isinstance(goal.get("target_id"), str):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.{kind} goal requires target_id")
                        if kind == "patrol":
                            data = goal.get("data") or {}
                            if not isinstance(data, Mapping) or not isinstance(data.get("locations"), list) or not data.get("locations"):
                                raise ScenarioError(f"scenario data {filename}:{record_id}.patrol goal requires data.locations")
                schedule = raw.get("schedule")
                if schedule is not None:
                    if not isinstance(schedule, list):
                        raise ScenarioError(f"scenario data {filename}:{record_id}.schedule must be a list")
                    for entry in schedule:
                        if not isinstance(entry, Mapping):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.schedule entries must be objects")
                        if not isinstance(entry.get("location_id"), str) or not entry.get("location_id", "").strip():
                            raise ScenarioError(f"scenario data {filename}:{record_id}.schedule requires location_id")
                        for key in ("from_turn", "to_turn", "cycle_turns"):
                            if key in entry and (not isinstance(entry[key], int) or isinstance(entry[key], bool)):
                                raise ScenarioError(f"scenario data {filename}:{record_id}.schedule.{key} must be an integer")
                        cycle = entry.get("cycle_turns")
                        if cycle is not None and cycle <= 0:
                            raise ScenarioError(f"scenario data {filename}:{record_id}.schedule.cycle_turns must be > 0")
                        start = entry.get("from_turn", 0)
                        end = entry.get("to_turn")
                        if isinstance(start, int) and isinstance(end, int) and end < start:
                            raise ScenarioError(f"scenario data {filename}:{record_id}.schedule has reversed turn range")
                        if cycle is not None:
                            if start < 0 or (isinstance(end, int) and end >= cycle):
                                raise ScenarioError(
                                    f"scenario data {filename}:{record_id}.schedule cyclic windows must fit within cycle_turns"
                                )

                presence = raw.get("presence")
                if presence is not None:
                    if not isinstance(presence, list):
                        raise ScenarioError(f"scenario data {filename}:{record_id}.presence must be a list")
                    for entry in presence:
                        if not isinstance(entry, Mapping):
                            raise ScenarioError(f"scenario data {filename}:{record_id}.presence entries must be objects")
                        if "location_id" not in entry or not isinstance(entry["location_id"], str) or not entry["location_id"].strip():
                            raise ScenarioError(f"scenario data {filename}:{record_id}.presence requires location_id")
                        for key in ("from_turn", "to_turn"):
                            if key in entry and not isinstance(entry[key], int):
                                raise ScenarioError(f"scenario data {filename}:{record_id}.presence.{key} must be an integer")
                        if isinstance(entry.get("from_turn"), int) and isinstance(entry.get("to_turn"), int) and entry["to_turn"] < entry["from_turn"]:
                            raise ScenarioError(f"scenario data {filename}:{record_id}.presence has reversed turn range")
                conditions = raw.get("encounter_conditions")
                if conditions is not None:
                    if not isinstance(conditions, list):
                        raise ScenarioError(f"scenario data {filename}:{record_id}.encounter_conditions must be a list")
                    for condition in conditions:
                        if not isinstance(condition, Mapping) or condition.get("type") not in {"location", "popularity", "reputation", "level", "realm", "relationship_affinity", "relationship_trust", "relationship_flag", "inventory", "quest", "event", "npc_present", "npc_absent"}:
                            raise ScenarioError(f"scenario data {filename}:{record_id} contains an unsupported encounter condition")
                        ctype = condition["type"]
                        required = {"location": "value", "popularity": "value", "reputation": "key", "level": "value", "realm": "value", "relationship_affinity": "target", "relationship_trust": "target", "relationship_flag": "target", "inventory": "item_id", "quest": "id", "event": "id", "npc_present": "npc_id", "npc_absent": "npc_id"}[ctype]
                        if not isinstance(condition.get(required), str if required in {"key", "target", "item_id", "id", "npc_id"} else (int, str)):
                            raise ScenarioError(f"scenario data {filename}:{record_id} condition {ctype} requires {required}")
                        if ctype == "relationship_flag" and (not isinstance(condition.get("flag"), str) or not condition.get("flag", "").strip()):
                            raise ScenarioError(f"scenario data {filename}:{record_id} relationship_flag requires flag")
                for list_field in ("dialogue_topics", "dialogue_rules", "knowledge_boundary", "aliases"):
                    if list_field in raw and not isinstance(raw[list_field], (list, tuple, str, Mapping)):
                        raise ScenarioError(f"scenario data {filename}:{record_id}.{list_field} has invalid type")
                references = raw.get("references", {})
                if references is not None:
                    if not isinstance(references, Mapping):
                        raise ScenarioError(f"scenario data {filename}:{record_id}.references must be an object")
                    for target_category, target_ids in references.items():
                        if target_category not in CATEGORY_FILES:
                            raise ScenarioError(
                                f"scenario data {filename}:{record_id} references unknown category {target_category!r}"
                            )
                        if not isinstance(target_ids, list) or any(not isinstance(x, str) or not x.strip() for x in target_ids):
                            raise ScenarioError(
                                f"scenario data {filename}:{record_id}.references[{target_category!r}] must be a list of ids"
                            )
                frozen = _freeze(dict(raw))
                records[record_id] = ScenarioRecord(category, record_id, frozen)
            normalized[category] = MappingProxyType(records)
        self._validate_cross_references(normalized)
        self._records = MappingProxyType(normalized)

    @staticmethod
    def _validate_cross_references(records: Mapping[str, Mapping[str, ScenarioRecord]]) -> None:
        for category, category_records in records.items():
            for record in category_records.values():
                references = record.data.get("references", {})
                if not references:
                    continue
                for target_category, target_ids in references.items():
                    target_records = records[target_category]
                    missing = [record_id for record_id in target_ids if record_id not in target_records]
                    if missing:
                        raise ScenarioError(
                            f"scenario data {category}:{record.id} references missing "
                            f"{target_category} id(s): {', '.join(missing)}"
                        )

    @classmethod
    def from_documents(cls, documents: Mapping[str, Mapping[str, Any]]) -> "ScenarioRegistry":
        unknown = sorted(set(documents) - set(FILE_CATEGORIES))
        if unknown:
            raise ScenarioError(f"unsupported canonical scenario data file(s): {', '.join(unknown)}")
        return cls(documents)

    def categories(self) -> tuple[str, ...]:
        return tuple(CATEGORY_FILES)

    def all(self, category: str) -> tuple[ScenarioRecord, ...]:
        self._check_category(category)
        return tuple(self._records[category].values())

    def get(self, category: str, record_id: str) -> ScenarioRecord | None:
        self._check_category(category)
        return self._records[category].get(record_id)

    def require(self, category: str, record_id: str) -> ScenarioRecord:
        record = self.get(category, record_id)
        if record is None:
            raise ScenarioError(f"unknown {category} id: {record_id}")
        return record

    def has(self, category: str, record_id: str) -> bool:
        return self.get(category, record_id) is not None

    def ids(self, category: str) -> tuple[str, ...]:
        self._check_category(category)
        return tuple(self._records[category])

    def find(self, category: str, field: str, value: Any) -> tuple[ScenarioRecord, ...]:
        return tuple(record for record in self.all(category) if record.data.get(field) == value)

    def _check_category(self, category: str) -> None:
        if category not in CATEGORY_FILES:
            raise ScenarioError(f"unknown scenario data category: {category}")
