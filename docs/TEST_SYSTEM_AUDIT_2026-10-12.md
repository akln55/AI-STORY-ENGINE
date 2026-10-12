# Test-System Audit — 2026-10-12

## Status and scope

This is the Stage 1 evidence record for improving verification confidence. It documents the existing test path and the proposed replacement in layers. It does not assert that the Android app has passed a device runtime test, and it does not change application behavior.

Repository revision inspected: `042a2d6c9591a2ca2e5fea09700f58fd7b9e25b3`.

## Verified results so far

- Test Suite run #55: [GitHub Actions](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38258828269) reported **487 passed in 10.28s**.
- Android Build run #9: [GitHub Actions](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38258932871) completed successfully. Build and APK static/provenance checks passed and the artifact was uploaded.
- The target phone then displayed an application-startup failure: `TypeError: Cannot convert float to kivy.properties.Property`. This is a real counterexample to treating a green test suite or successful APK packaging as evidence that the app starts correctly.

## What the current CI actually verifies

In `.github/workflows/test.yml`, CI installs pinned pytest and runs:
1. `.ci/test-venv/bin/python -m pytest -q tests`
2. `compileall -q .`
3. `tools/verify_android_readiness.py`
4. `tools/mutation_smoke.py`

The current fast mutation smoke in `tools/mutation_smoke.py` deliberately applies exactly three source mutations, all within `engine/core/validation.py`, and verifies that three named regression tests fail. Its own documentation correctly says that this is not a full mutation-testing engine.

The Android workflow builds the ARM64 native runtime, packages the APK, checks staged-source hashes and APK metadata, and uploads the APK plus provenance. It does not invoke `tools/android_apk_smoke.py`; the current workflow therefore has no automated installed-app launch gate on an Android device or emulator.

## Evidence of false confidence / uncovered behavior

- `tests/test_android_app_readiness.py` checks source/config substrings for several Android claims. These checks are useful configuration guards, but they do not import the shipped UI classes or launch the app.
- `tests/test_android_ci_workflow.py` checks the literal content of the workflow, not whether the packaged app starts.
- `tests/test_android_kivy_properties.py` uses AST inspection to guard the earlier `PillInput.padding` regression. It checks that one class attribute and its constructor argument have a desired shape; it does not load Kivy or audit all inherited Kivy properties.
- The current `rpg_android_app.py` still declares `font_size = sp(14)` and `multiline = False` at class scope in `PillInput` (lines 104–105), and `font_size = sp(15)`, `halign = "left"`, `valign = "middle"`, and `text_size = (None, None)` at class scope in `BodyLabel` (lines 125–128). The float error strongly suggests another inherited-property override remains. This is a prioritized runtime defect lead, not yet a verified root-cause fix; it must be reproduced through an actual Kivy import/initialization test in the relevant phase.
- `docs/TESTING.md` describes additional release checks (the dependency-free runner, scenario validation, and fresh-package/release verification) that are not all part of the current `test.yml` workflow.

## Selected verification strategy

Use a layered gate. Test count is reported as volume only, never as a confidence score.

1. **Deterministic unit/integration tests:** Keep pytest as the main runner; test observable contracts, invariants, state transitions, persistence round-trips, and failure recovery. Exercise provider errors through controlled local HTTP fixtures rather than relying on real API credentials or internet.
2. **Coverage baseline:** Add a pinned `pytest-cov` / coverage.py path with branch coverage and machine-readable reports. First establish a measured baseline and identify uncovered critical code; do not impose an arbitrary repository-wide percentage before the baseline is understood. Coverage identifies unexecuted paths; it does not by itself prove correctness.
3. **Property-based testing:** Add Hypothesis tests for adversarial structured-AI payloads, validation/effect batches, and save/load round-trips. Keep these in the pytest lane unless the dependency-free runner is deliberately extended.
4. **Mutation testing:** Retain the current three-mutation smoke as a fast regression check. Add a separate, scoped mutation-testing lane with a maintained Python mutation tool for critical engine modules; report surviving mutants and score, investigate equivalent mutants, and avoid claiming that the current 3/3 smoke is a whole-project mutation score.
5. **Kivy runtime checks:** Run tests with the exact Kivy version used by the app that import the real UI module and instantiate key widgets / app startup. Static AST checks may remain as fast guards, but cannot be the sole gate for Kivy property declarations.
6. **Packaged Android runtime gate:** Install and launch the produced APK on a compatible ARM64 emulator/device, collect logcat and require the process to remain alive without a fatal startup error. Before release acceptance, test a full gameplay turn, save/load, and local-model inference with network access disabled. If no device is attached to CI, explicitly report this as an external/manual release gate rather than silently passing it.
7. **Quality/static analysis:** Add pinned lint/type checks after baseline review; keep their findings separate from behavioral tests.

## Workflow changes recommended (not implemented in this audit)

- Add coverage measurement and retain the reports as CI artifacts.
- Add property-based tests to a separate pytest-only lane.
- Expand mutation testing in a separate scheduled or manually triggered job so normal build feedback stays bounded.
- Add a Kivy import/widget-instantiation gate and connect the available Android smoke tool to an appropriate ARM64 runtime. Do not claim a device gate passes when no compatible device/emulator actually ran it.
- Align `.github/workflows/test.yml` with the release layers promised by `docs/TESTING.md`, or revise documentation to state which checks run in which workflow.
- Keep build toolchain pins and the working build cache/configuration stable while improving test gates; test-harness work must not silently change SDK/NDK/Buildozer/p4a versions.

## Revised work plan (8 phases)

1. **Test confidence audit and verification design** — this document; identify gaps and adopt layered acceptance gates.
2. **Repository map** — map folders, modules, dependencies, runtime paths, test owners and build/package flow.
3. **Kivy/Android startup blocker** — reproduce the current property error with a real Kivy runtime test, fix all proven class-property violations together, and add regression coverage.
4. **Core architecture and domain audit** — deterministic game state, invariants, effect validation, parser, rules and scenario loading.
5. **AI contracts and provider resilience** — strict schema/security boundaries, malformed/oversized replies, timeout/rate-limit/retry/fallback and exactly-once state-commit behavior.
6. **Memory, world continuity and persistence** — long campaign, NPC knowledge/secret visibility, save/load and deterministic retrieval.
7. **Cross-cutting hardening and polish** — SAF/model import, resource budgets, concurrency/lifecycle, logging/diagnostics, performance, maintainability and prioritised enhancements.
8. **Release gate** — full test and quality reports, clean pinned build, APK provenance, and explicit device/runtime acceptance (gameplay, save/load, offline local inference).

## Exit criteria for Stage 1

- Existing CI guarantees are distinguished from checks it does not run.
- The test strategy is selected and recorded.
- No green build/test run is treated as proof of app startup.
- The next code-changing phase starts with a reproducible Kivy startup test.
