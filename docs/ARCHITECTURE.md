# RPG Engine — Architecture

Version 1.0 · Phase 0 · 2026-09-23

## 1. The gameplay loop (authoritative)

    PLAYER ACTION
    → ACTION PARSER            (free text → structured intent; engine-owned)
    → WORLD STATE              (current location, time, active events)
    → CHARACTER STATE          (stats, resources, inventory)
    → RELEVANT MEMORY          (retrieval, not full history)
    → SCENARIO LORE            (retrieved pack knowledge)
    → RPG RULES                (deterministic engine rules)
    → AI                       (narration + structured proposals only)
    → STRUCTURED RESPONSE      (schema-validated)
    → VALIDATION               (engine checks every proposal against rules)
    → STATE UPDATE             (only validated changes applied)
    → MEMORY UPDATE            (new memories classified & stored)
    → SAVE

Key invariant: steps after AI are **engine-owned**. The AI never writes state
directly.

## 2. Module map (planned, Phase 1+)

    engine/
      core/
        game.py            GameSession: owns the loop; orchestrates modules
        state.py           Authoritative runtime state (character, world, NPCs)
        clock.py           Game time / turns
        events.py          Event & quest state machines
        validation.py      Validates AI proposals against rules (hard gate)
      parser/
        intents.py         Player free text → structured intents
      rules/
        base.py            Rule interfaces (checks, resolvers, effects)
        registry.py        Rules contributed by engine + scenario hooks
      ai/
        adapter_base.py    AIAdapter interface (all providers implement this)
        schema.py          Structured output schema + parsing/validation
        context.py         Context assembly per turn (assemble_context, player-
                            facing) and per-NPC (assemble_npc_context, v1.3)
        fake.py            FakeAdapter — scripted, deterministic, for tests
        llama_cpp_adapter.py          LlamaCppAdapter (llama-cpp-python, desktop/dev)
        llama_cpp_process_adapter.py  LlamaCppProcessAdapter (development backend;
                                       localhost HTTP, not an end-user requirement)
      memory/
        system.py          MemorySystem/MemoryRecord: typed stores, visibility,
                            dedup (implemented; supersedes planned stores.py)
        retrieval.py       Deterministic filter/keyword/rank retrieval
        summarizer.py      Compaction of recent memory into durable memory (planned)
      npc/
        knowledge.py       Knowledge-as-memory helpers (grant_knowledge,
                            npc_knows, cross_check_refs) — implemented
      scenarios/
        loader.py          Pack discovery, loading, schema validation
        index.py           Scenario index / lore registry
      persistence/
        db.py              SQLite layer (persistent data)
        saves.py           Save slots, autosave, export/import
      ui/                  (Phase 7) interface layer; thin, swappable

## 3.1 AI security boundary

The in-app AI is an untrusted reasoning component. Its adapter interface exposes
only `generate(context)`. It receives a bounded, engine-assembled context and
returns a strict structured response. It has no filesystem, database, save,
scenario-write, code-execution, process-control, or tool-discovery capability.
See `docs/AI_SECURITY_SPEC.md`.

Scenario files and saves remain engine-owned. Local model files may be read by
the provider runtime as required for inference, but that is a deployment-level
process concern and is not exposed as an AI gameplay capability.

## 3. Layer rules

- `engine/core` never imports from `ai/`, `ui/`, or `scenarios/` content —
  **except** `core/game.py`, which is the composition root: it may depend on the
  `AIAdapter` *interface* (dependency-injected, never constructed) to drive the
  AI path. State/validation/clock/rules/parser remain fully AI-free.
- `ai/` receives a read-only view of state + assembled context; returns a
  structured response; has **no write path** to state.
- `ui/` never contains game rules; it renders state and forwards actions.
- Scenario packs may contribute: lore documents, data tables, and **declarative
  rule hooks** (e.g. thresholds, named effects). They may not ship executable
  engine code in Phase 1–5; scripted hooks are a later, gated decision (see
  docs/PROJECT_HISTORY.md when made).

## 4. Persistent data vs. runtime state

- **Runtime state** (in-memory, rebuilt from saves): current scene, cached
  retrieval indexes.
- **Persistent data** (SQLite, in `saves/` or user data dir): world state,
  character, NPCs, memory stores, events, save slots.
- Rule of thumb: if losing it would lose the game, it is persistent.

