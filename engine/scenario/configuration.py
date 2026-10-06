"""Runtime selection of a scenario's canonical chapter packs.

This module deliberately contains configuration, not mutable world state.  A
ScenarioConfiguration answers *which canonical material is active*; GameState
continues to answer *what has happened to the player/world*.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from engine.scenario.errors import ScenarioError
from engine.scenario.loader import ScenarioPack

ScenarioMode = Literal["sequential", "free"]


@dataclass(frozen=True)
class ScenarioConfiguration:
    scenario_id: str
    scenario_version: str
    mode: ScenarioMode
    selected_pack_ids: tuple[str, ...]
    start_chapter: int
    current_chapter: int

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ScenarioError("scenario configuration requires scenario_id")
        if not self.scenario_version.strip():
            raise ScenarioError("scenario configuration requires scenario_version")
        if self.mode not in ("sequential", "free"):
            raise ScenarioError("scenario mode must be 'sequential' or 'free'")
        if not self.selected_pack_ids:
            raise ScenarioError("scenario configuration requires at least one chapter pack")
        if len(set(self.selected_pack_ids)) != len(self.selected_pack_ids):
            raise ScenarioError("scenario configuration contains duplicate chapter pack ids")
        if self.start_chapter < 1 or self.current_chapter < 1:
            raise ScenarioError("scenario chapters must be positive")

    @classmethod
    def from_pack(
        cls,
        pack: ScenarioPack,
        *,
        mode: ScenarioMode = "sequential",
        selected_pack_ids: tuple[str, ...] | list[str] | None = None,
        start_chapter: int | None = None,
    ) -> "ScenarioConfiguration":
        manager = pack.chapter_manager
        if not manager.packs:
            raise ScenarioError("scenario has no chapter packs")
        selected = tuple(selected_pack_ids) if selected_pack_ids is not None else manager.pack_ids
        manager.validate_selection(selected, require_contiguous=(mode == "sequential"))
        start = manager.first_chapter(selected) if start_chapter is None else int(start_chapter)
        manager.validate_chapter_access(start, selected, mode)
        return cls(pack.scenario_id, pack.version, mode, selected, start, start)

    def validate_against(self, pack: ScenarioPack) -> None:
        if self.scenario_id != pack.scenario_id:
            raise ScenarioError(
                f"configuration belongs to scenario {self.scenario_id!r}, not {pack.scenario_id!r}"
            )
        if self.scenario_version != pack.version:
            raise ScenarioError(
                f"configuration targets scenario version {self.scenario_version!r}, not {pack.version!r}"
            )
        if pack.chapter_manager is None:
            raise ScenarioError("scenario has no chapter manager")
        pack.chapter_manager.validate_selection(
            self.selected_pack_ids, require_contiguous=(self.mode == "sequential")
        )
        pack.chapter_manager.validate_chapter_access(
            self.start_chapter, self.selected_pack_ids, self.mode
        )
        pack.chapter_manager.validate_chapter_access(
            self.current_chapter, self.selected_pack_ids, self.mode
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "mode": self.mode,
            "selected_pack_ids": list(self.selected_pack_ids),
            "start_chapter": self.start_chapter,
            "current_chapter": self.current_chapter,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "ScenarioConfiguration":
        try:
            return cls(
                str(value["scenario_id"]),
                str(value["scenario_version"]),
                value["mode"],  # type: ignore[arg-type]
                tuple(str(x) for x in value["selected_pack_ids"]),
                int(value["start_chapter"]),
                int(value["current_chapter"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ScenarioError(f"invalid scenario configuration: {exc}") from exc

    def with_current_chapter(self, chapter: int) -> "ScenarioConfiguration":
        return ScenarioConfiguration(
            self.scenario_id, self.scenario_version, self.mode,
            self.selected_pack_ids, self.start_chapter, chapter,
        )
