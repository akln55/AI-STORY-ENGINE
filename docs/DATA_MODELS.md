# RPG Engine — Data Models

Version 1.0 · Phase 0 · 2026-09-23

Schemas are **design contracts**, not final code. Implementations must match
these schemas or trigger the conflict process (CONSTITUTION §3.3).

All entities carry: `id` (stable UUID/ULID), `created_turn`, `last_updated_turn`.

## 1. Authoritative state (engine-owned, AI cannot write)

- **Character**: name, level, realm/rank (scenario-defined scale), stats (map of
  named values), resources (HP, stamina, Qi/MP…), inventory (list of item
  instance refs), location ref, status effects.
- **World**: current time (turn + in-world clock), locations (graph), active
  events, weather/world flags defined by scenario.
- **NPC**: id, name, location ref, disposition toward player, memory refs,
  state flags, schedule.
  **Implemented as of v1.3** (`engine/core/state.py::NPCState`): id, name,
  location_id, hp/max_hp, disposition, alive, traits (categorical labels),
  personality (`NPCPersonality`: courage/aggression/sociability/honesty/
  greed/curiosity/loyalty/patience, each 0..100), goals (`list[NPCGoal]`:
  id/description/priority 0..100/status), fears (`list[str]`), preferences
  (`list[str]`). Schedule is **not implemented** (deferred).
  Mutability: disposition, alive, personality.*, traits, fears, preferences
  are settable via ordinary `npc_changes` (validated, see §3). `id`, `name`,
  and `goals` are **not** AI-mutable in v1.3 — identity is immutable by
  design (plan §9), goals are engine/scenario-owned only (plan §38); no AI
  proposal path exists for goal creation, deletion, priority, or status.
- **Quest/Event**: id, status (hidden/available/active/completed/failed),
  triggers, participants, deadlines.
- **Relationship**: player↔NPC or NPC↔NPC; tracks affinity, trust, standing,
  notable history refs.

## 2. Memory stores (typed, persistent; player/system separation is mandatory)

| Store | Content | Visibility |
|-------|---------|------------|
| Permanent Memory | Immutable core facts about the run | System |
| Character Memory | Facts about the player character | System; player-known subset revealed via narration |
| Relationship Memory | Relationship history, promises, grievances | Split per participant knowledge |
| Location Memory | What happened where; location state history | System |
| Event Memory | Outcomes of significant events | System |
| Item Memory | Item provenance, history, properties | Split (owner-known vs. hidden) |
| Knowledge Memory | Learned lore, skills, techniques | Split |
| Rumor | Unverified information with source + spread state | Player-known once heard |
| Secret | Hidden truths with reveal conditions | **System-only** until revealed |
| Recent Memory | Raw recent turns; compaction source | System |

**Visibility rule:** every memory record has a `known_by` field (e.g.,
`player`, `npc:<id>`, `faction:<id>`, `system`). Retrieval for a context built
for the player includes only records the player knows. No exceptions.

## 3. Structured AI response (per-turn contract)

```json
{
  "narrative": "string",
  "state_changes": [
    {"type": "resource|stat|inventory|location|relationship|quest|npc|world",
     "target": "entity id or path",
     "operation": "set|add|remove|move|start|complete|fail",
     "value": "any",
     "reason": "string"}
  ],
  "memory_updates": [
    {"store": "memory store name",
     "content": "string",
     "visibility": "player|npc:<id>|faction:<id>|system",
     "importance": 0,
     "entity_id": "item or npc id, optional",
     "location_id": "location id, optional",
     "event_id": "opaque string, optional; must reference an existing event",
     "tags": ["optional", "strings"]}
  ],
  "npc_changes": [
    {"npc": "npc id",
     "field": "disposition|alive|traits|fears|preferences|personality.<courage|aggression|sociability|honesty|greed|curiosity|loyalty|patience>",
     "value": "any"}
  ],
  "events_triggered": ["event id"],
  "available_actions": ["short action descriptions"]
}
```

Rules:
- `narrative` is player-facing text. It is **never** parsed for state.
- All other fields are proposals. `engine/core/validation.py` may accept, modify
  (clamped), or reject each item, with reasons logged.
- Unknown schema fields are rejected in development; ignored with a warning in
  production.
- `memory_updates` is fully consumed (`engine/core/game.py::
  GameSession._ingest_memory_updates`): `entity_id`/`location_id`/
  `visibility` are cross-checked against live world state before storage
  (unknown reference → record silently dropped, not stored partially);
  `event_id` is stored and cross-checked against the authoritative event registry.
- `npc_changes` for `personality.*`, `traits`, `fears`, `preferences` is
  fully consumed and validated (bounds, type, dead-NPC restriction) —
  see NPC entry in §1. `goals` is parsed but **rejected** by validation;
  goal mutation has no AI proposal path in v1.3.

## 4. Save format (Phase 8 contract)

- One SQLite file per save slot, containing all state + memory stores for one
  scenario instance.
- Header table: `engine_version`, `scenario_id`, `scenario_format_version`,
  `created`, `modified`.
- Export = copy of the SQLite file (optionally zipped with pack manifest).
- Import validates header before opening; mismatch = explicit error.

## 5. Scenario pack manifest (`pack.json`)

```json
{
  "id": "kebab-case-unique",
  "format_version": 1,
  "name": "string",
  "description": "string",
  "start": {"location": "loc id", "character_template": "char id"},
  "rule_hooks": ["named engine hook refs"]
}
```

Content files use Markdown with YAML front-matter (`id`, `type`, `tags`,
`relations`, `aliases`) for retrieval indexing.

## v1.4 Event Foundation

The engine now stores scenario-defined `EventState` records in `WorldState`. Events follow the lifecycle `inactive -> active -> resolved|failed|cancelled`. AI `events_triggered` proposals are converted into validated `event/trigger` effects for existing events only; the engine remains authoritative. Event state is persisted additively under save format v5. Event creation and arbitrary event-definition mutation are not AI capabilities in this phase.


## Quest Foundation (v1.5)

`WorldState.quests` stores scenario/engine-owned `QuestState` records. A quest has a lifecycle (`available`, `active`, `completed`, `failed`, `abandoned`) and ordered `QuestObjective` records. Objective progress is derived from authoritative state for `collect`, `reach`, and `defeat`; `talk` objectives are completed from validated dialogue actions. AI narrative cannot complete objectives. Quest rewards are declarative definitions converted into validation-gated effects by the quest transaction layer; AI cannot directly mutate quest lifecycle state.


## Scenario Pack v1

A scenario pack is identified by `manifest.json` and contains `world.json`.
`pack_format` is currently `1`. `world.json` maps directly to existing
authoritative state models (character, locations/exits, items, NPCs,
relationships, events, and quests). Optional Markdown lore lives below `lore/`.
The loader supports directories and ZIP archives and always runs the engine
invariant checker before returning a usable state.

## 1.1 Temporary status effects (engine v1.21)

`CharacterState.status_effects` and `NPCState.status_effects` store engine-owned
`StatusEffectState` records. Supported effect IDs are deterministic and closed:
`poison`, `bleed`, `burn`, `regeneration`, `stamina_regen`, `stunned`, and `rooted`.

Status effects carry duration, potency, stack count, maximum stacks, and an optional
source ID. Addition, removal, stacking, expiration, and per-turn resource ticks all
pass through the validation gate. Blocking effects are evaluated before a normal
player action; status ticks happen at the start of a committed turn. Status records
are persisted and remain backward-compatible with older saves that have no such key.
