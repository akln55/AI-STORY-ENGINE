"""GameSession: owns the gameplay loop and orchestrates modules (ADR-0001).

Flow:
  parse -> rules (deterministic) OR AI (narrate+propose) -> validation gate
  -> state update -> memory update -> turn clock.

AI proposals and rule effects share one apply path: core.validation.apply_effects.
There is no other way state mutates.

Memory updates from AI are proposals; only validated records enter MemorySystem.
"""

from __future__ import annotations

import copy

from engine.ai.adapter_base import AIAdapter
from engine.ai.context import assemble_context
from engine.ai.schema import StructuredResponse
from engine.core.clock import GameClock
from engine.core.state import GameState
from engine.core.validation import ValidationReport, apply_effects
from engine.core.status import is_action_blocked, tick_status_effects
from engine.memory.system import MemorySystem, MemoryValidationError
from engine.npc.knowledge import cross_check_refs
from engine.npc.reactions import NPCReactionEngine
from engine.parser.intents import Intent, parse_input
from engine.quest.system import evaluate_quests
from engine.npc.encounter import EncounterResolver
from engine.npc.dialogue import build_dialogue_context, resolve_dialogue_target
from engine.npc.simulation import NPCSimulationEngine
from engine.scenario.configuration import ScenarioConfiguration
from engine.scenario.context import ScenarioContext
from engine.scenario.errors import ScenarioError
from engine.events import EventEngine
from engine.rules.base import Effect
from engine.rules.registry import RuleRegistry

RECENT_LOG_LIMIT = 50
MAX_AI_RETRY_ATTEMPTS = 2
# One player action owns exactly one AI transaction. A transaction may retry
# malformed structured output, but it may never recursively start another AI
# transaction or continue autonomously after a response is applied.
MAX_AI_CALLS_PER_PLAYER_ACTION = 2
MAX_RETRY_FEEDBACK_CHARS = 700
MEMORY_MAINTENANCE_INTERVAL = 25
MEMORY_RECENT_RETENTION_TURNS = 100


class AIResponseExhaustedError(RuntimeError):
    """Raised when every AI attempt produced malformed structured output."""


