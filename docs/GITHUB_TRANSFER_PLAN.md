# GitHub Transfer Plan — 2026-10-06

## Repository

- Public repository: `akln55/AI-STORY-ENGINE`
- Purpose: source/build repository only; no runtime secrets or user/model data.

## Completed

- GitHub connection/write access was repaired after an initial connector 403.
- `.gitignore` created.
- `SECURITY.md` created.
- A clean v1.28.3 source ZIP was uploaded to repository root.

## Current transfer status — security gate complete

The one-time importer workflow has been hardened and action-pinned. The Android build workflow is also action-pinned and read-only. The repository should receive the corrected v1.1 source bundle before the importer is run, so the imported source and CI workflow are from the same audited state.

### Current source bundle requirements

Upload filename to repository root: `RPG_ENGINE_v1.1_GITHUB_SOURCE_CORRECTED.zip`


The corrected bundle must contain:

- the v1.1 application source and tests;
- the corrected native llama.cpp build script;
- `buildozer.spec` with stable p4a commit `58d21141f17c889bf8585f5665921d72028f8831`;
- the corrected Android workflow;
- updated AI handoff/memory/decision/release documentation;
- no `.gguf`, `.apk`, `.aab`, private key, credential, `.env` secret, or build-cache content.

### After source import

Run the one-time source importer first. Do **not** start the Android build until the importer finishes successfully and the root ZIP has been removed. Then run the manual `Test suite` workflow. Only when that workflow passes should you run the manual `Android build` workflow.

The first Android CI run is an evidence-gathering gate, not a release claim. Record the complete result and artifact provenance. If it fails, classify the failure by layer before changing application code:

1. host/SDK/NDK setup;
2. llama.cpp cross-build;
3. python-for-android/Buildozer packaging;
4. APK metadata/output discovery;
5. application runtime;
6. physical-device inference.

### Stage 3 — device QA

Install the produced APK on the target Android device and verify launch, deterministic gameplay, save/load, SAF scenario import, provider configuration, and local GGUF inference.

## Secret policy

Never commit:

- API keys/tokens/passwords;
- private signing keys/certificates;
- service-account JSON;
- secret `.env` files;
- local saves/imports;
- GGUF/model files;
- APK/AAB files;
- build caches/virtualenvs.

Use GitHub Actions Secrets for CI-only credentials. Assume every committed file is public.


## v1.1 product delivery contract

- Active product release target: **v1.1**.
- Required AI modes: Local GGUF + Google Gemini API + OpenAI API.
- Local play must work offline after a compatible model is installed.
- Primary local target device: Redmi Note 12 Pro 4G.
- Preferred public model-discovery direction: Hugging Face, with compatibility/license/metadata filtering.
- External research/web access is a separate explicit capability, OFF by default.
- First delivery milestone: working APK + playable RPG loop + save/load + provider configuration.

The source ZIP must remain secret-free: no API keys, model files, signing keys, user saves, APKs, or build caches.
