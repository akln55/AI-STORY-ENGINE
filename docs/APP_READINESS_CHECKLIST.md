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
