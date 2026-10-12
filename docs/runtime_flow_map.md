# Runtime Flow Map

Last verified: 2026-10-12
Repository: `akln55/AI-STORY-ENGINE`
Use this document to navigate operational flows and failure boundaries. Sequence order is based on source structure and current workflow definitions; Android device execution remains unverified except for the reported startup failure.

## Flow index

| ID | Flow | Trigger | Primary owners | Evidence / tests |
|---|---|---|---|---|
| FLOW-BOOT | Android process startup | Android launches package | `main.py:84-106`, `rpg_android_app.py` | `tests/test_android_app_readiness.py`; target-device startup failure reported |
| FLOW-TURN | Player action to authoritative state | Player submits text | `rpg_android_app.py:326+`, `engine/app/controller.py:188-197`, `engine/core/game.py:128-193` | `tests/test_game_session.py`, `tests/test_gameplay_integration.py` |
| FLOW-AI | AI proposal to validated state changes | Parser routes action to AI path | `engine/core/game.py:340-402,477-544`; `engine/ai/schema.py:107-208`; `engine/core/validation.py:388-430` | `tests/test_ai_contract.py`, `tests/test_ai_schema.py`, `tests/test_validation.py` |
| FLOW-SAVE | Session to save slot | UI/controller save or autosave | `engine/app/controller.py:198-213`, `engine/persistence/saves.py:57-158`, `engine/persistence/db.py:376-511` | `tests/test_persistence.py`, `tests/test_persistence_memory.py` |
| FLOW-LOAD | Save slot to active session | User selects slot / recovery | `engine/persistence/saves.py:90-158`, `engine/app/controller.py:203-213` | `tests/test_persistence.py`, `tests/test_persistence_relationships.py` |
| FLOW-SCENARIO-INSTALL | Scenario archive to installed pack | User imports a scenario | `rpg_android_file_picker.py:8-51`, `engine/scenario/manager.py:61-103,172-198` | `tests/test_scenario_manager.py`, `tests/test_scenarios.py`; device SAF test outstanding |
| FLOW-MODEL-IMPORT | User model file to app-private model storage | User picks GGUF | `rpg_android_file_picker.py:68-134`, `engine/ai/model_manager.py:153-194`, `engine/app/controller.py:115-123` | `tests/test_model_manager.py`; device SAF test outstanding |
| FLOW-LOCAL-INFER | Packaged native server to structured AI response | Local model selected and a turn requires inference | `engine/ai/llama_native_runtime.py:118-229`, `engine/ai/llama_cpp_process_adapter.py:139-220`, `engine/ai/schema.py` | `tests/test_llama_native_runtime.py`, `tests/test_llama_cpp_process_adapter.py`; offline device inference outstanding |
| FLOW-REMOTE-INFER | UI-configured remote provider to response | Gemini/OpenAI-compatible provider selected | `engine/ai/gemini_adapter.py:67-130`, `engine/ai/openai_compatible_adapter.py:27-119`, `engine/ai/reliability.py` | provider adapter and retry tests; real credentials/rate limits are external gates |
| FLOW-CI-TEST | Push/manual test workflow | Push to main or dispatch | `.github/workflows/test.yml:1-59` | Last run: [#56](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38264902948) success |
| FLOW-CI-APK | Manual Android build and artifact | Workflow dispatch | `.github/workflows/android-build.yml:1-154` | Latest prior green build: [#9](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38258932871); build does not install/launch on a device |

## FLOW-BOOT — Android startup

| Step | Owner | Behavior / boundary |
|---|---|---|
| STEP-BOOT-1 | Android package | Android starts `org.rpgengine` and Kivy's Python activity. |
| STEP-BOOT-2 | `main.py:84-106` | Imports and starts `RPGEngineApp`; startup failures are written to a log and a fallback error path is attempted. |
| STEP-BOOT-3 | `rpg_android_app.py` | Defines Kivy widgets/screens and app lifecycle. Class definitions can fail before `app.run()`, so a source-text check is insufficient. |
| STEP-BOOT-4 | Device/ADB smoke | `tools/android_apk_smoke.py:29-126` installs, launches, waits, inspects process/logcat and fails on fatal startup errors. It must run on a compatible device/emulator. |

**Known failure:** the user's target phone reported `TypeError: Cannot convert float to kivy.properties.Property`. A previous APK build succeeded, but this does not clear FLOW-BOOT. The next code phase should first create a reproducible test using the pinned Kivy 2.3.1 runtime and instantiate/import the actual UI classes, then fix the demonstrated inherited-property conflict and add regression coverage.

## FLOW-TURN / FLOW-AI — one gameplay turn

1. Player text enters through `GameScreen.submit` in `rpg_android_app.py`; UI work and animation are presentation concerns.
2. `AppController.submit` delegates to `GameSession.handle_input` (`engine/app/controller.py:188-197`, `engine/core/game.py:128-193`).
3. The engine parses an intent and routes deterministic/meta/dialogue/AI paths. AI transaction logic and retry feedback live in `engine/core/game.py:340-544`.
4. Context is assembled from authoritative state, scenario knowledge, recent turns and retrieved memories (`engine/ai/context.py:73-292`).
5. The selected adapter returns a response. `engine/ai/schema.py:107-208` parses and validates the structure.
6. Proposed effects are converted and validated against live state (`engine/core/validation.py:120-430`). The validator is the mutation gate; the AI must not mutate state directly.
7. Only accepted effects are applied. Atomic rejection/rollback and failed-turn recovery live in `engine/core/validation.py:405-430` and `engine/core/game.py:194-272`.
8. Events, memory updates, turn logging and memory maintenance run in the game-session path (`engine/core/game.py:403-476,568-574`).
9. UI renders the result and autosave behavior is invoked through the app/controller path. Verify commit-once behavior under provider timeout/malformed response before declaring retry semantics safe.

### FLOW-AI failure and recovery matrix

| Failure | Current owner/path | Required observable guarantee | Test anchor / remaining gap |
|---|---|---|---|
| Invalid JSON/schema | `engine/ai/schema.py`, `GameSession._generate_with_retry` | Invalid proposal is rejected; no unvalidated effects mutate state. | `tests/test_ai_schema.py`, `tests/test_ai_retry.py`; broaden adversarial nested/type cases. |
| Provider timeout/unreachable | Adapter + `engine/ai/reliability.py` | Clear provider failure, bounded wait, no duplicate state commit. | `tests/test_gemini_adapter.py`, `tests/test_llama_cpp_process_adapter.py`, `tests/test_ai_reliability.py`; real service rate limits remain external. |
| Effect validation rejection | `engine/core/validation.py:388-430` | Rejected atomic batch does not partially mutate authoritative state. | `tests/test_validation.py`; existing mutation smoke checks one rejection mutation. |
| AI response flood / oversized content | `engine/ai/schema.py:107-208` | Bounded output is rejected before expensive state processing. | `tests/test_ai_schema.py`; property-based coverage not yet added. |
| Retry exhaustion | `engine/core/game.py:477-505` | Error/recovery path is explicit; turn and state do not advance twice. | `tests/test_ai_retry.py`, `tests/test_game_session.py`; confirm all adapters' failure shapes. |

## FLOW-SAVE / FLOW-LOAD — persistence

1. Controller delegates to `save_session` / `load_session` (`engine/app/controller.py:198-213`).
2. Slot and backup path management occurs in `engine/persistence/saves.py:24-196`.
3. State and memory are serialized/deserialized in `engine/persistence/db.py:105-375`.
4. Save writing and metadata/reading logic live in `engine/persistence/db.py:376-511`.
5. Tests cover state, memory and relationships across round-trips. Android app-private path behavior and lifecycle-triggered autosave still require device acceptance testing.

## FLOW-SCENARIO-INSTALL / FLOW-MODEL-IMPORT

- SAF opens Android's document picker; callbacks are asynchronous (`rpg_android_file_picker.py:8-51,96-134`).
- Selected URI is copied into app-private cache through `_copy_uri_to_cache` (`rpg_android_file_picker.py:68-95`); model import uses a size bound and scenario path should be checked for equivalent bounded behavior in its implementation phase.
- Scenario archives are parsed and checked in `engine/scenario/loader.py:72-128,137-160`, then installed by `ScenarioManager.install` (`engine/scenario/manager.py:61-103,172-198`).
- GGUF file validation and atomic installation belong to `engine/ai/model_manager.py:153-264`.
- SAF cancellation, corrupt file, unsupported extension, oversize input and callback exception behavior need real Android tests; source-only checks do not establish those outcomes.

## FLOW-LOCAL-INFER / FLOW-REMOTE-INFER

| Step | Local | Remote |
|---|---|---|
| Configuration | `AppController.set_local_model` and native runtime configuration | `AppController.set_gemini` / `set_openai_compatible` |
| Start/call | `NativeLlamaServer.start`, loopback health check, process adapter HTTP request | Provider adapter performs bounded HTTP request |
| Parse | Shared structured schema parser | Shared structured schema parser |
| Cleanup/recovery | Controller shutdown stops local runtime | Adapter/reliability layer reports errors; no local process to stop |
| External gate | Test on target ARM64 phone with network disabled | Test real credential/rate-limit/timeout cases in a controlled environment |

## FLOW-CI-TEST

1. Checkout source with credentials disabled.
2. Install isolated Python runtime and pinned pytest.
3. Run `python -m pytest -q tests`.
4. Compile Python source.
5. Run `tools/verify_android_readiness.py`.
6. Run `tools/mutation_smoke.py`, which currently applies three known mutations in `engine/core/validation.py`.
7. Workflow does **not** run the dependency-free runner, scenario validation, coverage reporting, property-based tests, or full mutation testing.

## FLOW-CI-APK

1. Checkout source; install host dependencies.
2. Prepare Android SDK/API 36 and pinned NDK 29.
3. Create isolated environment with Buildozer 1.6.0, Cython 0.29.33 and pytest 8.4.2.
4. Run source tests.
5. Build pinned llama.cpp v0.6.0 for ARM64 and check ELF architecture/hash.
6. Build APK using `buildozer.spec`, verify staged source provenance and APK package metadata.
7. Record SHA-256/provenance and upload APK/artifacts.
8. No ADB install/launch or gameplay/save/load/offline-inference step runs on the hosted build job.

## Idempotency, concurrency and cleanup notes

- Game turn processing has a checkpoint/rollback path; provider retries and effect application should be tested together to prove exactly-once state mutation.
- Save slots use explicit paths and backup helpers. Continue testing interruption/restore boundaries, not only normal round-trips.
- Native runtime owns a child process and local listening endpoint. Verify shutdown on app pause/exit and startup failure.
- SAF result handlers are callback-based; ensure errors are routed to visible UI rather than escaping the callback.
- CI test workflow cancels in-progress runs for the same ref; Android build workflow does not cancel in-progress builds.
- The native server is intended to bind to loopback; do not expose the local inference API to the LAN.

## Observability anchors

- Startup failure: `main.py` startup log helpers (lines 10-83).
- Build evidence: `.ci/native-elf.txt`, `.ci/native-sha256.txt`, `.ci/apk-badging.txt`, `.ci/apk-sha256.txt`, `.ci/android-build-provenance.txt` (workflow-generated artifacts).
- Device startup log: `tools/android_apk_smoke.py` defaults to `.ci/android-startup-logcat.txt`.
- Game turn logging: `GameSession._log_turn` in `engine/core/game.py:568-574`.

## Open questions

1. Which exact Kivy property declaration causes the startup exception under Kivy 2.3.1 on Android? Reproduce before changing it.
2. Is every async SAF callback failure caught and presented to the user?
3. Are app pause/stop events guaranteed to stop the native process and flush save state without racing an in-flight turn?
4. Do all provider timeout/retry paths leave turn number, memory and state unchanged until one valid response commits?
5. What coverage/branch-coverage baseline does the current suite achieve on core, persistence, scenario and provider code?
