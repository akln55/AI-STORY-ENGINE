"""Structured AI response schema (contract: docs/DATA_MODELS.md §3).

Strict parsing: malformed payloads raise ValueError — never any other
exception type. In production, adapters retry with feedback (see
`engine.core.game.GameSession._generate_with_retry`, which only catches
ValueError); in tests the fake adapter always produces valid payloads.
Narrative is player-facing text only and is NEVER parsed for state (ADR-0001).

Field implementation status (DATA_MODELS.md §3 is a forward-looking design
contract; this module parses the full contract, but the engine only *acts*
on a subset today):
  - narrative        -> player-facing text (engine/core/game.py)
  - state_changes     -> converted to Effect and validated (engine/core/game.py,
                          engine/core/validation.py) - IMPLEMENTED
  - npc_changes       -> converted to Effect(kind="npc") and validated -
                          IMPLEMENTED
  - memory_updates    -> parsed and consumed by
                          engine/core/game.py::GameSession._ingest_memory_updates,
                          which cross-checks entity_id/location_id/event_id/
                          visibility against live world state before handing
                          validated records to MemorySystem. IMPLEMENTED.
  - events_triggered  -> converted to validated event trigger effects by
                          GameSession; implemented for existing scenario-defined events.
  - available_actions -> parsed only; no UI affordance consumes this yet.
                          NOT YET CONSUMED.
Unconsumed fields cannot mutate state or influence engine behavior -- they
are inert data on the returned object. Do not treat their presence in this
schema as those features being implemented.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

_TOP_LEVEL_KEYS = {
    "narrative", "state_changes", "memory_updates",
    "npc_changes", "events_triggered", "available_actions",
}

# Provider output limits. These are engine-safety limits, not model-quality limits.
# They bound memory/CPU work caused by a malformed or unexpectedly huge provider response.
MAX_NARRATIVE_CHARS = 4000
MAX_STATE_CHANGES = 32
MAX_MEMORY_UPDATES = 32
MAX_NPC_CHANGES = 32
MAX_EVENTS_TRIGGERED = 32
MAX_AVAILABLE_ACTIONS = 16
MAX_MEMORY_CONTENT_CHARS = 1000
MAX_TAGS_PER_MEMORY = 16
MAX_TAG_CHARS = 80

_STATE_CHANGE_OPS = {
    "resource": {"add", "set"},
    "inventory": {"take", "drop"},
    "location": {"move"},
    "npc": {"set"},
    "relationship": {"set", "add", "flag_add", "flag_remove"},
    "reputation": {"set", "add"},
    "status": {"add", "remove", "tick"},
}


@dataclass
class StateChange:
    type: str
    target: str
    operation: str
    value: object
    reason: str = ""


@dataclass
class MemoryUpdate:
    store: str
    content: str
    visibility: str = "system"
    importance: int = 0
    entity_id: str | None = None
    location_id: str | None = None
    event_id: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class NPCChange:
    npc: str
    field: str
    value: object


@dataclass
class StructuredResponse:
    narrative: str
    state_changes: list[StateChange] = field(default_factory=list)
    memory_updates: list[MemoryUpdate] = field(default_factory=list)
    npc_changes: list[NPCChange] = field(default_factory=list)
    events_triggered: list[str] = field(default_factory=list)
    available_actions: list[str] = field(default_factory=list)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(f"invalid structured response: {msg}")


def parse_structured_response(data: dict) -> StructuredResponse:
    if not isinstance(data, dict):
        raise ValueError("invalid structured response: not an object")
    unknown = set(data) - _TOP_LEVEL_KEYS
    _require(not unknown, f"unknown top-level fields: {sorted(unknown)}")

    _require(isinstance(data.get("narrative"), str), "missing 'narrative' string")
    _require(len(data["narrative"]) <= MAX_NARRATIVE_CHARS, "narrative exceeds size limit")
    for key in ("state_changes", "memory_updates", "npc_changes",
                "events_triggered", "available_actions"):
        _require(isinstance(data.get(key, []), list), f"'{key}' must be a list")

    raw_state_changes = data.get("state_changes", [])
    _require(len(raw_state_changes) <= MAX_STATE_CHANGES, "too many state_changes")
    state_changes = []
    for item in raw_state_changes:
        _require(isinstance(item, dict), "state_change must be an object")
        _require(set(item) >= {"type", "target", "operation", "value"},
                 "state_change missing required fields")
        change_type = item["type"]
        # isinstance guard first: an unhashable type (list/dict) must raise the
        # same safe ValueError as any other malformed field, never a TypeError
        # from the `in` membership check below.
        _require(isinstance(change_type, str) and change_type in _STATE_CHANGE_OPS,
                 f"unknown type {change_type!r}")
        operation = item["operation"]
        _require(isinstance(operation, str) and operation in _STATE_CHANGE_OPS[change_type],
                 f"operation {operation!r} not allowed for '{change_type}'")
        if change_type == "relationship" and operation in {"flag_add", "flag_remove"}:
            _require(isinstance(item["value"], str) and bool(item["value"].strip()),
                     "relationship flag must be a non-empty string")
        state_changes.append(StateChange(
            type=change_type, target=str(item["target"]),
            operation=operation, value=item["value"],
            reason=str(item.get("reason", "")),
        ))

    raw_memory_updates = data.get("memory_updates", [])
    _require(len(raw_memory_updates) <= MAX_MEMORY_UPDATES, "too many memory_updates")
    memory_updates = []
    for item in raw_memory_updates:
        _require(isinstance(item, dict) and "store" in item and "content" in item,
                 "memory_update needs 'store' and 'content'")
        raw_tags = item.get("tags", [])
        _require(isinstance(raw_tags, list), "memory_update 'tags' must be a list")
        _require(len(str(item["content"])) <= MAX_MEMORY_CONTENT_CHARS, "memory_update content exceeds size limit")
        _require(len(raw_tags) <= MAX_TAGS_PER_MEMORY, "too many memory_update tags")
        _require(all(len(str(t)) <= MAX_TAG_CHARS for t in raw_tags), "memory_update tag exceeds size limit")
        memory_updates.append(MemoryUpdate(
            store=str(item["store"]), content=str(item["content"]),
            visibility=str(item.get("visibility", "system")),
            importance=int(item.get("importance", 0)),
            entity_id=(str(item["entity_id"]) if item.get("entity_id") is not None else None),
            location_id=(str(item["location_id"]) if item.get("location_id") is not None else None),
            event_id=(str(item["event_id"]) if item.get("event_id") is not None else None),
            tags=[str(t) for t in raw_tags],
        ))

    raw_npc_changes = data.get("npc_changes", [])
    _require(len(raw_npc_changes) <= MAX_NPC_CHANGES, "too many npc_changes")
    npc_changes = []
    for item in raw_npc_changes:
        _require(isinstance(item, dict) and set(item) >= {"npc", "field", "value"},
                 "npc_change needs 'npc', 'field', 'value'")
        npc_changes.append(NPCChange(npc=str(item["npc"]), field=str(item["field"]),
                                     value=item["value"]))

    raw_events = data.get("events_triggered", [])
    raw_actions = data.get("available_actions", [])
    _require(len(raw_events) <= MAX_EVENTS_TRIGGERED, "too many events_triggered")
    _require(len(raw_actions) <= MAX_AVAILABLE_ACTIONS, "too many available_actions")

    return StructuredResponse(
        narrative=data["narrative"],
        state_changes=state_changes,
        memory_updates=memory_updates,
        npc_changes=npc_changes,
        events_triggered=[str(e) for e in data.get("events_triggered", [])],
        available_actions=[str(a) for a in data.get("available_actions", [])],
    )


def parse_structured_response_json(text: str) -> StructuredResponse:
    """Adapter-boundary helper: raw provider text -> StructuredResponse.

    A real AIAdapter (Phase 3+) receives free-form text from an LLM and is
    responsible for turning it into a StructuredResponse. This is the one
    place that boundary happens: JSON-decode, then the same strict
    `parse_structured_response` used everywhere else. Malformed JSON is
    rejected exactly like any other malformed payload -- ValueError, never
    a raw json.JSONDecodeError -- so a future adapter's caller only ever
    needs to catch ValueError (matching `_generate_with_retry`'s contract).

    FakeAdapter does not use this: it hands pre-built dicts straight to
    `parse_structured_response`, which is fine for scripted tests.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise ValueError(f"invalid structured response: not valid JSON ({err})") from err
    return parse_structured_response(data)
