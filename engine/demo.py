"""Development demo world bootstrap loaded from the scenario data-pack."""
from __future__ import annotations

from pathlib import Path

from engine.core.state import GameState
from engine.scenario.loader import load_scenario


def build_demo_state() -> GameState:
    root = Path(__file__).resolve().parent.parent
    pack = load_scenario(root / "scenarios" / "demo-bootstrap")
    return pack.build_state()
