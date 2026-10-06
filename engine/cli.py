"""Minimal CLI gameplay loop (Phase 1; Kivy UI is Phase 7).

Usage:  python -m engine.cli
The engine core never prints (CONVENTIONS §1); this thin wrapper is the only
place player output is rendered.
"""

from __future__ import annotations

import sys

from engine.core.game import GameSession
from engine.demo import build_demo_state


def build_session(adapter=None) -> GameSession:
    """Thin seam so tests can build the same session the CLI uses."""
    return GameSession(state=build_demo_state(), adapter=adapter)


def main() -> int:
    session = build_session()
    print("RPG Engine — Phase 1 CLI demo world. Type 'help' for commands, 'quit' to exit.")
    print(session.handle_input("look"))
    while session.running:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        output = session.handle_input(line)
        if output:
            print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
