> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.

> **Historical document notice (updated 2026-10-12):** This file retains its original v1.28.0 design context. The initial status statements below are historical and must not be used as current implementation evidence. For current status, read `AI_START_HERE.md` and `docs/PROJECT_HISTORY.md`.

## Current implementation snapshot — 2026-10-12

- Local GGUF import and app-private storage lifecycle: implemented in source.
- Android-native `llama-server` lifecycle boundary and pinned CI cross-build script: implemented; successful packaging and physical-device inference must be verified separately.
- Hugging Face catalog search and a separate reachability diagnostic: implemented. The connectivity test does not download model files.
- AI provider UI: Local GGUF, Gemini, OpenAI, and OpenAI-compatible custom endpoint/model.
- API connection test/model discovery: implemented in the settings flow.
- Gameplay chat: player/narration/error role markers, busy-state feedback, progressive presentation, and safe distinct error presentation.
- Latest source verification: 524 tests passed; compileall, Android readiness, and mutation smoke passed.
- Current Android build #122: source tests and native cross-build passed; APK packaging and artifact verification were still in progress at the time this snapshot was written.
- Physical Android installation and real local-GGUF inference: not yet verified.

---


# ORIGINAL STATUS SNAPSHOT — 2026-10-05 (HISTORICAL)

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

