"""Rule registry: ordered list of rules; first match resolves an intent.

Scenario packs will contribute declarative hooks here later (ADR-0002); for now
the registry is assembled with the engine's built-in MVP rules.
"""

from __future__ import annotations

from engine.core.state import GameState
from engine.parser.intents import Intent
from engine.rules.base import Rule, RuleResult
from engine.rules import basic
from engine.npc.encounter import EncounterResolver


class RuleRegistry:
    def __init__(self, rules: list[Rule] | None = None, encounter_resolver: EncounterResolver | None = None):
        self._rules: list[Rule] = rules if rules is not None else default_rules(encounter_resolver)

    def resolve(self, intent: Intent, state: GameState) -> RuleResult | None:
        for rule in self._rules:
            result = rule.resolve(intent, state)
            if result is not None:
                return result
        return None


def default_rules(encounter_resolver: EncounterResolver | None = None) -> list[Rule]:
    return [
        basic.MovementRule(),
        basic.TakeRule(),
        basic.DropRule(),
        basic.AcceptQuestRule(),
        basic.AbandonQuestRule(),
        basic.AttackRule(encounter_resolver),
        basic.TechniqueRule(encounter_resolver),
    ]
