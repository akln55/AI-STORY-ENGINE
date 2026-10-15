# Project Atlas Map

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


Last updated: 2026-10-13
Current focus: AI provider connectivity; see `docs/AI_NETWORKING_STATUS.md`
Repository: `akln55/AI-STORY-ENGINE`
Version: `1.1.4`
Purpose: navigation map for future audits and implementation. This is an index of source-of-truth owners, not proof that every runtime path works.

## Product summary

A local-first, text-based RPG engine with a Kivy Android UI. The deterministic engine owns world/game state, validates AI-proposed effects before applying them, stores session and memory state in SQLite-backed saves, loads scenario packs, and supports local llama.cpp plus remote provider adapters.

Primary user surface: Android app. Developer surfaces: Python engine/tests/tools and GitHub Actions. The Android package currently targets `arm64-v8a`, Android API 36 (minimum 26), and Kivy 2.3.1; see `buildozer.spec:1-27`.

## Repository conventions

- Treat source code and current workflow/config as authoritative over older dated status documents.
- `docs/ARCHITECTURE.md` is useful for design intent but is dated/versioned and may lag current implementation.
- Stable map IDs below are navigation references, not test assertions.
- Keep AI as an untrusted proposer. Game state mutation belongs to deterministic engine validation/application paths.
- Build success and source tests do not establish successful startup on an Android device. The current device-startup defect is tracked in the audit report.
- Most recent audited source revision before this map: `d70623612b6503f21a2286675dee99b76a73fc93`. This map commit itself follows that revision.

## Capability index

| ID | Capability | Primary owner | Main consumers / related tests |
|---|---|---|---|
| CAP-PLAY | Parse player input, run game turns, recover failed turns | `engine/core/game.py:54-128,194-255`; `engine/parser/intents.py` | `tests/test_game_session.py`, `tests/test_gameplay_integration.py`, `tests/test_long_session.py` |
| CAP-STATE | Authoritative character/world/NPC/item/quest state | `engine/core/state.py:12-265`; `engine/core/invariants.py` | `tests/test_invariants.py`, `tests/test_validation.py` |
| CAP-RULES | Deterministic rules and atomic effect validation | `engine/core/validation.py:120-430`; `engine/rules/` | `tests/test_rules.py`, `tests/test_validation.py`, mutation smoke |
| CAP-AI | Structured AI response and proposal contract | `engine/ai/schema.py:65-208`; `engine/ai/security.py` | `tests/test_ai_schema.py`, `tests/test_ai_contract.py`, `tests/test_ai_security.py` |
| CAP-PROVIDER | Remote and local inference adapters, retry/health/fallback | `engine/ai/adapter_base.py:14-18`; `engine/ai/https_transport.py`; `engine/ai/connectivity.py`; `engine/ai/gemini_adapter.py:67-130`; `engine/ai/openai_compatible_adapter.py:27-119`; `engine/ai/llama_cpp_process_adapter.py:139-220`; `engine/ai/reliability.py` | `tests/test_gemini_adapter.py`, `tests/test_openai_compatible_adapter.py`, HTTPS transport tests, `tests/test_ai_reliability.py`, `tests/test_ai_retry.py`; physical provider call still unverified |
| CAP-LOCAL-MODEL | Import/download/validate GGUF and start local native server | `engine/ai/model_manager.py:66-332`; `engine/ai/llama_native_runtime.py:38-229`; `engine/app/controller.py:107-170` | `tests/test_model_manager.py`, `tests/test_llama_native_runtime.py`, `tests/test_app_controller.py` |
| CAP-MEMORY | Memory validation, visibility, retrieval, archival | `engine/memory/system.py:43-406`; `engine/memory/retrieval.py:18-118`; `engine/ai/context.py:73-292` | `tests/test_memory.py`, `tests/test_context_memory.py`, `tests/test_memory_ai.py`, `tests/test_knowledge.py` |
| CAP-SAVE | Serialize state/memory, atomic save/load, backups and slots | `engine/persistence/db.py:101-511`; `engine/persistence/saves.py:24-196` | `tests/test_persistence.py`, `tests/test_persistence_memory.py`, `tests/test_persistence_relationships.py` |
| CAP-SCENARIO | Validate, load, install and select scenario packs | `engine/scenario/loader.py:72-466`; `engine/scenario/manager.py:23-198`; `engine/scenario/retrieval.py` | `tests/test_scenarios.py`, `tests/test_scenario_manager.py`, `tests/test_scenario_registry.py`, `tests/test_scenario_retrieval.py` |
| CAP-NPC | NPC behavior, dialogue, encounter, knowledge and world simulation | `engine/npc/`; `engine/core/game.py:308-339,403-467` | `tests/test_npc_behavior.py`, `tests/test_npc_encounter.py`, `tests/test_npc_living_world.py`, `tests/test_npc_personality.py`, `tests/test_npc_simulation.py` |
| CAP-ANDROID-UI | Home, game, scenarios, AI/provider and model screens | `rpg_android_app.py:40-922` | `tests/test_android_kivy_properties.py`, `tests/test_android_app_readiness.py` |
| CAP-ANDROID-FILES | Android Storage Access Framework scenario/model import | `rpg_android_file_picker.py:8-134`; `rpg_android_app.py` import handlers | `tests/test_android_app_readiness.py`; actual device test remains required |

