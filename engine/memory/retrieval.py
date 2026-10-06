"""Deterministic memory retrieval — no embeddings, no randomness.

Same database state + same query → same ordered results.
"""

from __future__ import annotations

from engine.memory.system import MemoryRecord, MemorySystem

DEFAULT_LIMIT = 10


def _term_grams(term: str) -> set[str]:
    value = term.strip().lower()
    return {value[i:i + 3] for i in range(len(value) - 2)}


def retrieve(
    memory: MemorySystem,
    *,
    viewer: str = "player",
    store: str | None = None,
    entity_id: str | None = None,
    location_id: str | None = None,
    event_id: str | None = None,
    tags: list[str] | None = None,
    min_importance: int = 0,
    query_terms: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
    include_archive: bool = False,
) -> list[MemoryRecord]:
    """Filter then rank memories visible to `viewer`.

    Ranking (descending):
      1. tag/query term hit count
      2. importance
      3. recency (last_updated_turn, then created_turn)
      4. id (stable tie-break)
    """
    if limit < 0:
        limit = 0
    terms = [t.lower() for t in (query_terms or []) if t]
    tag_set = {t.lower() for t in (tags or [])}

    candidates: list[tuple[tuple, MemoryRecord]] = []

    # Use MemorySystem's derived indexes to narrow the candidate set before
    # applying the exact legacy substring scorer. Short terms (<3 chars) keep
    # the conservative full-scan fallback so behavior stays compatible.
    candidate_ids: set[str] | None = None
    indexes = []
    if store is not None:
        indexes.append(memory._store_index.get(store, set()))
    if entity_id is not None:
        indexes.append(memory._entity_index.get(entity_id, set()))
    if location_id is not None:
        indexes.append(memory._location_index.get(location_id, set()))
    if event_id is not None:
        indexes.append(memory._event_index.get(event_id, set()))
    if tag_set:
        tag_ids: set[str] = set()
        for tag in tag_set:
            tag_ids.update(memory._tag_index.get(tag, set()))
        indexes.append(tag_ids)
    long_terms = [t for t in terms if len(t) >= 3]
    if long_terms:
        term_ids: set[str] = set()
        for term in long_terms:
            grams = memory._gram_index
            gram_sets = [grams.get(g, set()) for g in _term_grams(term)]
            if not gram_sets or any(not s for s in gram_sets):
                continue
            ids = set.intersection(*map(set, gram_sets))
            term_ids.update(ids)
        indexes.append(term_ids)
    if indexes:
        candidate_ids = set.intersection(*(set(i) for i in indexes)) if all(indexes) else set()

    records = (memory.all_records() if candidate_ids is None
               else (memory.get(rid) for rid in candidate_ids))
    for rec in records:
        if rec is None:
            continue
        if not include_archive and rec.tier != "active":
            continue
        if not rec.known_by(viewer):
            continue
        if store is not None and rec.store != store:
            continue
        if entity_id is not None and rec.entity_id != entity_id:
            continue
        if location_id is not None and rec.location_id != location_id:
            continue
        if event_id is not None and rec.event_id != event_id:
            continue
        if rec.importance < min_importance:
            continue
        if tag_set and not tag_set.intersection(rec.tags):
            continue

        hit = 0
        content_l = rec.content.lower()
        for t in terms:
            if t in content_l or t in rec.tags:
                hit += 1
        # Stable sort key: higher is better, so negate for ascending sort.
        key = (
            -hit,
            -rec.importance,
            -rec.last_updated_turn,
            -rec.created_turn,
            rec.id,
        )
        candidates.append((key, rec))

    candidates.sort(key=lambda x: x[0])
    return [r for _, r in candidates[:limit]]
