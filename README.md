# RPG Engine

## Current state

- Product release: **v1.1.4**
- Canonical current handoff: `AI_START_HERE.md`
- Canonical project history: `docs/PROJECT_HISTORY.md`
- Verification: **477 passed, 0 failed**; compileall PASS; Android readiness PASS; mutation smoke 3/3; demo scenario validation PASS
- Android physical-device release proof: **not yet complete**

Read `AI_START_HERE.md` first. For previous milestones, failures, decisions, and lessons learned, read `docs/PROJECT_HISTORY.md`.

## Product target

The final application is an Android APK. Users should be able to install it directly, manage scenarios, start campaigns, play, save/load, and choose cloud or local AI without installing Termux or Python.

Local AI is intended to work like an app-managed local model system: the user downloads a supported GGUF model from inside the app, the model is stored in app-private storage, and an Android-native llama.cpp runtime performs inference on-device. Gemini remains an optional cloud provider. Google Colab is a proposed build environment for APK generation, not an end-user runtime.

## Architecture

The deterministic engine owns authoritative state. AI receives bounded context and returns structured proposals. The engine validates and atomically applies permitted effects. Scenario canon is read-only, and memory/knowledge visibility is enforced.

```text
Player action
  -> parser
  -> authoritative engine state/rules
  -> memory/scenario/NPC retrieval
  -> bounded AI context
  -> structured AI proposal
  -> validation/security gate
  -> atomic state update
  -> memory/event/quest updates
  -> save
```

## Current verification

The current v1.1.4 source/package baseline has **477 passing tests**, compileall PASS, Android readiness PASS, mutation smoke 3/3, and demo scenario validation PASS. Physical Android release behavior remains unproven until a real APK is built, installed, and exercised on hardware.

## Current development state

The deterministic engine, persistence/lifecycle hardening, local-AI/provider hardening, Android startup/staging safeguards, and current UI presentation work are implemented and regression-tested. The next gate is external proof: real GitHub Actions execution, APK provenance inspection, physical-device QA, and local-GGUF inference/benchmarking.

## Documentation

| File | Purpose |
|---|---|
| `AI_START_HERE.md` | Single canonical current handoff |
| `docs/PROJECT_HISTORY.md` | Single chronological history, decisions, failures, and lessons |
| `docs/CONSTITUTION.md` | Binding project rules |
| `docs/ARCHITECTURE.md` | Architecture and gameplay loop |
| `docs/DATA_MODELS.md` | Data contracts |
| `docs/SCENARIO_DATA_FORMAT.md` | Scenario pack specification |
| `docs/AI_SECURITY_SPEC.md` | AI security boundary |
| `docs/AI_EXECUTION_POLICY.md` | AI transaction policy |
| `docs/TESTING.md` | Test architecture and release checks |

Technical specifications remain separate because they define contracts. Current-state and historical duplication has been removed.

## v1.26.0 — Full Source Hardening

- Dependency-free runner rejects async tests and accidental return values instead of silently accepting them.
- Runner regression suite covers pass/fail/import/fixture/async/return-value behavior.
- `tools/mutation_smoke.py` detects three deliberate critical validation regressions.
- Release verification now requires pytest, stdlib runner, mutation smoke, compileall, scenario validation, and clean-package revalidation.


## v1.24.0 — Gameplay Core: hostile NPC retaliation

The first Gate B combat slice is now engine-authoritative: hostile NPCs can retaliate after a player attack or technique when they survive the hit. Retaliation is emitted as part of the same atomic effect batch, so it cannot partially apply. The threshold is deterministic (`disposition <= -25`) and damage is `max(1, npc.attack_power - player.defense)`. Non-hostile NPCs do not retaliate.


## v1.24.0 — Memory Lifecycle + Indexed Retrieval

- Memory retrieval now uses derived store/entity/location/event/tag/trigram indexes before applying the existing deterministic scorer.
- Existing substring ranking semantics remain intact; short-term queries use a conservative fallback.
- Recent memory has a lossless archive tier. Archived records remain persisted and can be explicitly retrieved but are excluded from normal context retrieval.
- GameSession performs deterministic memory maintenance every 25 turns once memory reaches 500 records, archiving recent records older than the configured 100-turn retention window.
- Save format remains v5 because the new memory tier field is additive and backward-compatible.
- Added indexed retrieval, archive round-trip, automatic maintenance, and 5,000-record long-session regression coverage.
- Engine Completion remains open for the final invariant/persistence/scenario/AI verification gates.
