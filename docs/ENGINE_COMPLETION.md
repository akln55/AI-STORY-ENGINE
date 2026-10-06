# Engine Completion Contract

**Current milestone:** v1.26.0 — Full Source Hardening

This document defines the gate that must pass before gameplay expansion is treated as the primary development target.

## Required engine properties

- `GameState` remains the sole authoritative mutable world state.
- AI responses are proposals only; all state-changing effects pass through `apply_effects`.
- A loaded scenario is composed as one validated `ScenarioContext` containing pack, registry, retriever, and configuration.
- `GameSession.from_scenario_pack()` is the canonical new-session factory for scenario play.
- Partial scenario composition is rejected once retrieval/configuration is involved. Registry-only composition remains available for low-level engine tests.
- Save identity and scenario configuration are derived from the live session when possible; callers no longer need to duplicate scenario identity manually.
- Scenario save loading validates the saved configuration against the loaded pack before constructing a session.
- Defeat recovery remains deterministic and authoritative.
- Status effects, quest transactions, events, combat, NPC simulation, memory, and persistence remain behind engine-owned validation boundaries.
- 200-turn and 1000-turn deterministic sessions remain regression gates.

## v1.22.1 changes — historical

1. Added canonical `ScenarioContext` construction to `GameSession` and save loading.
2. Rejected partial scenario wiring that can produce a retriever/configuration without a complete composition.
3. Preserved registry-only composition for isolated encounter/NPC engine tests.
4. Made `save_session()` derive scenario identity/configuration from the session by default and reject mismatches.
5. Updated `AppController` to use the canonical save/load contract instead of duplicating scenario wiring.
6. Added regression coverage for partial composition and scenario-aware save/load.
7. Hardened the stdlib llama.cpp HTTP test server so expected client timeouts do not leave the dependency-free runner hanging or emit misleading BrokenPipe failures.

## v1.23.0 — Memory Lifecycle + Indexed Retrieval

1. Added derived indexes for store, visibility, entity, location, event, tags, and content trigrams.
2. Preserved the existing deterministic substring scorer and stable tie-breaking after candidate narrowing.
3. Added a lossless `active` / `archive` memory tier; archive metadata is optional on load for save compatibility.
4. Added deterministic recent-memory lifecycle maintenance: old `recent` records are archived rather than deleted.
5. Integrated maintenance into `GameSession` at deterministic intervals with a 500-record activation threshold and 100-turn retention window.
6. Added 5,000-record retrieval/compaction stress coverage and session-level maintenance regression coverage.

**Verification:** 398 pytest tests passed.

## Completion gate still open

This milestone closes the Memory + Long-Session category for the deterministic engine scope. It does **not** claim the entire engine is finished. The remaining engine gate must still cover the final invariant matrix, long-session reliability evidence, persistence/recovery matrix, scenario transition coverage, AI contract/error behavior, and a fresh-package verification pass. Android product work and large gameplay expansion remain downstream of that gate.


## Turn transaction integrity

A complete player turn is now an engine transaction boundary. Unexpected exceptions during NPC simulation, status ticking, deterministic rules, scenario events, AI generation, or integration code restore the exact pre-turn state, memory, recent-turn log, scenario configuration, and clock before the exception is re-raised. This prevents partial world advancement after infrastructure/provider failures.


## v1.24.0 — NPC Living World Core

The NPC category is now complete for the deterministic engine scope:

1. Added scenario-authored executable NPC goals with deterministic priority ordering.
2. Supported `move_to`, `follow_npc`, `meet_npc`, `patrol`, and `survive` goals while preserving passive legacy goals.
3. Goal execution emits ordinary validation-gated effects; goal progress/status is authoritative runtime state and persists through saves.
4. Added deterministic NPC relationship reactions for explicit interaction outcomes. Dialogue now produces bounded relationship evolution without giving AI direct authority.
5. Added trust-gated NPC-to-NPC knowledge propagation for co-located NPCs; secret-tagged knowledge never propagates.
6. Added scenario validation and GameState invariants for goal kinds, references, progress, and patrol data.
7. Added 1,000-turn deterministic NPC simulation regression coverage.

**Verification:** [current release verification] tests passed; dependency-free runner passed; compileall passed; demo scenario validation passed.

## v1.26.0 — Full Source Hardening

1. Hardened the dependency-free runner so unsupported async tests and accidental return-value tests cannot silently pass.
2. Added subprocess regression coverage for runner failure semantics.
3. Added `tools/mutation_smoke.py` with three critical validation mutations; all three are currently detected by the regression suite.
4. Added `docs/TESTING.md` as the canonical verification contract.

**Verification target:** pytest + dependency-free runner + mutation smoke + compileall + scenario validation + clean-package verification.

## Remaining engine gate

NPC living-world core is complete, but the full engine gate remains open for final invariant matrix coverage, scenario transition/recovery evidence, AI provider contract hardening, and clean-package verification.


## v1.26.0 — AI Production Hardening

1. Added strict provider-output bounds for narrative size, effect counts, memory payload size, tags, events, and available actions.
2. Sanitized and bounded Gemini provider diagnostics so raw upstream response bodies are never surfaced wholesale.
3. Added explicit llama.cpp runtime configuration bounds for context size, output size, temperature, and GPU-layer count.
4. Added regression coverage for all new provider/schema safety boundaries.
5. Added `AI_START_HERE.md` as the ordered master task tree for the remaining project.

**Verification:** [current release verification] tests passed. Full release verification remains required before packaging.

## v1.26.0 — AI Production Reliability

Completed the deterministic provider-reliability layer: a shared provider-error taxonomy, bounded health metrics, provider fallback that never intercepts malformed structured output, explicit adapter capability declarations, positive timeout validation, and AI long-session reliability coverage. Provider diagnostics remain bounded and do not expose raw secrets or unbounded provider payloads.

**Verification:** [current release verification] tests passed; dependency-free runner passed; mutation smoke detected 3/3 critical mutations; compileall passed. Fresh-package verification is part of the release checklist.
