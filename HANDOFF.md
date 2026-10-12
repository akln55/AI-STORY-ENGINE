# RPG Engine — Current Handoff

**Updated:** 2026-10-12  
**Product version:** v1.1.4  
**Historical engineering baseline:** v1.28.3  
**Repository:** `akln55/AI-STORY-ENGINE`

## Read this first

- `AI_START_HERE.md` is the canonical current state and next-gate document.
- `MEMORY.md` stores durable project decisions.
- `docs/PROJECT_HISTORY.md` is chronological history, not current-state authority.

When documents disagree, prefer current source code/tests/configuration and observed CI results. Do not revive stale status claims from older dated documents.

## Product and architecture

RPG Engine is a deterministic Android text RPG with hybrid AI. The deterministic engine owns authoritative state. AI is a bounded proposer/narrator; all state-changing effects pass validation before atomic application.

Required provider paths in the app:
- Local GGUF
- Google Gemini
- OpenAI
- OpenAI-compatible custom endpoint/model

Once a compatible local model is installed and local runtime works, offline play is a product goal. External web/research access is a separate capability and is off by default.

## Android target

- Kivy 2.3.1; Buildozer 1.6.0.
- python-for-android stable v2026.05.09 / `58d21141f17c889bf8585f5665921d72028f8831`.
- Target API 36; minimum API 26; ABI arm64-v8a.
- NDK 29.0.14206865.
- llama.cpp v0.6.0 / `d81235049384534c167caea52b85a694f6103d14`.
- Entrypoint: `main.py -> rpg_android_app.py`.
- SAF helper: `rpg_android_file_picker.py`.
- Physical target: Redmi Note 12 Pro 4G.

Never restore `android.main` or `android.file_picker`.

## Latest source verification

- 524 pytest tests passed.
- Python compileall passed.
- Android readiness passed: v1.1.4 / target API 36 / SAF enabled.
- Mutation smoke detected 3/3 critical mutations.

The Android build workflow #122 has passed source tests and native llama.cpp cross-build and is currently at APK packaging. APK verification/provenance and artifact upload must be confirmed from the final run result before calling the build successful.

## Recent implementation changes

- Added Hugging Face connectivity diagnostics separate from model search/download.
- Expanded API provider selection with OpenAI-compatible endpoint/model fields and provider-aware defaults.
- Added compact visual markers in AI settings and gameplay chat.
- Distinguished gameplay errors from story narration and stopped showing raw exception strings in the chat.
- Added regression coverage for provider choices, chat markers, and safe gameplay error presentation.

## Non-negotiables

- AI cannot directly mutate GameState, persistence, scenario canon, or arbitrary files.
- Never commit secrets, API keys, model binaries, APKs, build caches, signing material, private credentials, or local saves.
- An imported GGUF is not proof of local inference.
- A built APK is not proof of Android runtime success.
- Keep verified, implemented, and unproven status separate.

## Release sequence

Source tests -> native cross-build -> APK build -> static APK/provenance verification -> ARM64 device startup smoke -> gameplay/save-load/SAF smoke -> local-GGUF inference smoke.

## CI discipline

Do not treat pending/cancelled runs as evidence. On failure, inspect the first failed job/step/log and fix that root cause before changing architecture. Group related changes to avoid unnecessary concurrent workflow churn.