## Bounded contexts / owners

| ID | Context | Responsibility and boundary |
|---|---|---|
| CTX-UI | Kivy presentation | `rpg_android_app.py` renders screens, accepts user actions, calls the controller and schedules UI updates. It should not become an alternate authority for game rules. |
| CTX-APP | Application orchestration | `engine/app/controller.py:44-213` connects scenarios, session, provider configuration, local runtime lifecycle, save/load and shutdown. |
| CTX-GAME | Deterministic simulation | `engine/core/game.py`, `state.py`, `clock.py`, `events.py`, `invariants.py`, `validation.py` own turn processing and state mutation. |
| CTX-AI | Untrusted inference boundary | `engine/ai/` builds context, calls a selected adapter, parses structured output and tracks provider reliability. AI output is a proposal, not a direct write. |
| CTX-MEM | Memory and retrieval | `engine/memory/` owns record validation, visibility, indexes, retrieval and archival. `engine/ai/context.py` selects relevant context. |
| CTX-PERSIST | Persistence | `engine/persistence/` owns serialization, SQLite-backed save files, slots and backup recovery. |
| CTX-SCENARIO | World/scenario data | `engine/scenario/` owns scenario format, loading, registry/retrieval and installed-pack index; sample content lives under `scenarios/demo-bootstrap/`. |
| CTX-NPC | Social/world simulation | `engine/npc/` owns NPC behavior and interactions; `engine/quest/` owns quest state and objective logic. |
| CTX-BUILD | Android packaging | `buildozer.spec`, `.github/workflows/android-build.yml`, `tools/build_llama_server_android.sh`, `tools/verify_android_staging.py`, `tools/verify_android_apk.py` own package construction and static provenance verification. |

## Surface map

| ID | Surface | Entry / contract |
|---|---|---|
| SURF-ANDROID | Android application | `main.py:84-106` bootstraps `RPGEngineApp` from `rpg_android_app.py`; startup failures are logged and have a fallback path. Package ID: `org.rpgengine`. |
| SURF-PY-ENGINE | Python engine/library | `engine/` contains the deterministic game engine, AI adapters, memory, persistence, scenario and NPC modules. |
| SURF-CLI | Developer/CLI | `engine/cli.py`, `engine/demo.py`; test factories in `tests/conftest.py`. |
| SURF-ADB-SMOKE | Device startup smoke | `tools/android_apk_smoke.py:19-126`; requires an actual compatible ARM64 Android device/emulator with ADB access. Not currently a step in the Android build workflow. |
| SURF-CI-TEST | Source test workflow | `.github/workflows/test.yml:1-59`; push to main or manual dispatch. |
| SURF-CI-APK | Android build workflow | `.github/workflows/android-build.yml:1-154`; manual dispatch, builds native ARM64 llama-server and debug APK, checks package metadata/provenance, uploads artifacts. |

## Storage and state owners

| State/data | Authoritative owner | Notes |
|---|---|---|
| Live game state | `engine/core/state.py:260-265` and `GameSession.state` | Mutations should pass through `engine/core/validation.py:388-430`. |
| Game turn/clock | `engine/core/clock.py`, `engine/core/game.py` | Meta commands may not advance a turn; test observable clock behavior. |
| AI response contract | `engine/ai/schema.py:107-208` | Reject malformed/unknown/oversized fields before converting to effects. |
| Persistent save data | `engine/persistence/db.py:376-511` | SQLite-backed serialization; slot/backups managed in `saves.py`. |
| In-memory campaign memory | `engine/memory/system.py` | Visibility and archival are explicit record properties. |
| Installed scenarios | `engine/scenario/manager.py:23-198` | Default Android location is app-private storage; installation index is `installed.json`. |
| Local GGUF files | `engine/ai/model_manager.py:136-332` | Validates file format/size and supports atomic install; caller supplies app-private storage root. |
| Native runtime process | `engine/ai/llama_native_runtime.py:118-229` | Starts a loopback server and exposes health/stop controls. |
| UI transcript/animation | `rpg_android_app.py` | Presentation state; must not be treated as authoritative persisted state. |

