"""Validate a scenario directory or .zip pack without third-party dependencies."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.scenario.loader import ScenarioError, load_scenario


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("usage: python tools/validate_scenario.py <scenario-dir-or-zip>")
        return 2
    try:
        pack = load_scenario(Path(args[0]))
    except (ScenarioError, OSError) as exc:
        print(f"INVALID: {exc}")
        return 1
    state = pack.build_state()
    print(f"VALID: {pack.scenario_id} {pack.version} — {pack.name}")
    print(f"locations={len(state.world.locations)} npcs={len(state.world.npcs)} "
          f"items={len(state.world.items)} events={len(state.world.events)} "
          f"quests={len(state.world.quests)} lore={len(pack.lore_documents)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
