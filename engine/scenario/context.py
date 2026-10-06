"""Immutable composition context for a running scenario.

A ScenarioContext bundles the canonical scenario objects that must travel
through the application boundary together.  It prevents callers from
accidentally wiring a registry from one pack with a retriever/configuration
from another pack.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.scenario.configuration import ScenarioConfiguration
from engine.scenario.errors import ScenarioError
from engine.scenario.loader import ScenarioPack


@dataclass(frozen=True)
class ScenarioContext:
    pack: ScenarioPack
    configuration: ScenarioConfiguration

    def __post_init__(self) -> None:
        if self.configuration.scenario_id != self.pack.scenario_id:
            raise ScenarioError("scenario context pack/configuration id mismatch")
        if self.configuration.scenario_version != self.pack.version:
            raise ScenarioError("scenario context pack/configuration version mismatch")
        self.configuration.validate_against(self.pack)

    @property
    def registry(self):
        return self.pack.registry

    @property
    def retriever(self):
        return self.pack.retriever

    @classmethod
    def from_pack(
        cls,
        pack: ScenarioPack,
        *,
        mode="sequential",
        selected_pack_ids=None,
        start_chapter=None,
    ) -> "ScenarioContext":
        config = ScenarioConfiguration.from_pack(
            pack,
            mode=mode,
            selected_pack_ids=selected_pack_ids,
            start_chapter=start_chapter,
        )
        return cls(pack, config)
