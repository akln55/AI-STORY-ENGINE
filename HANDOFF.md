# RPG Engine — Current Handoff

**Date:** 2026-10-07
**Product version:** v1.1.4
**Historical engineering baseline:** v1.28.3
**Repository:** `akln55/AI-STORY-ENGINE`

## Read this first

This file is the compact continuation handoff for a new chat/AI. `MEMORY.md` contains the durable decisions/preferences. `AI_START_HERE.md` points into the project documentation. `docs/PROJECT_HISTORY.md` is historical only.

When documents disagree, trust source code/tests first, then this handoff, then the other documentation. Never silently revive a historical status.

## Product

RPG Engine is a deterministic Android text-RPG engine. AI is a bounded proposer/narrator; deterministic engine state and validation remain authoritative.

Mandatory hybrid AI:
- Local GGUF
- Google Gemini API
- OpenAI API

Once a compatible local model is installed, gameplay must remain usable offline. External web/research access is a separate capability and is off by default.

## Android target

- Kivy `2.3.1`
- Buildozer `1.6.0`
- python-for-android stable `v2026.05.09`, commit `58d21141f17c889bf8585f5665921d72028f8831`
- Android target API `36`
- minimum API `26`
- ABI `arm64-v8a`
- NDK `29.0.14206865`
- native llama.cpp `v0.6.0`, commit `d81235049384534c167caea52b85a694f6103d14`
- primary physical target: Redmi Note 12 Pro 4G

Android entrypoint is `main.py -> rpg_android_app.py`. SAF helper is `rpg_android_file_picker.py`.

**Never reintroduce:** `android.main` or `android.file_picker`.

## Verified source/package baseline

- `481 passed, 0 failed`
- Python `compileall`: PASS
- Android readiness verifier: PASS
- mutation smoke: `3/3`
- demo scenario validation: PASS (`3 locations / 2 NPCs / 3 items / 2 quests / 1 lore`)
- clean release verification: PASS

This does **not** mean Android release verification is complete.

## Latest CI audit

GitHub Test Suite runs #30 and #32 failed in the test stage; #31 was cancelled by concurrency. The source-stage failure was a test-local `UnboundLocalError` plus stale assertions that had already drifted from the current workflow.

Android run #4 produced a valid APK but failed because the verifier searched its own source for the forbidden import strings. Android run #5 produced an APK but used an older package-domain state, yielding `org.rpgengine.rpgengine`; current `buildozer.spec` is corrected to `package.domain = org`, so the expected package is `org.rpgengine`.

The current verifier checks the final APK rather than Buildozer's internal staging tree. Physical Android installation and local-GGUF inference remain separate release gates.

## Non-negotiables

- AI cannot directly mutate authoritative GameState, persistence, scenario canon, or files.
- No secrets in Git.
- No GGUF model binaries, APKs, build caches, signing material, or private credentials in Git.
- Do not treat GGUF import as proof of on-device inference.
- Do not treat an APK file existing as proof that the app works.
- Keep verified / implemented / unproven / planned states explicitly separated.


## CI execution discipline

When a Test Suite run is triggered, do not finish the task immediately. A pending run is not a result. Continue with one small, independent verification or documentation task while it runs, then query the workflow status.

- **success:** treat the run as evidence and continue to the next gate.
- **failure:** inspect the first failing job/step/log, fix that root cause, and start the next run.
- **cancelled:** do not treat it as evidence; determine whether workflow concurrency cancelled it.

Group related changes before triggering the suite. Avoid a stream of commits that only cancel one another.

## Android release gates

APK creation is only the packaging gate. The release sequence is: source tests -> APK static verification -> ARM64 device startup/crash smoke -> gameplay/save/load smoke -> local-GGUF inference smoke. `tools/verify_android_apk.py` covers the static APK gate and `tools/android_apk_smoke.py` covers the real-device startup gate.
