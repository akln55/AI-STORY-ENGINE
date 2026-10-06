# RPG Engine — Technology Stack

Version 1.0 · Phase 0 · 2026-09-23

Constraints: developer works from **Android**; prefer **free, no-subscription**
tooling; must eventually package as an Android app; must stay simple.

## Decision summary

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | **Python 3.11** | Free, portable engine language; packaged into Android through python-for-android/Buildozer |
| Engine core | Plain Python stdlib-first | Constitution §2.6 — no unnecessary dependencies; core must run anywhere Python runs |
| Persistence | **SQLite** (stdlib `sqlite3`) | Transactional, file-based, portable, exportable as single files; ideal for save slots |
| AI client | **Abstract adapter** (`engine/ai/adapter_base.py`) with pluggable backends | Keeps engine independent of any provider; local-first |
| Local AI | **llama.cpp Android native runtime (CI-built ARM64 server boundary)** + `AIAdapter` | Free/offline option; model files are downloaded separately by the app; no Termux requirement |
| Remote AI (optional) | OpenAI-compatible HTTP adapter | Optional convenience; engine must never depend on it |
| Retrieval | SQLite FTS5 + embeddings later | FTS5 is stdlib-adjacent and free; semantic retrieval added in Phase 4 (local embedding model, no paid API) |
| UI (Phase 7) | **Kivy** | Mature, free, cross-platform, and packages to Android via Buildozer |
| Android packaging | **Buildozer + python-for-android** | Free route for packaging the Python engine/Kivy UI into an installable APK/AAB; build runs outside the phone |
| Android dev environment | **Cloud/desktop build environment (Google Colab or equivalent)** | User-facing product must not require Termux; APK is built outside the phone |
| VCS | **Git** (hosted on a free remote: Codeberg/GitHub) | Free; doubles as backup |
| Tests | `pytest` (+ stdlib `unittest` where lighter) | Free, standard |

## Rationale details

### Why Python and not Flutter/Dart or native?

Flutter is viable for Android UI but would force the entire engine into a new
language for no gameplay benefit. The engine's hardest problems (state, memory,
retrieval, validation) are logic-heavy, not UI-heavy. Python lets the user run
and package it into an Android APK with Buildozer. The end-user APK does not require Termux. If UI performance becomes an issue in Phase 7, the UI layer is the only
swappable part (see ARCHITECTURE.md §3) — that is an explicit, gated decision
point, not a hidden one.

### Why SQLite instead of JSON files?

JSON is fine for config; it is wrong for game state. SQLite gives atomic saves
(safe autosave on Android), one-file save slots, FTS5 for retrieval, and easy
export/import. Zero extra dependencies.

### Why an AI adapter instead of picking one model/provider?

Constitution §2.1 and §2.7: the engine must not depend on any paid or specific
AI service. The adapter pattern means local (llama.cpp) and remote
(OpenAI-compatible) backends are interchangeable, and tests use a scripted fake
adapter with zero cost.

## Dependency policy (binding)

1. New runtime dependencies require an ADR entry in `docs/PROJECT_HISTORY.md`.
2. Prefer stdlib. If stdlib is insufficient, prefer pure-Python, MIT/BSD/Apache
   licensed, actively maintained packages.
3. No dependency that requires a subscription, account, or paid key to *build or
   test* the engine. Optional AI backends are the only exception and must be
   runtime-swappable.

## Tooling risks of this stack

Captured in RISKS.md (R1–R6): Buildozer build friction, Termux limits, local
model size on phone, embedding retrieval cost.
