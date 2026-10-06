"""Deterministic chapter-pack management for loaded scenario canon."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from engine.scenario.errors import ScenarioError


@dataclass(frozen=True)
class ChapterRef:
    pack_id: str
    chapter_start: int
    chapter_end: int
    sequence: int

    def contains(self, chapter: int) -> bool:
        return self.chapter_start <= chapter <= self.chapter_end


class ChapterManager:
    """Read-only index over validated chapter packs.

    It never mutates GameState and never decides what story events happen.
    It only answers chapter selection/order questions.
    """

    def __init__(self, packs: Iterable[object]) -> None:
        refs = tuple(
            ChapterRef(p.pack_id, p.chapter_start, p.chapter_end, p.sequence)
            for p in packs
        )
        self._packs = refs
        self._by_id = {p.pack_id: p for p in refs}
        self._validate(refs)

    @property
    def packs(self) -> tuple[ChapterRef, ...]:
        return self._packs

    @property
    def pack_ids(self) -> tuple[str, ...]:
        return tuple(p.pack_id for p in self._packs)

    @property
    def chapter_count(self) -> int:
        return sum(p.chapter_end - p.chapter_start + 1 for p in self._packs)

    def get_pack(self, pack_id: str) -> ChapterRef | None:
        return self._by_id.get(pack_id)

    def require_pack(self, pack_id: str) -> ChapterRef:
        pack = self.get_pack(pack_id)
        if pack is None:
            raise ScenarioError(f"unknown chapter pack: {pack_id}")
        return pack

    def pack_for_chapter(self, chapter: int, selected_pack_ids: Iterable[str] | None = None) -> ChapterRef:
        if chapter < 1:
            raise ScenarioError("chapter must be positive")
        selected = set(selected_pack_ids) if selected_pack_ids is not None else set(self.pack_ids)
        for pack in self._packs:
            if pack.pack_id in selected and pack.contains(chapter):
                return pack
        raise ScenarioError(f"chapter {chapter} is not available in the selected chapter packs")

    def first_chapter(self, selected_pack_ids: Iterable[str] | None = None) -> int:
        selected = tuple(selected_pack_ids) if selected_pack_ids is not None else self.pack_ids
        self.validate_selection(selected, require_contiguous=False)
        return min(self.require_pack(pack_id).chapter_start for pack_id in selected)

    def validate_selection(self, selected_pack_ids: Iterable[str], *, require_contiguous: bool = True) -> None:
        selected = tuple(selected_pack_ids)
        if not selected:
            raise ScenarioError("at least one chapter pack must be selected")
        if len(set(selected)) != len(selected):
            raise ScenarioError("selected chapter packs contain duplicates")
        for pack_id in selected:
            self.require_pack(pack_id)
        if require_contiguous:
            expected = tuple(p.pack_id for p in self._packs if p.pack_id in set(selected))
            if selected != expected:
                raise ScenarioError("selected chapter packs must follow canonical scenario order")
            previous_end = None
            for pack_id in selected:
                pack = self.require_pack(pack_id)
                if previous_end is not None and pack.chapter_start != previous_end + 1:
                    raise ScenarioError("selected chapter packs must form one contiguous range")
                previous_end = pack.chapter_end

    def validate_chapter_access(self, chapter: int, selected_pack_ids: Iterable[str], mode: str) -> None:
        if mode not in ("sequential", "free"):
            raise ScenarioError("scenario mode must be 'sequential' or 'free'")
        selected = tuple(selected_pack_ids)
        self.validate_selection(selected, require_contiguous=(mode == "sequential"))
        self.pack_for_chapter(chapter, selected)

    @staticmethod
    def _validate(packs: tuple[ChapterRef, ...]) -> None:
        ids = [p.pack_id for p in packs]
        if len(ids) != len(set(ids)):
            raise ScenarioError("duplicate chapter pack ids")
        sequences = [p.sequence for p in packs]
        if sequences != list(range(1, len(sequences) + 1)):
            raise ScenarioError("chapter pack sequences must be contiguous starting at 1")
        for i in range(1, len(packs)):
            if packs[i].chapter_start != packs[i - 1].chapter_end + 1:
                raise ScenarioError("chapter pack ranges must be contiguous and non-overlapping")
