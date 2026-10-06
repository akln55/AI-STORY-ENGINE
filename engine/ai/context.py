"""Per-turn context assembly with memory retrieval and bounded budget.

Budget is a deterministic character-budget approximation (not a true tokenizer).
Exceeding the budget trims lower-ranked memory lines first, then older recent
turns, rather than raising — production-safe. A hard ceiling still raises if
the irreducible core (system + state + action) alone exceeds the budget.
"""

from __future__ import annotations

from engine.core.state import GameState, NPCPersonality
from engine.ai.security import DEFAULT_AI_ACCESS_POLICY, rules_text
from engine.npc.encounter import EncounterResolver
from engine.npc.behavior import NPCBehaviorResolver
from engine.memory.retrieval import retrieve
from engine.memory.system import MemorySystem
from engine.scenario.retrieval import ScenarioRetriever
from engine.scenario.registry import ScenarioRegistry
from engine.scenario.configuration import ScenarioConfiguration
from dataclasses import dataclass

RECENT_TURNS_LIMIT = 10
MEMORY_RETRIEVAL_LIMIT = 8
# Deterministic character budget (approx. token stand-in; ~4 chars/token heuristic
# is NOT claimed — this is explicitly a character budget).
_CONTEXT_CHAR_BUDGET = 6000
_HARD_CEILING = 12000

NPC_MEMORY_RETRIEVAL_LIMIT = 8
SCENARIO_RETRIEVAL_LIMIT = 6
SCENARIO_DOCUMENT_LIMIT = 3

# Personality descriptor bands (plan §39: numeric state stays authoritative;
# this is a formatting-only translation for compact prompt text).
_LOW_BAND = 34
_HIGH_BAND = 67


@dataclass
class ContextDiagnostics:
    """Optional per-build diagnostics; never contains secrets or full context."""
    initial_chars: int = 0
    final_chars: int = 0
    memory_lines_dropped: int = 0
    scenario_lines_dropped: int = 0
    recent_turns_dropped: int = 0
    effective_budget: int = _CONTEXT_CHAR_BUDGET


def _personality_band(value: int) -> str:
    if value < _LOW_BAND:
        return "low"
    if value >= _HIGH_BAND:
        return "high"
    return "moderate"


def _personality_lines(personality: NPCPersonality) -> list[str]:
    fields = (
        "courage", "aggression", "sociability", "honesty",
        "greed", "curiosity", "loyalty", "patience",
    )
    return [
        f"  - {_personality_band(getattr(personality, f))} {f}"
        for f in fields
    ]


def _estimate_size(text: str) -> int:
    return len(text)


