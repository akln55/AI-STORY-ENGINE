# RPG Engine — Durable Memory

## Project identity

- Android-first deterministic text RPG engine with hybrid AI.
- Product release: `v1.1.4`.
- Historical engineering baseline: `v1.28.3`.
- Repository: `akln55/AI-STORY-ENGINE`.
- Canonical current state: `AI_START_HERE.md`; chronology: `docs/PROJECT_HISTORY.md`.

## Architecture rules

- Deterministic engine owns truth.
- AI is an untrusted proposer/narrator behind adapter boundaries.
- AI proposals must pass schema/security/gameplay validation before mutation.
- AI never gets direct GameState/save/database/scenario-file authority.
- UI provider paths: Local GGUF, Gemini, OpenAI, OpenAI-compatible endpoint.
- Offline play after compatible local model installation is a product goal; physical-device inference still needs proof.
- External web/research capability is separate and off by default.

## Android contract

- Kivy 2.3.1; Buildozer 1.6.0.
- python-for-android v2026.05.09 / `58d21141f17c889bf8585f5665921d72028f8831`.
- API 36 / minimum API 26 / `arm64-v8a`.
- NDK 29.0.14206865.
- llama.cpp v0.6.0 / `d81235049384534c167caea52b85a694f6103d14`.
- Entrypoint: `main.py -> rpg_android_app.py`; SAF helper: `rpg_android_file_picker.py`.
- Physical target: Redmi Note 12 Pro 4G.
- Never restore `android.main` or `android.file_picker`.

## Current UI/AI notes

- Hugging Face search and connectivity diagnostics are separate actions.
- Connectivity test is not a model download.
- API settings support provider-aware endpoint/model defaults and custom OpenAI-compatible endpoints.
- Chat has distinct player/narration/error role markers; operational failures must not masquerade as story text or expose raw exception strings.
- Progressive text reveal is presentation-only.

## Latest source verification

- 524 tests passed in 10.09 seconds.
- `python -m compileall -q .`: PASS.
- Android readiness: PASS (v1.1.4, target API 36, SAF enabled).
- Mutation smoke: 3/3 detected.

These are source-level checks, not physical-device release proof. The Android build workflow #122 is in progress; wait for APK metadata/provenance verification and artifact upload before reporting success.

## Release gates

- Test-only CI before packaging.
- Native llama.cpp cross-build and APK packaging must both pass.
- Inspect final APK metadata, provenance, and SHA-256.
- Run ARM64 device startup/crash smoke.
- Run gameplay, save/load/autosave, SAF scenario import, and local-GGUF inference tests.
- Do not label Android release verified before device evidence exists.

## Workflow preferences

- Work one stage at a time; group related changes into atomic commits.
- Fix the first failing layer before changing architecture.
- Preserve solved Android/security fixes.
- Never commit API keys, tokens, passwords, signing material, model files, local saves, APKs, build caches, or secret `.env` files.
- Do not confuse product version v1.1.4 with historical engineering baseline v1.28.3.
