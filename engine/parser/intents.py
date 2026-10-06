"""Player free text -> structured intents (engine-owned, deterministic).

MVP command set per docs/PROTOTYPE_MVP.md: go, take, talk to, attack, look,
inventory, status, quit. Unknown input becomes a free-text intent passed to
the AI adapter (which may only narrate + propose validated changes).
"""

from __future__ import annotations

from dataclasses import dataclass

# Meta intents are handled by the session directly (info display, no effects).
META_ACTIONS = {"look", "inventory", "status", "help", "recover", "quit"}

# Rule-backed game intents.
RULE_ACTIONS = {"go", "take", "drop", "attack", "use", "accept", "abandon"}


@dataclass
class Intent:
    action: str          # go|take|drop|attack|use|accept|abandon|talk|free|look|inventory|status|help|quit
    target: str          # normalized target id/phrase ("" if none)
    raw: str             # original player input
    topic: str = ""      # optional dialogue topic

    @property
    def is_meta(self) -> bool:
        return self.action in META_ACTIONS


_VERBS = {
    "go": "go", "walk": "go", "move": "go", "head": "go",
    "take": "take", "grab": "take", "pick": "take",
    "drop": "drop",
    "attack": "attack", "hit": "attack", "strike": "attack", "fight": "attack",
    "use": "use", "cast": "use",
    "talk": "talk", "speak": "talk", "ask": "talk",
    "accept": "accept", "takequest": "accept",
    "abandon": "abandon", "quitquest": "abandon",
}


def _normalize_target(words: list[str]) -> str:
    return " ".join(words).strip().lower()


def parse_input(text: str) -> Intent:
    """Parse raw player input into an Intent. Pure function, no state access."""
    raw = text
    text = text.strip().lower()
    if not text:
        return Intent("free", "", raw)

    if text in ("look", "l", "inventory", "inv", "i", "status", "help", "recover", "quit"):
        aliases = {"l": "look", "inv": "inventory", "i": "inventory"}
        return Intent(aliases.get(text, text), "", raw)

    words = text.split()
    verb = _VERBS.get(words[0])
    rest = words[1:]

    # "talk to <npc>" / "speak with <npc>"
    if verb == "talk":
        if rest and rest[0] in ("to", "with"):
            rest = rest[1:]
        topic = ""
        for marker in ("about", "regarding", "on"):
            if marker in rest:
                idx = rest.index(marker)
                if idx > 0 and idx < len(rest) - 1:
                    topic = _normalize_target(rest[idx + 1:])
                    rest = rest[:idx]
                    break
        return Intent("talk", _normalize_target(rest), raw, topic=topic)

    if verb == "take" and rest[:1] == ["up"]:
        rest = rest[1:]

    if verb in ("go", "take", "drop", "attack", "use", "accept", "abandon"):
        return Intent(verb, _normalize_target(rest), raw)

    # Unknown phrasing: free-text intent for the AI.
    return Intent("free", "", raw)