def assemble_context(
    state: GameState,
    recent_turns: list[str],
    player_input: str,
    memory: MemorySystem | None = None,
    *,
    viewer: str = "player",
    scenario_retriever: ScenarioRetriever | None = None,
    scenario_configuration: ScenarioConfiguration | None = None,
    scenario_registry: ScenarioRegistry | None = None,
    current_turn: int = 0,
    max_context_chars: int | None = None,
    diagnostics: ContextDiagnostics | None = None,
) -> str:
    """Build AI context. Never includes system-only or foreign-NPC memories."""
    if not DEFAULT_AI_ACCESS_POLICY.can("read_context"):
        raise PermissionError("AI context access is disabled by policy")
    core_lines = [
        "CORE SYSTEM: You narrate a text RPG. You never decide game state;",
        "you may only PROPOSE state changes, which the engine validates.",
        "RPG RULES: movement follows location exits; combat uses fixed damage;",
        "items belong to locations or owners. Dead NPCs cannot act.",
        "",
        rules_text(),
        "",
        "CHARACTER CONTEXT:",
        f"  name={state.character.name} hp={state.character.hp}/"
        f"{state.character.max_hp} stamina={state.character.stamina}/"
        f"{state.character.max_stamina}",
        f"  location={state.character.location_id} "
        f"inventory={sorted(state.character.inventory)}",
        f"  popularity={state.character.popularity} reputation={dict(sorted(state.character.reputation.items()))}",
        "  status_effects=" + ", ".join(
            f"{x.effect_type}(turns={x.remaining_turns},stacks={x.stacks},potency={x.potency})"
            for x in state.character.status_effects
        ) if state.character.status_effects else "  status_effects=none",
        "",
        "WORLD STATE:",
        f"  location name: {state.world.locations.get(state.character.location_id, '?')}",
        "  encounterable npcs here: " + ", ".join(
            f"{n.name}(id={n.id},disp={n.disposition}"
            + (f",traits={','.join(n.traits)}" if n.traits else "")
            + ")"
            for n in EncounterResolver(
                scenario_registry if scenario_registry is not None else getattr(scenario_retriever, "registry", None)
            ).encounterable_npcs(
                state, turn=current_turn
            )
        ),
        "  items here: " + ", ".join(
            i.name for i in state.world.items.values()
            if i.location_id == state.character.location_id
        ),
    ]
    available_quests = [q for q in state.world.quests.values() if q.status == "available"]
    if available_quests:
        core_lines += ["", "AVAILABLE QUESTS:"]
        for q in available_quests:
            core_lines.append(f"  {q.id}: {q.title}")

    active_quests = [q for q in state.world.quests.values() if q.status == "active"]
    if active_quests:
        core_lines += ["", "ACTIVE QUESTS:"]
        for q in active_quests:
            done = sum(1 for o in q.objectives if o.completed)
            core_lines.append(f"  {q.id}: {q.title} [{done}/{len(q.objectives)} objectives]")
            for o in q.objectives:
                mark = "done" if o.completed else f"{o.current_count}/{o.required_count}"
                core_lines.append(f"    - {o.description} [{mark}]")

    # Relationship snapshot for NPCs present
    rel_bits = []
    for n in state.world.npcs.values():
        if n.location_id != state.character.location_id or not n.alive:
            continue
        rel = state.world.get_relationship("player", n.id)
        if rel:
            rel_bits.append(
                f"{n.id}:affinity={rel.affinity},trust={rel.trust},flags={sorted(rel.flags)}")
    if rel_bits:
        core_lines += ["  relationships: " + "; ".join(rel_bits)]

    scenario_lines: list[str] = []
    if scenario_retriever is not None:
        chapter = scenario_configuration.current_chapter if scenario_configuration is not None else None
        if scenario_configuration is not None:
            scenario_configuration.validate_against(_retriever_pack(scenario_retriever))
        terms = [w for w in player_input.lower().split() if len(w) > 2]
        # Current location and encounterable NPC names are high-signal context, but
        # the registry remains read-only and the runtime state remains authoritative.
        location_id = state.character.location_id
        location_name = state.world.locations.get(location_id, location_id)
        query = " ".join([location_name, *terms])
        categories = ("characters", "locations", "items", "events", "factions", "techniques", "knowledge")
        hits = []
        for category in categories:
            hits.extend(scenario_retriever.record(
                category=category, query=query, chapter=chapter, viewer=viewer,
                limit=SCENARIO_RETRIEVAL_LIMIT,
            ))
        hits.sort(key=lambda h: (-h.score, h.category or "", h.record_id or ""))
        hits = hits[:SCENARIO_RETRIEVAL_LIMIT]
        docs = scenario_retriever.documents_for(
            query=" ".join(terms), chapter=chapter, limit=SCENARIO_DOCUMENT_LIMIT,
            include_global_lore=False,
        )
        if hits or docs:
            scenario_lines += ["", "RELEVANT SCENARIO CANON:"]
            if chapter is not None:
                scenario_lines.append(f"  active chapter: {chapter}")
            for hit in hits:
                rec = hit
                data = rec.document.content if rec.document is not None else None
                if data is not None:
                    continue
                record = scenario_retriever.registry.require(rec.category, rec.record_id).data
                name = record.get("name", rec.record_id)
                summary = record.get("summary", record.get("description", ""))
                line = f"  - [{rec.category}] {name} (id={rec.record_id})"
                if summary:
                    line += f": {summary}"
                scenario_lines.append(line)
            for hit in docs:
                doc = hit.document
                if doc is not None:
                    excerpt = " ".join(doc.content.split())[:500]
                    scenario_lines.append(f"  - [chapter source:{doc.kind}] {doc.title}: {excerpt}")

    memory_lines: list[str] = []
    if memory is not None and len(memory) > 0:
        loc = state.character.location_id
        terms = [w for w in player_input.lower().split() if len(w) > 2]
        records = retrieve(
            memory,
            viewer=viewer,
            location_id=None,  # prefer broad + rank; location bias via terms
            query_terms=terms,
            limit=MEMORY_RETRIEVAL_LIMIT,
        )
        # Also pull location-tagged if not already included.
        loc_recs = retrieve(
            memory, viewer=viewer, location_id=loc, limit=4,
        ) if loc else []
        seen = {r.id for r in records}
        for r in loc_recs:
            if r.id not in seen:
                records.append(r)
                seen.add(r.id)
        if records:
            memory_lines.append("")
            memory_lines.append("RELEVANT MEMORY:")
            for r in records[:MEMORY_RETRIEVAL_LIMIT]:
                memory_lines.append(
                    f"  [{r.store}|imp={r.importance}|t={r.created_turn}] {r.content}"
                )

    recent_lines = ["", "RECENT SCENE:"]
    for turn in recent_turns[-RECENT_TURNS_LIMIT:]:
        recent_lines.append(f"  {turn}")

    action_lines = ["", f"PLAYER ACTION: {player_input}"]

    def build(scn_lines: list[str], mem_lines: list[str], rec_lines: list[str]) -> str:
        return "\n".join(core_lines + scn_lines + mem_lines + rec_lines + action_lines)

    context = build(scenario_lines, memory_lines, recent_lines)
    size = _estimate_size(context)
    effective_budget = _CONTEXT_CHAR_BUDGET if max_context_chars is None else max(1, min(_CONTEXT_CHAR_BUDGET, max_context_chars))
    if diagnostics is not None:
        diagnostics.initial_chars = size
        diagnostics.effective_budget = effective_budget

    # Trim memory first, then older recent turns.
    memory_before = len(memory_lines)
    scenario_before = len(scenario_lines)
    recent_before = len(recent_lines)
    while size > effective_budget and len(memory_lines) > 2:
        # Retrieval is deterministic and lowest-ranked memory entries are last.
        memory_lines.pop()
        context = build(scenario_lines, memory_lines, recent_lines)
        size = _estimate_size(context)

    while size > effective_budget and len(scenario_lines) > 1:
        scenario_lines.pop()
        context = build(scenario_lines, memory_lines, recent_lines)
        size = _estimate_size(context)

    while size > effective_budget and len(recent_lines) > 2:
        # drop oldest recent (index 2 is first turn line after header)
        if len(recent_lines) > 2:
            recent_lines.pop(2)
        context = build(scenario_lines, memory_lines, recent_lines)
        size = _estimate_size(context)

    if size > effective_budget and effective_budget < _HARD_CEILING:
        # A provider-specific smaller window may make the irreducible core too large.
        raise RuntimeError(f"context budget exceeded after truncation ({size} > {effective_budget})")
    if size > _HARD_CEILING:
        raise RuntimeError(f"context hard ceiling exceeded ({size} > {_HARD_CEILING})")
    if diagnostics is not None:
        diagnostics.final_chars = size
        diagnostics.memory_lines_dropped = max(0, memory_before - len(memory_lines))
        diagnostics.scenario_lines_dropped = max(0, scenario_before - len(scenario_lines))
        diagnostics.recent_turns_dropped = max(0, recent_before - len(recent_lines))
    return context


