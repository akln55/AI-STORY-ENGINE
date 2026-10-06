"""Authoritative game state (engine-owned only; AI never writes these).

Design contract: docs/DATA_MODELS.md §1.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StatusEffectState:
    """Persistent temporary effect attached to an actor."""

    effect_type: str
    remaining_turns: int
    potency: int = 1
    stacks: int = 1
    max_stacks: int = 1
    source_id: str | None = None


@dataclass
class CharacterState:
    """Authoritative player state, including deterministic progression/combat stats."""

    name: str = "Player"
    hp: int = 100
    max_hp: int = 100
    stamina: int = 100
    max_stamina: int = 100
    attack_power: int = 15
    defense: int = 0
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100
    realm_id: str = "base"
    realm_stage: int = 0
    location_id: str = ""
    inventory: list[str] = field(default_factory=list)
    techniques: list[str] = field(default_factory=list)
    popularity: int = 0
    reputation: dict[str, int] = field(default_factory=dict)
    status_effects: list[StatusEffectState] = field(default_factory=list)

    def has_item(self, item_id: str) -> bool:
        return item_id in self.inventory


@dataclass
class NPCPersonality:
    """Bounded (0..100) quantitative behavioral tendencies.

    Foundation only — a small, fixed set of parameters, not a psychology
    simulator. Complements (does not replace) NPCState.traits: traits are
    categorical labels, personality is numeric. See docs/DATA_MODELS.md §1.
    """

    courage: int = 50
    aggression: int = 50
    sociability: int = 50
    honesty: int = 50
    greed: int = 50
    curiosity: int = 50
    loyalty: int = 50
    patience: int = 50


@dataclass
class NPCGoal:
    """Persistent internal character state — not a quest.

    Engine/scenario-owned in this phase: not mutable via ordinary AI
    npc_changes (creation, deletion, priority, and status are all
    out of scope for AI proposals until a future goal-mutation system
    explicitly defines a legal transition).
    """

    id: str
    description: str
    priority: int
    status: str = "active"
    # Deterministic execution metadata. Empty for legacy/passive goals.
    kind: str = "passive"
    target_id: str | None = None
    target_location: str | None = None
    required_progress: int = 1
    progress: int = 0
    data: dict[str, object] = field(default_factory=dict)


@dataclass
class NPCState:
    id: str
    name: str
    location_id: str
    hp: int = 50
    max_hp: int = 50
    attack_power: int = 5
    defense: int = 0
    xp_reward: int = 25
    disposition: int = 0  # -100 (hostile) .. 100 (devoted)
    alive: bool = True
    # Foundation: short stable trait labels (not a personality engine)
    traits: list[str] = field(default_factory=list)
    # v1.3: quantitative behavioral tendencies (0..100 each)
    personality: NPCPersonality = field(default_factory=NPCPersonality)
    # v1.3: persistent internal goals (engine/scenario-owned; see NPCGoal)
    goals: list[NPCGoal] = field(default_factory=list)
    # v1.3: context signals only, not automatic rules (plan §8)
    fears: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    status_effects: list[StatusEffectState] = field(default_factory=list)


@dataclass
class ItemState:
    """An item instance. Exactly one of location_id (lying somewhere) or
    owner ('player' / npc id) is set."""

    id: str
    name: str
    location_id: str | None = None
    owner: str | None = None


@dataclass
class TechniqueState:
    """Scenario-defined combat technique. Execution remains engine-authoritative."""

    id: str
    name: str
    power: int = 0
    stamina_cost: int = 10
    description: str = ""


@dataclass
class RelationshipState:
    """Directed relationship between two parties.

    party_a / party_b are 'player' or an npc id.
    Keyed in WorldState by canonical_key(party_a, party_b) for undirected lookup,
    but affinity is stored as directed from a→b in this record (symmetric default).
    """

    party_a: str
    party_b: str
    affinity: int = 0  # -100 .. 100
    trust: int = 0  # -100 .. 100
    flags: list[str] = field(default_factory=list)  # e.g. "promise", "grievance"

    @staticmethod
    def canonical_key(a: str, b: str) -> str:
        """Stable undirected key for storage."""
        return "|".join(sorted([a, b]))


@dataclass
class EventState:
    """Persistent world event state owned by the engine.

    Events are scenario-defined records. The AI may request a legal transition,
    but cannot create arbitrary event definitions or bypass lifecycle rules.
    """

    id: str
    type: str
    status: str = "inactive"
    start_turn: int | None = None
    resolved_turn: int | None = None
    location_id: str | None = None
    participants: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class QuestObjective:
    """Authoritative quest objective progress.

    `type` is one of collect/reach/defeat/talk. Progress is derived from
    authoritative state by the quest system; AI narrative cannot complete it.
    """

    id: str
    description: str
    type: str
    target_id: str
    required_count: int = 1
    current_count: int = 0
    completed: bool = False


@dataclass
class QuestState:
    """Persistent quest definition and lifecycle state.

    Quests are scenario/engine-owned. Reward definitions are declarative and
    are converted into validation-gated effects by the quest transaction layer.
    """

    id: str
    title: str
    description: str = ""
    status: str = "available"
    giver: str | None = None
    participants: list[str] = field(default_factory=list)
    objectives: list[QuestObjective] = field(default_factory=list)
    rewards: list[dict[str, object]] = field(default_factory=list)
    rewards_claimed: bool = False
    prerequisites: list[dict[str, object]] = field(default_factory=list)
    hidden: bool = False
    expires_turn: int | None = None
    started_turn: int | None = None
    completed_turn: int | None = None
    failed_turn: int | None = None
    unlocks_on_complete: list[str] = field(default_factory=list)
    unlocks_on_fail: list[str] = field(default_factory=list)


@dataclass
class WorldState:
    """Locations graph + item/NPC placement + relationships."""

    locations: dict[str, str] = field(default_factory=dict)  # id -> display name
    exits: dict[str, list[str]] = field(default_factory=dict)  # id -> reachable ids
    items: dict[str, ItemState] = field(default_factory=dict)
    npcs: dict[str, NPCState] = field(default_factory=dict)
    relationships: dict[str, RelationshipState] = field(default_factory=dict)
    events: dict[str, EventState] = field(default_factory=dict)
    quests: dict[str, QuestState] = field(default_factory=dict)
    techniques: dict[str, TechniqueState] = field(default_factory=dict)

    def location_exists(self, location_id: str) -> bool:
        return location_id in self.locations

    def npc_exists(self, npc_id: str) -> bool:
        return npc_id in self.npcs

    def item_exists(self, item_id: str) -> bool:
        return item_id in self.items

    def reachable(self, from_id: str, to_id: str) -> bool:
        return to_id in self.exits.get(from_id, [])

    def event_exists(self, event_id: str) -> bool:
        return event_id in self.events

    def quest_exists(self, quest_id: str) -> bool:
        return quest_id in self.quests

    def party_exists(self, party_id: str) -> bool:
        return party_id == "player" or party_id in self.npcs

    def get_relationship(self, a: str, b: str) -> RelationshipState | None:
        return self.relationships.get(RelationshipState.canonical_key(a, b))


@dataclass
class GameState:
    """Root state container owned by GameSession."""

    character: CharacterState
    world: WorldState