## Runtime and integration index

| ID | Integration | Owner / notes |
|---|---|---|
| INT-LLAMA | Local llama.cpp server | Pinned source build in `tools/build_llama_server_android.sh`; runtime lifecycle in `engine/ai/llama_native_runtime.py`; process adapter in `engine/ai/llama_cpp_process_adapter.py`. |
| INT-GEMINI | Gemini API | `engine/ai/gemini_adapter.py`; external network, API key and timeout required. |
| INT-OPENAI-COMPAT | OpenAI-compatible API | `engine/ai/openai_compatible_adapter.py`; endpoint/model/key configured through controller/UI. |
| INT-ANDROID-SAF | Android document picker | `rpg_android_file_picker.py`; SAF document URI is copied into app-private cache before engine import. |
| INT-SQLITE | SQLite | `engine/persistence/db.py`; save/load durability and schema evolution require explicit tests. |
| INT-GITHUB-ACTIONS | CI/build | Workflows use read-only contents permissions and pinned action SHAs. Artifact upload occurs after APK verification. |

## Test and release navigation

- Test files: `tests/` (55 files at last tree inspection; 487 pytest tests in the last green run).
- Shared test factories: `tests/conftest.py`.
- Main suite: `python -m pytest -q tests`.
- Test-only CI: `.github/workflows/test.yml` runs pytest, `compileall`, Android readiness verification, and three-mutation smoke.
- APK build: `.github/workflows/android-build.yml` runs source tests, builds the pinned ARM64 native server, builds the APK, verifies staged-source hashes and APK metadata, then uploads APK and provenance.
- Fast mutation smoke: `tools/mutation_smoke.py`; currently three targeted mutations in core validation only.
- Dependency-free runner: `tools/run_tests.py`; it is documented in `docs/TESTING.md` but is not part of the current GitHub test workflow.
- Scenario validation: `tools/validate_scenario.py scenarios/demo-bootstrap`; documented release check, not in current test workflow.
- Device startup smoke: `tools/android_apk_smoke.py`; not run by hosted build CI and not evidence of gameplay/save/offline inference.
- Current high-priority unknown: Kivy class initialization/startup fails on the user's target phone with `TypeError: Cannot convert float to kivy.properties.Property`; source-only tests and APK packaging did not catch it.

## Detailed maps and canonical docs

- [Runtime flow map](runtime_flow_map.md)
- [Test map](test_map.md)
- [Test-system audit](TEST_SYSTEM_AUDIT_2026-10-12.md)
- [Architecture](ARCHITECTURE.md)
- [AI security and authority specification](AI_SECURITY_SPEC.md)
- [Testing and verification](TESTING.md)
- [Android build](ANDROID_BUILD.md)
- [Android APK smoke](ANDROID_APK_SMOKE.md)
- [App readiness checklist](APP_READINESS_CHECKLIST.md)
- [Risks](RISKS.md)

## Unknowns that affect the next audit

1. The exact Kivy inherited-property assignment causing the target-device startup exception is not yet reproduced by a real Kivy runtime test.
2. No verified device/emulator evidence currently proves full gameplay, save/load, SAF import, background/foreground lifecycle, or local inference with network disabled.
3. Coverage and branch-coverage baselines have not yet been measured.
4. Provider fallback and retry behavior has unit tests, but live-provider behavior with real service rate limits/credential failures remains an external integration gate.
5. Several docs contain older version/test counts; use current source/workflows and current run logs when deciding readiness.


## Current AI/network investigation (2026-10-13)

- Shared outbound HTTPS owner: `engine/ai/https_transport.py`; certificate and hostname validation remain enabled.
- Provider model-list probe: `engine/ai/connectivity.py`; this confirms a provider's model-list API path, not generation.
- Actual-generation diagnostic: `rpg_android_app.py` in `AIScreen.test_api_generation`; it calls the selected adapter's `generate` method and reports a sanitized error class.
- Android INTERNET permission exists in `buildozer.spec`, but permission presence is not proof of working mobile-data access.
- Last green source baseline: [run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305), 538 passed. The subsequent panel-height assertion was updated; latest CI must be checked.
- Physical device/carrier/provider behavior is an explicit unknown, not a passed gate. Do not start an APK build unless the user asks.