class GameSession:
    @classmethod
    def from_scenario_pack(cls, pack, *, adapter=None, mode="sequential", selected_pack_ids=None, start_chapter=None, memory=None):
        """Construct a session from one validated scenario composition context."""
        context = ScenarioContext.from_pack(
            pack, mode=mode, selected_pack_ids=selected_pack_ids, start_chapter=start_chapter
        )
        return cls(
            pack.build_state(),
            adapter=adapter,
            memory=memory,
            scenario_context=context,
        )

    def __init__(
        self,
        state: GameState,
        adapter: AIAdapter | None = None,
        registry: RuleRegistry | None = None,
        memory: MemorySystem | None = None,
        scenario_registry=None,
        scenario_retriever=None,
        scenario_configuration: ScenarioConfiguration | None = None,
        scenario_context: ScenarioContext | None = None,
    ):
        self.state = state
        self.adapter = adapter
        if scenario_context is not None:
            if any(x is not None for x in (scenario_registry, scenario_retriever, scenario_configuration)):
                raise ValueError(
                    "scenario_context is mutually exclusive with individual scenario wiring"
                )
            self.scenario_registry = scenario_context.registry
            self.scenario_retriever = scenario_context.retriever
            self.scenario_configuration = scenario_context.configuration
        else:
            # A registry-only composition remains supported for low-level NPC/encounter
            # engine tests. Once retrieval or a persisted scenario configuration is involved,
            # the complete three-part composition is mandatory and ScenarioContext is preferred.
            if scenario_retriever is not None and (scenario_registry is None or scenario_configuration is None):
                raise ValueError(
                    "scenario_retriever requires scenario_registry and scenario_configuration; "
                    "use ScenarioContext for scenario sessions"
                )
            if scenario_configuration is not None and scenario_retriever is None:
                raise ValueError(
                    "scenario_configuration requires scenario_retriever; use ScenarioContext"
                )
            self.scenario_registry = scenario_registry
            self.scenario_retriever = scenario_retriever
            self.scenario_configuration = scenario_configuration
            if self.scenario_retriever is not None:
                pack = self.scenario_retriever.scenario_pack
                if self.scenario_registry is not pack.registry:
                    raise ValueError("scenario registry does not belong to the scenario retriever pack")
                self.scenario_configuration.validate_against(pack)
        self.encounter_resolver = EncounterResolver(self.scenario_registry)
        self.event_engine = EventEngine(self.scenario_registry)
        self.npc_simulation = NPCSimulationEngine(self.scenario_registry)
        self.npc_reactions = NPCReactionEngine()
        self.registry = registry or RuleRegistry(encounter_resolver=self.encounter_resolver)
        self.clock = GameClock()
        self.recent_turns: list[str] = []
        self.last_report: ValidationReport | None = None
        self.memory = memory if memory is not None else MemorySystem()
        self._quit = False
        # Re-entrancy guard: the AI can never call back into the gameplay loop
        # and create an AI->AI loop. This is an application invariant, not a
        # prompt instruction.
        self._ai_transaction_active = False
        # Last committed pre-action state. Used only for deterministic defeat
        # recovery; it is never an AI-controlled mutation path.
        self._recovery_checkpoint = None

    def handle_input(self, text: str) -> str:
        intent = parse_input(text)
        if intent.action == "quit":
            self._quit = True
            return "Farewell."
        if intent.is_meta:
            return self._handle_meta(intent)

        # Defeat is an authoritative gameplay phase derived from the
        # authoritative HP value. Once HP reaches zero, ordinary actions
        # cannot continue mutating the world until a future checkpoint/recovery
        # system explicitly resolves the defeat. This prevents a dead player
        # from moving, fighting, accepting quests, or asking the AI to mutate
        # state after lethal damage.
        if self.is_defeated:
            out = "You are defeated. The world is paused until recovery is resolved."
            self.last_report = None
            self._log_turn(intent.raw, out)
            return out

        self._capture_recovery_checkpoint()
        try:
            self.clock.advance()

            self.npc_simulation.advance(self.state, turn=self.clock.turn, memory=self.memory)
            self.encounter_resolver.current_turn = self.clock.turn
            tick_status_effects(self.state, turn=self.clock.turn)
            if self.is_defeated:
                out = "You are defeated. The world is paused until recovery is resolved."
                self.last_report = None
                self._log_turn(intent.raw, out)
                return out
            if is_action_blocked(self.state):
                out = "You are unable to act right now."
                self.last_report = None
                self._log_turn(intent.raw, out)
                return out
            if intent.action == "talk":
                return self._handle_dialogue(intent)
            result = self.registry.resolve(intent, self.state)
            if result is not None:
                report = apply_effects(result.effects, self.state)
                self.last_report = report
                if report.clean:
                    for effect in result.effects:
                        if effect.kind == "quest" and effect.operation == "activate":
                            quest = self.state.world.quests.get(effect.target)
                            if quest is not None and quest.started_turn is None:
                                quest.started_turn = self.clock.turn
                    evaluate_quests(self.state, current_turn=self.clock.turn)
                self._evaluate_scenario_events()
                self._maintain_memory()
                return self._compose_rule_output(intent, result, report)

            if self.adapter is None:
                return "You can't do that. (no AI adapter configured)"
            return self._handle_ai(intent)
        except Exception:
            # A turn is the engine transaction boundary above individual effect batches.
            # Unexpected provider, scenario, simulation, or integration errors must never
            # leave the world half-advanced. Restore the exact pre-turn snapshot and
            # re-raise so the application layer can surface the real failure.
            self._rollback_failed_turn()
            raise

    @property
    def running(self) -> bool:
        return not self._quit

    @property
    def can_recover(self) -> bool:
        """Whether a committed pre-defeat checkpoint is available."""
        return self._recovery_checkpoint is not None

    def _rollback_failed_turn(self) -> None:
        """Restore the exact state captured immediately before a failed turn."""
        checkpoint = self._recovery_checkpoint
        if checkpoint is None:
            return
        self.state = copy.deepcopy(checkpoint["state"])
        self.clock.turn = checkpoint["turn"]
        self.recent_turns = copy.deepcopy(checkpoint["recent_turns"])
        self.memory = copy.deepcopy(checkpoint["memory"])
        self.scenario_configuration = copy.deepcopy(checkpoint["scenario_configuration"])
        self.encounter_resolver.current_turn = self.clock.turn
        self.last_report = None

    def _capture_recovery_checkpoint(self) -> None:
        """Capture the exact pre-action state before a mutating turn.

        The checkpoint is deliberately engine-owned and deep-copied so later
        combat/NPC/event mutations cannot alter the recovery target.
        """
        self._recovery_checkpoint = {
            "state": copy.deepcopy(self.state),
            "turn": self.clock.turn,
            "recent_turns": copy.deepcopy(self.recent_turns),
            "memory": copy.deepcopy(self.memory),
            "scenario_configuration": copy.deepcopy(self.scenario_configuration),
        }

    def recover_from_defeat(self) -> str:
        """Restore the last pre-action checkpoint after player defeat."""
        if not self.is_defeated:
            return "You are not defeated."
        if self._recovery_checkpoint is None:
            return "No recovery checkpoint is available."
        checkpoint = self._recovery_checkpoint
        self.state = copy.deepcopy(checkpoint["state"])
        self.clock.turn = checkpoint["turn"]
        self.recent_turns = copy.deepcopy(checkpoint["recent_turns"])
        self.memory = copy.deepcopy(checkpoint["memory"])
        self.scenario_configuration = copy.deepcopy(checkpoint["scenario_configuration"])
        self.last_report = None
        self._recovery_checkpoint = None
        return "Recovery complete. You return to the last committed state before defeat."

    def export_recovery_checkpoint(self):
        """Return a persistence-safe recovery snapshot, if one exists."""
        if self._recovery_checkpoint is None:
            return None
        from engine.persistence.db import state_to_dict
        cp = self._recovery_checkpoint
        payload = state_to_dict(cp["state"], cp["turn"], cp["recent_turns"], cp["memory"])
        config = cp["scenario_configuration"].to_dict() if cp["scenario_configuration"] is not None else None
        return {"state": payload, "scenario_configuration": config}

    def import_recovery_checkpoint(self, payload) -> None:
        """Restore a persisted recovery checkpoint into the session."""
        if not payload:
            self._recovery_checkpoint = None
            return
        from engine.persistence.db import state_from_dict
        state, turn, recent, memory = state_from_dict(payload["state"])
        config_raw = payload.get("scenario_configuration")
        config = ScenarioConfiguration.from_dict(config_raw) if config_raw else None
        self._recovery_checkpoint = {
            "state": state,
            "turn": turn,
            "recent_turns": recent,
            "memory": memory,
            "scenario_configuration": config,
        }

    @property
    def is_defeated(self) -> bool:
        """Whether the player is in the authoritative defeated phase."""
        return self.state.character.hp <= 0

    def _handle_meta(self, intent: Intent) -> str:
        c = self.state.character
        if intent.action == "look":
            here = c.location_id
            npcs = ", ".join(n.name for n in self.encounter_resolver.encounterable_npcs(self.state, turn=self.clock.turn)) or "none"
            items = ", ".join(i.name for i in self.state.world.items.values()
                              if i.location_id == here) or "none"
            exits = ", ".join(self.state.world.exits.get(here, [])) or "none"
            return (f"[{self.state.world.locations.get(here, here)}]\n"
                    f"You see: {npcs}. Items: {items}. Exits: {exits}.")
        if intent.action == "inventory":
            if not c.inventory:
                return "You carry nothing."
            names = [self.state.world.items[i].name for i in c.inventory
                     if i in self.state.world.items]
            return "You carry: " + ", ".join(names) + "."
        if intent.action == "status":
            phase = "DEFEATED" if self.is_defeated else "ACTIVE"
            location = self.state.world.locations.get(c.location_id, "?")
            return (f"{c.name} — HP {c.hp}/{c.max_hp}, "
                    f"stamina {c.stamina}/{c.max_stamina}, "
                    f"location: {location}, phase: {phase}, "
                    f"effects: {", ".join(x.effect_type for x in c.status_effects) or "none"}")
        if intent.action == "recover":
            return self.recover_from_defeat()
        if intent.action == "help":
            return ("Commands: go <place>, take <item>, drop <item>, "
                    "attack <target>, talk to <npc>, accept <quest>, abandon <quest>, "
                    "look, inventory, status, recover, quit. Anything else is described by the narrator.")
        return ""

    def _handle_dialogue(self, intent: Intent) -> str:
        target = resolve_dialogue_target(self.state, intent.target, self.encounter_resolver)
        if target is None:
            out = f"There is no NPC matching '{intent.target}'." if intent.target else "Talk to whom?"
            self.last_report = None
            self._log_turn(intent.raw, out)
            return out
        if not target.encounterable:
            if target.npc.location_id != self.state.character.location_id:
                out = f"The {target.npc.name} is not here."
            else:
                out = f"You cannot reach {target.npc.name} right now."
            self.last_report = None
            self._log_turn(intent.raw, out)
            return out
        if self.adapter is None:
            out = f"You can speak with {target.npc.name}, but no AI narrator is configured."
            self.last_report = None
            self._log_turn(intent.raw, out)
            return out
        self._ai_transaction_active = True
        try:
            return self._handle_ai_transaction(
                intent,
                dialogue_context=build_dialogue_context(
                    self.state, target, registry=self.scenario_registry, current_turn=self.clock.turn,
                    topic=intent.topic,
                ),
                talked_to=target.npc.id,
            )
        finally:
            self._ai_transaction_active = False
    def _handle_ai(self, intent: Intent) -> str:
        if self._ai_transaction_active:
            # Defensive guard for custom adapters/providers. Normal adapters
            # cannot reach this path, but future tool-enabled providers must
            # not be able to recursively consume tokens.
            out = "The narrator is already processing this action."
            self.last_report = None
            self._log_turn(intent.raw, out)
            return out

        self._ai_transaction_active = True
        try:
            return self._handle_ai_transaction(intent)
        finally:
            self._ai_transaction_active = False
    def _handle_ai_transaction(self, intent: Intent, *, dialogue_context: str | None = None, talked_to: str | None = None) -> str:
        context = assemble_context(
            self.state, self.recent_turns, intent.raw, memory=self.memory,
            viewer="player", scenario_retriever=self.scenario_retriever,
            scenario_configuration=self.scenario_configuration,
            current_turn=self.clock.turn,
        )
        if dialogue_context:
            context += "\n\n" + dialogue_context
        try:
            response = self._generate_with_retry(
                context, attempts=MAX_AI_CALLS_PER_PLAYER_ACTION
            )
        except AIResponseExhaustedError:
            out = "The narrator falters and has nothing coherent to say."
            self.last_report = None
            self._log_turn(intent.raw, out)
            return out
        effects = self._effects_from_response(response)
        if talked_to is not None:
            effects = self._scope_dialogue_effects(effects, talked_to)
        effects.extend(
            Effect(kind="event", target=event_id, operation="trigger",
                   value=self.clock.turn, reason="event trigger from AI")
            for event_id in response.events_triggered
        )
        report = apply_effects(effects, self.state)
        self.last_report = report
        if report.clean:
            evaluate_quests(self.state, talked_to=talked_to, current_turn=self.clock.turn)
            self._evaluate_scenario_events()
        self._ingest_memory_updates(response, report)
        if talked_to is not None and report.clean:
            reaction_report = apply_effects(
                list(self.npc_reactions.effects_for_player_interaction(
                    self.state, talked_to, outcome="talk"
                )),
                self.state,
            )
            if reaction_report.clean:
                report.accepted.extend(reaction_report.accepted)
            else:
                report.rejected.extend(reaction_report.rejected)
        self._maintain_memory()
        player_text = self._compose_ai_output(response, report)
        self._log_turn(intent.raw, player_text)
        return player_text

    def _evaluate_scenario_events(self) -> None:
        results = self.event_engine.evaluate(
            self.state, turn=self.clock.turn, configuration=self.scenario_configuration
        )
        if self.scenario_configuration is None:
            return
        for result in results:
            if result.new_chapter is None:
                continue
            try:
                pack = self.scenario_retriever.scenario_pack if self.scenario_retriever is not None else None
                if pack is None or pack.chapter_manager is None:
                    continue
                pack.chapter_manager.validate_chapter_access(
                    result.new_chapter,
                    self.scenario_configuration.selected_pack_ids,
                    self.scenario_configuration.mode,
                )
                self.scenario_configuration = self.scenario_configuration.with_current_chapter(result.new_chapter)
            except ScenarioError:
                # Invalid chapter transitions never become runtime state.
                continue

    def _ingest_memory_updates(
        self, response: StructuredResponse, report: ValidationReport
    ) -> None:
        """AI memory_updates are proposals; validate then store.

        Authority policy (ADR memory-write):
        - If the response proposed any state/npc effects and any were rejected,
          accompanying memory_updates are discarded. Rejected state must not
          become durable "facts" via memory (e.g. "player received sword" when
          the take was rejected).
        - Pure memory turns (no state_changes / npc_changes proposed) are allowed.
        - Successful (clean) effect batches allow memory_updates.
        - Each update still passes MemorySystem validation / dedup.
        """
        proposed_effects = bool(response.state_changes) or bool(response.npc_changes)
        if proposed_effects and not report.clean:
            return
        turn = self.clock.turn
        for mu in response.memory_updates:
            try:
                cross_check_refs(
                    self.state,
                    entity_id=mu.entity_id,
                    location_id=mu.location_id,
                    visibility=mu.visibility,
                    event_id=mu.event_id,
                )
                self.memory.add_from_proposal(
                    store=mu.store,
                    content=mu.content,
                    visibility=mu.visibility,
                    importance=mu.importance,
                    created_turn=turn,
                    entity_id=mu.entity_id,
                    location_id=mu.location_id,
                    event_id=mu.event_id,
                    tags=mu.tags,
                )
            except MemoryValidationError:
                continue

    def _maintain_memory(self) -> None:
        """Run bounded, lossless memory maintenance at deterministic intervals."""
        if self.clock.turn % MEMORY_MAINTENANCE_INTERVAL != 0:
            return
        if len(self.memory) < 500:
            return
        self.memory.archive_older_than(
            self.clock.turn, max_age=MEMORY_RECENT_RETENTION_TURNS, stores=("recent",)
        )

    def _generate_with_retry(
        self, context: str, attempts: int = MAX_AI_RETRY_ATTEMPTS
    ) -> StructuredResponse:
        last_err: ValueError | None = None
        attempts = max(1, min(int(attempts), MAX_AI_CALLS_PER_PLAYER_ACTION))
        for _ in range(attempts):
            try:
                return self.adapter.generate(context)
            except ValueError as err:
                last_err = err
                context = self._retry_feedback(context, err)
        raise AIResponseExhaustedError(
            f"AI adapter returned malformed structured output after "
            f"{attempts} attempt(s); giving up: {last_err}"
        ) from last_err

    @staticmethod
    def _retry_feedback(context: str, err: ValueError) -> str:
        safe_error = str(err)[:MAX_RETRY_FEEDBACK_CHARS]
        return (
            f"{context}\n\n"
            "SYSTEM NOTE: the previous response was malformed. This is the "
            "only permitted retry for this player action. Do not perform any "
            "additional actions, tool calls, or follow-up turns. Validation "
            f"error: {safe_error}\n"
            "Return ONLY valid JSON matching the required schema. Do not include Markdown fences or explanatory text."
        )

    @staticmethod
    def _scope_dialogue_effects(effects: list[Effect], talked_to: str) -> list[Effect]:
        """Prevent a conversation with one NPC from silently mutating another NPC.

        Dialogue may still produce normal validated world consequences (for
        example a relationship change or an event trigger), but NPC-specific
        changes must belong to the NPC actually being addressed.
        """
        scoped: list[Effect] = []
        for effect in effects:
            if effect.kind == "npc" and effect.target != talked_to:
                continue
            if effect.kind == "relationship":
                target = effect.target.replace(":", "|")
                parts = target.split("|", 1)
                if len(parts) == 2 and talked_to not in parts:
                    continue
            scoped.append(effect)
        return scoped

    @staticmethod
    def _effects_from_response(response: StructuredResponse) -> list[Effect]:
        effects = []
        for change in response.state_changes:
            value = change.value
            if change.type == "npc" and change.operation == "set":
                if isinstance(value, list) and len(value) == 2:
                    value = tuple(value)
            effects.append(Effect(
                kind=change.type, target=change.target,
                operation=change.operation, value=value, reason=change.reason,
            ))
        for npc_change in response.npc_changes:
            effects.append(Effect(
                kind="npc", target=npc_change.npc, operation="set",
                value=(npc_change.field, npc_change.value),
                reason="npc_change from AI",
            ))
        return effects

    def _compose_rule_output(self, intent: Intent, result, report: ValidationReport) -> str:
        if report.rejected:
            reasons = "; ".join(r.reason for r in report.rejected)
            out = f"{result.narration_hint} (engine note: {reasons})"
            self._log_turn(intent.raw, out)
            return out
        self._log_turn(intent.raw, result.narration_hint)
        return result.narration_hint

    def _compose_ai_output(self, response: StructuredResponse, report: ValidationReport) -> str:
        """Narrative consistency: if any effects were rejected, do not present
        the AI narrative as an unqualified success. Prefix a clear engine note.
        """
        text = response.narrative
        if report.rejected:
            reasons = "; ".join(r.reason for r in report.rejected)
            text = f"(The attempt does not fully succeed: {reasons})\n{text}"
        if response.available_actions:
            actions = [a.strip() for a in response.available_actions if a.strip()]
            if actions:
                text += "\nAvailable actions: " + " | ".join(actions[:8])
        return text

    def _log_turn(self, player_text: str, outcome: str) -> None:
        self.recent_turns.append(f"T{self.clock.turn} player: {player_text}")
        if outcome:
            self.recent_turns.append(f"T{self.clock.turn} outcome: {outcome}")
        if len(self.recent_turns) > RECENT_LOG_LIMIT:
            del self.recent_turns[: len(self.recent_turns) - RECENT_LOG_LIMIT]
