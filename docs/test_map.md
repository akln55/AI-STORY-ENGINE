# Test Map

Last verified: 2026-10-12
Purpose: connect critical behavior and invariants to the tests that actually assert them. A test file name alone is not evidence of coverage; entries below identify the main owner, current test anchors and the remaining acceptance gap.

## Summary

- Current CI test command: `.ci/test-venv/bin/python -m pytest -q tests` in `.github/workflows/test.yml`.
- Latest completed test run before this map: 487 passed in 10.28 seconds; [run #56](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38264902948).
- Current CI also runs `compileall -q .`, `tools/verify_android_readiness.py`, and `tools/mutation_smoke.py`.
- Coverage/branch-coverage reports are not currently generated.
- The three-mutation smoke only changes three conditions in `engine/core/validation.py`; it is not a whole-repository mutation score.
- Android build verification checks package metadata and source provenance. It does not install or launch the APK.
- A target-device Kivy startup exception has been observed despite a green test run/build. Device startup is therefore a critical unresolved acceptance gap.

## Behavior-to-test matrix

| ID | Critical behavior / invariant | Authoritative owner | Existing tests and actual signal | Gap / acceptance criteria |
|---|---|---|---|---|
| TEST-STATE | Only validated effects mutate authoritative game state | `engine/core/validation.py:120-430`, `engine/core/state.py:260-265` | `tests/test_validation.py`, `tests/test_invariants.py`; mutation smoke targets unreachable movement, atomic rejection and resurrection | Add property-based batches; assert rejected batches preserve a deep snapshot for many generated invalid sequences. |
| TEST-TURN | A player action advances or preserves turn/state according to intent and result | `engine/core/game.py:128-193,340-402` | `tests/test_game_session.py`, `tests/test_gameplay_integration.py`, `tests/test_events.py` | Exercise provider timeout, malformed output, retries and duplicate callbacks together; assert exactly one commit or no commit. |
| TEST-AI-SCHEMA | Structured response rejects invalid top-level/nested types, unknown keys and oversized content | `engine/ai/schema.py:102-208` | `tests/test_ai_schema.py`, `tests/test_ai_contract.py` | Expand generated nested types, extreme lengths, booleans-vs-integers and adversarial combinations with Hypothesis. |
| TEST-AI-SECURITY | AI cannot gain direct filesystem/process/state authority | `engine/ai/security.py`, `engine/core/validation.py` | `tests/test_ai_security.py`, `tests/test_ai_execution_policy.py` | Audit all adapter-to-state boundaries and ensure forbidden proposals never produce side effects. |
| TEST-PROVIDER | Provider response, HTTP errors and malformed envelope are normalized | `engine/ai/gemini_adapter.py:67-130`, `engine/ai/openai_compatible_adapter.py:27-119`, `engine/ai/llama_cpp_process_adapter.py:139-220` | `tests/test_gemini_adapter.py`, `tests/test_openai_compatible_adapter.py`, `tests/test_llama_cpp_process_adapter.py` | Ensure deterministic local HTTP fixtures cover timeout, 429/rate-limit, 5xx, invalid JSON, missing response fields and oversized bodies. Real-provider credential checks remain external. |
| TEST-RETRY | Retry/fallback is bounded and does not duplicate state commit | `engine/core/game.py:477-505`, `engine/ai/reliability.py:47-144` | `tests/test_ai_retry.py`, `tests/test_ai_reliability.py` | Add integrated failure matrix asserting turn, state, memory and event counters before/after exhausted retries and fallback. |
| TEST-MEMORY | Memory is validated, indexed, visible only to allowed viewers and retrievable deterministically | `engine/memory/system.py:43-406`, `engine/memory/retrieval.py:18-118` | `tests/test_memory.py`, `tests/test_context_memory.py`, `tests/test_memory_ai.py`, `tests/test_knowledge.py` | Add long campaign cases mixing secret visibility, duplicate memories, archive/restore and NPC knowledge. |
| TEST-LONG | Long sessions preserve invariants, bounded context and save/load integrity | `engine/core/game.py`, `engine/ai/context.py:73-292`, persistence owners | `tests/test_long_session.py` includes 200/1000 turns and 5000 memory records | Extend deterministic seeds and include provider errors, save interruption and visibility invariants over the campaign. |
| TEST-SAVE | Save/load round-trip preserves game, memory, relationships and turn | `engine/persistence/db.py:105-511`, `engine/persistence/saves.py:57-196` | `tests/test_persistence.py`, `tests/test_persistence_memory.py`, `tests/test_persistence_relationships.py` | Add corrupted/incomplete save and backup-restore tests for failure between temp write, replace and metadata update. |
| TEST-SCENARIO | Scenario ZIP/path/manifest data is validated before installation | `engine/scenario/loader.py:72-160`, `engine/scenario/manager.py:61-198` | `tests/test_scenarios.py`, `tests/test_scenario_manager.py`, `tests/test_scenario_registry.py` | Add archive bomb/oversize-entry, traversal, duplicate path, malformed UTF-8/JSON and interrupted install cases. |
| TEST-MODEL | GGUF imports/downloads are size-bounded, validated and installed atomically | `engine/ai/model_manager.py:81-264,289-332` | `tests/test_model_manager.py` | Verify cancellation/partial download and cleanup under I/O errors; actual large-model memory pressure is device-dependent. |
| TEST-LOCAL-RUNTIME | Native server is configured loopback-only, starts/stops and reports health | `engine/ai/llama_native_runtime.py:38-229` | `tests/test_llama_native_runtime.py` | Tests currently use temporary/fake binary paths for several checks; run actual ARM64 server/model on target device and verify offline inference. |
| TEST-UI-KIVY | Real Kivy widgets can be imported/instantiated under pinned runtime | `rpg_android_app.py:40-131` | `tests/test_android_kivy_properties.py` uses AST inspection for `PillInput` padding | **Critical gap:** add real Kivy 2.3.1 import/widget/app-startup test; reproduce and prevent the observed `float` to `Property` startup failure. |
| TEST-ANDROID-PACKAGE | APK contains expected package/source/native architecture and provenance | `tools/verify_android_staging.py`, `tools/verify_android_apk.py`, workflow | `tests/test_android_apk_verifier.py`, `tests/test_android_staging_verifier.py`, `tests/test_android_ci_workflow.py` | Keep static gate, but don't confuse it with runtime proof. |
| TEST-ANDROID-START | APK installs and stays alive after launch without fatal startup exception | `tools/android_apk_smoke.py:19-126` | Script exists; no current workflow step runs it | **Critical gap:** execute on compatible ARM64 device/emulator, archive logcat and fail on process exit/fatal exception. |
| TEST-ANDROID-FULL | Actual gameplay, save/load, SAF import, lifecycle and offline local inference work on device | Android UI/controller/SAF/runtime layers | `docs/APP_READINESS_CHECKLIST.md` lists several unchecked device items | Manual/device acceptance gate until compatible emulator/device is available and evidence is recorded. |
| TEST-CI | CI runs expected suites and uses pinned, read-only workflows | `.github/workflows/test.yml:1-59`, `.github/workflows/android-build.yml:1-154` | `tests/test_android_ci_workflow.py`, workflow logs | Workflow test verifies text/config shape; add executable YAML/static workflow validation and align docs with checks actually run. |

## Suite index

| ID | Suite / owner files | Run command | What it establishes |
|---|---|---|---|
| SUITE-CORE | `tests/test_game_session.py`, `test_gameplay_integration.py`, `test_validation.py`, `test_invariants.py` | `python -m pytest -q tests/test_game_session.py tests/test_gameplay_integration.py tests/test_validation.py tests/test_invariants.py` | Deterministic state rules, validation and game-loop behavior. |
| SUITE-AI | `tests/test_ai_*.py`, provider tests | `python -m pytest -q tests/test_ai_*.py tests/test_gemini_adapter.py tests/test_openai_compatible_adapter.py tests/test_llama_cpp_process_adapter.py` | AI schema/security/retry and provider adapter contracts. |
| SUITE-MEMORY | `tests/test_memory*.py`, `tests/test_context_memory.py`, `tests/test_knowledge.py` | `python -m pytest -q tests/test_memory*.py tests/test_context_memory.py tests/test_knowledge.py` | Memory persistence, retrieval, context assembly and knowledge visibility. |
| SUITE-PERSIST | `tests/test_persistence*.py` | `python -m pytest -q tests/test_persistence*.py` | Save/load and relationship/memory serialization. |
| SUITE-SCENARIO | `tests/test_scenario*.py`, `tests/test_scenarios.py` | `python -m pytest -q tests/test_scenario*.py tests/test_scenarios.py` | Scenario loading, registry, install and retrieval. |
| SUITE-ANDROID-STATIC | `tests/test_android_*.py` | `python -m pytest -q tests/test_android_*.py` | Source/config/package-verifier contracts; not device startup. |
| SUITE-LONG | `tests/test_long_session.py` | `python -m pytest -q tests/test_long_session.py` | Long deterministic sessions, invariant checks and memory/save integrity. |
| SUITE-CI | `.github/workflows/test.yml` | GitHub Actions push/manual dispatch | Full pytest suite, compileall, readiness verifier, three-mutation smoke. |
| SUITE-APK | `.github/workflows/android-build.yml` | GitHub Actions manual dispatch | ARM64 native build, APK packaging, static provenance and metadata. |

## Fixtures, fakes and test harnesses

- FIX-SESSION: `tests/conftest.py` creates deterministic `demo_state` and `session` factories; wrapped with pytest fixtures when pytest is installed.
- FIX-FAKE-AI: `engine/ai/fake.py` supplies deterministic AI behavior for tests. It avoids paid/network-dependent model calls, but cannot prove real-provider service behavior.
- FIX-TEMP-PERSIST: tests use temporary directories for save/model/runner behavior; verify each test cleans them up and doesn't share persistent state.
- FIX-MUTATION: `tools/mutation_smoke.py` copies the repo to temporary directories and applies three deliberate validation mutations; current score is 3/3 detected for those selected mutations only.
- FIX-ADB: `tools/android_apk_smoke.py` shells out to ADB, installs and launches the APK, then examines process/logcat. It changes the connected device by installing/launching the app, so run only when device testing is explicitly intended.

## CI command index

1. `.ci/test-venv/bin/python -m pytest -q tests`
2. `.ci/test-venv/bin/python -m compileall -q .`
3. `.ci/test-venv/bin/python tools/verify_android_readiness.py`
4. `.ci/test-venv/bin/python tools/mutation_smoke.py`
5. Android workflow additionally: `tools/build_llama_server_android.sh`, `tools/verify_android_staging.py`, `tools/verify_android_apk.py`, `aapt dump badging`, SHA-256/provenance generation and artifact upload.

Documented but not currently part of test CI:
- `python tools/run_tests.py` (dependency-free runner)
- `python tools/validate_scenario.py scenarios/demo-bootstrap` (scenario validation)
- `python -m pytest --cov=engine --cov-branch` (proposed; coverage plugin/config is not yet installed/pinned)

## Acceptance gaps, priority order

1. GAP-ANDROID-START — Reproduce the actual Kivy startup exception under Kivy 2.3.1 and add a real import/widget-startup regression test. The current AST guard alone is insufficient.
2. GAP-ANDROID-FULL — Run gameplay, save/load, background/foreground, SAF import and offline local inference on a compatible ARM64 device/emulator; archive logs and record each result.
3. GAP-RETRY-COMMIT — Prove exactly-once state/memory/event commit under provider timeout, malformed response, retry exhaustion and fallback.
4. GAP-COVERAGE — Establish line and branch coverage baselines, then prioritize uncovered critical modules rather than choosing an arbitrary whole-project threshold.
5. GAP-PROPERTY — Add Hypothesis to a pytest-only lane for schema payloads, effect batches, save/load round trips and scenario archive metadata.
6. GAP-MUTATION — Extend beyond the three hand-picked mutations using a scoped mutation-testing job; review surviving mutants and equivalent mutants.
7. GAP-SAF-ERRORS — Device-test cancellation, invalid extension, corrupt/oversized document and callback error presentation.
8. GAP-DOC-DRIFT — Align `docs/TESTING.md` and `docs/APP_READINESS_CHECKLIST.md` with current CI gates and current test counts.

## Flaky and external gates

- FLAKE-NETWORK: real remote provider tests may depend on network/credentials/rate limits. Keep primary CI deterministic with controlled local HTTP fixtures; separate live provider checks.
- FLAKE-DEVICE: emulator/device state, ADB permissions, model availability and hardware performance affect Android tests. Report these separately from source CI.
- FLAKE-RESOURCE: local model inference depends on RAM/storage/CPU and model quantization. A successful native server build does not establish that a particular GGUF model fits or responds on the phone.
- FLAKE-ASYNC-UI: Kivy Clock callbacks and SAF result callbacks need deterministic lifecycle tests plus real-device acceptance for OS integration.

## Related maps and specs

- [Project atlas](project_atlas_map.md)
- [Runtime flow map](runtime_flow_map.md)
- [Test-system audit](TEST_SYSTEM_AUDIT_2026-10-12.md)
- [Testing guide](TESTING.md)
- [Android APK smoke guide](ANDROID_APK_SMOKE.md)
- [App readiness checklist](APP_READINESS_CHECKLIST.md)
- [AI security specification](AI_SECURITY_SPEC.md)
