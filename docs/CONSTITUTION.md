# RPG Engine — Project Constitution

Version 1.0 · Phase 0 · 2026-09-23

This document is the binding rule set for the project. It overrides habit,
convenience, and undocumented decisions. Everything else in `docs/` elaborates it.

---

## 1. Mission

Build a private, personal-use, text-based RPG engine with persistent world state,
character/NPC state, deterministic rules, AI-driven narration, long-term memory,
lore retrieval, scenario packs, and save/load — designed for sessions of hundreds
to thousands of turns.

## 2. Non-negotiable principles

1. **The engine is authoritative; the AI is not.**
   AI output is narration plus *proposed* state changes. Every state change an AI
   proposes must pass engine validation before it is applied. The AI can never
   directly set HP, level, inventory, quests, NPC state, relationships, location,
   time, or events.
2. **Engine ≠ Scenario.**
   No fictional world (Martial Peak or otherwise) is hard-coded in the engine.
   Scenarios are data/content packages. Adding a new scenario must require little
   or no engine modification.
3. **Memory is retrieved, not dumped.**
   The full story history is never sent to the AI every turn. Context is assembled
   per turn from memory stores and lore retrieval.
4. **Player-known vs. system-known information is strictly separated.**
   Unknown secrets, rumors not yet heard, and hidden NPC state must not leak into
   player-visible narration or into prompts that influence what the player "knows".
5. **Long-session consistency is a design goal, not an afterthought.**
   The architecture must support Turn 1 → Turn 1000 continuity with bounded context.
6. **Simple and maintainable over clever.**
   No dependency without a stated reason. No premature abstraction. No
   over-engineering.
7. **Free / no-subscription-dependent tooling wherever reasonably possible.**
   The user develops from Android; the workflow must work without paid services.
8. **Documentation is the persistent source of truth.**
   The user must never need to re-provide conversation context. Important decisions
   live in this project's Markdown files.
9. **Test, don't assume.**
   Each phase has testable exit criteria (see AI_START_HERE.md). Untested systems are
   considered broken.
10. **Backward compatibility when practical.**
    Save formats and scenario pack formats are versioned; breaking changes are
    deliberate, documented ADRs — never accidental.

## 3. Change control

### 3.1 Silent changes are forbidden

Established architecture may not be silently changed. If an architectural change
is necessary:

1. Explain the problem.
2. Explain why the current design is insufficient.
3. Propose the alternative.
4. Identify affected files.
5. Implement only after the above is recorded.

### 3.2 Amendments to this constitution

Any change to this document is an Amendment. Amendments require:

- a new entry in `docs/PROJECT_HISTORY.md` (ADR format) stating the change and reason,
- a version bump of this document,
- a note in AI_START_HERE.md if the change affects phase scope.

### 3.3 Conflicts

If code and specification conflict, identify the conflict explicitly (file +
section), then resolve per §3.1. Never silently choose one side.

## 4. Scope boundaries

- **In scope:** the engine, scenario pack format, memory/retrieval, AI pipeline
  with validation, save system, tests, Android packaging.
- **Out of scope (for now):** multiplayer, graphics, audio, public release,
  networked services, monetization, any Martial Peak content population
  (architecture only in Phase 5).

## 5. Definitions

- **Engine** — the scenario-agnostic runtime that owns rules and state.
- **Scenario** — a data/content package (world, lore, characters, rules hooks)
  loaded by the engine.
- **State** — authoritative game data owned by the engine.
- **Proposal** — a structured AI output requesting state changes; never applied
  without validation.
- **Memory store** — a persistent, typed knowledge repository (see DATA_MODELS.md).
- **Context** — the per-turn prompt payload assembled by the engine.


---

## Current product-scope note — pending formal amendment (2026-10-05)

The historical scope section still describes networked services as out of scope. The current product decision is hybrid: local GGUF + Google Gemini API + OpenAI API, with explicit user-controlled external research capability.

This note does **not** silently amend the binding constitution. The formal amendment remains an open decision and requires user approval under the change-control rules above. Until then, the current implementation must not treat the old wording as permission to remove the confirmed hybrid-AI product requirement.
