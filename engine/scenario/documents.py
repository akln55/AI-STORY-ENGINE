"""Canonical Markdown document metadata used by scenario retrieval.

Markdown is source/context material, not authoritative runtime state. Documents are
kept as immutable metadata + text and are never written into GameState saves.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ScenarioDocument:
    path: str
    scope: str  # "lore" or "chapter"
    pack_id: str | None
    chapter_start: int | None
    chapter_end: int | None
    kind: str
    title: str
    content: str
    metadata: Mapping[str, object] = MappingProxyType({})

    @property
    def chapters(self) -> range | None:
        if self.chapter_start is None or self.chapter_end is None:
            return None
        return range(self.chapter_start, self.chapter_end + 1)
