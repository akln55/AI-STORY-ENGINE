"""Engine-owned memory stores with visibility, validation, and deduplication.

AI memory_updates are proposals only; they enter durable storage solely through
MemorySystem.add / add_from_proposal after validation.

Duplicate policy (structural, not semantic):
  Two records are duplicates when store, visibility, and normalized content
  (stripped, lowercased) are identical. On duplicate add, the existing record
  is refreshed (last_updated_turn, importance = max) and no new id is created.
  Legitimate repeated *events* with distinct content are kept.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Iterable


_ARCHIVE_ACTIVE = "active"
_ARCHIVE_ARCHIVED = "archive"

STORES = frozenset({
    "permanent", "character", "relationship", "event", "location",
    "item", "knowledge", "rumor", "secret", "recent",
})

_VIS_PLAYER = "player"
_VIS_SYSTEM = "system"
_NPC_RE = re.compile(r"^npc:[a-zA-Z0-9_\-]+$")
_FACTION_RE = re.compile(r"^faction:[a-zA-Z0-9_\-]+$")

IMPORTANCE_MIN = 0
IMPORTANCE_MAX = 100


class MemoryValidationError(ValueError):
    """Raised when a memory record fails validation before storage."""


@dataclass
class MemoryRecord:
    id: str
    store: str
    content: str
    visibility: str = _VIS_SYSTEM
    importance: int = 0
    created_turn: int = 0
    last_updated_turn: int = 0
    entity_id: str | None = None
    location_id: str | None = None
    event_id: str | None = None
    tags: list[str] = field(default_factory=list)
    tier: str = _ARCHIVE_ACTIVE

    def known_by(self, viewer: str) -> bool:
        if viewer == _VIS_SYSTEM:
            return True
        if self.visibility == _VIS_SYSTEM:
            return viewer == _VIS_SYSTEM
        if self.visibility == _VIS_PLAYER:
            return True
        if viewer == self.visibility:
            return True
        return False

    @staticmethod
    def content_key(content: str) -> str:
        return content.strip().lower()


def _validate_visibility(vis: str) -> str:
    if vis in (_VIS_PLAYER, _VIS_SYSTEM):
        return vis
    if _NPC_RE.match(vis) or _FACTION_RE.match(vis):
        return vis
    raise MemoryValidationError(f"invalid visibility {vis!r}")


def _validate_store(store: str) -> str:
    if store not in STORES:
        raise MemoryValidationError(f"unknown memory store {store!r}")
    return store


def _validate_importance(importance: int) -> int:
    if not isinstance(importance, int):
        raise MemoryValidationError("importance must be int")
    if not (IMPORTANCE_MIN <= importance <= IMPORTANCE_MAX):
        raise MemoryValidationError(
            f"importance {importance} outside [{IMPORTANCE_MIN}, {IMPORTANCE_MAX}]")
    return importance


def _validate_tags(tags: object) -> list[str]:
    if tags is None:
        return []
    if not isinstance(tags, (list, tuple)):
        raise MemoryValidationError("tags must be a list of strings")
    out = []
    for t in tags:
        if not isinstance(t, str) or not t.strip():
            raise MemoryValidationError(f"invalid tag {t!r}")
        out.append(t.strip().lower())
    return out


def _validate_turn(turn: int) -> int:
    if not isinstance(turn, int) or turn < 0:
        raise MemoryValidationError(f"turn must be non-negative int, got {turn!r}")
    return turn


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _dedup_key(store: str, visibility: str, content: str) -> tuple[str, str, str]:
    return (store, visibility, MemoryRecord.content_key(content))


def _trigrams(value: str) -> set[str]:
    """Return normalized 3-character grams used by the retrieval index."""
    text = re.sub(r"\s+", " ", value.strip().lower())
    if len(text) < 3:
        return set()
    return {text[i:i + 3] for i in range(len(text) - 2)}


def _validate_tier(tier: str) -> str:
    if tier not in (_ARCHIVE_ACTIVE, _ARCHIVE_ARCHIVED):
        raise MemoryValidationError(f"invalid memory tier {tier!r}")
    return tier


class MemorySystem:
    """In-memory store container. Persisted via persistence layer."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}
        # secondary index for structural dedup: key -> record id
        self._dedup: dict[tuple[str, str, str], str] = {}
        # Retrieval indexes. They are derived state and rebuilt on load.
        self._store_index: dict[str, set[str]] = {}
        self._visibility_index: dict[str, set[str]] = {}
        self._entity_index: dict[str, set[str]] = {}
        self._location_index: dict[str, set[str]] = {}
        self._event_index: dict[str, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}
        self._gram_index: dict[str, set[str]] = {}

    def __len__(self) -> int:
        return len(self._records)

    def all_records(self) -> list[MemoryRecord]:
        return list(self._records.values())

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._records.get(record_id)

    def add(
        self,
        store: str,
        content: str,
        *,
        visibility: str = _VIS_SYSTEM,
        importance: int = 0,
        created_turn: int = 0,
        entity_id: str | None = None,
        location_id: str | None = None,
        event_id: str | None = None,
        tags: list[str] | None = None,
        record_id: str | None = None,
        tier: str = _ARCHIVE_ACTIVE,
    ) -> MemoryRecord:
        """Validate and insert. Structural duplicates refresh existing record."""
        store = _validate_store(store)
        if not isinstance(content, str) or not content.strip():
            raise MemoryValidationError("content must be a non-empty string")
        visibility = _validate_visibility(visibility)
        importance = _validate_importance(importance)
        created_turn = _validate_turn(created_turn)
        tags_v = _validate_tags(tags)
        tier = _validate_tier(tier)
        if entity_id is not None and (not isinstance(entity_id, str) or not entity_id.strip()):
            raise MemoryValidationError(f"invalid entity_id {entity_id!r}")
        if location_id is not None and (not isinstance(location_id, str) or not location_id.strip()):
            raise MemoryValidationError(f"invalid location_id {location_id!r}")
        if event_id is not None and (not isinstance(event_id, str) or not event_id.strip()):
            raise MemoryValidationError(f"invalid event_id {event_id!r}")

        key = _dedup_key(store, visibility, content)
        existing_id = self._dedup.get(key)
        if existing_id and existing_id in self._records:
            rec = self._records[existing_id]
            rec.last_updated_turn = max(rec.last_updated_turn, created_turn)
            rec.importance = max(rec.importance, importance)
            if tags_v:
                merged = list(dict.fromkeys(rec.tags + tags_v))
                rec.tags = merged
            if entity_id and not rec.entity_id:
                rec.entity_id = entity_id
            if location_id and not rec.location_id:
                rec.location_id = location_id
            if event_id and not rec.event_id:
                rec.event_id = event_id
            return rec

        rid = record_id or _new_id()
        if rid in self._records:
            raise MemoryValidationError(f"duplicate memory id '{rid}'")
        rec = MemoryRecord(
            id=rid,
            store=store,
            content=content.strip(),
            visibility=visibility,
            importance=importance,
            created_turn=created_turn,
            last_updated_turn=created_turn,
            entity_id=entity_id.strip() if entity_id else None,
            location_id=location_id.strip() if location_id else None,
            event_id=event_id.strip() if event_id else None,
            tags=tags_v,
            tier=tier,
        )
        self._records[rid] = rec
        self._dedup[key] = rid
        self._index_record(rec)
        return rec

    def add_from_proposal(
        self,
        store: str,
        content: str,
        *,
        visibility: str = _VIS_SYSTEM,
        importance: int = 0,
        created_turn: int = 0,
        entity_id: str | None = None,
        location_id: str | None = None,
        event_id: str | None = None,
        tags: list[str] | None = None,
        tier: str = _ARCHIVE_ACTIVE,
    ) -> MemoryRecord:
        """Entry point for AI memory_updates after schema parse.

        Unknown visibility → system; importance clamped. Still raises on empty
        content / unknown store. Callers (engine/core/game.py) are responsible
        for cross-checking entity_id/location_id/event_id/visibility against
        live world state *before* calling this — this method itself only
        applies MemorySystem's own structural validation (non-empty strings).
        """
        vis = visibility if visibility in (_VIS_PLAYER, _VIS_SYSTEM) or _NPC_RE.match(
            visibility or "") or _FACTION_RE.match(visibility or "") else _VIS_SYSTEM
        try:
            imp = int(importance)
        except (TypeError, ValueError):
            imp = 0
        imp = max(IMPORTANCE_MIN, min(IMPORTANCE_MAX, imp))
        return self.add(
            store=store,
            content=content,
            visibility=vis,
            importance=imp,
            created_turn=created_turn,
            entity_id=entity_id,
            location_id=location_id,
            event_id=event_id,
            tags=tags,
            tier=tier,
        )

    @staticmethod
    def _index_add(index: dict[str, set[str]], key: str | None, record_id: str) -> None:
        if key is None or not key:
            return
        index.setdefault(key, set()).add(record_id)

    def _index_record(self, rec: MemoryRecord) -> None:
        self._index_add(self._store_index, rec.store, rec.id)
        self._index_add(self._visibility_index, rec.visibility, rec.id)
        self._index_add(self._entity_index, rec.entity_id, rec.id)
        self._index_add(self._location_index, rec.location_id, rec.id)
        self._index_add(self._event_index, rec.event_id, rec.id)
        for tag in rec.tags:
            self._index_add(self._tag_index, tag, rec.id)
        for gram in _trigrams(rec.content + " " + " ".join(rec.tags)):
            self._index_add(self._gram_index, gram, rec.id)

    def _rebuild_indexes(self) -> None:
        self._store_index = {}
        self._visibility_index = {}
        self._entity_index = {}
        self._location_index = {}
        self._event_index = {}
        self._tag_index = {}
        self._gram_index = {}
        for rec in self._records.values():
            self._index_record(rec)

    def archive_older_than(
        self, current_turn: int, *, max_age: int = 100, stores: tuple[str, ...] = ("recent",)
    ) -> int:
        """Move old transient records to the lossless archive tier.

        Archived records remain persisted and explicitly retrievable, but are
        excluded from normal context retrieval. Durable typed memories are never
        archived by this default policy.
        """
        current_turn = _validate_turn(current_turn)
        if max_age < 0:
            raise MemoryValidationError("max_age must be non-negative")
        allowed = {_validate_store(store) for store in stores}
        cutoff = max(0, current_turn - max_age)
        changed = 0
        for rec in self._records.values():
            if rec.tier == _ARCHIVE_ACTIVE and rec.store in allowed and rec.created_turn < cutoff:
                rec.tier = _ARCHIVE_ARCHIVED
                changed += 1
        return changed

    def archive_count(self) -> int:
        return sum(1 for r in self._records.values() if r.tier == _ARCHIVE_ARCHIVED)

    def remove(self, record_id: str) -> bool:
        rec = self._records.pop(record_id, None)
        if rec is None:
            return False
        key = _dedup_key(rec.store, rec.visibility, rec.content)
        if self._dedup.get(key) == record_id:
            del self._dedup[key]
        self._rebuild_indexes()
        return True

    def clear_store(self, store: str) -> int:
        store = _validate_store(store)
        to_del = [rid for rid, r in self._records.items() if r.store == store]
        for rid in to_del:
            self.remove(rid)
        return len(to_del)

    def replace_all(self, records: Iterable[MemoryRecord]) -> None:
        new: dict[str, MemoryRecord] = {}
        dedup: dict[tuple[str, str, str], str] = {}
        for r in records:
            _validate_store(r.store)
            _validate_visibility(r.visibility)
            _validate_importance(r.importance)
            _validate_turn(r.created_turn)
            _validate_turn(r.last_updated_turn)
            _validate_tier(r.tier)
            if r.id in new:
                raise MemoryValidationError(f"duplicate memory id '{r.id}' on load")
            key = _dedup_key(r.store, r.visibility, r.content)
            # On load, last-wins for structural dup keys (keep one)
            if key in dedup:
                old_id = dedup[key]
                del new[old_id]
            new[r.id] = r
            dedup[key] = r.id
        self._records = new
        self._dedup = dedup
        self._rebuild_indexes()

    def to_list(self) -> list[dict]:
        out = []
        for r in self._records.values():
            out.append({
                "id": r.id,
                "store": r.store,
                "content": r.content,
                "visibility": r.visibility,
                "importance": r.importance,
                "created_turn": r.created_turn,
                "last_updated_turn": r.last_updated_turn,
                "entity_id": r.entity_id,
                "location_id": r.location_id,
                "event_id": r.event_id,
                "tags": list(r.tags),
                "tier": r.tier,
            })
        return out

    @classmethod
    def from_list(cls, data: list[dict]) -> "MemorySystem":
        ms = cls()
        records = []
        for d in data:
            records.append(MemoryRecord(
                id=str(d["id"]),
                store=str(d["store"]),
                content=str(d["content"]),
                visibility=str(d.get("visibility", _VIS_SYSTEM)),
                importance=int(d.get("importance", 0)),
                created_turn=int(d.get("created_turn", 0)),
                last_updated_turn=int(d.get("last_updated_turn", 0)),
                entity_id=d.get("entity_id"),
                location_id=d.get("location_id"),
                event_id=d.get("event_id"),
                tags=list(d.get("tags") or []),
                tier=str(d.get("tier", _ARCHIVE_ACTIVE)),
            ))
        ms.replace_all(records)
        return ms
