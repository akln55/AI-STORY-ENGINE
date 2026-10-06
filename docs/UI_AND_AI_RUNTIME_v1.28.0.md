
# CURRENT LOCAL AI STATUS — 2026-10-05

This document defines the intended runtime boundary. The implementation remains partial:

- GGUF import/selection UI: **implemented**
- app-private model copy: **implemented**
- development `llama-cpp-python` adapter: **implemented**
- development localhost `llama-server` adapter: **implemented**
- in-app model catalog/downloader: **not implemented**
- Android-native llama.cpp integration: **not implemented**
- native process lifecycle manager: **not implemented**
- physical-device local inference: **not verified**


# v1.28.0 — Android UI & AI Runtime Direction

## UI contract

The Android application now uses a single dark visual system:

- deep neutral background similar to ChatGPT dark mode;
- rounded cards and controls;
- muted secondary text;
- green accent for primary actions;
- compact bottom navigation;
- lightweight screen transitions;
- no external image assets required for the core UI.

## AI provider contract

The UI exposes:

1. Local GGUF model import/selection.
2. Gemini through the existing Gemini adapter.
3. OpenAI-compatible API endpoints through the new generic adapter.

The UI does not embed a model into the APK and does not require Termux.

## Native local runtime boundary

The Python engine already contains the `AIAdapter` boundary and a `LlamaCppAdapter` for environments where `llama-cpp-python` exists. Android production local inference must not depend on `llama-cpp-python` being installable at runtime.

Current upstream `llama.cpp` Android guidance provides a native Android binding and app-private GGUF loading through a `ContentResolver`/`Uri` -> app-private file -> native inference path. The next native milestone should integrate that binding behind the existing `AIAdapter` boundary instead of starting a local server or requiring Termux.

This release therefore intentionally does not claim that local GGUF inference is already operational inside the Android APK.


## v1.1 product decisions (2026-10-05)

- Hybrid AI is mandatory: Local GGUF + Google Gemini API + OpenAI API.
- Local play must work offline once a compatible model is installed.
- External web/research access is a separate explicit capability and is OFF by default.
- Preferred public local-model discovery/download direction: Hugging Face, with app-side compatibility/licensing/metadata checks.
- Primary validation device: Redmi Note 12 Pro 4G.
- Initial local model policy: approximately 1.5B–3B instruct models, efficient 4-bit/Q4 variants, ~2 GB preferred file size ceiling and ~3 GB provisional maximum pending benchmarking.
- UI: dark/gray ChatGPT-like, soft rounded surfaces; player text right-aligned; NPC/other speakers left-aligned; distinct bubbles/cards for each speaker.
- Progressive AI text is a presentation animation only and is independent of save/state semantics.
