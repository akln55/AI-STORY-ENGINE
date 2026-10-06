# RPG Engine — Minimal Working Prototype (MVP) Definition

Version 1.0 · Phase 0 · 2026-09-23

This defines the **smallest playable slice** that still proves the core thesis:
*the engine owns state; the AI narrates and proposes; validation gates everything.*

The MVP spans the original Phases 1–3. The historical phase plan is summarized in docs/PROJECT_HISTORY.md. Everything here is a definition —
nothing is implemented yet.

## MVP feature set

1. **CLI loop** (text in / text out; UI comes in Phase 7).
2. **One minimal scenario pack** (`scenarios/demo/`, generic fantasy "village +
   forest road" — deliberately *not* Martial Peak) with:
   - 3 locations, 1 NPC, 2 items, 1 simple quest.
   - `pack.json` + indexed Markdown lore files per ARCHITECTURE.md §9.
3. **Character state**: HP, stamina, inventory, location. (Level/stats/Qi come
   in Phase 6.)
4. **Action parser**: handles `go <place>`, `take <item>`, `talk to <npc>`,
   `attack <target>`, `look`, `inventory`, `status`, `quit`; unknown actions fall
   through to a free-text intent passed to the AI.
5. **Deterministic rules**: movement between known locations, item
   take/drop ownership, simple combat resolution (HP/stamina deltas) — engine
   resolves these; the AI narrates the outcome.
6. **AI pipeline** with the structured response schema (DATA_MODELS.md §3):
   - Assembled context (system + rules + scenario + state + recent memory).
   - Scripted fake adapter for tests; llama.cpp adapter for real runs.
   - Validation gate: unvalidated proposals rejected/logged; state only changes
     through the gate.
7. **Recent Memory store** (the other nine stores land in Phase 4, with retrieval).
8. **Save/Load**: one slot, SQLite file. (Multiple slots/autosave/export in Phase 8.)

## MVP acceptance tests (all must pass to exit Phase 3)

- T1: `go forest` moves the character; engine state confirms location change;
  AI receives the move as context, not as its own decision.
- T2: `take rope` adds rope to inventory; engine owns the item; a fabricated AI
  proposal to grant a nonexistent item is rejected by validation.
- T3: Attack the NPC: HP changes match the combat rule exactly, even if the AI
  narrated a different number.
- T4: Save, exit, load → identical state.
- T5: Turn 200 smoke test: 200 arbitrary turns run without context growth beyond
  the configured budget (Recent Memory compaction works).

## Explicit non-goals for the MVP

- No semantic retrieval, no full memory store set, no quests engine (single
  hard-coded check), no UI, no Android packaging, no Martial Peak content.