def _retriever_pack(retriever: ScenarioRetriever):
    """Return a lightweight pack facade for configuration validation.

    ScenarioConfiguration validation needs scenario identity/chapter-manager data.
    Retrieval itself intentionally exposes only immutable registry/documents, so
    the loader attaches these optional attributes when a full ScenarioPack is used.
    """
    pack = getattr(retriever, "scenario_pack", None)
    if pack is None:
        raise ValueError("scenario_configuration requires a ScenarioRetriever loaded from a ScenarioPack")
    return pack


def assemble_npc_context(
    state: GameState,
    npc_id: str,
    memory: MemorySystem | None = None,
    *,
    query_terms: list[str] | None = None,
    scenario_registry: ScenarioRegistry | None = None,
    scenario_retriever: ScenarioRetriever | None = None,
    current_turn: int = 0,
) -> str:
    """Build context for reasoning ABOUT one NPC (plan §11, §37-39).

    Hard anti-spoiler invariant: retrieval uses viewer=f"npc:{npc_id}", so
    other NPCs' private (npc:<other>) memories and system-only records are
    never included — MemoryRecord.known_by enforces this the same way it
    does for the player-facing assemble_context above. This function does
    not decide what the NPC does (no behavior-evaluation layer, plan §17-19
    explicitly defers that); it only assembles facts an AI prompt or future
    rule could use to reason about the NPC.

    Raises KeyError if npc_id does not exist in state.world.npcs.
    """
    npc = state.world.npcs[npc_id]

    lines = [
        "NPC:",
        f"  id: {npc.id}",
        f"  name: {npc.name}",
        f"  location: {state.world.locations.get(npc.location_id, npc.location_id)}",
        f"  alive: {npc.alive}",
        "",
        "PERSONALITY PROFILE:",
        *_personality_lines(npc.personality),
    ]

    if npc.traits:
        lines += ["", "TRAITS:", *(f"  - {t}" for t in npc.traits)]

    if npc.fears:
        lines += ["", "FEARS:", *(f"  - {f}" for f in npc.fears)]

    if npc.preferences:
        lines += ["", "PREFERENCES:", *(f"  - {p}" for p in npc.preferences)]

    active_goals = [g for g in npc.goals if g.status == "active"]
    if active_goals:
        lines += ["", "ACTIVE GOALS:"]
        for g in sorted(active_goals, key=lambda g: -g.priority):
            lines.append(f"  - {g.description} [priority {g.priority}]")

    rel = state.world.get_relationship("player", npc.id)
    if rel is not None:
        lines += [
            "",
            "RELATIONSHIP TO PLAYER:",
            f"  affinity: {rel.affinity}",
            f"  trust: {rel.trust}",
        ]

    behavior = NPCBehaviorResolver(registry=scenario_registry).build(state, npc_id, turn=current_turn)
    lines += [
        "",
        "BEHAVIOR BOUNDARY:",
        f"  encounterable: {behavior.can_interact}",
        f"  allowed_action_types: {', '.join(behavior.allowed_action_types)}",
    ]

    if scenario_retriever is not None:
        hits = scenario_retriever.record(
            category="characters", record_id=npc_id, chapter=current_turn,
            viewer=f"npc:{npc_id}", limit=1,
        )
        if hits:
            record = scenario_retriever.registry.require("characters", npc_id).data
            lines += ["", "CANONICAL NPC DATA:"]
            for key in ("faction_id", "first_appearance_chapter", "last_known_chapter", "status"):
                if key in record:
                    lines.append(f"  {key}: {record[key]}")
            aliases = record.get("aliases")
            if isinstance(aliases, list) and aliases:
                lines.append("  aliases: " + ", ".join(str(a) for a in aliases))
            speech = record.get("speech_style")
            if isinstance(speech, dict):
                lines.append("  speech_style: " + ", ".join(f"{k}={v}" for k, v in sorted(speech.items())))
        knowledge = scenario_retriever.record(
            category="knowledge", query=" ".join(query_terms or ()),
            chapter=current_turn, viewer=f"npc:{npc_id}", limit=NPC_MEMORY_RETRIEVAL_LIMIT,
        )
        if knowledge:
            lines += ["", "SCENARIO KNOWLEDGE AVAILABLE TO NPC:"]
            for hit in knowledge:
                data = scenario_retriever.registry.require("knowledge", hit.record_id).data
                fact = data.get("fact", data.get("content", data.get("description", hit.record_id)))
                lines.append(f"  - {fact}")

    if memory is not None and len(memory) > 0:
        records = retrieve(
            memory,
            viewer=f"npc:{npc_id}",
            store="knowledge",
            query_terms=query_terms,
            limit=NPC_MEMORY_RETRIEVAL_LIMIT,
        )
        if records:
            lines += ["", "KNOWN FACTS:"]
            for r in records:
                lines.append(f"  - {r.content}")

    return "\n".join(lines)
