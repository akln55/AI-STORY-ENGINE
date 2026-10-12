# RPG Engine — AI START HERE

**Canonical current handoff:** this file  
**Canonical historical record:** `docs/PROJECT_HISTORY.md`  
**Product release:** `v1.1.4`  
**Last verified source CI for application code (commit `4f13ef3106d621bab616f87696d4b3436bc51c60`): [535 tests passed](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38306455458); compileall, Android readiness, and mutation smoke passed. The later changes so far are documentation-only.  
**Current Android build:** check the [Android build workflow](https://github.com/akln55/AI-STORY-ENGINE/actions/workflows/android-build.yml) for the newest run. Older build #122 is historical and does not validate the recent model-download/UI fixes; APK metadata/provenance verification and artifact upload must complete before claiming packaging success.

> This file describes current state only. Older checkpoint/version documents are historical evidence, not current-state authority.

## 1. Product identity

RPG Engine is a deterministic, local-first text RPG for Android, not a prose chatbot. The engine owns truth; AI proposes narration and structured effects only.

```text
Player action
  -> parser / deterministic rules
  -> authoritative GameState
  -> bounded memory, scenario, and NPC context
  -> AI proposal
  -> validation/security gate
  -> atomic state mutation
  -> event/quest/memory updates
  -> persistence
```

AI cannot directly write authoritative GameState, saves, databases, scenario canon, or arbitrary files.

## 2. Android target and entrypoint

- Standalone Android APK; no end-user Termux/Python requirement.
- Minimum API: **26**; target API: **36**.
- ABI: **arm64-v8a**.
- Kivy: **2.3.1**; Buildozer: **1.6.0**.
- python-for-android: **v2026.05.09**, commit `58d21141f17c889bf8585f5665921d72028f8831`.
- Android NDK: **29.0.14206865**.
- Native llama.cpp: **v0.6.0**, commit `d81235049384534c167caea52b85a694f6103d14`.
- Entrypoint: `main.py -> rpg_android_app.py`.
- SAF helper: `rpg_android_file_picker.py`.
- Physical validation target: Redmi Note 12 Pro 4G.

Never restore `android.main` or `android.file_picker`.

## 3. AI providers and local runtime

The UI exposes these provider paths:
- **Local GGUF** — import/select a model into app-private storage.
- **Gemini** — Google API provider.
- **OpenAI** — OpenAI API provider.
- **OpenAI-compatible** — custom compatible endpoint and model ID.

The Hugging Face catalog search is separate from connectivity diagnostics. The connection test probes reachability and does not download a model. API connectivity/model discovery and gameplay generation are separate operations.

### Implemented in source

- GGUF import through Android SAF and app-private model storage.
- GGUF integrity/structure validation and model-manager lifecycle.
- `AIAdapter` boundary and development adapters.
- Android-native `llama-server` lifecycle code and pinned CI cross-build script.
- Provider selection and endpoint/model configuration.
- API connectivity/model discovery controls.
- Hugging Face catalog search and connection diagnostics.
- Bounded/sanitized provider diagnostics.
- Chat role bubbles, progressive text presentation, busy-state handling, and separate user-facing gameplay error bubbles.

### Still unproven or incomplete

- A successful, fully verified APK artifact from the current Android build run.
- Installation/launch on physical ARM64 Android hardware.
- Real local GGUF inference and performance/thermal/memory measurements on the target phone.
- A complete in-app model-management experience beyond current catalog/search/import capabilities.

Initial local-model policy remains conservative: roughly **1.5B–3B instruct**, efficient 4-bit variants, around 2 GB preferred and around 3 GB provisional maximum until device benchmarks exist.

## 4. Current source verification

Recorded source-only evidence for the reviewed application code is [CI run 38306455458](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38306455458), at commit `4f13ef3106d621bab616f87696d4b3436bc51c60` (535 tests). For the current APK state, use the [Android build workflow run list](https://github.com/akln55/AI-STORY-ENGINE/actions/workflows/android-build.yml); older run #122 predates the latest review fixes.

- **524 tests passed** in 10.09 seconds.
- `python -m compileall -q .`: PASS.
- Android readiness: PASS (`version=1.1.4, target_api=36, SAF=enabled`).
- Mutation smoke: **3/3 detected**.

This does not prove that an APK was successfully packaged or that Android runtime behavior works.

## 5. Release gates

1. Source tests and static checks.
2. Native llama.cpp cross-build.
3. Build APK.
4. Verify final APK metadata, source/staging provenance, and SHA-256.
5. Upload APK and provenance artifacts.
6. Install/launch on ARM64 Android and retain startup logs.
7. Verify gameplay, save/load/autosave, SAF scenario import, provider configuration, and local-GGUF inference.

Only call the app Android-verified after the relevant device gates pass.

## 6. Current UI contract

- Dark neutral hierarchy, rounded surfaces/controls, muted secondary text.
- Primary actions have explicit contrast and visible pressed/disabled states.
- Player messages are right-aligned; narration/NPC messages are left-aligned.
- Chat role markers distinguish `SEN`, `ANLATI`, and `HATA`.
- Busy state prevents duplicate submissions.
- Progressive text reveal is presentation-only and must not control save/state semantics.
- Operational/provider failures must not be rendered as story narration or expose raw exception details to the player.

## 7. Non-negotiable rules

- AI is an untrusted proposer, never the authority over game state.
- No secrets, API keys, model binaries, APKs, build caches, signing material, local saves, or secret `.env` files in Git.
- Do not treat GGUF import as proof of on-device inference.
- Do not treat an APK existing as proof the app launches.
- Keep implemented, source-verified, artifact-verified, device-verified, and planned states separate.
- If CI fails, inspect the first failing layer/log before changing architecture.

## 8. Reading order

1. This file — current state and next gate.
2. `docs/PROJECT_HISTORY.md` — chronological history and lessons.
3. `docs/ARCHITECTURE.md` — architecture and gameplay loop.
4. `docs/CONSTITUTION.md` — binding rules.
5. `docs/TESTING.md` and `docs/ANDROID_BUILD.md` — verification/release gates.
6. The relevant subsystem specification before changing that subsystem.