## 5. Context assembly (design contract)

Per-turn context, assembled by `engine/ai/context.py`:

    CORE SYSTEM PROMPT
    + RPG RULES (engine)
    + SCENARIO RULES (pack, retrieved)
    + CHARACTER CONTEXT (sheet + status)
    + WORLD STATE (location, time, nearby NPCs, active events)
    + RELEVANT MEMORY (retrieval-ranked, budget-capped)
    + RELEVANT LORE (pack retrieval)
    + CURRENT SCENE (recent beats, summarized as needed)
    + PLAYER ACTION (parsed intent + raw text)

Objective: **high relevance with minimal unnecessary context.** Budgets are
configurable constants; exceeding a budget fails loudly in development, trims by
rank in production.

**Per-NPC context (v1.3, implemented):** `assemble_npc_context(state, npc_id,
memory)` builds a separate, smaller context for reasoning *about* one NPC —
identity, personality (numeric state, described in bands: low/moderate/high),
traits, fears/preferences, active goals (sorted by priority; non-active goals
excluded), relationship-to-player, and knowledge retrieved with
`viewer=f"npc:{npc_id}"`. This reuses the same `MemoryRecord.known_by`
visibility rule as the player-facing context, so one NPC's private memory
never leaks into another NPC's context or the player's. It does not decide
NPC behavior — no autonomous planner or behavior-evaluation layer exists in
v1.3 (deferred; see AI_START_HERE.md).

## 6. Structured AI output

See DATA_MODELS.md §Structured AI Response for the schema. Narrative text and
state changes are separate fields; validation operates only on the structured
fields; narration is never parsed for state.

## 7. Long-session consistency strategy

1. **Bounded context** — every turn assembles only what retrieval selects.
2. **Tiered memory** — recent (turn-level) → durable (typed stores) → archive
   (compacted summaries). Promotion is engine-controlled, not AI-controlled.
3. **Anchors** — NPCs, locations, quests, and promises get stable IDs referenced
   across turns, so Turn 50 facts are retrievable at Turn 1000 by ID, not by
   re-reading history.
4. **Consistency checks** — validation step includes cheap contradiction checks
   (e.g., proposing to move to a location that no longer exists).

## 8. Save system design (contract for Phase 8)

- New Game / Save / Load / Autosave / multiple slots / Export / Import.
- One save = one scenario instance. Saves embed the scenario pack ID + pack
  format version; loading a save for a missing/incompatible pack is an explicit
  error, never a silent merge.
- Scenario isolation: runtime state is keyed by scenario instance ID; two
  scenarios never share runtime state or memory stores.

## 9. Scenario pack format (architecture only — no content yet)

    scenarios/<PackName>/
      pack.json                 (id, format_version, name, rules hooks refs)
      00_Scenario_Index.md      (machine-readable index of pack contents)
      Chapters/ Characters/ Factions/ Locations/ Items/
      Techniques/ Realms/ Events/ Relationships/ Timeline/ Lore/ Arcs/

Each content file carries front-matter (id, type, tags, relations) so the index
and retrieval layer can operate without parsing prose. Format is versioned;
`tools/` will include a pack validator.

## v1.4 Event Foundation

The engine now stores scenario-defined `EventState` records in `WorldState`. Events follow the lifecycle `inactive -> active -> resolved|failed|cancelled`. AI `events_triggered` proposals are converted into validated `event/trigger` effects for existing events only; the engine remains authoritative. Event state is persisted additively under save format v5. Event creation and arbitrary event-definition mutation are not AI capabilities in this phase.

Android hardening: packaged Android builds resolve default saves to app-private writable storage rather than beside bundled source files. Event terminal transitions also enforce chronological turn ordering.


### Quest authority

Quest state is engine-owned. Objective completion is computed from authoritative world state rather than narrative. Quest context is read-only prompt context. This prevents an AI response such as “quest completed” from changing quest state.


## 8. Current implementation boundary

At checkpoint v1.7.2 the scenario loader is intentionally a package-integrity
layer. It validates and discovers canonical JSON/Markdown files and constructs
the `world.json` bootstrap state. It does **not** yet expose canonical scenario
content as a mutable runtime registry or retrieve chapter Markdown during play.
Those responsibilities begin only in the Scenario Registry / Chapter Manager
phase defined by `AI_START_HERE.md`.
