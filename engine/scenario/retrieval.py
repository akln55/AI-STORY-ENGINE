"""Deterministic retrieval over canonical scenario JSON and Markdown.

This is intentionally lexical and metadata-driven in v1. It does not use embeddings,
network services, randomness, or AI. Same scenario + same query => same ordering.
Future semantic retrieval can be layered on top without changing this contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from engine.scenario.documents import ScenarioDocument
from engine.scenario.registry import ScenarioRecord, ScenarioRegistry

DEFAULT_LIMIT = 10
_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


@dataclass(frozen=True)
class ScenarioHit:
    source_type: str  # "record" or "document"
    category: str | None
    record_id: str | None
    document: ScenarioDocument | None
    score: int
    matched_terms: tuple[str, ...]


class ScenarioRetriever:
    """Read-only deterministic retrieval over a loaded scenario's canonical data."""

    def __init__(
        self,
        registry: ScenarioRegistry,
        documents: Iterable[ScenarioDocument] = (),
    ) -> None:
        self.registry = registry
        self.documents = tuple(documents)
        self.scenario_pack = None
        self._record_term_index: dict[str, set[tuple[str, str]]] = {}
        self._document_term_index: dict[str, set[int]] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build derived lexical indexes without changing retrieval semantics."""
        self._record_term_index = {}
        for category in self.registry.categories():
            for rec in self.registry.all(category):
                text = " ".join((rec.id, str(rec.data.get("name", "")),
                                  str(rec.data.get("description", "")),
                                  str(rec.data.get("summary", "")),
                                  str(rec.data.get("aliases", ""))))
                for term in _terms(text):
                    grams = _trigrams(term)
                    for gram in grams:
                        self._record_term_index.setdefault(gram, set()).add((category, rec.id))
        self._document_term_index = {}
        for index, doc in enumerate(self.documents):
            for term in _terms(f"{doc.title} {doc.kind} {doc.content}"):
                for gram in _trigrams(term):
                    self._document_term_index.setdefault(gram, set()).add(index)

    def record(
        self,
        *,
        category: str | None = None,
        record_id: str | None = None,
        query: str | None = None,
        chapter: int | None = None,
        limit: int = DEFAULT_LIMIT,
        viewer: str = "player",
    ) -> tuple[ScenarioHit, ...]:
        """Retrieve canonical JSON records using exact filters plus lexical ranking."""
        if limit <= 0:
            return ()
        terms = _terms(query)
        categories = (category,) if category else self.registry.categories()
        candidates: list[ScenarioHit] = []
        allowed = set(categories)
        indexed_ids: set[tuple[str, str]] | None = None
        if terms and all(len(term) >= 3 for term in terms):
            indexed_ids = set()
            for term in terms:
                postings = [self._record_term_index.get(g, set()) for g in _trigrams(term)]
                if postings:
                    indexed_ids.update(set.intersection(*map(set, postings)))
        for cat in categories:
            for rec in self.registry.all(cat):
                if indexed_ids is not None and (cat, rec.id) not in indexed_ids:
                    continue
                if record_id is not None and rec.id != record_id:
                    continue
                if chapter is not None and not _record_available_in_chapter(rec, chapter):
                    continue
                if not _record_visible_to(rec, viewer):
                    continue
                score, matched = _score_record(rec, terms)
                if terms and score == 0:
                    continue
                candidates.append(ScenarioHit("record", cat, rec.id, None, score, matched))
        candidates.sort(key=lambda h: (-h.score, h.category or "", h.record_id or ""))
        return tuple(candidates[:limit])

    def documents_for(
        self,
        *,
        query: str | None = None,
        chapter: int | None = None,
        pack_id: str | None = None,
        kinds: Iterable[str] | None = None,
        limit: int = DEFAULT_LIMIT,
        include_global_lore: bool = False,
    ) -> tuple[ScenarioHit, ...]:
        """Retrieve Markdown source context, optionally scoped to chapter/pack/kind."""
        if limit <= 0:
            return ()
        terms = _terms(query)
        kind_set = set(kinds or ())
        candidates: list[ScenarioHit] = []
        indexed_docs: set[int] | None = None
        if terms and all(len(term) >= 3 for term in terms):
            indexed_docs = set()
            for term in terms:
                postings = [self._document_term_index.get(g, set()) for g in _trigrams(term)]
                if postings:
                    indexed_docs.update(set.intersection(*map(set, postings)))
        for index, doc in enumerate(self.documents):
            if indexed_docs is not None and index not in indexed_docs:
                continue
            if pack_id is not None and doc.pack_id != pack_id:
                continue
            if chapter is not None and doc.scope == "lore" and not include_global_lore:
                continue
            if chapter is not None and doc.chapters is not None and chapter not in doc.chapters:
                continue
            if chapter is not None and doc.scope == "chapter" and doc.chapters is None:
                continue
            if kind_set and doc.kind not in kind_set:
                continue
            score, matched = _score_document(doc, terms)
            if terms and score == 0:
                continue
            candidates.append(ScenarioHit("document", None, None, doc, score, matched))
        candidates.sort(key=lambda h: (-h.score, h.document.path if h.document else ""))
        return tuple(candidates[:limit])

    def search(
        self,
        query: str | None = None,
        *,
        chapter: int | None = None,
        category: str | None = None,
        pack_id: str | None = None,
        limit: int = DEFAULT_LIMIT,
        viewer: str = "player",
        include_global_lore: bool = False,
    ) -> tuple[ScenarioHit, ...]:
        """Combined JSON + Markdown search with deterministic source ordering."""
        record_hits = list(self.record(category=category, query=query, chapter=chapter, limit=limit, viewer=viewer))
        doc_hits = list(self.documents_for(query=query, chapter=chapter, pack_id=pack_id, limit=limit, include_global_lore=include_global_lore))
        combined = record_hits + doc_hits
        combined.sort(key=lambda h: (-h.score, h.source_type, h.category or "", h.record_id or "", h.document.path if h.document else ""))
        return tuple(combined[: max(0, limit)])


def _trigrams(value: str) -> set[str]:
    text = re.sub(r"\s+", " ", value.strip().lower())
    if len(text) < 3:
        return set()
    return {text[i:i + 3] for i in range(len(text) - 2)}


def _terms(query: str | None) -> tuple[str, ...]:
    if not query:
        return ()
    # Preserve first occurrence order, while deduplicating case-insensitively.
    result: list[str] = []
    seen: set[str] = set()
    for token in _TOKEN_RE.findall(query.lower()):
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return tuple(result)


def _score_text(text: str, terms: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    lower = text.lower()
    matched: list[str] = []
    score = 0
    for term in terms:
        count = lower.count(term)
        if count:
            matched.append(term)
            score += min(count, 3)
    return score, tuple(matched)


def _score_record(record: ScenarioRecord, terms: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    data = record.data
    text_parts = [record.id, str(data.get("name", "")), str(data.get("description", "")), str(data.get("summary", "")), str(data.get("aliases", ""))]
    score, matched = _score_text(" ".join(text_parts), terms)
    if not terms:
        score = 0
    return score, matched


def _score_document(doc: ScenarioDocument, terms: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    return _score_text(f"{doc.title} {doc.kind} {doc.content}", terms)


def _record_available_in_chapter(record: ScenarioRecord, chapter: int) -> bool:
    data = record.data
    for field in ("first_appearance", "first_chapter", "available_from_chapter", "known_from_chapter", "chapter"):
        value = data.get(field)
        if isinstance(value, int) and chapter < value:
            return False
    last = data.get("last_appearance", data.get("last_chapter"))
    if isinstance(last, int) and chapter > last:
        return False
    return True


def _record_visible_to(record: ScenarioRecord, viewer: str) -> bool:
    data = record.data
    visibility = data.get("visibility")
    if visibility in ("system", "secret") and viewer != "system":
        return False
    known_by = data.get("known_by")
    if isinstance(known_by, (list, tuple)):
        if known_by:
            return viewer in known_by or "public" in known_by
        return False
    return True
