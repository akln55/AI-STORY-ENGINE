# App Readiness Checklist — current status

## Source/package contract

- [x] Android entrypoint is root `main.py` -> `rpg_android_app.RPGEngineApp`
- [x] Engine/app version synchronized at `1.1.4`
- [x] Kivy pinned to 2.3.1
- [x] Target API 36; minimum API 26; arm64-v8a
- [x] Legacy external-storage permission removed
- [x] Android scenario import uses SAF
- [x] App-private save storage
- [x] Pause/stop autosave and deferred autosave during in-flight turns
- [x] Android readiness verifier
- [x] Source CI: 524 tests passed
- [x] `compileall`
- [x] Mutation smoke: 3/3 detected
- [x] Provider-aware AI settings and Hugging Face connectivity diagnostics
- [x] Gameplay errors separated from story narration

## Current Android build run

- [x] Source tests in Android build workflow
- [x] Pinned llama.cpp native cross-build
- [ ] APK debug build
- [ ] Final APK metadata/staging provenance verification
- [ ] APK SHA-256 and provenance artifact upload

Current run: [Android build #122](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38297334671). Refresh these boxes only after the workflow reports its final result.

## Device verification (not yet proven)

- [ ] APK installs on a compatible ARM64 device/emulator
- [ ] First-launch/startup smoke test
- [ ] Gameplay turn completes normally
- [ ] Save/load and background/foreground autosave
- [ ] SAF scenario import and invalid-scenario error path
- [ ] API provider configuration/connectivity
- [ ] Local GGUF activation and real inference
- [ ] Long-session stability and performance/thermal/memory checks

Source tests do not establish that an APK installs or works on a physical device. Do not mark the release Android-verified before device evidence exists.


## 2026-10-14 — Current source/release status

This dated note supersedes stale build-run references above without deleting the historical record.

- [x] Source CI run 38517225272 succeeded on HEAD 59e30799162f94fa59201f75b0b9972577718032.
- [x] Snapshot checks: pytest 549 passed; compileall and Android readiness passed; mutation smoke 3/3; demo-bootstrap scenario valid.
- [ ] Repair/document tools/run_tests.py: 31 passed / 5 failed (pytest/monkeypatch fixture incompatibility).
- [ ] Validate a real ChatGPT-generated scenario archive through import, launch, AI context/retrieval and save/load.
- [ ] Finish scenario list/demo deletion behavior and test Android composer/provider/settings UI on a device.
- [ ] Build APK from current HEAD and verify metadata, provenance and artifact.
- [ ] Physical-device launch, gameplay, save/load and local GGUF inference remain unverified.

Detailed plan: docs/DEVELOPMENT_PLAN.md. This commit updates documentation only; no code fix or APK build was performed.
